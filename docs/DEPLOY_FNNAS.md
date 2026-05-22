# 飞牛 Docker 部署说明

本文档用于把当前项目部署到飞牛 NAS 的 Docker/Compose 环境。

## 1. 准备目录

建议在飞牛上准备两个目录：

```text
/vol1/docker/yixuan
/vol1/docker/yixuan/nas_data
```

`/vol1/docker/yixuan` 放项目发布包内容，`nas_data` 放图片、素材、审核标注和交付文件。

## 2. 准备环境变量

复制 `.env.production.template` 为 `.env`，重点修改：

```env
POSTGRES_PASSWORD=强数据库密码
DATABASE_URL=postgresql+asyncpg://photo_user:强数据库密码@db:5432/photo_tracker
NAS_HOST_PATH=/vol1/docker/yixuan/nas_data
SECRET_KEY=强随机字符串
ALLOWED_ORIGINS=http://飞牛IP:15173
FRONTEND_PORT=15173
```

`SECRET_KEY` 可以这样生成：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 3. 启动服务

在项目目录执行：

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

后端容器启动时会自动执行 Alembic 迁移。也可以手动确认：

```bash
docker compose -f docker-compose.prod.yml exec web alembic current
docker compose -f docker-compose.prod.yml exec web alembic upgrade head
```

## 4. 首次登录

浏览器打开：

```text
http://飞牛IP:15173
```

默认账号：

```text
admin / adminadmin
```

上线后必须第一时间修改默认密码。

## 5. 备份与恢复

备份：

```bash
. ./.env
sh scripts/backup_db.sh
```

恢复会覆盖当前数据库，必须显式确认：

```bash
. ./.env
RESTORE_CONFIRM=YES sh scripts/restore_db.sh backups/yixuan_db_YYYYMMDD_HHMMSS.dump
```

图片文件不在数据库备份中，需要同步备份 `NAS_HOST_PATH` 指向的目录。

## 6. 升级步骤

1. 先执行数据库备份。
2. 备份 `NAS_HOST_PATH` 图片目录。
3. 上传新的发布包覆盖项目代码。
4. 执行 `docker compose -f docker-compose.prod.yml up -d --build`。
5. 检查 `web` 健康状态和前端页面。

## 7. 常见检查

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f frontend
```

如果图片无法显示，优先检查 `.env` 里的 `NAS_HOST_PATH` 是否存在，且容器内 `/mnt/nas_data` 能访问到真实图片。
