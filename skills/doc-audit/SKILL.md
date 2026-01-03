---
name: doc-audit
description: Intelligent document audit system for compliance review, legal or technical document verification, and engineering document validation using LLM
type: active
version: 1.0.0
---

# Document Audit Skill

**This is an ACTIVE skill** - Uses Python scripts with Aspose.Words to parse DOCX documents and LLM to perform intelligent auditing.

## When to Use This Skill

Use this skill when you need to:
- Audit Word documents (.docx) for compliance with specific rules
- Verify legal or technical documents for language accuracy and consistency
- Review engineering specifications for technical correctness
- Check documents for typos, grammar errors, unclear references, and logical inconsistencies
- Generate detailed audit reports with issue tracing

## Core Workflow

```
1. Parse Rules     → Convert natural language audit criteria to structured rules
2. Parse Document  → Extract text blocks from .docx with proper numbering (Aspose)
3. Execute Audit   → LLM audits each text block against rules independently
4. Generate Report → Create HTML report with findings and source tracing
```

## Available Tools

### 1. Parse Audit Rules

Convert natural language audit criteria into structured JSON rules:

```bash
python scripts/parse_rules.py --input "your audit criteria text"
python scripts/parse_rules.py --file rules.txt
```

**Default Rules Include:**
- Typos and spelling errors
- Grammar errors
- Unclear references (ambiguous pronouns, vague terms)
- Logical inconsistencies (contradictions between facts and conclusions)

**Returns:** JSON with rule ID, description, severity level, and category

### 2. Parse Document

Extract text blocks from a Word document using Aspose.Words:

```bash
python scripts/parse_document.py document.docx
python scripts/parse_document.py document.docx --output blocks.jsonl
```

**Features:**
- Captures automatic numbering (e.g., "1.1", "Chapter 1")
- Splits by headings - each heading starts a new block
- Tables converted to structured JSON as independent blocks
- Preserves heading context for each block

**Returns:** JSONL file with text blocks

### 3. Run Audit

Execute LLM audit on each text block:

```bash
python scripts/run_audit.py --document blocks.jsonl --rules rules.json
python scripts/run_audit.py --document blocks.jsonl --rules rules.json --model gemini-3-flash
```

**Process:**
- Constructs prompt: [Parent Heading Context] + [Current Block] + [Rules]
- Submits each block independently to LLM
- Saves intermediate results to manifest.jsonl
- Supports resume from interruption
- Accepts JSON/JSONL blocks only (use `parse_document.py` first)

**Returns:** Audit manifest (JSONL) with findings

### 4. Generate Report

Create HTML audit report from audit manifest:

```bash
python scripts/generate_report.py manifest.jsonl --output report.html
python scripts/generate_report.py manifest.jsonl --output report.html --template custom_template.html
```

**Features:**
- Total issue count and distribution by category/severity
- Issue details with original text reference
- Suggested corrections
- Source tracing (heading + block content)
- HTML is escaped by default; use `--trusted-html` only if inputs are trusted

## Quick Start Example

```bash
# 1. Parse your audit rules (or use defaults)
python scripts/parse_rules.py --input "Check for: unclear amounts, missing currency specifications, vague timelines"

# 2. Parse the document
python scripts/parse_document.py contract.docx --output contract_blocks.jsonl

# 3. Run the audit
python scripts/run_audit.py --document contract_blocks.jsonl --rules rules.json

# 4. Generate the report
python scripts/generate_report.py manifest.jsonl --output audit_report.html
```

## Technical Requirements

### Dependencies

```bash
pip install aspose-words jinja2 google-generativeai openai
```

**Core Libraries:**
- `aspose-words`: Professional DOCX parsing with list label extraction
- `jinja2`: HTML report templating
- `google-generativeai` / `openai`: LLM API access

**Recommended LLM:** Gemini-3-Flash or GPT-5.2

### Preflight Dependency Check (Required)

Before running any script, the agent must verify the runtime prerequisites. If any required dependency is missing, stop and tell the user exactly how to install it and which environment variables to set.

- `parse_document.py` requires `aspose-words`
- `generate_report.py` uses `jinja2` (optional; falls back to a minimal template if missing)
- `run_audit.py` requires at least one LLM client:
  - Gemini: `google-generativeai` + `GOOGLE_API_KEY`
  - OpenAI: `openai` + `OPENAI_API_KEY`

**Failure handling:** If a required package or API key is missing, do not proceed with the workflow. Provide the exact `pip install ...` command(s) and the `export ...` command(s) needed to prepare the environment.

### Environment Variables

```bash
# For Gemini
export GOOGLE_API_KEY=your_api_key

# For OpenAI
export OPENAI_API_KEY=your_api_key
```

## Data Structures

### Audit Rule Format

```json
{
  "id": "R001",
  "description": "Check for vague or ambiguous monetary amounts",
  "severity": "high",
  "category": "semantic_risk",
  "keywords": ["approximately", "about", "around", "roughly"]
}
```

### Text Block Format

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "heading": "2.1 Penalty Clause",
  "content": "If Party B delays payment, they shall pay approximately 1% of the total amount as compensation.",
  "type": "text",
  "parent_headings": ["Chapter 2 Contract Terms", "2.1 Penalty Clause"]
}
```

### Audit Result Format

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "p_heading": "2.1 Penalty Clause",
  "p_content": "If Party B delays payment, they shall pay approximately 1% of the total amount as compensation.",
  "is_violation": true,
  "issue_type": "semantic_risk",
  "rule_id": "R002",
  "violation_reason": "Contains vague term 'approximately' and does not specify currency, violating rule R002.",
  "suggestion": "Revise to: 'shall pay 1% of the contract total amount as penalty (settled in CNY).'"
}
```

## Acceptance Criteria

1. **Numbering Accuracy**: All heading numbers must match the Word document display (including multi-level lists)
2. **Table Integrity**: Tables must preserve row/column relationships in JSON format
3. **Block Independence**: Each block is audited independently without cross-block interference
4. **Traceability**: Every issue can be traced back to its source heading and content

## Best Practices

### Writing Effective Audit Rules

1. **Be Specific**: "Check for amounts without currency specification" is better than "Check for vague amounts"
2. **Include Examples**: Provide examples of violations and corrections
3. **Set Appropriate Severity**: Use high/medium/low consistently
4. **Categorize Properly**: Group related rules (grammar, logic, compliance, etc.)

### Handling Large Documents

- Documents are processed block-by-block
- Progress is saved to manifest.jsonl for resume capability (`--resume`)
- Use `--rate-limit` to control API pacing, and `--start-block` / `--end-block` to chunk runs

### Customizing Reports

- Modify `assets/report_template.html` for custom styling
- Add company branding, custom sections, or additional statistics
- Export manifest.jsonl for integration with other systems

## File Structure

```
doc-audit/
├── SKILL.md                    # This file
├── scripts/
│   ├── parse_rules.py          # Rule parsing
│   ├── parse_document.py       # DOCX parsing (Aspose)
│   ├── run_audit.py            # LLM audit execution
│   └── generate_report.py      # Report generation
├── assets/
│   ├── default_rules.json      # Default audit rules
│   └── report_template.html    # Jinja2 report template
└── references/
    └── algorithm_examples.md   # Implementation reference
```

## Limitations

- Only supports .docx format (not .doc, .pdf, or other formats)
- Each text block is audited independently - no cross-reference validation
- Requires Aspose.Words license for production use (evaluation watermark in trial)
- LLM quality depends on chosen model and rule clarity

## Troubleshooting

**Numbering Not Captured:**
- Ensure `doc.update_list_labels()` is called before extraction
- Check if document uses automatic numbering vs. manual numbering

**Table Parsing Issues:**
- Verify table uses standard Word table format (not text boxes or images)
- Check for merged cells which may affect structure

**LLM Rate Limiting:**
- Adjust `--rate-limit` parameter (default: 0.5 seconds between requests)
- Use batch mode for large documents

**Memory Issues with Large Documents:**
- Process in chunks using `--start-block` and `--end-block` parameters
- Save checkpoints frequently with `--checkpoint-interval`

## Related Resources

- [Aspose.Words Documentation](https://reference.aspose.com/words/python-net/)
- [llms.txt Convention](https://llmstxt.org/)
- Original PRD: prd-doc-audit.md
