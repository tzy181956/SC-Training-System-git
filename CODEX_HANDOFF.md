# CODEX_HANDOFF

## 2026-05-16 接手补充

接手当前 `服务器端` 分支时，除常规 build、compileall 和文本编码检查外，建议直接执行完整本地基线检查：

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\check_fk_orphans.py
.\.venv\Scripts\python.exe scripts\migrate_db.py ensure
.\.venv\Scripts\python.exe scripts\backend_check.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe ..\scripts\check_text_encoding.py

cd ..\frontend
npm ci
npm run build
npm run test:e2e
```

当前已落地训练端离线草稿 Playwright E2E，覆盖正常完成、断网 pending、刷新恢复和恢复同步。每次涉及训练端同步、本地草稿、session 状态或训练模式打开计划流程的改动，都应优先运行 `npm run test:e2e`。

不要把以下运行时或数据文件提交到 Git：

- `backend/training.db`
- `backend/backups/`
- `backend/tmp_e2e_training_offline_draft.db*`
- `frontend/test-results/`
- `frontend/playwright-report/`
- `frontend/blob-report/`
- `logs/`
- `.env`、数据库备份、截图、视频、trace、临时测试产物

长任务结束时建议输出阶段交接信息，至少包含当前分支、最新 commit、验证命令结果、剩余风险和下一步建议，方便新会话接手。

最终报告中不要输出裸的内部指令格式，例如 `cwd="..." branch="..."` 这类内容；路径和分支状态应放在代码块里或用普通中文说明，避免 Codex Desktop 渲染异常。

## 项目是什么

这是一个面向体能训练管理、训练执行、测试数据管理和监控分析的 Web 平台。

当前系统已包含：

- 登录与账号管理
- 管理模式
- 训练模式
- 实时监控模式
- 动作库
- 训练模板与计划分配
- 测试数据与测试评分
- 日志与备份恢复

## 当前技术结构

- 前端：Vue 3
- 后端：FastAPI
- 数据库：SQLite
- ORM：SQLAlchemy
- 图表：ECharts
- 迁移：Alembic + `backend/scripts/migrate_db.py`

## 当前运行形态

项目当前采用“两套环境并行”：

- 本地开发环境：Windows + `scripts/start_system.bat`
- 服务器运行环境：Ubuntu + Nginx + systemd + SQLite

代码通过 GitHub 同步，生产数据不通过 GitHub 同步。

## 当前权限与模式

系统当前为登录制。

主角色：

- `admin`
- `coach`

主模式：

- 管理模式
- 训练模式
- 实时监控模式

## 当前重点模块

- 动作库管理
- 训练模板管理
- 计划分配
- 训练执行与本地草稿/同步
- 训练报告与训练负荷
- 测试类型/测试项目主数据
- 测试数据总库
- 测试评分与雷达图
- 监控端
- 备份恢复与日志

## 当前数据库与迁移

当前正式数据库演进路径是：

- Alembic migration
- `backend/scripts/migrate_db.py ensure`

不要再把以下内容当成正式主方案：

- `backend/app/core/schema_sync.py`
- 仅靠 `init_db.py` 补表补字段

## 当前主要风险

- 大数据页面需要持续控制首屏体积和查询体量
- 训练端本地草稿仍是浏览器本机恢复能力，不是跨设备同步
- 文档体系此前残留旧口径，接手前要优先看当前权威文档
- 当前工作区可能存在未完成功能分支改动，不应自动写进权威文档

## 接手时先看什么

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `CURRENT_STATUS.md`
4. `DEVELOPMENT_GUIDE.md`
5. `NEXT_STEPS.md`
6. `docs/deployment/tencent-lighthouse-ubuntu.md`
7. `docs/phase1-database-migrations.md`

## 接手时先做什么

1. 看 `git status`
2. 区分哪些改动是当前未完成功能、哪些是文档/日志/运行产物
3. 跑最小检查：

```powershell
cd frontend
npm run build
cd ..
backend\.venv\Scripts\python.exe -m compileall backend\app
python scripts/check_text_encoding.py
```

4. 再决定本轮是修代码、修文档、做迁移还是做部署维护

## 明确约束

- 不要破坏生产部署链路
- 不要把生产数据库或备份带回 Git
- 不要把旧文档当成真实实现来源
- 每轮实际改动都要同步 `CHANGELOG.md`
- 如果发现文档口径再次落后于代码，优先修文档
