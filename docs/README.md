# 文档导航中心

最后更新：2026-05-21

本目录用于把项目文档从“全部通读”整理为“按任务导航”。开发前仍以根目录 `kf01.md` 为入口，但实际查找时优先按下面场景进入对应文档。

## 30 秒定位

| 我要做什么 | 先读哪份文档 | 继续查哪里 |
| --- | --- | --- |
| 新功能、修 Bug、重构 | `../kf01.md` | `STANDARDS.md` |
| 判断页面属于哪个业务流程 | `PAGE_BUSINESS_FLOW.md` | `../ARCHITECTURE.md` |
| 查接口路径、认证、响应结构 | `API_NAVIGATION.md` | `../API_REGISTRY.md` |
| 接手当前项目现状 | `AUDIT_2026-05-21.md` | `PAGE_BUSINESS_FLOW.md` |
| 改数据库模型或状态枚举 | `STANDARDS.md` | `../ARCHITECTURE.md`、`../app/alembic/versions/` |
| 改客户审核/交付外链 | `PAGE_BUSINESS_FLOW.md` | `../app/routers/reviews.py`、`../app/routers/deliveries.py` |
| 排查 404 或登录问题 | `API_NAVIGATION.md` | `../frontend_admin/src/stores/userStore.ts`、`../frontend_admin/vite.config.ts` |

## 文档分类

### 1. 入口与规范

- `../kf01.md`：开发前置规则，保留为所有任务入口。
- `STANDARDS.md`：可执行开发规范，按后端、前端、API、数据、测试分类。

### 2. 系统地图

- `PAGE_BUSINESS_FLOW.md`：页面、路由、组件、API、业务动作的对应关系。
- `API_NAVIGATION.md`：接口分组索引和前端调用入口。
- `../ARCHITECTURE.md`：系统架构全量说明。
- `../API_REGISTRY.md`：接口台账全量说明。

### 3. 审计记录

- `AUDIT_2026-05-21.md`：本次页面与业务流程审计结果。
- 根目录 `AUDIT_REPORT*.md`、`BUGFIX*.md`：历史审计和修复记录，作为追溯资料，不作为日常入口。

## 推荐阅读路径

1. 先读 `../kf01.md` 的“任务导航”。
2. 根据任务进入 `PAGE_BUSINESS_FLOW.md` 或 `API_NAVIGATION.md`。
3. 需要规则细节时读 `STANDARDS.md`。
4. 只有涉及架构、状态机、接口签名时再打开 `../ARCHITECTURE.md` 或 `../API_REGISTRY.md` 的对应章节。

