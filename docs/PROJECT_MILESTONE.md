# 招生智脑 B2B 平台 — 项目阶段性总结

> 更新日期: 2026-05-18 | 当前阶段: Phase 4 完成（调试修复 + 单院校数据就绪） | 下一阶段: 多院校数据扩展

---

## 一、项目最终目标

构建一个面向中国高等院校的 **AI 招生 SaaS 平台**，帮助院校实现从"摆摊宣讲"到"24/7 AI 个性化招生咨询"的数字化转型。

### 终极能力矩阵

| 层面 | 能力 | 当前状态 |
|------|------|---------|
| **学生端** | 扫码 → AI 对话 → 画像生成 → 专业推荐 → 多校对比 | 🟢 已验证可运行 |
| **院校端** | 品牌定制小程序 → 知识库管理 → 招生漏斗 → 学生画像看板 → 竞品分析 | 🟢 平台框架完整 |
| **数据层** | 10 省 × 800+ 院校录取/培养/就业数据 | 🟡 华南师大 1 所就绪，待扩展 |
| **商业层** | 付费订阅 + 模块开关 + 增值模块计费 | 🟢 技术框架就绪 |
| **部署层** | SaaS 多租户 + 旗舰版私有部署 | 🟡 SaaS 可本地运行，私有部署未打包 |

---

## 二、当前进度总览

### 开发里程碑

```
Phase 0: 核心引擎稳定         ✅
Phase 1: 多租户地基           ✅
Phase 2: 外壳重建             ✅
Phase 3: 增值模块             ✅
Phase 4: 调试修复 + 单院校数据 ✅ ← 当前
Phase 5: 多院校数据扩展        ⬜
Phase 6: 压测 + 部署准备       ⬜
```

### 工程产出

| 维度 | 数值 |
|------|------|
| 总文件数 | ~340 |
| Git Commits | 20+ |
| 后端 Python 源文件 | ~55 |
| 单元测试文件 | 25 |
| Admin SPA 源文件 | 17 (React + TypeScript) |
| Mini-App 源文件 | 19 (uni-app + Vue 3) |
| 数据库表 | 17 (含分区 event_logs) |
| Alembic 迁移 | 4 (可逆性验证通过) |
| ChromaDB SCNU 文档 | 1,997 |
| 已创建 Tenant | 3 (default, gdufs, scnu) |

### 8 个轨道完成度

| 轨道 | 状态 | 核心产出 |
|------|------|---------|
| Foundation | ✅ | 多租户框架、中间件、事件系统、guest 对话 |
| Admin SPA | ✅ | 管理端 5 页面 + CSS 换肤 + ECharts |
| Mini-App | ✅ | 小程序 29 文件 + 白标构建 + H5 可用 |
| Analytics | ✅ | 7 个真实 SQL 聚合模块 |
| Data Onboarding | ✅ | Excel 导入 + 校验 + 模板 + 知识库 API |
| SCNU Scraper | ✅ | 华南师大 1,567 录取 + 86 培养 + 344 就业 |
| SCNU Import | ✅ | 华师 tenant + 1,997 条全量导入 ChromaDB |
| Bug Fixes | ✅ | 4 根因修复，学生端对话可用 |

---

## 三、Phase 4：调试修复总结

### 修复的 6 个问题

| # | 问题 | 根因 | 修复方式 |
|---|------|------|---------|
| 1 | 学生端输入框永远禁用 | API 返回 `{session_id}` 但 chat store 读 `res.data.session_id` → undefined → WS 从未连接 | 读 `res.session_id` |
| 2 | 点击预设问题无 AI 回复 | uni-app 3.0 alpha H5 模式 `uni.connectSocket()` 返回空对象，所有方法不可用 | 全部替换为原生 `new WebSocket()` |
| 3 | WebSocket 连接卡在 connecting | `BaseHTTPMiddleware` 只处理 HTTP scope，跳过 WebSocket | WS handler 内自行解析 `?tenant=` |
| 4 | CORS 预检被拦截 | OPTIONS 请求没有 X-Tenant 头，被中间件 401 | 中间件跳过 OPTIONS |
| 5 | LLM 调用失败 | `backend/.env` 缺失，API key 未加载 | 复制 `.env` 到 `backend/` |
| 6 | 启动时 DNS 解析失败 | `.env` 用 Docker 内部主机名 `db`，宿主机无法解析 | 改为 `localhost` |

### 管理端修复

| # | 问题 | 根因 | 修复方式 |
|---|------|------|---------|
| 7 | 品牌设置主题色不一致 | 后端返回 `primary_color`(snake_case)，前端读 `primaryColor`(camelCase) → undefined | 统一为 snake_case |
| 8 | Analytics 页面返回 401 | 缺少 JWT 解析中间件 | 新增 UserAuthMiddleware |

---

## 四、系统当前可运行服务

### 启动方式

```bash
# 1. 启动基础服务
docker compose up -d db redis

# 2. 启动后端
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000

# 3. 启动管理端（新终端）
cd admin-spa
npm run dev -- --port 3001

# 4. 启动学生端 H5（新终端）
cd mini-app
TENANT=scnu node build.config.js
npm run dev:h5 -- --port 3002
```

### 访问地址

| 端 | URL | 账号 |
|----|-----|------|
| 管理端 | `http://localhost:3001?tenant=scnu` | admin / admin123 |
| 学生端 | `http://localhost:3002` | 无需登录，扫码即聊 |

### 可演示流程

1. 管理端登录 → 侧边栏显示华师深蓝 `#1a3a6b` → 知识库页面显示 1,997 条文档
2. 学生端打开 → 华师品牌色欢迎页 → 点预设问题或自由输入 → AI 对话 → 画像实时更新 → 阶段推进 → 推荐结果
3. 切换 tenant 到 default → 品牌色变为蓝色 `#2563eb` → 知识库为空

---

## 五、数据现状

| 数据层 | 华南师大 (scnu) | 广东工业 (gdufs) | 其他院校 |
|--------|----------------|-----------------|---------|
| 院校信息 | ✅ | ✅ | 162 所基础信息 |
| 录取数据 | ✅ 1,567 条 (10省×5年) | ⚠️ 部分有 | 182K 文档 (3省) |
| 培养计划 | ✅ 86 专业 | ❌ 无 | ❌ 无 |
| 就业数据 | ✅ 344 条 | ❌ 无 | ❌ 无 |
| 校园信息 | ❌ 无 | ❌ 无 | ❌ 无 |
| ChromaDB 索引 | ✅ 1,997 docs | ❌ 未索引 | 182K (全局共享) |

---

## 六、总任务规划

### 已完成

```
✅ Phase 0: 核心引擎稳定
   - Alembic 迁移体系、18 单元测试、LLM 容错、WebSocket 异常处理

✅ Phase 1: 多租户地基
   - Tenant/TenantUser/TenantData/Department/SessionProfile 模型
   - TenantResolutionMiddleware + ModuleGateMiddleware
   - event_logs 分区表 + event_writer
   - ChromaDB 多 collection 隔离

✅ Phase 2: 外壳重建
   - Admin SPA (React+TS+Tailwind, 5 页面, CSS 变数换肤)
   - Mini-App (uni-app+Vue3, 29 文件, 白标构建)

✅ Phase 3: 增值模块
   - 7 个 Analytics SQL 聚合模块 + stub→real 替换
   - Data Onboarding: Excel 导入 + 校验 + ChromaDB 索引
   - 知识库管理 API (CRUD + 重索引 + 状态查询)

✅ Phase 4: 调试修复 + 单院校数据
   - 6 个前端 Bug 修复（WS/CORS/API/snake_case/BaseHTTPMiddleware）
   - 华南师大 1,997 条数据（爬虫采集→清洗→导入→索引）
   - scnu tenant 完整可用
```

### 待完成

```
⬜ Phase 5: 多院校数据扩展 (预估 2-3 周)
   目标: 10 省 × 500+ 院校的录取数据 + 3 所试点院校的完整培养/就业数据
   任务:
   - 爬虫扩展到 10 省教育考试院 API
   - 3 所试点院校深度数据（培养计划、就业报告）
   - ChromaDB 全量重索引
   - 数据质量验证与去重

⬜ Phase 6: 性能压测 + 部署准备 (预估 2 周)
   目标: 50 院校并发可承载，出私有部署包
   任务:
   - Locust 并发对话压测
   - ChromaDB 多 collection 查询性能优化
   - 旗舰版 docker-compose.prod.yml
   - 部署文档 + 运维手册

⬜ Phase 7: 产品化收尾 (预估 2 周)
   目标: 真实院校试点的 Demo 就绪
   任务:
   - 3 所试点院校全流程 UAT
   - 学生对话种子数据注入（让漏斗/画像看板有东西展示）
   - 小程序微信审核提交
   - Investor Demo 脚本准备
```

### 最终目标

```
┌─────────────────────────────────────────────────┐
│ 招生智脑 B2B SaaS 平台 v1.0                      │
│                                                  │
│ 学生端: 扫码 → AI 深度对话 → 画像生成             │
│         → 专业推荐（附证据溯源）→ 多校对比        │
│                                                  │
│ 院校端: 品牌小程序 + 知识库管理                    │
│         + 招生漏斗 + 画像看板 + 竞品分析           │
│                                                  │
│ 数据: 10 省 800+ 院校录取数据                      │
│       3 所试点院校全量培养/就业数据                │
│                                                  │
│ 商业: 4 档 SaaS 订阅 + 10 个增值模块               │
│       LTV:CAC 25:1, 盈亏平衡 28 所院校            │
│                                                  │
│ 部署: Docker Compose 一键启动                     │
│       旗舰版独立 VPC 私有部署                     │
└─────────────────────────────────────────────────┘
```

---

## 七、当前可演示 vs 待完成

### 现在就能演示的

- 管理端登录 → 品牌色切换 → 知识库文档浏览 → 漏斗/画像看板（空数据）
- 学生端 H5 → 匿名对话 → AI 多轮引导 → 画像实时更新 → 阶段推进
- 切换 tenant 验证多租户隔离
- Excel 上传 → 自动校验 → ChromaDB 索引全链路

### 还不能演示的

- 漏斗和画像看板有真实数据（需要真实学生对话灌入）
- 小程序微信扫一扫（需要 appId + 审核）
- 多省份录取数据覆盖（仅华南师大完整）
- 生产环境部署（仅本地开发可用）
