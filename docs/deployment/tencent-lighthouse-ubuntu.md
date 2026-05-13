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
sudo mkdir -p /opt/sc-training-system
sudo chown -R $USER:$USER /opt/sc-training-system
git clone <仓库地址> /opt/sc-training-system
```

### 5.3 创建 systemd 服务用户

```bash
sudo useradd --system --home /opt/sc-training-system --shell /usr/sbin/nologin sc-training
```

### 5.4 创建数据目录

生产环境建议把 SQLite、WAL/SHM sidecar 文件和自动备份目录统一放在独立数据目录，并交给 `sc-training` 服务用户写入：

```bash
sudo mkdir -p /opt/sc-training-system-data
sudo chown -R sc-training:sc-training /opt/sc-training-system-data
sudo chmod 750 /opt/sc-training-system-data
```

### 5.5 配置后端 `.env`

路径：

- `/opt/sc-training-system/backend/.env`
- 仓库示例：`deploy/backend.env.production.example`

建议直接从示例文件复制：

```bash
cd /opt/sc-training-system
cp deploy/backend.env.production.example backend/.env
sudo chown root:sc-training backend/.env
sudo chmod 640 backend/.env
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

```bash
cd /opt/sc-training-system/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/migrate_db.py ensure
```

这是生产环境首次启动前必须执行的正式迁移步骤。

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
cd /opt/sc-training-system
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
cd /opt/sc-training-system/backend
source .venv/bin/activate
python scripts/migrate_db.py ensure
sudo systemctl restart sc-training-backend
```

生产恢复流程不会隐式调用 `schema_sync.py` 自动改表。
如果恢复的是旧备份，必须依赖正式 Alembic migration 把结构收口到当前代码版本。

## 11. 更新标准流程

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

更新原则：

- 先备份，再迁移，再重启服务
- `python scripts/migrate_db.py ensure` 必须在每次生产启动或更新前执行
- 如果迁移失败，不要继续重启生产服务
- 不要指望启动时的 `schema_sync` 自动补表来兜底生产更新

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
