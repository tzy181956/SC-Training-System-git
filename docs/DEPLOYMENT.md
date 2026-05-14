# GitHub Actions 自动部署说明

> 适用对象：`Deploy Production` workflow  
> 触发分支：`服务器端`  
> 部署方式：GitHub Actions 先做基础检查，再通过 SSH 登录腾讯云服务器，在服务器指定 Git 工作目录执行 `git pull`、依赖安装、数据库迁移、前端构建、服务重启和健康检查。

## 1. GitHub Secrets 清单

进入 GitHub 仓库：

`Settings -> Secrets and variables -> Actions -> Repository secrets -> New repository secret`

必须配置：

| Secret | 含义 |
| --- | --- |
| `SERVER_HOST` | 腾讯云服务器公网 IP 或域名。不要带 `http://` 或 `https://`。 |
| `SERVER_USER` | 用于 SSH 部署的服务器用户，例如 `deploy`。 |
| `SSH_PRIVATE_KEY` | 部署用户对应的 SSH 私钥完整内容。只放私钥，不放公钥。 |
| `DEPLOY_PATH` | 服务器上的项目 Git 工作目录。该目录必须存在 `.git`，并能 `git pull` `服务器端` 分支。 |

建议配置：

| Secret | 含义 |
| --- | --- |
| `SERVER_PORT` | SSH 端口，默认 `22`。如果腾讯云安全组或 sshd 改过端口，必须配置。 |
| `SSH_KNOWN_HOSTS` | 服务器 SSH host key 的 `known_hosts` 行。强烈建议配置，避免部署时临时信任 `ssh-keyscan` 结果。 |

可选配置：

| Secret 或 Variable | 默认值 | 含义 |
| --- | --- | --- |
| `SERVICE_NAME` | `sc-training-backend` | systemd 后端服务名。 |
| `NGINX_SERVICE` | `nginx` | Nginx systemd 服务名。 |
| `HEALTHCHECK_URL` | `http://127.0.0.1/health` | 部署完成后的健康检查地址。 |

兼容旧名称：

当前 workflow 仍兼容旧 Secrets：`SSH_HOST`、`SSH_USER`、`SSH_PORT`、`SSH_KEY`。如果新旧都配置，优先使用新名称：`SERVER_HOST`、`SERVER_USER`、`SERVER_PORT`、`SSH_PRIVATE_KEY`。

## 2. 腾讯云安全组端口

建议只开放：

- `22`：SSH。若你自定义了 SSH 端口，则开放自定义端口。
- `80`：HTTP。
- `443`：HTTPS，配置域名和证书后使用。

不要开放：

- `8000`：FastAPI 只应监听 `127.0.0.1:8000`，由 Nginx 本机反代。
- `5173`：Vite dev server 只属于本地开发。
- `3306` 或 `ALL`。

## 3. SSH 公钥和私钥放哪里

在本地电脑生成部署密钥：

```bash
ssh-keygen -t ed25519 -C "sc-training-github-actions" -f sc_training_actions_ed25519
```

生成后会有两个文件：

- `sc_training_actions_ed25519`：私钥，放到 GitHub Secret `SSH_PRIVATE_KEY`
- `sc_training_actions_ed25519.pub`：公钥，放到服务器部署用户的 `authorized_keys`

在服务器上配置公钥：

```bash
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
echo '<把 sc_training_actions_ed25519.pub 的整行内容放这里>' | sudo tee /home/deploy/.ssh/authorized_keys >/dev/null
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

不要把私钥提交到仓库。不要把公钥填进 `SSH_PRIVATE_KEY`。

## 4. SSH_KNOWN_HOSTS 配置

推荐先在可信环境核对服务器 host key 指纹：

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

在本地电脑获取 `known_hosts` 行：

```bash
ssh-keyscan -p 22 your-server-host.example > sc-training-known-hosts
ssh-keygen -lf sc-training-known-hosts
cat sc-training-known-hosts
```

确认指纹一致后，把 `cat sc-training-known-hosts` 输出的完整内容保存为 GitHub Secret：`SSH_KNOWN_HOSTS`。

如果不配置 `SSH_KNOWN_HOSTS`，workflow 会临时执行 `ssh-keyscan`，但会打印 warning。生产环境建议不要长期依赖临时扫描。

## 5. 服务器目录和首次准备

当前 workflow 要求 `DEPLOY_PATH` 是一个 Git 工作目录。示例：

```bash
sudo mkdir -p /opt/sc-training-system
sudo chown -R deploy:deploy /opt/sc-training-system
sudo -u deploy git clone -b 服务器端 <你的 GitHub 仓库地址> /opt/sc-training-system
```

注意：服务器上的 `deploy` 用户也必须有权限从 GitHub 拉取仓库。  
如果仓库是 private，需要给服务器单独配置 GitHub deploy key 或其他只读拉取凭据。这个凭据是“服务器 -> GitHub”的凭据，不是 `SSH_PRIVATE_KEY`；`SSH_PRIVATE_KEY` 只用于“GitHub Actions -> 腾讯云服务器”。

如果你沿用 systemd 模板里的默认路径 `/opt/sc-training-system/current/backend`，则有两种做法，二选一：

- 把 `DEPLOY_PATH` 设置为 `/opt/sc-training-system/current`，并确保 `/opt/sc-training-system/current` 本身是 Git clone。
- 或把 systemd / Nginx 模板里的 `current` 路径改成你的 Git 工作目录，例如 `/opt/sc-training-system/backend` 和 `/opt/sc-training-system/frontend/dist`。

生产后端环境文件必须存在：

```bash
cd <DEPLOY_PATH>
cp deploy/backend.env.production.example backend/.env
nano backend/.env
```

至少确认：

```dotenv
APP_ENV=production
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:////opt/sc-training-system-data/training.db
CORS_ORIGINS=["https://your-domain.example"]
CORS_ORIGIN_REGEX=
```

服务器依赖：

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nodejs npm nginx curl
```

部署用户需要能无密码执行这些命令：

```bash
sudo tee /etc/sudoers.d/sc-training-deploy >/dev/null <<'EOF'
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart sc-training-backend, /usr/bin/systemctl reload nginx, /usr/sbin/nginx -t, /usr/bin/systemctl --no-pager --full status sc-training-backend, /usr/bin/journalctl -u sc-training-backend -n 100 --no-pager
EOF
sudo chmod 440 /etc/sudoers.d/sc-training-deploy
```

如果系统里的命令路径不同，用 `which systemctl`、`which nginx`、`which journalctl` 确认后再调整 sudoers。

## 6. Actions 执行流程

`Deploy Production` 当前流程：

1. checkout 仓库
2. 安装后端依赖
3. 安装前端依赖
4. 执行后端基础检查
5. 执行前端生产构建
6. 校验部署 Secrets
7. 配置 SSH key 和 `known_hosts`
8. 测试 SSH 连接
9. SSH 登录服务器
10. 在 `DEPLOY_PATH` 执行 `git fetch`、`git checkout 服务器端`、`git pull --ff-only`
11. 安装后端依赖
12. 执行 `python scripts/migrate_db.py ensure`
13. 执行 `npm ci && npm run build`
14. 执行 `sudo nginx -t`
15. 重启后端 systemd 服务
16. reload Nginx
17. 请求 `HEALTHCHECK_URL`

## 7. 手动重新运行部署

在 GitHub 网页：

1. 进入仓库。
2. 点击顶部 `Actions`。
3. 左侧选择 `Deploy Production`。
4. 点击失败或最近一次运行。
5. 如果要重跑同一次提交，点击右上角 `Re-run jobs`。
6. 如果要手动触发，回到 `Deploy Production` workflow 首页，点击 `Run workflow`，选择 `服务器端` 分支，再点击绿色按钮。

## 8. 常见错误和排查

### Permission denied

含义：SSH 认证失败。

检查：

- GitHub Secret `SSH_PRIVATE_KEY` 是否是私钥，不是 `.pub` 公钥。
- 私钥是否包含完整的 `BEGIN OPENSSH PRIVATE KEY` 到 `END OPENSSH PRIVATE KEY`。
- 公钥是否已经放到服务器 `/home/deploy/.ssh/authorized_keys`。
- `SERVER_USER` 是否就是放置公钥的用户。
- 服务器 `/home/deploy/.ssh` 权限是否为 `700`，`authorized_keys` 是否为 `600`。

### Connection refused

含义：网络能到服务器，但 SSH 端口没有服务监听或被安全组拦截。

检查：

- 腾讯云安全组是否开放 `SERVER_PORT`。
- `SERVER_PORT` 是否和服务器 `/etc/ssh/sshd_config` 一致。
- 服务器 sshd 是否运行：`sudo systemctl status ssh`。

### Host key verification failed

含义：`known_hosts` 不匹配或缺失。

检查：

- GitHub Secret `SSH_KNOWN_HOSTS` 是否保存了当前服务器的 host key。
- 服务器重装后 host key 会变化，需要重新核对并更新 `SSH_KNOWN_HOSTS`。
- 如果端口不是 `22`，`known_hosts` 行通常是 `[host]:port` 格式。

### cd: no such file or directory

含义：`DEPLOY_PATH` 不存在。

检查：

- GitHub Secret 或 Variable `DEPLOY_PATH` 是否填对。
- 服务器上是否真的存在这个目录。
- 该目录是否属于部署用户，部署用户是否有读写权限。

### DEPLOY_PATH is not a git working tree

含义：`DEPLOY_PATH` 目录下没有 `.git`。

检查：

- 是否把 `DEPLOY_PATH` 填成了 release 根目录，而不是 Git clone。
- 如果使用 `/opt/sc-training-system/current`，确认它不是无 `.git` 的发布包目录。
- 重新在该目录执行 `git clone -b 服务器端 <repo> <DEPLOY_PATH>`。

### npm command not found

含义：服务器没有安装 Node.js / npm，或部署用户 PATH 里找不到。

处理：

```bash
sudo apt update
sudo apt install -y nodejs npm
npm -v
```

### python3 command not found

含义：服务器没有 Python 3。

处理：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 --version
```

### alembic not found

含义：后端依赖没有装好，或虚拟环境没有激活。

检查：

- `backend/requirements.txt` 是否包含 `alembic`。
- Actions 日志中 `python -m pip install -r requirements.txt` 是否失败。
- 在服务器手动执行：

```bash
cd <DEPLOY_PATH>/backend
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/migrate_db.py ensure
```

### sudo: a password is required

含义：部署用户没有免密码执行 systemd / nginx 命令的权限。

处理：

- 检查 `/etc/sudoers.d/sc-training-deploy`。
- 确认里面的用户名和 `SERVER_USER` 一致。
- 确认命令路径和服务器实际路径一致。

### git pull --ff-only failed

含义：服务器 Git 工作目录有本地提交、分支分叉或未提交改动。

处理：

- 不要直接删除生产数据。
- 先登录服务器检查：

```bash
cd <DEPLOY_PATH>
git status
git branch --show-current
git log --oneline --decorate -n 5
```

如果只是服务器代码目录有无关本地改动，先明确影响范围，再决定是否提交、暂存或重新 clone。

### git fetch origin 失败并提示 Permission denied

含义：服务器上的部署用户不能从 GitHub 拉取仓库。

检查：

- 登录服务器后执行：`sudo -u deploy ssh -T git@github.com`
- 如果仓库是 private，确认服务器部署用户已经配置 GitHub deploy key。
- 确认 `DEPLOY_PATH` 的 `origin` 地址正确：`git remote -v`
- 这个错误不是 `SSH_PRIVATE_KEY` 配错。`SSH_PRIVATE_KEY` 只负责 Actions 登录腾讯云服务器。

## 9. GitHub 网页手动操作清单

你需要在 GitHub 网页完成：

1. 打开仓库页面。
2. 进入 `Settings`。
3. 左侧进入 `Secrets and variables`。
4. 点击 `Actions`。
5. 在 `Repository secrets` 中新增：
   - `SERVER_HOST`
   - `SERVER_USER`
   - `SSH_PRIVATE_KEY`
   - `DEPLOY_PATH`
   - 推荐：`SERVER_PORT`
   - 推荐：`SSH_KNOWN_HOSTS`
6. 如需修改服务名或健康检查地址，再新增：
   - `SERVICE_NAME`
   - `NGINX_SERVICE`
   - `HEALTHCHECK_URL`
7. 回到 `Actions`。
8. 点击 `Deploy Production`。
9. 点击 `Run workflow`，选择 `服务器端` 分支。
10. 观察运行日志中是否出现：
    - `SSH connection OK`
    - `Pulling latest code with fast-forward only`
    - `Running database migration ensure`
    - `Building frontend`
    - `Health check passed`
    - `Deployment completed successfully`
