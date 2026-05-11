# CODEX_HANDOFF

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
