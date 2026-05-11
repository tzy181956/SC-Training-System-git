# 第一阶段本地草稿与 Session 的关系设计

> 文档状态：历史阶段设计文档  
> 当前用途：保留训练端本地草稿与正式训练课关系的设计背景。  
> 当前优先阅读：根目录权威文档，以及训练端当前实现代码。  

## 1. 这一步只解决什么

本文档只解决**本地草稿（local draft）与正式训练课（session）的关系设计**，不直接实现同步代码，不改数据库，不改训练端 UI，也不扩展模板系统、监控端或报表。

本轮只回答这几件事：

1. 本地草稿是什么
2. session 什么时候才真正成立
3. 为什么本地草稿和 session 不是两套业务
4. 本地草稿至少需要哪些字段
5. 本地草稿与正式 session 如何保持一致
6. 第一阶段建议新增哪些表或字段（先设计，不落迁移）

---

## 1.1 当前实现进度（训练端 MVP）

当前仓库已经先落了一版**前端本地草稿 MVP**，边界如下：

- 整堂课一个本地草稿
- 每录完一组立即写入当前设备当前浏览器
- 历史组修改后也会刷新整课草稿
- 重新进入训练课时，会弹出“恢复 / 放弃”提示
- 后端不可用时，组记录仍可先保存在本机草稿里
- 本地已有草稿时，会按组做最小后台补传重试
- 增量补传连续失败达到阈值后，会自动进入整堂课覆盖同步兜底
- 整课兜底也长期失败时，会进入 `manual_retry_required`，并把异常同步问题暴露给教练 / 管理端
- 训练页支持手动触发整课补传
- 明显冲突会记录到 `training_sync_conflicts`，并通过训练回看页的异常提示卡对教练/管理员可见
- 当前持久化同步状态已收敛到：
  - `synced`
  - `pending`
  - `manual_retry_required`

本轮**没有**实现：

- 复杂冲突合并界面
- 独立的同步冲突处理后台页面
- 跨浏览器、跨设备或清缓存后仍可恢复的强持久化草稿方案

也就是说，当前实现已经从“最小增量补传”推进到了“增量补传 + 整课覆盖兜底 + 最小冲突可见性 + 人工重试闭环”阶段，但还没有进入“复杂冲突处理界面”和“跨设备强持久化草稿”阶段。

需要明确：当前本地草稿依赖浏览器 `localStorage`，主要覆盖同一浏览器 / 同一设备内的断网续录和页面异常关闭恢复，不要把它描述成跨设备永久安全方案。

---

## 2. 先统一结论：本地草稿是什么

### 定义

`Local Draft` 是 **session 的离线镜像**。

它不是另一套训练业务，也不是另一份“临时计划”。  
它只是训练端为了保证现场录入稳定，而在本地维护的一份**可恢复、可补传、可重算**的 session 镜像。

### 这意味着

- 训练现场录入时，先写本地草稿
- 后台网络可用时，再把本地草稿增量或整堂课同步到后端
- 后端正式 session 与本地草稿描述的是**同一堂训练课**
- 差别只在于：
  - 一个是本地优先的离线镜像
  - 一个是后端正式记录

### 本地草稿不是：

- 另一份 template
- 另一条 assignment
- 另一个独立的“训练记录系统”

---

## 3. Session 什么时候真正成立

第一阶段必须严格遵守这个规则：

### 规则

**第一组提交成功时，正式创建/确认 session。**

### 这条规则直接带来的边界

#### 打开候选计划时

- 还没有正式开始训练
- 不应该创建正式 `in_progress` session
- 训练执行状态最多只能是 `not_started`

#### 第一组提交成功时

- 训练课正式开始
- 此时才创建或确认后端 `session`
- 本地草稿从“候选训练的本地镜像”升级为“已开始 session 的本地镜像”

#### 为什么这么设计

因为业务上：

- 打开计划不等于开始训练
- 查看内容不等于开始训练
- 只有第一组真正落住，才说明这堂训练课真实发生了

---

## 4. 为什么本地草稿和 Session 不是两套业务

这个问题必须先解释清楚，否则后面很容易做成双轨系统。

### 正确关系

```text
Assignment -> Local Draft -> Session
```

更准确一点说：

```text
Assignment 命中候选训练
    ↓
训练端生成/恢复该次训练的本地草稿
    ↓
第一组提交成功
    ↓
正式创建/确认 Session
    ↓
本地草稿继续作为 Session 的离线镜像存在
```

### 核心原则

同一堂训练课，只允许有一套业务语义：

- 模板定义训练内容原型
- assignment 决定这堂训练“候选可做”
- session 是正式记录
- local draft 只是 session 的本地缓存/镜像/补传载体

### 不允许做成什么样

不允许把 local draft 做成：

- 一套与 session 长期并行的训练主数据
- 一套与后端 session 字段完全不同的业务结构
- 一个永远不能稳定映射回 session 的本地临时表

第一阶段里，local draft 必须从设计上保证：

- 能唯一指向某一堂候选训练
- 一旦 session 成立，能稳定绑定该 session
- 同步时以同一堂课为单位对齐，而不是漂移成两套数据

---

## 5. 本地草稿最小字段草案

第一阶段先做最小必要字段，不要过度复杂化。

## 5.1 顶层草稿对象（LocalDraft）

建议最少包含以下字段：

| 字段 | 类型建议 | 说明 |
|---|---|---|
| `session_key` | `string` | 本地草稿唯一键，用于稳定标识这堂训练 |
| `athlete_id` | `number` | 队员 ID |
| `assignment_id` | `number \\| null` | 候选计划 ID；如果来自 assignment，则必须保留 |
| `session_id` | `number \\| null` | 后端正式 session ID；第一组成功前可以为空 |
| `session_date` | `string(date)` | 这堂训练所属日期 |
| `template_id` | `number \\| null` | 为了恢复和对齐模板来源，建议冗余保留 |
| `template_name_snapshot` | `string \\| null` | 可选快照，用于本地恢复和诊断 |
| `status` | `TrainingExecutionStatus` | 本地视角的训练执行状态 |
| `sync_status` | `SyncStatus` | 当前同步状态 |
| `pending_operations` | `LocalDraftSyncOperation[]` | 待补传的单组操作队列 |
| `current_item_id` | `number \\| null` | 当前正在录入的动作项 |
| `items` | `LocalDraftItem[]` | 本地动作项镜像 |
| `notes` | `string` | 训练级备注，和 session 对齐 |
| `last_modified_at` | `string(datetime)` | 本地最后修改时间 |
| `last_synced_at` | `string(datetime) \\| null` | 最近一次确认同步成功时间 |
| `device_id` | `string` | 设备标识，用于冲突识别 |
| `version` | `number` | 本地草稿版本号，用于重试和覆盖判断 |

当前已经落地的持久化同步状态用到：

- `synced`
- `pending`
- `manual_retry_required`

界面层如果需要“正在同步”提示，当前由页面局部 loading 状态承担，不再把 `sync_error` 作为第一阶段文档中的统一持久化状态。

### 推荐的 `session_key`

第一阶段建议直接采用**可稳定复原的组合键**生成：

```text
draft:{athlete_id}:{assignment_id}:{session_date}
```

如果未来允许无 assignment 训练，再扩展为：

```text
draft:{athlete_id}:{source}:{source_id}:{session_date}
```

当前阶段先不要过度设计。

---

## 5.2 动作项镜像（LocalDraftItem）

建议最少包含：

| 字段 | 类型建议 | 说明 |
|---|---|---|
| `session_item_id` | `number \\| null` | 后端 session item ID；正式 session 建立后回填 |
| `template_item_id` | `number \\| null` | 对应模板项 ID |
| `exercise_id` | `number` | 动作 ID |
| `sort_order` | `number` | 顺序 |
| `status` | `pending \\| in_progress \\| completed` | 动作项状态 |
| `prescribed_sets` | `number` | 计划组数 |
| `prescribed_reps` | `number \\| null` | 计划次数 |
| `initial_load_mode` | `string \\| null` | 负荷方式快照 |
| `initial_load_value` | `number \\| null` | 负荷值快照 |
| `enable_auto_load` | `boolean` | 是否启用自动调重 |
| `records` | `LocalDraftSetRecord[]` | 本地组记录镜像 |
| `last_modified_at` | `string(datetime)` | 该动作项最后修改时间 |

---

## 5.3 组记录镜像（LocalDraftSetRecord）

建议最少包含：

| 字段 | 类型建议 | 说明 |
|---|---|---|
| `record_key` | `string` | 本地记录唯一键 |
| `record_id` | `number \\| null` | 后端 SetRecord ID；同步成功后回填 |
| `set_number` | `number` | 第几组 |
| `weight` | `number \\| null` | 重量 |
| `reps_completed` | `number \\| null` | 完成次数 |
| `rir` | `number \\| null` | RIR |
| `completed_at` | `string(datetime)` | 本组完成时间 |
| `dirty` | `boolean` | 是否待同步 |
| `last_modified_at` | `string(datetime)` | 最后修改时间 |

### 为什么必须有 `dirty`

因为第一阶段的同步策略是：

- 每录完一组先写本地
- 后台再尝试增量补传

所以至少要能明确：

- 哪些组已经同步
- 哪些组仍待同步

---

## 6. 本地草稿与正式 Session 的一致性规则

这是第一阶段最核心的设计约束。

## 6.1 一对一关系

在第一阶段，同一堂训练课应满足：

- 一个 `assignment + athlete + session_date`
- 对应一份本地草稿
- 最终对应一条正式 session

也就是说：

```text
1 Local Draft  <->  1 Session
```

本地草稿是 session 的离线镜像，不允许长期一对多或多对多漂移。

---

## 6.2 来源一致

当 local draft 来源于某条 assignment 时，它必须始终保留：

- `assignment_id`
- `athlete_id`
- `session_date`

这样后续无论：

- 本地恢复
- 后端创建 session
- 后台同步
- 冲突诊断

都能回到同一堂训练课。

---

## 6.3 第一组之前：以草稿为主，还没有正式 session

在第一组提交成功之前：

- 可以有 local draft
- 可以记录当前动作、局部输入、未提交的组内容
- 但 `session_id` 允许为空
- 后端正式 session 还不应被确认成立

这一阶段的本地草稿，表示的是：

- “这堂训练正在准备开始”

而不是：

- “这堂训练已经正式开始并持久化到后端”

---

## 6.4 第一组之后：草稿与 session 进入绑定状态

当第一组提交成功后：

- 后端正式创建/确认 `session`
- 本地草稿回填 `session_id`
- 后续该草稿必须与这个 `session_id` 绑定

从这时起，一致性原则是：

- 本地草稿描述的就是该 `session` 的离线镜像
- 新增组、改单组、补录组，都先落本地草稿，再同步回同一个 session

---

## 6.5 内容一致性规则

第一阶段建议统一以下原则：

### 原则 A：本地草稿是现场录入真源

训练现场优先级最高，因此：

- 训练现场录入的最新内容先写本地
- 后台再补传

### 原则 B：绝大多数情况下以后写入的本地草稿为准

当后端 session 与本地草稿不一致时：

- 默认以本地草稿的最终版本覆盖后端

前提是：

- 它来自当前录入设备的连续训练过程
- 没有检测到明显多端冲突

### 原则 C：明显冲突必须可见

如果发现：

- 不同设备在同一 session 上短时间内修改同一组
- 本地版本明显落后于后端已确认版本

则不能静默覆盖，必须至少做到：

- 写入 `training_sync_conflicts` 记录明显冲突
- 在整课兜底长期失败时进入 `manual_retry_required`
- 让教练 / 管理端能看到“同步异常，待处理”或冲突提示

第一阶段当前统一口径为：

- 明显冲突写日志并可见
- 长时间失败转人工重试，而不是继续发明新的持久化状态名

---

## 6.6 状态一致性规则

local draft 与 session 的状态关系建议如下：

| 场景 | Local Draft 状态 | Session 状态 |
|---|---|---|
| 已命中计划但尚未正式开始 | `not_started` | `not_started` 或未正式开始占位 |
| 第一组已提交 | `in_progress` | `in_progress` |
| 全部完成 | `completed` | `completed` |
| 触发跨日收口时一组未做 | `absent` | `absent` |
| 触发跨日收口时部分完成 | `partial_complete` | `partial_complete` |

### 关键原则

- `not_started` 是当前 local draft / 训练执行状态 / session 占位统一使用的未开始状态
- 但它不代表“打开计划就已经正式开始训练”

---

## 7. 第一阶段推荐的同步策略边界（只定边界，不写实现）

这一步不写一堆同步代码，但要先把边界说清楚。

## 7.1 训练端写入顺序

推荐固定为：

```text
录入一组
  -> 写本地草稿
  -> 标记 dirty
  -> 后台尝试补传
  -> 成功后清 dirty / 更新 last_synced_at
```

## 7.2 同步粒度

第一阶段推荐：

1. 优先增量补传（按组记录同步）
2. 若增量链路不稳定，允许整堂课覆盖同步兜底

### 当前已落地的兜底规则

- 正常情况下优先走单组增量补传
- 当增量补传连续失败达到阈值时，自动切换到整堂课覆盖同步兜底
- 教练也可以在训练页手动触发整课补传
- 整课补传默认以本地草稿最终结果为准覆盖后端
- 如果发现“服务端已在上次确认基线之后发生变化”，会记录冲突日志，并在训练回看页提示复核

当前仍然**没有**进入复杂合并算法和冲突人工处理工作流，这部分留到后续阶段。

---

## 8. 第一阶段后的扩展设计参考（当前不代表已落地）

这一步只保留后续扩展参考，不代表当前仓库已经落地对应数据库迁移。

当前真实实现仍然是：

- 本地草稿保存在浏览器 `localStorage`
- 后端只为同步异常与冲突落最小记录

## 8.1 如后续需要把草稿正式落库，可考虑：`session_local_drafts`

### 用途

作为后续版本的正式本地草稿镜像承载表；当前第一阶段**未实现**。

### 建议字段

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `session_key` | 本地草稿唯一键，唯一索引 |
| `athlete_id` | 队员 |
| `assignment_id` | 计划分配 |
| `session_id` | 后端正式 session，可空 |
| `session_date` | 训练日期 |
| `status` | 训练执行状态 |
| `sync_status` | 同步状态 |
| `device_id` | 设备标识 |
| `version` | 版本号 |
| `payload_json` | 本地草稿完整镜像 |
| `last_modified_at` | 最后修改时间 |
| `last_synced_at` | 最后同步成功时间 |
| `created_at` | 创建时间 |

### 为什么建议先用 `payload_json`

第一阶段重点是把训练链路做稳，不是先设计一整套复杂本地草稿拆表。

因此：

- 顶层先一张 draft 表
- 详细内容先放 `payload_json`

就足够支撑：

- 本地恢复
- 补传
- 冲突诊断

后续如果稳定后，再拆成更细表结构。

---

## 8.2 可选新增字段建议：`training_sessions.sync_status`

### 用途

让正式 session 自身也能带一个后端视角同步标识。

### 建议取值

- `pending`
- `synced`
- `manual_retry_required`

### 是否第一阶段立刻落地

可以，但不是这一步必须马上加表的内容。  
当前阶段先把 local draft 表结构设计清楚更重要。

---

## 8.3 可选新增字段建议：`training_sessions.source_session_key`

### 用途

把正式 session 与最初本地草稿稳定关联起来。

### 价值

- 故障恢复
- 同步补传
- 冲突排查
- 日志追踪

### 是否第一阶段立刻落地

建议作为正式实现时优先考虑，但本轮先不落迁移。

---

## 9. 当前代码与该设计的主要差距

当前代码已经从“打开计划即正式开始”的旧实现，收口为：

```text
openPlanSession()
  -> 后端直接 get_or_create_session_for_assignment()
  -> 返回一个 `not_started` session 占位
  -> 训练端按 `session_key` 维护和恢复本地草稿
  -> 第一组提交成功或后续补传成功后，再正式进入 `in_progress`
```

对应文件：

- `frontend/src/stores/training.ts`
- `frontend/src/utils/trainingDraft.ts`
- `backend/app/services/session_service.py`

这意味着当前已经补齐：

1. 本地草稿层
2. `session_key`
3. 持久化 `sync_status`（`synced / pending / manual_retry_required`）
4. `pending_operations` 单组补传队列
5. “第一组成功后才正式进入 `in_progress`” 的状态切换机制
6. 教练端 / 管理端最小同步异常可见性

当前仍保留的阶段性差距是：

1. 复杂冲突处理界面还没有落地
2. 当前本地草稿仍然只是浏览器本地方案，不具备跨设备强持久化
3. 训练入口打开计划时仍会拿到 `not_started` 占位 session，而不是完全无 session 行的最终形态

所以第一阶段后续真正该继续收的是：

- 教练端 / 管理端同步可见性
- 长时间失败后的待处理状态
- 更完整的同步冲突处理入口
- 冲突日志后的人工确认工作流

---

## 10. 这份设计文档的结论

可以把第一阶段本地草稿与 session 的关系概括成一句话：

> 本地草稿不是第二套训练系统，而是正式 session 在训练现场的离线镜像；  
> 第一组提交成功之前，它以 assignment 为锚存在；第一组成功之后，它以 session 为锚继续存在。

第一阶段只要守住这条线，后面的同步、恢复、冲突处理、日志和备份机制都还有清晰落点。
