# 第一阶段数据库迁移基线与表结构规划

> 文档状态：当前有效，但包含历史阶段上下文  
> 当前优先阅读：根目录 `README.md`、`PROJECT_CONTEXT.md`、服务器部署文档  
> 说明：本文档保留迁移接入过程与阶段性规划细节，适合作为迁移专题参考；系统当前正式迁移主路径仍以 Alembic + `backend/scripts/migrate_db.py` 为准。

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
4. 先执行：

```text
alembic stamp c318e7988c37
```

5. 再执行：

```text
alembic upgrade head
```

意义：

- 先把当前库标记为“已接入 Alembic 基线”
- 再按正式 revision 顺序补齐后续结构
- 即使部分字段或表曾被 `schema_sync.py` 兜底创建，后续 migration 也应保持幂等兼容

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
- 如果当前库已有业务表但没有版本表：先 `stamp` 基线，再 `upgrade head`
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
backend/backups/training-YYYYMMDD-HHMMSS-before_migration-<label>.db
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

- 危险操作统一备份（第一版已接入）
- 定时备份（第一版已接入）
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

## 7.2 浏览器本地草稿（当前不新增 `session_local_drafts` 表）

### 当前实现口径

第一阶段当前**没有**新增数据库表 `session_local_drafts`。

当前训练端本地草稿仍保存在：

- 浏览器 `localStorage`

后端当前只为同步异常与冲突落最小可见记录：

- `training_sync_issues`
- `training_sync_conflicts`

### 为什么不写成数据库表

- 当时训练端的设计背景仍以“浏览器本地优先恢复与补传”作为主假设
- 第一阶段优先要保证断网继续录入、页面异常关闭后恢复、后台补传和人工重试闭环
- 当前实现已经落在浏览器本地优先方案上，不应再把仓库文档写成“数据库里已经有 session_local_drafts 表”

### 当前边界

- 草稿主要覆盖同一浏览器 / 同一设备内的恢复
- 不等同于跨浏览器、跨设备或清缓存后仍可恢复的强持久化方案
- 如果后续真的要把草稿正式落库，再单独补 migration 和回退说明

---

## 7.3 `sync_status` 相关结构

### 当前统一口径

第一阶段当前统一使用：

```text
pending
synced
manual_retry_required
```

### 结构落点

当前主要落在：

- 浏览器本地草稿 `sync_status`
- 后端 `training_sync_issues.issue_status` / `resolved_at`（用于“同步异常，待处理”最小可见性）

当前**没有**落到：

- `training_sessions.sync_status`

### 原因

- 当前系统已经有正式同步状态枚举，不再是“尚未统一”阶段
- 训练端、教练端、管理端已经有第一版同步异常可见性与人工重试入口
- 但这仍是第一阶段基础闭环，不应误写成更复杂的持久化状态机已经完成

### 给谁用

- 训练端状态灯与手动同步入口
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

如后续把浏览器本地草稿正式迁移为后端持久化方案，可考虑：

- `session_local_drafts`
- `sync_status`

说明：当前第一阶段真实实现**未落**这条 migration，当前草稿仍以浏览器 `localStorage` 为主。

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

如果 `bootstrap` 是对现有数据库执行“先 `stamp` 基线，再 `upgrade head`”：

- 会新增 `alembic_version`
- 也可能继续补跑基线之后尚未正式落库的 revision
- 因此回退仍应优先依赖迁移前备份，而不是假设“只是打了一个版本标记”

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

只要它还存在，后续新增 migration 就必须默认考虑：

- 历史数据库可能已经被 `schema_sync.py` 补过字段或表
- migration 需要先检查表/字段/索引是否已存在，再决定是否执行 DDL
- 旧库接管不能再靠 `stamp head` 直接掩盖结构缺口

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

---

## 12. 截至 Step 15 已落地的 revisions

当前仓库里，第一阶段已经实际落地到 Alembic 的 revisions 如下：

| 顺序 | Revision | 文件 | 对应步骤 / 主题 |
| --- | --- | --- | --- |
| 1 | `c318e7988c37` | `backend/alembic/versions/20260423_c318e7988c37_baseline_schema.py` | 基线接管 |
| 2 | `5f2d4f0f4b8b` | `backend/alembic/versions/20260423_5f2d4f0f4b8b_add_training_sync_conflicts.py` | Step 08：整堂课覆盖同步兜底的冲突日志 |
| 3 | `9d1b2c3a4e5f` | `backend/alembic/versions/20260424_9d1b2c3a4e5f_add_training_sync_issues.py` | Step 09：同步异常待处理 |
| 4 | `b1f8d2e7c6a1` | `backend/alembic/versions/20260424_b1f8d2e7c6a1_add_training_session_edit_logs.py` | Step 11：课后修改 / 补录日志 |
| 5 | `f3a4b5c6d7e8` | `backend/alembic/versions/20260424_f3a4b5c6d7e8_add_dangerous_operation_logs.py` | Step 14：危险操作日志 |
| 6 | `c7d8e9f0a1b2` | `backend/alembic/versions/20260424_c7d8e9f0a1b2_add_content_change_logs_and_user_team_id.py` | Step 15：日志页聚合来源补齐 |

### 12.1 这些 revision 分别解决什么

#### `5f2d4f0f4b8b`｜`training_sync_conflicts`

- 为什么加：给整堂课覆盖同步兜底保留“明显冲突”的最小日志载体。
- 给谁用：教练 / 管理端查看同步冲突，后端记录本地快照与远端快照摘要。
- 和旧结构关系：旧结构没有同步冲突表，这里是新增最小审计表，不替代训练主表。
- 回退注意：删表即可回退结构，但业务上更推荐用迁移前备份恢复，以免丢失冲突追溯记录。

#### `9d1b2c3a4e5f`｜`training_sync_issues`

- 为什么加：把“自动重试失败后转人工处理”的异常状态落库。
- 给谁用：训练端状态灯、教练端异常可见性、管理端日志页。
- 和旧结构关系：它不是训练记录本身，而是同步链路的异常追踪表。
- 回退注意：如已产生待处理异常记录，回退前应先确认是否需要保留这些排障信息。

#### `b1f8d2e7c6a1`｜`training_session_edit_logs`

- 为什么加：课后修改、补录、删除训练组后必须可追溯。
- 给谁用：训练回看、日志页、后续审计。
- 和旧结构关系：不改变 `training_sessions / training_session_items / set_records` 主数据关系，只增加旁路日志表。
- 回退注意：结构可回退，但一旦回退会失去已记录的课后修正轨迹。

#### `f3a4b5c6d7e8`｜`dangerous_operation_logs`

- 为什么加：删除、清空重导、恢复备份等高风险动作不能只靠前端弹窗，后端也要有日志。
- 给谁用：管理端日志页、危险操作审计。
- 和旧结构关系：同样是新增旁路日志，不改主业务表。
- 回退注意：若系统已依赖该表做日志查询，回退前需同步调整日志聚合接口。

#### `c7d8e9f0a1b2`｜`content_change_logs` + `users.team_id`

- 为什么加：
  - `content_change_logs`：补齐模板 / 动作库等内容修改日志来源。
  - `users.team_id`：支撑日志页“教练只看自己队伍、管理员看全部”的最小过滤边界。
- 给谁用：`GET /api/logs` 聚合查询、模板 / 动作库变更记录、队伍过滤。
- 和旧结构关系：
  - `content_change_logs` 是新增旁路日志表，不替代内容主表。
  - `users.team_id` 是在现有 `users` 上补一个最小归属字段，不扩成复杂权限系统。
- 迁移顺序：
  1. 先执行已有危险操作日志 revision。
  2. 再补 `users.team_id` 和 `content_change_logs`。
  3. 最后由日志接口统一聚合多类日志。
- 回退注意：
  - 若已使用 `team_id` 做日志过滤，回退前要先降级接口行为。
  - `content_change_logs` 删除后会失去模板 / 动作库修改历史。

### 12.2 当前链路的迁移顺序说明

截至 Step 15，推荐顺序已经明确为：

1. `baseline_schema`
2. 同步兜底相关表
3. 训练课课后修正日志
4. 危险操作日志
5. 通用内容修改日志与最小队伍归属字段

这个顺序的含义是：

- 先保证训练端稳定链路有记录可追
- 再补管理端危险操作保护
- 最后补日志页所需的统一查询来源

### 12.3 兼容性与幂等性说明

当前这批 migrations 仍然兼顾旧库接管阶段，原则是：

- 基线后新增 revision 尽量避免对旧数据做激进改写
- 新增日志表优先采用“旁路新增”方式，不破坏训练主链数据
- 对旧库运行迁移时，仍建议先备份再 `upgrade`
- 运行期 `schema_sync.py` 还在过渡期存在，但不应继续承担正式迁移主职责
