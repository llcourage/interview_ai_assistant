# Integration Test Setup - 完成清单

## ✅ 已创建的文件

1. **docker-compose.test.yml** (项目根目录)
   - 配置了 Postgres、PostgREST 和 Nginx 代理
   - 端口映射：54321 (Supabase API), 54322 (Postgres)

2. **backend/tests/integration/nginx.test.conf**
   - Nginx 配置，将 `/rest/v1/` 请求代理到 PostgREST

3. **backend/tests/integration/test_schema.sql**
   - 测试专用的数据库 schema
   - 移除了外键约束和 RLS（测试环境不需要）

4. **backend/tests/integration/conftest.py**
   - pytest fixtures
   - 自动启动/停止 Docker Compose
   - 设置测试环境变量

5. **backend/tests/integration/test_db_smoke.py**
   - 基础 smoke test
   - 验证数据库读写操作

6. **backend/tests/integration/BUILD.bazel**
   - Bazel 测试配置

## 🚀 下一步：运行测试

### 方式 1: 使用 Bazel（推荐）

```bash
# 确保 pytest 已安装（在系统 Python 或通过 pip_parse）
# 如果使用 pip_parse，需要在 MODULE.bazel 中配置

bazel test //backend/tests/integration:integration_tests --test_output=streamed
```

### 方式 2: 直接使用 pytest

```bash
# 1. 启动 Docker Compose
docker compose -f docker-compose.test.yml up -d

# 2. 等待服务就绪（约 5 秒）
# 3. 运行测试
pytest backend/tests/integration/

# 4. 停止 Docker Compose
docker compose -f docker-compose.test.yml down -v
```

## ⚠️ 注意事项

1. **pytest 依赖**: 如果 Bazel 报错找不到 pytest，需要：
   - 在系统 Python 环境中安装：`pip install pytest pytest-asyncio`
   - 或配置 pip_parse（见下方）

2. **Docker 必须运行**: 测试需要 Docker 和 Docker Compose

3. **端口冲突**: 确保 54321 和 54322 端口未被占用

## 📝 配置 pip_parse（可选）

如果要在 Bazel 中使用 `@pypi//pytest`，需要在 `MODULE.bazel` 中添加：

```python
pip = use_extension("@rules_python//python/extensions:pip.bzl", "pip")
pip.parse(
    name = "pypi",
    requirements_lock = "//:requirements_lock.txt",
)
use_repo(pip, "pypi")
```

然后生成 `requirements_lock.txt`。

## ✅ 验证测试环境

运行 smoke test 成功后，你会看到：

```
✅ Docker compose started
⏳ Waiting for services to be ready...
test_supabase_admin_can_write_user_plans PASSED
🧹 Stopping docker compose...
```

## 🔒 安全确认

测试环境变量强制设置为 `http://localhost:54321`，**绝对不会**连接到真实的 Supabase 项目。


