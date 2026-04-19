# CODEX_HANDOFF

## 项目是什么

这是一个面向体能训练管理与训练执行的 Web 平台，主要使用场景是教练在管理模式下配置训练模板、分配计划，队员或教练在训练模式下用 iPad 录入训练数据。

## 用户是谁

当前主要用户就是项目维护者本人。  
这是单人开发项目，不需要团队协作文档口吻，文档重点是：

- 跨电脑继续开发
- 跨会话继续开发
- 让 Codex 快速理解项目背景、当前状态和下一步

## 系统目标是什么

目标不是做一个通用 SaaS，而是做一套能在真实队伍环境里用起来的体能训练管理系统。当前最核心的链路是：

1. 管理运动员与测试数据  
2. 配置动作库与训练模板  
3. 分配训练计划  
4. 在训练模式中实际执行和记录  
5. 回看训练与测试数据

## 当前技术结构

- 前端：Vue 3
- 后端：FastAPI
- 数据库：SQLite
- ORM：SQLAlchemy
- 图表：ECharts
- 启动方式：Windows 脚本为主
  - [start_system.bat](C:\Users\Tian Ziyu\Documents\New project\scripts\start_system.bat)
  - [init_system.bat](C:\Users\Tian Ziyu\Documents\New project\scripts\init_system.bat)

当前数据库没有正式迁移框架，结构变化依赖：

- [init_db.py](C:\Users\Tian Ziyu\Documents\New project\backend\scripts\init_db.py)
- [schema_sync.py](C:\Users\Tian Ziyu\Documents\New project\backend\app\core\schema_sync.py)

当前初始化链路已经改为非破坏式：

- `init_system.bat` 只安装依赖并创建/补齐数据库结构
- `start_system.bat` 自动触发初始化时也不会清库
- 不再自动导入示例数据
- 危险导入脚本默认需要手动输入确认词，不会静默清理数据

## 已完成什么

- 动作库、模板、计划分配、训练模式、训练报告、测试记录页面都已存在
- 训练模式支持：
  - 点计划即进入训练
  - 当前组确认提交
  - 历史组即时修改
  - 自动完成动作 / session
  - iPad 友好的大按钮交互
- 计划分配支持：
  - 分组概览
  - 已分配 / 未分配查看
  - 批量取消分配
- 已完成真实数据导入能力：
  - 从双层表头 Excel 解析女篮青年队测试数据
  - 写入运动员主档和测试记录
  - 忽略排名、总分、总排名
- 真实数据已成为默认长期工作模式，demo 初始化能力已移除

## 当前卡点是什么

- 仓库里仍有一些旧页面和文档存在中文乱码
- 测试数据页还是“可用”，但不是最终形态
- 数据库演进方式还比较临时，没有 Alembic 这类迁移体系
- 模板与动作库保留，但旧 demo 组织字典仍有残留引用，不能随便整库清空

## 当前最想解决的问题

1. 用真实数据把整条业务链路再验证一遍
2. 清掉残留 demo 假设和乱码文案
3. 把真实数据导入流程沉淀成可重复使用的稳定操作

## 当前数据状态

当前本地库 `backend/training.db` 已处于真实数据验证状态：

- 16 名女篮青年队队员
- 368 条测试记录
- 示例运动员 / 测试 / 分配 / 训练 session / 训练组记录已清空
- 模板和动作库保留

如果在新电脑或新库上继续开发，不要假设这些数据天然存在。需要时重新执行导入脚本。

## 下一次接手时应优先做什么

1. 先读：
   - [CURRENT_STATUS.md](C:\Users\Tian Ziyu\Documents\New project\CURRENT_STATUS.md)
   - [NEXT_STEPS.md](C:\Users\Tian Ziyu\Documents\New project\NEXT_STEPS.md)
2. 再确认当前库状态：
   - 是否仍是 16 名真实队员 / 368 条测试记录
   - 是否误重新灌入 demo 数据
3. 再决定本轮是：
   - 做真实数据展示验证
   - 修乱码
   - 修导入链路
   - 还是继续训练 / 计划模块开发

## 明确约束

### 不要乱改

- 训练模板和动作库：当前要求是保留
- 训练模式主流程：已经做过多轮交互修正，除非明确修 bug，不要顺手大改
- Windows 启动脚本：已适配跨电脑环境，改动前要先验证现有行为
- 当前真实数据导入脚本：优先修正和增强，不要随意推翻
- 初始化与启动链路：默认应保证不覆盖已有真实数据

### 优先保持稳定

- `/training` 训练执行链路
- `/assignments` 计划分配链路
- 真实数据导入和测试记录展示链路
- 运动员主档中的身体指标字段

## 与我协作时建议采用的工作方式

- 先读文档，再看代码，不要直接猜
- 优先用仓库现状来判断，不要凭空设计
- 一次只解决一条业务链路，不顺手做大重构
- 改代码前先说明会读取哪些文件、会改哪些部分
- 优先小步修改，然后跑最小验证
- 如果发现旧文档或页面有乱码，直接指出并分批修，不要假装没看到
- 对无法从仓库确定的内容，写“待确认”，不要编造

## 关键文件

- 项目总说明：
  - [README.md](C:\Users\Tian Ziyu\Documents\New project\README.md)
  - [PROJECT_CONTEXT.md](C:\Users\Tian Ziyu\Documents\New project\PROJECT_CONTEXT.md)
  - [DEVELOPMENT_GUIDE.md](C:\Users\Tian Ziyu\Documents\New project\DEVELOPMENT_GUIDE.md)
- 当前状态与下一步：
  - [CURRENT_STATUS.md](C:\Users\Tian Ziyu\Documents\New project\CURRENT_STATUS.md)
  - [NEXT_STEPS.md](C:\Users\Tian Ziyu\Documents\New project\NEXT_STEPS.md)
- 真实数据导入：
  - [import_real_test_data.py](C:\Users\Tian Ziyu\Documents\New project\backend\scripts\import_real_test_data.py)
- 数据结构变化：
  - [athlete.py](C:\Users\Tian Ziyu\Documents\New project\backend\app\models\athlete.py)
  - [test_record.py](C:\Users\Tian Ziyu\Documents\New project\backend\app\models\test_record.py)
  - [schema_sync.py](C:\Users\Tian Ziyu\Documents\New project\backend\app\core\schema_sync.py)
