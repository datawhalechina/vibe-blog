# Live Generation E2E Stabilization

## Goal

Keep live generation tests within a bounded external-fetch budget and prevent
tests from opening a blog detail page before its history record is readable.

## Production Changes

1. Apply configurable per-request timeouts, retry limits, and a total deadline
   to deep scraping.
2. Give the mini preset a smaller request budget and fewer source URLs.
3. Process sources against one shared deadline, stop after the configured
   success count, and bound Jina retry/backoff plus HTTP fallback by each
   source's remaining slice.
4. Preserve the existing Jina-to-HTTP fallback and output structure.
5. Keep task terminal transitions queryable and prevent later events from
   overwriting completed, failed, or cancelled states.
6. Allow explicit API requests to disable research and image generation while
   keeping both options enabled by default for normal users.
7. Publish task completion immediately after history persistence so optional
   summary and logging post-processing cannot delay the queryable result.

## E2E Changes

1. Centralize outline waiting with immediate failed/cancelled task detection.
2. Centralize generation waiting on both a completed task and a readable
   history record rather than a fixed sleep or an unverified task ID.
3. Run TC02 and TC16 through an intercepted mini request with research and
   image generation disabled so they exercise the live writing pipeline
   without spending their budget on independent external media providers.
4. Use the helpers in TC02, TC15, and TC16 without changing API or SSE names.

## Verification

- Deep scraper and E2E helper unit tests.
- Full backend tests, frontend tests, and frontend production build.
- Focused live TC02, TC15, and TC16 where configured providers are available.
