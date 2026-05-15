# CHANGELOG

## Unreleased / V1-dev

### Documentation

- 重修根目录权威文档与协作文档口径：
  - `README.md`
  - `PROJECT_CONTEXT.md`
  - `CURRENT_STATUS.md`
  - `DEVELOPMENT_GUIDE.md`
  - `CODEX_HANDOFF.md`
  - `NEXT_STEPS.md`
- 文档主叙事已从“免登录 + 局域网本地主场景”切换为“登录制 + 服务器运行 + 本地开发并行”。
- 统一说明当前正式数据库演进路径为 Alembic + `backend/scripts/migrate_db.py`，不再把 `schema_sync.py` / `init_db.py` 写成正式主方案。

### Fixed

- 修复后端真实启动时 `/ready/deep` Alembic head 检查误把 `alembic.ini` 定位到仓库根目录的问题，恢复深度就绪检查对后端迁移配置的正常读取。
- 修复 `backend/scripts/create_user.py` 仍使用旧 `team_id / allow_teamless_role` 参数导致临时账号创建失败的问题，改为当前账号服务使用的 `sport_id / allow_sportless_role`。
- 修复训练端组记录数字输入在真实浏览器中会把 `v-model` 值转成数字，导致提交时调用 `.trim()` 崩溃的问题，恢复平板端第一组录入能力。
- 修复整课覆盖同步签名把数据库 naive datetime 和前端 UTC datetime 视为不同内容的问题，避免无真实远端修改时误报 `409 Conflict`。
- 修复训练端断网录入后刷新页面时，带 `assignmentId / athleteId / sessionDate` 的训练课恢复路径会跳过本地草稿判断，导致未同步组记录被服务器旧快照覆盖的问题。
- 修复整课覆盖同步冲突在返回 `409` 时同步异常 / 冲突记录被事务回滚的问题，确保 `manual_retry_required` 可被教练或管理员后续处理。
- 修复训练端 / 监控端 GET 接口仍可能隐式触发跨日收口写库的问题；只读接口保持只读，兜底收口改由启动、显式维护接口和非 GET 训练入口承担。
- 修复前端开发服务器下登录请求误打到 `5173/api/*` 自身导致 `404` 的问题：`frontend/vite.config.ts` 和 `frontend/scripts/dev-server.mjs` 已补 `/api -> http://127.0.0.1:8000` 开发代理，登录页不再因为前后端端口分离而直接报 `Request failed with status code 404`。

- 修复 `backend/app/services/__init__.py` 的包级联导入导致的循环依赖，恢复 `scripts/phase1_acceptance_check.ps1` 中 `Backend phase1 smoke` 的通过能力，避免 `schema_sync -> services.__init__ -> backup_service` 启动链路再次被阻塞。
- 修复 `backend/scripts/phase1_backend_smoke_check.py` 对固定日期 `2099-01-01` 的过时假设，改为按 assignment 当前日期窗口和 `repeat_weekdays` 自动选择有效训练日，并在失败路径统一释放数据库连接，避免验收脚本被新训练日规则或 SQLite 文件锁误伤。

### Added

- 新增最小多账号与管理员账号体系闭环：
  - 后端补齐 `backend/scripts/create_user.py` 首个管理员交互式创建链路，以及 `/api/users`、`/api/users/{id}`、`/api/users/{id}/reset-password` 管理员专用账号管理接口
  - `/api/auth/me` 已扩展为前端统一权限来源，返回 `role_code`、`team_id`、`mode`、`available_modes`、`can_manage_users`、`can_manage_system`
  - 前端接入真实登录态：`access_token` 持久化、统一 Bearer 注入、`401` 清理登录态、登录页表单、受保护路由守卫、管理员账号管理页 `/users`
  - 三套 shell 已补充最小退出登录入口，管理端导航和部分页面按 `admin / coach / training` 做入口收口
  - 本轮继续补齐 admin 账号管理收尾：`POST /api/users/{id}/activate`、`POST /api/users/{id}/deactivate`、用户列表时间字段、前端停用二次确认，以及账号管理页独立启用/停用动作

- 新增测试数据模块的一级/二级分类主数据管理：
  - 后端新增 `test_type_definitions` / `test_metric_definitions` 主数据表、`/api/test-definitions` 接口与 Alembic 迁移，支持测试类型和测试项目的增删改，并保留历史测试记录字符串快照不受影响
  - 测试数据页改为从主数据动态加载“测试类型 / 测试项目 / 默认单位”，并在页面内提供“管理测试类型 / 管理测试项目”弹窗，可把二级分类调整到不同一级分类下
  - 测试导入模板新增“测试项目参考”工作表，按系统当前维护的一级/二级分类导出参考项

- 新增训练完成后的 Session RPE 反馈闭环：
  - 后端在 `training_sessions` 增加 `session_rpe`、`session_feedback` 字段，并复用 `completed_at`
  - 新增 `POST /api/training/sessions/{session_id}/finish-feedback`，支持重复覆盖提交整体 RPE 与备注
  - 训练端新增 `frontend/src/components/training/SessionRpeModal.vue`，支持自动弹窗、稍后填写、顶部提醒条、已提交摘要与再次修改
  - 监控端卡片 / 详情和训练报告补充 Session RPE、备注、完成时间展示
  - 整课覆盖同步快照补充 Session RPE / 备注字段，避免 full sync 时丢失训练完成反馈

- 新增监控端第一轮结构预留：
  - `frontend/src/views/MonitorDashboardView.vue`
  - `frontend/src/components/layout/MonitorShell.vue`
  - `frontend/src/types/monitoring.ts`
  - `docs/monitoring-dashboard-design.md`
- 新增监控端第一版只读数据链路与组件骨架：
  - `backend/app/api/endpoints/monitoring.py`
  - `backend/app/schemas/monitoring.py`
  - `backend/app/services/monitoring_service.py`
  - `frontend/src/api/monitoring.ts`
  - `frontend/src/mocks/monitoringTodayMock.ts`
  - `frontend/src/components/monitoring/MonitoringSummaryCards.vue`
  - `frontend/src/components/monitoring/MonitoringAthleteBoard.vue`
  - `frontend/src/components/monitoring/MonitoringAthleteCard.vue`
  - `frontend/src/components/monitoring/MonitoringAthleteDetailOverlay.vue`
  - `frontend/src/components/monitoring/MonitoringAlertPanel.vue`
- 新增监控端状态准确性 smoke check：
  - `backend/scripts/monitoring_smoke_check.py`
- 新增监控端运动员排序工具：
  - `frontend/src/utils/monitoringSort.ts`
- 监控端第一版自动刷新已接入页面开关，默认关闭，开启后按 30 秒间隔静默刷新。
- 新增监控端队员今日训练详情只读接口：
  - `GET /api/monitoring/athlete-detail`
- 新增训练端与监控端共用的公共基础：
  - `frontend/src/composables/useTeamFilter.ts`
  - `frontend/src/constants/trainingStatus.ts`

- 新增训练模式主链路、计划分配概览、批量分配预览与基础训练录入能力。
- 新增动作库结构化分类、标签筛选、维护入口与配套导入链路。
- 新增训练模式顶部局域网访问入口卡片，支持复制地址和二维码。
- 新增仓库级文本编码防线：
  - `.editorconfig`
  - `.gitattributes`
  - `scripts/check_text_encoding.py`
  - `docs/text-encoding.md`
- 新增第一阶段重构术语与边界文档：
  - `docs/phase1-terminology-and-boundaries.md`
- 新增训练课状态流重定义文档：
  - `docs/phase1-session-status-flow.md`
- 新增本地草稿与 session 关系设计文档：
  - `docs/phase1-local-draft-and-session.md`

### Changed

- 第一轮账号权限与队伍隔离已经正式接入现有训练主链：
  - `admin` 收口为超级角色；`coach` 和 `training` 未绑定 `team_id` 时访问队伍业务接口会直接得到明确 `403`
  - `athletes`、`training/*`、`monitoring/*`、`training-reports/*`、`training-loads/*`、`logs` 等接口已经按本轮方案接入最小角色和队伍边界
  - 管理端首页、动作库、运动员页和模式切换已按当前账号可用权限做最小裁剪，不再沿用免登录模式的全量入口

- 测试项目主数据已新增“低值优先（数值越小越好）”方向配置：
  - `test_metric_definitions` 新增 `is_lower_better` 字段，默认未勾选时按高值优先处理
  - 默认目录中的速度/变向/耐力计时项目会自动预设为低值优先，其他项目保持高值优先
  - 测试数据页“管理测试项目”弹窗已支持勾选方向，已有项目列表和当前趋势区会显示“低值优先 / 高值优先”提示
  - 低值优先项目的趋势图纵轴已改为反向显示，并固定从 `0` 起顶，保证数值越小的点越靠上
  - 修复低值优先项目反向纵轴下“全队区间”阴影带消失的问题，区间阴影现在会按视觉上的上边界/下边界重新计算
  - `GET /api/test-definitions` 的项目返回已补充方向字段，供后续图表、运动员测试排名和评分逻辑统一复用
- 测试数据页左侧已改为“趋势筛选优先 + 手动补录折叠区”：
  - 趋势筛选已补充项目、队伍两级过滤，运动员下拉会按当前项目/队伍条件联动收窄，右侧趋势图、全队区间与下方记录卡片同步只看当前筛选范围
  - 左侧主卡默认只显示运动员、测试类型、测试项目和日期范围筛选，日期范围留空即代表全部日期
  - 手动添加测试记录保留为折叠展开区，并复用当前左侧筛选的运动员/类型/项目作为补录对象
  - 右侧趋势图下方的数据卡片已改为只显示当前左侧趋势筛选命中的记录，不再混入同一运动员的其他测试项目
- 测试导入导出已增加“运动员编码”防重名口径：
  - `athletes` 新增全系统唯一的 `code` 字段，旧数据迁移后按 `ATH-000123` 形式自动回填；管理模式运动员页面可查看并修改编码
  - 测试导入模板主表、模板内运动员名单参考表、测试数据总库导出都已补充“运动员编码”列；导入模板中红色表头表示必填列
  - 测试 Excel 导入已改为优先按运动员编码匹配；未填编码时仅在姓名唯一时允许导入，遇到重名会明确提示先补运动员编码
- 计划分配已支持按固定星期几循环：`athlete_plan_assignments` 新增 `repeat_weekdays`，分配页可多选周一到周日，旧数据为空时按每天训练兼容；训练模式、实时模式、session 创建与训练报告统计都会按“日期范围 + 循环星期”共同判断应训练日，非应训练日不再显示计划、不再生成 session，也不计入未完成和完成率口径。
- 计划分配已允许同一队员在重叠日期内继续追加多份计划；计划分配页不再因“已有当前/后续计划”而禁止选人，同时服务端新增“同一队员 + 同一模板 + 同一开始/结束日期的 active 分配不得完全重复”的拦截与中文错误提示。
- 训练模式中间“查看计划”动作卡片已改为横向单行布局：动作名称加粗放大置左，组次重量收口到中间，训练中的完成进度收口到最右侧，默认不再额外占行显示动作备注。
- 训练模式头部筛选已补齐“训练项目”一档，并放在训练日期与训练队伍之间；项目与队伍筛选按当天可见队员联动收口，避免切换项目后仍保留无效队伍筛选。
- 运动员模块已在原页面内补齐“管理项目 / 管理队伍”弹窗入口，支持项目与队伍的新增、删除，并在删除时按“有引用即拒绝”保护运动员、模板和用户关联数据。
- Removed the training-mode bottom-right `Training Layout Debug` overlay from `frontend/src/components/layout/TrainingShell.vue`, and deleted the unused `TrainingViewportDebug` component.
- Unified user-visible mode naming across the frontend to `训练模式 / 管理模式 / 实时模式`, and mapped legacy `训练端 / 管理端 / 监控端` values to the new labels at display time.
- Froze session `completed_at` at the first Session RPE submission, and surfaced post-workout duration in management reports and realtime assignment details using existing session timing fields.
- Added persisted session duration / `sRPE` load metrics plus daily per-athlete training load snapshots, exposed a read-only training-load API skeleton, and surfaced `训练用时 / Session RPE / sRPE` in management-mode training data cards.
- Removed the redundant `监控端` entry from the management sidebar, keeping mode switching unified through the shared top-right three-segment switcher.
- Unified the training, management, and monitoring mode entry switchers into the same three-segment top-right control, reusing the monitoring-style pill switch across all three shells.
- Tightened the training `Session RPE` modal by collapsing the feedback textarea to a single-line visual footprint, enlarging the selected `RPE X/10` number display, and scaling the core controls up for easier iPad use.
- Session RPE scale buttons in the training modal now use per-value color styling across 0-10, so the clickable row matches the slider and headline color feedback.
- Session RPE copy/display is now centralized in `frontend/src/constants/sessionRpe.ts`, and the same 0-10 label/help mapping is reused by the training modal, training summary bar, monitoring views, and training report.
- `AGENTS.md` 已补充前端视觉验收硬约束：凡涉及 UI、布局、响应式或样式修改，必须启动项目并用真实浏览器或 Playwright 做修改前后视觉检查，不能只靠读代码或 `npm run build` 判断效果。
- 训练端 `Session RPE` 已填写后的展示已从大面积摘要卡片压缩为动作列表上方的紧凑横向 summary bar，修正中栏扩张挤压动作列表的问题，并保留轻量 `修改 RPE` 入口。
- `Session RPE` 输入弹窗已补充 0-10 颜色分级：大号数字、刻度高亮、滑条进度/滑块和描述标签按同一色阶从绿色过渡到黄色、橙色和红色，未选择时保持中性灰色。

- 启动器后端环境准备阶段已改为完整自修复流程：自动创建或复用 `backend/.venv`、升级 pip、按 `backend/requirements.txt` 安装依赖，并在数据库迁移前验证 `alembic.config`、`sqlalchemy`、`fastapi`；依赖缺失会归类为 `backend_dependency_missing`，不再误提示数据库被锁。
- `auth` store、前端路由和管理端导航已预留 `monitor` 独立模式与 `/monitor` 入口，不再把监控端混入现有管理页或训练页。
- `/api/monitoring/today` 已注册为监控端第一版只读接口，按日期、队伍和未分队参数聚合运动员、计划分配、训练课、组记录与同步异常。
- 前一轮为“监控端状态准确性与验收脚本收口”，未新增自动刷新、详情弹层、图表、编辑、删除或补录能力。
- 本轮继续收口监控端验收和刷新能力，不新增详情弹层、图表、大屏模式、编辑、删除或补录。
- `/api/monitoring/today` 的状态判断已按真实训练数据继续收紧：有效计划无记录为 `not_started`，有记录且不是所有当天有效计划目标组数完成为 `in_progress`，所有当天有效计划目标组数完成才是 `completed`，手动结束未完成为 `partial_complete`，全部最终缺席为 `absent`，无有效计划为 `no_plan`。
- `/api/monitoring/today` 已修正同一运动员当天多份 active assignment 的聚合风险：无 session 的 assignment 也计入 `total_sets` 和 `total_items`，避免一份计划完成时误把当天整体显示为 `completed`。
- `/api/monitoring/today` 的后端 schema 已将 `session_status` 与 `sync_status` 收紧为 Literal 枚举，接口结构保持不变。
- `MonitorDashboardView` 已从占位页改为监控端取数容器，页面展示拆到 monitoring 组件目录，并预留手动刷新以外的自动刷新状态。
- 监控端队员卡片点击已改为当前 `/monitor` 页面上的居中大卡片覆盖层，不跳转页面、不使用右侧抽屉、不展开摘要卡片，不影响看板 grid 布局。
- 监控端详情覆盖层打开时按需请求队员当天训练明细，按 assignment 分组展示所有动作、目标组数、目标次数、目标重量或目标说明，以及每组实际重量、实际次数、RIR、完成时间和备注。
- 监控端详情仍保持只读，不提供编辑、删除、补录；“查看训练报告 / 进入训练记录页”仍作为次级跳转按钮。
- `backend/scripts/monitoring_smoke_check.py` 已增强队员详情验证，覆盖未开始模板动作、完成记录、进行中未完成组、多计划展示和同步异常状态。
- 监控端运动员卡片排序已抽到 `frontend/src/utils/monitoringSort.ts`，规则仍为同步异常、进行中、未开始、已结束未完成、缺席、已完成、无计划；跳转能力改由详情覆盖层内按钮触发。
- 监控端自动刷新第一版已实现：默认关闭，可手动开启/关闭，页面隐藏时暂停，请求失败仅在顶部状态提示，组件卸载时清理 timer。
- `scripts/phase1_acceptance_check.ps1` 已纳入 `Monitoring status aggregation smoke check`，该步骤失败会阻断第一阶段统一验收。
- 监控端运动员看板在普通 iPad 横屏宽度下优先使用 2 列卡片，避免 1024px - 1080px 下 3 列过窄影响阅读。
- `TrainingModeView` 与 `TrainingSessionView` 已复用 `useTeamFilter`，统一队伍筛选、筛选后队员列表和选中队员同步逻辑。
- `TrainingModeSidebar`、`TrainingSessionView`、`TrainingReportsView` 与 `TrainingSessionCard` 已开始复用集中训练状态文案和 tone，为后续监控端接口与看板共用状态显示打底。

- 本轮“重构结构”分支结构收口不新增业务功能，重点收紧：
  - 移除 Git 跟踪的临时数据库 `backend/tmp_step8.db` 与运行时启动摘要 `logs/startup/*.txt`，并补齐 `.gitignore` / `logs/startup/.gitkeep`
  - 训练顶部日期 / 队伍筛选统一抽为 `frontend/src/components/training/TrainingHeaderFilters.vue`，避免 `TrainingModeView` 与 `TrainingSessionView` 继续复制 iPad Safari 适配样式
  - 训练端顶栏高度、左侧栏宽度、右侧栏宽度、三栏 gap、筛选宽度统一收口到 `frontend/src/components/training/trainingLayout.css`
  - `frontend/src/stores/training.ts` 将本地 session 状态重算拆到 `utils/trainingSessionState.ts`，草稿与同步队列辅助逻辑拆到 `services/trainingDraftSync.ts`
  - `backend/app/services/session_service.py` 将 item 状态判断、session 状态判断、session/full-sync snapshot 序列化和冲突签名计算抽到 `session_state_utils.py`
  - 同步异常摘要、手动补传结果和整课覆盖冲突说明统一改为中文可读文案，避免教练端和管理端继续出现英文处理提示

- 第一阶段协作文档已统一收口为“真实实现口径”：
  - 跨日未收口统一表述为“后端启动时自动跨日收口昨日及更早未结束训练课，训练入口保留兜底收口”，不再把当前实现写成零点定时任务
  - 训练端本地草稿统一表述为“浏览器 `localStorage` 本地优先保底”，明确其主要覆盖同一浏览器 / 同一设备内恢复，不再夸大为跨设备强持久化
  - `AGENTS.md`、`README.md`、`PROJECT_CONTEXT.md`、`CODEX_HANDOFF.md` 与第一阶段核心文档已同步修正旧术语和旧行为描述

- 根目录 `AGENTS.md` 已按用户提供的 `AGENTS长期项目开发约束_可复制版.docx` 整体重写，覆盖旧的第一阶段阶段性协作口径并切换为长期项目开发约束。

- 跨日未收口训练课的主收口触发点已改为“后端启动时先执行一次”：
  - `backend/app/main.py` 在对外提供请求前先执行 `close_due_sessions()`，并移除原来的周期性自动收口循环
  - 启动时收口失败会明确打印错误并阻止启动，确保“启动成功”就意味着昨天及更早未收口训练课已完成状态纠正
  - `backend/app/services/session_service.py` 保留非 GET 训练入口里的 `close_due_sessions()` 兜底调用，继续作为保险层
  - `docs/phase1-session-status-flow.md`、`docs/phase1-step-index.md` 已补充本次阶段收尾修复记录

- 启动器失败摘要已收口为“可复制摘要 + 详细日志 + 排障文档”闭环：
  - `scripts/system_launcher.ps1` 失败时会输出失败步骤、错误类型、最可能原因、建议修复，并写入 `logs/startup/last-launcher-summary.txt`
  - 同时保留 `logs/startup/last-launcher-detail.log` 与带时间戳的摘要/详细日志副本，便于先发简版摘要给 AI，再按需补详细日志
  - `start_system.bat` / `init_system.bat` 改为优先调用 `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`，避免仅因 `PATH` 异常就在入口层误报 `powershell_missing`
  - 前端依赖自检已从“少数包探测”收口为“按 `frontend/package.json` 校验全部直接依赖和 devDependencies”；`node_modules` 缺失或声明包不完整时会自动执行 `npm install`
  - `npm install` 后会再次校验声明依赖，避免启动器误判“前端依赖已就绪”却在浏览器里才报 `Failed to resolve import "qrcode"`
  - 当前前端依赖相关失败会区分：
    - `frontend_dependency_install_failed`
    - `frontend_dependency_validation_failed`
  - `docs/phase1-launcher-failure-summary.md`、`docs/phase1-startup-launcher.md`、`docs/phase1-step-index.md` 已补齐 Step 17 记录

- 第一阶段总验收已收口为“人工清单 + 一键自测 + 放行标准”：
  - 新增 `docs/phase1-final-acceptance.md`，统一记录 1 台电脑 + 2 台 iPad 的人工验收路径、失败定义和阻塞放行规则
  - 新增 `scripts/phase1_acceptance_check.ps1`，统一执行第一阶段最小自测命令
  - 新增 `backend/scripts/phase1_backend_smoke_check.py`，在临时数据库副本上覆盖首组建课、增量补传、整课兜底、同步异常人工重试、状态重算、备份恢复基础能力
  - `docs/phase1-step-index.md` 已补齐 Step 18 记录

- 训练模式访问地址已收口为单一来源：
  - 前端页面的“推荐地址”改为直接读取 Vite dev server 解析出的 `Network` 地址
  - `start_system.bat` 不再自行选择另一套局域网 IP，改为读取前端启动时写入的统一地址
  - `runtime-access.json` 在前端 dev server 启动时生成，避免页面地址和 bat 窗口地址不一致
  - Vite dev server 额外提供动态 `/runtime-access.json` 接口，避免启动后新增的运行时文件被 SPA 回退吞掉

- 训练端本地草稿恢复链路收口到“重开即提示 / 继续回动作列表 / 放弃删除草稿”：
  - `TrainingModeView` 打开时会扫描可恢复草稿，并弹出统一恢复提示
  - 点击“继续录课”后统一带恢复上下文进入训练页，优先回到动作列表而不是直接落进录组面板
  - 恢复后继续保留当前动作高亮，帮助队员回到上次中断位置
  - 点击“放弃草稿”会直接删除本地草稿，不新增重复 `session`
  - 当预览路由在恢复过程中切换成正式 `session` 路由时，会保留恢复上下文，避免继续路径丢失

- 训练端同步闭环继续收紧到“状态灯 + 异常待处理 + 人工重试”阶段：
  - 训练页状态灯收口为两态：`正常 / 有未同步数据`
  - 增量补传和整课兜底长期失败后，不再无限自动重试，而是转入 `manual_retry_required`
  - 新增 `training_sync_issues`，用于持久化“同步异常，待处理”的最小后端可见记录
  - 教练回看页新增“同步异常待处理”面板，可直接手动重试
  - 管理端首页新增待处理同步异常列表与手动重试入口
  - 训练端在人工处理阶段仍保持本地优先录入，并持续刷新最新草稿快照给后端异常记录

- 训练课收口规则已落地到训练端和后端主链路：
  - 训练页新增“结束计划”按钮
  - 手动结束未录满的训练课会记为 `partial_complete`
  - 触发跨日收口后，昨日及更早未收口训练课会重算为 `absent / partial_complete / completed`
  - 整堂课录满后会给出轻量自动完成提示
  - 本地草稿对 `completed / absent / partial_complete` 等最终状态会自动停止恢复提示
- 训练端本地草稿已接入最小增量补传闭环：
  - 每录完一组后会按 session 维度在后台悄悄尝试单组补传
  - 失败不打断训练，前端只保留“有未同步数据”状态
  - 本地草稿新增 `pending_operations` 队列，用于记录待补传的单组创建/修改
  - 当前同步状态仍只收敛到最小 `synced / pending`
  - 增量补传连续失败达到阈值后，会自动进入整课覆盖同步兜底
  - 训练页新增手动“整课补传”入口，可按本地草稿整体覆盖后端
  - 明显冲突会写入 `training_sync_conflicts`，并在训练回看页提示教练/管理员复核
  - 本轮继续收口首组创建规则：打开计划只返回训练草稿快照，不再提前落库 session；首组成功后才正式创建/确认 session 并进入 `in_progress`
  - 修复训练端离线本地保存分支返回值错误，确保上传失败后仍可继续录入并留下待同步标记
  - 训练报告侧状态展示同步兼容 `not_started / absent / partial_complete`
- 训练端已接入“整堂课一个本地草稿”的 MVP：
  - 每录完一组立即保存到本机
  - 历史组修改后同步刷新整课草稿
  - 重新进入训练课时支持恢复或放弃本地草稿
  - 后端暂不可用时仍可继续本地录入，后续由增量补传 / 整课兜底 / 人工重试闭环继续收口
- 根目录 `AGENTS.md` 已重写为“第一阶段核心稳定性重构”导向，明确训练端、本地草稿、同步状态、session 状态流、迁移、备份与危险操作规则。
- 训练模板编辑收口为“统一保存模板”模式：
  - 新增动作默认不再勾选“主项动作”和“启用自动调重”
  - 进阶逻辑仅在启用自动调重时显示
  - 动作选择改为“一级分类 + 二级分类 + 可搜索动作”
  - 参数区改为紧凑布局
  - 训练目标改为自由输入
  - 动作备注默认收为单行
- 训练模板中彻底删除 `rest_seconds / 休息时间`，并改为按卡片排列顺序决定训练顺序。
- 计划分配页上半区改为“当前与后续计划”概览：
  - 视图范围从“仅查看日期当天”扩展为“查看日期当天 + 未来有效计划”
  - 分组状态区分为“进行中 / 即将开始”
  - 未分配人数改为按“从当前日期往后无有效计划”计算
- 计划分配预览收口为“队员名单 + 单份模板预览 + 异常提示区”，不再按人重复渲染同一模板。
- 计划分配页左侧第二步移除重复模板预览，右侧改为唯一正式预览区；模板选中后即可先显示模板内容。
- 计划分配页删除“刷新预览”按钮，备注也改为自动触发预览更新。
- 取消已分配计划的主入口从下方队员卡片移到上方概览分组内，支持按组内选中队员后删除分配。
- 计划分配页下方第一步队员区只负责新增分配，不再承担删除已有计划的职责。
- 训练模式头部改为更紧凑的单行布局，并将日期/队伍筛选提到头部区域。
- 动作库页面和运动员页面的筛选区统一为“搜索框单独一行，筛选控件下一行”的布局。
- 动作库页面收口为日常维护界面，网页端不再暴露导入入口，仅保留浏览、筛选、新建、编辑、删除。
- 项目中文乱码治理完成：恢复损坏文档与导入脚本内容，并建立统一 UTF-8 协作规范。

### Fixed

- 修复测试数据模块中“总表已有历史记录，但测试类型下显示 0 个测试项目”的问题：
  - 默认测试分类已补齐 `基础身体 / 速度测试 / 耐力测试` 的缺失二级项目
  - 系统启动、数据库迁移、单条新增测试记录、批量导入测试记录时，都会自动把历史 `test_records` 中缺失的一级/二级分类回填到测试主数据，避免再次出现主数据与历史记录脱节

- 修复 `/api/exercises` 因历史空值数据导致返回 `500`、动作库页面空白的问题。
- 修复固定重量模板在计划分配预览中被误判为“缺少测试基准”的问题，前端现仅对 `missing_basis` 触发阻断。
- 修复训练模板动作卡片在桌面端过早退化为单列、动作搜索控件与分类下拉样式不一致的问题。
- 修复训练模式头部访问卡片、模式切换区反复串行换行与文案乱码问题。
- 修复计划分配概览与下方新增分配流程之间的职责混淆，避免重复预览和重复删除入口。
- 修复批量更新运动员性别时写入错误字符导致页面显示异常的问题。
- 修复多份协作文档及 `backend/scripts/import_real_test_data.py` 的内容级中文乱码问题。
- 修复训练模式“查看计划”区域在左侧队员列表滑走后缺少当前队员姓名提示的问题，避免教练和队员在预览或录课时看错人。
- 修复训练模式中队员当前只有 1 份候选计划时，大卡片仍需先点人、再点计划才能进入训练的问题，改为点击大卡片即可直接走同一条开课链路。
- 修复训练模式和训练记录页在普通 iPad 横屏下因断点过早降为手机单列布局的问题，改为 `mobile / tablet / desktop` 三档断点，并在开发环境新增训练布局调试浮层。
- 修复训练页顶部标题区在平板和桌面端过高、信息堆叠的问题，改为单行工具栏头部，并将访问地址、复制入口、二维码和生成时间折叠进访问入口弹层。

- 修复训练记录页顶部长期缺少“训练日期 / 训练队伍”筛选的问题，将同一套头部筛选插槽接入 `TrainingSessionView`，并移除传给侧栏的失效筛选参数。
- 修复训练端左侧队员列表默认顺序不稳定的问题，统一改为“当天有计划的队员排前面，再按姓名升序排序；无计划队员排后面”，并让默认选中队员跟随这套顺序。
- 修复训练记录页关键信息层级不清的问题，将“当前队员”从下方“查看计划”卡片上移到上方“训练记录”卡片，并替换原计划名显示为更突出的队员姓名；训练记录页下方不再重复显示同一条当前队员提示。
- 修复训练记录右侧下一组录入默认值总是回退到计划默认的问题，改为第二组起优先继承最新一组实际录入的重量、次数和 RIR；建议卡继续显示，但不再自动覆盖输入框默认值。
- 修复训练端左侧队员列表在主动结束训练后仍把 `partial_complete` 渲染为红色“未完成”的问题；现在训练端侧栏会将已结束的 `partial_complete` 统一显示为绿色“已完成”，避免现场教练误判，但后端正式状态仍保持不变。
- 调整训练端左侧队员列表里 `partial_complete` 的视觉口径：文案继续显示“已完成”，但颜色改为偏黄一点的绿色，与真正全完成的纯绿色做区分。
- 调整训练记录页顶部信息卡片排版：删除“训练记录”“当前队员”标签文字，将姓名、状态、同步状态收为横排信息条，并压缩卡片高度与内边距。
- 修复训练模式顶部工具栏在普通 iPad 横屏下日期筛选和队伍筛选发生重叠的问题：头部改为明确的三段式 grid 布局，日期/队伍筛选改为固定宽度 wrapper + 内部控件填充的稳定结构，并让右侧次要按钮在窄平板宽度下优先压缩或隐藏，避免再去挤压中间筛选区。
- 调整训练模式与训练记录页顶部日期/队伍筛选框的文字对齐：将日期和队伍筛选统一成同一种可视 pill 结构，由居中的文本层负责展示、透明原生控件负责交互，避免 iPad Safari 原生 `date` 输入基线偏上导致两者不在同一垂直中心线。
- 移除训练模式顶部 iPad 布局排查阶段临时加入的调试 outline 框线，保留稳定后的 topbar 布局和右下角开发环境调试浮层。
- 调整训练模式中间“查看计划”预览卡的信息密度：每个动作除组数和次数外，新增负荷预览，优先显示该队员 assignment override 的实际千克，其次显示 session 已分配重量，再回退到模板里的固定重量或百分比设定。
- 调整训练模式中间“查看计划”预览卡的负荷文案格式：不再单独显示“负荷预览”，改为直接并入动作摘要，统一显示为“组数 × 次数 × 重量/百分比”。
- 调整训练模式中间“查看计划”预览卡的动作备注显示：移除默认占位文案“按设定目标完成本动作”，现在仅在动作确实存在备注时才显示备注。
- 调整训练记录右侧 RIR 交互按钮：移除 `-1 / +1`，统一改为 `0 / 1 / 2 / 3 / 4+` 的单排小按钮，当前组和历史组都按固定档位直接选择，减少现场录入时的重复点击。
- 修复管理端运动员页面只有新增和编辑、缺少删除链路的问题：新增管理端删除按钮、前端危险操作确认、后端运动员删除接口，以及“已有计划分配 / 训练记录 / 测试记录时拒绝删除”的保护逻辑。
### Notes

- 当前项目仍未完全引入正式数据库迁移框架，运行时 schema 修补逻辑仍存在于 `backend/app/core/schema_sync.py`，这是第一阶段后续必须收口的工程项。
- 第一阶段重构重点应转向：
  - 训练端本地草稿保存与恢复
  - 后台同步链路与同步状态
  - session 创建/确认时机与状态流
  - 自动结束、缺席、未完全按计划完成规则
  - 正式迁移、备份、恢复与日志能力
- `docs/phase1-terminology-and-boundaries.md` 现已作为第一阶段术语、状态枚举和边界整理的统一基线文档。
