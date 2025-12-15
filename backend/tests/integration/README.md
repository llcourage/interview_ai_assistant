# Integration Tests

集成测试使用本地 Docker 环境（Postgres + PostgREST）来模拟 Supabase，完全隔离，不会连接到真实 Supabase。

## 文件说明

- `conftest.py`: pytest fixtures，处理 Docker Compose 生命周期和环境变量
- `test_db_smoke.py`: 基础 smoke test，验证数据库读写
- `test_schema.sql`: 测试专用的数据库 schema（移除了外键约束和 RLS）
- `nginx.test.conf`: Nginx 配置，将 Supabase API 请求代理到 PostgREST
- `BUILD.bazel`: Bazel 测试配置

## 运行测试

### 前置要求

1. Docker 和 Docker Compose 已安装
2. pytest 已安装（在 Python 环境中或通过 pip_parse）

### 运行方式

```bash
# 使用 Bazel 运行
bazel test //backend/tests/integration:integration_tests --test_output=streamed

# 或直接使用 pytest（需要先启动 Docker Compose）
docker compose -f docker-compose.test.yml up -d
pytest backend/tests/integration/
docker compose -f docker-compose.test.yml down -v
```

## 环境变量

测试会自动设置以下环境变量（在 `conftest.py` 中）：

- `SUPABASE_URL=http://localhost:54321` (本地 Nginx 代理)
- `SUPABASE_SERVICE_ROLE_KEY=test-service-role-key`
- `SUPABASE_ANON_KEY=test-anon-key`
- `STRIPE_SECRET_KEY=sk_test_mock_key`
- `STRIPE_WEBHOOK_SECRET=whsec_test_mock_secret`

## 验证不会连接真实 Supabase

测试环境变量强制设置为 `http://localhost:54321`，确保只会连接到本地 Docker 服务，不会连接到真实的 Supabase 项目。


