# 第一阶段训练课状态流重定义

## 1. 这一步只解决什么

本文档只解决**训练课状态流重定义**，不直接修改数据库、不改训练端 UI、不改模板系统、不写监控端和报表逻辑。

本轮只回答四件事：

1. 第一阶段应该统一成什么状态枚举
2. 每个状态如何进入、如何退出
3. 哪些事件会触发状态变化
4. 真正要改的后端模块有哪些

---

## 2. 先统一边界：当前代码到底用什么状态

当前代码里最容易混淆的一点是：

- `assignment` 是候选训练计划
- `session` 是一堂真实训练课
- 训练入口和训练课详情当前都对外使用同一套状态文案

而业务规则又明确要求：

- 打开候选计划不算开始
- 第一组提交成功时，才正式创建/确认 `session`

这意味着：

### 结论 A：第一阶段当前实现统一使用 `not_started`

当前仓库的后端模型、服务层和前端页面都已经统一到：

1. 训练入口 / 候选计划视图用 `not_started`
2. `TrainingSession.status` 的未开始占位也用 `not_started`

因此本阶段文档不再继续沿用早期草案里的 `planned` 术语，避免后续开发误以为仓库仍存在另一套状态体系。

---

## 3. 第一阶段当前实现统一的状态枚举

## 3.1 对外训练状态（页面、接口、服务层统一口径）

### 当前取值

```text
not_started
in_progress
completed
absent
partial_complete
```

### 含义

- `not_started`
  - 已存在候选计划，或已生成未开始占位 session
  - 但还没有正式开始训练
  - 打开计划、查看内容都不算开始

- `in_progress`
  - 第一组提交成功后进入
  - 此时正式创建/确认 `session`

- `completed`
  - 所有应录的组都已经录完
  - 或手动结束时经过重算，确认整堂课已完成

- `absent`
  - 触发跨日收口时，一组都没做

- `partial_complete`
  - 已经做了部分组记录
  - 但没有完成整堂课
  - 在跨日收口或手动结束重算后进入

### 为什么当前统一为 `not_started`

因为当前代码已经用 `not_started` 贯通：

- `TrainingSession.status` 默认值
- 训练入口状态映射
- 前端侧边栏与训练页状态展示

所以这里按真实实现记录，不再把 `planned` 作为当前阶段文档推荐值。

---

## 3.2 正式训练课状态

### 建议名称

`SessionStatus`

### 当前取值

```text
not_started
in_progress
completed
absent
partial_complete
```

### 说明

当前 `TrainingSession.status` 已对外统一为以上五个值。

其中：

- `not_started` 是未开始占位状态
- `in_progress` 才表示第一组已提交、训练正式开始
- `completed / absent / partial_complete` 是终态

因此：

- `not_started` 虽然出现在正式 session 记录里，但不代表“打开计划就算开始”
- 第一阶段仍应避免继续使用旧的 `pending` 作为对外正式 session 状态

如果内部实现上仍有过渡逻辑，也必须满足：

- 对外接口与服务层统一按上面五个状态解释
- 不能再把“打开计划”直接写成 `in_progress`

---

## 4. 每个状态的进入条件与退出条件

## 4.1 `not_started`

### 进入条件

- assignment 已命中当前训练日期
- 该 assignment 还没有被正式开始
- 尚无有效组记录提交成功

### 退出条件

- 第一组提交成功 => 进入 `in_progress`
- 触发跨日收口且一组都没做 => 进入 `absent`
- assignment 被取消 => 退出训练候选集合，不再参与本状态流

### 备注

- 打开计划页面
- 查看动作列表
- 查看动作详情

以上行为都**不应该**让 `not_started` 退出。

---

## 4.2 `in_progress`

### 进入条件

- 第一组训练数据提交成功
- 此时正式创建/确认 `session`

### 退出条件

- 所有应录的组都已录完 => `completed`
- 手动结束训练，且经重算发现仍有未完成内容 => `partial_complete`
- 触发跨日收口时仍未全部完成 => `partial_complete`

### 备注

- 历史组修改、补录、改单次重量/次数等，不应直接退出 `in_progress`
- 只有状态重算后才决定是否变为 `completed` 或 `partial_complete`

---

## 4.3 `completed`

### 进入条件

满足以下任一：

- 所有该录的组都已经录完
- 手动结束训练时，经重算确认整堂课已经完成
- 课后补录后经重算，发现现有记录已满足完成条件

### 退出条件

- 课后修正或删除组记录后，经重算发现不再满足完成条件
  - 若至少做过部分内容 => `partial_complete`
  - 若极端情况下所有记录都被撤销/清空，应按业务规则回退为 `absent` 或回到异常待处理，不建议静默回退为 `not_started`

### 备注

- 第一阶段允许教练课后修正
- 但修正后必须重算状态，并写日志

---

## 4.4 `absent`

### 进入条件

- 触发跨日收口时
- 该 assignment 一组都没做

### 退出条件

- 课后补录第一组及以上记录，并触发状态重算
  - 若只完成部分 => `partial_complete`
  - 若全部完成 => `completed`
  - 若补录后仍在继续录入过程 => `in_progress`

### 备注

- `absent` 不是“没打开计划”
- 而是“触发跨日收口时一组都没做”

---

## 4.5 `partial_complete`

### 进入条件

满足以下任一：

- 触发跨日收口时，已做部分内容但没做满
- 手动结束计划时，已做部分内容但没做满
- 原本 `completed` 的训练课经课后修正重算后，不再满足完成条件，但仍保留部分记录

### 退出条件

- 课后补录并重算后全部满足 => `completed`

### 备注

- 这是第一阶段必须新增并统一的正式状态
- 当前代码库里已经统一为这个状态值

---

## 5. 事件触发列表

下面是第一阶段必须统一的事件触发规则。

## 5.1 打开候选计划

### 事件

队员/教练在训练端打开某个候选计划

### 处理规则

- 允许为当前候选计划创建一个 `not_started` session 占位
- 但不能写入 `started_at`
- 也不能进入 `in_progress`
- 当前训练执行状态仍为 `not_started`

### 当前代码问题

当前实现已从“打开计划即 `in_progress`”收口为：
- 打开计划时只返回训练草稿快照，不创建正式 session
- 第一组提交成功后，才正式创建/确认 session 并进入 `in_progress`

这仍然和“第一组前完全不落库 session 行”的最终目标有差距，但已经满足本阶段“打开不算开始”的核心边界。

---

## 5.2 第一组提交成功

### 事件

第一条组记录提交成功

### 处理规则

- 正式创建或确认 `session`
- `TrainingExecutionStatus` => `in_progress`
- `SessionStatus` => `in_progress`
- 写入第一条 `SetRecord`

### 备注

这是第一阶段最关键的状态切换点。

---

## 5.3 后续组提交成功

### 事件

继续提交新的组记录

### 处理规则

- 先重算当前动作项完成情况
- 再重算整堂课完成情况
- 如果整堂课全部完成 => `completed`
- 否则保持 `in_progress`

---

## 5.4 手动结束计划

### 事件

用户点击“结束计划”

### 处理规则

结束不是强行写死状态，而应：

1. 先重算当前已有记录
2. 若全部完成 => `completed`
3. 若仍有未完成内容 => `partial_complete`

### 备注

手动结束应是“触发收口与重算”，不是“无条件 completed”。

- 本阶段 `absent` 只由跨日收口产生
- 手动结束时，即使一组都没做，也先统一记为 `partial_complete`

---

## 5.5 跨日收口（无定时任务版）

### 事件

系统在后端启动时先收口昨日及更早未结束训练课；训练相关入口继续保留兜底收口

### 处理规则

- 一组都没做 => `absent`
- 做了部分但没做满 => `partial_complete`
- 全部完成 => `completed`

### 备注

这是第一阶段必须补齐的跨日收口规则；当前实现不依赖零点定时任务。

当前仓库已将跨日自动收口的主触发点收口为：

- 后端每次启动成功前先执行一次跨日收口
- 训练相关入口继续保留 `close_due_sessions()` 兜底

这样即使当天先进入报表、日志或管理页，而不是先进入训练流程，昨天及更早未收口的训练课也会先被统一纠正。

---

## 5.6 课后补录 / 修改 / 删除组记录

### 事件

教练在课后对组记录做补录、修改或删除

### 处理规则

- 每次修改后都必须触发状态重算
- 可能发生的回流：
  - `absent` => `in_progress` / `partial_complete` / `completed`
  - `partial_complete` => `completed`
  - `completed` => `partial_complete`

### 备注

- 课后修正允许存在
- 但必须写日志
- 且状态不能写死不变

---

## 6. 推荐的重算规则顺序

第一阶段建议把状态重算统一成下面的判断顺序：

1. 若 assignment 已失效或不参与当天训练流程，则不进入本次判断
2. 统计当前已有 `SetRecord` 数量
3. 若记录数为 0：
   - 未触发跨日收口 => `not_started`
   - 已触发跨日收口 => `absent`
   - 若是手动结束事件 => `partial_complete`
4. 若记录数 > 0 且所有应录组都完成：
   - `completed`
5. 若记录数 > 0 且未全部完成：
   - 未触发跨日收口 => `in_progress`
   - 已触发跨日收口或手动结束 => `partial_complete`

---

## 7. 第一阶段需要修改的后端模块清单

这一步只列出后端改造范围，不展开前端 UI。

## 7.1 必改模块

### `backend/app/services/session_service.py`

**原因：**

- 当前这里直接把“打开计划”写成开始训练
- 当前 session 状态重算只覆盖 `pending / in_progress / completed`
- 这里是第一阶段状态流重构的主战场

**需要改的点：**

- 重定义 session 创建/确认时机
- 引入 `absent / partial_complete`
- 改写 `_recompute_session_status()`
- 调整 `submit_set_record()`、`update_set_record()`、`complete_session()` 的状态收口逻辑
- 重写 assignment -> training status 的映射规则

### `backend/app/api/endpoints/sessions.py`

**原因：**

- 当前 `/training/plans/{assignment_id}/session` 语义仍接近“开始训练”
- 这层需要和新的状态流保持一致

**需要改的点：**

- 重新定义“打开候选计划”相关接口语义
- 避免接口名和行为继续强化“打开即开始”
- 明确哪些接口是：
  - 取候选计划详情
  - 正式开始/确认训练
  - 提交组记录
  - 手动结束训练

### `backend/app/models/training_session.py`

**原因：**

- 当前 `TrainingSession.status` 默认值与目标状态流不一致

**需要改的点：**

- 配合新状态流统一正式 session 状态字段取值
- 明确 `completed_at` 与状态收口关系

### `backend/app/schemas/training_session.py`

**原因：**

- 当前 schema 同时混有 `session.status`、`training_status` 等不同层次状态

**需要改的点：**

- 对外 schema 中统一状态语义
- 区分：
  - 正式 `session_status`
  - 派生 `training_status`

---

## 7.2 高相关、建议同步检查的模块

### `backend/app/services/assignment_service.py`

**原因：**

- assignment 本身不等于 session
- 但 overview / preview / active assignment 逻辑会受到新状态边界影响

**这一步不要求重写 assignment 规则**

但至少应同步检查：

- assignment 是否继续只承担候选计划职责
- 是否有地方把 assignment 状态误当成训练课状态

### `backend/app/schemas/assignment.py`

**原因：**

- 若 assignment overview 中继续返回训练相关状态，需要保证术语清晰

这一步只建议同步检查，不要求现在扩字段。

---

## 8. 本轮明确不碰的内容

这一步状态流重定义**不应该顺手改**：

- 训练端 UI 结构
- 模板系统
- 测试系统
- 自动调重 / AI 建议
- 监控端
- 报表
- 权限系统
- 外网访问
- 大规模数据库结构设计

---

## 9. 本文档给后续单步改造的直接结论

如果下一步进入正式实现，最先应该落地的是：

1. `session_service.py` 中把“打开计划即开始训练”改掉
2. 统一正式 `SessionStatus`
3. 统一 `not_started / in_progress / completed / absent / partial_complete` 这套当前已落地的状态口径
4. 补齐 `absent / partial_complete`
5. 把手动结束和跨日收口都改成“重算状态”，而不是写死结果
