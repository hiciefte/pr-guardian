# PR Guardian Translation Constitution

## Core Principles

### I. Translation Quality First (NON-NEGOTIABLE)
All translation changes must maintain linguistic accuracy, cultural appropriateness, and consistency with existing translations; Every review comment from CodeRabbitAI, including nitpicks, should be evaluated as they often contain legitimate improvements in translation quality, terminology consistency, or localization best practices; Translation corrections take priority over code-focused review patterns; Context preservation across all language variants is mandatory.

### II. Conventional Commit Standards (NON-NEGOTIABLE)
All commits must follow the seven rules of great git commit messages as defined by cbeams.me/git-commit:
1. Separate subject from body with blank line
2. Limit subject line to 50 characters (72 hard limit)
3. Capitalize the subject line
4. Do not end subject line with a period
5. Use imperative mood ("Add translation" not "Added translation")
6. Wrap body at 72 characters
7. Explain what and why, not how

Commits must complete the sentence: "If applied, this commit will [your subject line]"; All commits must be GPG signed before pushing to remote repository.

### III. Translation-Only Scope
PR Guardian operates exclusively on translation file changes (.properties, .json, .yml, etc.); No code modifications, build configurations, or infrastructure changes are permitted; Translation automation tools (Transifex, OpenAI, etc.) are acknowledged and respected; Manual translation edits follow established repository translation pipelines.

### IV. Nitpick Implementation for Translations
Unlike code reviews where nitpicks are optional, translation nitpicks often contain valuable improvements:
- Terminology consistency corrections
- Cultural localization improvements
- Grammar and syntax refinements
- Punctuation and formatting standardization
- Translation tone and formality adjustments

All translation nitpicks are classified as "Constructive Suggestions" and implemented unless clearly subjective or contradicting established glossaries.

### V. Incremental and Reversible Changes
Each translation improvement is committed atomically with descriptive messages; Changes reference the original review comment ID; All commits are reversible through git history; Implementation progress tracked with status updates on original PR; Failed implementations trigger rollback and error reporting; Signed commits ensure authenticity and non-repudiation.

## Translation Classification Framework

### Critical Translation Issues (MUST IMPLEMENT)
**Criteria**: Incorrect terminology breaking functionality (UI labels, error messages, action buttons); Cultural inappropriateness or offensive content; Placeholder variable mishandling (e.g., `{user}` broken); Missing translations causing fallback to source language; Character encoding issues or special character corruption.

**Action**: Implement immediately with highest priority; Verify across all affected language files; Update translation glossary if new term patterns emerge; Commit with reference to review comment.

### Constructive Translation Improvements (SHOULD IMPLEMENT)
**Criteria**: Terminology consistency across translations; Grammar and syntax improvements; Punctuation standardization; Translation tone adjustments (formal/informal); Localization enhancements (date formats, number formats, currency); Contextual clarity improvements.

**Action**: Implement as these improve translation quality; Evaluate consistency impact across language variants; Apply to all relevant language files simultaneously; Document reasoning in commit body.

### Translation Nitpicks (IMPLEMENT UNLESS SUBJECTIVE)
**Criteria**: Minor phrasing improvements; Alternative word choices within correct range; Formatting preferences (spacing, capitalization styles); Stylistic consistency adjustments; Regional dialect preferences.

**Action**: Implement by default as translation quality benefits; Skip only if contradicts established glossary or style guide; Log decision with reasoning; Acknowledge in PR comment with implementation status.

### Translation Questions (RESPOND AND CLARIFY)
**Criteria**: Clarification about translation context; Source language ambiguity; Cultural adaptation queries; Technical term interpretation requests.

**Action**: Provide detailed explanation in response comment; Consult translation glossary or style guide; Update documentation if question reveals gap; No code changes unless clarification reveals error.

### Translation Praise (ACKNOWLEDGE ONLY)
**Criteria**: Positive feedback on translation quality; Approval of terminology choices; Recognition of localization efforts.

**Action**: Acknowledge for team morale; No implementation required; Track for quality metrics.

## Quality Gates

### Pre-Implementation Validation
All translation comments classified with confidence ≥ 70%; Critical issues have clear functional impact on user experience; Changes maintain placeholder variable integrity; Terminology validated against translation glossary; Style guide compliance verified; Git branch clean with no uncommitted changes.

### Implementation Standards
Each translation change is atomic and isolated; Commit messages follow seven conventional commit rules; Subject line uses imperative mood and stays under 50 chars; Body wraps at 72 characters and explains why; All commits GPG signed before push; Signature verification passes: `git verify-commit HEAD`; Changes preserve translation key structure; No new encoding or formatting errors introduced.

### Post-Implementation Verification
All translation files parse correctly (valid properties/JSON/YAML); Placeholder variables intact (regex validation); Consistent changes applied across language variants; GPG commit signatures verified; Implementation status comment posted to PR; Validation log saved to `claudedocs/pr_guardian_i18n_{pr_number}_{timestamp}.md`; No manual intervention required for successful implementations.

## Commit Signing Requirements

### GPG Configuration
Git configured with user signing key: `git config user.signingkey [KEY_ID]`; Signing enabled globally or per-repository: `git config commit.gpgsign true`; Public key added to GitHub account for verification; Key not expired or revoked.

### Signing Workflow
Every commit signed with `-S` flag: `git commit -S -m "message"`; Verify signature before push: `git log --show-signature -1`; Push only after signature verification succeeds; Unsigned commits rejected by pre-push validation.

### Signature Verification
GitHub displays "Verified" badge on signed commits; Local verification: `git verify-commit <commit-hash>`; GPG key matches committer email in GitHub account; Signature created with non-expired key.

## Translation-Specific Safety

### Translation File Boundaries
Changes limited to files matching patterns: `*.properties`, `**/i18n/**/*.json`, `**/locales/**/*.yml`, `**/lang/**/*`; No modifications to base/source language configuration files; No changes to translation automation scripts; Respect repository's established translation pipeline.

### Placeholder Integrity
Validate placeholder variables before commit: `{variable}`, `%s`, `{{key}}`, `$variable`; Regex patterns for common placeholder formats; Reject changes breaking placeholder syntax; Test placeholder rendering if tooling available.

### Cross-Locale Consistency
When implementing terminology changes, scan all language files for consistency; Apply equivalent improvements to all language variants; Document locale-specific exceptions; Maintain translation key structure across all files.

### Glossary and Style Guide Compliance
Reference project translation glossary if available; Follow established terminology preferences; Respect formal/informal tone guidelines; Adhere to punctuation and formatting conventions; Escalate glossary conflicts to human review.

## Security and Safety

### Authentication and Authorization
GitHub token stored securely (environment variable, secrets manager); Required scopes: `repo`, `write:discussion`; GPG private key secured and passphrase-protected; No token or key exposure in logs, commits, or error messages; Token and key rotation supported without code changes.

### Safe Implementation Boundaries
No destructive operations (force push, branch deletion, PR auto-merge); No changes outside translation file paths; Rollback capability for all implementations; Human review required for: glossary conflicts, cultural sensitivity concerns, large-scale terminology changes, automated translation pipeline modifications.

### Error Handling and Recovery
All GitHub API calls retry with exponential backoff; Network failures logged and reported without terminating workflow; Implementation failures rollback changes and report error; Validation failures skip implementation and log reasoning; Rate limit handling respects GitHub API quotas; GPG signing failures abort commit and report configuration issue.

## Governance

This constitution supersedes all implementation decisions for translation PRs; Amendments require documentation, approval, and migration plan; All PR operations must verify compliance with core principles; Translation quality takes precedence over code review conventions; Commit signing is non-negotiable for all changes;

**Version**: 2.0.0 | **Ratified**: 2025-10-24 | **Last Amended**: 2025-10-24
