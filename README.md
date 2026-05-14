# 体能训练管理平台

这是一个面向体能教练、运动队训练执行与测试分析的 Web 平台。系统当前采用“服务器运行 + 本地开发并行”的形态，核心目标是让教练可以稳定完成：

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

当前流程采用“Actions 构建并上传发布包”的方式：

1. checkout 代码
2. 安装后端依赖
3. 安装前端依赖
4. 运行后端编译检查、文本编码检查；如果仓库中存在 pytest 测试，则自动运行 pytest
5. 构建前端 `frontend/dist`
6. 打包发布产物
7. 通过 SSH 上传到服务器
8. 在服务器执行 `scripts/deploy.sh`
9. 服务器安装后端依赖、执行 `python scripts/migrate_db.py ensure`
10. 重启 `sc-training-backend`，reload Nginx
11. 请求 `/health` 做健康检查

发布包不会覆盖以下生产文件和目录：

- `backend/.env`
- `backend/.venv`
- `backend/training.db*`
- `backend/backups`
- `frontend/node_modules`
- `logs`

#### 需要配置的 GitHub Secrets

进入 GitHub 仓库：

`Settings -> Secrets and variables -> Actions -> New repository secret`

必须配置：

- `SSH_HOST`：服务器公网 IP 或域名
- `SSH_USER`：用于部署的 SSH 用户，例如 `deploy`
- `SSH_KEY`：部署用户对应的 SSH 私钥内容
- `DEPLOY_PATH`：服务器项目目录，例如 `/opt/sc-training-system`

可选配置：

- `SSH_PORT`：SSH 端口，默认 `22`
- `SERVICE_NAME`：systemd 后端服务名，默认 `sc-training-backend`
- `HEALTHCHECK_URL`：健康检查地址，默认 `http://127.0.0.1/health`

不要把任何私钥、服务器密码、`.env`、数据库、备份文件提交进仓库。

#### 首次配置服务器命令

以下命令用于 Ubuntu 服务器首次准备。把 `<REPO_URL>`、`your-domain.example`、`<DEPLOY_PUBLIC_KEY>` 替换成自己的值。

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx rsync curl
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

准备项目目录和数据目录：

```bash
sudo mkdir -p /opt/sc-training-system /opt/sc-training-system-data
sudo chown -R deploy:deploy /opt/sc-training-system
sudo chown -R sc-training:sc-training /opt/sc-training-system-data
sudo chmod 770 /opt/sc-training-system-data
```

首次拉取一份代码，用于复制 systemd / Nginx 模板：

```bash
sudo -u deploy git clone -b 服务器端 <REPO_URL> /opt/sc-training-system
```

配置生产后端 `.env`：

```bash
cd /opt/sc-training-system
sudo cp deploy/backend.env.production.example backend/.env
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

首次手动初始化依赖、迁移和服务：

```bash
sudo -u deploy bash -lc 'cd /opt/sc-training-system/backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python scripts/migrate_db.py ensure'
sudo -u deploy bash -lc 'cd /opt/sc-training-system/frontend && npm install && npm run build'

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
