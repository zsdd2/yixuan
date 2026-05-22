# 404 错误快速修复指南

## 问题诊断

根据截图，三个功能都报 404 错误：
1. 基础设置 - GET `/api/v1/system/configs/external_share_url`
2. 生成链接 - POST `/api/v1/reviews/create`
3. 下载选中 - GET `/api/v1/projects/{id}/photos/download`

## 根本原因

**后端服务没有重启**，新添加的代码没有生效。

## 解决方案

### 方案1：Docker 环境（推荐）

```bash
# 1. 重启后端容器
docker-compose restart web

# 2. 查看日志确认启动成功
docker-compose logs -f web

# 看到以下输出表示成功：
# [OK] Database tables ready
# [OK] Seed data ready
```

### 方案2：本地开发环境

```bash
# 1. 停止当前运行的后端进程
# Windows: 在任务管理器中结束 python.exe 进程（PID 29180）
# 或者在命令行：
taskkill /F /PID 29180

# 2. 重新启动后端
cd f:\yixuan
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 看到以下输出表示成功：
# INFO:     Uvicorn running on http://0.0.0.0:8000
# [OK] Database tables ready
# [OK] Seed data ready
```

### 方案3：验证接口是否生效

启动后端后，在浏览器访问：

```
http://localhost:8000/docs
```

检查以下接口是否存在：
- ✅ GET `/api/v1/system/configs/{config_key}` - 新添加的接口
- ✅ POST `/api/v1/reviews/create` - 应该已存在
- ✅ GET `/api/v1/projects/{project_id}/photos/download` - 应该已存在

## 前端问题修复

前端有 TypeScript 编译错误，但不影响开发模式运行。如需修复：

```bash
cd frontend_admin

# 开发模式（推荐，支持热更新）
npm run dev

# 或者生产构建（需要先修复 TS 错误）
npm run build
```

## 验证步骤

### 1. 验证基础设置
1. 打开设置中心
2. 应该能看到"基础设置" Tab
3. 输入外网链接并保存
4. 刷新页面，配置应该保留

### 2. 验证分享审核
1. 进入项目详情
2. 点击"分享审核"按钮
3. 选择照片
4. 点击"生成链接"
5. 应该成功生成分享链接

### 3. 验证批量下载
1. 进入最终交付图页面
2. 勾选照片
3. 点击"下载选中"
4. 应该成功下载 ZIP 文件

## 常见问题

### Q1: 重启后还是 404
**A**: 检查端口是否被占用
```bash
# Windows
netstat -ano | findstr :8000

# 如果端口被占用，结束进程
taskkill /F /PID <PID>
```

### Q2: 前端无法连接后端
**A**: 检查 CORS 配置
- 确保前端运行在 `http://localhost:15173`
- 确保后端 CORS 允许该域名（已配置）

### Q3: 数据库连接失败
**A**: 检查 PostgreSQL 是否运行
```bash
# Docker 环境
docker-compose ps

# 应该看到 db 容器状态为 Up
```

## 修改文件清单

本次修复涉及以下文件：

```
app/routers/system.py                                (新增 GET /configs/{config_key})
app/routers/projects.py                              (修正字段名 + 安全加固)
frontend_admin/src/views/SettingsCenter.vue          (增加错误处理)
frontend_admin/src/components/ShareReviewModal.vue   (增加错误处理)
frontend_admin/src/components/ProjectDelivery.vue    (增加错误处理)
```

## 技术支持

如果问题仍未解决，请提供：
1. 后端启动日志（前20行）
2. 浏览器控制台完整错误信息
3. 访问 http://localhost:8000/docs 的截图
