# **智能文档审计系统 PRD (Aspose 版)**

## **1. 项目背景**

在合规性审查、法务核查及工程管理中，人工逐行对比文档与规则极其耗时且易错。本项目旨在通过 LLM (大语言模型) 自动对 .docx 文档进行拆解，并根据动态生成的审计规则进行逐个文本块检查，最终生成可视化的审计报告。审计规则专注于独立文本块内容的准确性，不考虑跨文本块之间的勾稽关系。

## **2. 核心业务流程**

1. **规则解析阶段**：
   - **输入**：人工输入的自然语言审计准则。
   - **处理**：LLM 解析出结构化规则集 (JSON)，包含：规则 ID、描述、严重级别及推荐分类。
   - **交互**：用户确认/修改解析后的规则。
2. **文档解析阶段 (Aspose.Words)**：
   - **自动编号捕获**：利用 Aspose 渲染引擎提取段落前端的真实编号字符串（如 "1.1", "第一章"）。
   - **文本块拆分**：将文档拆分为“文本块”。以标题（Heading）为界，将标题及其后续段落合并为一个文本块。
   - **表格对象转换**：识别文档中的 Table 对象，将其内容转换为结构化的 JSON 格式，作为一个独立的文本块。
3. **循环审计阶段**：
   - **构建 Prompt**：`[所属标题上下文]` + `[当前文本块内容]` + `[审计规则集]`。
   - **执行**：LLM 逐个文本块返回审计结果（JSON 格式）。
4. **汇总报告阶段**：
   - **统计**：汇总问题总数、分类分布、风险级别。
   - **导出**：生成 HTML 审计报告，支持原文溯源。

## **3. 功能需求详细说明**

### **3.1 规则解析模块**

- **输入**：一段非结构化的文字。
- **默认规则**：错别字、语法错误、指代关系模糊、逻辑推理有误（如事实和结论矛盾）。用户可在此基础上添加特定审计需求。

### **3.2 深度文档解析 (Aspose 技术方案)**

- **编号还原**：必须使用 `doc.update_list_labels()` 预处理，通过 `paragraph.list_label.label_string` 获取“所见即所得”的编号。
- **块拆分逻辑**：
  - 遇到标题（Outline Level < Body Text）时，开启新的文本块。
  - 遇到表格时，独立成块。
- **表格转 JSON**：遍历 Table -> Row -> Cell，生成二维数组或键值对 JSON。

### **3.3 审计执行循环**

- **上下文保持**：在处理段落内容时，需附带该段落所属的最近一个标题编号及内容，作为 LLM 理解背景的依据。
- **清单文件 (Intermediate Manifest)**：格式采用 JSONL，记录每个块的审计状态。

## **4. 技术约束**

- **语言**：Python 3.10+
- **核心库**：`aspose-words` (专业文档解析), `jinja2` (报告模板), `requests/google-generativeai` (LLM 接口)
- **LLM**：推荐 Gemini 1.5 Pro 或 GPT-4o。

## **5. 关键算法实现示例 (Python)**

### **5.1 自动编号与标题追踪提取**

以下算法演示了如何利用 Aspose.Words 遍历文档节点，并根据标题层级拆分文本块。

```
import aspose.words as aw

def extract_audit_blocks(file_path):
    doc = aw.Document(file_path)
    # 必须更新编号标签，否则无法获取渲染后的编号字符串
    doc.update_list_labels()
    
    blocks = []
    current_heading = "前言/未分类"
    current_content = []

    # 获取文档主体中的所有节点
    nodes = doc.sections[0].body.get_child_nodes(aw.NodeType.ANY, False)

    for node in nodes:
        if node.node_type == aw.NodeType.PARAGRAPH:
            para = node.as_paragraph()
            text = para.get_text().strip()
            if not text: continue

            # 获取自动编号 (如 "1.1")
            label = para.list_label.label_string
            full_text = f"{label} {text}" if label else text

            # 判断是否为标题 (大纲级别非正文)
            if para.paragraph_format.outline_level != aw.OutlineLevel.BODY_TEXT:
                # 存入上一个块
                if current_content:
                    blocks.append({"heading": current_heading, "content": "\n".join(current_content), "type": "text"})
                    current_content = []
                current_heading = full_text
            else:
                current_content.append(full_text)

        elif node.node_type == aw.NodeType.TABLE:
            # 遇到表格，先结算之前的文本内容
            if current_content:
                blocks.append({"heading": current_heading, "content": "\n".join(current_content), "type": "text"})
                current_content = []
            
            # 将表格转换为 JSON
            table_data = []
            for row in node.as_table().rows:
                row_data = [cell.get_text().strip().replace('\x07', '') for cell in row.as_row()]
                table_data.append(row_data)
            
            blocks.append({
                "heading": f"表格 (隶属: {current_heading})",
                "content": table_data,
                "type": "table"
            })

    # 结算最后一个块
    if current_content:
        blocks.append({"heading": current_heading, "content": "\n".join(current_content), "type": "text"})
    
    return blocks
```

### **5.2 审计清单数据结构**

清单文件 (Manifest) 的单条记录示例如下：

```
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "p_heading": "2.1 违约金条款",
  "p_content": "如乙方逾期支付，应支付大概总金额 1% 的赔偿。",
  "is_violation": true,
  "issue_type": "语义风险",
  "violation_reason": "包含模糊词汇'大概'，且未明确赔偿金的币种，违反规则 R002。",
  "suggestion": "建议修改为：'应支付合同总金额 1% 的违约金（以人民币结算）。'"
}
```

## **6. 验收标准**

1. **编号准确性**：所有标题编号必须与 Word 文档中显示的一致（含多级列表）。
2. **表格完整性**：表格数据不能丢失行列关系，JSON 格式需能被 LLM 正确解析。
3. **独立性**：审计过程需证明每个块是独立提交给 LLM 的，无跨块干扰。

