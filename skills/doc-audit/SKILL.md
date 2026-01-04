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

### Phase 0: Environment Setup (First Time Only)

Before running any audit, set up the project environment:

```bash
bash skills/doc-audit/scripts/setup_project_env.sh
source .claude-work/env.sh
```

This creates:
- `.claude-work/doc-audit/` - Directory for intermediate files (blocks, manifest)
- `.claude-work/venv/` - Python virtual environment with all dependencies
- `.claude-work/env.sh` - Environment activation script
- `.claude-work/workflow-doc-audit.sh` - Convenience workflow script

**Note:** User should have already set `GOOGLE_API_KEY` or `OPENAI_API_KEY` environment variable to choose their preferred LLM provider.

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
   - Output: `.claude-work/doc-audit/blocks.jsonl`
6. **Execute Audit** - LLM audits each text block against rules independently
   - Output: `.claude-work/doc-audit/manifest.jsonl`
7. **Generate Report** - Create HTML report with findings and source tracing
   - Output: `<document_directory>/<document_name>_audit_report.html` (same directory as source document)

```
Phase 0 (Setup - First Time Only):
Environment Setup → [User sets API key] → Ready to Audit

Path A (Default Rules):
User: "Audit file.docx" → Parse Document → Audit (default rules) → Report

Path B (Custom Rules):
User: "Check for X, Y, Z" → Generate Rules → Present ───┐
                              ↑                         │
                              └─ (Modify) ←─ Review ────┘ (User confirms)
                                               │
                                          (User Approves)
                                               ↓
                                          Parse Document → Audit → Report
                                          
Final Report Location: Same directory as source document (<filename>_audit_report.html)
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

**Returns:** JSON file with:
- `version`: Schema version (e.g., "1.0")
- `total_rules`: Number of rules in the ruleset
- `rules`: Array of rule objects, each containing rule ID, description, severity, category, and optional examples

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
- Total issue count and distribution by category
- Issue details with original text reference
- Suggested corrections
- Source tracing (heading + block content)
- HTML is escaped by default; use `--trusted-html` only if inputs are trusted

## Quick Start (Agent Workflow)

### One-Step Workflow (Recommended)

Use the convenience script for the complete audit workflow:

```bash
# Phase 0: Setup environment (first time only)
bash skills/doc-audit/scripts/setup_project_env.sh

# Run complete audit with default rules (assumes API key already set)
./.claude-work/workflow-doc-audit.sh /path/to/contract.docx

# With custom rules
./.claude-work/workflow-doc-audit.sh /path/to/contract.docx .claude-work/doc-audit/custom_rules.json
```

**Output:** Report saved to `/path/to/contract_audit_report.html`

---

### Step-by-Step Workflow

#### Phase 0: Environment Setup (First Time Only)

```bash
bash skills/doc-audit/scripts/setup_project_env.sh
source .claude-work/env.sh
```

This creates:
- `.claude-work/doc-audit/` - Intermediate files directory
- `.claude-work/venv/` - Python virtual environment
- `.claude-work/env.sh` - Environment activation script
- `.claude-work/workflow-doc-audit.sh` - Convenience workflow script

**Prerequisites:** User should have `GOOGLE_API_KEY` or `OPENAI_API_KEY` environment variable set.

---

#### Decision Point: Does user specify custom audit requirements?

### ➤ Path A: NO - Use Default Rules

**When:** User requests "audit [filename]" without specific requirements

**Workflow:**
1. **Skip Phase 1** - Use default rules directly
2. **Phase 2-Step 5:** Parse document

```bash
python skills/doc-audit/scripts/parse_document.py /path/to/contract.docx \
  --output .claude-work/doc-audit/blocks.jsonl
```

3. **Phase 2-Step 6:** Run audit with default rules

```bash
python skills/doc-audit/scripts/run_audit.py \
  --document .claude-work/doc-audit/blocks.jsonl \
  --rules skills/doc-audit/assets/default_rules.json \
  --output .claude-work/doc-audit/manifest.jsonl
```

4. **Phase 2-Step 7:** Generate report (saved to source document directory)

```bash
python skills/doc-audit/scripts/generate_report.py \
  .claude-work/doc-audit/manifest.jsonl \
  --output /path/to/contract_audit_report.html \
  --template skills/doc-audit/assets/report_template.html
```

**Output:** `/path/to/contract_audit_report.html`

---

### ➤ Path B: YES - Custom Rules with User Interaction

**When:** User specifies custom audit requirements

**Example:** User says: _"Check for unclear payment amounts, missing currency, vague deadlines"_

**Workflow:**

1. **Phase 1-Step 1:** Analyze user requirements (agent understands the request)

2. **Phase 1-Step 2:** Generate initial custom audit rules

```bash
python skills/doc-audit/scripts/parse_rules.py \
  --input "Check for unclear payment amounts, missing currency, vague deadlines" \
  --output .claude-work/doc-audit/custom_rules.json
```

3. **Phase 1-Step 3:** Present generated rules to user for confirmation

**Agent action:** Show the generated rules and ask:
> _"Please review the generated rules. Any changes needed?"_

4. **Phase 1-Step 4:** Handle user feedback

   **If user requests changes:**
   > User says: _"Change R007 severity to HIGH, add rule for signature requirements"_

   Iterate and refine:
   ```bash
   python skills/doc-audit/scripts/parse_rules.py \
     --base-rules .claude-work/doc-audit/custom_rules.json \
     --input "Change R007 severity to HIGH, add rule for signature requirements" \
     --output .claude-work/doc-audit/custom_rules.json
   ```

   → **Return to Step 3** (present updated rules and ask for confirmation again)

   **If user approves:**
   > User says: _"Looks good, proceed with audit"_

   → **Proceed to Phase 2**

5. **Phase 2-Step 5:** Parse the document

```bash
python skills/doc-audit/scripts/parse_document.py /path/to/contract.docx \
  --output .claude-work/doc-audit/blocks.jsonl
```

6. **Phase 2-Step 6:** Run audit with confirmed custom rules

```bash
python skills/doc-audit/scripts/run_audit.py \
  --document .claude-work/doc-audit/blocks.jsonl \
  --rules .claude-work/doc-audit/custom_rules.json \
  --output .claude-work/doc-audit/manifest.jsonl
```

7. **Phase 2-Step 7:** Generate report (saved to source document directory)

```bash
python skills/doc-audit/scripts/generate_report.py \
  .claude-work/doc-audit/manifest.jsonl \
  --output /path/to/contract_audit_report.html \
  --template skills/doc-audit/assets/report_template.html
```

**Output:** `/path/to/contract_audit_report.html`

---

### Summary

| Scenario | Phase 1 (Rules) | Phase 2 (Audit) | Output |
|----------|----------------|-----------------|---------|
| **Path A:** Default rules | Skip | Parse → Audit → Report | `<document>_audit_report.html` |
| **Path B:** Custom rules | Generate → Confirm (iterate if needed) | Parse → Audit → Report | `<document>_audit_report.html` |

**Final report location:** Always saved to the same directory as the source document.

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
  "category": "semantic",
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

The manifest entry written by `run_audit.py` contains both the `violations` array (all violations found) and backward-compatible single-violation fields:

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "p_heading": "2.1 Penalty Clause",
  "p_content": "If Party B delays payment, they shall pay approximately 1% of the total amount as compensation.",
  "is_violation": true,
  "violations": [
    {
      "rule_id": "R002",
      "category": "semantic",
      "violation_text": "approximately 1% of the total amount",
      "violation_reason": "Contains vague term 'approximately' and does not specify currency",
      "suggestion": "Revise to: 'shall pay 1% of the contract total amount as penalty (settled in CNY).'"
    }
  ],
  "category": "semantic",
  "rule_id": "R002",
  "violation_reason": "Contains vague term 'approximately' and does not specify currency",
  "suggestion": "Revise to: 'shall pay 1% of the contract total amount as penalty (settled in CNY).'"
}
```

**Note:** The `violations` array contains all violations found in the text block. The `category` field for each violation is automatically populated by the script based on the `rule_id` lookup in the rules file. The top-level `category`, `rule_id`, `violation_reason`, and `suggestion` fields are populated from the first violation for backward compatibility with older report templates.

**LLM Output:** The LLM only outputs `rule_id`, `violation_text`, `violation_reason`, and `suggestion` for each violation. The script adds `category` by looking up the rule's category from the rules file.

When no violations are found:
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "p_heading": "2.1 Penalty Clause",
  "p_content": "Party B shall pay 1% of the contract amount within 30 days.",
  "is_violation": false,
  "violations": []
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
│   ├── setup_project_env.sh    # Environment setup script (NEW)
│   ├── parse_rules.py          # Rule parsing
│   ├── parse_document.py       # DOCX parsing (Aspose)
│   ├── run_audit.py            # LLM audit execution
│   └── generate_report.py      # Report generation
└── assets/
    ├── default_rules.json      # Default audit rules
    └── report_template.html    # Jinja2 report template

# Working directory (created by setup script)
.claude-work/
├── doc-audit/                  # Intermediate files
│   ├── blocks.jsonl            # Parsed document blocks
│   ├── manifest.jsonl          # Audit results
│   └── custom_rules.json       # Custom rules (optional)
├── venv/                       # Python virtual environment
├── logs/                       # Operation logs
├── env.sh                      # Environment activation script
├── workflow-doc-audit.sh       # Convenience workflow script
└── README-doc-audit.md         # Working directory documentation
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
