# Anthropic API Contract: PR Guardian

**Phase**: 1 (Design)
**Date**: 2025-10-24
**Status**: Complete
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)

## Overview

This document defines the Anthropic REST API interaction patterns for PR Guardian's LLM-based comment parsing, including endpoint specifications, tool use/function calling schemas, request/response formats, error handling, retry logic, and cost optimization strategies. All API interactions use the official Anthropic Python SDK (`anthropic==0.40.0`).

**Primary Use Case**: Parse natural language CodeRabbitAI review comments (e.g., "nitpick: Consider using 'Hola' instead of 'Saludo'") into structured translation change data with confidence scoring.

**Selected Model**: Claude 3 Haiku (`claude-3-haiku-20240307`) - Selected for 85-90% accuracy, 1.4s p50 latency, and $1.13/month optimized cost.

---

## Authentication

### API Key Requirements

**API Key Type**: Anthropic API Key (project-specific or workspace-wide)

**Obtaining API Key**:
1. Visit https://console.anthropic.com/
2. Navigate to Settings → API Keys
3. Create new API key with descriptive name (e.g., "pr-guardian-production")
4. Copy key immediately (only shown once)

**Required Permissions**:
- Claude API access (Messages API endpoint)
- No additional scopes required (API key has full access by default)

**API Key Storage**:
```bash
# Environment variable (runtime mounting)
export ANTHROPIC_API_KEY="sk-ant-api03-xxxxxxxxxxxxxxxxxxxx"

# Docker Compose
environment:
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# Docker Secrets (recommended for production)
secrets:
  anthropic_api_key:
    file: /secrets/anthropic_api_key
```

### Authentication Verification

**SDK Initialization**:
```python
from anthropic import Anthropic
import os

# Initialize client with API key from environment
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Test authentication with minimal request
try:
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=10,
        messages=[{"role": "user", "content": "Test"}]
    )
    print("✓ Anthropic API authenticated successfully")
except Exception as e:
    print(f"✗ Anthropic API authentication failed: {e}")
    exit(1)
```

**Error Codes**:
- `401 Unauthorized`: Invalid or missing API key
- `403 Forbidden`: API key lacks necessary permissions
- `429 Too Many Requests`: Rate limit exceeded

**Contract**:
- Must verify API key validity on startup before processing
- Exit with error code 1 if authentication fails
- Log authentication success (redact API key value)
- Cache client instance for session reuse (avoid re-initialization)

---

## Rate Limiting

### API Limits

**Anthropic API Rate Limits** (as of 2025-10-24):
- **Requests**: 50 requests/minute (tier-dependent, may vary)
- **Tokens**: 40,000 tokens/minute input, 40,000 tokens/minute output (tier-dependent)
- **Concurrent Requests**: 5 concurrent connections (tier-dependent)

**Rate Limit Headers** (returned in response):
```
anthropic-ratelimit-requests-limit: 50
anthropic-ratelimit-requests-remaining: 49
anthropic-ratelimit-requests-reset: 2025-10-24T14:30:00Z
anthropic-ratelimit-tokens-limit: 40000
anthropic-ratelimit-tokens-remaining: 39850
anthropic-ratelimit-tokens-reset: 2025-10-24T14:30:00Z
```

### Parallel Request Strategy

For PR Guardian's use case (200 comments in 30-minute window):
- **Sequential Processing**: 200 × 1.5s = 300s (5 minutes)
- **Parallel Processing (10 concurrent)**: 200 / 10 × 1.5s = 30s
- **Recommended Concurrency**: 5-10 concurrent requests (within API limits)

**Implementation**:
```python
import asyncio
from anthropic import AsyncAnthropic

# Initialize async client
async_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Semaphore for concurrency control
semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

async def parse_comment_async(comment: ReviewComment) -> TranslationExtraction:
    """Parse single comment with concurrency control."""
    async with semaphore:
        response = await async_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": format_comment(comment)}],
            tools=[extraction_tool]
        )
        return extract_from_response(response)

# Process all comments in parallel
async def parse_all_comments(comments: list[ReviewComment]) -> list[TranslationExtraction]:
    """Parse multiple comments in parallel."""
    tasks = [parse_comment_async(comment) for comment in comments]
    extractions = await asyncio.gather(*tasks)
    return extractions

# Usage
extractions = asyncio.run(parse_all_comments(comments))
```

### Exponential Backoff Implementation

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import anthropic

@retry(
    retry=retry_if_exception_type((
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
        anthropic.APITimeoutError
    )),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def parse_comment_with_retry(
    comment_body: str,
    file_path: str,
    diff_hunk: str
) -> TranslationExtraction:
    """Parse comment with automatic retry on transient failures."""
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": format_comment(comment_body, file_path, diff_hunk)}],
        tools=[EXTRACTION_TOOL]
    )
    return extract_from_response(response)
```

**Retry Strategy**:
- **Max Attempts**: 3
- **Wait Times**: 2s, 4s, 8s (exponential with multiplier=1)
- **Jitter**: Automatic via tenacity library
- **Retryable Errors**: `APIConnectionError`, `RateLimitError`, `APITimeoutError`
- **Non-Retryable Errors**: `AuthenticationError`, `BadRequestError`, `InvalidRequestError`

---

## API Endpoints

### Messages API (Primary Endpoint)

**Endpoint**: `POST https://api.anthropic.com/v1/messages`

**SDK Method**: `client.messages.create()`

**Purpose**: Create structured translation extraction from natural language comment using tool use/function calling.

**Request Schema**:
```python
from pydantic import BaseModel, Field

class TranslationExtraction(BaseModel):
    """Structured extraction from CodeRabbitAI comment."""
    translation_key: str = Field(description="The key in the translation file being changed")
    original_value: str = Field(description="Current translation text")
    new_value: str = Field(description="Suggested replacement text")
    locale: str = Field(description="Language locale (e.g., es_ES, de_DE)")
    reasoning: str = Field(description="Why the change is suggested")
    confidence: float = Field(description="Confidence in extraction accuracy (0.0-1.0)", ge=0.0, le=1.0)

# Define tool for structured output
EXTRACTION_TOOL = {
    "name": "extract_translation_change",
    "description": "Extract structured translation change from CodeRabbitAI comment",
    "input_schema": TranslationExtraction.model_json_schema()
}

# System prompt (cached for cost optimization)
SYSTEM_PROMPT = """You are a translation change extraction assistant.

Your task: Parse CodeRabbitAI review comments about translation changes and extract:
- translation_key: The key in the translation file being changed
- original_value: Current translation text
- new_value: Suggested replacement text
- locale: Language locale (e.g., es_ES, de_DE)
- reasoning: Why the change is suggested
- confidence: Your confidence in extraction accuracy (0.0-1.0)

Rules:
- Extract locale from file path if not explicit in comment
- If original_value not stated, infer from diff_hunk
- Be precise with quotation marks and special characters
- Return confidence < 0.8 if comment is ambiguous
- Preserve placeholder variables exactly ({variable}, %s, {{key}}, etc.)
- Return confidence < 0.6 if extraction is uncertain or comment is unclear"""
```

**Request Example**:
```python
response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=500,
    system=SYSTEM_PROMPT,  # Cached for cost optimization
    messages=[{
        "role": "user",
        "content": f"""File: {file_path}

Diff context:
{diff_hunk}

CodeRabbitAI comment:
{comment_body}

Extract the translation change as structured data."""
    }],
    tools=[EXTRACTION_TOOL],
    tool_choice={"type": "tool", "name": "extract_translation_change"}
)
```

**Response Schema**:
```python
# Successful tool use response
{
    "id": "msg_01XYZ...",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_01ABC...",
            "name": "extract_translation_change",
            "input": {
                "translation_key": "greeting",
                "original_value": "Saludo",
                "new_value": "Hola",
                "locale": "es_ES",
                "reasoning": "The suggestion recommends 'Hola' as a more natural and common Spanish greeting...",
                "confidence": 0.87
            }
        }
    ],
    "model": "claude-3-haiku-20240307",
    "stop_reason": "tool_use",
    "usage": {
        "input_tokens": 245,
        "output_tokens": 78
    }
}
```

**Extraction Function**:
```python
def extract_from_response(response) -> TranslationExtraction:
    """Extract TranslationExtraction from Anthropic API response."""
    # Validate response contains tool use
    if not response.content or response.content[0].type != "tool_use":
        raise ValueError("Response does not contain tool use")

    # Extract tool use block
    tool_use = response.content[0]

    # Validate tool name matches
    if tool_use.name != "extract_translation_change":
        raise ValueError(f"Unexpected tool name: {tool_use.name}")

    # Parse input into Pydantic model for validation
    extraction = TranslationExtraction(**tool_use.input)

    return extraction
```

---

## Error Handling

### Error Categories

**1. Authentication Errors (Non-Retryable)**
```python
from anthropic import AuthenticationError

try:
    response = client.messages.create(...)
except AuthenticationError as e:
    logger.error(f"Authentication failed: {e}")
    # Check ANTHROPIC_API_KEY environment variable
    # Exit application (cannot proceed without valid API key)
    exit(1)
```

**2. Rate Limit Errors (Retryable with Backoff)**
```python
from anthropic import RateLimitError

try:
    response = client.messages.create(...)
except RateLimitError as e:
    logger.warning(f"Rate limit exceeded: {e}")
    # Automatic retry via @retry decorator
    # Or manual: wait for e.retry_after seconds
    time.sleep(e.retry_after if hasattr(e, 'retry_after') else 60)
```

**3. Invalid Request Errors (Non-Retryable)**
```python
from anthropic import BadRequestError, InvalidRequestError

try:
    response = client.messages.create(...)
except (BadRequestError, InvalidRequestError) as e:
    logger.error(f"Invalid request: {e}")
    # Log comment details for debugging
    logger.error(f"Comment ID: {comment.id}, Body: {comment.body[:100]}")
    # Skip this comment and continue
    return None
```

**4. Network Errors (Retryable)**
```python
from anthropic import APIConnectionError, APITimeoutError

try:
    response = client.messages.create(...)
except (APIConnectionError, APITimeoutError) as e:
    logger.warning(f"Network error: {e}")
    # Automatic retry via @retry decorator
```

**5. Validation Errors (Non-Retryable)**
```python
from pydantic import ValidationError

try:
    extraction = TranslationExtraction(**tool_use.input)
except ValidationError as e:
    logger.error(f"Extraction validation failed: {e}")
    logger.error(f"LLM output: {tool_use.input}")
    # Skip this comment (LLM returned invalid data)
    return None
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Circuit breaker for LLM API calls."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            # Check if timeout has elapsed
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                logger.info("Circuit breaker: half-open (testing)")
            else:
                raise Exception("Circuit breaker: open (too many failures)")

        try:
            result = func(*args, **kwargs)
            # Success: reset failure count
            if self.state == "half-open":
                self.state = "closed"
                logger.info("Circuit breaker: closed (recovered)")
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker: open (failures: {self.failure_count})")

            raise e

# Usage
circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

def parse_comment_safe(comment: ReviewComment) -> TranslationExtraction | None:
    """Parse comment with circuit breaker protection."""
    try:
        return circuit_breaker.call(parse_comment_with_retry, comment.body, comment.file_path, comment.diff_hunk)
    except Exception as e:
        logger.error(f"Circuit breaker prevented call: {e}")
        return None
```

---

## Cost Optimization

### Pricing (as of 2025-10-24)

**Claude 3 Haiku Pricing**:
- **Input**: $0.25 per million tokens
- **Output**: $1.25 per million tokens

**Prompt Caching Pricing** (when enabled):
- **Cache Writes**: $0.30 per million tokens (1.2× input price)
- **Cache Reads**: $0.03 per million tokens (10× cheaper than input)

### Expected Costs

**Base Cost Calculation** (no caching):
```
6,000 requests/month (200 PRs × 30 days)
× 245 input tokens/request = 1,470,000 input tokens
× 78 output tokens/request = 468,000 output tokens

Input cost: 1.47M × $0.25 / 1M = $0.3675
Output cost: 0.468M × $1.25 / 1M = $0.585
Total: $0.95/month (base)
```

**With Prompt Caching** (35% cache hit rate):
```
Cache writes (first request): 6,000 × 0.35 = 2,100 requests
  → 2,100 × 200 tokens × $0.30 / 1M = $0.126

Cache reads (subsequent): 6,000 × 0.35 = 2,100 requests
  → 2,100 × 200 tokens × $0.03 / 1M = $0.0126

No cache (65%): 6,000 × 0.65 = 3,900 requests
  → 3,900 × 245 tokens × $0.25 / 1M = $0.239

Output (all): 6,000 × 78 × $1.25 / 1M = $0.585

Total with prompt caching: $0.96/month
```

**With Semantic Caching** (additional 30% reduction):
```
Semantic cache hits: 6,000 × 0.30 = 1,800 requests (no API call)
Remaining: 4,200 requests to API

Input cost: 4,200 × 245 × $0.25 / 1M = $0.257
Output cost: 4,200 × 78 × $1.25 / 1M = $0.409

Total with semantic caching: $0.67/month
```

**Optimized Cost**: ~$1.13/month (with both caching strategies, allowing for variability)

### Prompt Caching Implementation

```python
response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=500,
    system=[
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}  # Cache system prompt
        }
    ],
    messages=[{"role": "user", "content": user_message}],
    tools=[EXTRACTION_TOOL]
)

# Cached responses include usage breakdown
print(response.usage)
# {
#   "input_tokens": 45,          # Non-cached input
#   "cache_creation_input_tokens": 200,  # First request: cache write
#   "cache_read_input_tokens": 200,      # Subsequent: cache read
#   "output_tokens": 78
# }
```

**Caching Strategy**:
- **Cache**: System prompt (200 tokens, static across all requests)
- **Non-Cached**: User message with comment body, file path, diff (45-50 tokens per request)
- **Cache TTL**: 5 minutes (Anthropic default)
- **Expected Cache Hit Rate**: 35% (comments processed in batches within 5-minute window)

### Semantic Caching Implementation

```python
import redis
import hashlib

# Initialize Redis client (optional, for semantic caching)
redis_client = redis.Redis(host='redis', port=6379, decode_responses=False)

def get_cache_key(comment_body: str, file_path: str) -> str:
    """Generate cache key from comment content."""
    content = f"{file_path}|{comment_body}"
    return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"

def parse_with_semantic_cache(comment: ReviewComment) -> TranslationExtraction:
    """Parse comment with Redis-based semantic caching."""
    cache_key = get_cache_key(comment.body, comment.file_path)

    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        logger.info(f"Semantic cache hit for comment {comment.id}")
        return TranslationExtraction.model_validate_json(cached)

    # Cache miss: call LLM
    extraction = parse_comment_with_retry(comment.body, comment.file_path, comment.diff_hunk)

    # Store in cache (7-day TTL)
    redis_client.setex(
        cache_key,
        7 * 24 * 60 * 60,  # 7 days
        extraction.model_dump_json()
    )

    return extraction
```

**Semantic Cache Configuration**:
- **Storage**: Redis (redis:7-alpine Docker image)
- **TTL**: 7 days (covers weekly translation PR cycles)
- **Expected Hit Rate**: 20-40% (similar comments across PRs)
- **Cost Savings**: 30% reduction in API calls

---

## Performance Metrics

### Latency Expectations

**Claude 3 Haiku Performance**:
- **p50 Latency**: 1.4 seconds
- **p95 Latency**: 2.8 seconds
- **p99 Latency**: 4.2 seconds
- **Output Speed**: 127 tokens/second

**PR Guardian Use Case** (200 comments):
- **Sequential Processing**: 200 × 1.5s = 300 seconds (5 minutes)
- **Parallel (10 concurrent)**: 200 / 10 × 1.5s = 30 seconds
- **Within 30-minute window**: ✅ Comfortably achievable

### Token Usage Estimates

**Per Request**:
- **System Prompt**: 200 tokens (cached)
- **User Message**: 45-50 tokens
  - File path: ~10 tokens
  - Diff hunk: ~20 tokens
  - Comment body: ~15-20 tokens
- **Tool Definition**: Included in system prompt
- **Output**: ~78 tokens (structured JSON)

**Total per Request**: 245 input + 78 output = 323 tokens

**Monthly** (6,000 requests):
- **Input**: 1.47M tokens
- **Output**: 468K tokens
- **Total**: 1.94M tokens/month

---

## Validation and Quality Assurance

### Multi-Level Validation

**Level 1: Pydantic Schema Validation**
```python
class TranslationExtraction(BaseModel):
    """Structured extraction with automatic validation."""
    translation_key: str = Field(min_length=1)
    original_value: str = Field(min_length=1)
    new_value: str = Field(min_length=1)
    locale: str = Field(pattern=r'^[a-z]{2}_[A-Z]{2}$')
    reasoning: str = Field(min_length=10)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator('new_value')
    def values_must_differ(cls, v, values):
        """Ensure new value differs from original."""
        if 'original_value' in values and v == values['original_value']:
            raise ValueError("new_value must differ from original_value")
        return v
```

**Level 2: Placeholder Integrity Validation**
```python
import re

def extract_placeholders(text: str) -> set[str]:
    """Extract all placeholder patterns from text."""
    patterns = [
        r'\{[a-zA-Z0-9_]+\}',      # {variable}
        r'%[sd]',                   # %s, %d
        r'\{\{[a-zA-Z0-9_]+\}\}',  # {{key}}
        r'\$[a-zA-Z0-9_]+',         # $variable
        r'%\([a-zA-Z0-9_]+\)[sd]'   # %(name)s
    ]
    placeholders = set()
    for pattern in patterns:
        placeholders.update(re.findall(pattern, text))
    return placeholders

def validate_placeholder_integrity(extraction: TranslationExtraction) -> bool:
    """Ensure placeholders preserved between original and new values."""
    original_placeholders = extract_placeholders(extraction.original_value)
    new_placeholders = extract_placeholders(extraction.new_value)

    if original_placeholders != new_placeholders:
        logger.warning(f"Placeholder mismatch: {original_placeholders} != {new_placeholders}")
        return False

    return True
```

**Level 3: Confidence Threshold Validation**
```python
def validate_and_decide(extraction: TranslationExtraction) -> tuple[bool, str]:
    """Validate extraction and determine implementation decision."""
    # Pydantic validation already passed

    # Placeholder integrity check
    if not validate_placeholder_integrity(extraction):
        return False, "Placeholder integrity check failed"

    # Confidence-based decision
    if extraction.confidence >= 0.80:
        return True, "High confidence: auto-implement"
    elif extraction.confidence >= 0.60:
        return False, f"Medium confidence ({extraction.confidence:.2f}): flag for human review"
    else:
        return False, f"Low confidence ({extraction.confidence:.2f}): skip"
```

---

## Contract Summary

**Key Contracts**:
1. **Authentication**: API key required in `ANTHROPIC_API_KEY` environment variable
2. **Rate Limits**: 50 requests/minute, 40K tokens/minute (tier-dependent)
3. **Retry Logic**: 3 max attempts with exponential backoff (2s, 4s, 8s)
4. **Concurrency**: 5-10 concurrent requests maximum
5. **Error Handling**: Non-retryable errors (auth, validation) vs retryable (network, rate limit)
6. **Circuit Breaker**: 5-failure threshold with 60-second timeout
7. **Validation**: Multi-level (Pydantic, placeholder integrity, confidence thresholds)
8. **Cost**: $1.13-2.40/month for 6,000 requests (optimized with caching)
9. **Performance**: 1.4s p50 latency, 5x speedup with 10 concurrent requests

**Next Steps**: Update quickstart.md with Anthropic API key setup instructions and optional Redis deployment for semantic caching.
