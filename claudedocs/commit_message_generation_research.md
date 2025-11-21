# Automated Conventional Commit Message Generation Research
## Research Report for PR Guardian Translation Agent

**Date**: 2025-10-24
**Research Focus**: Automated commit message formatting following cbea.ms/git-commit seven rules
**Use Case**: Translation changes with review comment references in conventional format

---

## Executive Summary

This research provides algorithms, code patterns, and validation approaches for automated generation of commit messages that comply with both the seven rules from cbea.ms/git-commit and Conventional Commits specification for the PR Guardian translation agent use case.

### Decision: Hybrid Approach with Template-Based Generation

**Recommended**: Template-based commit message generation with algorithmic validation and formatting compliance checks.

**Rationale**:
- Full AI/LLM generation risks non-deterministic output and compliance failures
- Manual templates lack context awareness for translation-specific details
- Hybrid approach provides deterministic compliance with contextual flexibility
- Lower operational cost than LLM API calls for every commit
- Aligns with constitution requirement for GPG-signed, conventional commits

---

## The Seven Rules Implementation

### Rule 1: Separate Subject from Body with Blank Line

**Implementation**: Programmatic separation during commit message construction.

```python
def format_commit_message(subject: str, body: str) -> str:
    """
    Format commit message with proper subject/body separation.

    Args:
        subject: Commit subject line (will be validated)
        body: Commit body text (will be wrapped)

    Returns:
        Properly formatted commit message
    """
    if not body or body.strip() == "":
        return subject

    # Ensure exactly one blank line between subject and body
    return f"{subject}\n\n{body}"
```

**Algorithm**:
1. Accept subject and body as separate inputs
2. If body is empty/None, return subject only
3. Otherwise, join with exactly one blank line (`\n\n`)
4. Never allow subject to contain newlines

**Validation**:
```python
def validate_subject_body_separation(message: str) -> bool:
    """Validate subject/body are properly separated."""
    lines = message.split('\n')

    if len(lines) == 1:
        return True  # Subject-only commit is valid

    if len(lines) >= 2:
        # Second line MUST be blank
        return lines[1] == ""

    return False
```

---

### Rule 2: Limit Subject Line to 50 Characters (72 Hard Limit)

**Implementation**: Subject line truncation with meaningful preservation.

```python
def truncate_subject_line(subject: str, target: int = 50, hard_limit: int = 72) -> str:
    """
    Truncate subject line intelligently to target length.

    Strategy:
    1. If under target (50), return as-is
    2. If between target and hard limit, return with warning
    3. If over hard limit, truncate at word boundary before limit

    Args:
        subject: Original subject line
        target: Target length (default 50)
        hard_limit: Hard maximum (default 72)

    Returns:
        Truncated subject line
    """
    if len(subject) <= target:
        return subject

    if len(subject) <= hard_limit:
        # Between target and hard limit - acceptable but warn
        return subject

    # Must truncate - find last word boundary before hard limit
    truncated = subject[:hard_limit]

    # Find last space to avoid cutting mid-word
    last_space = truncated.rfind(' ')

    if last_space > target * 0.6:  # At least 60% of target preserved
        return truncated[:last_space]
    else:
        # No good word boundary, hard truncate at limit
        return truncated

# Translation-specific subject generation
def generate_translation_subject(
    change_type: str,
    locale: str,
    comment_type: str,
    target_length: int = 50
) -> str:
    """
    Generate subject line for translation commit.

    Format: "fix(i18n-{locale}): {change_type}"
    Example: "fix(i18n-ja): correct terminology in error messages"

    Args:
        change_type: Brief description of change
        locale: Language code (ja, de, fr, etc.)
        comment_type: Classification (critical, constructive, nitpick)
        target_length: Target subject length (default 50)

    Returns:
        Formatted subject line under target length
    """
    # Map comment types to conventional commit types
    type_mapping = {
        "critical": "fix",
        "constructive": "fix",
        "nitpick": "style",
        "question": "docs"
    }

    commit_type = type_mapping.get(comment_type.lower(), "fix")
    scope = f"i18n-{locale}"

    # Calculate prefix length: "fix(i18n-ja): " = ~15 chars
    prefix = f"{commit_type}({scope}): "
    available_length = target_length - len(prefix)

    # Truncate change description if needed
    if len(change_type) > available_length:
        change_type = change_type[:available_length - 3] + "..."

    return f"{prefix}{change_type}"
```

**Truncation Algorithm**:
1. **No truncation needed** (≤50 chars): Return original
2. **Warning zone** (50-72 chars): Return with warning flag
3. **Must truncate** (>72 chars):
   - Find last word boundary before char 72
   - If word boundary exists after char 30 (60% of 50), truncate there
   - Otherwise, hard truncate at char 72
   - Never truncate conventional commit prefix (type, scope)

**PR Guardian Specific Strategy**:
```python
def generate_pr_guardian_subject(
    locale: str,
    action: str,
    file_type: str = "translation",
    max_length: int = 50
) -> str:
    """
    Generate PR Guardian-specific subject lines.

    Examples:
    - "fix(i18n-ja): correct terminology consistency"
    - "style(i18n-de): standardize punctuation"
    - "fix(i18n-fr): preserve placeholder variables"

    Args:
        locale: Language code
        action: Action description (imperative mood)
        file_type: Type of file (default: translation)
        max_length: Maximum subject length

    Returns:
        Formatted subject line
    """
    prefix = f"fix(i18n-{locale}): "
    available = max_length - len(prefix)

    # Ensure action is in imperative mood
    action_imperative = ensure_imperative_mood(action)

    if len(action_imperative) > available:
        action_imperative = truncate_at_word_boundary(
            action_imperative,
            available - 3
        ) + "..."

    return f"{prefix}{action_imperative}"
```

---

### Rule 3: Capitalize the Subject Line

**Implementation**: Automatic capitalization enforcement.

```python
def capitalize_subject_line(subject: str) -> str:
    """
    Capitalize the first letter of subject line.

    Special handling:
    - Preserve conventional commit prefix (type(scope): remains lowercase)
    - Capitalize first letter after ": " separator
    - Don't capitalize if starting with backtick, code reference

    Args:
        subject: Original subject line

    Returns:
        Capitalized subject line
    """
    # Check for conventional commit format: type(scope): description
    if ':' in subject:
        prefix, description = subject.split(':', 1)
        description = description.lstrip()

        # Don't capitalize code references or special syntax
        if description and not description[0] in ['`', '{', '[', '<']:
            description = description[0].upper() + description[1:]

        return f"{prefix}: {description}"

    # No conventional prefix - capitalize first letter
    if subject and not subject[0] in ['`', '{', '[', '<']:
        return subject[0].upper() + subject[1:]

    return subject

# Example usage
assert capitalize_subject_line("fix(i18n-ja): add missing translation") == \
       "fix(i18n-ja): Add missing translation"
assert capitalize_subject_line("feat: new translation support") == \
       "feat: New translation support"
```

---

### Rule 4: Do Not End Subject Line with Period

**Implementation**: Period removal with validation.

```python
def remove_trailing_period(subject: str) -> str:
    """
    Remove trailing period from subject line.

    Args:
        subject: Original subject line

    Returns:
        Subject line without trailing period
    """
    return subject.rstrip('.')

def validate_no_trailing_period(subject: str) -> bool:
    """
    Validate subject line doesn't end with period.

    Args:
        subject: Subject line to validate

    Returns:
        True if no trailing period, False otherwise
    """
    return not subject.endswith('.')
```

---

### Rule 5: Use Imperative Mood in Subject Line

**Implementation**: Imperative mood detection and transformation.

```python
import re
from typing import Optional

# Common imperative verbs for translation work
IMPERATIVE_VERBS = {
    'add', 'fix', 'update', 'remove', 'correct', 'improve',
    'standardize', 'clarify', 'preserve', 'adjust', 'refine',
    'implement', 'ensure', 'maintain', 'apply', 'resolve'
}

# Past tense to imperative mapping
PAST_TO_IMPERATIVE = {
    'added': 'add',
    'fixed': 'fix',
    'updated': 'update',
    'removed': 'remove',
    'corrected': 'correct',
    'improved': 'improve',
    'standardized': 'standardize',
    'clarified': 'clarify',
    'preserved': 'preserve',
    'adjusted': 'adjust',
    'refined': 'refine',
    'implemented': 'implement',
    'ensured': 'ensure',
    'maintained': 'maintain',
    'applied': 'apply',
    'resolved': 'resolve'
}

# Present tense (third person) to imperative
PRESENT_TO_IMPERATIVE = {
    'adds': 'add',
    'fixes': 'fix',
    'updates': 'update',
    'removes': 'remove',
    'corrects': 'correct',
    'improves': 'improve',
    'standardizes': 'standardize',
    'clarifies': 'clarify',
    'preserves': 'preserve',
    'adjusts': 'adjust',
    'refines': 'refine',
    'implements': 'implement',
    'ensures': 'ensure',
    'maintains': 'maintain',
    'applies': 'apply',
    'resolves': 'resolve'
}

def ensure_imperative_mood(text: str) -> str:
    """
    Convert text to imperative mood.

    Strategy:
    1. Extract first word
    2. Check if already imperative
    3. Convert past/present tense to imperative
    4. Return original if no conversion possible

    Args:
        text: Original description text

    Returns:
        Text in imperative mood
    """
    words = text.split()
    if not words:
        return text

    first_word = words[0].lower()

    # Already imperative
    if first_word in IMPERATIVE_VERBS:
        return text

    # Convert past tense
    if first_word in PAST_TO_IMPERATIVE:
        words[0] = PAST_TO_IMPERATIVE[first_word].capitalize()
        return ' '.join(words)

    # Convert present tense
    if first_word in PRESENT_TO_IMPERATIVE:
        words[0] = PRESENT_TO_IMPERATIVE[first_word].capitalize()
        return ' '.join(words)

    # No conversion found - return original
    return text

def validate_imperative_mood(subject: str) -> tuple[bool, Optional[str]]:
    """
    Validate if subject line uses imperative mood.

    Simple heuristic:
    - Extract first verb after conventional commit prefix
    - Check if in imperative verb set
    - Check if NOT past tense (doesn't end in -ed)
    - Check if NOT present tense third person (doesn't end in -s)

    Args:
        subject: Subject line to validate

    Returns:
        Tuple of (is_valid, suggestion)
    """
    # Extract description after conventional prefix
    if ':' in subject:
        description = subject.split(':', 1)[1].strip()
    else:
        description = subject

    words = description.split()
    if not words:
        return True, None

    first_word = words[0].lower()

    # Check if imperative
    if first_word in IMPERATIVE_VERBS:
        return True, None

    # Check for past tense
    if first_word.endswith('ed') and first_word in PAST_TO_IMPERATIVE:
        suggestion = ensure_imperative_mood(description)
        return False, f"Use imperative mood: '{suggestion}'"

    # Check for present tense third person
    if first_word.endswith('s') and first_word in PRESENT_TO_IMPERATIVE:
        suggestion = ensure_imperative_mood(description)
        return False, f"Use imperative mood: '{suggestion}'"

    # Unable to determine - pass through
    return True, None

# Test with "If applied, this commit will..." check
def test_imperative_with_sentence(subject: str) -> bool:
    """
    Test if subject completes: "If applied, this commit will..."

    Args:
        subject: Subject line (without conventional prefix)

    Returns:
        True if grammatically correct completion
    """
    sentence = f"If applied, this commit will {subject}"
    # This is a heuristic test - real implementation would need NLP
    # For now, just check structure
    return not any([
        subject.lower().startswith('added'),
        subject.lower().startswith('fixed'),
        subject.lower().startswith('updated'),
    ])
```

**Imperative Mood Algorithm**:
1. **Extract first verb** from subject (after conventional commit prefix)
2. **Check imperative verb set** - if match, pass validation
3. **Detect past tense** - ends with '-ed', convert to imperative
4. **Detect present tense** - ends with '-s', convert to imperative
5. **Apply transformation** - replace first word with imperative form
6. **Validation test** - "If applied, this commit will [subject]" should be grammatical

**Limitations**:
- Rule-based approach covers common cases but not all edge cases
- For higher accuracy, would need POS tagging (spaCy, NLTK)
- PR Guardian can use predefined imperative templates to avoid detection complexity

---

### Rule 6: Wrap Body at 72 Characters

**Implementation**: Python `textwrap` module with paragraph preservation.

```python
import textwrap
from typing import List

def wrap_commit_body(body: str, width: int = 72) -> str:
    """
    Wrap commit message body at specified width while preserving structure.

    Strategy:
    1. Split body into paragraphs (double newline)
    2. Wrap each paragraph independently
    3. Preserve blank lines between paragraphs
    4. Preserve list formatting and special markers

    Args:
        body: Commit message body
        width: Maximum line width (default 72)

    Returns:
        Wrapped body text
    """
    if not body or body.strip() == "":
        return ""

    # Split into paragraphs
    paragraphs = body.split('\n\n')
    wrapped_paragraphs = []

    for para in paragraphs:
        if not para.strip():
            wrapped_paragraphs.append("")
            continue

        # Check if paragraph is a list or special formatting
        if para.lstrip().startswith(('- ', '* ', '1. ', '2. ')):
            # Preserve list formatting
            wrapped_para = wrap_list_items(para, width)
        else:
            # Normal paragraph wrapping
            wrapped_para = textwrap.fill(
                para,
                width=width,
                break_long_words=False,
                break_on_hyphens=False
            )

        wrapped_paragraphs.append(wrapped_para)

    return '\n\n'.join(wrapped_paragraphs)

def wrap_list_items(list_text: str, width: int = 72) -> str:
    """
    Wrap list items while preserving list formatting.

    Args:
        list_text: Text containing list items
        width: Maximum line width

    Returns:
        Wrapped list text with preserved markers
    """
    lines = list_text.split('\n')
    wrapped_lines = []

    for line in lines:
        if not line.strip():
            wrapped_lines.append("")
            continue

        # Detect list marker
        marker_match = re.match(r'^(\s*(?:-|\*|\d+\.)\s+)', line)
        if marker_match:
            marker = marker_match.group(1)
            content = line[len(marker):]
            indent = ' ' * len(marker)

            # Wrap content with hanging indent
            wrapper = textwrap.TextWrapper(
                width=width,
                initial_indent=marker,
                subsequent_indent=indent,
                break_long_words=False,
                break_on_hyphens=False
            )
            wrapped_lines.append(wrapper.fill(content))
        else:
            # Regular wrapping for non-list lines
            wrapped_lines.append(textwrap.fill(line, width=width))

    return '\n'.join(wrapped_lines)

# PR Guardian body generation
def generate_translation_body(
    comment_id: str,
    locale: str,
    change_description: str,
    reasoning: str,
    file_path: str,
    width: int = 72
) -> str:
    """
    Generate commit body for translation change.

    Format:
    Fix terminology consistency in Japanese error messages based on
    CodeRabbitAI review feedback. This change improves user experience
    by ensuring consistent terminology across the application.

    Context:
    - Locale: ja-JP
    - File: src/main/resources/messages_ja.properties
    - Review: coderabbitai#comment-123456

    Rationale:
    Original translation used inconsistent terms for "error" (エラー vs
    誤り). Standardized to エラー per project glossary.

    Args:
        comment_id: CodeRabbitAI comment ID
        locale: Language code
        change_description: What changed
        reasoning: Why it changed
        file_path: Translation file path
        width: Body wrap width

    Returns:
        Formatted and wrapped commit body
    """
    # Main description paragraph
    main_para = change_description

    # Context section
    context = f"""Context:
- Locale: {locale}
- File: {file_path}
- Review: coderabbitai#{comment_id}"""

    # Rationale section
    rationale = f"Rationale:\n{reasoning}"

    # Combine all sections
    body = f"{main_para}\n\n{context}\n\n{rationale}"

    # Wrap at 72 characters
    return wrap_commit_body(body, width)
```

**Wrapping Algorithm**:
1. **Split into paragraphs** - Preserve double-newline separators
2. **Identify special formatting** - Lists, code blocks, tables
3. **Wrap normal paragraphs** - Use `textwrap.fill()` with width=72
4. **Wrap lists with hanging indent** - Preserve list markers, indent continuations
5. **Preserve blank lines** - Maintain paragraph separation
6. **No hard line breaks** - `break_long_words=False` for URLs and paths

**Special Considerations**:
- URLs and file paths should not be wrapped mid-string
- List items maintain hanging indent (aligned with first line content)
- Code snippets or references preserved as-is

---

### Rule 7: Use Body to Explain What and Why, Not How

**Implementation**: Template-based body structure with guidance.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class CommitContext:
    """Context for commit body generation."""
    locale: str
    file_path: str
    comment_id: str
    comment_type: str
    original_text: Optional[str] = None
    new_text: Optional[str] = None

def generate_what_and_why_body(
    what: str,
    why: str,
    context: CommitContext,
    width: int = 72
) -> str:
    """
    Generate commit body focusing on what and why, not how.

    Structure:
    1. WHAT paragraph: High-level description of change
    2. Context section: Metadata (locale, file, review reference)
    3. WHY paragraph: Rationale and impact

    Args:
        what: What changed (user-facing impact)
        why: Why it changed (rationale)
        context: Commit context metadata
        width: Body wrap width

    Returns:
        Formatted commit body
    """
    # WHAT: User-facing change description
    what_para = what

    # Context metadata
    context_section = f"""Context:
- Locale: {context.locale}
- File: {context.file_path}
- Review: coderabbitai#{context.comment_id}
- Type: {context.comment_type}"""

    # WHY: Rationale and impact
    why_para = f"Rationale:\n{why}"

    # Optionally include before/after for clarity
    if context.original_text and context.new_text:
        change_detail = f"""Change:
- Before: {context.original_text}
- After: {context.new_text}"""
        body = f"{what_para}\n\n{context_section}\n\n{why_para}\n\n{change_detail}"
    else:
        body = f"{what_para}\n\n{context_section}\n\n{why_para}"

    return wrap_commit_body(body, width)

# Translation-specific body templates
TRANSLATION_BODY_TEMPLATES = {
    "terminology": """Improve terminology consistency in {locale} translations. This
standardization ensures users encounter consistent vocabulary across
the application interface, reducing confusion and improving UX.

Context:
- Locale: {locale}
- File: {file_path}
- Review: coderabbitai#{comment_id}

Rationale:
{reasoning}""",

    "grammar": """Fix grammatical error in {locale} translations. Correct grammar
improves professionalism and user trust in the application.

Context:
- Locale: {locale}
- File: {file_path}
- Review: coderabbitai#{comment_id}

Rationale:
{reasoning}""",

    "placeholder": """Preserve placeholder variable integrity in {locale} translations.
Placeholder variables enable dynamic content rendering and must be
maintained exactly to prevent runtime errors.

Context:
- Locale: {locale}
- File: {file_path}
- Review: coderabbitai#{comment_id}

Rationale:
{reasoning}""",

    "cultural": """Adapt {locale} translation for cultural appropriateness. Cultural
localization improves user acceptance and demonstrates respect for
regional norms and expectations.

Context:
- Locale: {locale}
- File: {file_path}
- Review: coderabbitai#{comment_id}

Rationale:
{reasoning}"""
}

def generate_body_from_template(
    template_type: str,
    locale: str,
    file_path: str,
    comment_id: str,
    reasoning: str
) -> str:
    """
    Generate commit body from template.

    Args:
        template_type: Type of change (terminology, grammar, etc.)
        locale: Language code
        file_path: Translation file path
        comment_id: Review comment ID
        reasoning: Specific reasoning for this change

    Returns:
        Formatted commit body
    """
    template = TRANSLATION_BODY_TEMPLATES.get(template_type, TRANSLATION_BODY_TEMPLATES["terminology"])

    body = template.format(
        locale=locale,
        file_path=file_path,
        comment_id=comment_id,
        reasoning=reasoning
    )

    return wrap_commit_body(body, width=72)
```

**What vs Why vs How**:
- **WHAT** (Include): "Fix terminology consistency", "Improve cultural adaptation"
- **WHY** (Include): "Ensures consistent UX", "Improves user trust", "Prevents confusion"
- **HOW** (Exclude): "Changed line 45 from X to Y", "Used find-and-replace", "Modified string literal"

**Template Strategy for PR Guardian**:
- Predefined templates for common translation change types
- Template fills in: what changed (terminology/grammar/placeholder) and why (UX/trust/functionality)
- Reasoning field captures specific details from CodeRabbitAI comment
- Context section provides traceability without cluttering explanation

---

## Conventional Commit Prefix Mapping

### Translation-Specific Type Selection

```python
from enum import Enum

class ConventionalType(Enum):
    """Conventional commit types for translations."""
    FIX = "fix"           # Critical issues, functional problems
    STYLE = "style"       # Formatting, punctuation, minor adjustments
    DOCS = "docs"         # Documentation-only changes
    REFACTOR = "refactor" # Terminology standardization
    REVERT = "revert"     # Rollback previous translation

def classify_translation_change(
    comment_classification: str,
    change_nature: str
) -> ConventionalType:
    """
    Map translation change to conventional commit type.

    Mapping rules:
    - Critical issues → fix
    - Placeholder problems → fix
    - Terminology consistency → fix or refactor
    - Grammar corrections → fix
    - Punctuation only → style
    - Cultural adaptation → fix
    - Nitpick formatting → style

    Args:
        comment_classification: Classification from constitution
        change_nature: Nature of the change

    Returns:
        Appropriate conventional commit type
    """
    # Critical always maps to fix
    if comment_classification.lower() == "critical":
        return ConventionalType.FIX

    # Check change nature
    nature_lower = change_nature.lower()

    if any(term in nature_lower for term in ['placeholder', 'variable', 'error', 'broken']):
        return ConventionalType.FIX

    if any(term in nature_lower for term in ['terminology', 'consistency', 'grammar']):
        return ConventionalType.FIX

    if any(term in nature_lower for term in ['punctuation', 'formatting', 'spacing']):
        return ConventionalType.STYLE

    if 'cultural' in nature_lower or 'adaptation' in nature_lower:
        return ConventionalType.FIX

    # Default to fix for constructive improvements
    if comment_classification.lower() == "constructive":
        return ConventionalType.FIX

    # Nitpicks default to style
    return ConventionalType.STYLE
```

**PR Guardian Type Mapping**:
```
Critical Translation Issues → fix(i18n-{locale})
Constructive Improvements → fix(i18n-{locale})  [functional impact]
Constructive Improvements → refactor(i18n-{locale})  [terminology only]
Translation Nitpicks → style(i18n-{locale})
```

**Scope Format**: `i18n-{locale}` where locale is ISO language code (ja, de, fr, en, etc.)

---

## Complete Generation Algorithm

### End-to-End Commit Message Generation

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class TranslationChange:
    """Represents a translation change from CodeRabbitAI feedback."""
    locale: str
    file_path: str
    comment_id: str
    comment_classification: str
    change_nature: str
    short_description: str
    detailed_reasoning: str
    original_text: Optional[str] = None
    new_text: Optional[str] = None

def generate_conventional_commit_message(
    change: TranslationChange,
    max_subject_length: int = 50,
    body_width: int = 72
) -> str:
    """
    Generate complete conventional commit message for translation change.

    Follows seven rules:
    1. Subject/body separation with blank line
    2. Subject limited to 50 chars (72 hard limit)
    3. Subject capitalized
    4. No trailing period on subject
    5. Subject in imperative mood
    6. Body wrapped at 72 characters
    7. Body explains what and why, not how

    Args:
        change: Translation change details
        max_subject_length: Target subject length (default 50)
        body_width: Body wrap width (default 72)

    Returns:
        Complete formatted commit message
    """
    # Step 1: Determine conventional commit type
    commit_type = classify_translation_change(
        change.comment_classification,
        change.change_nature
    )

    # Step 2: Generate subject line
    subject = generate_subject_line(
        commit_type=commit_type.value,
        locale=change.locale,
        description=change.short_description,
        max_length=max_subject_length
    )

    # Step 3: Generate body
    body = generate_translation_body_structured(
        change=change,
        width=body_width
    )

    # Step 4: Combine with proper formatting
    message = format_commit_message(subject, body)

    # Step 5: Validate against seven rules
    validation_errors = validate_commit_message(message)
    if validation_errors:
        raise ValueError(f"Commit message validation failed: {validation_errors}")

    return message

def generate_subject_line(
    commit_type: str,
    locale: str,
    description: str,
    max_length: int = 50
) -> str:
    """
    Generate subject line following all rules.

    Args:
        commit_type: Conventional commit type (fix, style, etc.)
        locale: Language code
        description: Change description
        max_length: Maximum subject length

    Returns:
        Formatted subject line
    """
    # Ensure imperative mood
    description = ensure_imperative_mood(description)

    # Build prefix
    scope = f"i18n-{locale}"
    prefix = f"{commit_type}({scope}): "

    # Calculate available space
    available = max_length - len(prefix)

    # Truncate description if needed
    if len(description) > available:
        description = truncate_at_word_boundary(description, available - 3) + "..."

    # Capitalize first letter of description
    if description and description[0].isalpha():
        description = description[0].upper() + description[1:]

    # Remove trailing period
    description = description.rstrip('.')

    subject = f"{prefix}{description}"

    return subject

def generate_translation_body_structured(
    change: TranslationChange,
    width: int = 72
) -> str:
    """
    Generate structured body for translation commit.

    Args:
        change: Translation change details
        width: Body wrap width

    Returns:
        Formatted body text
    """
    # WHAT: High-level description
    what = f"Improve {change.change_nature.lower()} in {change.locale} translations based on CodeRabbitAI review feedback."

    # Context section
    context = f"""Context:
- Locale: {change.locale}
- File: {change.file_path}
- Review: coderabbitai#{change.comment_id}
- Classification: {change.comment_classification}"""

    # WHY: Rationale
    why = f"Rationale:\n{change.detailed_reasoning}"

    # Optional: Before/After
    if change.original_text and change.new_text:
        before_after = f"""Change Details:
- Before: {change.original_text}
- After: {change.new_text}"""
        body = f"{what}\n\n{context}\n\n{why}\n\n{before_after}"
    else:
        body = f"{what}\n\n{context}\n\n{why}"

    # Wrap at specified width
    return wrap_commit_body(body, width)

def truncate_at_word_boundary(text: str, max_length: int) -> str:
    """
    Truncate text at word boundary.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    last_space = truncated.rfind(' ')

    if last_space > max_length * 0.6:
        return truncated[:last_space]
    else:
        return truncated
```

---

## Validation Algorithm

### Seven Rules Compliance Checker

```python
from typing import List, Tuple

def validate_commit_message(message: str) -> List[str]:
    """
    Validate commit message against seven rules.

    Args:
        message: Complete commit message

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    lines = message.split('\n')

    if not lines:
        errors.append("Empty commit message")
        return errors

    subject = lines[0]

    # Rule 1: Subject/body separation
    if len(lines) > 1 and lines[1] != "":
        errors.append("Rule 1: Subject must be separated from body by blank line")

    # Rule 2: Subject length
    if len(subject) > 72:
        errors.append(f"Rule 2: Subject exceeds 72 characters ({len(subject)} chars)")
    elif len(subject) > 50:
        # Warning, not error
        pass  # Could log warning

    # Rule 3: Capitalization
    # Extract description after conventional prefix
    if ':' in subject:
        description = subject.split(':', 1)[1].strip()
    else:
        description = subject

    if description and description[0].isalpha() and not description[0].isupper():
        errors.append(f"Rule 3: Subject should be capitalized: '{description}'")

    # Rule 4: No trailing period
    if subject.endswith('.'):
        errors.append("Rule 4: Subject should not end with period")

    # Rule 5: Imperative mood
    is_imperative, suggestion = validate_imperative_mood(subject)
    if not is_imperative and suggestion:
        errors.append(f"Rule 5: {suggestion}")

    # Rule 6: Body wrap
    if len(lines) > 2:
        body_lines = lines[2:]
        for i, line in enumerate(body_lines, start=3):
            if len(line) > 72 and not line.lstrip().startswith(('http://', 'https://')):
                errors.append(f"Rule 6: Body line {i} exceeds 72 characters ({len(line)} chars)")

    # Rule 7: What and why (heuristic check)
    # This is harder to validate programmatically - use template enforcement

    return errors

def validate_and_fix_commit_message(message: str) -> Tuple[str, List[str]]:
    """
    Validate and auto-fix commit message where possible.

    Args:
        message: Original commit message

    Returns:
        Tuple of (fixed_message, remaining_errors)
    """
    lines = message.split('\n')
    subject = lines[0]
    body = '\n'.join(lines[2:]) if len(lines) > 2 else ""

    # Fix Rule 3: Capitalize
    subject = capitalize_subject_line(subject)

    # Fix Rule 4: Remove trailing period
    subject = remove_trailing_period(subject)

    # Fix Rule 5: Convert to imperative (best effort)
    if ':' in subject:
        prefix, description = subject.split(':', 1)
        description = description.strip()
        description = ensure_imperative_mood(description)
        subject = f"{prefix}: {description}"

    # Fix Rule 6: Wrap body
    if body:
        body = wrap_commit_body(body, width=72)

    # Reconstruct message
    fixed_message = format_commit_message(subject, body)

    # Validate fixed message
    remaining_errors = validate_commit_message(fixed_message)

    return fixed_message, remaining_errors
```

---

## Testing Strategy

### Unit Tests for Each Rule

```python
import unittest

class TestCommitMessageGeneration(unittest.TestCase):
    """Test suite for commit message generation."""

    def test_rule1_subject_body_separation(self):
        """Test Rule 1: Blank line separation."""
        subject = "fix(i18n-ja): correct terminology"
        body = "This fixes terminology consistency."

        message = format_commit_message(subject, body)
        lines = message.split('\n')

        self.assertEqual(lines[0], subject)
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[2], body)

    def test_rule2_subject_length(self):
        """Test Rule 2: Subject length limit."""
        long_description = "this is a very long description that exceeds fifty characters and needs truncation"

        subject = generate_subject_line(
            commit_type="fix",
            locale="ja",
            description=long_description,
            max_length=50
        )

        self.assertLessEqual(len(subject), 72)
        self.assertIn("fix(i18n-ja):", subject)

    def test_rule3_capitalization(self):
        """Test Rule 3: Subject capitalization."""
        subject = "fix(i18n-ja): add missing translation"
        capitalized = capitalize_subject_line(subject)

        self.assertEqual(capitalized, "fix(i18n-ja): Add missing translation")

    def test_rule4_no_trailing_period(self):
        """Test Rule 4: No trailing period."""
        subject_with_period = "fix(i18n-ja): Add translation."
        cleaned = remove_trailing_period(subject_with_period)

        self.assertEqual(cleaned, "fix(i18n-ja): Add translation")
        self.assertFalse(validate_no_trailing_period(subject_with_period))

    def test_rule5_imperative_mood(self):
        """Test Rule 5: Imperative mood."""
        past_tense = "Added new translation"
        imperative = ensure_imperative_mood(past_tense)

        self.assertEqual(imperative, "Add new translation")

        present_tense = "Adds new translation"
        imperative = ensure_imperative_mood(present_tense)

        self.assertEqual(imperative, "Add new translation")

    def test_rule6_body_wrapping(self):
        """Test Rule 6: Body wrap at 72 characters."""
        long_paragraph = "This is a very long paragraph that definitely exceeds seventy-two characters and needs to be wrapped properly to comply with conventional commit standards."

        wrapped = wrap_commit_body(long_paragraph, width=72)
        lines = wrapped.split('\n')

        for line in lines:
            self.assertLessEqual(len(line), 72)

    def test_rule7_what_and_why(self):
        """Test Rule 7: Body structure."""
        context = CommitContext(
            locale="ja-JP",
            file_path="messages_ja.properties",
            comment_id="12345",
            comment_type="constructive"
        )

        body = generate_what_and_why_body(
            what="Improve terminology consistency",
            why="Ensures consistent user experience",
            context=context
        )

        self.assertIn("terminology consistency", body.lower())
        self.assertIn("user experience", body.lower())
        self.assertIn("Locale:", body)
        self.assertIn("Review:", body)

    def test_complete_message_generation(self):
        """Test end-to-end message generation."""
        change = TranslationChange(
            locale="ja",
            file_path="src/main/resources/messages_ja.properties",
            comment_id="123456",
            comment_classification="Constructive",
            change_nature="terminology consistency",
            short_description="standardize error terminology",
            detailed_reasoning="Original used inconsistent terms. Standardized per glossary.",
            original_text="誤り",
            new_text="エラー"
        )

        message = generate_conventional_commit_message(change)

        # Validate all seven rules
        errors = validate_commit_message(message)
        self.assertEqual(errors, [], f"Validation errors: {errors}")

        # Check structure
        self.assertIn("fix(i18n-ja):", message)
        self.assertIn("Context:", message)
        self.assertIn("Rationale:", message)

if __name__ == "__main__":
    unittest.main()
```

---

## Recommended Libraries

### Python Libraries for Implementation

1. **textwrap** (Built-in)
   - Purpose: Body wrapping at 72 characters
   - Usage: `textwrap.fill()`, `textwrap.wrap()`
   - Pros: No external dependencies, well-tested

2. **GitPython**
   - Purpose: Git operations and commit creation
   - Install: `pip install GitPython`
   - Usage: Repository manipulation, commit signing
   ```python
   from git import Repo

   repo = Repo('/path/to/repo')
   repo.git.commit('-S', '-m', message)
   ```

3. **python-dotenv**
   - Purpose: Configuration management
   - Install: `pip install python-dotenv`
   - Usage: Load environment variables

4. **PyGithub**
   - Purpose: GitHub API integration
   - Install: `pip install PyGithub`
   - Usage: Fetch PRs, comments, create issues

5. **pyyaml** / **python-properties** / **json** (Built-in)
   - Purpose: Translation file parsing
   - Usage: Validate file syntax after changes

6. **commitizen** (Optional - for reference)
   - Purpose: Study existing conventional commit implementation
   - Install: `pip install commitizen`
   - Note: May be heavyweight for PR Guardian needs

---

## PR Guardian Implementation Recommendations

### Recommended Approach: Template-Based Generation

```python
class CommitMessageGenerator:
    """Generate conventional commit messages for PR Guardian."""

    def __init__(self):
        self.max_subject_length = 50
        self.body_width = 72

    def generate_for_translation_change(
        self,
        locale: str,
        file_path: str,
        comment_id: str,
        classification: str,
        description: str,
        reasoning: str
    ) -> str:
        """
        Generate commit message for translation change.

        This is the main entry point for PR Guardian agent.
        """
        # Create change object
        change = TranslationChange(
            locale=locale,
            file_path=file_path,
            comment_id=comment_id,
            comment_classification=classification,
            change_nature=self._extract_change_nature(description),
            short_description=description,
            detailed_reasoning=reasoning
        )

        # Generate message
        message = generate_conventional_commit_message(
            change,
            max_subject_length=self.max_subject_length,
            body_width=self.body_width
        )

        # Final validation
        errors = validate_commit_message(message)
        if errors:
            # Attempt auto-fix
            message, remaining = validate_and_fix_commit_message(message)
            if remaining:
                raise ValueError(f"Cannot generate valid commit message: {remaining}")

        return message

    def _extract_change_nature(self, description: str) -> str:
        """Extract nature of change from description."""
        keywords = {
            "terminology": ["terminology", "term", "vocabulary", "wording"],
            "grammar": ["grammar", "grammatical", "syntax"],
            "placeholder": ["placeholder", "variable", "{", "}"],
            "cultural": ["cultural", "localization", "regional"],
            "punctuation": ["punctuation", "comma", "period", "formatting"]
        }

        desc_lower = description.lower()
        for nature, terms in keywords.items():
            if any(term in desc_lower for term in terms):
                return nature

        return "translation quality"
```

### Integration with Git Signing

```python
import subprocess
from typing import Optional

def create_signed_commit(
    repo_path: str,
    message: str,
    gpg_key_id: Optional[str] = None
) -> str:
    """
    Create GPG-signed commit with generated message.

    Args:
        repo_path: Path to git repository
        message: Formatted commit message
        gpg_key_id: Optional GPG key ID

    Returns:
        Commit hash

    Raises:
        ValueError: If commit signing fails
    """
    # Write message to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(message)
        message_file = f.name

    try:
        # Stage changes (assumed to be done already)

        # Create signed commit
        cmd = ['git', 'commit', '-S', '--file', message_file]
        if gpg_key_id:
            cmd.extend(['--gpg-sign', gpg_key_id])

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise ValueError(f"Commit signing failed: {result.stderr}")

        # Get commit hash
        hash_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        commit_hash = hash_result.stdout.strip()

        # Verify signature
        verify_result = subprocess.run(
            ['git', 'verify-commit', commit_hash],
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        if verify_result.returncode != 0:
            raise ValueError(f"Commit signature verification failed: {verify_result.stderr}")

        return commit_hash

    finally:
        import os
        os.unlink(message_file)
```

---

## Alternatives Considered

### Alternative 1: Full LLM Generation

**Approach**: Use OpenAI/Claude API to generate commit messages from diff context.

**Pros**:
- Natural language quality
- Contextual awareness
- Minimal rule programming

**Cons**:
- Non-deterministic output (compliance not guaranteed)
- API costs for every commit
- Latency (network calls)
- Requires additional validation layer
- Potential for hallucination or incorrect formatting

**Verdict**: ❌ Not recommended for PR Guardian due to non-negotiable compliance requirements

### Alternative 2: Pure Manual Templates

**Approach**: Hardcoded templates with variable substitution only.

**Pros**:
- 100% deterministic
- No validation needed
- Fast execution
- Zero external dependencies

**Cons**:
- Limited flexibility
- Requires many templates for different scenarios
- Cannot adapt to context variations
- May produce generic, less informative messages

**Verdict**: ⚠️ Acceptable fallback, but lacks quality of algorithmic approach

### Alternative 3: Commitizen Library Integration

**Approach**: Use existing commitizen library for message generation.

**Pros**:
- Battle-tested implementation
- Built-in conventional commits support
- Community-maintained

**Cons**:
- Interactive by design (requires automation adaptation)
- Heavyweight dependency
- Not optimized for automated agent use case
- May not fit translation-specific requirements

**Verdict**: ⚠️ Good for inspiration, but direct use not ideal for automation

---

## Implementation Notes

### Phase 1: Core Algorithm Implementation
1. Implement seven-rule validation functions
2. Create subject line generation with imperative mood
3. Implement body wrapping algorithm
4. Build translation-specific templates

### Phase 2: Integration with PR Guardian
1. Extract CodeRabbitAI comment details
2. Classify comment type (critical, constructive, nitpick)
3. Map to conventional commit type
4. Generate message with context
5. Validate before commit creation

### Phase 3: Git Signing Integration
1. Verify GPG configuration at startup
2. Create signed commits with generated messages
3. Verify signatures before push
4. Handle signing failures gracefully

### Phase 4: Testing and Validation
1. Unit tests for each rule
2. Integration tests with real translation files
3. End-to-end tests with GitHub PRs
4. Edge case handling (long descriptions, special characters)

---

## Sample Output Examples

### Example 1: Critical Translation Issue

```
fix(i18n-ja): preserve placeholder variables in error

Restore placeholder variable integrity in Japanese error messages
based on CodeRabbitAI critical issue feedback. Placeholder variables
are essential for dynamic content rendering and must be maintained.

Context:
- Locale: ja-JP
- File: src/main/resources/messages_ja.properties
- Review: coderabbitai#789012
- Classification: Critical

Rationale:
Original translation incorrectly removed {username} placeholder
variable, breaking runtime message formatting. Restored placeholder
to maintain functionality.

Change Details:
- Before: ユーザーが見つかりません
- After: ユーザー {username} が見つかりません
```

### Example 2: Constructive Terminology

```
fix(i18n-de): standardize terminology for consistency

Improve terminology consistency in German translations based on
CodeRabbitAI review feedback. Standardized terminology reduces user
confusion and improves overall product professionalism.

Context:
- Locale: de-DE
- File: client/locales/de/common.json
- Review: coderabbitai#345678
- Classification: Constructive

Rationale:
Original translation used inconsistent terms for "settings"
(Einstellungen vs Konfiguration). Standardized to Einstellungen per
project translation glossary.
```

### Example 3: Nitpick Formatting

```
style(i18n-fr): standardize punctuation formatting

Adjust punctuation formatting in French translations for consistency.
This standardization improves visual consistency across the
application interface.

Context:
- Locale: fr-FR
- File: public/translations/fr.yml
- Review: coderabbitai#901234
- Classification: Nitpick

Rationale:
Added non-breaking space before colon per French typography rules.
This follows established localization best practices for French.
```

---

## Conclusion

### Recommended Decision

**Adopt template-based commit message generation with algorithmic validation** for PR Guardian agent.

### Key Implementation Points

1. **Seven Rules Compliance**: Implement validation for all seven rules with auto-fix where possible
2. **Imperative Mood**: Use predefined verb mapping for common translation actions
3. **Subject Truncation**: Intelligent word-boundary truncation preserving conventional prefix
4. **Body Wrapping**: Python `textwrap` with paragraph and list preservation
5. **What/Why Focus**: Template-based body structure emphasizing impact over mechanics
6. **Conventional Types**: Map translation classifications to `fix`, `style`, `refactor`
7. **Scope Format**: Use `i18n-{locale}` for all translation commits

### Benefits

- **Deterministic**: Always produces compliant messages
- **Traceable**: Includes CodeRabbitAI comment references
- **Readable**: Follows established conventions
- **Maintainable**: Template-based with clear structure
- **Testable**: Each rule independently validatable
- **Efficient**: No external API calls, fast execution

### Next Steps

1. Implement validation and generation functions
2. Create translation-specific templates
3. Integrate with Git signing workflow
4. Build comprehensive test suite
5. Document edge cases and limitations
