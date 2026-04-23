# 第一阶段数据库迁移基线与表结构规划

## 1. 这一步只解决什么

本文档只解决**正式数据库迁移机制接入**与**第一阶段表结构规划**，不顺手修改训练业务逻辑，不直接落地后续阶段的大量表结构。

本轮交付只包含：

1. Alembic 迁移脚手架
2. 当前模型对应的基线迁移
3. 面向现有数据库的迁移入口与基线接管方式
4. 第一阶段最可能新增/调整的表与字段规划
5. 迁移顺序、回退注意事项、迁移前备份设计

---

## 2. 本轮新增的迁移基础设施

### 2.1 Alembic 脚手架

新增文件：

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/20260423_c318e7988c37_baseline_schema.py`

用途：

- 让数据库结构演进不再长期依赖运行时 `schema_sync.py` 黑盒补表
- 为后续第一阶段的正式 schema 调整提供可追踪 revision 链

### 2.2 迁移执行脚本

新增文件：

- `backend/scripts/migrate_db.py`

用途：

- 提供统一迁移命令入口
- 在首次接入当前已有数据库时自动判断：
  - 现有库是否已经有业务表
  - 是否已经有 `alembic_version`
- 在迁移前自动备份数据库

### 2.3 初始化入口切换

调整文件：

- `backend/scripts/init_db.py`

变化：

- 不再直接 `create_all + ensure_runtime_schema`
- 改为走正式迁移入口 `bootstrap_database()`

这意味着当前初始化链路开始正式接入迁移机制。

---

## 3. 第一阶段迁移基线是什么

### 基线 revision

- `20260423_c318e7988c37_baseline_schema.py`

### 基线语义

这条 revision 表示：

> “当前仓库已有业务模型的数据库基线”

它不是第一阶段所有后续改造的终点，而是：

- 当前已有结构的可追踪起点
- 未来所有数据库变更都应在它之后继续追加 revision

### 为什么要先做基线

如果没有基线：

- 后续新增 `local draft`
- 收紧 `session status`
- 增加同步状态
- 增加训练修改日志

这些改动就只能继续依赖运行时补列或人工改库。

基线先建立后，后续第一阶段 schema 调整才有正式顺序。

---

## 4. 当前数据库如何接入这条基线

当前项目已经有正在使用的 `backend/training.db`。  
这类数据库不能直接把“创建全部表”的基线 migration 再执行一遍，否则会报表已存在。

因此接管策略分两类。

## 4.1 现有数据库（已有业务表）

处理方式：

1. 迁移脚本先自动备份当前数据库
2. 检测到已有业务表但还没有 `alembic_version`
3. 不执行基线建表 SQL
4. 直接执行：

```text
alembic stamp head
```

意义：

- 把当前库标记为“已处于基线版本”
- 不重复建表
- 从此之后再追加 revision 时，就能正式 `upgrade`

## 4.2 新数据库（还没有业务表）

处理方式：

1. 若数据库为空或尚未创建业务表
2. 直接执行：

```text
alembic upgrade head
```

意义：

- 由基线 migration 正式创建当前 schema

---

## 5. 迁移命令与推荐用法

## 5.1 首次接管当前数据库

推荐命令：

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\migrate_db.py bootstrap
```

行为：

- 自动备份数据库
- 如果当前库已有业务表但没有版本表：`stamp head`
- 如果当前库是空库：`upgrade head`

## 5.2 查看当前 revision

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\migrate_db.py current
```

## 5.3 后续升级到最新 revision

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\migrate_db.py upgrade head
```

## 5.4 手动标记 revision（通常只在特殊恢复场景使用）

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\migrate_db.py stamp head
```

---

## 6. 迁移前自动备份设计

第一阶段迁移必须默认带备份意识。

当前脚本 `backend/scripts/migrate_db.py` 的设计是：

- 每次执行 `bootstrap` 前
- 若数据库文件存在
- 自动复制到：

```text
backend/backups/training.migration-backup-YYYYMMDD-HHMMSS.db
```

### 为什么备份必须先于迁移

因为第一阶段后续的 schema 变化里，会逐步出现：

- 状态枚举收紧
- 字段删改
- 本地草稿相关新表
- 训练日志结构

这些都属于**有状态风险**的演进，不能依赖“迁移失败了再想办法补救”。

### 当前设计边界

本轮先做：

- 迁移前自动备份设计
- `bootstrap` 自动备份

后续再扩展：

- 危险操作统一备份
- 定时备份
- 可视化恢复入口

---

## 7. 第一阶段最可能新增/调整的表和字段规划

下面这些是**第一阶段规划中的目标结构**，不是本轮已经全部落地的变更。

## 7.1 `training_sessions.status` 统一

### 计划调整

将正式 session 状态逐步收口到：

```text
in_progress
completed
absent
partial_complete
```

并把“尚未开始”留在训练执行视图层，不再作为正式 session 状态长期存在。

### 原因

- 当前 `pending / in_progress / completed` 不足以表达缺席和未完全完成
- 也无法与自动结束规则对齐

### 给谁用

- 训练端 session 主链路
- 教练回看
- 后续日志与同步修复

### 与旧结构关系

- 旧字段：仍是 `training_sessions.status`
- 新策略：统一状态值语义，不额外新开第二个正式状态字段

### 迁移顺序建议

1. 先完成状态流文档收口
2. 再新增迁移 revision，调整允许值与数据回写规则
3. 最后改服务层逻辑

### 回退注意事项

- 若已有旧值 `pending`
- 回退时必须保留从新值回旧值的映射说明
- 不能直接丢失状态语义

---

## 7.2 新增 `session_local_drafts`

### 计划新增

新增表：

```text
session_local_drafts
```

### 原因

- 第一阶段要实现“本地草稿是 session 的离线镜像”
- 当前训练端没有正式本地草稿承载结构

### 给谁用

- 训练端本地恢复
- 后台补传
- 同步异常排查

### 建议最小字段

- `id`
- `session_key`
- `athlete_id`
- `assignment_id`
- `session_id`
- `session_date`
- `status`
- `sync_status`
- `device_id`
- `version`
- `payload_json`
- `last_modified_at`
- `last_synced_at`
- `created_at`

### 与旧结构关系

- 新增表，不替代 `training_sessions`
- 它是 `training_sessions` 的离线镜像，而不是第二套业务表

### 迁移顺序建议

1. 先建表
2. 再接训练端本地草稿逻辑
3. 再接同步链路

### 回退注意事项

- 回退时如果本地草稿尚未真正投入使用，可只回退表结构
- 若已进入使用期，回退前必须先导出或保留草稿数据

---

## 7.3 `sync_status` 相关结构

### 计划新增/调整

第一阶段至少需要统一：

```text
local_only
syncing
synced
sync_error
```

### 结构建议

优先放在：

- `session_local_drafts.sync_status`

可选后续扩展到：

- `training_sessions.sync_status`

### 原因

- 当前系统没有正式同步状态枚举
- 无法支撑训练端、教练端、管理端统一查看同步健康度

### 给谁用

- 训练端本地提示
- 教练课后异常处理
- 管理端故障诊断

### 与旧结构关系

- 当前无旧字段，可直接新增

### 迁移顺序建议

1. 先在 local draft 表中落地
2. 观察是否需要在正式 session 侧冗余同步状态

### 回退注意事项

- 新增字段回退相对简单
- 但若已写入业务逻辑，回退前必须同时回退状态机和读取逻辑

---

## 7.4 课后补录与修改日志基础结构

### 计划新增

建议新增一张基础日志表，例如：

```text
training_session_change_logs
```

### 原因

第一阶段就已经明确允许：

- 课后补录
- 课后修改组记录
- 课后状态重算

这些动作必须有基础日志落点。

### 给谁用

- 教练回查
- 管理员排查
- 同步冲突与异常诊断

### 建议最小字段

- `id`
- `session_id`
- `session_item_id`
- `set_record_id`
- `change_type`
- `operator_id`
- `before_json`
- `after_json`
- `reason`
- `created_at`

### 与旧结构关系

- 新增表，不影响现有训练记录主表
- 只做变更追踪

### 迁移顺序建议

1. 先建日志表
2. 再在训练记录修改入口补写日志

### 回退注意事项

- 回退表结构前先确认是否需要保留审计记录
- 一旦投入使用，不建议轻易删除历史日志

---

## 8. 第一阶段建议的迁移顺序

建议按下面顺序推进，而不是一口气把所有未来表都加进去。

### Migration 0001

基线迁移：

- 建立 Alembic revision 链
- 接管当前数据库

### Migration 0002

训练课状态流相关结构调整：

- `training_sessions.status` 统一
- 必要的状态字段补齐

### Migration 0003

本地草稿基础结构：

- `session_local_drafts`
- `sync_status`

### Migration 0004

训练修改/补录日志：

- `training_session_change_logs`

### 为什么按这个顺序

因为第一阶段主链路是：

1. 先收状态流
2. 再收本地草稿与同步
3. 再补日志

如果先上复杂日志或一堆未来阶段表，只会扩大范围。

---

## 9. 回退方式说明

## 9.1 当前基线接管的回退

如果 `bootstrap` 是对现有数据库执行 `stamp head`：

- 数据库结构本身不会被改写
- 主要变化是新增 `alembic_version`

回退方式：

1. 使用迁移前自动备份的数据库文件恢复
2. 或手动删除 `alembic_version` 并恢复到旧启动方式（不推荐长期这样做）

## 9.2 后续 schema 变更 revision 的回退

推荐原则：

- **优先恢复备份**
- 不把 `downgrade` 当作唯一保险

原因：

- 后续第一阶段里会出现状态值转换、字段删改、日志结构调整
- 这些操作不一定都适合只靠反向 SQL 完全恢复

### 推荐回退顺序

1. 确认迁移前备份存在
2. 若 revision 可安全 downgrade，先执行 `downgrade -1`
3. 若涉及破坏性结构或数据语义转换，优先直接恢复迁移前备份

---

## 10. 当前与旧结构的关系说明

本轮之后，数据库结构演进的推荐路径变为：

- 正式路径：
  - `alembic revision`
  - `alembic upgrade`
  - `scripts/migrate_db.py`

- 过渡期保留：
  - `backend/app/core/schema_sync.py`

### 这意味着什么

`schema_sync.py` 现在仍可作为过渡期防线存在，  
但它不应继续承担“长期正式迁移机制”的职责。

后续任何新字段、新表、新状态结构：

- 先走 migration
- 再决定是否保留极少量运行时兜底

不能再反过来以 `schema_sync.py` 作为主方案。

---

## 11. 这一步的最终结论

第一阶段数据库演进现在应当正式切换为：

> “Alembic 基线 + 迁移脚本 + 迁移前自动备份 + 分阶段 revision”

而不是继续依赖：

> “启动时自动补字段/修表”

本轮只先把**迁移骨架、基线和表结构规划**搭起来。  
后续真正进入第一阶段实现时，应按本文档的顺序逐条追加 revision，而不是把所有未来表一次性建进去。
