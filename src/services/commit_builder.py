"""Commit Message Builder following conventional commit rules."""

import logging
import re
import textwrap

from src.models import (
    ChangeType,
    ClassificationType,
    CommentClassification,
    TranslationChange,
)

logger = logging.getLogger(__name__)

# Maximum lengths per cbea.ms/git-commit
MAX_SUBJECT_LENGTH = 50
MAX_BODY_LINE_LENGTH = 72

# Imperative mood verb mappings
PAST_TO_IMPERATIVE = {
    "added": "Add",
    "fixed": "Fix",
    "updated": "Update",
    "changed": "Change",
    "removed": "Remove",
    "improved": "Improve",
    "corrected": "Correct",
    "refined": "Refine",
    "replaced": "Replace",
    "modified": "Modify",
    "adjusted": "Adjust",
}

GERUND_TO_IMPERATIVE = {
    "adding": "Add",
    "fixing": "Fix",
    "updating": "Update",
    "changing": "Change",
    "removing": "Remove",
    "improving": "Improve",
    "correcting": "Correct",
    "refining": "Refine",
    "replacing": "Replace",
    "modifying": "Modify",
    "adjusting": "Adjust",
}


def build_commit_message(
    change: TranslationChange,
    classification: CommentClassification,
) -> str:
    """
    Build a commit message following conventional commit rules.

    Rules from cbea.ms/git-commit:
    1. Separate subject from body with blank line
    2. Limit subject line to 50 characters
    3. Capitalize the subject line
    4. Do not end subject line with period
    5. Use imperative mood in subject line
    6. Wrap body at 72 characters
    7. Use body to explain what and why

    Args:
        change: Translation change being committed
        classification: Comment classification with context

    Returns:
        Formatted commit message

    Example:
        message = build_commit_message(change, classification)
        # Returns:
        # Fix Spanish translation for greeting key
        #
        # Update 'hola' to 'Hola' for proper capitalization.
        #
        # CodeRabbitAI comment: #123
    """
    # Build subject line
    subject = _build_subject_line(change, classification)

    # Build body
    body = _build_body(change, classification)

    # Combine with blank line separator
    if body:
        return f"{subject}\n\n{body}"
    return subject


def _build_subject_line(
    change: TranslationChange,
    classification: CommentClassification,
) -> str:
    """
    Build subject line for commit message.

    Args:
        change: Translation change
        classification: Comment classification

    Returns:
        Subject line string
    """
    # Determine action verb based on change type
    verb_map = {
        ChangeType.FIX: "Fix",
        ChangeType.REFINEMENT: "Refine",
        ChangeType.UPDATE: "Update",
    }
    verb = verb_map.get(change.change_type, "Update")

    # Build description based on classification
    type_desc = {
        ClassificationType.CRITICAL: "critical issue in",
        ClassificationType.CONSTRUCTIVE: "translation for",
        ClassificationType.NITPICK: "style in",
    }
    desc = type_desc.get(classification.type, "translation in")

    # Build subject
    locale_name = change.locale.replace("_", " ")
    subject = f"{verb} {desc} {locale_name} {change.translation_key}"

    # Truncate if needed
    if len(subject) > MAX_SUBJECT_LENGTH:
        # Try shorter version
        subject = f"{verb} {locale_name} '{change.translation_key}'"

        if len(subject) > MAX_SUBJECT_LENGTH:
            # Truncate key name
            max_key_len = MAX_SUBJECT_LENGTH - len(f"{verb} {locale_name} ''") - 3
            key_truncated = change.translation_key[:max_key_len] + "..."
            subject = f"{verb} {locale_name} '{key_truncated}'"

    # Ensure capitalized and no trailing period
    subject = subject[0].upper() + subject[1:] if subject else subject
    subject = subject.rstrip(".")

    return subject


def _build_body(
    change: TranslationChange,
    classification: CommentClassification,
) -> str:
    """
    Build body for commit message.

    Args:
        change: Translation change
        classification: Comment classification

    Returns:
        Body string
    """
    lines = []

    # What changed
    change_desc = (
        f"Change '{change.original_value}' to '{change.new_value}' "
        f"in {change.file_path}."
    )
    lines.append(_wrap_text(change_desc))

    # Why it changed
    if classification.reasoning:
        # Extract LLM reasoning if present
        reasoning = classification.reasoning
        if "LLM:" in reasoning:
            reasoning = reasoning.split("LLM:")[-1].strip()

        why = f"Reason: {reasoning}"
        lines.append(_wrap_text(why))

    # Pattern tags if present
    if classification.pattern_tags:
        tags = ", ".join(classification.pattern_tags)
        lines.append(f"Tags: {tags}")

    # CodeRabbitAI comment reference
    lines.append("")
    lines.append(f"CodeRabbitAI comment: #{change.comment_id}")

    return "\n".join(lines)


def _wrap_text(text: str) -> str:
    """
    Wrap text to maximum line length.

    Args:
        text: Text to wrap

    Returns:
        Wrapped text
    """
    return "\n".join(
        textwrap.wrap(text, width=MAX_BODY_LINE_LENGTH)
    )


def validate_commit_message(message: str) -> tuple[bool, list[str]]:
    """
    Validate commit message against conventional rules.

    Args:
        message: Commit message to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors: list[str] = []

    if not message:
        return False, ["Empty commit message"]

    lines = message.split("\n")
    subject = lines[0]

    # Rule 2: Subject length
    if len(subject) > MAX_SUBJECT_LENGTH:
        errors.append(
            f"Subject line too long ({len(subject)} chars, max {MAX_SUBJECT_LENGTH})"
        )

    # Rule 3: Capitalization
    if subject and not subject[0].isupper():
        errors.append("Subject line should be capitalized")

    # Rule 4: No trailing period
    if subject.endswith("."):
        errors.append("Subject line should not end with period")

    # Rule 5: Imperative mood
    if not _is_imperative_mood(subject):
        errors.append("Subject line should use imperative mood")

    # Rule 1: Blank line separator
    if len(lines) > 1 and lines[1].strip():
        errors.append("Second line should be blank (separate subject from body)")

    # Rule 6: Body line length
    for i, line in enumerate(lines[2:], start=3):
        if len(line) > MAX_BODY_LINE_LENGTH:
            errors.append(
                f"Line {i} too long ({len(line)} chars, max {MAX_BODY_LINE_LENGTH})"
            )

    return len(errors) == 0, errors


def _is_imperative_mood(subject: str) -> bool:
    """
    Check if subject line uses imperative mood.

    Args:
        subject: Subject line text

    Returns:
        True if appears to use imperative mood
    """
    if not subject:
        return False

    first_word = subject.split()[0].lower()

    # Check against past tense
    if first_word in PAST_TO_IMPERATIVE:
        return False

    # Check against gerund
    if first_word in GERUND_TO_IMPERATIVE:
        return False

    # Check common past tense endings
    if first_word.endswith("ed") and first_word not in ["need", "seed"]:
        return False

    # Check gerund endings
    if first_word.endswith("ing"):
        return False

    return True


def ensure_imperative_mood(subject: str) -> str:
    """
    Convert subject line to imperative mood if needed.

    Args:
        subject: Subject line text

    Returns:
        Subject line in imperative mood
    """
    if not subject:
        return subject

    words = subject.split()
    first_word = words[0].lower()

    # Convert past tense
    if first_word in PAST_TO_IMPERATIVE:
        words[0] = PAST_TO_IMPERATIVE[first_word]
        return " ".join(words)

    # Convert gerund
    if first_word in GERUND_TO_IMPERATIVE:
        words[0] = GERUND_TO_IMPERATIVE[first_word]
        return " ".join(words)

    # Try to fix common patterns
    if first_word.endswith("ed"):
        # Simple conversion: added -> add
        base = first_word[:-2] if first_word.endswith("ded") else first_word[:-1]
        words[0] = base.capitalize()
        return " ".join(words)

    if first_word.endswith("ing"):
        # Simple conversion: adding -> add
        base = first_word[:-3]
        if first_word.endswith("tting"):
            base = first_word[:-4]
        words[0] = base.capitalize()
        return " ".join(words)

    return subject


def build_batch_commit_message(
    changes: list[TranslationChange],
    classifications: list[CommentClassification],
) -> str:
    """
    Build a commit message for multiple changes.

    Args:
        changes: List of translation changes
        classifications: Corresponding classifications

    Returns:
        Combined commit message
    """
    if not changes:
        return ""

    if len(changes) == 1:
        return build_commit_message(changes[0], classifications[0])

    # Group by locale
    by_locale: dict[str, list[TranslationChange]] = {}
    for change in changes:
        if change.locale not in by_locale:
            by_locale[change.locale] = []
        by_locale[change.locale].append(change)

    # Build subject
    locale_count = len(by_locale)
    change_count = len(changes)

    if locale_count == 1:
        locale = list(by_locale.keys())[0]
        subject = f"Update {change_count} translations in {locale}"
    else:
        subject = f"Update {change_count} translations across {locale_count} locales"

    # Truncate if needed
    if len(subject) > MAX_SUBJECT_LENGTH:
        subject = f"Update {change_count} translations"

    # Build body
    body_lines = []

    for locale, locale_changes in by_locale.items():
        body_lines.append(f"\n{locale}:")
        for change in locale_changes:
            body_lines.append(f"  - {change.translation_key}")

    # Add comment references
    comment_ids = sorted(set(c.comment_id for c in changes))
    body_lines.append("")
    body_lines.append(
        f"CodeRabbitAI comments: {', '.join(f'#{cid}' for cid in comment_ids)}"
    )

    return f"{subject}\n" + "\n".join(body_lines)
