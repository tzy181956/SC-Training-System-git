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

当前数据库演进方式：

- 初始化脚本：`backend/scripts/init_db.py`
- 运行时补列 / 删列：`backend/app/core/schema_sync.py`

目前还没有正式迁移框架（如 Alembic），所以改模型时要特别注意：

- 现有数据库如何升级
- `schema_sync.py` 是否需要同步处理

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

- `backend/training.db` 已纳入 Git 跟踪
- 需要跨电脑同步数据时，应提交数据库文件
- SQLite 不适合多人同时改同一份库；如发生并行修改，需要手工决定保留哪一份数据库变更

## 中文与编码注意事项

- 后端脚本中的中文字段名不能随意改动，特别是 Excel 表头映射
- 如果怀疑中文乱码，不要只看 PowerShell 输出
- 优先用编辑器或 Python UTF-8 读取验证文件内容
- 乱码检查说明见：
  - `docs/text-encoding.md`
