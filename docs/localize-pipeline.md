# Localize Pipeline Integration

PR Guardian is configured with a Java `.properties` suffix layout under
`src/main/resources`.

## Files

- `messages.properties` is the English source bundle.
- `messages_de.properties`, `messages_es.properties`, and
  `messages_fr.properties` are partially translated target bundles.
- `config.yaml` configures Localize Pipeline for the three target locales.
- `glossary.json` contains project-specific term guidance.
- `.github/workflows/translate.yml` runs the pipeline from GitHub Actions.

The workflow includes a small OpenAI `/v1/models` connectivity probe before the
translation action. This keeps missing secrets or hosted-runner network issues
separate from translation failures in the action logs.

## First Run

The workflow is pinned to `bisq-network/localize-pipeline@v0.1.1`. It runs
with `process-all-files: true` for the initial backfill and opens a translation
pull request from `localize/pr-guardian-ai-translations`.

After the first translation PR is reviewed and merged, change the workflow to
run on the default branch and remove `process-all-files: true` for normal
incremental translation updates.

## Required Secret

Add `OPENAI_API_KEY` as a repository Actions secret. Do not commit API keys,
tokens, or deploy credentials.
