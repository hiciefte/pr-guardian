"""Feedback pattern aggregation service for PR Guardian."""

import logging
from collections import defaultdict
from typing import Optional

from src.models import (
    CommentClassification,
    FeedbackPattern,
    PatternSeverity,
    PatternType,
    TranslationChange,
)

logger = logging.getLogger(__name__)

# Pattern type mapping from tags to PatternType enum
PATTERN_TAG_MAPPING: dict[str, PatternType] = {
    "terminology": PatternType.TERMINOLOGY,
    "term": PatternType.TERMINOLOGY,
    "vocab": PatternType.TERMINOLOGY,
    "word-choice": PatternType.TERMINOLOGY,
    "punctuation": PatternType.PUNCTUATION,
    "punct": PatternType.PUNCTUATION,
    "formality": PatternType.FORMALITY,
    "formal": PatternType.FORMALITY,
    "tone": PatternType.FORMALITY,
    "register": PatternType.FORMALITY,
    "grammar": PatternType.GRAMMAR,
    "syntax": PatternType.GRAMMAR,
    "agreement": PatternType.GRAMMAR,
    "placeholder": PatternType.PLACEHOLDER,
    "variable": PatternType.PLACEHOLDER,
    "format": PatternType.PLACEHOLDER,
    "cultural": PatternType.CULTURAL,
    "localization": PatternType.CULTURAL,
    "regional": PatternType.CULTURAL,
}

# Frequency thresholds for severity assignment
SEVERITY_THRESHOLDS = {
    "critical": 10,  # 10+ occurrences = critical
    "moderate": 5,   # 5-9 occurrences = moderate
    "minor": 1,      # 1-4 occurrences = minor
}

# Recommendation templates by pattern type
RECOMMENDATION_TEMPLATES: dict[PatternType, list[str]] = {
    PatternType.TERMINOLOGY: [
        "Review and update glossary with consistent terminology",
        "Create terminology guidelines for affected locales",
        "Consider implementing term base validation in translation workflow",
    ],
    PatternType.PUNCTUATION: [
        "Establish locale-specific punctuation rules in style guide",
        "Add punctuation validation to pre-commit hooks",
        "Review spacing rules around punctuation marks",
    ],
    PatternType.FORMALITY: [
        "Define formality levels for each target locale",
        "Create formal/informal usage guidelines",
        "Review audience expectations for tone consistency",
    ],
    PatternType.GRAMMAR: [
        "Add grammar checking to translation review process",
        "Create grammar reference for common error patterns",
        "Consider automated grammar validation tools",
    ],
    PatternType.PLACEHOLDER: [
        "Implement placeholder validation in CI/CD pipeline",
        "Document placeholder naming conventions",
        "Add automated tests for placeholder integrity",
    ],
    PatternType.CULTURAL: [
        "Conduct cultural review for affected locales",
        "Update cultural adaptation guidelines",
        "Consider regional variants for culturally sensitive content",
    ],
}


def aggregate_feedback_patterns(
    classifications: list[CommentClassification],
    changes: list[TranslationChange],
    session_id: str,
) -> list[FeedbackPattern]:
    """
    Aggregate CodeRabbitAI feedback patterns for translation system improvements.

    Analyzes classifications and changes to detect recurring patterns by type,
    counting frequency per locale and extracting examples.

    Args:
        classifications: List of comment classifications from the session
        changes: List of translation changes implemented
        session_id: Current session identifier

    Returns:
        List of aggregated feedback patterns with severity and recommendations
    """
    if not classifications:
        logger.debug("No classifications to aggregate")
        return []

    # Group by pattern type
    pattern_data: dict[PatternType, dict] = defaultdict(
        lambda: {
            "frequency": 0,
            "locales": set(),
            "examples": [],
            "comment_ids": set(),
        }
    )

    # Process classifications
    for classification in classifications:
        if not classification.should_implement:
            continue

        # Extract pattern types from tags
        pattern_types = _extract_pattern_types(classification.pattern_tags)

        if not pattern_types:
            # Default to terminology if no specific pattern detected
            pattern_types = [PatternType.TERMINOLOGY]

        for pattern_type in pattern_types:
            data = pattern_data[pattern_type]
            data["frequency"] += 1
            data["comment_ids"].add(classification.comment_id)

            # Add affected locales
            for locale in classification.affected_locales:
                data["locales"].add(locale)

            # Add example (limit to 5)
            if len(data["examples"]) < 5:
                example = _format_example(classification, changes)
                if example and example not in data["examples"]:
                    data["examples"].append(example)

    # Convert to FeedbackPattern objects
    patterns: list[FeedbackPattern] = []

    for pattern_type, data in pattern_data.items():
        if data["frequency"] == 0:
            continue

        # Ensure we have at least one example
        if not data["examples"]:
            data["examples"] = [f"Pattern detected in {data['frequency']} comment(s)"]

        # Ensure we have at least one locale
        locales = list(data["locales"]) if data["locales"] else ["en_US"]

        severity = _determine_severity(data["frequency"])
        recommendations = _generate_recommendations(pattern_type, data["frequency"])

        try:
            pattern = FeedbackPattern(
                pattern_type=pattern_type,
                frequency=data["frequency"],
                affected_locales=locales,
                examples=data["examples"][:5],  # Max 5 examples
                severity=severity,
                recommendations=recommendations,
                session_id=session_id,
                automated_fix_possible=_can_automate(pattern_type),
            )
            patterns.append(pattern)
            logger.debug(
                f"Created pattern: {pattern_type.value} with frequency {data['frequency']}"
            )
        except ValueError as e:
            logger.warning(f"Failed to create pattern {pattern_type}: {e}")
            continue

    # Sort by severity and frequency
    patterns.sort(
        key=lambda p: (
            {"critical": 0, "moderate": 1, "minor": 2}[p.severity.value],
            -p.frequency,
        )
    )

    logger.info(f"Aggregated {len(patterns)} feedback patterns from {len(classifications)} classifications")
    return patterns


def should_create_issue(
    patterns: list[FeedbackPattern],
    min_patterns: int = 1,
    min_critical: int = 1,
    min_total_frequency: int = 3,
) -> bool:
    """
    Determine if feedback patterns warrant creating a GitHub issue.

    Args:
        patterns: List of aggregated feedback patterns
        min_patterns: Minimum number of patterns required
        min_critical: Minimum critical patterns to auto-create issue
        min_total_frequency: Minimum total frequency across all patterns

    Returns:
        True if an issue should be created
    """
    if not patterns:
        return False

    # Count critical patterns
    critical_count = sum(
        1 for p in patterns if p.severity == PatternSeverity.CRITICAL
    )

    # Always create issue for critical patterns
    if critical_count >= min_critical:
        logger.info(f"Issue creation triggered: {critical_count} critical pattern(s)")
        return True

    # Check minimum patterns threshold
    if len(patterns) < min_patterns:
        return False

    # Check total frequency threshold
    total_frequency = sum(p.frequency for p in patterns)
    if total_frequency >= min_total_frequency:
        logger.info(
            f"Issue creation triggered: total frequency {total_frequency} >= {min_total_frequency}"
        )
        return True

    # Check for high-priority patterns
    high_priority_count = sum(1 for p in patterns if p.is_high_priority)
    if high_priority_count >= 2:
        logger.info(f"Issue creation triggered: {high_priority_count} high-priority patterns")
        return True

    return False


def _extract_pattern_types(tags: list[str]) -> list[PatternType]:
    """Extract PatternType enums from classification tags."""
    pattern_types: list[PatternType] = []

    for tag in tags:
        tag_lower = tag.lower().strip()
        if tag_lower in PATTERN_TAG_MAPPING:
            pattern_type = PATTERN_TAG_MAPPING[tag_lower]
            if pattern_type not in pattern_types:
                pattern_types.append(pattern_type)

    return pattern_types


def _determine_severity(frequency: int) -> PatternSeverity:
    """Determine severity level based on frequency thresholds."""
    if frequency >= SEVERITY_THRESHOLDS["critical"]:
        return PatternSeverity.CRITICAL
    elif frequency >= SEVERITY_THRESHOLDS["moderate"]:
        return PatternSeverity.MODERATE
    else:
        return PatternSeverity.MINOR


def _generate_recommendations(pattern_type: PatternType, frequency: int) -> list[str]:
    """Generate improvement recommendations based on pattern type and frequency."""
    base_recommendations = RECOMMENDATION_TEMPLATES.get(pattern_type, [])

    if not base_recommendations:
        return ["Review and address recurring feedback patterns"]

    recommendations = list(base_recommendations)

    # Add frequency-specific recommendations
    if frequency >= SEVERITY_THRESHOLDS["critical"]:
        recommendations.insert(0, f"PRIORITY: Address {frequency} occurrences urgently")

    return recommendations[:3]  # Limit to 3 recommendations


def _format_example(
    classification: CommentClassification,
    changes: list[TranslationChange],
) -> Optional[str]:
    """Format an example from classification and related changes."""
    # Find related change
    related_change = next(
        (c for c in changes if c.comment_id == classification.comment_id),
        None
    )

    if related_change:
        return (
            f"{related_change.translation_key}: "
            f"'{related_change.original_value[:50]}...' -> "
            f"'{related_change.new_value[:50]}...'"
        )

    # Fallback to reasoning excerpt
    if classification.reasoning:
        return classification.reasoning[:100]

    return None


def _can_automate(pattern_type: PatternType) -> bool:
    """Determine if pattern type can be automatically fixed."""
    automatable = {
        PatternType.PLACEHOLDER,
        PatternType.PUNCTUATION,
    }
    return pattern_type in automatable
