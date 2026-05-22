# 发布检查清单

## 发布前

- 确认 `npm run build` 通过。
- 确认 `docker compose -f docker-compose.prod.yml config` 通过。
- 确认 `.env` 已替换强密码和强 `SECRET_KEY`。
- 确认 `ALLOWED_ORIGINS` 是实际访问地址。
- 确认 `NAS_HOST_PATH` 指向飞牛上的真实图片目录。
- 备份数据库和图片目录。

## 不进入发布包的内容

- `frontend_admin/node_modules`
- `frontend_admin/dist`
- `__pycache__`
- `.pytest_cache`
- `*.log`
- `nas_mock_data`
- `test_photos`
- 本地 `.env`

## 发布后

- 登录后台并修改默认管理员密码。
- 创建一个测试项目，上传或导入一张图片。
- 检查图片预览、客户审核链接、最终交付链接。
- 检查素材中心上传、快速分类、下载。
- 检查 `docker compose -f docker-compose.prod.yml logs web` 没有持续错误。

## 回滚

1. 停止服务。
2. 恢复上一版发布包。
3. 恢复数据库备份。
4. 恢复图片目录备份。
5. 重新启动服务。
