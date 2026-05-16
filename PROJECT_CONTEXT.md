# 项目背景说明

## 2026-05-16 当前事实补充

### 训练执行与同步现状

训练端本地草稿与同步链路已由 Playwright E2E 覆盖，当前 `npm run test:e2e` 会自动启动临时后端、临时前端和临时 SQLite 数据库，验证以下链路：

- 正常训练录入完成，并在训练报告和监控端确认 `completed`；
- 断网后新增组记录进入 `pending`，刷新后本地草稿不丢失；
- 恢复网络后 pending 草稿可同步，后端记录数正确，刷新后仍存在。

本地草稿仍然是浏览器本机 `localStorage` 恢复能力，适合同一设备、同一浏览器内的训练现场容错；它不是跨浏览器、跨设备、清缓存后仍可恢复的强同步方案。

### 数据迁移现状

数据库结构演进当前以 Alembic migration 为正式路径，入口为 `backend/scripts/migrate_db.py`。`schema_sync.py` 仅作为过渡期兜底，不再作为正式迁移主方案继续扩展。

当前 migration head 为 `c9d0e1f2a3b4`，已完成 Alembic metadata drift、business metadata 决策和 FK drift 收口。`backend/scripts/backend_check.py` 当前应完全通过。

新增的 `backend/scripts/check_fk_orphans.py` 是迁移前只读预检脚本，用于确认候选外键字段不存在 orphan data。服务器生产库或生产库快照在执行 `migrate_db.py ensure` 前，必须先运行该脚本并确认 orphan=0。

## 文档身份

这份文档是当前系统的产品与架构事实说明。  
它描述“系统现在是什么”，不是历史阶段回顾，也不是未来路线图。

## 一句话目标

这是一个面向体能训练团队场景的训练管理与测试分析平台，服务于教练对训练、测试、计划与回看分析的完整闭环。

## 当前产品定位

当前项目的现实定位是：

- 已有正式登录与角色边界
- 已有服务器部署链路
- 仍保留本地 Windows 开发与联调能力
- 以真实队伍数据与真实工作流为约束的业务系统

它不是通用 SaaS，也不是只面向本地演示的原型。

## 当前技术结构

- 前端：Vue 3 + Vue Router + Pinia
- 后端：FastAPI
- 数据库：SQLite
- ORM：SQLAlchemy
- 图表：ECharts
- 迁移：Alembic + `backend/scripts/migrate_db.py`
- 部署：Nginx + systemd + 同域 `/api`

## 当前运行方式

### 本地开发环境

- Windows
- 启动入口：`scripts/start_system.bat`
- 初始化入口：`scripts/init_system.bat`
- 前端开发端口：`5173`
- 后端开发端口：`8000`

### 服务器运行环境

- Ubuntu
- Nginx 提供 Web 入口
- 后端 FastAPI 常驻运行
- 后端仅监听 `127.0.0.1:8000`
- 前端请求后端统一走同域 `/api`
- 生产数据库独立于代码目录保存

## 当前权限与模式

系统当前为登录制。

当前主角色：

- `admin`
- `coach`

当前前端路由包含三种模式：

- 管理模式
- 训练模式
- 实时监控模式

## 当前核心业务链路

1. 管理运动员、队伍与账号
2. 维护测试类型、测试项目与测试记录
3. 维护动作库与动作分类
4. 维护训练模板
5. 分配训练计划
6. 在训练模式中执行并记录训练
7. 在监控端查看进度与异常
8. 在训练报告与测试评分中回看结果

## 当前核心业务对象

- 运动员 `athletes`
- 项目 `sports`
- 队伍 `teams`
- 用户 `users`
- 动作分类 `exercise_categories`
- 动作 `exercises`
- 训练模板 `training_plan_templates`
- 模板动作 `training_plan_template_items`
- 计划分配 `athlete_plan_assignments`
- 训练课 `training_sessions`
- 训练课动作项 `training_session_items`
- 组记录 `set_records`
- 测试记录 `test_records`
- 测试类型定义 `test_type_definitions`
- 测试项目定义 `test_metric_definitions`
- 评分模板 `score_profiles / score_dimensions / score_dimension_metrics`

## 当前已落地模块

- 运动员管理
- 队伍与项目管理
- 账号管理
- 动作库管理
- 训练模板管理
- 计划分配
- 训练执行与训练回看
- 实时监控端
- 测试数据管理
- 测试评分与雷达图
- 日志
- 备份恢复

## 训练执行与同步现状

训练端当前已经具备“本地优先 + 后台同步”的最小闭环：

- 浏览器本地草稿基于 `localStorage`
- 每组提交优先写本地
- 后端恢复后做补传
- 同步状态已收口为 `synced / pending / manual_retry_required`
- 明显同步异常可在系统中被看见

需要注意：

- 这不是跨浏览器、跨设备的强持久化方案
- 它是训练执行阶段的容错能力，不是服务器存储替代品

## 数据迁移现状

当前数据库演进正式主路径是：

- Alembic migration
- `backend/scripts/migrate_db.py`

`schema_sync.py` 仍可能存在于仓库中作为兼容兜底，但不应被理解为正式迁移主方案。

## 部署现状

当前系统已经存在服务器部署链路：

- 腾讯云 Ubuntu 调试/运行环境
- Nginx 托管前端构建产物
- FastAPI 通过 systemd 常驻
- 生产数据库与代码目录分离
- 代码通过 GitHub 同步，生产数据不通过 GitHub 同步

## 当前最高优先级

1. 保持训练执行、计划分配、测试数据和监控链路稳定
2. 保持迁移、备份和排障链路可重复
3. 持续校正文档，使开发者能按当前事实接手项目
4. 在不破坏现有主链路的前提下继续推进性能与交互优化
