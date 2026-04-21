# 动作库模块说明

## 1. 权威数据源

- 文件：`C:\Users\tzy\Downloads\exos_action_library_tagged_for_codex.xlsx`
- 主数据表：`动作库_标签版`
- 辅助说明表：
  - `标签字段说明`
  - `标签枚举参考`

程序不重新解释 Excel 中的专业分类和标签，只负责按既定字段解析、清洗、导入和展示。

## 2. Excel 字段映射

- `动作ID建议` -> `exercises.code`
- `动作名称` -> `exercises.name`
- `动作英文原名` -> `exercises.name_en`
- `一级分类` -> `exercises.level1_category`
- `二级分类` -> `exercises.level2_category`
- `基础动作` -> `exercises.base_movement`
- `一级分类_EN / 二级分类_EN / 基础动作_EN / 动作英文原名` -> `exercises.original_english_fields`
- 全部 `标签_...` -> `exercises.structured_tags`
- `标签_检索关键词` -> `exercises.search_keywords` 的基础来源
- `标签词条` -> `exercises.tag_text`
- `分类路径` -> `exercises.category_path`
- 原始 Excel 行 -> `exercises.raw_row`

## 3. 标准化动作对象

动作库接口与前端统一使用如下语义：

```json
{
  "id": 0,
  "code": "string",
  "name": "中文动作名",
  "name_en": "英文原名",
  "source_type": "exos_excel | custom_manual",
  "level1_category": "string",
  "level2_category": "string",
  "base_movement": "string",
  "category_path": "string",
  "original_english_fields": {
    "movementTypeCategoryEn": "string",
    "movementTypeEn": "string",
    "baseMovementEn": "string",
    "movementEn": "string"
  },
  "structured_tags": {},
  "search_keywords": [],
  "tag_text": "string",
  "raw_row": {}
}
```

兼容说明：

- `alias` 仍保留在数据库和接口中作为兼容镜像字段
- 新代码统一使用 `name_en` 作为英文原名主字段

## 4. 导入规则

- 主导入服务：`backend/app/services/exercise_library_import.py`
- CLI 入口：`backend/scripts/import_exos_action_library.py`

维护级导入命令：

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\import_exos_action_library.py --preview
.\.venv\Scripts\python.exe scripts\import_exos_action_library.py --apply --replace-existing
```

导入规则：

- 多值标签按 `|` 拆分
- 去掉首尾空格
- 去空项
- 去重
- 首选 `code` 去重
- 如需兼容旧库，可退回 `(中文名, 英文名, 基础动作分类)` 映射
- `replace-existing` 会清理不在当前 Excel 中的旧 `exos_excel` 动作记录，并清理孤立系统分类

## 5. 页面能力

当前动作库页面支持：

- 一级分类筛选
- 二级分类联动
- 关键词搜索
- 结构化标签筛选
- 动作列表浏览
- 动作详情查看
- 网页端新建动作
- 网页端编辑动作
- 网页端删除动作

搜索范围包括：

- 中文动作名
- 英文原名
- `search_keywords`
- `tag_text`

### 导入能力定位

- EXOS Excel 仍是动作库初始化与维护级补录的权威来源
- 网页端已关闭 `导入预览` 和 `导入 Excel` 入口，不再把大规模导入作为常规交互暴露
- 当前导入仅保留为维护级后备能力：
  - 后端导入 API
  - CLI 脚本 `backend/scripts/import_exos_action_library.py`
- 日常维护默认走网页端增删改

## 6. 与训练计划模块的关系

- 模板和计划模块通过统一动作接口获取动作列表
- 训练计划保存动作时，以 `exercise_id` 作为主引用
- 界面展示中可同时使用 `code`、分类摘要和基础动作作为辅助信息
- 后续不允许依赖中文动作名唯一性做匹配
- 删除动作时必须先校验模板项和训练执行项引用；若仍被引用，应拒绝删除并返回明确错误

## 7. 后续扩展建议

当前结构为后续扩展预留了位置，可继续追加：

- 动作图片
- 动作视频
- 动作说明
- 替代动作
- 进阶 / 回归动作
- 训练处方参数
- 禁忌与风险提示
