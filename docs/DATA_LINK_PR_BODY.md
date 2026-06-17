# Summary

This PR adds and polishes the C task data link pipeline for admissions consultation data. It keeps the development version lightweight while making it reviewable and ready for A/B group integration.

# Core Capabilities

- Saves consultation sessions and messages.
- Extracts student information through rules.
- Adds LLM structured extraction with an OpenAI-compatible client.
- Uses `HybridExtractor`: `llm` on success, `rule_fallback` on LLM failure, `rule` when no key is configured.
- Merges multi-turn student profiles without clearing old fields.
- Generates intent score, intent level, and tags.
- Generates report summary statistics.
- Provides local JSON mock storage.
- Adds demo, interactive manual testing, and automated tests.

# How To Run

```bash
npm run data-link:demo
npm run data-link:interactive
npm run test:data-link
```

# Test Result

```text
data-link tests passed: 18
```

Tests use fake/mock LLM clients and do not call external APIs.

# LLM Configuration

Configure LLM extraction with environment variables:

```bash
DATA_LINK_LLM_ENABLED=true
DATA_LINK_LLM_PROVIDER=deepseek
DATA_LINK_LLM_API_KEY=your-real-key
DATA_LINK_LLM_BASE_URL=https://api.deepseek.com/v1/chat/completions
DATA_LINK_LLM_MODEL=deepseek-chat
DATA_LINK_LLM_TIMEOUT=20
```

No real API key is committed. Without an API key, the pipeline uses rule extraction.

# A/B Group Integration Notes

B group can call `process_consultation_turn` after each AI reply is generated.

A group can replace `JsonDataLinkStore` with a future `DatabaseDataLinkStore` that implements the same store methods. The core pipeline does not need major changes.

See `docs/DATA_LINK_INTEGRATION_GUIDE.md` for details.

# Current Limitations

- JSON storage is for development and demo only.
- LLM output may be unstable, so rule fallback remains required.
- This PR does not add production database migrations, admin pages, privacy controls, or real user authorization.
