# 数据指南 (Data Guide)

> 最后更新: 2026-05-14 | 分支: main | 维护者: SlveO

## 一、数据总览

| 数据层 | 位置 | 内容 | 数量 |
|--------|------|------|------|
| PostgreSQL | Docker `gaokao_agents-db-1` (localhost:5432) | 院校+录取+行业+映射 | 4表 |
| Chroma向量库 | 宿主机 `backend/chroma_data/` (Docker共享卷) | 语义检索索引 | 182K文档 |
| JSON种子文件 | 宿主机 `data/seed/` (Git追踪) | 院校+录取的静态副本 | 2文件 |
| JSON原始数据 | 宿主机 `data/raw/` (Git追踪) | 爬虫原始产出 | 多文件 |
| JSON Schema | 宿主机 `data/approved/` (Git追踪) | 完整数据集 | 6文件 |

## 二、数据存储详情

### 2.1 PostgreSQL (Docker容器内)

**连接方式：**
- Docker内部: `postgresql+asyncpg://gaokao:gaokao@db:5432/gaokao` (backend容器用)
- 宿主机: `postgresql+asyncpg://gaokao:gaokao@localhost:5432/gaokao` (调试用)

**表结构：**

| 表名 | 记录数 | 用途 |
|------|--------|------|
| `colleges` | 162 | 院校信息（粤65+京63+沪34） |
| `admission_data` | 194,041 | 录取分数线（31省×2021-2024） |
| `industry_analysis` | 60 | 行业分析（10行业×6年） |
| `major_industry_mapping` | 20 | 专业→行业→岗位映射 |

**查询示例：**
```sql
-- 按省份统计院校和录取数据
SELECT c.province, count(distinct c.id) as schools, count(a.id) as admissions
FROM colleges c LEFT JOIN admission_data a ON a.college_id = c.id
GROUP BY c.province;

-- 查询特定专业的录取数据
SELECT c.name, a.major_name, a.year, a.province, a.min_score, a.min_rank
FROM admission_data a JOIN colleges c ON c.id = a.college_id
WHERE a.major_name LIKE '%计算机%' AND a.year = 2024 AND a.province = '广东'
ORDER BY a.min_score DESC LIMIT 20;
```

### 2.2 Chroma向量库 (宿主机，Docker共享卷)

**路径：** `backend/chroma_data/` (Git忽略，但由docker-compose挂载到容器 `/app/chroma_data`)

**集合：** `colleges_majors` — 182K文档

**元数据结构：**
```python
{
    "college_id": "uuid",
    "college_name": "中山大学",
    "major_name": "计算机科学与技术",
    "level": "985",
    "province": "广东",
    "city": "广州",
    "min_rank": 4200,
    "min_score": 655,
    "subjects": "物理+化学",
    "source_url": "https://static-data.gaokao.cn/...",
    "industries": "信息传输、软件和信息技术服务业"
}
```

### 2.3 JSON种子文件 (宿主机，Git追踪)

| 文件 | 路径 | 大小 | 记录数 |
|------|------|------|--------|
| schools.json | `data/seed/schools.json` | 42KB | 162 |
| scores.json | `data/seed/scores.json` | 69MB | 194,041 |

**schools.json 字段：** name, code, type, level, province, city, is_985, is_211, is_double_first, intro

**scores.json 字段：** college_name, major_name, year, province, batch, min_score, min_rank, subject_requirements, source_url

### 2.4 JSON原始/中间数据

| 文件 | 内容 |
|------|------|
| `data/raw/gaokao_scores/admissions_multiprov_merged.json` | 广东64K条 |
| `data/raw/beijing_scores.json` | 北京59K条 |
| `data/raw/shanghai_scores.json` | 上海71K条 |
| `data/raw/industry_data/industries.json` | 行业分析60条 |
| `data/raw/industry_data/major_industry_mapping.json` | 专业映射20条 |
| `data/raw/school_ids_*.json` | 粤/京/沪学校platform ID映射 |
| `data/approved/colleges_full.json` | 完整院校信息 |
| `data/approved/admissions.json` | 完整录取数据 |
| `data/approved/industries.json` | 行业数据 |
| `data/approved/major_industry_mapping.json` | 映射数据 |

## 三、API调用方式

### 3.1 后端已注册路由

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/colleges` | GET | 院校列表（分页，默认20条/页） |
| `/api/v1/colleges/{id}` | GET | 院校详情 |
| `/api/v1/industries` | GET | 行业分析列表（可选?year=2024） |
| `/api/v1/mappings` | GET | 专业-行业映射（可选?major_name=） |
| `/api/v1/industries/by-major` | GET | 按专业查行业数据（?major_name=） |
| `/api/v1/recommendations` | GET | 生成志愿推荐（基于Chroma检索+LLM排序） |

### 3.2 调用示例

```bash
# 查看所有广东985院校
curl "http://localhost:8000/api/v1/colleges?level=985&province=广东&page_size=100"

# 查看2024年行业薪资数据
curl "http://localhost:8000/api/v1/industries?year=2024"

# 查计算机专业的就业方向
curl "http://localhost:8000/api/v1/industries/by-major?major_name=%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%A7%91%E5%AD%A6%E4%B8%8E%E6%8A%80%E6%9C%AF"

# 获取推荐（需认证token）
curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/recommendations"
```

## 四、数据导入流程

### 4.1 从种子文件导入 (全新环境)

```bash
# 1. 启动Docker服务
docker compose up -d db redis

# 2. 导入种子数据到PostgreSQL
# 方式A: Docker内部运行（推荐）
docker exec gaokao_agents-backend-1 python -c "
import asyncio, sys; sys.path.insert(0, '/app')
from scripts.seed_db import seed
asyncio.run(seed('data/seed'))
"

# 方式B: 宿主机运行（需localhost可连DB）
DATABASE_URL="postgresql+asyncpg://gaokao:gaokao@localhost:5432/gaokao" \
python scripts/seed_db.py data/seed/
```

### 4.2 重建Chroma索引

```bash
# 宿主机运行（需要sentence-transformers + chromadb）
cd D:/_Greatest_programmer/_Projects/gaokao_agents
python -c "
import asyncio; from scripts.index_chroma import index
asyncio.run(index())
"

# 或使用backend目录下的副本（容器兼容）
docker exec gaokao_agents-backend-1 python /app/index_chroma.py
```

**注意：** Chroma索引需要加载bge-large-zh-v1.5模型（~1.3GB），首次运行会下载到 `C:/Users/<user>/.cache/huggingface/` 或Docker的modelscope卷。

## 五、数据扩充流水线

### 5.1 新增省份院校数据

**前置条件：** 已安装依赖 `pip install httpx sentence-transformers chromadb`

```
步骤1: 扫描学校ID
  运行范围扫描找到目标省份院校在static-data.gaokao.cn上的内部ID
  参考: scrapers/config_beijing.py 中的格式
  输出: data/raw/school_ids_{省份}.json

步骤2: 创建学校配置文件
  格式参考: scrapers/config_beijing.py
  包含: platform ID → (学校名, code_id) 字典

步骤3: 采集录取数据
  修改 scripts/collect_provinces.py 中的main()函数
  添加新省份的collect_schools调用
  运行: python scripts/collect_provinces.py
  输出: data/raw/{省份}_scores.json

步骤4: 合并导入
  将新数据合并到 all_scores 列表
  更新 colleges 字典（添加新学校）
  运行导入脚本写入PostgreSQL

步骤5: 重建Chroma
  运行Chroma重建脚本（约需1-3小时/20万条）
  完成后重启backend: docker compose restart backend

步骤6: 验证
  curl http://localhost:8000/api/v1/colleges?province={新省份}
  curl http://localhost:8000/api/health
```

### 5.2 更新现有数据（新年度）

```
1. 修改 scripts/collect_provinces.py 中的 YEARS 列表
2. 运行采集脚本（仅采集新年份）
3. 合并到scores.json
4. 重新导入PostgreSQL (TRUNCATE + 全量导入)
5. 重建Chroma索引
```

### 5.3 关键脚本速查

| 脚本 | 用途 | 运行位置 |
|------|------|----------|
| `scripts/collect_provinces.py` | 多省份录取数据采集 | 宿主机 |
| `scripts/seed_db.py` | 导入数据到PostgreSQL | Docker/宿主机 |
| `scripts/index_chroma.py` | 重建Chroma索引 | 宿主机 |
| `scripts/monitor_chroma.py` | 实时监控索引进度 | 宿主机 |
| `backend/index_chroma.py` | Chroma重建(Docker版) | Docker内 |
| `scrapers/run_all.py` | 旧版全流程编排器 | 宿主机 |

## 六、多设备协作注意事项

1. **数据文件通过Git同步：** `data/seed/`、`data/raw/`、`data/approved/` 均在版本控制中
2. **Chroma索引不在Git中：** `backend/chroma_data/` 在 `.gitignore`，每台设备需独立重建
3. **PostgreSQL数据不在Git中：** 通过运行 `seed_db.py` 从种子文件恢复
4. **嵌入模型需独立下载：** 每台设备首次运行索引时自动下载
5. **Docker卷持久化：** `pgdata` 和 `ms_cache` 卷在设备间不共享

**新设备初始化流程：**
```bash
git clone <repo> && cd gaokao_agents
docker compose up -d db redis backend frontend
docker exec gaokao_agents-backend-1 python scripts/seed_db.py
# Chroma索引需在宿主机重建（见第四节）
```

## 七、数据源说明

所有数据来自公开API：
- **static-data.gaokao.cn** (掌上高考/中国教育在线) — 院校信息+录取分数线
- 省份ID对照: 北京=11, 上海=31, 广东=44, 完整列表见 `scripts/collect_provinces.py`

学校内部ID（platform_id）与教育部代码（MOE code）的映射关系存储在：
- `scrapers/sources/eol_api.py` 的 `SCHOOL_ID_MAP` 字典（广东）
- `scrapers/config_beijing.py` 的 `BEIJING_SCHOOLS` 字典
- `scrapers/config_shanghai.py` 的 `SHANGHAI_SCHOOLS` 字典
