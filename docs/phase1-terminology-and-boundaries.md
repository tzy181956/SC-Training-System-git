# 第一阶段重构术语与边界整理

## 1. 文档目标

本文档只服务于**第一阶段核心稳定性重构**，目标是统一当前代码库中最容易混淆的业务术语、状态枚举和阶段边界。

这份文档解决的问题只有三类：

1. 当前代码里 `template / assignment / session / training_status` 的语义边界不一致。
2. 训练端最关键的 `local draft / sync status` 已有最小 MVP，但还需要继续统一命名、状态和可见范围。
3. 第一阶段到底必须做什么、后续再做什么、当前明确不做什么，需要有统一基线。

本文档**不直接修改数据库、训练端 UI 或业务流程**，只作为后续重构落地时的统一命名和边界依据。

---

## 2. 当前代码库中的术语现状

### 2.1 已经存在且相对清晰的术语

#### 训练模板 `template`

当前后端模型：

- `TrainingPlanTemplate`
- `TrainingPlanTemplateItem`

对应文件：

- `backend/app/models/training_plan.py`

当前语义基本正确：模板表示一份可复用训练内容原型。

#### 计划分配 `assignment`

当前后端模型：

- `AthletePlanAssignment`

对应文件：

- `backend/app/models/assignment.py`
- `backend/app/services/assignment_service.py`

当前语义也基本正确：assignment 表示某份模板在某个时间范围内分配给某个运动员，是候选训练计划，不是一堂正式训练课。

### 2.2 已存在但语义混乱的术语

#### 训练课 `session`

当前后端模型：

- `TrainingSession`
- `TrainingSessionItem`
- `SetRecord`

对应文件：

- `backend/app/models/training_session.py`
- `backend/app/services/session_service.py`

当前代码的核心问题：

- 打开计划时仍会创建/确认一条 `TrainingSession`
- `TrainingSession.status` 默认值已收口为 `not_started`
- `get_or_create_session_for_assignment()` 不再把打开计划等同于正式开始训练，但仍早于“第一组成功前完全不落库”的最终目标

这与第一阶段目标冲突。第一阶段里：

- 打开计划不算开始
- 第一组提交成功才算正式开始，并创建/确认 session

#### 训练状态 `training_status`

当前代码里存在至少两套状态语义：

1. `TrainingSession.status`
   - 当前实际使用：`pending / in_progress / completed`
2. assignment/athlete 视图聚合状态
   - `not_started / in_progress / completed`
   - `no_plan`
3. assignment overview 分组状态
   - `active_now / upcoming`

这说明当前状态命名已经分裂：

- 一套是 session 自身状态
- 一套是 assignment 映射到训练视图的状态
- 一套是 overview 分组状态

第一阶段必须把这些分清楚，不能继续混着用。

### 2.3 当前代码里还没有正式建模的术语

#### 本地草稿 `local draft`

当前前端训练端：

- `frontend/src/stores/training.ts`
- `frontend/src/views/TrainingSessionView.vue`
- `frontend/src/components/training/TrainingSetPanel.vue`

现状：

- 已有 session 的本地离线镜像
- 每录一组会先写本地，再尝试后台补传
- 已支持恢复或放弃本地草稿
- 已有 `pending_operations` 记录待补传的单组创建/修改

结论：

- `Local Draft` 已经落地训练端最小 MVP
- 第一阶段后续要继续补齐统一可见性、长时间失败待处理和冲突处理

#### 同步状态 `sync status`

当前代码库已经有训练端最小同步状态层，但还没有形成贯穿前后端和管理可见性的完整模型。

现状：

- 训练端 Local Draft 已统一落地 `synced / pending / manual_retry_required`
- 已有训练端本地草稿与后端 session 的基础同步生命周期定义
- 教练端 / 管理端已经有“同步异常，待处理”的最小可见性
- 当前仍未落地复杂冲突合并界面与更细粒度的持久化状态机

结论：

- `Sync Status` 已进入第一阶段基础闭环，但后续仍可继续细化异常处理与冲突工作台

---

## 3. 第一阶段统一术语表

| 中文术语 | 英文术语 | 第一阶段统一建议命名 | 当前代码对应 | 第一阶段边界说明 |
|---|---|---|---|---|
| 训练模板 | `template` | `TrainingPlanTemplate` / `template` | 已存在 | 可复用训练内容原型，不是实际训练课 |
| 计划分配 | `assignment` | `AthletePlanAssignment` / `assignment` | 已存在 | 模板在时间范围内对运动员的候选训练计划，不等于 session |
| 训练课 | `session` | `TrainingSession` / `session` | 已存在但语义需收紧 | 一堂真实训练课的正式记录 |
| 本地草稿 | `local draft` | `LocalDraft` / `sessionDraft` | 已实现基础闭环 | 浏览器本地 `localStorage` 中的 session 离线镜像，主要覆盖同一浏览器 / 设备内恢复 |
| 组记录 | `set record` | `SetRecord` / `setRecord` | 已存在 | 某动作某一组的实际训练记录 |
| 同步状态 | `sync status` | `SyncStatus` | 已实现基础闭环 | 本地草稿 / session 的同步生命周期状态，当前已落地 `synced / pending / manual_retry_required` |
| 缺席 | `absent` | `absent` | 已实现 | 触发跨日收口时一组都没做 |
| 未完全按计划完成 | `partial_complete` | `partial_complete` | 已实现 | 做了部分，但触发跨日收口时整堂课未完成 |

---

## 4. 第一阶段必须统一的状态枚举

第一阶段至少要把以下枚举层级统一清楚。

## 4.1 AssignmentStatus

### 用途

表示一条计划分配记录本身是否仍然有效。

### 建议枚举

```text
AssignmentStatus = {
  active,
  cancelled
}
```

### 说明

- `active`：当前 assignment 仍有效，可被命中
- `cancelled`：该 assignment 已取消，不应再进入训练候选列表

### 当前代码现状

这套值已经存在于：

- `backend/app/models/assignment.py`
- `backend/app/services/assignment_service.py`

这部分可以直接沿用。

---

## 4.2 SessionStatus

### 用途

表示一堂训练课本身的正式状态。

### 第一阶段必须统一为

```text
SessionStatus = {
  not_started,
  in_progress,
  completed,
  absent,
  partial_complete
}
```

### 严格定义

- `not_started`
  - assignment 已命中
  - 但训练尚未正式开始
  - 打开计划、查看内容都不算开始

- `in_progress`
  - 第一组训练数据提交成功后进入
  - 从这一刻开始正式创建/确认 session

- `completed`
  - 整堂训练按规则完成
  - 或系统按规则自动判定为完成

- `absent`
  - 触发跨日收口时，一组都没做

- `partial_complete`
  - 已完成部分组记录
  - 但触发跨日收口时，没有完成整堂课

### 当前代码现状

当前训练主链路已开始收口为：

```text
not_started
in_progress
completed
absent
partial_complete
```

外围兼容层里仍可能出现历史 `pending` 值，但主链路已经不再把它当正式 `SessionStatus` 持续扩散。

当前仍需继续约束的是：

- 打开计划不能直接进入 `in_progress`
- 第一组成功后才算正式开始

### 第一阶段重构要求

- `pending` 不再作为正式 `SessionStatus` 对外使用
- session 正式状态统一改成上面五个值
- “打开计划不算开始”必须落地

---

## 4.3 SessionItemStatus

### 用途

表示一堂训练课中某个动作项的完成状态。

### 第一阶段建议保持

```text
SessionItemStatus = {
  pending,
  in_progress,
  completed
}
```

### 说明

`SessionItemStatus` 和 `SessionStatus` 不必强行完全同构。

原因：

- item 粒度不需要 `absent`
- item 粒度也不一定需要 `partial_complete`

当前 item 状态只要能支撑：

- 未开始该动作
- 正在做该动作
- 该动作已完成

就足够。

### 当前代码现状

这套值已经存在于：

- `backend/app/models/training_session.py`
- `backend/app/services/session_service.py`

第一阶段可以保留这组值。

---

## 4.4 AssignmentTrainingStatus（派生展示状态）

### 用途

这是**由 assignment + session 聚合出来的视图状态**，不是正式数据库主状态。

### 第一阶段建议枚举

```text
AssignmentTrainingStatus = {
  not_started,
  in_progress,
  completed
}
```

### 说明

它只用于训练模式下展示：

- 这条 assignment 对应的训练现在还没开始
- 正在进行中
- 已完成

不应与 `SessionStatus` 混为一谈。

### 当前代码现状

这套值已经在：

- `backend/app/services/session_service.py`

中以映射结果形式存在。

第一阶段建议保留其“派生视图状态”定位，但不要让它继续冒充 session 正式状态。

---

## 4.5 AthleteTrainingStatus（运动员当天视图状态）

### 用途

用于训练模式首页或训练队员列表的聚合展示。

### 第一阶段建议枚举

```text
AthleteTrainingStatus = {
  no_plan,
  not_started,
  in_progress,
  completed
}
```

### 说明

这是 UI 聚合状态，不是 assignment 或 session 的主状态。

### 当前代码现状

当前已经存在于：

- `backend/app/services/session_service.py`
- `frontend/src/stores/training.ts`

第一阶段可以保留，但必须明确它只是聚合展示层。

---

## 4.6 AssignmentGroupStatus

### 用途

用于计划分配上半区概览，区分当前与未来计划分组。

### 第一阶段建议枚举

```text
AssignmentGroupStatus = {
  active_now,
  upcoming
}
```

### 说明

这是 assignment overview 的分组标签，不是 assignment 主状态。

### 当前代码现状

已存在于：

- `backend/app/services/assignment_service.py`

可直接保留。

---

## 4.7 SyncStatus

### 用途

用于本地草稿和后台同步链路。

### 第一阶段当前已统一为

```text
SyncStatus = {
  pending,
  synced,
  manual_retry_required
}
```

### 严格定义

- `pending`
  - 本地草稿已写入
  - 后端尚未确认接收，或仍有待补传操作

- `synced`
  - 当前本地草稿与后端已对齐

- `manual_retry_required`
  - 自动重试与整课兜底都未成功
  - 已进入“同步异常，待处理”状态，需人工触发重试

### 当前代码现状

当前代码库已经落地：

- `pending`
- `synced`
- `manual_retry_required`
- 训练端 / 教练端 / 管理端最小可见性

当前仍可继续补齐：

- 更细粒度的临时执行态（如仅用于界面 loading 的 `syncing`）
- 更复杂的冲突审核界面
- 更完整的异常归因与统计

---

## 5. 第一阶段必须明确收紧的边界

## 5.1 必须做

以下内容属于第一阶段**必须做**：

### 训练端主链路

- 本地草稿保存与恢复
- 每组先写本地，再后台同步
- 同步失败不打断训练
- 同步状态统一可见

### Session 状态流

- 打开计划不算开始
- 第一组提交成功才正式开始训练
- session 状态统一为：
  - `not_started`
  - `in_progress`
  - `completed`
  - `absent`
  - `partial_complete`
- 跨日收口规则明确（后端启动主触发 + 训练入口兜底）

### Assignment 与 Session 边界

- assignment 只是候选训练计划
- session 才是一堂真实训练课
- 不再混用术语

### 基础工程能力

- 正式迁移机制取代长期运行时补字段
- 启动、初始化、环境检查、错误提示继续收紧
- 危险操作、日志、备份与恢复做基础版

---

## 5.2 后续再做

以下内容应在第一阶段之后逐步推进：

- 历史训练课以快照优先显示
- 更复杂的 assignment 周期规划
- 监控端增强
- 汇总与报表深化
- 更细的权限与多队规则
- 更完整的同步冲突处理页
- 更精细的日志检索和审计视图

---

## 5.3 当前明确不做

第一阶段当前明确不做深：

- 自动调重 / AI 建议
- 复杂权限系统
- 外网访问 / 云部署
- 复杂监控图表
- 复杂报表系统
- 智能导入识别
- 测试系统复杂标准化
- 测试结果自动强绑定训练建议
- 大规模 UI 美化
- 模板系统的大改
- 测试系统的大改

---

## 6. 当前代码与第一阶段目标的主要差距

这是后续重构任务最应该围绕的差距表。

## 6.1 Session 创建时机不对

当前：

- 打开计划时会创建/确认一条 `TrainingSession`
- 但当前已先收口为 `not_started` 占位，而不是直接设为 `in_progress`

第一阶段应改为：

- 打开计划不算正式开始训练
- 至少不能创建正式进行中的 session
- 第一组提交成功时才正式进入 `in_progress`
- 打开计划只返回训练草稿快照，不提前落库 session

## 6.2 缺少 Local Draft

当前：

- 已有本地持久层
- 训练录入失败时可回退到本地草稿并继续录入
- 已支持草稿恢复与后台单组补传

第一阶段应改为：

- 每堂课有本地草稿
- 每组先写本地
- 失败不打断训练
- 后台自动重试补传

## 6.3 缺少 SyncStatus

当前：

- 训练端只有最小 `synced / pending` 同步状态
- 无持续失败后的“待处理”概念

第一阶段应改为：

- 建立统一同步状态
- 训练端、教练端、管理端基础可见
- 长时间失败后进入待处理

## 6.4 SessionStatus 不完整

当前：

- 训练主链路已经补齐 `absent`
- 训练主链路已经补齐 `partial_complete`
- 但外围聚合、展示和历史兼容层仍需继续统一

第一阶段应继续收口到前后端统一解释。

## 6.5 仍依赖运行时 schema 修补

当前：

- `backend/app/core/schema_sync.py` 仍承担长期补字段职责

第一阶段应逐步替换为：

- 正式迁移
- 迁移前备份
- 明确迁移说明

---

## 7. 第一阶段建议命名规则

为了减少前后端到处特判，建议后续重构时统一按下面规则命名。

### 后端模型 / schema / service

- `Template` 只用于模板
- `Assignment` 只用于候选训练计划
- `Session` 只用于真实训练课
- `SetRecord` 只用于实际组记录
- `LocalDraft` 只用于本地草稿
- `SyncStatus` 只用于同步生命周期

### 前端 store / API / 视图

- `trainingStatus` 只用于展示态
- `sessionStatus` 只用于真实 session 状态
- `assignmentStatus` 只用于 assignment 主状态
- `groupStatus` 只用于 overview 分组态
- `syncStatus` 只用于本地草稿/同步态

---

## 8. 建议作为第一阶段后续任务的直接起点

如果按当前代码库进入正式重构，最应该先动的模块是：

### Step 1

训练端本地草稿保存与恢复：

- `frontend/src/stores/training.ts`
- `frontend/src/views/TrainingSessionView.vue`
- `frontend/src/components/training/TrainingSetPanel.vue`

### Step 2

session 创建时机与状态流收紧：

- `backend/app/services/session_service.py`
- `backend/app/models/training_session.py`
- `backend/app/schemas/training_session.py`

### Step 3

同步状态与后台同步链路：

- 训练端 store
- session 相关 API
- 后续异常提示与日志挂点

### Step 4

正式迁移机制替换运行时补 schema：

- `backend/app/core/schema_sync.py`
- 启动与初始化脚本

---

## 9. 本文档使用方式

从这一版开始，后续任何第一阶段相关改动都应优先检查：

1. 术语有没有越界
2. 状态枚举有没有混用
3. 是否把 assignment 当成 session
4. 是否绕开了 local draft / sync status 设计
5. 是否顺手扩展了第一阶段明确不该深做的模块

如果某次改动需要新增状态、字段或新表，必须先说明：

- 它属于哪一层术语
- 它和这里定义的哪个枚举或边界相关
- 为什么不能复用现有概念
