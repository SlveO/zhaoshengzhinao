---
name: kb-reindex
description: Rebuild ChromaDB vector index for a tenant's college data. Invoke when user says "reindex", "rebuild knowledge base", "index colleges", or "refresh vector data".
---

# Knowledge Base Reindex

Rebuild the ChromaDB vector index for a specific tenant's college/major data.

## Steps

1. **Identify tenant** — confirm which tenant to reindex (e.g., `scnu`)

2. **Run indexing**:
   The indexing logic lives in `backend/knowledge/` which handles:
   - Reading tenant data (admission scores, majors, college info)
   - Generating embeddings via the configured LLM
   - Storing in ChromaDB collection `{tenant_slug}_colleges`

3. **Verify**:
   - Check the ChromaDB collection exists and has documents
   - Spot-check a semantic search query to confirm results

## Notes
- Each tenant has its own ChromaDB collection (`{tenant_slug}_colleges`)
- The old `backend/knowledge_base/` module provides the global/historical ChromaDB client — do not confuse with the tenant-aware `backend/knowledge/`
