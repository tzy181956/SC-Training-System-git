# 开发规范说明

## 文档身份

这份文档描述当前阶段的开发协作规范。  
它面向已经进入“服务器运行 + 本地开发并行”阶段的项目，不再把 Windows 本地链路写成唯一运行方式。

## 总体原则

- 先看现有实现，再做最小必要修改
- 训练执行稳定性优先于功能扩张
- 数据安全与可回退优先于一次性改完
- 文档、迁移、验证和代码同等重要
- 用户可见中文说明要与当前系统事实一致

## 当前事实基线

实施任何改动前，应以代码事实而不是旧文档为准，尤其要优先核对：

- `frontend/src/router/index.ts`
- `backend/app/api/router.py`
- 权限与登录相关实现
- Alembic `versions/`
- `backend/scripts/migrate_db.py`
- `deploy/` 与 `docs/deployment/tencent-lighthouse-ubuntu.md`

## 后端规范

- 核心业务逻辑放 `services`
- API 层负责参数接收、服务调用、返回结构
- 数据库结构变更优先走 Alembic migration
- 不把关键业务规则只写在前端
- 新增高成本查询时优先考虑列表分页、轻量响应和索引需求

### 数据库迁移要求

- 正式迁移入口：`backend/scripts/migrate_db.py`
- 迁移前先备份
- 新增表/字段/索引时必须同步补 migration
- 不再把 `schema_sync.py` 写成正式主方案

## 前端规范

- 页面与状态来源清晰
- 训练模式优先触摸操作效率
- 管理模式优先信息清晰与危险操作明确
- 实时监控优先状态可见性，不反向干扰训练录入
- 大数据页面优先考虑分页、搜索式加载和按需请求

## 接口规范

- 保持字段命名稳定
- 同一业务概念不要在不同接口返回不同字段名
- 新接口优先服务完整页面场景，不让前端拼大量零散请求

## 文档规范

每次实际改动后都要同步考虑文档影响，至少检查：

- `README.md`
- `PROJECT_CONTEXT.md`
- `CURRENT_STATUS.md`
- `DEVELOPMENT_GUIDE.md`
- `CODEX_HANDOFF.md`
- `NEXT_STEPS.md`
- `CHANGELOG.md`
- `docs/` 下相关专题文档

如果旧文档已经不符合当前实现，不要继续引用它当事实来源。

## 变更记录要求

每一轮会修改仓库内容的工作，都必须同步更新 `CHANGELOG.md`。

至少记录：

- 新增能力
- 行为变更
- 修复项
- 运维/迁移/部署注意事项

## 本地开发规则

- 本地开发入口仍使用 `scripts/start_system.bat`、`scripts/init_system.bat`
- 本地前后端联调仍使用 Windows + Vite dev server + FastAPI
- 本地数据库可继续使用 `backend/training.db`
- 本地开发脚本是开发工具，不是生产启动方式
- 不要因为服务器部署而破坏现有 Windows 本地开发链路

## 服务器运行规则

- 服务器是当前正式运行环境
- 前端通过构建产物部署
- 后端仅监听 `127.0.0.1:8000`
- Nginx 提供外部访问并反代 `/api`
- 生产数据库与代码目录分离
- 不开放开发端口到公网

## 服务器更新标准流程

默认通过 GitHub Actions 发布 release。服务器侧检查：

```bash
readlink -f /opt/sc-training-system/current
sudo systemctl status sc-training-backend
curl http://127.0.0.1/health
```

## 编码与中文规范

- 仓库文本文件统一使用 UTF-8
- 不要把终端乱码文本直接回写源码或文档
- 提交前建议运行：

```powershell
python scripts/check_text_encoding.py
```

详细规则见 `docs/text-encoding.md`。

## 改动提交前检查

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

- 关键页面或关键接口可用
- 文档口径没有落后于代码
- 若有 migration，迁移链路可运行
- `CHANGELOG.md` 已更新
