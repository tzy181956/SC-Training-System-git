# 腾讯云轻量应用服务器 Ubuntu 部署说明

本文档用于第一次将本项目部署到腾讯云轻量应用服务器 Ubuntu。

目标是先跑通：

- HTTP 访问
- 前端同域 `/api`
- FastAPI 后端常驻
- SQLite 单机部署

本文档当前不包含：

- Docker
- PostgreSQL
- HTTPS 证书自动化

## 一、部署架构说明

当前部署架构如下：

1. 服务器环境：腾讯云轻量应用服务器 Ubuntu。
2. Nginx 对外提供 `80` 端口，后续 `HTTPS` 单独配置。
3. 前端 Vue 通过 `npm run build` 生成 `dist`，由 Nginx 托管。
4. 后端 FastAPI 通过 systemd 常驻运行。
5. 后端只监听 `127.0.0.1:8000`。
6. Nginx 将 `/api/` 反代到 `127.0.0.1:8000/api/`。
7. Nginx 将 `/health` 反代到 `127.0.0.1:8000/health`。
8. 数据库当前使用 SQLite。
9. 不使用 Docker。
10. 不迁移 PostgreSQL。

## 二、腾讯云防火墙要求

轻量应用服务器防火墙当前只建议开放：

- `22`：SSH
- `80`：HTTP
- `443`：HTTPS，后续有域名和证书时再使用

当前不要开放：

- `5173`
- `8000`
- `3306`
- `ALL`

说明：

- `5173` 是本地开发端口，不用于生产。
- `8000` 只给 Nginx 在本机回源，不应对公网开放。
- 当前部署是单机 SQLite，不需要 `3306`。

## 三、服务器基础依赖安装

先连接到 Ubuntu 服务器，然后执行：

```bash
sudo apt update
sudo apt install -y git
sudo apt install -y python3 python3-venv python3-pip
sudo apt install -y nodejs npm
sudo apt install -y nginx
```

安装完成后可简单确认：

```bash
python3 --version
node -v
npm -v
nginx -v
```

## 四、拉取项目

项目固定部署路径：

- `/opt/sc-training-system`

首次部署：

```bash
sudo mkdir -p /opt/sc-training-system
sudo chown -R $USER:$USER /opt/sc-training-system
git clone <你的仓库地址> /opt/sc-training-system
```

如果目录已经存在，进入目录后更新：

```bash
cd /opt/sc-training-system
git pull origin 服务器端
```

如果 `/opt/sc-training-system` 已存在但不是这个项目仓库，不要直接覆盖。先确认目录内容，再决定是否备份或迁移。

## 五、后端 .env 配置

生产环境必须手动创建：

- `/opt/sc-training-system/backend/.env`

最小示例：

```dotenv
APP_ENV=production
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/sc-training-system-data/training.db
CORS_ORIGINS=["http://服务器IP"]
```

说明：

1. 不要把 `.env` 提交到 Git。
2. `SECRET_KEY` 不要使用 `dev-secret-key-change-me`。
3. `CORS_ORIGINS` 可以先写 `http://服务器IP`，后续有域名后再改成 `https://你的域名`。
4. 如果 `APP_ENV=production` 但缺少 `SECRET_KEY`、`DATABASE_URL` 或 `CORS_ORIGINS`，后端会启动失败。这是正常的安全保护，不是 bug。

创建方式示例：

```bash
cd /opt/sc-training-system/backend
nano .env
```

## 六、创建生产数据目录

推荐将生产数据目录独立出来：

- `/opt/sc-training-system-data`

执行：

```bash
sudo mkdir -p /opt/sc-training-system-data
sudo chown -R $USER:$USER /opt/sc-training-system-data
sudo chmod 755 /opt/sc-training-system-data
```

如果你使用的部署用户不是当前 SSH 用户，请把 `$USER` 替换成实际部署用户。

## 七、后端依赖安装

执行：

```bash
cd /opt/sc-training-system/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果后续有依赖变更，更新代码后也要重新执行：

```bash
cd /opt/sc-training-system/backend
source .venv/bin/activate
pip install -r requirements.txt
```

## 八、数据库迁移

首次部署前执行：

```bash
cd /opt/sc-training-system/backend
source .venv/bin/activate
python scripts/migrate_db.py ensure
```

说明：

1. 首次部署前执行一次。
2. 每次代码更新后也建议执行一次。
3. 如果已经有真实 `training.db`，迁移前先备份，不要直接在唯一一份生产库上冒险。

## 九、创建第一个 admin

当前项目已有脚本：

- `backend/scripts/create_user.py`

示例命令：

```bash
cd /opt/sc-training-system/backend
source .venv/bin/activate
python scripts/create_user.py --username admin --display-name "系统管理员" --role-code admin
```

说明：

1. 该脚本会通过 `getpass` 交互输入密码，不会在命令行明文回显。
2. 不要把真实密码写进文档、脚本或 shell 历史里。
3. 第一个 `admin` 创建后，后续 `coach` / `training` 账号通过后台“账号管理”页面创建。

## 十、前端安装和构建

执行：

```bash
cd /opt/sc-training-system/frontend
npm install
npm run build
```

说明：

1. 构建产物位于 `frontend/dist`。
2. 如果是 `2GB` 服务器，`npm run build` 因内存不足失败，可以先评估是否临时增加 swap；当前文档不默认执行任何 swap 相关危险命令。

## 十一、安装 systemd 后端服务

使用现有模板：

- `deploy/sc-training-backend.service`

执行：

```bash
cd /opt/sc-training-system
sudo cp deploy/sc-training-backend.service /etc/systemd/system/sc-training-backend.service
sudo systemctl daemon-reload
sudo systemctl enable sc-training-backend
sudo systemctl start sc-training-backend
sudo systemctl status sc-training-backend
journalctl -u sc-training-backend -f
```

## 十二、安装 Nginx 配置

使用现有模板：

- `deploy/nginx-sc-training.conf`

执行：

```bash
cd /opt/sc-training-system
sudo cp deploy/nginx-sc-training.conf /etc/nginx/sites-available/sc-training
sudo ln -s /etc/nginx/sites-available/sc-training /etc/nginx/sites-enabled/sc-training
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status nginx
```

## 十三、首次验收

先在服务器本机执行：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1/health
curl http://127.0.0.1/
```

然后做浏览器验收：

1. 浏览器访问 `http://服务器IP`
2. 用 `admin` 登录
3. 创建 `coach`
4. 创建 `training`
5. 用 `training` 登录，确认进入训练模式
6. 用 `coach` 登录，确认不能进入账号管理

接口权限验收建议：

未登录应返回 `401`：

```bash
curl -i http://127.0.0.1/api/users
```

如需用 `curl` 验证 `coach` / `admin`，可先登录拿 token：

```bash
curl -X POST http://127.0.0.1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"你的用户名","password":"你的密码"}'
```

然后替换 `<TOKEN>`：

```bash
curl -i http://127.0.0.1/api/users -H "Authorization: Bearer <COACH_TOKEN>"
curl -i http://127.0.0.1/api/users -H "Authorization: Bearer <ADMIN_TOKEN>"
```

预期结果：

- 未登录访问 `/api/users`：`401`
- `coach` 访问 `/api/users`：`403`
- `admin` 访问 `/api/users`：`200`

## 十四、日常更新流程

每次更新建议按这个顺序执行：

```bash
cd /opt/sc-training-system
git pull origin 服务器端
```

```bash
cd /opt/sc-training-system/backend
source .venv/bin/activate
pip install -r requirements.txt
python scripts/migrate_db.py ensure
```

```bash
cd /opt/sc-training-system/frontend
npm install
npm run build
```

```bash
sudo systemctl restart sc-training-backend
sudo systemctl reload nginx
curl http://127.0.0.1/health
```

补充说明：

1. 如果只改前端，通常仍需要执行 `npm run build` 和 `sudo systemctl reload nginx`。
2. 如果只改后端，通常需要执行 `sudo systemctl restart sc-training-backend`。
3. 如果改数据库模型，必须先准备 Alembic 迁移，并执行 `python scripts/migrate_db.py ensure`。
4. 如果改 Python 或前端依赖，必须重新执行 `pip install -r requirements.txt` 或 `npm install`。
5. 每次更新后都必须再做浏览器人工验收。
6. 如果更新涉及数据库风险，先备份生产数据再执行。

## 十五、备份和数据注意事项

请始终遵守：

1. 生产数据库不要提交 Git。
2. 生产数据库不要随意覆盖。
3. 操作数据库前先备份。
4. 手动备份目录固定为 `/opt/sc-training-system-data/manual-backups`。
5. 换服务器时需要一起迁移：
   - `.env`
   - `training.db`
   - `manual-backups`
   - Nginx 配置
   - systemd 配置
6. SQLite 只适合单机单实例，不要开多个后端实例写同一份库。

当前推荐配置：

- 数据库：`/opt/sc-training-system-data/training.db`
- 手动备份目录：`/opt/sc-training-system-data/manual-backups/`
- 自动备份脚本：`/opt/sc-training-system-data/backup_daily.sh`
- `crontab` 目标项：

```cron
30 2 * * * /opt/sc-training-system-data/backup_daily.sh >> /opt/sc-training-system-data/manual-backups/backup.log 2>&1
```

## 十六、常见错误排查

### 1. Nginx 502

优先检查：

```bash
sudo systemctl status sc-training-backend
curl http://127.0.0.1:8000/health
journalctl -u sc-training-backend -f
```

### 2. 页面能打开但接口失败

优先检查：

- 前端是否请求同域 `/api`
- Nginx `/api` 反代是否仍指向 `127.0.0.1:8000/api/`

### 3. 后端启动失败

优先检查：

- `backend/.env` 是否存在
- `APP_ENV=production` 下是否正确配置了：
  - `SECRET_KEY`
  - `DATABASE_URL`
  - `CORS_ORIGINS`

### 4. npm build 失败

优先检查：

- `node` / `npm` 是否正常
- 服务器内存是否不足

### 5. 登录失败

优先检查：

- 是否已经创建第一个 `admin`
- 账号是否为 `active`
- 密码是否正确

### 6. 端口访问异常

优先检查：

- 腾讯云防火墙是否已开放 `80`
- 不要开放 `8000`

## 十七、本地开发与云服务器协作规范

### 环境分工

- 本地电脑是开发环境。
- 腾讯云 Ubuntu 服务器是线上调试 / 运行环境。
- GitHub 是代码同步中转。
- 本地数据库和服务器数据库不是同一个。
- 代码通过 GitHub 同步，生产数据不通过 GitHub 同步。

### 本地开发规则

- 本地可以继续使用 Windows 启动脚本、局域网访问、Vite dev server、FastAPI 本地后端。
- 本地可以继续使用 `backend/training.db` 做开发数据。
- 但不要把 `backend/training.db`、`backend/backups/*.db`、`.env`、日志、`node_modules`、`dist` 等运行时文件提交到 Git。
- 本地开发默认可以使用 `APP_ENV=development`。
- 不要因为服务器部署而删除或破坏现有 Windows 本地启动链路。

### 服务器运行规则

- 服务器项目目录：`/opt/sc-training-system`
- 服务器数据目录：`/opt/sc-training-system-data`
- 生产数据库：`/opt/sc-training-system-data/training.db`
- 后端 systemd 服务名：`sc-training-backend`
- 后端只监听 `127.0.0.1:8000`
- Nginx 对外提供 `80`
- Nginx 托管 `frontend/dist`
- `/api/` 反代到 `http://127.0.0.1:8000/api/`
- `/health` 反代到 `http://127.0.0.1:8000/health`
- 不开放 `8000`、`5173`、`3306`、`ALL`
- 当前 HTTP 调试版已经部署成功，HTTPS 和域名后续再做

### 本地与服务器差异

- Windows 不区分大小写，Ubuntu 区分大小写。
- Windows 路径是反斜杠，Ubuntu 路径是正斜杠。
- 本地 Vite dev server 不等于服务器生产 build。
- 本地 `localhost` / 局域网 IP 不能写死到生产代码。
- 服务器前端请求后端必须走同域 `/api`。
- 不允许在前端代码里写死 `localhost:8000`、`127.0.0.1:8000`、`192.168.x.x:8000` 或服务器公网 IP。
- 服务器数据库和本地数据库不同，不能用 `git pull` 覆盖生产数据库。

### 性能注意事项

- 动作库约 `1795` 条。
- `exercise_categories` 约 `788` 条。
- 动作库和训练模板首次加载较慢。
- 当前先不在本部署文档里直接推动性能重构。
- 后续优化方向是分页、搜索式加载、轻量接口、管理首页避免全量加载。
- 后续修改动作库和训练模板时，应优先考虑分页和懒加载，不要继续扩大首屏全量请求。

## 十八、后续 HTTPS

当前文档先以跑通 HTTP 为目标。

后续有正式域名后，再单独配置 HTTPS。

本次文档不包含复杂证书自动化步骤。
