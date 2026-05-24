# 数据指南 (Data Guide)

> 最后更新: 2026-05-23 | 当前状态: SCNU 单院校深度数据可用；Phase 5 多省数据扩展暂缓

## 本轮说明

本轮基础设施加固不新增省份、不新增爬虫配置、不扩展 Phase 5 数据范围。当前完整可演示数据以华南师大 `scnu` tenant 为主，包含录取、培养、就业数据导入与 ChromaDB 索引。下方“数据扩充流水线”保留为后续 Phase 5 的操作参考。

## 一、数据位置速查

**项目数据位于仓库 `data/`、`backend/chroma_data/` 和租户导入表中。**

| 你要什么 | 在哪里 | 怎么读 |
|----------|--------|--------|
| 院校信息 (162校) | `data/seed/schools.json` | JSON数组，字段: name/code/type/level/province/city/is_985/is_211 |
| 录取数据 (194K条) | `data/seed/scores.json` | JSON数组，字段: college_name/major_name/year/province/min_score/min_rank |
| 行业分析 (60条) | `data/approved/industries.json` | JSON数组，字段: industry_name/avg_annual_salary/outlook |
| 专业映射 (20条) | `data/approved/major_industry_mapping.json` | JSON数组，字段: major_name/primary_industries/salary_range |
| 华师综合咨询知识 | `data/approved/scnu_comprehensive_knowledge.json` | JSON数组，字段: category/topic/summary/text/qa/source_url |
| 向量索引 (182K文档) | `backend/chroma_data/` | ChromaDB集合 `colleges_majors` |
| 数据库 (4表) | Docker `gaokao_agents-db-1:5432` | PostgreSQL, 用户gaokao/密码gaokao/库gaokao |

## 二、API接入方式

**后端地址:** `http://localhost:8000`

| 端点 | 方法 | 用途 | 示例 |
|------|------|------|------|
| `/api/v1/colleges` | GET | 院校列表 | `?province=广东&level=985&page_size=100` |
| `/api/v1/colleges/{id}` | GET | 院校详情 | `/api/v1/colleges/<uuid>` |
| `/api/v1/industries` | GET | 行业分析 | `?year=2024` |
| `/api/v1/mappings` | GET | 专业映射 | `?major_name=计算机科学与技术` |
| `/api/v1/industries/by-major` | GET | 专业→行业详情 | `?major_name=计算机科学与技术` |
| `/api/v1/knowledge/search` | GET | 租户知识库RAG检索 | `?q=华师住宿费多少&k=5&data_type=campus_life` |
| `/api/v1/recommendations` | GET | 志愿推荐 | 需Bearer Token |
| `/api/health` | GET | 健康检查 | 返回 `{"status":"ok"}` |

**推荐API调用前提:** 用户需先走完对话流程构建画像（RIASEC+价值观+地域），否则返回空列表。注册+登录即可调用其他端点。

## 三、华南师大综合咨询知识库

本轮新增 `scnu` tenant 的综合咨询知识包，面向高考生常见问题整理，覆盖学校概况、三校区四校园、优势学科、师范特色、招生批次、录取规则、转专业限制、选科与外语、体检限制、学费住宿费、奖助政策、招生计划入口、招生办联系方式和志愿咨询策略。

导入并索引：

```bash
python scripts/create_scnu_tenant.py
python scripts/import_scnu_knowledge.py
```

RAG 检索示例：

```bash
curl "http://localhost:8000/api/v1/knowledge/search?q=华南师范大学住宿费多少&k=5&data_type=campus_life" \
  -H "X-Tenant: scnu"
```

返回结构：

```json
{
  "query": "华南师范大学住宿费多少",
  "tenant": "scnu",
  "results": [
    {
      "text": "华南师范大学 收费与住宿...",
      "metadata": {"category": "收费与住宿", "source_url": "..."},
      "source_url": "https://zsb.scnu.edu.cn/a/20250515/684.html"
    }
  ]
}
```

## 四、ChromaDB状态（已验证）

```
SQLite完整性: ok
文档数:       182,000
语义检索:     正常 (查询"计算机"返回3条匹配)
残留目录:     已清理 (释放1.2GB)
sqlite3大小:  589MB → 当前正常
```

**之前报 `sqlite3.OperationalError` 的原因:** 索引重建进程与backend同时访问SQLite导致的瞬时锁冲突，非数据损坏。索引进程结束后自动恢复。

## 五、数据扩充流水线（严格流程）

### 新增省份 (如浙江/江苏)

```
步骤1: 扫描学校platform ID
  python -c "
  import asyncio,httpx,json
  # 扫描目标省份(province=33浙江), 找到所有学校在static-data.gaokao.cn的内部ID
  # 参考 scrapers/config_beijing.py 的输出格式
  # 保存到 data/raw/school_ids_浙江.json
  "

步骤2: 创建学校配置文件
  # 参照 scrapers/config_beijing.py 格式
  # 文件: scrapers/config_zhejiang.py
  # 内容: ZHEJIANG_SCHOOLS = {"pid": ("学校名", "code_id"), ...}

步骤3: 采集录取数据
  # 修改 scripts/collect_provinces.py:
  #   1. import ZHEJIANG_SCHOOLS
  #   2. 在main()中添加: zj_records = await collect_schools(ZHEJIANG_SCHOOLS, "Zhejiang")
  #   3. 保存到 data/raw/zhejiang_scores.json
  # 运行: python scripts/collect_provinces.py
  # 时间: ~10-30分钟/省份 (取决于学校数量)

步骤4: 合并导入PostgreSQL
  # 用 data/raw/ 下的各省JSON文件
  # 构建colleges字典 + scores列表
  # 运行导入 (参考DATA_GUIDE.md第四节)

步骤5: 重建Chroma索引
  python scripts/index_chroma.py  # 宿主机运行, 1-2小时

步骤6: 重启backend + 验证
  docker compose restart backend
  curl http://localhost:8000/api/v1/colleges?province=浙江
```

### 更新新年份数据

```
1. 修改 scripts/collect_provinces.py 中 YEARS = [2025] (添加新年份)
2. 运行采集 → 合并 → 导入 → 重建Chroma
```

## 五、当前数据覆盖

| 省份 | 院校 | 录取记录 | 年份 | 省数 |
|------|------|----------|------|------|
| 广东 | 65 | 64,083 | 2020-2024 | 31 |
| 北京 | 63 | 59,087 | 2021-2024 | 31 |
| 上海 | 34 | 70,871 | 2021-2024 | 31 |
| **合计** | **162** | **194,041** | | |

## 六、验证步骤（主session接入时执行）

```bash
# 1. 确认PostgreSQL可访问
docker exec gaokao_agents-db-1 psql -U gaokao -d gaokao \
  -c "SELECT province, count(*) FROM colleges GROUP BY province;"
# 期望输出: 广东=65, 北京=63, 上海=34

# 2. 确认Chroma可读
python -c "
import chromadb
c = chromadb.PersistentClient(path='D:/_Greatest_programmer/_Projects/gaokao_agents/backend/chroma_data')
col = c.get_collection('colleges_majors')
print(f'Chroma: {col.count()} docs')
r = col.query(query_texts=['计算机'], n_results=3)
print(f'Query: {len(r[\"ids\"][0])} results')
"
# 期望: 182000 docs, 3 results

# 3. 确认API可用
curl http://localhost:8000/api/health
# 期望: {"status":"ok"}

# 4. 确认推荐链路
# 注册用户 → 获取token → GET /api/v1/recommendations
```

## 七、关键脚本

| 脚本 | 位置 | 用途 |
|------|------|------|
| collect_provinces.py | scripts/ | 队列模式采集多省录取数据 |
| seed_db.py | scripts/ | 从JSON导入PostgreSQL |
| index_chroma.py | scripts/ | 宿主机重建Chroma索引 |
| index_chroma.py | backend/ | Docker内重建Chroma(容器兼容版) |
| monitor_chroma.py | scripts/ | 实时监控索引进度 |

## 八、多设备协作

- **Git同步范围:** `data/seed/`, `data/raw/`, `data/approved/`, 全部爬虫代码
- **不在Git中:** `backend/chroma_data/` (需每设备独立重建), Docker卷 pgdata/ms_cache
- **新设备初始化:** clone → docker compose up → seed_db.py → index_chroma.py (1-2h)
- **嵌入模型:** bge-large-zh-v1.5 (~1.3GB), 首次运行自动下载
