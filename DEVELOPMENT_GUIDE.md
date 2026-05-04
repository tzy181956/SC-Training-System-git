# 开发规范说明

## 总体原则

- 优先保证主流程可运行
- 小步修改，不轻易推翻已有结构
- 先理解现有实现，再扩展功能
- 用户可见页面优先保持全中文
- 变更记录和验证同等重要，不能省略

## 变更记录要求

每一轮会修改仓库内容的工作，都必须同步更新根目录 `CHANGELOG.md`。

最低要求：

- 记录新增能力
- 记录行为变更
- 记录修复项
- 记录重要运维或数据说明

不要把 changelog 留到“最后统一补”。  
它应当和以下动作同级：

- 跑构建验证
- 跑脚本验证
- 核对关键页面行为

## 后端规范

- 核心业务逻辑必须放在 `services`
- API 层只负责参数接收、调用服务、返回结果
- 数据模型改动要考虑 SQLite 与未来 PostgreSQL 迁移
- 数据库结构变更优先走正式 migration，不再把 `schema_sync.py` 当作长期主方案
- 不把关键业务规则写死在前端
- 新增聚合逻辑时，优先复用现有表，不随意新增表

### 数据库迁移要求

- 当前迁移基线与规划文档见：
  - `docs/phase1-database-migrations.md`
- 当前迁移入口脚本：
  - `backend/scripts/migrate_db.py`
- 初始化脚本 `backend/scripts/init_db.py` 已切到迁移 bootstrap 入口
- 迁移前必须先备份数据库
- 新增表/字段时必须写清：
  - 为什么加
  - 给谁用
  - 与旧结构关系
  - 迁移顺序
  - 回退注意事项

## 前端规范

- 页面与组件拆分清晰
- 训练模式优先触摸操作体验
- 大按钮、卡片布局、横屏优先
- 重量、次数、RIR 等高频交互优先减少输入成本
- 若已有状态管理逻辑，优先延续当前 store 结构
- 训练端本地草稿与后台补传优先走“本地优先、后台静默重试”，不要让同步失败打断现场录入
- 训练顶部日期 / 队伍筛选统一复用 `frontend/src/components/training/TrainingHeaderFilters.vue`，不要在 `TrainingModeView.vue` 和 `TrainingSessionView.vue` 各自复制 pill 结构或 iPad Safari 兼容样式
- 训练端共享尺寸变量统一收口在 `frontend/src/components/training/trainingLayout.css`，包括顶栏高度、三栏 gap、左侧栏宽度、右侧栏宽度与筛选宽度；后续不要再在两个训练 View 各写一套相似断点

## 接口规范

- API 命名保持统一
- 返回结构尽量稳定，不随意破坏现有前端调用
- 新接口优先面向页面完整场景返回，不让前端拼过多零散请求

## 中文与编码规范

### 仓库文本编码

仓库文本文件统一使用 UTF-8。

后续检查中文文件时，不要把 PowerShell 默认输出当作最终依据。优先使用：

- 编辑器直接打开文件
- Python `Path(...).read_text(encoding='utf-8')`

### 不要做的事

- 不要把终端里看到的乱码文本直接复制回源码或文档
- 不要用不确定编码的重定向输出覆盖仓库文件
- 不要全仓做盲目“自动转码”

### 仓库级检查

使用专用扫描脚本：

```powershell
python scripts/check_text_encoding.py
```

该脚本会检查：

- replacement character（`U+FFFD`）
- Private Use 区字符
- 典型 mojibake 片段
- 常见文本文件中的可疑编码问题

详细说明见：

- `docs/text-encoding.md`

## 中文展示规范

- 面向教练和训练用户的页面尽量不用英文
- 模板名、动作名、测试名尽量使用中文
- 内部代码、接口路径、数据库 `code` 字段可以保留英文

## 启动与环境规范

- 启动入口统一使用 `scripts/start_system.bat`
- 初始化入口统一使用 `scripts/init_system.bat`
- 不轻易改坏 Windows 一键启动链路
- Python 固定为 `3.12.x`
- Node.js 固定为 `18+`

## 动作库模块约束

- 动作库唯一权威源是 Excel `exos_action_library_tagged_for_codex.xlsx` 的 `动作库_标签版`
- 动作库实现必须分层：
  - Excel 解析层
  - 数据标准化层
  - 服务层
  - 前端筛选与展示层
- 不允许回退到旧 `tags / exercise_tags` 作为动作库主逻辑
- 所有 `标签_...` 字段都属于结构化筛选字段，不能只降级为备注文本
- 新代码统一使用：
  - `name` 作为中文动作名
  - `name_en` 作为英文原名
  - `code` 作为稳定外部编码
- 不要重新把 Excel 导入按钮放回动作库页面主流程

## 训练模板与计划分配约束

- 训练模板当前以记录优先，不默认开启自动调重
- 模板顺序由卡片排列决定，不暴露手工顺序输入
- 计划分配右侧预览区是唯一正式预览入口，不在左侧重复渲染模板动作列表
- 计划分配阻断逻辑只认后端稳定状态值，不用中文文案参与判断

## 改动提交前检查

每次较大改动前后，至少检查：

```powershell
cd frontend
npm run build
```

```powershell
cd ..
backend\.venv\Scripts\python.exe -m compileall backend\app
python scripts/check_text_encoding.py
```

同时确认：

- 关键页面能打开
- 一键启动脚本能用
- 新功能至少有一组本地验证步骤
- `CHANGELOG.md` 已同步记录

## 跨电脑继续开发

在新电脑上继续开发时，建议顺序：

1. 安装 Python 3.12、Node.js、Git
2. 克隆仓库
3. 双击 `scripts/start_system.bat`
4. 阅读：
   - `README.md`
   - `PROJECT_CONTEXT.md`
   - `DEVELOPMENT_GUIDE.md`
   - `CURRENT_STATUS.md`
   - `NEXT_STEPS.md`

## 协作建议

- 使用私有仓库
- 主分支尽量保持可运行
- 大改动新建分支
- 使用 Pull Request 或至少做分支合并
- 不建议多人长期同时直接改 `main`
- 如果文档有乱码、过期或与当前实现不符，应优先修文档再继续累积新改动
