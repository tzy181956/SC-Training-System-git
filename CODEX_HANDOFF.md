# CODEX_HANDOFF

## 项目是什么

这是一个面向体能训练管理与训练执行的 Web 平台。主要使用场景是：

- 教练在管理模式下维护动作库、训练模板、计划分配、测试数据
- 教练或队员在训练模式下使用 iPad 记录训练数据

## 用户是谁

当前主要用户就是项目维护者本人，以及同一队伍中的教练与训练执行人员。  
这是一个单人主导开发项目，文档重点不是团队流程，而是：

- 跨电脑继续开发
- 跨会话继续开发
- 让 Codex 快速接手当前上下文

## 当前系统目标

当前目标不是做通用产品，而是把真实队伍场景里的主链路做稳：

1. 管理运动员和测试数据
2. 维护动作库
3. 维护训练模板
4. 分配训练计划
5. 在训练模式中执行并记录训练
6. 回看测试与训练结果

## 当前技术结构

- 前端：Vue 3
- 后端：FastAPI
- 数据库：SQLite
- ORM：SQLAlchemy
- 图表：ECharts
- 启动方式：Windows 脚本
  - `scripts/start_system.bat`
  - `scripts/init_system.bat`

数据库结构演进仍主要依赖：

- `backend/scripts/init_db.py`
- `backend/app/core/schema_sync.py`

## 当前状态摘要

- 系统已经进入真实数据验证阶段
- 本地库 `backend/training.db` 保存当前工作数据
- 动作库已经重构为结构化动作库
- 训练模板、计划分配、训练模式主流程都可用
- 训练模式支持局域网访问地址与二维码
- 训练端本地草稿当前以浏览器 `localStorage` 为主，主要覆盖同一浏览器 / 同一设备内的断网续录与重开恢复
- 后端启动时会先自动跨日收口昨日及更早未结束训练课，训练入口保留 `close_due_sessions()` 兜底
- 页面仍在持续做交互收口，但主链路已经稳定

## 动作库现状

- 唯一权威源：`exos_action_library_tagged_for_codex.xlsx / 动作库_标签版`
- 网页端只负责：
  - 浏览
  - 搜索
  - 标签筛选
  - 新建 / 编辑 / 删除
- Excel 导入入口不再出现在网页端

## 训练模板现状

- 以记录优先为主，不默认启用自动调重
- 模板卡片顺序就是训练顺序
- `rest_seconds` 已彻底删除
- 模板统一保存，不对单卡单独保存

## 计划分配现状

- 上半区概览显示“当前 + 未来有效计划”
- 右侧未分配名单按“从当前日期往后无有效计划”计算
- 左侧第二步不再重复展示模板预览
- 右侧是唯一正式预览区
- 已有计划取消改为从下方队员卡片直接进入

## 训练模式现状

- 默认训练模式优先
- 共享 iPad 录入
- 当前组确认提交
- 历史组即时修改
- 自动完成动作与 session
- 同步状态当前收口为：`synced / pending / manual_retry_required`，训练页只对外显示“正常 / 有未同步数据”
- 本地草稿恢复基于当前浏览器本机存储，不要按跨设备强持久化理解
- 顶部显示：
  - 推荐访问地址
  - 复制按钮
  - 二维码

## 当前主要风险

- 仍未引入正式数据库迁移框架
- 真实数据导入脚本对 Excel 表头有较强依赖
- 文档和中文文本曾发生过内容级乱码，需要持续做 UTF-8 检查
- PowerShell 输出可能误导中文判断，不能只看终端

## 接手时先看什么

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `DEVELOPMENT_GUIDE.md`
4. `CURRENT_STATUS.md`
5. `NEXT_STEPS.md`
6. `docs/text-encoding.md`

## 接手时先做什么

1. 看 `git status`
2. 确认本地数据库是否为当前工作数据
3. 跑最小检查：

```powershell
cd frontend
npm run build
cd ..
backend\.venv\Scripts\python.exe -m compileall backend\app
python scripts/check_text_encoding.py
```

4. 再决定本轮是：
   - 修业务 bug
   - 调整交互
   - 修文档
   - 还是继续真实数据验证

## 明确约束

- 不要轻易重置训练模板和动作库
- 不要随意破坏一键启动链路
- 不要用终端乱码文本回写源码或文档
- 每轮实际改动都必须更新 `CHANGELOG.md`
- 如果发现协作文档又出现乱码或与实现不符，优先修文档
