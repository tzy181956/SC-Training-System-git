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
      "has_alert": true
    }
  ]
}
```

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
- `has_alert`
- `updated_at`

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
- `MonitoringAlertPanel.vue`：负责同步异常和未完成提醒

刷新策略：

- 当前只启用手动刷新
- 页面已预留 `autoRefreshEnabled` 和 `refreshIntervalMs`
- 自动刷新后续再接入，第一版不默认开启

## 8. 当前排序与跳转规则

运动员卡片排序：

- 同步异常 `manual_retry_required`
- `in_progress`
- `not_started`
- `partial_complete`
- `absent`
- `completed`
- `no_plan`
- 同优先级内按姓名升序

点击跳转：

- `in_progress` 且有 `session_id`：跳转训练记录页
- `completed` / `partial_complete` / `absent`：跳转训练报告页，并带当天日期查询参数
- `not_started`：跳转训练端并保留当前日期查询参数
- `no_plan`：不跳转，只提示当天没有有效训练计划
