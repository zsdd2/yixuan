# ArtSelect V5.0 认证与权限系统指南

> **创建日期：** 2026-04-24  
> **版本：** 1.0  
> **状态：** 已完成并测试通过

---

## 📋 系统概述

ArtSelect V5.0 已成功集成完整的用户认证与基于角色的访问控制（RBAC）系统，实现了多租户隔离和细粒度权限管理。

---

## 🔐 核心功能

### 1. 用户认证
- **JWT Token 认证**：基于 Bearer Token 的无状态认证
- **密码安全**：使用 bcrypt 哈希算法（成本因子 12）
- **Token 有效期**：7 天（可配置）
- **密码修改**：需验证旧密码，防止会话劫持

### 2. 角色权限体系（RBAC）

| 角色 | 权限范围 | 说明 |
|------|---------|------|
| **super_admin** | 全局所有权限 | 系统超级管理员，可管理所有用户和项目 |
| **admin** | 全局所有权限 | 管理员，可管理所有用户和项目 |
| **staff** | 自己创建的项目 | 员工（摄影师/修图师），只能访问自己创建的项目 |
| **client** | customer_id = 自己的项目 | 客户，只能访问分配给自己的项目 |

### 3. 数据可见性隔离

**项目列表（GET /api/v1/projects）：**
- `super_admin` / `admin`：查看所有项目
- `staff`：查看 `created_by = 自己` 的项目
- `client`：查看 `customer_id = 自己` 的项目

**项目照片（GET /api/v1/projects/{id}/photos）：**
- `super_admin` / `admin`：访问所有项目的照片
- `staff`：仅访问自己创建的项目照片
- `client`：仅访问 `customer_id = 自己` 的项目照片

---

## 🚀 快速开始

### 初始管理员账号

系统启动时自动创建超级管理员账号：

```
用户名：admin
密码：adminadmin
角色：super_admin
```

**⚠️ 重要：** 首次登录后请立即修改密码！

### 登录流程

**1. 调用登录接口**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"adminadmin"}'
```

**响应示例：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "admin",
  "display_name": "超级管理员",
  "role": "super_admin"
}
```

**2. 使用 Token 访问受保护接口**

```bash
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <access_token>"
```

---

## 📡 API 接口清单

### 认证接口（/api/v1/auth）

| Method | 路径 | 说明 | 权限 |
|--------|------|------|------|
| POST | `/login` | 用户登录 | 公开 |
| GET | `/me` | 获取当前用户信息 | 需认证 |
| PUT | `/me/password` | 修改当前用户密码 | 需认证 |

### 用户管理接口（/api/v1/users）

| Method | 路径 | 说明 | 权限 |
|--------|------|------|------|
| GET | `/` | 用户列表 | admin+ |
| POST | `/` | 创建用户 | admin+ |
| GET | `/{id}` | 用户详情 | admin+ |
| PATCH | `/{id}` | 更新用户（角色/状态） | admin+ |
| DELETE | `/{id}` | 删除用户 | admin+ |

---

## 🗄️ 数据库模型变更

### User 表增强

```sql
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(255);
```

**新增字段：**
- `last_login_at`：最后登录时间（用于审计）

**角色枚举扩展：**
```python
class UserRole(str, enum.Enum):
    super_admin = "super_admin"  # 新增
    admin = "admin"
    staff = "staff"
    client = "client"
```

### Project 表增强

```sql
ALTER TABLE projects ADD COLUMN customer_id BIGINT REFERENCES users(id) ON DELETE SET NULL;
```

**新增字段：**
- `customer_id`：关联客户用户账号（role=client），用于客户权限隔离

**关系映射：**
- `creator`：项目创建者（User.projects_created）
- `customer`：项目客户（User.projects_as_customer）

---

## 🔧 技术实现细节

### 1. 认证核心模块（app/auth.py）

```python
from jose import jwt
from passlib.context import CryptContext

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
```

**核心函数：**
- `verify_password(plain, hashed)`：验证密码
- `get_password_hash(password)`：生成密码哈希
- `create_access_token(data)`：生成 JWT Token
- `decode_access_token(token)`：解码 JWT Token

### 2. 依赖注入（app/deps.py）

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT Token 中解析当前用户"""
    token = credentials.credentials
    payload = decode_access_token(token)
    # ... 验证逻辑
    return user
```

**快捷类型别名：**
```python
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_roles(UserRole.super_admin, UserRole.admin))]
SuperAdminUser = Annotated[User, Depends(require_roles(UserRole.super_admin))]
```

### 3. 权限拦截示例

```python
@router.get("/api/v1/projects")
async def list_projects(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    base_where = []
    
    # RBAC 权限过滤
    if current_user.role == UserRole.client:
        base_where.append(Project.customer_id == current_user.id)
    elif current_user.role == UserRole.staff:
        base_where.append(Project.created_by == current_user.id)
    # super_admin 和 admin 无需过滤
    
    # ... 查询逻辑
```

---

## 📦 依赖包清单

```txt
# 认证与安全
passlib[bcrypt]==1.7.4
bcrypt==3.2.2              # 必须 <4.0.0，兼容 passlib
python-jose[cryptography]==3.3.0
```

**⚠️ 重要：** bcrypt 必须使用 3.x 版本，5.x 版本与 passlib 不兼容。

---

## 🧪 测试验证

### 1. 登录测试

```bash
# 成功登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"adminadmin"}'

# 预期响应：200 OK + JWT Token
```

### 2. 获取当前用户信息

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <token>"

# 预期响应：
# {"user_id":1,"username":"admin","display_name":"超级管理员","role":"super_admin","is_active":true}
```

### 3. 权限拦截测试

```bash
# 未认证访问（应返回 401）
curl -X GET http://localhost:8000/api/v1/projects

# 已认证访问（应返回 200）
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer <token>"
```

---

## 🔄 数据库重置流程

```bash
# 1. 重置数据库（会清空所有数据）
python reset_db.py

# 2. 重启后端容器
docker-compose restart web

# 3. 验证超级管理员账号
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"adminadmin"}'
```

---

## 🛡️ 安全最佳实践

### 1. 生产环境配置

**修改 JWT 密钥：**
```python
# app/auth.py
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "fallback-key")
```

**环境变量：**
```bash
# .env
JWT_SECRET_KEY=your-production-secret-key-here
ACCESS_TOKEN_EXPIRE_DAYS=7
```

### 2. 密码策略

- **最小长度**：6 位（建议生产环境提高到 8-12 位）
- **哈希算法**：bcrypt（成本因子 12）
- **修改密码**：必须验证旧密码

### 3. Token 管理

- **存储位置**：前端存储在 LocalStorage 或 Pinia
- **传输方式**：HTTP Header `Authorization: Bearer <token>`
- **过期处理**：前端检测 401 错误，跳转登录页

---

## 📝 后续开发建议

### 1. 前端集成

**登录页面（LoginView.vue）：**
```vue
<script setup>
import { ref } from 'vue'
import axios from 'axios'

const username = ref('')
const password = ref('')

async function handleLogin() {
  const { data } = await axios.post('/api/v1/auth/login', {
    username: username.value,
    password: password.value
  })
  
  // 存储 Token
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('user_info', JSON.stringify(data))
  
  // 跳转到工作台
  router.push('/dashboard')
}
</script>
```

**Axios 拦截器：**
```javascript
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token 过期，跳转登录页
      localStorage.removeItem('access_token')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)
```

**路由守卫：**
```javascript
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})
```

### 2. 权限管理界面

**用户列表页面：**
- 显示所有用户（用户名、角色、状态、最后登录时间）
- 支持搜索、筛选（按角色、激活状态）
- 支持修改角色、禁用/启用用户

**角色权限说明：**
- 在设置中心增加『角色权限』说明文档
- 展示各角色的权限范围和数据可见性

### 3. 审计日志

**建议增加：**
- 登录日志（成功/失败、IP 地址、时间）
- 操作日志（创建/修改/删除项目、用户管理）
- 敏感操作记录（修改密码、角色变更）

---

## 🐛 常见问题排查

### 1. 登录失败（401 Unauthorized）

**原因：**
- 用户名或密码错误
- 用户被禁用（`is_active = false`）

**排查：**
```sql
SELECT id, username, role, is_active FROM users WHERE username = 'admin';
```

### 2. Token 验证失败（401 Unauthorized）

**原因：**
- Token 格式错误（缺少 `Bearer` 前缀）
- Token 已过期
- JWT 密钥不匹配

**排查：**
```bash
# 检查 Token 格式
curl -v http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <token>"

# 查看详细错误日志
docker-compose logs web --tail=50
```

### 3. 权限不足（403 Forbidden）

**原因：**
- 当前用户角色不满足接口要求
- 客户尝试访问非自己的项目

**排查：**
```python
# 检查用户角色
print(f"User: {current_user.username}, Role: {current_user.role}")

# 检查项目归属
print(f"Project customer_id: {project.customer_id}, User ID: {current_user.id}")
```

---

## 📚 相关文档

- [API_REGISTRY.md](./API_REGISTRY.md) — API 接口台账（已更新认证接口）
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) — 开发者指南
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 系统架构文档

---

**文档版本：** 1.0  
**最后更新：** 2026-04-24  
**维护者：** 开发团队
