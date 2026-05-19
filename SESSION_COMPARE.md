# Session A: 学生主页面（跨院校对比）

> 分支: `feat/compare-page` | 基于: `develop` | Web-first

## 启动

```bash
git checkout develop && git checkout -b feat/compare-page
```

必读: `docs/superpowers/specs/2026-05-19-optimization-design.md` §A

## 任务

### 1. 新增跨院校推荐 API

`backend/recommendation/cross_college.py`:

```python
async def cross_college_recommendations(profile: dict, tenant_slugs: list[str], top_n: int = 10) -> list[dict]:
    """遍历 tenant ChromaDB collections，按画像匹配度返回 Top-N 院校"""
    results = []
    for slug in tenant_slugs:
        candidates = retrieve_candidates(profile, k=10, tenant_slug=slug)
        if candidates:
            # 计算该院校的平均匹配分
            avg_score = sum(c.get("distance", 0) for c in candidates) / len(candidates)
            results.append({
                "tenant_slug": slug,
                "majors": [c["metadata"] for c in candidates[:3]],
                "match_score": round(100 - avg_score * 100, 1),
            })
    results.sort(key=lambda r: r["match_score"], reverse=True)
    return results[:top_n]
```

路由 `GET /api/v1/compare/recommendations` — 读取 active tenants，调 cross_college_recommendations。

### 2. 新增 H5 对比页面

`mini-app/src/pages/compare/index.vue`:
- 院校卡片列表（名称、匹配度 %、Top-3 专业）
- 点开专业详情 → 录取概率、分数线
- 多选对比（最多 3 所院校并排）

`mini-app/src/pages.json` 加路由。

### 3. 从 chat 页面跳转

chat 页面"推荐"按钮 → `/pages/compare/index`，带 profile snapshot。

## 完成标志

- [ ] `GET /api/v1/compare/recommendations` 返回 SCNU + 其他 tenant 的匹配结果
- [ ] H5 对比页面可展示多院校卡片
