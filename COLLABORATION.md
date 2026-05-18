# 招生智脑 B2B 平台 — 多 Session 协作文档

> 最后更新: 2026-05-18 | 每 session 启动时必读

---

## 项目概述

将 Gaokao Agents 从单用户 B2C 原型改造为多租户 B2B SaaS 平台。核心策略：**AI 引擎复用，外壳重建。**

详细设计见 `docs/superpowers/specs/2026-05-18-b2b-platform-design.md`

---

## Git 分支策略

```
main ──────────────────────────────────────────────── (稳定，保护)
  │
  └─ develop ─────────────────────────────────────── (集成，PR 目标)
       │
       ├─ feat/foundation ────── Phase 0+1: 稳定化+多租户地基
       │
       ├─ feat/admin-spa ─────── Phase 2a: 管理端 SPA 重建
       │
       ├─ feat/mini-app ──────── Phase 2b: 小程序
       │
       ├─ feat/analytics ─────── Phase 3a: 增值分析模块
       │
       └─ feat/data-onboarding ─ Phase 3b: 数据接入管道
```

### 分支命名规范

```
feat/<component>       新功能分支
fix/<component>        Bug 修复分支
refactor/<component>   重构分支
```

### 合并规则

1. **feat/* → develop**: PR + review。功能完整、测试通过
2. **develop → main**: 里程碑完成后合并。所有测试通过
3. **禁止**: 直接 push 到 main 或 develop
4. **禁止**: feat/* 分支之间互相合并（会导致依赖混乱）

---

## 并行开发轨道

完成 `feat/foundation` 后，以下 4 个轨道可并行：

| 轨道 | 分支 | 依赖 | 产出 |
|------|------|------|------|
| **Foundation** | `feat/foundation` | 无 | 多租户框架 + 核心引擎 + API scaffold |
| **Admin SPA** | `feat/admin-spa` | Foundation API 就绪 | 管理端 React 应用 → 详见 `SESSION_ADMIN_SPA.md` |
| **Mini-App** | `feat/mini-app` | Foundation API 就绪 | uni-app 小程序 → 详见 `SESSION_MINI_APP.md` |
| **Analytics** | `feat/analytics` | Foundation API 就绪 | 增值分析模块 → 详见 `SESSION_ANALYTICS.md` |
| **Data Onboarding** | `feat/data-onboarding` | Foundation 数据模型 | 数据接入管道 → 详见 `SESSION_DATA_ONBOARDING.md` |

**轨道启动条件**: Foundation 轨道的 API scaffold（Phase 1 Week 5）完成后，其他轨道即可启动。

---

## Session 启动清单

每个新 session 开始前：

1. [ ] 阅读本文件（COLLABORATION.md）
2. [ ] 阅读 `CONVENTIONS.md`
3. [ ] 阅读你的轨道专属 Session 文档（`SESSION_ADMIN_SPA.md` 或 `SESSION_MINI_APP.md`）
4. [ ] 阅读 `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` 中相关章节
5. [ ] `git fetch origin && git checkout <你的分支>`
6. [ ] 检查 `SESSION_STATE.md` 确认你的轨道没有冲突
7. [ ] 开始工作前更新 `SESSION_STATE.md` 标记你的轨道为 `active`

---

## Session 间通信

### 阻塞/依赖通知

如果一个轨道需要另一个轨道产出但尚未完成：

1. 在 `SESSION_STATE.md` 的"阻塞队列"添加条目
2. 在对应轨道的工作分支上 `git log` 确认最新进度
3. 如果紧急：在 develop 分支上先提交 interface/stub 供其他轨道使用

### 接口契约

所有轨道间的接口契约定义在 `CONVENTIONS.md` 的"API 契约"部分。**修改跨轨道接口必须先更新契约文档再提交代码。**

---

## 每日同步

每个 session 结束前更新 `SESSION_STATE.md`：

- 今天完成了什么（任务编号）
- 有什么 blocker
- 接下来要做什么

---

## 目录约定

```
gaokao_agents/
├── COLLABORATION.md          # 本文件
├── CONVENTIONS.md             # 代码规范 + API 契约
├── SESSION_STATE.md           # 实时状态跟踪（高频更新）
├── backend/                   # Python 后端（新目录结构见设计文档 §4）
├── admin-spa/                 # 🔴 新增：管理端 React SPA
├── mini-app/                  # 🔴 新增：uni-app 小程序
├── scrapers/                  # 数据采集管道（保留）
├── docs/
│   └── superpowers/
│       ├── specs/             # 设计文档
│       └── plans/             # 实施计划
└── docker/                    # Docker 配置
```
