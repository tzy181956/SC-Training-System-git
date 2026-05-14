# 第一阶段已落地文档索引

> 文档状态：历史阶段索引  
> 当前用途：用于追溯 phase1 文档来源。  
> 当前系统阅读入口请优先使用 `README.md` 中的阅读顺序，而不是本阶段索引。

## 1. 这份索引解决什么

这份索引只做一件事：

- 把当前仓库里**已经有记录**和**这次补齐的记录**放到同一张清单里，避免后续再靠聊天记录追溯。

说明：

- 一部分前期工作先以“边界 / 设计文档”落地，不一定天然带有步骤编号。
- 从 Step 08 开始，步骤边界已经相对明确。
- 本索引的目标不是重写所有内容，而是给出**步骤 → 文档**的稳定映射。
- Step 08 之前已经做过的内容，本次也重新核查过仓库内是否有落地记录；没有强行伪造编号映射，而是统一纳入“前置与跨步文档”作为正式追溯入口。

---

## 2. 前置与跨步文档

这些文档不是单一步骤交付，但属于第一阶段的基础记录：

| 类型 | 文档 | 说明 |
| --- | --- | --- |
| 术语与边界 | `docs/phase1-terminology-and-boundaries.md` | 统一 `template / assignment / session / local draft / sync status` 语义 |
| 本地草稿与 Session 关系 | `docs/phase1-local-draft-and-session.md` | 收口本地草稿与正式训练课的边界 |
| 训练课状态流 | `docs/phase1-session-status-flow.md` | 收口第一阶段状态枚举和进入规则 |
| 数据库迁移总览 | `docs/phase1-database-migrations.md` | 记录 Alembic 基线、迁移策略和已落地 revisions |

这部分同时承担了 **Step 08 之前已完成工作的仓库内记录**。  
原因是这些较早的重构动作当时按“边界 / 状态 / 数据流”收口，没有逐条以 Step 编号落文档。  
本次已经重新检查，相关内容都能从上面几份基础文档追溯，不再额外补一堆会制造伪精确映射的编号文档。

---

## 3. 步骤化文档映射

| 步骤 | 主题 | 文档 | 状态 |
| --- | --- | --- | --- |
| Step 08 | 整堂课覆盖同步兜底 | `docs/phase1-full-session-sync-fallback.md` | 本次补齐 |
| Step 09 | 同步状态灯与异常待处理闭环 | `docs/phase1-sync-status-and-manual-retry.md` | 已存在 |
| Step 10 | 恢复提示与继续录课 | `docs/phase1-draft-restore-flow.md` | 已存在 |
| Step 11 | 课后修改、补录、自动重算状态 | `docs/phase1-post-class-correction.md` | 本次补齐 |
| Step 12 | 启动器一步步检查、初始化、启动 | `docs/phase1-startup-launcher.md` | 本次补齐 |
| Step 13 | 迁移前备份、危险操作前备份、定时备份 | `docs/phase1-backup-policy.md` | 已存在 |
| Step 14 | 危险操作二次确认与影响范围说明 | `docs/phase1-dangerous-operation-guardrails.md` | 已存在 |
| Step 15 | 日志页基础版 | `docs/phase1-log-page.md` | 本次补齐 |
| Step 16 | 备份恢复页基础版 | `docs/phase1-restore-page.md` | 本次新增 |
| Step 17 | 启动器失败摘要与排障文档联动 | `docs/phase1-launcher-failure-summary.md` | 本次新增 |
| Step 18 | 第一阶段总验收脚本与人工测试清单 | `docs/phase1-final-acceptance.md` | 本次新增 |

---

## 4. 非 Phase 1 主题但已在仓库中的相关文档

以下文档与当前阶段并行存在，但不属于本轮 Phase 1 稳定性重构主线：

| 文档 | 说明 |
| --- | --- |
| `docs/exercise-library-facets.md` | 动作库模块筛选面板的数据来源说明 |
| `docs/text-encoding.md` | 中文乱码与编码问题说明 |

---

## 5. 当前结论

截至当前，这一轮仓库内文档状态已经调整为：

1. Step 08、11、12、15 的缺口已补齐。
2. Step 16、17、18 已新增独立步骤文档。
3. Step 09、10、13、14 的已有文档保留继续使用。
4. Step 08 之前已完成的内容，已确认可由前置边界、状态流、迁移总览等基础文档追溯。
5. 前置边界、状态流、迁移总览文档继续作为跨步骤基础文档。

后续如果再推进新的第一阶段步骤，建议遵守同一规则：

- 代码落地时同步补一份步骤文档
- 涉及 schema 的，再同步更新 `docs/phase1-database-migrations.md`
- 最后回填这份索引

---

## 6. 阶段收尾修复补充记录

- 跨日未收口训练课的主触发点已从“进入训练流程时顺手收口”升级为“后端每次启动成功前先执行一次”。
- 启动后的兜底收口由显式维护接口和非 GET 训练入口承担；训练端 / 监控端 GET 保持只读，不再隐式写库。
- 本次未新增定时任务，也未改动前端、本地草稿、同步、模板、测试、权限、备份恢复或数据库结构。
