# 第一阶段重构补充｜日志页基础版

## 1. 这一步只解决什么

本文件只记录第一阶段中的“日志页基础版”，目标是：

1. 先让系统能查：
   - 谁改了什么
   - 哪些课被课后改过
   - 哪些同步失败过
   - 哪些危险操作执行过
2. 日志数据统一由后端提供，不允许前端临时拼接。
3. 前端只负责筛选和展示，不负责拼接多表逻辑。

本步不展开：

- 图表分析页
- 审计大屏
- 复杂统计报表

---

## 2. 统一日志接口

本步新增统一查询接口：

- `GET /api/logs`

支持筛选参数：

- `date_from`
- `date_to`
- `actor_name`
- `object_type`
- `limit`

核心文件：

- `backend/app/api/endpoints/logs.py`
- `backend/app/services/log_service.py`
- `backend/app/schemas/logs.py`

---

## 3. 日志来源

统一日志接口当前聚合以下几类真实后端数据：

1. 内容修改日志
   - 表：`content_change_logs`
   - 作用：模板 / 动作库 create / update 等普通修改记录
2. 训练课课后修改日志
   - 表：`training_session_edit_logs`
   - 作用：课后补录、修改、删除训练组记录
3. 同步异常日志
   - 表：`training_sync_issues`
4. 同步冲突日志
   - 表：`training_sync_conflicts`
5. 危险操作日志
   - 表：`dangerous_operation_logs`

这满足第一版要求的覆盖范围：

- 模板 / 动作库修改
- 训练课课后补录 / 修改
- 同步失败 / 冲突
- 危险操作

---

## 4. 新增的数据结构

### 4.1 `content_change_logs`

本步新增：

- 模型：`backend/app/models/content_change_log.py`
- 迁移：`backend/alembic/versions/20260424_c7d8e9f0a1b2_add_content_change_logs_and_user_team_id.py`

用途：

- 记录模板和动作的普通修改
- 让日志页不仅能看到“删除了什么”，还能看到“修改了什么”

主要字段：

- `action_type`
- `object_type`
- `object_id`
- `object_label`
- `actor_name`
- `team_id`
- `summary`
- `before_snapshot`
- `after_snapshot`
- `extra_context`

### 4.2 `users.team_id`

本步同时在 `users` 上补了：

- `team_id`

目的不是立即重做权限系统，而是给“教练仅看自己队伍日志”预留后端过滤基础。

当前边界也要写清楚：

- 仓库现阶段仍以免登录模式运行为主
- `users` 表当前没有真实在线登录链路在使用
- 所以**结构已经补好，但当前运行默认仍是全量可见**

---

## 5. 模板 / 动作日志如何接入

本步新增内容修改日志写入服务：

- `backend/app/services/content_change_log_service.py`

并把以下写入点接到了真实业务服务中：

### 模板侧

- `backend/app/services/plan_service.py`
  - `create_template`
  - `update_template`
  - `add_template_item`
  - `update_template_item`

### 动作侧

- `backend/app/services/exercise_service.py`
  - `create_exercise`
  - `update_exercise`

这样日志页能查到“新建 / 修改模板、模板动作、动作”的普通操作，不再只覆盖删除。

---

## 6. 训练修改 / 同步 / 危险操作如何进入日志页

这三类日志没有新造第二套表，而是直接复用已有结构：

- `training_session_edit_logs`
- `training_sync_issues`
- `training_sync_conflicts`
- `dangerous_operation_logs`

统一聚合服务 `log_service.list_logs()` 会把它们标准化为同一响应结构：

- 时间
- 操作人
- 对象类型
- 影响对象
- 队伍 / 运动员 / 训练课上下文
- 关键前后变更

---

## 7. 前端页面

前端本步新增：

- API：`frontend/src/api/logs.ts`
- 页面：`frontend/src/views/LogsView.vue`
- 路由：`frontend/src/router/index.ts`
- 导航入口：`frontend/src/components/layout/AppShell.vue`

页面功能保持第一阶段风格，优先实用：

1. 按时间筛选
2. 按操作人筛选
3. 按对象类型筛选
4. 展示日志明细
5. 在明细里展开查看 `before / after` 快照

不做图表，不做复杂排序，不做复杂筛选器。

---

## 8. 权限边界

### 8.1 已做好的结构

后端统一日志接口已经支持按当前用户做最小过滤：

- `admin`：可看全部
- `coach`：按 `team_id` 过滤

相关代码：

- `backend/app/models/user.py`
- `backend/app/api/deps.py`
- `backend/app/api/endpoints/auth.py`
- `backend/app/services/log_service.py`

### 8.2 当前实际运行边界

但当前项目的实际运行仍有一个现实限制：

- 现在主要还是免登录模式
- `users` 表当前没有被真实登录流程持续使用

所以本步的真实落地状态是：

- **后端结构已支持队伍过滤**
- **当前默认运行模式仍以全量可见为主**

这不是漏做，而是当前身份源还没真正接上。

---

## 9. 关键文件

本步新增或关键修改文件如下：

- `backend/app/models/content_change_log.py`
- `backend/app/schemas/logs.py`
- `backend/app/services/content_change_log_service.py`
- `backend/app/services/log_service.py`
- `backend/app/api/endpoints/logs.py`
- `backend/app/services/plan_service.py`
- `backend/app/services/exercise_service.py`
- `backend/alembic/versions/20260424_c7d8e9f0a1b2_add_content_change_logs_and_user_team_id.py`
- `frontend/src/api/logs.ts`
- `frontend/src/views/LogsView.vue`
- `frontend/src/router/index.ts`
- `frontend/src/components/layout/AppShell.vue`

---

## 10. 人工验收

1. 进入管理端 `/logs` 页面。
2. 分别按：
   - 时间
   - 操作人
   - 对象类型
   做筛选，确认结果变化正常。
3. 在模板页改一个模板，再回到日志页，确认能查到模板修改日志。
4. 在动作库页改一个动作，再回到日志页，确认能查到动作修改日志。
5. 在训练回看页改一组或补录一组，再回到日志页，确认能查到课后修改日志。
6. 查看已有同步异常 / 冲突，确认日志页能查到对应记录。
7. 执行一个危险操作后，确认日志页能查到危险操作记录。

---

## 11. 技术自测

本步最小技术自测应覆盖：

1. 后端编译通过：`python -m compileall backend/app`
2. 前端构建通过：`npm run build`
3. 临时库迁移后，`GET /api/logs` 可正常返回结果
4. 在临时库中创建动作和模板后，日志接口能查到对应 `content_change` 记录

---

## 12. 当前边界

本步仍未解决：

- 日志分页和复杂排序
- 完整的教练 / 管理员真实权限闭环
- 图表化审计分析

第一阶段先把“查得到、来源清楚、可追溯”收紧，不把日志页扩成分析平台。
