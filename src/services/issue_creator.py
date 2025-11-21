"""GitHub issue creation service for PR Guardian feedback."""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.models import (
    FeedbackIssue,
    FeedbackPattern,
    PatternSeverity,
    PatternType,
    SessionReport,
)
from src.services.github_client import GitHubClient

logger = logging.getLogger(__name__)


class IssueCreator:
    """
    Creates GitHub issues with aggregated feedback patterns.

    Generates well-formatted markdown issues with session summaries,
    pattern analysis tables, and improvement recommendations.
    """

    def __init__(self, client: GitHubClient):
        """
        Initialize IssueCreator.

        Args:
            client: GitHubClient instance for API operations
        """
        self._client = client

    def create_feedback_issue(
        self,
        owner: str,
        repo: str,
        session_report: SessionReport,
        patterns: list[FeedbackPattern],
    ) -> FeedbackIssue:
        """
        Create a feedback issue with aggregated patterns.

        Args:
            owner: Repository owner
            repo: Repository name
            session_report: Session report with statistics
            patterns: List of aggregated feedback patterns

        Returns:
            Created FeedbackIssue with issue details

        Raises:
            GitHubAPIError: On issue creation failure
        """
        if not patterns:
            raise ValueError("Cannot create issue without patterns")

        # Generate issue content
        title = self._generate_title(session_report, patterns)
        body = self.format_issue_body(session_report, patterns)
        labels = self._generate_labels(patterns)

        # Create issue via GitHub API
        result = self._client.create_issue(
            owner=owner,
            repo=repo,
            title=title,
            body=body,
            labels=labels,
        )

        # Extract pattern types for tracking
        pattern_types = [p.pattern_type.value for p in patterns]

        issue = FeedbackIssue(
            issue_number=result["number"],
            url=result["url"],
            title=title,
            body=body,
            target_repository=f"{owner}/{repo}",
            created_at=datetime.now(timezone.utc),
            session_id=session_report.session_id,
            pattern_types=pattern_types,
            labels=labels,
        )

        logger.info(
            f"Created feedback issue #{issue.issue_number} in {owner}/{repo} "
            f"with {len(patterns)} patterns"
        )

        return issue

    def format_issue_body(
        self,
        session_report: SessionReport,
        patterns: list[FeedbackPattern],
    ) -> str:
        """
        Generate markdown issue body with complete analysis.

        Args:
            session_report: Session report with statistics
            patterns: List of aggregated feedback patterns

        Returns:
            Formatted markdown string
        """
        sections = [
            self._format_header(),
            self._format_session_summary(session_report),
            self._format_patterns_section(patterns),
            self._format_recommendations_section(patterns),
            self._format_affected_locales_section(patterns),
            self._format_examples_section(patterns),
            self._format_footer(session_report),
        ]

        return "\n\n".join(sections)

    def format_patterns_table(self, patterns: list[FeedbackPattern]) -> str:
        """
        Format patterns as a markdown table.

        Args:
            patterns: List of feedback patterns

        Returns:
            Formatted markdown table
        """
        if not patterns:
            return "*No patterns detected*"

        lines = [
            "| Pattern Type | Frequency | Severity | Locales | Automatable |",
            "|-------------|-----------|----------|---------|-------------|",
        ]

        for pattern in patterns:
            severity_icon = self._get_severity_icon(pattern.severity)
            locales = ", ".join(pattern.affected_locales[:3])
            if len(pattern.affected_locales) > 3:
                locales += f" +{len(pattern.affected_locales) - 3}"

            automatable = "Yes" if pattern.automated_fix_possible else "No"

            lines.append(
                f"| {pattern.pattern_type.value.title()} | "
                f"{pattern.frequency} | "
                f"{severity_icon} {pattern.severity.value.title()} | "
                f"{locales} | "
                f"{automatable} |"
            )

        return "\n".join(lines)

    def _generate_title(
        self,
        session_report: SessionReport,
        patterns: list[FeedbackPattern],
    ) -> str:
        """Generate issue title based on patterns."""
        # Count severity
        critical_count = sum(
            1 for p in patterns if p.severity == PatternSeverity.CRITICAL
        )

        if critical_count > 0:
            prefix = f"[CRITICAL] "
        else:
            prefix = ""

        # Get primary pattern types
        pattern_names = [p.pattern_type.value.title() for p in patterns[:3]]
        pattern_str = ", ".join(pattern_names)

        date_str = session_report.start_time.strftime("%Y-%m-%d")

        return f"{prefix}Translation Feedback: {pattern_str} ({date_str})"

    def _generate_labels(self, patterns: list[FeedbackPattern]) -> list[str]:
        """Generate issue labels based on patterns."""
        labels = ["translation-feedback", "automated", "pr-guardian"]

        # Add severity label
        has_critical = any(
            p.severity == PatternSeverity.CRITICAL for p in patterns
        )
        if has_critical:
            labels.append("priority:critical")
        elif any(p.severity == PatternSeverity.MODERATE for p in patterns):
            labels.append("priority:moderate")

        # Add pattern type labels (limit to avoid too many)
        pattern_types = set(p.pattern_type for p in patterns)
        for pt in list(pattern_types)[:3]:
            labels.append(f"pattern:{pt.value}")

        return labels

    def _format_header(self) -> str:
        """Format issue header."""
        return (
            "## PR Guardian Translation Feedback\n\n"
            "This issue was automatically generated by PR Guardian based on "
            "CodeRabbitAI review feedback patterns detected during translation PR processing."
        )

    def _format_session_summary(self, session_report: SessionReport) -> str:
        """Format session summary section."""
        repos = ", ".join(session_report.repositories_processed) or "N/A"
        date_str = session_report.start_time.strftime("%Y-%m-%d %H:%M UTC")
        duration = (
            f"{session_report.duration_seconds:.1f}s"
            if session_report.duration_seconds
            else "N/A"
        )

        return (
            "### Session Summary\n\n"
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| Session ID | `{session_report.session_id}` |\n"
            f"| Date | {date_str} |\n"
            f"| Duration | {duration} |\n"
            f"| Repositories | {repos} |\n"
            f"| PRs Processed | {session_report.prs_processed} |\n"
            f"| Comments Processed | {session_report.comments_classified} |\n"
            f"| Changes Implemented | {session_report.changes_implemented} |\n"
            f"| Commits Created | {session_report.commits_created} |"
        )

    def _format_patterns_section(self, patterns: list[FeedbackPattern]) -> str:
        """Format pattern analysis section."""
        table = self.format_patterns_table(patterns)

        total_frequency = sum(p.frequency for p in patterns)

        return (
            "### Pattern Analysis\n\n"
            f"**Total Patterns Detected:** {len(patterns)}\n"
            f"**Total Occurrences:** {total_frequency}\n\n"
            f"{table}"
        )

    def _format_recommendations_section(
        self, patterns: list[FeedbackPattern]
    ) -> str:
        """Format recommendations section."""
        # Collect unique recommendations prioritized by pattern severity
        seen_recs: set[str] = set()
        recommendations: list[tuple[str, PatternSeverity]] = []

        for pattern in patterns:
            for rec in pattern.recommendations:
                if rec not in seen_recs:
                    seen_recs.add(rec)
                    recommendations.append((rec, pattern.severity))

        # Sort by severity
        severity_order = {"critical": 0, "moderate": 1, "minor": 2}
        recommendations.sort(
            key=lambda x: severity_order.get(x[1].value, 3)
        )

        lines = ["### Recommendations\n"]

        for rec, severity in recommendations[:10]:  # Limit to 10
            icon = self._get_severity_icon(severity)
            lines.append(f"- {icon} {rec}")

        return "\n".join(lines)

    def _format_affected_locales_section(
        self, patterns: list[FeedbackPattern]
    ) -> str:
        """Format affected locales section."""
        # Aggregate locales across patterns
        locale_counts: dict[str, int] = {}
        for pattern in patterns:
            for locale in pattern.affected_locales:
                locale_counts[locale] = locale_counts.get(locale, 0) + pattern.frequency

        # Sort by frequency
        sorted_locales = sorted(
            locale_counts.items(), key=lambda x: x[1], reverse=True
        )

        if not sorted_locales:
            return "### Affected Locales\n\n*No locale information available*"

        lines = ["### Affected Locales\n"]
        for locale, count in sorted_locales:
            lines.append(f"- **{locale}**: {count} occurrence(s)")

        return "\n".join(lines)

    def _format_examples_section(self, patterns: list[FeedbackPattern]) -> str:
        """Format examples section."""
        lines = ["### Examples\n"]

        for pattern in patterns[:5]:  # Limit to 5 patterns
            lines.append(f"#### {pattern.pattern_type.value.title()}\n")

            for i, example in enumerate(pattern.examples[:3], 1):
                # Escape backticks in examples
                escaped = example.replace("`", "'")
                lines.append(f"{i}. `{escaped}`")

            lines.append("")

        return "\n".join(lines)

    def _format_footer(self, session_report: SessionReport) -> str:
        """Format issue footer."""
        return (
            "---\n\n"
            "*This issue was automatically generated by "
            "[PR Guardian](https://github.com/pr-guardian/pr-guardian). "
            "Please review and take appropriate action on the identified patterns.*\n\n"
            f"Session: `{session_report.session_id}`"
        )

    def _get_severity_icon(self, severity: PatternSeverity) -> str:
        """Get icon for severity level."""
        icons = {
            PatternSeverity.CRITICAL: "!!",
            PatternSeverity.MODERATE: "!",
            PatternSeverity.MINOR: "-",
        }
        return icons.get(severity, "-")
