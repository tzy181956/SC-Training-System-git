# 体能训练管理平台

这是一个面向体能教练、运动队训练执行与测试分析的 Web 平台。系统当前采用“服务器运行 + 本地开发并行”的形态，核心目标是让教练可以稳定完成：

- 运动员与队伍管理
- 动作库维护
- 训练模板配置
- 计划分配
- 训练执行与训练回看
- 测试数据导入、补录、筛选、删除与导出
- 测试评分与雷达图分析
- 监控端查看当天训练状态
- 日志、备份与账号管理

## 当前产品形态

当前系统是一个已经具备服务器部署形态的训练管理系统。

- 前端：Vue 3
- 后端：FastAPI
- 数据库：SQLite
- ORM：SQLAlchemy
- 图表：ECharts
- 数据迁移：Alembic + `backend/scripts/migrate_db.py`

当前运行形态分为两套环境：

- 本地开发环境：Windows + `scripts/start_system.bat` / `scripts/init_system.bat`
- 服务器运行环境：Ubuntu + Nginx + systemd + SQLite + 同域 `/api`

## 当前访问与权限

系统当前为登录制。

- `admin`
  - 可访问管理、训练、监控、日志、备份、账号管理等完整能力
- `coach`
  - 可访问管理、训练、监控、测试评分等业务能力

当前前端包含三类模式入口：

- 管理模式
- 训练模式
- 实时监控模式

## 核心模块

- 运动员与队伍管理
- 动作库与动作分类树
- 训练模板与模板动作项
- 计划分配与计划概览
- 训练执行、组记录、本地草稿与同步状态
- 训练报告与训练负荷
- 测试类型/测试项目主数据
- 测试数据总库与导入导出
- 测试评分与雷达图
- 监控端总览与运动员详情
- 日志、备份恢复、账号管理

## 本地开发

### 环境要求

- Python `3.12.x`
- Node.js `18+`
- Git

### 启动与初始化

本地开发推荐入口：

- 启动：`scripts/start_system.bat`
- 初始化：`scripts/init_system.bat`

这两条脚本当前定位是：

- 开发环境准备工具
- 本地联调启动工具
- 故障排查入口

它们不是生产环境启动方式。

### 本地验证

建议至少执行：

```powershell
cd frontend
npm run build
```

```powershell
cd ..
backend\.venv\Scripts\python.exe -m compileall backend\app
python scripts/check_text_encoding.py
```

## 服务器部署

当前服务器部署架构是：

- Nginx 对外提供 HTTP
- 前端构建产物由 Nginx 托管
- FastAPI 通过 systemd 常驻
- 后端仅监听 `127.0.0.1:8000`
- 前端通过同域 `/api` 访问后端
- 生产数据库独立存放在服务器数据目录

部署与更新请优先阅读：

- [docs/deployment/tencent-lighthouse-ubuntu.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\docs\deployment\tencent-lighthouse-ubuntu.md)

## 数据库与迁移

当前正式数据库演进路径是：

- Alembic migration
- `backend/scripts/migrate_db.py ensure`

`schema_sync.py` 仅保留为过渡期兼容兜底，不再是正式主迁移方案。

## 阅读顺序

新开发者建议先按这个顺序了解项目：

1. [README.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\README.md)
2. [PROJECT_CONTEXT.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\PROJECT_CONTEXT.md)
3. [CURRENT_STATUS.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\CURRENT_STATUS.md)
4. [DEVELOPMENT_GUIDE.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\DEVELOPMENT_GUIDE.md)
5. [CODEX_HANDOFF.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\CODEX_HANDOFF.md)
6. [docs/deployment/tencent-lighthouse-ubuntu.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\docs\deployment\tencent-lighthouse-ubuntu.md)
7. [docs/phase1-database-migrations.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\docs\phase1-database-migrations.md)
8. [docs/text-encoding.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\docs\text-encoding.md)

## 文档分层说明

当前文档分为三类：

- 根目录权威文档：描述当前系统事实与协作规则
- `docs/` 专题文档：描述单一主题的规范、设计或历史阶段说明
- 历史阶段文档：会显式标注“历史阶段 / 归档参考”，不再冒充当前实现

## 说明

- 当前工作区可能包含未完成开发分支上的功能改动，文档默认只记录“已经完成并与代码事实一致”的内容。
- 本仓库文本文件统一使用 UTF-8；如果怀疑有乱码，优先运行 `python scripts/check_text_encoding.py`。
