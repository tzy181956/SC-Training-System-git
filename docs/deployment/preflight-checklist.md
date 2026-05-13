# 上线前检查清单

> 文档状态：当前有效  
> 用途：服务器端分支上线、更新、迁移前的标准自检清单

## 1. 环境与配置

- [ ] 服务器部署目录已确认：`/opt/sc-training-system`
- [ ] 数据目录已确认：`/opt/sc-training-system-data`
- [ ] 后端 `.env` 已存在：`/opt/sc-training-system/backend/.env`
- [ ] `.env` 中已显式配置：
  - [ ] `APP_ENV=production`
  - [ ] `SECRET_KEY`
  - [ ] `DATABASE_URL=sqlite:////opt/sc-training-system-data/training.db`
  - [ ] `CORS_ORIGINS=["https://your-domain.example"]`
- [ ] `CORS_ORIGIN_REGEX` 在生产环境保持为空，除非你明确知道风险
- [ ] 已确认 systemd 服务用户存在：`sc-training`
- [ ] `/opt/sc-training-system/backend/.env` 对 `sc-training` 可读
- [ ] 未继续依赖开发默认值
- [ ] 前端未写死 `localhost`、`127.0.0.1`、局域网 IP 或公网 IP
- [ ] 前端默认仍走同域 `/api`，没有改成直连公网 IP 或 `:8000`

## 2. 数据库与迁移

- [ ] 已确认当前生产库路径正确
- [ ] 已在迁移前执行数据库备份
- [ ] 已执行正式迁移命令：

```bash
cd /opt/sc-training-system/backend
source .venv/bin/activate
python scripts/migrate_db.py ensure
```

- [ ] 已明确：生产环境启动时不会依赖 `schema_sync.py` 自动改表
- [ ] 已明确：如果生产环境做过备份恢复，恢复后还要再执行一次 `python scripts/migrate_db.py ensure`
- [ ] 如迁移失败，已停止继续重启生产服务

## 3. 前后端构建检查

- [ ] 后端依赖已安装完成
- [ ] 前端依赖已安装完成
- [ ] 前端构建通过：

```bash
cd /opt/sc-training-system/frontend
npm install
npm run build
```

- [ ] 后端语法编译通过：

```bash
cd /opt/sc-training-system/backend
python -m compileall app scripts
```

## 4. systemd 服务检查

- [ ] 已使用最新 `deploy/sc-training-backend.service`
- [ ] systemd 单元中的 `User=sc-training`、`Group=sc-training` 已确认
- [ ] `WorkingDirectory`、`EnvironmentFile`、`ExecStart` 路径与服务器一致
- [ ] 服务监听仅为 `127.0.0.1:8000`
- [ ] Uvicorn 启动参数包含：
  - [ ] `--proxy-headers`
  - [ ] `--forwarded-allow-ips=127.0.0.1`
- [ ] 服务硬化项已确认：
  - [ ] `NoNewPrivileges=true`
  - [ ] `PrivateTmp=true`
  - [ ] `ProtectSystem=strict`
  - [ ] `ProtectHome=true`
  - [ ] `ReadWritePaths=/opt/sc-training-system-data`
- [ ] 数据目录已执行 `chown -R sc-training:sc-training /opt/sc-training-system-data`
- [ ] 数据目录对服务进程可写，允许 SQLite 生成 `training.db-wal` / `training.db-shm`

常用检查：

```bash
sudo systemctl daemon-reload
sudo systemctl restart sc-training-backend
sudo systemctl status sc-training-backend
journalctl -u sc-training-backend -n 100 --no-pager
```

## 5. Nginx 与公网入口

- [ ] 已使用最新 `deploy/nginx-sc-training.conf`
- [ ] 公网生产优先使用 `deploy/nginx-sc-training.production.conf`，或确认基础版里的登录限流注释已真正改成生效配置
- [ ] `/api/` 与 `/health` 反代仍指向 `127.0.0.1:8000`
- [ ] 未开放 `8000` 端口到公网
- [ ] 仅开放 `22`、`80`、`443`
- [ ] 已配置真实 `server_name`
- [ ] 公网部署已启用 HTTPS
- [ ] 公网部署已启用登录限流

登录限流最低要求：

```nginx
limit_req_zone $binary_remote_addr zone=sc_training_login:10m rate=5r/m;
```

- [ ] 已确认 `limit_req_zone` 写在 Nginx 全局 `http {}` 中，不只是站点注释
- [ ] `/api/auth/login` 已挂载 `limit_req`
- [ ] `index.html` 已设置 `Cache-Control: no-store`
- [ ] `/assets/` 已设置长缓存
- [ ] 安全响应头已检查：`X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`
- [ ] 修改后已执行：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 6. 健康检查

- [ ] 本机健康检查通过：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1/health
```

- [ ] 浏览器可正常打开前端首页
- [ ] 登录页可正常加载
- [ ] 管理模式、训练模式、监控模式入口可见且可切换

## 7. 备份与恢复准备

- [ ] 已确认本机备份目录可写
- [ ] 已确认危险操作前会先备份
- [ ] 已准备异地备份副本
- [ ] 已确认恢复流程前会先备份当前生产库
- [ ] 已明确：生产恢复后不会隐式运行 `schema_sync.py`
- [ ] 已明确：生产恢复后必须补跑 `python scripts/migrate_db.py ensure`
- [ ] 已知道最近一次可用备份在哪里

## 8. 登录与权限回归

- [ ] `admin` 可登录
- [ ] `coach` 可登录
- [ ] 错误密码返回正常，不暴露敏感信息
- [ ] 登录频繁失败时可被 Nginx 限流
- [ ] `admin` 可访问管理、日志、备份、账号管理
- [ ] `coach` 不会误拿到 `admin` 能力
- [ ] 未登录访问受保护页面会被拦回登录页

## 9. 训练现场回归

- [ ] 至少使用一台教练电脑和一台平板/手机做联调
- [ ] 训练端可打开当天计划
- [ ] 每组录入后本地保存正常
- [ ] 断网或后端短暂不可用时不影响继续录入
- [ ] 恢复网络后可正常补传
- [ ] 监控端能在短时间内看到训练状态变化
- [ ] 同步异常时监控端有提示
- [ ] 手动结束未完成课程后状态正确
- [ ] 训练报告能看到刚刚的训练记录

## 10. 最终放行条件

只有同时满足下面条件，才建议执行正式上线或更新：

- [ ] 迁移已完成
- [ ] 构建已完成
- [ ] systemd 正常
- [ ] Nginx 正常
- [ ] 健康检查正常
- [ ] 备份存在
- [ ] 登录限流已启用
- [ ] 权限回归通过
- [ ] 训练现场回归通过
