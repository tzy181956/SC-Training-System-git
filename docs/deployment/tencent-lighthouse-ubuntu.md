# 腾讯云 Ubuntu 部署说明

> 文档状态：当前有效  
> 用途：服务器阶段权威部署与更新说明

## 1. 适用范围

本文档描述当前项目在腾讯云 Ubuntu 环境下的正式部署方式。  
它适用于：

- 新服务器首次部署
- 已有服务器更新代码
- 本地开发与服务器运行分工确认

它不再把 Windows 本地启动链路写成生产主运行方式。

## 2. 当前部署架构

当前正式部署架构如下：

1. 服务器环境：Ubuntu
2. Nginx 对外提供 Web 访问
3. 前端通过 `npm run build` 构建后由 Nginx 托管
4. 后端 FastAPI 通过 systemd 常驻
5. 后端仅监听 `127.0.0.1:8000`
6. Nginx 将 `/api/` 反代到 `127.0.0.1:8000/api/`
7. Nginx 将 `/health` 反代到 `127.0.0.1:8000/health`
8. 数据库当前使用 SQLite
9. 生产数据库与代码目录分离保存

## 3. 目录约定

- 项目目录：`/opt/sc-training-system`
- 数据目录：`/opt/sc-training-system-data`
- 生产数据库：`/opt/sc-training-system-data/training.db`
- 手动备份目录：`/opt/sc-training-system-data/manual-backups`

## 4. 防火墙要求

当前建议仅开放：

- `22`
- `80`
- `443`（有域名和 HTTPS 时再使用）

不要开放：

- `5173`
- `8000`
- `3306`
- `ALL`

## 5. 首次部署流程

### 5.1 安装依赖

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nodejs npm nginx
```

### 5.2 拉取代码

```bash
git clone <仓库地址> /tmp/sc-training-system-template
```

### 5.3 创建 systemd 服务用户

```bash
sudo useradd --system --home /opt/sc-training-system --shell /usr/sbin/nologin sc-training
```

### 5.4 创建数据目录

生产环境建议把 SQLite、WAL/SHM sidecar 文件和自动备份目录统一放在独立数据目录，并交给 `sc-training` 服务用户写入：

```bash
sudo mkdir -p /opt/sc-training-system/releases /opt/sc-training-system/shared/backend /opt/sc-training-system-data
sudo chown -R deploy:deploy /opt/sc-training-system
sudo chown -R sc-training:sc-training /opt/sc-training-system-data
sudo chmod 750 /opt/sc-training-system-data
```

### 5.5 配置后端 `.env`

路径：

- `/opt/sc-training-system/shared/backend/.env`
- 仓库示例：`deploy/backend.env.production.example`

建议直接从示例文件复制：

```bash
cp /tmp/sc-training-system-template/deploy/backend.env.production.example /opt/sc-training-system/shared/backend/.env
sudo chown root:sc-training /opt/sc-training-system/shared/backend/.env
sudo chmod 640 /opt/sc-training-system/shared/backend/.env
```

最小示例：

```dotenv
APP_ENV=production
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/sc-training-system-data/training.db
CORS_ORIGINS=["https://your-domain.example"]
CORS_ORIGIN_REGEX=
```

说明：

- 生产环境启动前不要继续依赖开发默认值。
- `APP_ENV=production` 启动时不会执行运行时 `schema_sync` 自动改表。
- 生产数据库结构必须提前通过 `python scripts/migrate_db.py ensure` 收口完成。
- 前端默认走同域 `/api`，不要在前端业务代码或 `.env` 里写死公网 IP。

## 6. 后端部署

GitHub Actions 当前会通过 SSH 登录服务器，在 `DEPLOY_PATH` 指向的 Git 工作目录执行 `git pull`，然后完成后端依赖安装、`python scripts/migrate_db.py ensure`、前端构建、systemd 重启、Nginx reload 和健康检查。

详细的 GitHub Secrets、SSH key、known_hosts 和常见错误说明见：

- `docs/DEPLOYMENT.md`

这是生产环境首次启动前必须完成的正式迁移步骤。

不要把 `backend/app/core/schema_sync.py` 当作生产迁移路径。
它只保留开发环境兜底职责；生产环境必须依赖 Alembic migration。

当前 SQLite 生产连接会自动启用：

- `PRAGMA foreign_keys=ON`
- `PRAGMA journal_mode=WAL`
- `PRAGMA busy_timeout=5000`

因此数据目录必须允许后端服务写入：

- `training.db`
- `training.db-wal`
- `training.db-shm`

## 7. 前端部署

```bash
cd /opt/sc-training-system/frontend
npm install
npm run build
```

## 8. systemd 与 Nginx

使用仓库内模板：

- `deploy/sc-training-backend.service`
- `deploy/nginx-sc-training.conf`
- `deploy/nginx-sc-training.production.conf`（公网生产推荐）

典型流程：

```bash
cd /tmp/sc-training-system-template
sudo cp deploy/sc-training-backend.service /etc/systemd/system/sc-training-backend.service
sudo cp deploy/nginx-sc-training.production.conf /etc/nginx/sites-available/sc-training
sudo ln -s /etc/nginx/sites-available/sc-training /etc/nginx/sites-enabled/sc-training
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl daemon-reload
sudo systemctl enable sc-training-backend
sudo systemctl start sc-training-backend
sudo nginx -t
sudo systemctl reload nginx
```

生产建议：

- `deploy/sc-training-backend.service` 默认使用 `User=sc-training`、`Group=sc-training`
- `deploy/sc-training-backend.service` 已加入 `NoNewPrivileges`、`PrivateTmp`、`ProtectSystem=strict` 与 `ReadWritePaths=/opt/sc-training-system-data`
- systemd 模板中的 Uvicorn 已增加 `--proxy-headers --forwarded-allow-ips=127.0.0.1`
- 部署前必须确认 `/opt/sc-training-system-data` 对 `sc-training` 可写，否则 SQLite 的 `training.db`、`training.db-wal`、`training.db-shm` 和备份目录都无法正常工作
- 不要开放 `8000` 到公网；后端只允许 Nginx 在本机回源
- `deploy/nginx-sc-training.conf` 只提供基础版和限流示例注释；公网生产应优先使用 `deploy/nginx-sc-training.production.conf`，或手动把基础版中的限流配置真正启用

公网部署时，必须在 Nginx 全局 `http {}` 中声明登录限流 zone，并启用登录接口限流示例：

```nginx
limit_req_zone $binary_remote_addr zone=sc_training_login:10m rate=5r/m;
```

启用后再次执行：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

注意：

- 只把 `limit_req` 留在注释里不算启用
- 如果修改了 systemd 单元文件，必须重新执行 `sudo systemctl daemon-reload`

## 9. HTTPS 与公网暴露

如果系统要通过公网访问，建议在正式使用前完成 HTTPS：

1. 准备真实域名并更新 `server_name`
2. 使用 Nginx + 证书工具（如 Certbot）签发证书
3. 把前端访问入口与 `CORS_ORIGINS` 改成正式 `https://` 域名
4. 保留后端监听 `127.0.0.1:8000`，不要把 `8000` 暴露到公网

最低要求：

- 对外仅开放 `80/443`
- 业务登录与训练数据传输不应长期停留在纯 HTTP

## 10. 备份与异地备份

生产环境至少要同时具备：

- 服务器本机日常备份
- 危险操作前备份
- 异地备份副本

建议做法：

1. 保留 `/opt/sc-training-system-data` 本机备份目录
2. 定期把数据库备份文件同步到另一台机器、对象存储或离线介质
3. 异地备份至少保留最近若干天可恢复版本
4. 恢复演练时先对当前生产库再做一次备份

如果生产环境执行过备份恢复，还需要在恢复完成后立即执行：

```bash
cd /opt/sc-training-system/current/backend
source .venv/bin/activate
python scripts/migrate_db.py ensure
sudo systemctl restart sc-training-backend
```

生产恢复流程不会隐式调用 `schema_sync.py` 自动改表。
如果恢复的是旧备份，必须依赖正式 Alembic migration 把结构收口到当前代码版本。

## 11. 服务器手动更新标准流程

本节是**手动部署流程**，不依赖 GitHub Actions 自动部署。GitHub Actions 的 SSH 自动部署说明见 `docs/DEPLOYMENT.md`。

手动更新核心顺序：

1. 停止后端服务
2. 备份生产数据库
3. 更新代码
4. 在服务器生产库或生产库快照上运行 FK orphan 预检
5. orphan=0 后执行 Alembic migration
6. 构建前端
7. 启动后端服务并 reload Nginx
8. 检查 `/health`、`/ready`、`/ready/deep`
9. 浏览器 / iPad 抽测训练主链

### 11.1 确认服务器工作区

```bash
cd /opt/sc-training-system/current
git branch --show-current
git status --short
git log --oneline -n 5
```

必须确认当前分支是 `服务器端`，工作区干净，并且最新代码包含目标 commit。若 `git status --short` 有输出，立即停止，不要继续部署。

### 11.2 停止后端服务并备份生产数据库

迁移前建议先停止后端服务：

```bash
sudo systemctl stop sc-training-backend
sudo systemctl status sc-training-backend --no-pager --full
```

原因：当前生产数据库使用 SQLite，且可能运行在 WAL 模式下。运行中直接复制 `training.db`、`training.db-wal`、`training.db-shm` 可能存在一致性风险；迁移前备份应尽量在后端停止写入后执行。

如果项目已有可用备份脚本，应优先使用备份脚本生成迁移前备份。手动备份示例：

```bash
mkdir -p /opt/sc-training-system-data/manual-backups
ts=$(date +%Y%m%d-%H%M%S)

cp /opt/sc-training-system-data/training.db \
  /opt/sc-training-system-data/manual-backups/training-${ts}-before-manual-deploy.db

[ -f /opt/sc-training-system-data/training.db-wal ] && cp /opt/sc-training-system-data/training.db-wal /opt/sc-training-system-data/manual-backups/training-${ts}-before-manual-deploy.db-wal
[ -f /opt/sc-training-system-data/training.db-shm ] && cp /opt/sc-training-system-data/training.db-shm /opt/sc-training-system-data/manual-backups/training-${ts}-before-manual-deploy.db-shm

ls -lh /opt/sc-training-system-data/manual-backups/training-${ts}-before-manual-deploy.db*
```

必须确认备份文件存在且大小合理。备份失败时立即停止，不要继续部署。

### 11.3 更新服务器代码

```bash
cd /opt/sc-training-system/current
git fetch origin
git checkout 服务器端
git pull --ff-only origin 服务器端
git log --oneline -n 5
git status --short
```

如果 `git pull --ff-only` 失败，或 `git status --short` 不干净，立即停止。

### 11.4 安装后端依赖并确认生产库连接

```bash
cd /opt/sc-training-system/current/backend
source .venv/bin/activate
python -m pip install -r requirements.txt
grep DATABASE_URL .env
```

`DATABASE_URL` 应指向服务器生产库，例如：

```text
sqlite:////opt/sc-training-system-data/training.db
```

如果 `DATABASE_URL` 不是服务器生产库路径，立即停止。

### 11.5 FK orphan 预检

正式服务器迁移前，必须先在服务器生产库或生产库快照上运行：

```bash
python scripts/check_fk_orphans.py
```

只有确认 orphan=0 后，才能执行：

```bash
python scripts/migrate_db.py ensure
```

如果任何 orphan 不为 0，立即停止，不要执行 migration。

### 11.6 执行 migration

```bash
python scripts/migrate_db.py ensure
python scripts/migrate_db.py current
```

当前目标 revision 为：

```text
c9d0e1f2a3b4
```

如果 migration 失败，立即停止，不要启动生产服务，也不要指望启动时的 `schema_sync.py` 自动补表来兜底生产更新。

### 11.7 构建前端

```bash
cd /opt/sc-training-system/current/frontend
npm ci
npm run build
```

`Vite chunk size warning` 可以记录为 warning，不作为失败。`npm ci` 或 `npm run build` 失败时立即停止。

### 11.8 启动后端并 reload Nginx

```bash
sudo nginx -t
sudo systemctl start sc-training-backend
sudo systemctl status sc-training-backend --no-pager --full
sudo systemctl reload nginx
sudo systemctl status nginx --no-pager --full
```

如果 Nginx 配置检查失败、后端服务启动失败或 Nginx reload 失败，立即停止并查看日志：

```bash
sudo journalctl -u sc-training-backend -n 100 --no-pager
sudo journalctl -u nginx -n 100 --no-pager
```

### 11.9 健康检查和 revision 检查

```bash
curl -i http://127.0.0.1/health
curl -i http://127.0.0.1/ready
curl -i http://127.0.0.1/ready/deep
```

必须确认：

- `/health` 返回 200
- `/ready` 返回 200
- `/ready/deep` 返回 200
- `/ready/deep` 中 `current_revision` 必须等于 `head_revision`
- `current_revision` 和 `head_revision` 都必须是 `c9d0e1f2a3b4`

也就是：

```text
current_revision=head_revision=c9d0e1f2a3b4
```

如果 revision 不一致，立即停止，不要继续验收训练流程。

### 11.10 前端页面和浏览器 / iPad 抽测

浏览器访问服务器前端入口，例如：

```text
http://你的服务器IP/
```

先确认：

- 页面能正常打开，没有白屏
- 浏览器 DevTools Network 中 API 请求走同域 `/api`
- 不应出现直连 `localhost:8000`、`127.0.0.1:8000`、`5173`
- 必要时强制刷新页面：`Ctrl + F5`

训练主链抽测：

1. 使用管理员或教练账号登录。
2. 进入训练模式，选择一个有当天计划的运动员。
3. 打开当天训练计划，确认打开计划不等于开始训练。
4. 进入动作详情，录入一组重量 / 次数 / RIR 并提交。
5. 在监控端确认该运动员状态、当前动作、完成组数和最新一组数据已更新。
6. 在训练报告或训练记录回看中确认刚录入的一组存在，且重量 / 次数 / RIR 正确。

训练端无法打开计划、录入后数据未保存、监控端或报告端看不到刚录入数据时，立即停止继续验收。

### 11.11 回滚注意事项

数据库 migration 成功后，不要只回滚代码而继续使用已迁移数据库。回滚必须同时考虑：

- 当前代码是否兼容 `c9d0e1f2a3b4` 数据库结构
- 目标旧代码是否兼容当前数据库结构
- 是否需要恢复 migration 前数据库备份
- 前端构建产物、后端代码和数据库版本是否匹配

优先策略是：

```text
恢复到 migration 前备份 + 回到对应旧代码
```

而不是：

```text
只回滚代码，继续使用已迁移数据库
```

恢复备份属于危险操作，必须先再次备份当前生产库，停止后端服务，明确恢复哪个备份文件，并在恢复后重新检查 `/health`、`/ready`、`/ready/deep`。

## 12. 本地开发与服务器分工

### 本地开发

- 使用 Windows、本地 Vite dev server、本地 FastAPI 和开发数据库
- 可继续使用 `scripts/start_system.bat` / `scripts/init_system.bat`
- 本地启动链路属于开发工具链，不是生产运行方式

### 服务器运行

- 使用 Ubuntu、Nginx、systemd、SQLite 生产库
- 前端必须走构建产物
- 后端必须走同域 `/api`
- 生产数据不通过 GitHub 同步

## 13. 当前注意事项

- 不要在前端业务代码中写死 `localhost`、局域网 IP 或服务器公网 IP
- 不要把前端 API 改成直连公网 IP；默认应保持同域 `/api`
- 任何迁移、恢复、覆盖数据库前先备份
- 当前正式迁移主路径是 Alembic + `python scripts/migrate_db.py ensure`
- 公网部署必须启用登录限流
- `schema_sync.py` 不是生产迁移路径
- 不要开放 `8000` 端口
