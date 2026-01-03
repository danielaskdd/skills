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

The doc-audit skill supports two workflow paths depending on whether user has specific audit requirements:

### Phase 1: Rule Selection (Optional)

**Decision Point:** Does user specify custom audit requirements?

**Path A: Use Default Rules (Simple)**
- User only requests "audit [filename]" without specific requirements
- **Skip rule generation** - use `assets/default_rules.json` directly
- Proceed immediately to Phase 2

**Path B: Custom Rules (Iterative)**
1. **Analyze Requirements** - Agent converts user's needs into clear criteria
2. **Generate Rules** - Call `parse_rules.py` to merge base rules with requirements
3. **User Confirmation** - Present generated rules for review
4. **Iterate if Needed** - Refine based on feedback, return to step 3

### Phase 2: Document Audit

5. **Parse Document** - Extract text blocks from .docx with proper numbering (Aspose)
6. **Execute Audit** - LLM audits each text block against rules independently
7. **Generate Report** - Create HTML report with findings and source tracing

```
Path A (Default Rules):
User: "Audit file.docx" → Parse Document → Audit (default rules) → Report

Path B (Custom Rules):
User: "Check for X, Y, Z" → Generate Rules → Present ───┐
                              ↑                         │
                              └─ (Modify) ←─ Review ────┘
                                               │
                                          (User Approves)
                                               ↓
                                          Parse Document → Audit → Report
```

## Available Tools

### 1. Parse Audit Rules (Iterative)

Intelligently merge base rules with user requirements using LLM (always enabled):

```bash
# Initial generation (uses default_rules.json automatically)
python scripts/parse_rules.py \
  --input "Check for ambiguous payment terms and missing signatures" \
  --output contract_rules.json

# Iteration 1: Refine based on user feedback
python scripts/parse_rules.py \
  --base-rules contract_rules.json \
  --input "Change R007 severity to HIGH, add rule for checking witness requirements" \
  --output contract_rules.json

# Iteration 2: Further refinement
python scripts/parse_rules.py \
  --base-rules contract_rules.json \
  --input "Remove R009, make signature rule more specific" \
  --output contract_rules.json

# Read requirements from file
python scripts/parse_rules.py \
  --file requirements.txt \
  --output contract_rules.json
```

**Key Parameters:**
- `--input <text>`: User requirements or modification requests (required unless using --file). If both `--input` and `--file` are omitted, the script outputs base rules unchanged (LLM deps/API key are still required by current validation).
- `--file <path>`: Read requirements from file instead of --input
- `--base-rules <file>`: Base rules to merge with (default: auto-detects `assets/default_rules.json`)
- `--output <file>`: Output rules file (default: rules.json)
- `--no-base`: Start from scratch without base rules
- `--api-key <key>`: LLM API key (optional, uses GOOGLE_API_KEY or OPENAI_API_KEY by default)

**LLM Requirement:**
- Requires `google-generativeai` or `openai` package installed
- Requires `GOOGLE_API_KEY` or `OPENAI_API_KEY` environment variable set

**Default Rules (10 total):**
- R001-R002: Grammar and spelling
- R003-R004: Clarity and logic
- R005-R007: Monetary amounts, currency, and time references
- R008-R010: Technical terms, passive voice, double negatives

**Workflow:**
1. First call: Merges default rules + user requirements
2. Subsequent calls: Merges previous output + user refinements
3. LLM intelligently handles overlaps, updates, and additions

**Returns:** Complete unified JSON ruleset with rule ID, description, severity, category, and examples

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
python scripts/generate_report.py manifest.jsonl --output report.html --template assets/report_template.html
```

**Important:** The `--template` parameter is **required**. Use `assets/report_template.html` or provide your own custom Jinja2 template.

**Features:**
- Total issue count and distribution by category/severity
- Issue details with original text reference
- Suggested corrections
- Source tracing (heading + block content)
- HTML is escaped by default; use `--trusted-html` only if inputs are trusted

## Quick Start Examples

### Path A: Using Default Rules (No Custom Requirements)

When user only requests "audit [filename]" without specific requirements:

```bash
# Step 1: Parse the document
python scripts/parse_document.py contract.docx --output contract_blocks.jsonl

# Step 2: Run audit with default rules directly
python scripts/run_audit.py \
  --document contract_blocks.jsonl \
  --rules assets/default_rules.json

# Step 3: Generate the HTML audit report (template required)
python scripts/generate_report.py manifest.jsonl --output audit_report.html --template assets/report_template.html
```

### Path B: Custom Rules (User Has Specific Requirements)

When user specifies custom audit requirements:

```bash
# Step 1: Generate custom audit rules (iterative process)
# Initial generation - merges default rules with user requirements
python scripts/parse_rules.py \
  --input "Check for unclear payment amounts, missing currency, vague deadlines" \
  --output contract_rules.json

# Review generated rules, then refine if needed
python scripts/parse_rules.py \
  --base-rules contract_rules.json \
  --input "Change R007 to HIGH severity, add rule for signature requirements" \
  --output contract_rules.json

# Step 2: Parse the document once rules are confirmed
python scripts/parse_document.py contract.docx --output contract_blocks.jsonl

# Step 3: Run the audit with confirmed custom rules
python scripts/run_audit.py \
  --document contract_blocks.jsonl \
  --rules contract_rules.json

# Step 4: Generate the HTML audit report (template required)
python scripts/generate_report.py manifest.jsonl --output audit_report.html --template assets/report_template.html
```

## Agent Workflow Decision Tree

**IF** user request is "audit [filename]" with NO specific requirements:
1. Skip rule generation entirely
2. Parse document: `parse_document.py`
3. Run audit with default rules: `run_audit.py --rules assets/default_rules.json`
4. Generate report: `generate_report.py --template <template.html>`

**ELSE IF** user specifies custom audit requirements:
1. Understand requirements and structure them
2. Generate rules: `parse_rules.py --input "..."`
3. Present generated rules to user for confirmation
4. IF user requests changes:
   - Iterate: `parse_rules.py --base-rules <previous> --input "modifications"`
   - Return to step 3
5. Once user approves rules
6. Parse document: `parse_document.py`
7. Run audit with custom rules: `run_audit.py --rules <custom_rules>.json`
8. Generate report: `generate_report.py --template <template.html>`

## Technical Requirements

### Dependencies

```bash
pip install aspose-words jinja2 google-generativeai openai
```

**Core Libraries:**
- `aspose-words`: Professional DOCX parsing with list label extraction
- `jinja2`: HTML report templating
- `google-generativeai` / `openai`: LLM API access

**Recommended LLM:** gemini-3-flash or gpt-5.2

### Preflight Dependency Check (Required)

Before running any script, the agent must verify the runtime prerequisites. If any required dependency is missing, stop and tell the user exactly how to install it and which environment variables to set.

- `parse_document.py` requires `aspose-words`
- `generate_report.py` requires `jinja2`
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
  "examples": {
    "violation": "Party B shall pay approximately 10% of the total amount.",
    "correction": "Party B shall pay exactly 10% of the total contract amount (RMB)."
  }
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

- Modify `assets/report_template.html` for custom styling, and pass it via `--template`
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
└── assets/
    ├── default_rules.json      # Default audit rules
    └── report_template.html    # Jinja2 report template
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

**Memory Issues with Large Documents:**
- Process in chunks using `--start-block` and `--end-block` parameters
- Use `--resume` to continue from previous run if interrupted

## Related Resources

- [Aspose.Words Documentation](https://reference.aspose.com/words/python-net/)
- [llms.txt Convention](https://llmstxt.org/)
- Original PRD: prd-doc-audit.md
