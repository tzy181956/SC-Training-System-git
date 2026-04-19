# CHANGELOG

## Unreleased / V1-dev

### Added

- 增加训练模式与训练 session 主流程
- 增加计划分配概览、分组展示、批量取消分配
- 增加训练模式下当前组提交、历史组即时修改
- 增加训练状态颜色提示、自动完成动作、自动完成 session
- 增加跨电脑更稳的 Windows 启动 / 初始化脚本逻辑
- 增加运动员主档身体字段：
  - `height`
  - `weight`
  - `body_fat_percentage`
  - `wingspan`
  - `standing_reach`
- 增加测试记录展示字段：
  - `result_text`
- 增加真实 Excel 数据导入脚本：
  - [import_real_test_data.py](C:\Users\Tian Ziyu\Documents\New project\backend\scripts\import_real_test_data.py)
- 增加运行时 schema 同步：
  - [schema_sync.py](C:\Users\Tian Ziyu\Documents\New project\backend\app\core\schema_sync.py)

### Changed

- 训练模式改为“点计划即训练”，不再依赖开始训练前的确认页
- 当前组恢复为手动确认提交，历史组保持即时修改
- 训练录入区改成更适合 iPad 的大按钮交互
- 训练模式左侧队员计划改为常驻展开
- 训练模式侧边栏新增日期旁的队伍筛选
- 测试数据页改为支持展示时间文本和力量体重比计算
- 运动员页扩展为可编辑身体主档数据
- 缺少测试基准时，计划分配不再被阻断，改为“训练时录入”

### Fixed

- 修复跨电脑复制 `.venv` 后因旧解释器绝对路径导致初始化失败的问题
- 修复 Node `spawn EPERM` 排查后造成的误判，明确区分环境限制与项目问题
- 修复模板页面“新增动作卡片看起来可点但实际无反应”的交互问题
- 修复计划分配概览接口被动态路由误拦截的问题
- 修复训练最后一组提交后动作状态不同步的问题
- 修复历史脏 session 中已满组但仍显示 `in_progress` 的问题
- 修复训练录入中默认伪造 `20` 公斤的问题
- 修复真实 Excel 导入时把“全队平均”汇总行误导入为运动员的问题

### Notes

- 当前仓库已从“纯 demo 演示”过渡到“真实女篮青年队测试数据验证”
- 本地数据库当前状态：
  - 16 名真实队员
  - 368 条测试记录
  - 训练模板与动作库保留
  - 示例运动员、测试记录、计划分配、训练记录已清空
- 目前仍没有正式数据库迁移框架，模型扩展依赖：
  - `backend/scripts/init_db.py`
  - `backend/app/core/schema_sync.py`
