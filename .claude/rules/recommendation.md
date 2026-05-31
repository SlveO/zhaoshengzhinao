# Recommendation Engine

Pipeline in `backend/services/recommendation_service.py`:
1. Retrieve candidates from ChromaDB (hybrid: semantic search + subject filter + diversity, max 3 per college)
2. Enrich with industry data (`IndustryAnalysis`, `MajorIndustryMapping`)
3. Build LLM prompt with adaptive weighting based on profile completeness level
4. Call DeepSeek (temp=0.3) with retry (2 attempts, exponential backoff)
5. Save `Recommendation` record
6. Write analytics event
