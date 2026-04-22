# 中文乱码与文本编码说明

## 这份文档解决什么问题

本仓库曾同时出现两类中文异常：

1. **文件内容真的已经损坏**
   - 典型表现：出现明显不符合正常中文语义的错误转码片段
   - 原因通常是 UTF-8 文本被按 GBK/ANSI 打开后又重新保存
2. **终端显示乱码**
   - 文件本身是正常 UTF-8
   - 但 PowerShell / cmd 输出编码不稳定，看起来像乱码

这两类问题必须分开判断。

## 正确判断方式

不要只靠终端输出判断文件是否损坏。优先使用：

- 编辑器直接打开文件
- Python UTF-8 读取

示例：

```python
from pathlib import Path
print(Path("README.md").read_text(encoding="utf-8"))
```

## 仓库统一规则

- 文本文件统一使用 UTF-8
- 不要把终端里看到的乱码文本直接复制回源码或文档
- 不要用不确定编码的重定向输出覆盖仓库文件

仓库级规范文件：

- `.editorconfig`
- `.gitattributes`

## 检查脚本

项目提供了乱码扫描脚本：

```powershell
python scripts/check_text_encoding.py
```

它会检查：

- UTF-8 解码失败
- replacement character（`U+FFFD`）
- Private Use 区字符
- 常见 mojibake 片段

## 推荐使用场景

在以下场景执行检查：

- 修复文档后
- 修改大量中文文案后
- 导入/生成文本文件后
- 提交前

## 当前已知高风险文件

如果这些文件再次出现异常，应优先检查：

- `README.md`
- `PROJECT_CONTEXT.md`
- `DEVELOPMENT_GUIDE.md`
- `CODEX_HANDOFF.md`
- `CURRENT_STATUS.md`
- `NEXT_STEPS.md`
- `backend/README.md`
- `backend/scripts/import_real_test_data.py`

## 修复原则

- 不做全仓自动反转码
- 优先按文件、按语义、按可信历史版本恢复
- 对高风险脚本（如 Excel 导入脚本），必须对照真实业务字段名核对

## 当前经验结论

- PowerShell 输出可能误导判断，但不等于文件已经损坏
- 真正的内容级乱码通常来自错误解码后再次保存
- 只要统一 UTF-8 规范并在提交前跑一次扫描，后续大多数问题都能提前发现
