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

### 5.3 创建数据目录

```bash
sudo mkdir -p /opt/sc-training-system-data
sudo chown -R $USER:$USER /opt/sc-training-system-data
sudo chmod 755 /opt/sc-training-system-data
```

### 5.4 配置后端 `.env`

路径：

- `/opt/sc-training-system/backend/.env`

最小示例：

```dotenv
APP_ENV=production
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/sc-training-system-data/training.db
CORS_ORIGINS=["http://服务器地址"]
```

## 6. 后端部署

```bash
cd /opt/sc-training-system/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/migrate_db.py ensure
```

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

典型流程：

```bash
cd /opt/sc-training-system
sudo cp deploy/sc-training-backend.service /etc/systemd/system/sc-training-backend.service
sudo cp deploy/nginx-sc-training.conf /etc/nginx/sites-available/sc-training
sudo ln -s /etc/nginx/sites-available/sc-training /etc/nginx/sites-enabled/sc-training
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl daemon-reload
sudo systemctl enable sc-training-backend
sudo systemctl start sc-training-backend
sudo nginx -t
sudo systemctl reload nginx
```

## 9. 更新标准流程

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

## 10. 本地开发与服务器分工

### 本地开发

- 使用 Windows、本地 Vite dev server、本地 FastAPI 和开发数据库
- 可继续使用 `scripts/start_system.bat` / `scripts/init_system.bat`
- 本地启动链路属于开发工具链，不是生产运行方式

### 服务器运行

- 使用 Ubuntu、Nginx、systemd、SQLite 生产库
- 前端必须走构建产物
- 后端必须走同域 `/api`
- 生产数据不通过 GitHub 同步

## 11. 当前注意事项

- 不要在前端业务代码中写死 `localhost`、局域网 IP 或服务器公网 IP
- 任何迁移、恢复、覆盖数据库前先备份
- 当前正式迁移主路径是 Alembic + `python scripts/migrate_db.py ensure`
