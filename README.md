# 体能训练管理平台 V1

这是一个以 `iPad / 平板横屏` 为主要使用场景的体能训练管理平台，服务于教练的训练模板配置、计划分配、训练执行记录与测试数据管理。

当前系统以“真实使用可落地、记录优先”为目标，已经具备以下主链路：

> 说明：训练端本地草稿当前使用浏览器 `localStorage` 做本地优先保底，适合断网继续录入、页面异常关闭后在同一浏览器 / 同一设备内恢复；它不是跨浏览器、跨设备或清缓存后仍可恢复的强持久化方案。


- 运动员管理
- 动作库维护
- 训练模板管理
- 计划分配与概览
- 训练模式执行
- 测试数据记录与查看
- Windows 一键初始化与一键启动
- 同局域网访问训练模式
- 训练端浏览器本地草稿（同一浏览器 / 同一设备优先）保存与恢复
- 训练端单组增量补传与后台静默重试（最小闭环）
- 增量补传长期失败后的整课覆盖同步兜底
- 明显同步冲突的最小日志记录与训练回看提示
- 后端启动时自动跨日收口昨日及更早未结束训练课，训练入口保留兜底收口

## 当前使用方式

系统目前采用 **免登录模式**：

- 默认进入 **训练模式**
- 右上角可切换到 **管理模式**
- 系统会记住上次使用的模式
- 不需要输入账号密码

## 环境要求

- Python `3.12.x`
- Node.js `18+`
- Git

建议安装时都勾选加入 `PATH`。

## 一键启动

平时直接双击：

- `scripts/start_system.bat`

这个脚本会自动：

- 检查 Python / Node.js / npm
- 在缺少环境时调用初始化
- 启动后端与前端
- 打开浏览器
- 生成训练模式访问地址和二维码所需的运行时配置

> 当前初始化链路是**非破坏式**的：只会创建或补齐数据库结构，不会自动清空已有真实业务数据。

## 初始化

如果你需要手动重装环境，可以单独双击：

- `scripts/init_system.bat`

它会完成：

- 检查 Python / Node.js / npm
- 创建后端虚拟环境
- 安装后端依赖
- 创建或补齐数据库结构
- 安装前端依赖

## 数据库迁移

项目现在已经接入正式迁移脚手架（Alembic 基线 + 迁移入口脚本）。

推荐命令：

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\migrate_db.py bootstrap
```

说明：

- 对当前已有业务库：先自动备份，再将现库标记到基线 revision
- 对新库：先自动备份（如存在），再执行 `upgrade head`
- 迁移规划与第一阶段新增表/字段说明见：
  - `docs/phase1-database-migrations.md`

## 训练模式访问

通过 `scripts/start_system.bat` 启动后，训练模式顶部会显示：

- 当前推荐访问地址
- 一键复制按钮
- 二维码

只要其他教练或 iPad 与电脑处于同一网络下，就可以直接：

- 输入训练模式顶部显示的地址访问
- 或扫码进入网页

## 真实数据导入

真实测试数据导入脚本位于：

- `backend/scripts/import_real_test_data.py`

它当前面向“女篮青年队真实测试 Excel”导入，特点如下：

- 默认读取 OneDrive 中的真实 Excel 路径
- 也支持通过命令行参数或环境变量覆盖源文件
- 导入前必须输入固定确认词
- 会清理旧的运动员、测试记录、计划分配、训练 session、组记录
- **不会**清理训练模板和动作库

手动执行示例：

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\import_real_test_data.py
```

如需指定 Excel：

```powershell
set REAL_TEST_DATA_XLSX=C:\path\to\测试结果.xlsx
.\.venv\Scripts\python.exe scripts\import_real_test_data.py
```

## 动作库说明

当前动作库已经重构为结构化动作库：

- 唯一权威数据源：`exos_action_library_tagged_for_codex.xlsx`
- 主数据表：`动作库_标签版`
- 数据落库分为：
  - `exercise_categories`：一级分类、二级分类、基础动作
  - `exercises`：具体动作、英文原名、结构化标签、搜索关键词、分类路径、原始行数据

网页端动作库当前以日常维护为主：

- 浏览
- 搜索
- 标签筛选
- 新建
- 编辑
- 删除

Excel 导入能力保留在后端 API / CLI 中，默认不在网页端暴露。

## 目录结构

```text
backend/    后端服务、数据库、业务逻辑、导入脚本
frontend/   前端页面、组件、状态管理、PWA 资源
scripts/    Windows 一键初始化、启动、检查脚本
docs/       专项说明文档
```

## 关键文档

- `PROJECT_CONTEXT.md`
  - 当前产品范围、业务规则、技术结构
- `DEVELOPMENT_GUIDE.md`
  - 协作规范、编码约束、验证方式
- `CODEX_HANDOFF.md`
  - 跨会话/跨电脑继续开发时的接手说明
- `CURRENT_STATUS.md`
  - 当前项目状态摘要
- `NEXT_STEPS.md`
  - 下一步建议工作项
- `docs/phase1-final-acceptance.md`
  - 第一阶段总验收清单，按 `1 台电脑 + 2 台 iPad` 场景逐项验收
- `EXERCISE_LIBRARY_SPEC.md`
  - 动作库字段来源与结构说明
- `docs/text-encoding.md`
  - 中文乱码问题说明、检查方式与防护规则
- `docs/deployment/tencent-lighthouse-ubuntu.md`
  - 腾讯云 Ubuntu 部署请参考这份文档
  - 本地开发 -> GitHub -> 腾讯云服务器更新规范也在这份文档里

## 编码与乱码检查

仓库文本文件统一使用 UTF-8。  
如果怀疑有中文乱码，不要只看 PowerShell 输出，优先使用：

- 编辑器直接打开文件
- Python `Path(...).read_text(encoding='utf-8')` 校验

仓库提供了专用扫描脚本：

```powershell
python scripts/check_text_encoding.py
```

它会扫描：

- 典型 mojibake 片段
- replacement character（`U+FFFD`）
- Private Use 区字符
- 常见文本文件中的可疑内容

## 上传前检查

建议至少执行：

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

- `README.md`、`PROJECT_CONTEXT.md` 等协作文档无乱码
- 启动链路不会覆盖真实业务数据
- `CHANGELOG.md` 已同步记录本轮改动
- 第一阶段收尾或交付前，至少跑一轮 `docs/phase1-final-acceptance.md` 和 `scripts/phase1_acceptance_check.ps1`

## Git 与数据库协作

当前规则已经调整为：

- 本地开发数据库可以继续使用 `backend/training.db`
- 腾讯云服务器生产数据库固定为 `/opt/sc-training-system-data/training.db`
- 本地数据库和服务器数据库不是同一个
- 代码通过 GitHub 同步，生产数据不通过 GitHub 同步
- `backend/training.db` 和 `backend/backups/*.db` 不再纳入 Git 跟踪
- `.env`、数据库、备份、日志、`node_modules`、`dist` 等运行时文件不要提交到 Git
- 服务器更新默认流程是：本地改代码 -> push 到 GitHub -> 服务器 `git pull origin 服务器端` -> 安装依赖 / 迁移 / build / 重启服务

如果需要完整部署和服务器更新说明，请优先阅读：

- `docs/deployment/tencent-lighthouse-ubuntu.md`

## 常见问题

### 1. 浏览器打不开页面

请检查：

- 前端是否运行在 `5173`
- 后端是否运行在 `8000`
- 是否有其他程序占用了端口

### 2. iPad 打得开页面但没有数据

常见原因：

- 后端没有成功启动
- 防火墙拦截了 `8000`
- iPad 和电脑不在同一个 Wi-Fi

### 3. 新电脑上拉下代码后无法继续工作

建议顺序：

1. 安装 Python 3.12、Node.js、Git
2. 拉取仓库
3. 双击 `scripts/start_system.bat`
4. 需要真实数据时再单独执行导入脚本

### 4. 终端里看到中文乱码

请先区分：

- 是终端显示问题
- 还是文件内容真的已经损坏

不要把终端里显示异常的文本直接复制回仓库文件。  
详细说明见：

- `docs/text-encoding.md`
