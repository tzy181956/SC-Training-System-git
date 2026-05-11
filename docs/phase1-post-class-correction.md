# 第一阶段重构补充｜课后修改、补录与状态重算

> 文档状态：当前有效专题  
> 当前用途：说明课后修正、补录与状态重算的基础边界。  
> 注意：权限与入口以当前登录制实现和管理端代码为准。  

## 1. 这一步只解决什么

本文件只记录第一阶段中的“课后修正最小闭环”，目标是：

1. 教练可以在管理端修正真实录入错误。
2. 教练可以补录漏掉的组。
3. 所有课后修改都必须有日志。
4. 修改后训练课状态自动重算，避免前后不一致。

本步不展开：

- 审批流
- 复杂权限系统
- 补练场景

---

## 2. 管理端入口

当前课后修改入口沿用训练回看链路，不另起大页面：

- 页面：`frontend/src/views/TrainingReportsView.vue`
- 训练课卡片：`frontend/src/components/report/TrainingSessionCard.vue`
- API：`frontend/src/api/trainingReports.ts`

后端入口：

- `PATCH /api/training-reports/set-records/{record_id}`
- `POST /api/training-reports/session-items/{item_id}/sets`
- `DELETE /api/training-reports/set-records/{record_id}`

对应实现：

- `backend/app/api/endpoints/training_reports.py`
- `backend/app/services/session_service.py`

---

## 3. 本步允许的课后修改范围

### 3.1 修改已有组

教练可修改：

- 重量 `actual_weight`
- 次数 `actual_reps`
- RIR `actual_rir`
- 备注 `notes`

### 3.2 补录漏掉的组

教练可对某个动作补录新组，最小字段仍是：

- 重量
- 次数
- RIR
- 可选备注

### 3.3 删除误录组

若某组是明显误录，允许删除；删除同样属于危险操作，会写危险操作日志。

---

## 4. 修改后自动重算规则

课后修改不是只改一行数值，而是要立即收口到整堂课状态。

本步修改后会自动触发：

1. 当前动作完成情况重算
2. 整堂训练课状态重算

重算目标仍遵守第一阶段状态流：

- `not_started`
- `in_progress`
- `completed`
- `absent`
- `partial_complete`（代码层当前仍沿用该内部值）

重算意义：

- 教练补录一组后，原本未完成的课可能变成完成
- 教练删掉一组后，原本完成的课也可能回退成未完全完成

---

## 5. 日志落点

### 5.1 课后修改日志

本步的课后修正日志写入：

- 表：`training_session_edit_logs`
- 模型：`backend/app/models/training_edit_log.py`

记录内容至少包含：

- `session_id`
- `session_item_id`
- `set_record_id`
- `action_type`
- `actor_name`
- `object_type / object_id`
- `summary`
- `before_snapshot`
- `after_snapshot`
- `edited_at`

### 5.2 危险操作日志

删除误录组同时会写入：

- 表：`dangerous_operation_logs`

这是因为“删训练记录”属于第一阶段定义的危险操作。

---

## 6. 关键文件

本步相关的主要文件如下：

- `backend/app/models/training_edit_log.py`
- `backend/app/services/session_service.py`
- `backend/app/api/endpoints/training_reports.py`
- `backend/app/services/training_report_service.py`
- `frontend/src/api/trainingReports.ts`
- `frontend/src/components/report/TrainingSessionCard.vue`
- `frontend/src/views/TrainingReportsView.vue`

---

## 7. 失败处理

本步的失败处理要求很明确：

1. 单次修改失败，不影响原训练记录继续保留。
2. 日志写入与训练记录修改在同一后端事务里完成，避免“改了数据没日志”。
3. 删除组记录前先做危险操作备份，防止误删后完全无兜底。

---

## 8. 人工验收

1. 进入训练回看页，选中一堂已有训练记录的课。
2. 修改某一组的重量 / 次数 / RIR。
3. 确认页面回显更新，且训练课状态如预期重算。
4. 对某个动作补录一组。
5. 确认该动作完成情况和整堂课状态发生对应变化。
6. 删除一组误录记录。
7. 确认：
   - 需要危险操作确认
   - 删除后状态重新计算
   - 日志中可查到修改 / 补录 / 删除记录

---

## 9. 技术自测

本步最小技术自测应覆盖：

1. 修改已有组后，`training_session_edit_logs` 成功写入。
2. 补录新组后，`training_session_edit_logs` 成功写入。
3. 删除组后，同时存在：
   - 训练修改日志
   - 危险操作日志
4. 修改 / 补录 / 删除之后，session 状态自动重算。

---

## 10. 当前边界

本步仍未解决：

- 谁可以改哪支队伍的训练记录
- 是否需要审批通过后才生效
- 多人同时修改同一堂课的冲突裁决

第一阶段先保证“能改、可追溯、状态一致”，不把问题扩成权限和审批系统。
