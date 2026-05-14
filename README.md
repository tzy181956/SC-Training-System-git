# 体能训练管理平台

这是一个面向体能教练、运动队训练执行与测试分析的 Web 平台。系统当前采用“服务器运行 + 本地开发并行”的形态，核心目标是让教练可以稳定完成：

作者：`@TZY`

- 运动员与队伍管理
- 动作库维护
- 训练模板配置
- 计划分配
- 训练执行与训练回看
- 测试数据导入、补录、筛选、删除与导出
- 测试评分与雷达图分析
- 监控端查看当天训练状态
- 日志、备份与账号管理

## 当前产品形态

当前系统是一个已经具备服务器部署形态的训练管理系统。

- 前端：Vue 3
- 后端：FastAPI
- 数据库：SQLite
- ORM：SQLAlchemy
- 图表：ECharts
- 数据迁移：Alembic + `backend/scripts/migrate_db.py`

当前运行形态分为两套环境：

- 本地开发环境：Windows + `scripts/start_system.bat` / `scripts/init_system.bat`
- 服务器运行环境：Ubuntu + Nginx + systemd + SQLite + 同域 `/api`

## 当前访问与权限

系统当前为登录制。

- `admin`
  - 可访问管理、训练、监控、日志、备份、账号管理等完整能力
- `coach`
  - 可访问管理、训练、监控、测试评分等业务能力

当前前端包含三类模式入口：

- 管理模式
- 训练模式
- 实时监控模式

## 核心模块

- 运动员与队伍管理
- 动作库与动作分类树
- 训练模板与模板动作项
- 计划分配与计划概览
- 训练执行、组记录、本地草稿与同步状态
- 训练报告与训练负荷
- 测试类型/测试项目主数据
- 测试数据总库与导入导出
- 测试评分与雷达图
- 监控端总览与运动员详情
- 日志、备份恢复、账号管理

## 本地开发

### 环境要求

- Python `3.12.x`
- Node.js `18+`
- Git

### 启动与初始化

本地开发推荐入口：

- 启动：`scripts/start_system.bat`
- 初始化：`scripts/init_system.bat`

这两条脚本当前定位是：

- 开发环境准备工具
- 本地联调启动工具
- 故障排查入口

它们不是生产环境启动方式。

### 本地验证

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

## 服务器部署

当前服务器部署架构是：

- Nginx 对外提供 HTTP
- 前端构建产物由 Nginx 托管
- FastAPI 通过 systemd 常驻
- 后端仅监听 `127.0.0.1:8000`
- 前端通过同域 `/api` 访问后端
- 生产数据库独立存放在服务器数据目录

部署与更新请优先阅读：

- [docs/deployment/tencent-lighthouse-ubuntu.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\docs\deployment\tencent-lighthouse-ubuntu.md)

### GitHub Actions 自动部署

仓库已提供自动部署流程：

- Workflow：`.github/workflows/deploy.yml`
- 服务器执行脚本：`scripts/deploy.sh`
- 触发分支：`服务器端`
- 触发方式：向 `服务器端` 分支 push，或在 GitHub Actions 页面手动运行 `Deploy Production`

当前流程采用“Actions 基础检查 + SSH 登录服务器 git pull”的方式。完整配置说明见：

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

自动部署大致流程：

1. checkout 代码
2. 安装后端依赖
3. 安装前端依赖并构建前端
4. 校验部署 Secrets
5. 配置 SSH key 和 known_hosts
6. 测试 SSH 连接
7. 登录服务器，在 `DEPLOY_PATH` 执行 `git pull`
8. 在服务器安装后端依赖、执行 `python scripts/migrate_db.py ensure`
9. 在服务器执行 `npm ci && npm run build`
10. 重启 `sc-training-backend`，reload Nginx
11. 请求 `/health` 做健康检查

#### 需要配置的 GitHub Secrets

进入 GitHub 仓库：

`Settings -> Secrets and variables -> Actions -> New repository secret`

必须配置：

- `SERVER_HOST`：服务器公网 IP 或域名
- `SERVER_USER`：用于部署的 SSH 用户，例如 `deploy`
- `SSH_PRIVATE_KEY`：部署用户对应的 SSH 私钥内容
- `DEPLOY_PATH`：服务器上的项目 Git 工作目录，必须存在 `.git`

可选配置：

- `SERVER_PORT`：SSH 端口，默认 `22`
- `SSH_KNOWN_HOSTS`：推荐配置，服务器 SSH host key 的 `known_hosts` 行；为空时 workflow 才会退回 `ssh-keyscan` 并打印 warning
- `SERVICE_NAME`：systemd 后端服务名，默认 `sc-training-backend`
- `NGINX_SERVICE`：Nginx 服务名，默认 `nginx`
- `HEALTHCHECK_URL`：健康检查地址，默认 `http://127.0.0.1/health`

当前 workflow 仍兼容旧 Secrets：`SSH_HOST`、`SSH_USER`、`SSH_PORT`、`SSH_KEY`，但新配置请优先使用 `SERVER_*` 和 `SSH_PRIVATE_KEY`。

不要把任何私钥、服务器密码、`.env`、数据库、备份文件提交进仓库。

获取 `SSH_KNOWN_HOSTS` 的推荐方式：

```bash
# 在服务器控制台或已经可信的 SSH 会话里查看服务器 host key 指纹
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub

# 在本地电脑获取 known_hosts 行，并用上一行指纹核对
ssh-keyscan -p 22 your-domain.example > sc-training-known_hosts
ssh-keygen -lf sc-training-known_hosts
cat sc-training-known_hosts
```

核对无误后，把 `sc-training-known_hosts` 的内容保存为 GitHub Secret：`SSH_KNOWN_HOSTS`。如果 SSH 端口不是 `22`，把命令里的端口改成实际端口；`known_hosts` 行中会使用 `[host]:port` 格式。

#### 首次配置服务器命令

以下命令用于 Ubuntu 服务器首次准备。把 `<REPO_URL>`、`your-domain.example`、`<DEPLOY_PUBLIC_KEY>` 替换成自己的值。

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nodejs npm nginx curl
```

创建部署用户和后端服务用户：

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo useradd --system --home /opt/sc-training-system --shell /usr/sbin/nologin sc-training || true
sudo usermod -aG sc-training deploy
```

配置部署用户 SSH 公钥：

```bash
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
echo '<DEPLOY_PUBLIC_KEY>' | sudo tee /home/deploy/.ssh/authorized_keys >/dev/null
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

准备项目目录、共享配置目录和数据目录：

```bash
sudo mkdir -p /opt/sc-training-system /opt/sc-training-system-data
sudo chown -R deploy:deploy /opt/sc-training-system
sudo chown -R sc-training:sc-training /opt/sc-training-system-data
sudo chmod 770 /opt/sc-training-system-data
```

首次拉取代码到部署目录：

```bash
sudo -u deploy git clone -b 服务器端 <REPO_URL> /opt/sc-training-system
```

配置生产后端 `.env`：

```bash
sudo cp /opt/sc-training-system/deploy/backend.env.production.example /opt/sc-training-system/backend/.env
cd /opt/sc-training-system
sudo chown root:sc-training backend/.env
sudo chmod 640 backend/.env
sudo nano backend/.env
```

`backend/.env` 至少需要确认：

```dotenv
APP_ENV=production
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/sc-training-system-data/training.db
CORS_ORIGINS=["http://your-domain.example"]
CORS_ORIGIN_REGEX=
```

安装 systemd 和 Nginx 配置：

```bash
cd /opt/sc-training-system
sudo cp deploy/sc-training-backend.service /etc/systemd/system/sc-training-backend.service
sudo cp deploy/nginx-sc-training.production.conf /etc/nginx/sites-available/sc-training
sudo nano /etc/nginx/sites-available/sc-training
sudo ln -sf /etc/nginx/sites-available/sc-training /etc/nginx/sites-enabled/sc-training
sudo rm -f /etc/nginx/sites-enabled/default
```

在 Nginx 配置里把 `server_name your-domain.example;` 改成你的域名或服务器公网 IP。

公网生产版 Nginx 配置启用了登录限流，需要在 `/etc/nginx/nginx.conf` 的 `http {}` 内加入：

```nginx
limit_req_zone $binary_remote_addr zone=sc_training_login:10m rate=5r/m;
```

允许部署用户无密码执行部署所需的最小 sudo 命令：

```bash
sudo tee /etc/sudoers.d/sc-training-deploy >/dev/null <<'EOF'
deploy ALL=(root) NOPASSWD: /usr/sbin/nginx -t, /usr/bin/systemctl restart sc-training-backend, /usr/bin/systemctl reload nginx, /usr/bin/systemctl --no-pager --full status sc-training-backend, /usr/bin/journalctl -u sc-training-backend -n 80 --no-pager
EOF
sudo chmod 440 /etc/sudoers.d/sc-training-deploy
```

如果沿用 systemd 模板中的 `/opt/sc-training-system/current/backend` 路径，需要把模板路径改成 `/opt/sc-training-system/backend`，或按 `docs/DEPLOYMENT.md` 改为让 `DEPLOY_PATH=/opt/sc-training-system/current` 且该目录本身是 Git clone。

首次手动初始化依赖、迁移和服务时，可以先使用 GitHub Actions 完成一次部署。随后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable sc-training-backend
sudo systemctl restart sc-training-backend
sudo nginx -t
sudo systemctl reload nginx
curl http://127.0.0.1/health
```

首次配置完成后，再到 GitHub 配置 Secrets。之后向 `服务器端` 分支 push，即会自动部署到生产服务器。

## 数据库与迁移

当前正式数据库演进路径是：

- Alembic migration
- `backend/scripts/migrate_db.py ensure`

`schema_sync.py` 仅保留为过渡期兼容兜底，不再是正式主迁移方案。

### 破坏性数据清理

破坏性业务数据清理不随 Alembic migration 或 deploy 自动执行。需要先人工确认影响范围，再显式运行对应脚本。

当前可用脚本：

- `backend/scripts/data_cleanup/delete_vibration_equipment_exercises.py`

该脚本用于清理动作库中带 `振动器材` 器械标签的动作。默认不会删除数据，先执行 dry-run：

```powershell
cd backend
set PYTHONPATH=.
.\.venv\Scripts\python.exe scripts\data_cleanup\delete_vibration_equipment_exercises.py --dry-run
```

确认 dry-run 输出的删除数量、样例和引用检查后，再手动执行：

```powershell
.\.venv\Scripts\python.exe scripts\data_cleanup\delete_vibration_equipment_exercises.py --confirm DELETE_VIBRATION_EQUIPMENT_EXERCISES
```

执行模式会先创建危险操作前备份，成功或失败都会写入危险操作日志。若目标动作仍被训练模板或历史训练课引用，脚本会拒绝删除。

## 阅读顺序

新开发者建议先按这个顺序了解项目：

1. [README.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\README.md)
2. [PROJECT_CONTEXT.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\PROJECT_CONTEXT.md)
3. [CURRENT_STATUS.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\CURRENT_STATUS.md)
4. [DEVELOPMENT_GUIDE.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\DEVELOPMENT_GUIDE.md)
5. [CODEX_HANDOFF.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\CODEX_HANDOFF.md)
6. [docs/deployment/tencent-lighthouse-ubuntu.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\docs\deployment\tencent-lighthouse-ubuntu.md)
7. [docs/phase1-database-migrations.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\docs\phase1-database-migrations.md)
8. [docs/text-encoding.md](C:\Users\tzy\Documents\GitHub\SC-Training-System-git\docs\text-encoding.md)

## 文档分层说明

当前文档分为三类：

- 根目录权威文档：描述当前系统事实与协作规则
- `docs/` 专题文档：描述单一主题的规范、设计或历史阶段说明
- 历史阶段文档：会显式标注“历史阶段 / 归档参考”，不再冒充当前实现

## 说明

- 当前工作区可能包含未完成开发分支上的功能改动，文档默认只记录“已经完成并与代码事实一致”的内容。
- 本仓库文本文件统一使用 UTF-8；如果怀疑有乱码，优先运行 `python scripts/check_text_encoding.py`。
