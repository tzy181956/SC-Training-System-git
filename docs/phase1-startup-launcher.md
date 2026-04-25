# 第一阶段重构补充｜一步步检查、初始化、启动

## 1. 这一步只解决什么

本文件只记录第一阶段中的“一键初始化 + 一键启动”重构，目标是：

1. 非程序员点击一个脚本后，系统能按步骤检查环境并尽量跑起来。
2. 出错时不再只是黑盒报错，而是明确：
   - 哪一步失败
   - 可能原因
   - 建议修复方式
   - 可复制的错误摘要

本步不展开：

- 图形化运维面板
- 远程部署
- 业务逻辑改造

---

## 2. 当前启动器到底是哪个文件

当前真正的主启动器是：

- `scripts/system_launcher.ps1`

两个 `.bat` 文件只是 Windows 入口包装：

- `scripts/start_system.bat`
  - 调用 `system_launcher.ps1 -Mode start`
- `scripts/init_system.bat`
  - 调用 `system_launcher.ps1 -Mode init`

包装层当前直接走系统绝对路径：

- `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`

这样做的目的，是避免仅仅因为 `PATH` 被改坏，就在入口层误报“找不到 powershell”。

也就是说：

- 你平时双击运行的通常是 `.bat`
- 真正执行分步检查、初始化和启动逻辑的是 `PowerShell` 脚本

---

## 3. 启动流程

当前启动器按“先检查、再初始化、再启动”的顺序执行。

### 3.1 `init` 模式

用于首次初始化或补环境，重点做：

1. 检查 PowerShell
2. 检查 Python / Node
3. 检查并准备后端虚拟环境
4. 检查并补齐前端声明依赖
5. 检查数据库并执行迁移

这里的“前端声明依赖”指 `frontend/package.json` 中声明的直接依赖和 devDependencies。  
当前启动器不再只探测少数几个包，而是统一校验整份前端依赖声明；只要：

- `frontend/node_modules` 缺失
- 或声明包里有任意一个未安装

就会自动执行一次 `npm install`，避免把“缺正式依赖”的问题拖到浏览器里才由 Vite 报错。

### 3.2 `start` 模式

用于正常启动，重点做：

1. 检查环境
2. 检查并补齐前端声明依赖
3. 检查数据库 / 迁移状态
4. 启动后端
5. 启动前端
6. 生成推荐访问地址

---

## 4. 错误分类与输出方式

本步要求失败时必须“说人话”，当前实现收口为：

1. 启动器按步骤输出当前进度
2. 某一步失败时，立即生成可复制失败摘要
3. 总结文件包含：
   - 模式（`start / init`）
   - 失败步骤
   - 错误类型
   - 最可能原因
   - 建议修复方式
   - 详细日志路径
   - 对应排障文档路径
   - 最近日志摘录

总结文件位置：

- `logs/startup/last-launcher-summary.txt`
- `logs/startup/launcher-summary-YYYYMMDD-HHMMSS.txt`

详细日志位置：

- `logs/startup/last-launcher-detail.log`
- `logs/startup/launcher-detail-YYYYMMDD-HHMMSS.log`

排障文档位置：

- `docs/phase1-launcher-failure-summary.md`

也就是说：

- 先把 `last-launcher-summary.txt` 发给 AI
- 如果还需要更多上下文，再补 `last-launcher-detail.log`

当前与前端依赖相关的失败至少会明确到两类：

- `frontend_dependency_install_failed`
  - `npm install` 本身执行失败
- `frontend_dependency_validation_failed`
  - 安装后再次校验时，`package.json` 声明的包仍不完整

---

## 5. 运行时地址输出

启动器的访问地址输出遵循“当前实际前端运行地址优先”原则：

- 本地健康检查地址：后端 `http://127.0.0.1:8000/health`
- 前端推荐地址基于 `runtime-access.json`
- 对外推荐地址会优先写入：
  - `frontend/public/runtime-access.json`

这样做的目的，是把网页里显示的推荐访问地址和启动器输出尽量对齐。

---

## 6. 与迁移和备份的关系

启动器不是单独存在的，它与以下能力联动：

1. 数据库迁移
   - 通过 `backend/scripts/migrate_db.py`
2. 迁移前备份
   - 由备份服务在迁移前执行
3. 启动摘要
   - 统一写入 `logs/startup/`

所以第一阶段里，启动器是“工程可用性收口点”，不是简单的两个启动命令拼接。

---

## 7. 关键文件

本步主要文件如下：

- `scripts/system_launcher.ps1`
- `scripts/start_system.bat`
- `scripts/init_system.bat`
- `backend/scripts/migrate_db.py`
- `backend/app/services/backup_service.py`
- `frontend/public/runtime-access.json`

---

## 8. 人工验收

1. 在一台未完全准备好的机器上运行 `start_system.bat` 或 `init_system.bat`。
2. 确认启动器会按步骤输出，而不是直接报一屏黑字异常。
3. 如果缺少 Python 或 Node，大环境不会被自动偷偷安装，但会给出明确提示。
4. 若小依赖缺失，确认会尝试自动安装或给出明确修复建议。
5. 制造一次失败场景，确认 `logs/startup/last-launcher-summary.txt` 被写出，且内容可直接复制。

---

## 9. 技术自测

本步最小技术自测应覆盖：

1. `start` 与 `init` 两种模式都能重复执行。
2. PowerShell 包装入口能正确转发到 `system_launcher.ps1`。
3. 失败时会写启动摘要文件。
4. 成功启动后能给出可访问地址。

---

## 10. 当前边界

本步仍未解决：

- GUI 启动向导
- 自动下载安装 Python / Node 大环境
- 远程机器诊断与自动修复

第一阶段先做到“能一步步检查、失败能定位”，不把启动器做成复杂运维系统。
