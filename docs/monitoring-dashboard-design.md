# Monitoring Dashboard Design

## 1. 目标

监控端是第二阶段的只读看板入口，核心目标是让教练在训练过程中快速看到：

- 当天训练日期
- 当前队伍范围
- 每名运动员当前训练状态
- 当前动作或最近动作
- 已完成动作数 / 总动作数
- 已完成组数 / 总组数
- 最新一组训练数据
- 同步异常和待人工处理项

第一版优先做到“看清现场”，不替代训练端录入。

## 2. 与其他端的边界

### 训练端

- 训练端负责录入、本地草稿、增量同步和手动补传
- 监控端不负责录入，不直接修改训练课
- 监控端可以跳转到训练记录详情，但不接管训练端主流程

### 管理端

- 管理端负责配置、回看、日志、备份恢复和课后修正
- 监控端只展示当天现场状态，不做复杂配置
- 同步异常的最终处理仍保留在管理端和训练端相关链路

### 报告端

- 报告端负责历史统计、趋势和课后分析
- 监控端只看当天或当前训练时段，不做深度图表分析

## 3. 第一版页面模块

第一页只做最小闭环，推荐包含：

1. 顶部栏
   日期筛选、队伍筛选、手动刷新、更新时间
2. 队伍汇总区
   当天各队伍人数、状态数量、同步异常数量
3. 运动员状态看板
   按队伍或筛选条件展示运动员卡片
4. 异常提醒区
   同步异常、未开始、长时间未更新等提醒
5. 跳转入口
   跳转到训练记录详情或管理端相关详情页

## 4. 推荐后端接口

### GET `/api/monitoring/today`

当前第一版已新增该接口骨架，用于支撑“今日训练状态看板”的只读数据链路。

用途：

- 返回当天训练现场主看板所需数据
- 优先服务监控端首页的运动员卡片和顶部汇总
- 状态判断基于当天所有有效计划聚合，不只看已有训练课

推荐返回字段：

```json
{
  "session_date": "2026-04-26",
  "updated_at": "2026-04-26T10:22:11+08:00",
  "teams": [
    {
      "team_id": 1,
      "team_name": "一队",
      "athlete_count": 18
    }
  ],
  "athletes": [
    {
      "athlete_id": 101,
      "athlete_name": "张三",
      "team_id": 1,
      "team_name": "一队",
      "session_id": 9001,
      "session_status": "in_progress",
      "sync_status": "pending",
      "current_exercise_name": "深蹲",
      "completed_items": 2,
      "total_items": 5,
      "completed_sets": 8,
      "total_sets": 15,
      "latest_set": {
        "actual_weight": 100,
        "actual_reps": 5,
        "actual_rir": 2,
        "completed_at": "2026-04-26T10:20:02+08:00"
      },
      "alert_level": "warning",
      "alert_reasons": [
        "本地数据待同步"
      ],
      "has_alert": true
    }
  ]
}
```

状态聚合规则：

- 没有当天有效计划：`no_plan`
- 有计划，但所有计划都没有记录：`not_started`
- 有任意记录，但不是所有当天有效计划的目标组数都完成：`in_progress`
- 所有当天有效计划的所有目标组数均完成：`completed`
- 有训练课已手动结束为 `partial_complete` 时，整体状态优先显示 `partial_complete`
- 所有当天有效计划都已最终收口为 `absent`：`absent`
- 同一运动员当天多份 active assignment 会合并计算 `completed_sets / total_sets` 和 `completed_items / total_items`
- 没有 session 的 assignment 仍计入 `total_sets` 和 `total_items`，避免一份已完成计划掩盖另一份未开始计划

异常提醒规则：

- `manual_retry_required`：`critical`，同步异常待处理
- `pending`：`warning`，本地数据待同步
- `partial_complete`：`warning`，已结束未完成
- `absent`：`warning`，缺席
- `not_started` 且训练开始超过 30 分钟仍未开始：`warning`
- `in_progress` 且最近一组距离当前时间超过 20 分钟：`warning`
- 最新一组 `RIR <= 0`：`warning`
- 主项最近一组 `RIR >= 4`：`info`
- `completed_sets > total_sets`：`warning`
- `has_alert` 兼容旧前端，当前等价于 `alert_level != "none"`

### GET `/api/monitoring/team-summary`

用途：

- 返回按队伍聚合的当天训练状态汇总
- 用于顶部统计区或队伍总览卡片

推荐返回字段：

```json
{
  "session_date": "2026-04-26",
  "updated_at": "2026-04-26T10:22:11+08:00",
  "teams": [
    {
      "team_id": 1,
      "team_name": "一队",
      "total_athletes": 18,
      "not_started_count": 6,
      "in_progress_count": 7,
      "completed_count": 3,
      "partial_complete_count": 1,
      "absent_count": 1,
      "pending_sync_count": 2,
      "manual_retry_required_count": 1
    }
  ]
}
```

### GET `/api/monitoring/athlete-detail`

当前第一版新增该只读接口，用于队员详情覆盖层按需加载“本次训练”完整明细，不把动作和组记录塞进 `/api/monitoring/today`。

参数：

- `session_date`：训练日期，必填
- `athlete_id`：运动员 ID，必填

用途：

- 返回指定队员当天所有有效训练计划
- 每份计划独立展示训练课状态、动作进度、组数进度
- 每个动作展示目标组数、目标次数、目标重量或目标说明
- 每个动作展示已完成的每组记录，包括实际重量、实际次数、RIR、完成时间、备注
- 当 assignment 尚未创建 session 时，仍从 template items 构建动作列表，records 为空
- 当同一天有多份有效 assignment 时，按 assignment 分组返回
- `session_status` 与 `/api/monitoring/today` 复用同一套状态判断口径

推荐返回字段：

```json
{
  "session_date": "2026-04-26",
  "updated_at": "2026-04-26T10:22:11+08:00",
  "athlete_id": 101,
  "athlete_name": "张三",
  "team_id": 1,
  "team_name": "一队",
  "session_status": "in_progress",
  "sync_status": "synced",
  "alert_level": "none",
  "alert_reasons": [],
  "has_alert": false,
  "assignments": [
    {
      "assignment_id": 301,
      "template_id": 12,
      "template_name": "下肢力量 A",
      "session_id": 9001,
      "session_status": "in_progress",
      "completed_items": 1,
      "total_items": 4,
      "completed_sets": 3,
      "total_sets": 12,
      "exercises": [
        {
          "item_id": 5001,
          "exercise_id": 8,
          "exercise_name": "深蹲",
          "sort_order": 1,
          "prescribed_sets": 4,
          "prescribed_reps": 5,
          "target_weight": 100,
          "target_note": null,
          "is_main_lift": true,
          "status": "in_progress",
          "completed_sets": 2,
          "records": [
            {
              "id": 7001,
              "set_number": 1,
              "target_weight": 100,
              "target_reps": 5,
              "actual_weight": 100,
              "actual_reps": 5,
              "actual_rir": 2,
              "completed_at": "2026-04-26T10:20:02+08:00",
              "notes": null
            }
          ]
        }
      ]
    }
  ]
}
```

## 5. 第一版展示字段建议

监控端第一版优先展示：

- `session_date`
- `team_id`
- `team_name`
- `athlete_id`
- `athlete_name`
- `session_id`
- `session_status`
- `sync_status`
- `current_exercise_name`
- `completed_items`
- `total_items`
- `completed_sets`
- `total_sets`
- `latest_set.actual_weight`
- `latest_set.actual_reps`
- `latest_set.actual_rir`
- `latest_set.completed_at`
- `alert_level`
- `alert_reasons`
- `has_alert`
- `updated_at`

接口类型约束：

- `session_status` 在后端 schema 中收紧为 `no_plan / not_started / in_progress / completed / partial_complete / absent`
- `sync_status` 在后端 schema 中收紧为 `synced / pending / manual_retry_required`
- `alert_level` 在后端 schema 中收紧为 `none / info / warning / critical`
- API 返回字段结构保持不变，类型约束用于防止监控端状态字符串继续发散

## 6. 第一版明确不做

- 不做训练记录编辑
- 不做批量结束课程
- 不做批量补录
- 不做模板修改
- 不做动作库修改
- 不做复杂统计图表
- 不做 AI 分析
- 不做 WebSocket 强实时要求

第一版坚持：

- 只读展示
- 手动刷新 + 后续可扩展轮询
- 跳转到已有训练记录或管理端页面

## 7. 当前前端组件骨架

第一版页面拆分为：

- `MonitorDashboardView.vue`：负责日期、队伍、加载数据、手动刷新和向子组件传参
- `MonitoringSummaryCards.vue`：负责状态汇总卡片
- `MonitoringAthleteBoard.vue`：负责运动员看板容器
- `MonitoringAthleteCard.vue`：负责单个运动员状态卡片
- `MonitoringAthleteDetailOverlay.vue`：负责当前页居中大卡片详情覆盖层
- `MonitoringAlertPanel.vue`：负责同步异常、未完成和现场过程异常提醒

刷新策略：

- 当前默认仍是手动刷新
- 页面提供“开启自动刷新 / 关闭自动刷新”按钮
- 自动刷新默认间隔为 30000ms
- 页面隐藏时暂停自动刷新，页面重新可见后恢复
- 自动刷新失败不弹窗，只在顶部状态显示“最近刷新失败，数据可能不是最新”
- 组件卸载时清理 timer，避免长期停留或切换页面后继续请求

## 8. 当前排序与详情交互规则

运动员卡片排序：

- `alert_level = critical`
- `alert_level = warning`
- `alert_level = info`
- `in_progress`
- `not_started`
- `partial_complete`
- `absent`
- `completed`
- `no_plan`
- 同优先级内按姓名升序
- 排序规则集中在 `frontend/src/utils/monitoringSort.ts`，页面不再维护独立优先级表

点击队员卡片：

- 不离开 `/monitor`
- 不展开摘要卡片，不撑开运动员看板 grid
- 在当前页面上方显示居中的大卡片详情覆盖层
- 覆盖层四周保留空白，点击空白关闭
- 点击详情卡片内部不关闭
- 按 Escape 可以关闭
- 自动刷新后，如果当前队员仍在筛选范围内，详情层继续显示并使用最新数据；如果不在当前筛选范围，详情层自动关闭

详情覆盖层会在打开时请求 `/api/monitoring/athlete-detail`，不影响底层看板布局和自动刷新。

详情覆盖层展示：

- 队员姓名、队伍、今日状态、同步状态
- 完成动作数 / 总动作数、完成组数 / 总组数
- 按 assignment 分组的训练计划名称、训练课状态、动作进度、组数进度
- 每个动作的动作名、主项标识、目标组数、目标次数、目标重量或目标说明、动作状态
- 每个动作已完成的每组记录：目标重量、目标次数、实际重量、实际次数、RIR、完成时间、备注
- 未完成动作显示“暂无完成组记录”，未录满动作显示剩余未完成组数
- `no_plan`、`manual_retry_required`、`partial_complete`、`absent` 的轻量提示

详情覆盖层按钮：

- `关闭`：只关闭覆盖层
- `查看训练报告`：跳转训练报告页，并带当天日期查询参数
- `进入训练记录页`：仅存在 `session_id` 时显示，点击后跳转训练记录页

## 9. 当前验收脚本

新增 `backend/scripts/monitoring_smoke_check.py`，使用临时 SQLite 数据库构造监控端状态矩阵，不读取也不污染真实 `backend/training.db`。

覆盖样本：

- `no_plan`
- `not_started`
- `in_progress`
- `completed`
- `partial_complete`
- `absent`
- `manual_retry_required`
- `pending`
- `not_started` 超时
- `in_progress` 长时间未更新
- 最近一组 `RIR <= 0`
- 主项最近一组 `RIR >= 4`
- 实际组数超过计划组数
- 同日多计划：一份计划已完成，另一份计划未开始，整体预期不能显示为 `completed`

脚本验证：

- `session_status` 分布
- `sync_status`
- `completed_sets / total_sets`
- `completed_items / total_items`
- `latest_set`
- `alert_level / alert_reasons`
- `MonitoringTodayRead` schema 结构

统一验收：

- `scripts/phase1_acceptance_check.ps1` 已纳入 `Monitoring status aggregation smoke check`
- 该步骤失败时，第一阶段整体验收失败
