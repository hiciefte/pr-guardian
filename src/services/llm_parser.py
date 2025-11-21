"""LLM-Based Comment Parser using Anthropic Claude."""

import asyncio
import logging
import os
import time
from typing import Any

import anthropic

from src.models import ReviewComment, TranslationExtraction

logger = logging.getLogger(__name__)

# System prompt for extraction task
EXTRACTION_SYSTEM_PROMPT = """You are a translation review assistant. Your task is to extract structured translation change information from CodeRabbitAI review comments.

For each comment, extract:
1. The translation key being discussed
2. The original translation value
3. The suggested new translation value
4. The locale (language code in xx_XX format)
5. The reasoning for the change
6. Your confidence in the extraction (0.0-1.0)

Guidelines:
- Only extract if the comment clearly suggests a translation change
- If information is missing or ambiguous, lower your confidence
- Locale should be inferred from file path or content (e.g., es_ES, ja_JP, en_US)
- Confidence >= 0.80: Clear, unambiguous suggestion
- Confidence 0.60-0.79: Some ambiguity but likely correct
- Confidence < 0.60: Significant uncertainty, may be incorrect

Return structured data using the provided tool."""

# Tool definition for structured output
EXTRACTION_TOOL = {
    "name": "extract_translation_change",
    "description": "Extract translation change information from a review comment",
    "input_schema": {
        "type": "object",
        "properties": {
            "translation_key": {
                "type": "string",
                "description": "The translation key being changed",
            },
            "original_value": {
                "type": "string",
                "description": "Current translation text",
            },
            "new_value": {
                "type": "string",
                "description": "Suggested replacement text",
            },
            "locale": {
                "type": "string",
                "description": "Language locale in xx_XX format (e.g., es_ES, ja_JP)",
            },
            "reasoning": {
                "type": "string",
                "description": "Why the change is suggested",
            },
            "confidence": {
                "type": "number",
                "description": "Extraction confidence (0.0-1.0)",
            },
            "is_valid_extraction": {
                "type": "boolean",
                "description": "Whether the comment contains a valid translation change",
            },
        },
        "required": [
            "translation_key",
            "original_value",
            "new_value",
            "locale",
            "reasoning",
            "confidence",
            "is_valid_extraction",
        ],
    },
}


class CircuitBreaker:
    """Circuit breaker pattern for failure protection."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half-open

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )

    def record_success(self) -> None:
        """Record a success and reset failure count."""
        self.failure_count = 0
        self.state = "closed"

    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if reset timeout has passed
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.reset_timeout
            ):
                self.state = "half-open"
                return True
            return False

        # half-open: allow one request
        return True


class LLMParser:
    """
    LLM-based comment parser using Anthropic Claude.

    Uses Claude 3 Haiku for efficient translation extraction with
    structured output via tool use.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-haiku-20241022",
        max_tokens: int = 500,
        confidence_threshold: float = 0.80,
        max_retries: int = 3,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        """
        Initialize LLM parser.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use for parsing
            max_tokens: Maximum tokens for LLM response
            confidence_threshold: Minimum confidence for auto-implementation
            max_retries: Maximum retry attempts for API calls
            circuit_breaker: Circuit breaker for failure protection
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var."
            )

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.confidence_threshold = confidence_threshold
        self.max_retries = max_retries
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    async def parse_comment(
        self,
        comment: ReviewComment,
    ) -> TranslationExtraction | None:
        """
        Parse a review comment to extract translation change information.

        Args:
            comment: Review comment to parse

        Returns:
            TranslationExtraction if valid extraction, None otherwise
        """
        if not self.circuit_breaker.allow_request():
            logger.warning("Circuit breaker open, skipping request")
            return None

        # Build context from comment
        context = self._build_context(comment)

        for attempt in range(self.max_retries):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=EXTRACTION_SYSTEM_PROMPT,
                    tools=[EXTRACTION_TOOL],
                    tool_choice={"type": "tool", "name": "extract_translation_change"},
                    messages=[
                        {
                            "role": "user",
                            "content": context,
                        }
                    ],
                )

                # Extract tool use result
                extraction_data = self._extract_tool_result(response)
                if not extraction_data:
                    logger.debug(f"No extraction from comment {comment.id}")
                    return None

                # Check if valid extraction
                if not extraction_data.get("is_valid_extraction", False):
                    logger.debug(
                        f"Comment {comment.id} not a valid translation change"
                    )
                    return None

                # Build TranslationExtraction model
                extraction = TranslationExtraction(
                    translation_key=extraction_data["translation_key"],
                    original_value=extraction_data["original_value"],
                    new_value=extraction_data["new_value"],
                    locale=extraction_data["locale"],
                    reasoning=extraction_data["reasoning"],
                    confidence=extraction_data["confidence"],
                    comment_id=comment.id,
                    llm_model=self.model,
                )

                self.circuit_breaker.record_success()
                return extraction

            except anthropic.RateLimitError as e:
                logger.warning(f"Rate limited (attempt {attempt + 1}): {e}")
                await asyncio.sleep(2 ** attempt)

            except anthropic.APIError:
                logger.exception(f"API error (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    self.circuit_breaker.record_failure()
                await asyncio.sleep(1)

            except Exception:
                logger.exception("Unexpected error parsing comment")
                self.circuit_breaker.record_failure()
                return None

        return None

    async def parse_comments_parallel(
        self,
        comments: list[ReviewComment],
        max_concurrency: int = 10,
    ) -> list[TranslationExtraction]:
        """
        Parse multiple comments in parallel.

        Args:
            comments: List of review comments to parse
            max_concurrency: Maximum concurrent API calls

        Returns:
            List of successful extractions
        """
        if not comments:
            return []

        semaphore = asyncio.Semaphore(max_concurrency)

        async def parse_with_limit(comment: ReviewComment):
            async with semaphore:
                return await self.parse_comment(comment)

        tasks = [parse_with_limit(comment) for comment in comments]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        extractions: list[TranslationExtraction] = []
        for result in results:
            if isinstance(result, TranslationExtraction):
                extractions.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Extraction failed: {result}")

        logger.info(
            f"Parsed {len(extractions)} extractions from {len(comments)} comments"
        )
        return extractions

    def _build_context(self, comment: ReviewComment) -> str:
        """
        Build context string for LLM from comment.

        Args:
            comment: Review comment

        Returns:
            Context string for LLM
        """
        parts = [f"Review Comment ID: {comment.id}"]

        if comment.file_path:
            parts.append(f"File: {comment.file_path}")

        if comment.line_number:
            parts.append(f"Line: {comment.line_number}")

        if comment.conventional_label:
            parts.append(f"Label: {comment.conventional_label}")

        if comment.diff_hunk:
            parts.append(f"\nDiff Context:\n```\n{comment.diff_hunk}\n```")

        parts.append(f"\nComment Body:\n{comment.body}")

        return "\n".join(parts)

    def _extract_tool_result(self, response: Any) -> dict | None:
        """
        Extract tool use result from API response.

        Args:
            response: Anthropic API response

        Returns:
            Tool input dict or None
        """
        for content in response.content:
            if content.type == "tool_use":
                return content.input
        return None


def get_implementation_decision(confidence: float) -> str:
    """
    Get implementation decision based on confidence score.

    Args:
        confidence: Extraction confidence (0.0-1.0)

    Returns:
        Decision string: 'implement', 'human_review', or 'skip'
    """
    if confidence >= 0.80:
        return "implement"
    elif confidence >= 0.60:
        return "human_review"
    else:
        return "skip"
