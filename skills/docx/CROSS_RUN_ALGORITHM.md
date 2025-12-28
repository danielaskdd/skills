# 跨 Run 字符串匹配算法设计文档

## 问题背景

### 当前 `apply_edits.py` v2.0 的局限性

**核心限制**：假设目标字符串完全包含在单个 `<w:r>` 节点内。

```python
# v2.0 代码 (apply_edits.py:203-210)
node = self.doc["word/document.xml"].get_node(tag='w:r', contains=find_text)
```

**问题场景**：
```xml
<!-- 逻辑文本: "This is important text" -->
<!-- 物理存储: 分布在 3 个 Run 中 -->
<w:p>
  <w:r><w:t>This is </w:t></w:r>
  <w:r><w:rPr><w:b/></w:rPr><w:t>important</w:t></w:r>
  <w:r><w:t> text</w:t></w:r>
</w:p>
```

如果要替换 "important text"，v2.0 算法会失败，因为没有单个 `<w:r>` 包含完整字符串。

---

## 解决方案：混合架构

### 架构图

```
┌──────────────────────────────────────────────────────┐
│ python-docx                                          │
│ ─────────────────────────────────────────────────    │
│ • 段落级分析 (para.text)                              │
│ • Run 遍历 (para.runs)                                │
│ • 字符偏移映射                                         │
└──────────────────┬───────────────────────────────────┘
                   │ 输出: 逻辑匹配 → 物理 Run 编辑列表
                   ▼
┌──────────────────────────────────────────────────────┐
│ Document 库 (scripts/document.py)                    │
│ ─────────────────────────────────────────────────    │
│ • DOM 节点操作                                         │
│ • 修订标记生成 (<w:ins>, <w:del>)                     │
│ • XML 重构和保存                                       │
└──────────────────────────────────────────────────────┘
```

### 为什么不能只用 python-docx？

**关键限制**：python-docx **无法创建修订标记**（tracked changes）。

参考 [PYTHON_DOCX_GUIDE.md](PYTHON_DOCX_GUIDE.md):
> ❌ Create tracked changes (insertions/deletions)
> **For these tasks, use: Tracked changes: YAML workflow with Document library**

### 为什么不能只用 Document 库？

**Document 库的问题**：
- ✅ 支持修订标记（`<w:ins>`, `<w:del>`）
- ✅ 支持 DOM 操作
- ❌ **缺少高级段落分析 API**：无法直接获取段落的合并文本
- ❌ 需要手动处理 Unicode 编码（`&#数字;`）和 XML 转义

---

## 核心算法：逻辑映射法

### 阶段 1: 段落级分析（python-docx）

```python
from docx import Document

doc = Document('file.docx')
para = doc.paragraphs[2]  # 获取第 3 个段落

# 自动获取合并后的文本（所有 Run 合并）
full_text = para.text  # "This is important text"

# 查找目标字符串
target = "important text"
match_start = full_text.find(target)  # 返回: 8
match_end = match_start + len(target)  # 返回: 22
```

**优势**：
- 自动处理 XML 编码（Unicode）
- 自动合并所有 Run 的文本
- 避免 XML 标签干扰

---

### 阶段 2: Run 偏移映射

```python
class RunMapper:
    def __init__(self, paragraph_text, runs_info):
        self.paragraph_text = paragraph_text
        self.run_offsets = self._calculate_offsets(runs_info)

    def _calculate_offsets(self, runs_info):
        """
        构建偏移表:
        [
            {'idx': 0, 'start': 0, 'end': 8, 'text': 'This is '},
            {'idx': 1, 'start': 8, 'end': 17, 'text': 'important'},
            {'idx': 2, 'start': 17, 'end': 22, 'text': ' text'},
        ]
        """
        offsets = []
        position = 0
        for idx, info in enumerate(runs_info):
            text = info['text']
            offsets.append({
                'idx': idx,
                'start': position,
                'end': position + len(text),
                'text': text
            })
            position += len(text)
        return offsets
```

**关键洞察**：
- 逻辑视图：段落是一个连续的字符串
- 物理视图：段落由多个独立的 Run 组成
- 映射关系：每个 Run 对应一个字符范围 `[start, end)`

---

### 阶段 3: 匹配区间到 Run 列表

```python
def map_to_runs(self, match_start, match_end, delete_text, insert_text):
    """
    输入:
        match_start = 8, match_end = 22
        delete_text = "important text"
        insert_text = "critical info"

    输出:
        [
            {
                'run_idx': 1,
                'before': '',           # Run 开头无不变部分
                'delete': 'important',  # 删除 Run 1 的全部文本
                'insert': 'critical info',  # 新文本插入到第一个 Run
                'after': '',
                'is_first': True
            },
            {
                'run_idx': 2,
                'before': '',
                'delete': ' text',      # 删除 Run 2 的全部文本
                'insert': '',           # 后续 Run 不插入
                'after': '',
                'is_first': False
            }
        ]
    """
    edits = []
    is_first = True

    for offset in self.run_offsets:
        # 计算重叠区间
        overlap_start = max(offset['start'], match_start)
        overlap_end = min(offset['end'], match_end)

        if overlap_start >= overlap_end:
            continue  # 此 Run 不受影响

        # 局部偏移（相对于 Run 起始位置）
        local_start = overlap_start - offset['start']
        local_end = overlap_end - offset['start']

        # 拆分 Run 文本
        before = offset['text'][:local_start]
        delete = offset['text'][local_start:local_end]
        after = offset['text'][local_end:]

        # 只有第一个 Run 插入新文本
        insert = insert_text if is_first else ''

        edits.append({
            'run_idx': offset['idx'],
            'before': before,
            'delete': delete,
            'insert': insert,
            'after': after,
            'is_first': is_first
        })

        is_first = False

    return edits
```

**示例计算过程**：

| Run | 原文本 | start | end | 重叠范围 | 局部删除 | 插入 |
|-----|--------|-------|-----|----------|----------|------|
| 1   | "important" | 8 | 17 | [8, 17) | "important" | "critical info" |
| 2   | " text" | 17 | 22 | [17, 22) | " text" | "" |

---

### 阶段 4: 生成修订标记 XML

```python
def build_cross_run_replacement(edits, dom_runs):
    """
    为每个受影响的 Run 生成修订标记

    输入:
        edits = [
            {'run_idx': 1, 'delete': 'important', 'insert': 'critical info', ...},
            {'run_idx': 2, 'delete': ' text', 'insert': '', ...}
        ]
        dom_runs = [<w:r>节点1, <w:r>节点2]

    输出:
        '<w:del><w:r><w:rPr>...</w:rPr><w:delText>important</w:delText></w:r></w:del>
         <w:ins><w:r><w:rPr>...</w:rPr><w:t>critical info</w:t></w:r></w:ins>
         <w:del><w:r><w:rPr>...</w:rPr><w:delText> text</w:delText></w:r></w:del>'
    """
    parts = []

    for edit, dom_run in zip(edits, dom_runs):
        # 提取原始格式
        rpr = rpr_xml(dom_run)  # <w:rPr>...</w:rPr>
        rsid = dom_run.getAttribute("w:rsidR")

        # 前面不变的部分
        if edit['before']:
            parts.append(f'<w:r w:rsidR="{rsid}">{rpr}{t_tag(edit["before"])}</w:r>')

        # 删除标记
        if edit['delete']:
            if edit['is_first']:
                # 第一个 Run：删除 + 插入（保留格式）
                parts.append(f'<w:del><w:r>{rpr}{del_text_tag(edit["delete"])}</w:r></w:del>')
                if edit['insert']:
                    parts.append(f'<w:ins><w:r>{rpr}{t_tag(edit["insert"])}</w:r></w:ins>')
            else:
                # 后续 Run：仅删除
                parts.append(f'<w:del><w:r>{rpr}{del_text_tag(edit["delete"])}</w:r></w:del>')

        # 后面不变的部分
        if edit['after']:
            parts.append(f'<w:r w:rsidR="{rsid}">{rpr}{t_tag(edit["after"])}</w:r>')

    return "".join(parts)
```

**格式继承规则**：
- 插入的文本使用**第一个被删除 Run 的格式**（`<w:rPr>`）
- 这确保了替换文本保持原始文本的第一个字符的格式
- 符合 Word 的修订行为预期

---

## 使用示例

### YAML 配置

```yaml
version: "1.0"
document:
  input: "report.docx"
  output: "report_edited.docx"

revision:
  author: "Claude AI"
  track_changes: true

edits:
  - type: replace_partial_cross_run
    description: "修正跨格式的拼写错误"
    find_text: "This is important information"
    paragraph_index: 2  # 可选：指定段落索引
    changes:
      - delete: "important"
        insert: "critical"
```

### 执行

```bash
# 前提：已经使用 workflow.sh 解包文档
python skills/docx/scripts/apply_edits_v3_cross_run.py \
    .claude-work/edits/corrections.yaml \
    .claude-work
```

### 输出

```
============================================================
Word 文档编辑工具 v3.0 - 跨 Run 字符串匹配版本
============================================================

✓ 文档已加载: report.docx
✓ 作者: Claude AI
✓ 修订模式: 启用

开始应用 1 个编辑操作...

[1] 修正跨格式的拼写错误
    类型: replace_partial_cross_run
    定位到段落: #2
    段落文本: This is important information that we need to consider...
    删除: 'important'
    插入: 'critical'
    影响 1 个 Run
    ✓ 完成

正在保存文档...
✓ 文档已保存

============================================================
✓ 所有操作已完成
============================================================
```

---

## 技术细节

### 1. 为什么使用 python-docx 分析而不是直接解析 XML？

**对比**：

| 方法 | 优势 | 劣势 |
|------|------|------|
| 直接解析 XML | 完全控制 | 需手动处理 Unicode 编码（`&#20013;`）、空格保留、嵌套结构 |
| python-docx | 自动处理编码、自动合并文本 | 无法生成修订标记 |

**最佳实践**：分析用 python-docx，编辑用 Document 库。

### 2. 为什么插入文本放在第一个 Run？

**Word 修订行为**：
- 当删除 "**important** text" 并插入 "critical info" 时
- Word 会将 "critical info" 放在删除起始位置
- 格式继承自第一个被删除的字符

**实现**：
```python
if edit['is_first']:
    parts.append(f'<w:del>...</w:del>')
    parts.append(f'<w:ins>{rpr}{t_tag(insert_text)}</w:ins>')
```

### 3. 如何处理连续多次替换？

**问题**：同一段落需要多次替换时，第一次替换改变了文本，第二次匹配会失败。

**解决方案（简化版）**：
```python
# 第一次替换后更新逻辑文本
updated_text = para_text[:match_start] + insert_text + para_text[match_end:]
mapper.paragraph_text = updated_text
```

**生产版本**：重新加载 python-docx 文档以获取最新状态。

---

## 测试场景

### 场景 1: 跨粗体和普通格式

**原文**：
```
This is important text.
        ^^^^^^^^^^^^^^^
        (粗体)  (普通)
```

**YAML**：
```yaml
- delete: "important text"
  insert: "critical info"
```

**结果**：
```xml
<w:del><w:r><w:b/><w:delText>important</w:delText></w:r></w:del>
<w:ins><w:r><w:b/><w:t>critical info</w:t></w:r></w:ins>
<w:del><w:r><w:delText> text</w:delText></w:r></w:del>
```

**Word 显示**：
```
This is ~~important~~ ~~text~~ critical info.
```
（删除线部分为删除标记，下划线部分为插入标记）

### 场景 2: 跨三个 Run

**原文**：
```
<Run1>Hello </Run1><Run2 bold>world</Run2><Run3>!</Run3>
```

**删除**：`"world!"`
**插入**：`"everyone"`

**结果**：
```xml
<w:r>Hello </w:r>
<w:del><w:r><w:b/><w:delText>world</w:delText></w:r></w:del>
<w:ins><w:r><w:b/><w:t>everyone</w:t></w:r></w:ins>
<w:del><w:r><w:delText>!</w:delText></w:r></w:del>
```

**Word 显示**：
```
Hello ~~world~~ ~~!~~ **everyone**
```
（注意 "everyone" 继承了 "world" 的粗体格式）

---

## 与 v2.0 的对比

| 特性 | v2.0 (apply_edits.py) | v3.0 (apply_edits_v3_cross_run.py) |
|------|----------------------|-----------------------------------|
| 单 Run 替换 | ✅ | ✅ |
| 跨 Run 替换 | ❌ | ✅ |
| XML 标签干扰 | 🔶 需要手动处理 | ✅ 自动避免 |
| Unicode 支持 | ✅ | ✅ |
| 修订标记 | ✅ | ✅ |
| 格式继承 | ✅ 保留原始格式 | ✅ 继承第一个字符格式 |
| 段落定位 | 基于 `contains` + `line_range` | 基于段落索引（更精确） |
| 依赖 | Document 库 | Document 库 + python-docx |

---

## 限制和注意事项

### 当前限制

1. **段落索引假设**：假设 python-docx 和 Document 库的段落顺序一致
   - 通常成立，但特殊情况需验证（如表格中的段落）

2. **连续替换**：同一段落多次替换需要重新加载文档
   - 当前版本使用简化的文本更新
   - 生产环境建议每次替换后重新初始化 python-docx

3. **表格支持**：未测试表格内跨 Run 替换
   - python-docx 的 `table.cell.paragraphs` 可能与 DOM 节点顺序不同

### 未来改进

1. **自动段落定位**：
   ```python
   # 基于段落内容的哈希值匹配 DOM 节点
   para_hash = hashlib.md5(para.text.encode()).hexdigest()
   ```

2. **增量更新**：
   ```python
   # 每次替换后只更新受影响的 Run 映射
   mapper.update_run(run_idx, new_text)
   ```

3. **表格支持**：
   ```python
   # 专门的表格单元格匹配逻辑
   cell_para = table.rows[r].cells[c].paragraphs[p]
   ```

---

## 总结

### 核心创新

1. **混合架构**：分析用 python-docx，编辑用 Document 库
2. **逻辑映射法**：段落文本（逻辑）→ Run 列表（物理）
3. **格式继承**：插入文本保留第一个被删除字符的格式

### 适用场景

✅ **推荐使用 v3.0**：
- 文本可能跨越多个格式（粗体、斜体、字体变化）
- 替换包含特殊格式的文本
- 需要精确的段落级匹配

✅ **继续使用 v2.0**：
- 确定文本在单个 Run 内
- 性能敏感场景（v3.0 需要加载两个库）
- 简单的拼写修正

---

## 参考资料

- [PYTHON_DOCX_GUIDE.md](PYTHON_DOCX_GUIDE.md) - python-docx 使用指南
- [apply_edits.py](scripts/apply_edits.py) - v2.0 实现
- [Document 库文档](scripts/document.py) - 修订标记 API
- [OOXML 规范](ooxml/OOXML_REFERENCE.md) - Word XML 格式参考
