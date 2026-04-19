# 后端说明

后端技术栈：

- FastAPI
- SQLAlchemy
- SQLite

## 环境要求

- Python `3.12.x`

不要使用 Python `3.14`。当前依赖栈在 Windows 下会触发 `pydantic-core` 源码构建，增加 Rust 和编译工具要求，不适合当前项目。

## 手动启动方式

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe scripts\seed_demo.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 推荐方式

优先使用项目根目录的脚本：

- `scripts/start_system.bat`

如果环境缺失，它会自动调用初始化脚本。

## 数据库说明

开发环境数据库位于：

- `backend/training.db`

当前初始化脚本是面向开发环境的，会重建数据库并导入示例数据。

## 上传前检查

```powershell
python -m compileall backend\app
```
