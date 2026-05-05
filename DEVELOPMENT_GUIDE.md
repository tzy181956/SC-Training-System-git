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

## 本地开发与云服务器部署环境分工

- 本地电脑是开发环境，继续使用 Windows、本地 FastAPI、Vite dev server 和局域网访问。
- 腾讯云 Ubuntu 服务器是线上调试 / 运行环境，使用 Nginx + systemd + FastAPI + SQLite。
- GitHub 只负责代码同步中转，不负责同步生产数据。
- 本地数据库和服务器数据库不是同一个。
- 代码通过 GitHub 同步，生产数据不通过 GitHub 同步。

## 本地开发规则

- 本地可以继续使用 `scripts/start_system.bat`、`scripts/init_system.bat`、Vite dev server、本地 FastAPI 后端和局域网访问。
- 本地可以继续使用 `backend/training.db` 作为开发数据。
- 本地开发默认可以使用 `APP_ENV=development`。
- 不要因为服务器部署而删除或破坏现有 Windows 本地启动链路。
- 不要把 `backend/training.db`、`backend/backups/*.db`、`.env`、日志、`node_modules`、`dist`、运行时生成文件提交到 Git。

## 服务器运行规则

- 服务器项目目录固定为 `/opt/sc-training-system`。
- 服务器数据目录固定为 `/opt/sc-training-system-data`。
- 生产数据库固定为 `/opt/sc-training-system-data/training.db`。
- 后端 systemd 服务名固定为 `sc-training-backend`。
- 后端只监听 `127.0.0.1:8000`。
- Nginx 对外提供 `80`。
- Nginx 托管 `/opt/sc-training-system/frontend/dist`。
- `/api/` 反代到 `http://127.0.0.1:8000/api/`。
- `/health` 反代到 `http://127.0.0.1:8000/health`。
- 不开放 `8000`、`5173`、`3306`、`ALL` 到公网。
- 当前腾讯云环境是 HTTP 调试版，域名和 HTTPS 后续再做。

## 服务器更新标准流程

每次服务器更新默认按以下顺序执行：

```bash
cd /opt/sc-training-system
git pull origin 服务器端

cd /opt/sc-training-system/backend
source .venv/bin/activate
pip install -r requirements.txt
python scripts/migrate_db.py ensure

cd /opt/sc-training-system/frontend
npm install
npm run build

sudo systemctl restart sc-training-backend
sudo systemctl reload nginx

curl http://127.0.0.1/health
```

补充约束：

- 如果只改前端，通常仍需要 `npm run build` 和 `sudo systemctl reload nginx`。
- 如果只改后端，通常需要 `sudo systemctl restart sc-training-backend`。
- 如果改数据库模型，必须先准备 Alembic 迁移，再执行 `python scripts/migrate_db.py ensure`。
- 如果改 Python 或前端依赖，必须重新执行 `pip install -r requirements.txt` 或 `npm install`。
- 每次更新后必须再做浏览器人工验收。

## 本地与服务器差异

- Windows 默认不区分大小写，Ubuntu 区分大小写。
- Windows 路径是反斜杠，Ubuntu 路径是正斜杠。
- 本地 Vite dev server 不等于服务器生产 build。
- 本地 `localhost`、`127.0.0.1`、局域网 IP 不能写死到生产代码。
- 服务器前端请求后端必须走同域 `/api`。
- 不允许在前端代码里写死 `localhost:8000`、`127.0.0.1:8000`、`192.168.x.x:8000` 或服务器公网 IP。
- 服务器数据库和本地数据库不同，不能用 `git pull` 覆盖生产数据库。

## 运行数据、备份与性能注意事项

- 生产数据库路径：`/opt/sc-training-system-data/training.db`。
- 手动备份目录：`/opt/sc-training-system-data/manual-backups`。
- 每日自动备份脚本：`/opt/sc-training-system-data/backup_daily.sh`。
- `crontab` 应存在：

```cron
30 2 * * * /opt/sc-training-system-data/backup_daily.sh >> /opt/sc-training-system-data/manual-backups/backup.log 2>&1
```

- 任何覆盖数据库、迁移旧库、重大修改前必须先备份。
- 当前已知数据规模：动作库约 `1795` 条，`exercise_categories` 约 `788` 条。
- 当前已知问题：动作库和训练模板首次加载较慢。
- 当前先不在本规则中直接推动优化；后续优化方向是分页、搜索式加载、轻量接口、管理首页避免全量加载。
- 后续修改动作库 / 训练模板时，应优先考虑分页和懒加载，不要继续扩大首屏全量请求。

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
- 本地开发 -> GitHub -> 腾讯云服务器更新是默认协作路径；不要直接在服务器上手改业务代码后长期脱离 Git 管理
- 如果文档有乱码、过期或与当前实现不符，应优先修文档再继续累积新改动
