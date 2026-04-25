# 第一阶段重构补充｜启动器失败摘要与排障文档联动

## 1. 这一步只解决什么

本文件只记录第一阶段中的“启动器失败摘要与排障文档联动”，目标是：

1. 启动器失败时，不再只留一屏难以转发的原始日志。
2. 失败时自动生成一段**可复制、适合直接发给 AI** 的错误摘要。
3. 摘要同时给出：
   - 失败步骤
   - 错误类型
   - 最可能原因
   - 建议修复
4. 仍然保留详细日志文件路径，保证摘要和原始日志能对应。
5. 给非程序员一份固定排障文档，先看常见问题，再决定是否继续求助。

本步不展开：

- 启动器 GUI
- 复杂运维面板
- 业务逻辑改造

---

## 2. 当前产物

### 2.1 可复制失败摘要

失败时会写出：

```text
logs/startup/last-launcher-summary.txt
```

同时保留一份带时间戳的副本：

```text
logs/startup/launcher-summary-YYYYMMDD-HHMMSS.txt
```

摘要内容固定收口为：

1. 时间
2. 模式（`start / init`）
3. 失败步骤
4. 错误类型
5. 错误代码
6. 最可能原因
7. 建议修复
8. 详细日志路径
9. 对应排障文档路径
10. 最近几行日志摘录

### 2.2 详细日志

启动器详细日志会写到：

```text
logs/startup/last-launcher-detail.log
```

同时保留一份带时间戳的原始详细日志：

```text
logs/startup/launcher-detail-YYYYMMDD-HHMMSS.log
```

详细日志负责保留：

- 每一步开始时间
- 每一步结果
- 启动器执行的命令
- 命令输出全文
- 最终成功 / 失败状态

### 2.3 排障文档

当前统一排障文档就是本文件本身：

```text
docs/phase1-launcher-failure-summary.md
```

失败摘要会把这个文档路径一起写进去，方便直接打开对照。

---

## 3. 失败摘要适合怎么用

第一阶段推荐做法不是把整屏终端输出截图发给 AI，而是：

1. 先复制 `last-launcher-summary.txt`
2. 如果 AI 还需要更多上下文，再补 `last-launcher-detail.log`

这样做的原因是：

- 摘要先给出结构化信息
- 详细日志只在需要时再补
- 可以减少“乱日志里没有重点”的沟通成本

---

## 4. 当前错误类型与建议映射

下表是启动器当前固定收口的错误类型：

| 错误代码 | 错误类型 | 最常见原因 | 首选修复建议 |
| --- | --- | --- | --- |
| `powershell_missing` | PowerShell 不可用 | 当前电脑没有可用的 Windows PowerShell，或 `powershell.exe` 不在 PATH | 先恢复 Windows PowerShell，再重新运行 `.bat` |
| `python_missing` | Python 3.12 未找到 | 没安装 Python 3.12，或 PATH 没指向它 | 安装 Python 3.12.x 并加入 PATH |
| `python_version_unsupported` | Python 版本不支持 | 默认 `python` 指到了 3.12 以外版本 | 切换到 Python 3.12 后再运行 |
| `node_missing` | Node.js 未找到 | 没安装 Node.js，或 PATH 没指向 `node` | 安装 Node.js 18+ |
| `node_broken` | Node.js 命令损坏 | PATH 里的 Node 安装损坏 | 重装 Node.js 18+ |
| `node_version_unsupported` | Node.js 版本过低 | 当前 Node 主版本低于前端要求 | 升级到 Node.js 18+ |
| `npm_missing` | npm 未找到 | Node 安装不完整或 PATH 缺 npm | 重装 Node.js，并确认 npm 可用 |
| `backend_venv_create_failed` | 后端虚拟环境创建失败 | 项目目录不可写，或被安全软件拦截 | 确认可写、关闭拦截后重试 |
| `backend_venv_validation_failed` | 后端虚拟环境校验失败 | `.venv` 指向错误 Python 或创建不完整 | 删除 `backend/.venv` 后重建 |
| `backend_pip_upgrade_failed` | 后端 pip 升级失败 | 网络访问 PyPI 失败，或环境损坏 | 先确认网络，再重试 |
| `backend_dependency_install_failed` | 后端依赖安装失败 | `requirements.txt` 没装完整 | 检查网络与 Python 版本后重试 |
| `frontend_dependency_install_failed` | 前端依赖安装失败 | `npm install` 失败 | 检查网络 / registry，必要时删 `frontend/node_modules` 后重试 |
| `database_migration_failed` | 数据库迁移失败 | 数据库被占用，或某条迁移执行失败 | 关闭占用 `backend/training.db` 的程序后重试 |
| `backend_port_conflict` | 后端端口冲突 | 8000 端口被其他程序占用 | 关闭占用 8000 的程序 |
| `backend_start_unhealthy` | 后端启动后未就绪 | 后端窗口已打开，但应用初始化报错 | 看后端窗口第一条 traceback |
| `backend_start_failed` | 后端启动失败 | 后端进程没拉起来到健康状态 | 检查依赖、端口和后端窗口报错 |
| `frontend_port_conflict` | 前端端口冲突 | 5173 端口被其他程序占用 | 关闭占用 5173 的程序 |
| `frontend_start_unhealthy` | 前端启动后未就绪 | 前端启动了，但 `runtime-access.json` 没准备好 | 看前端窗口第一条错误 |
| `frontend_start_failed` | 前端启动失败 | 前端进程没拉起到可访问状态 | 检查依赖、端口和前端窗口报错 |

---

## 5. 常见问题怎么修

### 5.0 `.bat` 能启动但 `PATH` 被改坏

当前包装层不再依赖 `PATH` 去找 `powershell.exe`，而是直接使用：

- `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`

这意味着：

1. 如果只是 `PATH` 被改坏，启动器仍然会继续往下跑。
2. 真正缺的是 Python / Node / npm 时，会给出更准确的失败摘要。
3. 只有系统里的 `Windows PowerShell` 本体真的不可用时，才会落到 `powershell_missing`。

### 5.1 PowerShell 未找到

对应错误代码：

- `powershell_missing`

建议动作：

1. 在开始菜单里搜索 `Windows PowerShell`
2. 如果搜不到，先恢复系统自带 PowerShell
3. 如果能打开但 `.bat` 仍提示找不到，检查 `powershell.exe` 是否在 PATH

### 5.2 Python 3.12 未安装

对应错误代码：

- `python_missing`
- `python_version_unsupported`

建议动作：

1. 安装 Python 3.12.x
2. 安装时勾选加入 PATH
3. 安装后重新打开一个新终端再运行启动器

### 5.3 Node / npm 不可用

对应错误代码：

- `node_missing`
- `node_broken`
- `node_version_unsupported`
- `npm_missing`

建议动作：

1. 安装或重装 Node.js 18+
2. 安装完成后重新打开终端
3. 再运行一次 `start_system.bat` 或 `init_system.bat`

### 5.4 后端依赖或虚拟环境异常

对应错误代码：

- `backend_venv_create_failed`
- `backend_venv_validation_failed`
- `backend_pip_upgrade_failed`
- `backend_dependency_install_failed`

建议动作：

1. 先关闭可能占用项目目录的程序
2. 如有必要，手动删除：
   - `backend/.venv`
3. 确认网络正常后重新运行启动器

### 5.5 前端依赖安装失败

对应错误代码：

- `frontend_dependency_install_failed`

建议动作：

1. 确认网络可访问 npm registry
2. 如有必要，手动删除：
   - `frontend/node_modules`
3. 再重新运行启动器

### 5.6 数据库迁移失败

对应错误代码：

- `database_migration_failed`

建议动作：

1. 关闭占用 `backend/training.db` 的程序
2. 再运行启动器
3. 若仍失败，把失败摘要和详细日志一起发给 AI 或维护者

### 5.7 端口冲突

对应错误代码：

- `backend_port_conflict`
- `frontend_port_conflict`

建议动作：

1. 关闭已有的后端 / 前端窗口
2. 关闭其他占用 8000 或 5173 的程序
3. 重新运行启动器

### 5.8 服务窗口已开但不健康

对应错误代码：

- `backend_start_unhealthy`
- `backend_start_failed`
- `frontend_start_unhealthy`
- `frontend_start_failed`

建议动作：

1. 先看新弹出的后端 / 前端窗口
2. 找第一条真正报错，不要只看最后一行
3. 如果自己判断不出来，优先把失败摘要发给 AI
4. 如果 AI 还要上下文，再补 `last-launcher-detail.log`

---

## 6. 人工验收

本步建议至少验这几件事：

1. 故意制造一个失败场景后，能看到 `logs/startup/last-launcher-summary.txt`
2. 摘要足够短，能直接复制给 AI
3. 摘要里包含：
   - 失败步骤
   - 错误类型
   - 最可能原因
   - 建议修复
   - 详细日志路径
4. `logs/startup/last-launcher-detail.log` 与摘要里的失败步骤能对上
5. 用户只看本文件，也能知道常见问题先怎么自查

---

## 7. 当前边界

本步仍然没有做：

- 图形化排障助手
- 自动下载安装 Python / Node
- 自动分析完整 traceback 并生成智能修复方案

第一阶段先做到：

> “失败时先给人和 AI 一段结构化摘要，再保留详细日志兜底。”
