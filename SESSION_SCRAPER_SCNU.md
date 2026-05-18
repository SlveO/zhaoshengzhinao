# Session 指令：华南师范大学数据采集

> 分支: `feat/data-scnu-scraper` | 基于: `develop` | 产出供 Data Import 轨道消费

---

## 启动清单

### 1. 必读文档

| 顺序 | 文件 | 关注内容 |
|------|------|---------|
| 1 | `COLLABORATION.md` | 分支策略 |
| 2 | `CONVENTIONS.md` | Python 规范 |
| 3 | `docs/PROJECT_MILESTONE.md` §四 | 数据五层结构、现有数据状态 |
| 4 | `scrapers/sources/eol_api.py` | 已有爬虫参考——高考网 API 模式 |
| 5 | `scrapers/base_scraper.py` | 基类：重试/限流/日志/持久化 |
| 6 | `scrapers/config.py` | 现有院校列表、省份配置 |

### 2. 创建分支

```bash
git checkout develop
git checkout -b feat/data-scnu-scraper
```

### 3. 目标院校

**华南师范大学 (South China Normal University)**

| 属性 | 值 |
|------|-----|
| 院校代码 (MOE) | 10574 |
| 层次 | 211、双一流 |
| 所在地 | 广州 |
| 校区 | 石牌、大学城、南海 |
| 本科专业数 | ~85 个 |
| 官网 | https://www.scnu.edu.cn |
| 招生网 | https://zsb.scnu.edu.cn |
| 教务处 | https://jwc.scnu.edu.cn |

---

## 数据采集任务

### Task 1: 录取分数线（P0 — 最重要）

**数据源**: 高考网 API (`static-data.gaokao.cn`)

**需采集**:

| 维度 | 范围 |
|------|------|
| 年份 | 2021, 2022, 2023, 2024, 2025 |
| 省份 | 广东（主）+ 其他已覆盖省（北京、上海、江苏、浙江、湖北、湖南、四川、山东、河南） |
| 批次 | 本科批 |
| 字段 | major_name, min_score, min_rank, subject_requirements, enrollment_quota |

**实现**: 在 `scrapers/config.py` 中新增华南师大的 platform_id 映射，复用现有 `eol_api.py`。

```python
# scrapers/config.py 新增
SCNU_SCHOOLS = {
    "10574": {  # 华南师范大学 MOE code
        "name": "华南师范大学",
        "platform_id": "XXX",  # 需从 gaokao.cn 查询
    }
}
```

**验证标准**: 至少产出 500 条录取记录（85 专业 × 5 年 × 2+ 省）

### Task 2: 专业培养计划（P1）

**数据源**: 华南师大教务处官网 + 各学院网站

**需采集**（每个专业）:

| 字段 | 来源 |
|------|------|
| major_name | 招生网专业目录 |
| college (所属学院) | 同上 |
| duration (学制) | 4年/5年 |
| degree (学位) | 理学学士/工学学士/... |
| core_courses (核心课程) | 培养方案 PDF |
| objective (培养目标) | 培养方案 PDF |
| credit_requirement (学分要求) | 培养方案 PDF |

**爬取策略**:
1. 先爬招生网 → 获取完整专业列表 + 所属学院
2. 再爬各学院网站 → 获取培养方案 PDF
3. PDF 解析 → 提取核心课程和培养目标文本

**验证标准**: 至少覆盖 60 个专业的培养计划（师范类 + 主流非师范类）

### Task 3: 就业质量报告（P1）

**数据源**: 华南师大就业指导中心官网 → 年度就业质量报告 PDF

**需采集**（每个专业/学院）:

| 字段 | 来源 |
|------|------|
| employment_rate | 就业质量报告 |
| avg_salary | 就业质量报告（如有） |
| main_industries | 就业质量报告行业分布 |
| typical_employers | 就业质量报告重点单位 |
| further_study_rate | 就业质量报告深造率 |
| top_graduate_schools | 深造去向 |

**年份**: 2021-2024 届（4 份报告）

**实现**: PDF 解析器（已有 `scrapers/parsers/` 目录结构）

**验证标准**: 至少产出 30 个专业/学院的就业数据

### Task 4: 课程设计安排（P2 — 加分项）

**数据源**: 各学院网站 → 教学计划/课程表

**需采集**（每个专业）:
- 学期-by-学期课程安排
- 必修/选修分类
- 实践环节（实习、毕业设计）

**验证标准**: 至少覆盖 20 个专业的课程安排

---

## 爬虫实现要求

### 复用现有基础设施

```python
# 所有爬虫继承 base_scraper.BaseScraper
from scrapers.base_scraper import BaseScraper

class SCNUCurriculumScraper(BaseScraper):
    source_name = "scnu_curriculum"
    delay_seconds = 2.0  # 礼貌爬取
```

### 输出格式

所有数据输出到 `data/raw/scnu/`：

```
data/raw/scnu/
├── admissions.json        # 录取数据
├── curriculums.json       # 培养计划
├── employment.json        # 就业数据
└── courses.json           # 课程安排
```

每份 JSON 文件的结构与 `CONVENTIONS.md` 中 TenantData 的 content 字段对应。

### 容错要求

- 单个专业数据爬取失败 → 记录错误，继续下一个
- 网络超时 → 重试 3 次（BaseScraper 已实现）
- PDF 解析失败 → 记录文件名，人工后续处理
- 最终输出: `data/raw/scnu/errors.json` 记录所有失败项

---

## 不碰的文件

```
admin-spa/        ← 不碰
mini-app/         ← 不碰
backend/          ← 不碰（只读 scrapers/config.py）
```

---

## 完成标志

- [ ] `data/raw/scnu/admissions.json` - 500+ 条录取记录
- [ ] `data/raw/scnu/curriculums.json` - 60+ 专业培养计划
- [ ] `data/raw/scnu/employment.json` - 30+ 专业就业数据
- [ ] `data/raw/scnu/errors.json` - 失败项清单
- [ ] 所有爬虫可通过 `python -m scrapers.sources.scnu_xxx` 独立运行
