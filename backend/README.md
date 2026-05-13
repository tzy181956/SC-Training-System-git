# 后端说明

## 技术栈

- FastAPI
- SQLAlchemy
- SQLite

## 环境要求

- Python `3.12.x`

不要使用 Python `3.14`。当前依赖栈在 Windows 下会触发 `pydantic-core` 源码构建，额外引入 Rust 与编译工具要求，不适合当前项目。

## 推荐启动方式

优先使用项目根目录脚本：

- `scripts/start_system.bat`

这个脚本会负责：

- 环境检查
- 缺失依赖时触发初始化
- 启动前后端

## 手动启动方式

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 数据库说明

开发环境数据库位于：

- `backend/training.db`

当前数据库演进方式已经开始切换为：

- 正式迁移基线：`backend/alembic/`
- 迁移入口脚本：`backend/scripts/migrate_db.py`
- 初始化入口：`backend/scripts/init_db.py`

运行时 `backend/app/core/schema_sync.py` 目前仍保留为过渡期兜底，但不再作为长期正式迁移方案。
它当前只应用于开发环境启动兜底；`APP_ENV=production` 启动时不会自动改表，生产数据库结构必须通过 Alembic + `backend/scripts/migrate_db.py` 管理。
对已有历史库的正式接管应优先通过 `backend/scripts/migrate_db.py` 完成；`bootstrap` 会先标记 Alembic 基线，再补跑后续 revisions，避免把缺失迁移直接“盖过去”。

推荐命令：

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\migrate_db.py bootstrap
```

迁移规划、顺序、回退与第一阶段拟新增表/字段说明见：

- `docs/phase1-database-migrations.md`

## 真实数据导入

真实测试数据导入脚本：

- `backend/scripts/import_real_test_data.py`

特点：

- 默认读取 OneDrive 中的真实测试 Excel
- 支持命令行参数和环境变量覆盖 Excel 路径
- 执行前必须输入固定确认词
- 会清理：
  - 运动员
  - 测试记录
  - 计划分配
  - training sessions
  - 组记录
- 会保留：
  - 训练模板
  - 动作库

手动执行：

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\import_real_test_data.py
```

指定文件：

```powershell
set REAL_TEST_DATA_XLSX=C:\path\to\测试结果.xlsx
.\.venv\Scripts\python.exe scripts\import_real_test_data.py
```

## 上传前检查

```powershell
backend\.venv\Scripts\python.exe -m compileall backend\app
backend\.venv\Scripts\python.exe -m py_compile backend\scripts\import_real_test_data.py
python scripts\check_text_encoding.py
```

## Git 与数据库协作

- 本地开发数据库不通过 Git 同步
- 生产数据库不通过 Git 同步
- 生产数据库以 `/opt/sc-training-system-data/training.db` 为唯一真实数据源
- 数据同步应通过数据库备份、导入导出或后续专门迁移工具完成
- GitHub 只同步代码和文档，不同步运行时数据库
- SQLite 不适合多人同时修改同一份数据库文件；生产环境以服务器上的数据库为准

## 中文与编码注意事项

- 后端脚本中的中文字段名不能随意改动，特别是 Excel 表头映射
- 如果怀疑中文乱码，不要只看 PowerShell 输出
- 优先用编辑器或 Python UTF-8 读取验证文件内容
- 乱码检查说明见：
  - `docs/text-encoding.md`

## 生产环境配置（development / production）

- 默认 `APP_ENV=development`，本地开发在没有 `backend/.env` 的情况下仍可继续使用：
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
  - 默认 SQLite：`backend/training.db`
- 部署到 Ubuntu 等生产环境时，请手动创建 `backend/.env`，至少显式配置：
  - `APP_ENV=production`
  - `SECRET_KEY`
  - `DATABASE_URL`
  - `CORS_ORIGINS`
- 生产环境如果缺少上述变量，或 `SECRET_KEY` 仍是 `dev-secret-key-change-me`，后端会在启动时直接失败，不再依赖代码里的开发默认值裸跑。
- `CORS_ORIGIN_REGEX` 可以保留为空；除非你明确知道风险，否则不要在生产环境使用宽泛正则。

生产环境最小示例：

```dotenv
APP_ENV=production
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/sc-training-system-data/training.db
CORS_ORIGINS=["https://your-domain.example"]
CORS_ORIGIN_REGEX=
```

## systemd 后端服务模板

项目已提供 systemd 后端服务模板：

- `deploy/sc-training-backend.service`

默认部署路径约定：

- 项目：`/opt/sc-training-system`
- 后端：`/opt/sc-training-system/backend`
- 虚拟环境：`/opt/sc-training-system/backend/.venv`
- 后端监听：`127.0.0.1:8000`

如果你的部署路径不同，请同步修改 service 文件中的：

- `WorkingDirectory`
- `EnvironmentFile`
- `ExecStart`

常用命令：

```bash
sudo cp deploy/sc-training-backend.service /etc/systemd/system/sc-training-backend.service
sudo systemctl daemon-reload
sudo systemctl enable sc-training-backend
sudo systemctl start sc-training-backend
sudo systemctl status sc-training-backend
journalctl -u sc-training-backend -f
sudo systemctl restart sc-training-backend
curl http://127.0.0.1:8000/health
```

说明：

- service 使用 `backend/.env` 作为 `EnvironmentFile`
- 启动命令不使用 `--reload`
- 启动命令不使用多 worker
- 该模板只监听 `127.0.0.1:8000`，用于交给 Nginx 在本机反向代理
- 如果 `APP_ENV=production` 但 `.env` 缺少 `SECRET_KEY`、`DATABASE_URL` 或 `CORS_ORIGINS`，后端会在启动时直接失败

## Nginx 同域反代模板

项目已提供 Nginx 配置模板：

- `deploy/nginx-sc-training.conf`

用途：

- Nginx 对外监听 `80`
- 前端静态文件目录：`/opt/sc-training-system/frontend/dist`
- `/api/` 回源到 `http://127.0.0.1:8000/api/`
- `/health` 回源到 `http://127.0.0.1:8000/health`
- Vue Router 使用 history fallback

常用命令：

```bash
sudo cp deploy/nginx-sc-training.conf /etc/nginx/sites-available/sc-training
sudo ln -s /etc/nginx/sites-available/sc-training /etc/nginx/sites-enabled/sc-training
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status nginx
curl http://127.0.0.1/health
curl http://127.0.0.1/
```

说明：

- 模板默认 `server_name _;`，有正式域名后再改成真实域名
- 当前模板不包含 HTTPS，HTTPS 后续单独配置
- `8000` 只供 Nginx 本机回源，不应直接开放到公网
