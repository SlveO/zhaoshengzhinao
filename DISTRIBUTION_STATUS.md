# 文件分发工作流 — 协作者状态文档

> 最后更新：2026-06-05 | 作者：bigteacher-bit
> 分支：`feat/distribution`（已合并到 `develop`）
> PR：待创建

---

## 功能概述

为招生办老师提供"文件定时分发到企业微信群"的自动化工作流。

```
招生办上传文件 → 配置群机器人渠道 → 创建定时任务 → 到时自动推送
```

---

## 已完成 ✅

| 模块 | 内容 | 测试 |
|------|------|------|
| 数据库 | 5 张新表 (distribution_channels/files/tasks/logs/access_tokens) | Alembic 迁移 005 |
| 后端 API | `/api/v1/distribution/*` 完整 REST | 12/12 单元测试通过 |
| 安全 | Fernet 加密 webhook URL、文件类型白名单、单次访问令牌 | ✅ |
| 调度 | APScheduler 30s 轮询执行到期任务 | 代码完成，集成测试待验证 |
| 企业微信 | 群机器人 Webhook（文本/文件/上传）| 真实 Webhook 待测试 |
| 模块开关 | `ModuleKey.DISTRIBUTION`，在 tenant.config.modules 中控制 | ✅ |
| 前端 | 3 页面（文件分发/分发渠道/分发日志）+ 4 组件 | TypeScript 零错误，构建通过 |
| 风格 | 完全复用现有 CSS 类，无新 UI 库 | ✅ |

---

## 待完成 ⚠️（需要其他协作者接力）

### 1. 集成测试（需要 PostgreSQL）

```bash
cd backend
# 先执行数据库迁移
alembic upgrade head

# 运行集成测试
python -m pytest tests/integration/test_distribution_api.py -v
```
目前 13 条集成测试用例已写好，等待有 PostgreSQL 的环境验证。

### 2. 真实企业微信 Webhook 端到端测试

需要一个企业微信测试群 + 群机器人 webhook URL：
1. 在企业微信群里添加群机器人 → 获取 webhook URL
2. `POST /api/v1/distribution/channels` 注册渠道
3. `POST /api/v1/distribution/channels/{id}/test` 发送测试消息
4. 上传文件 → 创建任务 → `POST /api/v1/distribution/tasks/{id}/run` 立即触发
5. 确认群内收到文件、日志记录 status=success

### 3. 生产环境部署前提

```bash
# 必须设置的环境变量
export WEBHOOK_ENCRYPTION_KEY="<Fernet.generate_key() 生成的密钥>"
export FILE_STORE_DIR="./file_store"

# 数据库迁移
cd backend && alembic upgrade head

# 前端构建
cd admin-spa && npm run build
```

⚠️ **`WEBHOOK_ENCRYPTION_KEY` 不设置的话每次重启生成新 key，已加密的 webhook URL 将无法解密！**

### 4. 启用模块开关

在 tenant 的 `config.modules` 中添加：
```json
{ "distribution": true }
```
此后侧边栏才会出现"分发"分组菜单。

### 5. 前端 API 真实联调

当前前端有 mock 数据 fallback，API 失败时自动使用。后端部署好后，前端的 Axios 代理需要指向正确的后端地址。

---

## API 速查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/distribution/channels` | 渠道列表（分页） |
| POST | `/api/v1/distribution/channels` | 创建渠道 |
| POST | `/api/v1/distribution/channels/{id}/test` | 测试 webhook 连接 |
| DELETE | `/api/v1/distribution/channels/{id}` | 软删除渠道 |
| POST | `/api/v1/distribution/files/upload` | 上传文件（multipart） |
| GET | `/api/v1/distribution/files` | 文件列表 |
| DELETE | `/api/v1/distribution/files/{id}` | 删除文件 |
| GET | `/api/v1/distribution/tasks` | 任务列表（可按状态筛选） |
| POST | `/api/v1/distribution/tasks` | 创建任务 |
| POST | `/api/v1/distribution/tasks/{id}/run` | 立即执行 |
| POST | `/api/v1/distribution/tasks/{id}/pause` | 暂停 |
| POST | `/api/v1/distribution/tasks/{id}/resume` | 恢复 |
| GET | `/api/v1/distribution/logs` | 执行日志（可按状态/任务/渠道筛选） |

---

## 新增文件清单

```
backend/
├── distribution/     # 完整模块（8 文件）
├── migrations/versions/005_distribution_tables.py
└── tests/
    ├── integration/test_distribution_api.py
    └── unit/test_wechat_service.py

admin-spa/src/
├── api/distribution.ts
├── mock/distribution.ts
├── components/
│   ├── FileUpload.tsx
│   ├── ChannelFormModal.tsx
│   ├── TaskFormModal.tsx
│   └── TaskStatusBadge.tsx
└── pages/
    ├── DistributionTasksPage.tsx
    ├── DistributionChannelsPage.tsx
    └── DistributionLogsPage.tsx
```

## 修改文件清单

```
backend/
├── config.py           # +3 配置项
├── main.py             # 路由注册 + 调度器生命周期
├── models/__init__.py  # 导入 distribution 模型
├── core/module_registry.py   # +DISTRIBUTION 模块
├── core/tenant_context.py    # +文件下载公共路径
├── migrations/env.py  # 导入 distribution 模型
├── requirements.txt   # +apscheduler
└── tests/conftest.py  # +distribution 配置

admin-spa/src/
├── App.tsx            # +3 路由
├── components/Sidebar.tsx  # +分发菜单组
├── types/index.ts     # +4 接口
└── index.css          # +upload-zone 样式
```
