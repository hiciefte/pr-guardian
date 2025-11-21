"""Comment Classification Service based on constitution framework."""

import logging
import re
from typing import Literal

from src.models import (
    ClassificationType,
    CommentClassification,
    ReviewComment,
    TranslationExtraction,
)

logger = logging.getLogger(__name__)


def pre_classify_comment(comment: ReviewComment) -> CommentClassification:
    """
    Pre-classify a comment without extraction to determine if it's actionable.

    Used before LLM parsing to skip obviously non-actionable comments.

    Args:
        comment: Original review comment

    Returns:
        CommentClassification with basic classification
    """
    # Check conventional label from CodeRabbitAI
    label = (comment.conventional_label or "").lower()
    body_lower = comment.body.lower()

    # Question classification
    if label == "question" or ("?" in comment.body and "suggest" not in body_lower):
        return CommentClassification(
            comment_id=comment.id,
            type=ClassificationType.QUESTION,
            priority=3,
            should_implement=False,
            confidence=1.0,
            reasoning="Question - no implementation needed",
            skip_reason="Question - no implementation needed",
        )

    # Praise classification
    praise_words = ["good", "great", "excellent", "well done", "nice"]
    if label == "praise" or any(word in body_lower for word in praise_words):
        if "but" not in body_lower and "however" not in body_lower:
            return CommentClassification(
                comment_id=comment.id,
                type=ClassificationType.PRAISE,
                priority=3,
                should_implement=False,
                confidence=1.0,
                reasoning="Praise - no implementation needed",
                skip_reason="Praise - no implementation needed",
            )

    # Critical indicators
    critical_keywords = ["error", "bug", "broken", "wrong", "incorrect", "critical"]
    if label == "critical" or any(kw in body_lower for kw in critical_keywords):
        return CommentClassification(
            comment_id=comment.id,
            type=ClassificationType.CRITICAL,
            priority=1,
            should_implement=True,
            confidence=0.8,
            reasoning="Critical issue - requires attention",
        )

    # Nitpick classification
    nitpick_indicators = ["nitpick", "typo", "minor", "small", "trivial"]
    if label in nitpick_indicators or any(ind in body_lower for ind in nitpick_indicators):
        return CommentClassification(
            comment_id=comment.id,
            type=ClassificationType.NITPICK,
            priority=3,
            should_implement=True,
            confidence=0.7,
            reasoning="Minor improvement suggestion",
        )

    # Default to Constructive
    return CommentClassification(
        comment_id=comment.id,
        type=ClassificationType.CONSTRUCTIVE,
        priority=2,
        should_implement=True,
        confidence=0.8,
        reasoning="Constructive suggestion",
    )


# Pattern tags for comment categorization
PATTERN_TAGS = {
    "terminology": [
        "term", "terminology", "glossary", "vocabulary", "word choice",
        "technical term", "noun", "verb",
    ],
    "punctuation": [
        "punctuation", "period", "comma", "semicolon", "colon",
        "exclamation", "question mark",
    ],
    "formality": [
        "formal", "informal", "casual", "tone", "register",
        "polite", "respectful",
    ],
    "grammar": [
        "grammar", "tense", "conjugation", "agreement", "syntax",
        "plural", "singular",
    ],
    "consistency": [
        "consistent", "inconsistent", "match", "align", "uniform",
    ],
    "clarity": [
        "clear", "unclear", "ambiguous", "confusing", "understandable",
    ],
    "localization": [
        "locale", "culture", "format", "date", "number", "currency",
    ],
    "placeholder": [
        "placeholder", "variable", "parameter", "interpolation",
    ],
}

# Glossary conflict indicators
GLOSSARY_CONFLICT_PATTERNS = [
    r"glossary\s+(?:conflict|mismatch|disagree)",
    r"(?:differs?|different)\s+from\s+glossary",
    r"standard\s+term",
    r"established\s+(?:term|translation)",
]


def classify_comment(
    comment: ReviewComment,
    extraction: TranslationExtraction,
) -> CommentClassification:
    """
    Classify a comment based on constitution framework.

    Determines classification type, priority, and implementation decision.

    Args:
        comment: Original review comment
        extraction: LLM-extracted translation information

    Returns:
        CommentClassification with type, priority, and decision
    """
    # Detect pattern tags
    pattern_tags = _detect_pattern_tags(comment.body)

    # Check for glossary conflicts
    glossary_conflict = _check_glossary_conflict(comment.body)

    # Determine classification type and priority
    classification_type, priority = _determine_classification(
        comment=comment,
        extraction=extraction,
        pattern_tags=pattern_tags,
    )

    # Determine if should implement
    should_implement, skip_reason, requires_review = _determine_implementation(
        extraction=extraction,
        classification_type=classification_type,
        glossary_conflict=glossary_conflict,
    )

    # Build reasoning
    reasoning = _build_reasoning(
        classification_type=classification_type,
        extraction=extraction,
        pattern_tags=pattern_tags,
        glossary_conflict=glossary_conflict,
    )

    return CommentClassification(
        comment_id=comment.id,
        type=classification_type,
        priority=priority,
        should_implement=should_implement,
        confidence=extraction.confidence,
        reasoning=reasoning,
        skip_reason=skip_reason,
        pattern_tags=pattern_tags,
        affected_locales=[extraction.locale],
        requires_human_review=requires_review,
        glossary_conflict=glossary_conflict,
    )


def _detect_pattern_tags(body: str) -> list[str]:
    """
    Detect pattern tags in comment body.

    Args:
        body: Comment body text

    Returns:
        List of detected pattern tags
    """
    detected: list[str] = []
    body_lower = body.lower()

    for tag, keywords in PATTERN_TAGS.items():
        for keyword in keywords:
            if keyword in body_lower:
                detected.append(tag)
                break

    return detected


def _check_glossary_conflict(body: str) -> bool:
    """
    Check if comment indicates glossary conflict.

    Args:
        body: Comment body text

    Returns:
        True if glossary conflict detected
    """
    for pattern in GLOSSARY_CONFLICT_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            return True
    return False


def _determine_classification(
    comment: ReviewComment,
    extraction: TranslationExtraction,
    pattern_tags: list[str],
) -> tuple[ClassificationType, Literal[1, 2, 3]]:
    """
    Determine classification type and priority.

    Args:
        comment: Original review comment
        extraction: Translation extraction
        pattern_tags: Detected pattern tags

    Returns:
        Tuple of (classification_type, priority)
    """
    # Check conventional label from CodeRabbitAI
    label = (comment.conventional_label or "").lower()

    # Critical indicators
    critical_keywords = ["error", "bug", "broken", "wrong", "incorrect", "critical"]
    if label == "critical" or any(kw in extraction.reasoning.lower() for kw in critical_keywords):
        return ClassificationType.CRITICAL, 1

    # Question classification
    if label == "question" or "?" in comment.body and "suggest" not in comment.body.lower():
        return ClassificationType.QUESTION, 3

    # Praise classification
    if label == "praise" or any(
        word in comment.body.lower()
        for word in ["good", "great", "excellent", "well done", "nice"]
    ):
        if "but" not in comment.body.lower() and "however" not in comment.body.lower():
            return ClassificationType.PRAISE, 3

    # Nitpick classification
    nitpick_indicators = ["nitpick", "typo", "minor", "small", "trivial"]
    if label in nitpick_indicators or any(
        ind in extraction.reasoning.lower() for ind in nitpick_indicators
    ):
        return ClassificationType.NITPICK, 3

    # Punctuation and style are typically nitpicks
    if "punctuation" in pattern_tags or (
        "style" in pattern_tags and len(pattern_tags) == 1
    ):
        return ClassificationType.NITPICK, 3

    # Default to Constructive
    return ClassificationType.CONSTRUCTIVE, 2


def _determine_implementation(
    extraction: TranslationExtraction,
    classification_type: ClassificationType,
    glossary_conflict: bool,
) -> tuple[bool, str | None, bool]:
    """
    Determine implementation decision.

    Args:
        extraction: Translation extraction
        classification_type: Classification type
        glossary_conflict: Whether glossary conflict exists

    Returns:
        Tuple of (should_implement, skip_reason, requires_human_review)
    """
    # Skip glossary conflicts
    if glossary_conflict:
        return (
            False,
            "Glossary conflict detected - requires human review",
            True,
        )

    # Skip low confidence extractions
    if extraction.confidence < 0.60:
        return (
            False,
            f"Low confidence extraction ({extraction.confidence:.2f})",
            False,
        )

    # Questions and praise don't need implementation
    if classification_type == ClassificationType.QUESTION:
        return (
            False,
            "Question - no implementation needed",
            False,
        )

    if classification_type == ClassificationType.PRAISE:
        return (
            False,
            "Praise - no implementation needed",
            False,
        )

    # Medium confidence needs review
    if extraction.confidence < 0.80:
        return (
            True,
            None,
            True,  # requires human review
        )

    # High confidence - implement
    return (True, None, False)


def _build_reasoning(
    classification_type: ClassificationType,
    extraction: TranslationExtraction,
    pattern_tags: list[str],
    glossary_conflict: bool,
) -> str:
    """
    Build reasoning explanation for classification.

    Args:
        classification_type: Classification type
        extraction: Translation extraction
        pattern_tags: Detected pattern tags
        glossary_conflict: Whether glossary conflict exists

    Returns:
        Reasoning string
    """
    parts = []

    # Type reasoning
    type_reasons = {
        ClassificationType.CRITICAL: "Critical issue affecting functionality",
        ClassificationType.CONSTRUCTIVE: "Constructive suggestion improving quality",
        ClassificationType.NITPICK: "Minor style or formatting improvement",
        ClassificationType.QUESTION: "Question requiring clarification",
        ClassificationType.PRAISE: "Positive feedback on translation",
    }
    parts.append(type_reasons.get(classification_type, ""))

    # Pattern reasoning
    if pattern_tags:
        parts.append(f"Patterns: {', '.join(pattern_tags)}")

    # Confidence reasoning
    if extraction.confidence >= 0.80:
        parts.append("High confidence extraction")
    elif extraction.confidence >= 0.60:
        parts.append("Medium confidence - review recommended")
    else:
        parts.append("Low confidence - skipping")

    # Glossary conflict
    if glossary_conflict:
        parts.append("Glossary conflict detected")

    # LLM reasoning
    parts.append(f"LLM: {extraction.reasoning}")

    return ". ".join(part for part in parts if part)


def batch_classify_comments(
    comments: list[ReviewComment],
    extractions: list[TranslationExtraction],
) -> list[CommentClassification]:
    """
    Classify multiple comments in batch.

    Args:
        comments: List of review comments
        extractions: Corresponding list of extractions

    Returns:
        List of classifications
    """
    # Build comment lookup
    comment_map = {c.id: c for c in comments}

    classifications: list[CommentClassification] = []

    for extraction in extractions:
        comment = comment_map.get(extraction.comment_id)
        if not comment:
            logger.warning(
                f"No comment found for extraction {extraction.comment_id}"
            )
            continue

        classification = classify_comment(comment, extraction)
        classifications.append(classification)

    # Sort by priority
    classifications.sort(key=lambda c: c.priority)

    return classifications
