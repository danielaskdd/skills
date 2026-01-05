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
source .claude-work/doc-audit/env.sh
```

This creates:
- `.claude-work/env.sh` - Script for setting up python virtual environment and environment variables
- `.claude-work/doc-audit/` - Directory for all doc-audit files (env, scripts, intermediate files)
- `.claude-work/venv/` - Python virtual environment (shared across skills)
- `.claude-work/logs/` - Operation logs (shared across skills)

**Note:** User should have already set `GOOGLE_API_KEY` or `OPENAI_API_KEY` environment variable to choose their preferred LLM provider.

### Phase 1: Rule Selection

**Decision Point:** Does user specify custom audit requirements?

**Path A: Use Default Rules (Simple)**

- User only requests "audit [filename]" without specific requirements
- **Skip rule generation** - use `.claude-work/doc-audit/default_rules.json` (copied from `assets/default_rules.json` during enviroment setup)
- Proceed immediately to Phase 2

**Path B: Custom Rules (Iterative)**

1. **Analyze Requirements** - Agent converts user's needs into clear criteria

2. **Generate Rules** - Invoke `parse_rules.py` to generate customized rules by merging them with the default rules

   ⚠️ **CRITICAL**: Do NOT use the `--no-base` flag unless the user explicitly requests to exclude default rules. The default behavior is to merge user requirements WITH base rules.

3. **User Confirmation** - ⚠️ **MANDATORY STEP - DO NOT SKIP**:

   After generating rules, you **MUST**:
   - Use `read_file` to read the generated rules file (`.claude-work/doc-audit/custom_rules.json`)
   - Present ALL rules to user in the following simplified format:
     ```
     [R001] Rule description...
     [R002] Rule description...
     [R003] Rule description...
     ...
     Total: N rules
     ```
   - Ask user explicitly: "请审阅以上规则。是否批准继续审计？或需要修改规则？" (Please review the rules above. Approve to continue audit? Or need modifications?)
   - **DO NOT proceed to Phase 2 until user explicitly confirms approval**

4. **Iterate if Needed** - If user requests changes, refine rules using `parse_rules.py` again, then return to step 3 for re-confirmation

### Phase 2: Parse and Audit

5. **Parse Document** - Extract text blocks from .docx with proper numbering (Aspose)
   - Output: `.claude-work/doc-audit/blocks.jsonl`
6. **Execute Audit Work Flow** - LLM audits each text block against rules by `workflow.sh` (created by enviroment setup)
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
                                          Parse Document → Execute Audit
                                          
Final Report Location: Same directory as source document (<filename>_audit_report.html)
```

## Available Tools

### 1. Environment Setup (First Time Only)

Setup the project environment before running any audit:

```bash
bash scripts/setup_project_env.sh
source ./.claude-work/doc-audit/env.sh
```

**What it creates:**

- `.claude-work/venv/` - Python virtual environment (shared across skills)
- `.claude-work/logs/` - Operation logs (shared across skills)
- `.claude-work/doc-audit/` - Document audit working directory
- `.claude-work/doc-audit/env.sh` - Environment activation script
- `.claude-work/doc-audit/workflow.sh` - Convenience workflow script
- `.claude-work/doc-audit/default_rules.json` - Default audit rules (copied from assets)
- `.claude-work/doc-audit/report_template.html` - Report template (copied from assets)

**Installed packages:**
- `aspose-words` - DOCX parsing
- `jinja2` - HTML templating
- `google-genai` - Google Gemini LLM
- `openai` - OpenAI LLM

**Note:** User must set `GOOGLE_API_KEY` or `OPENAI_API_KEY` environment variable before running audits.

### 2. Generate Customized Rules (Iterative)

Intelligently merge base rules with user requirements using LLM.

**DEFAULT BEHAVIOR**: Always merges with base rules unless user explicitly requests otherwise.

**Common Usage Patterns:**

```bash
# ✅ RECOMMENDED: Initial generation (automatically merges with default rules)
# Use when: User wants custom requirements PLUS default rules
python scripts/parse_rules.py \
  --input "Check for ambiguous payment terms and missing signatures" \
  --output .claude-work/doc-audit/custom_rules.json

# ✅ RECOMMENDED: Iterative refinement (continues from previous output)
# Use when: User wants to modify/add/remove specific rules
python scripts/parse_rules.py \
  --base-rules .claude-work/doc-audit/custom_rules.json \
  --input "Add rule for checking ambiguous references" \
  --output .claude-work/doc-audit/custom_rules.json

# ✅ Further iteration
python scripts/parse_rules.py \
  --base-rules .claude-work/doc-audit/custom_rules.json \
  --input "Remove R009, make signature rule more specific" \
  --output .claude-work/doc-audit/custom_rules.json

# Use --base-rules parameter to generate customized rules for most of the time.
# ⚠️ ONLY use --no-base when user EXPLICITLY requests to exclude default rules
# Example user requests that warrant --no-base:
#   - "Only check for X and Y, don't include any default rules"
#   - "Start from scratch without default rules"
#   - "I only want these specific rules, no others"
python scripts/parse_rules.py \
  --no-base \
  --input "Check for missing section numbers and inconsistent terminology" \
  --output .claude-work/doc-audit/custom_rules.json
```

**Decision Guide:**
- User: "Check for A, B, C" → ✅ Use  `--base-rules`
- User: "Add rule for X" → ✅ Use `--base-rules`
- User: "ONLY check for A, no other rules" → ⚠️ Use `--no-base`
- User: "Don't include default/standard rules" → ⚠️ Use `--no-base`

**Key Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--input` / `-i` | text | No* | User requirements or modification requests (natural language) |
| `--file` / `-f` | path | No* | Read requirements from file instead of --input |
| `--base-rules` | path | No | Base rules to merge with (default: auto-detects `.claude-work/doc-audit/default_rules.json`, then falls back to `assets/default_rules.json`) |
| `--output` / `-o` | path | No | Output rules file (default: `rules.json`) |
| `--no-base` | flag | No | ⚠️ **DO NOT USE** unless user explicitly requests to exclude default rules. Starts from scratch without loading any base rules. |
| `--api-key` | text | No | API key for LLM service (uses `GOOGLE_API_KEY` or `OPENAI_API_KEY` env var by default) |

\* At least one of `--input` or `--file` is required, unless you just want to renumber base rules

**LLM Requirements:**
- Requires `google-genai` or `openai` package installed
- Requires `GOOGLE_API_KEY` / `DOC_AUDIT_GEMINI_MODEL` or `OPENAI_API_KEY` / `DOC_AUDIT_OPENAI_MODEL` environment variable set

**Workflow:**

1. **First call**: Merges default rules + user requirements → generates numbered rules (R001, R002, ...)
2. **Subsequent calls**: Merges previous output + user refinements → intelligently updates/adds/removes rules
3. **LLM processing**: Handles overlaps, updates, additions, and removals based on natural language instructions
4. **Renumbering**: All rules are renumbered sequentially to avoid ID conflicts

**Output Format:**

```json
{
  "version": "1.0",
  "total_rules": 5,
  "rules": [
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
  ]
}
```

### 3. Parse Document

Extract text blocks from a Word document with proper heading hierarchy and numbering:

```bash
# Basic usage (outputs to <document>_blocks.jsonl)
python scripts/parse_document.py document.docx

# Custom output path
python scripts/parse_document.py document.docx \
  --output .claude-work/doc-audit/blocks.jsonl

# With preview and statistics
python scripts/parse_document.py document.docx \
  --output blocks.jsonl \
  --preview \
  --stats

# Output as regular JSON instead of JSONL
python scripts/parse_document.py document.docx \
  --output blocks.json \
  --format json
```

**Key Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document` | path | Yes | Path to the DOCX file to parse |
| `--output` / `-o` | path | No | Output file path (default: `<document>_blocks.jsonl`) |
| `--format` | choice | No | Output format: `jsonl` (default) or `json` |
| `--preview` | flag | No | Print preview of first 5 extracted blocks |
| `--stats` | flag | No | Print document statistics (headings, characters, etc.) |

**Features:**

- **Automatic numbering capture**: Extracts list labels (e.g., "1.1", "Chapter 1") via Aspose's `update_list_labels()`
- **Heading-based splitting**: Each heading starts a new text block
- **Table conversion**: Tables converted to structured 2D JSON arrays as independent blocks
- **Heading hierarchy**: Preserves parent headings context for each block
- **Deterministic UUIDs**: Generates consistent UUIDs from heading + content + position for reliable resume

**Workflow:**

1. Load document with Aspose.Words
2. Call `doc.update_list_labels()` to render automatic numbering
3. Iterate through body nodes (paragraphs and tables)
4. For each heading: save previous block, update heading stack based on outline level
5. For each paragraph: append to current block
6. For each table: convert to 2D array, save as separate block
7. Generate deterministic UUID for each block using SHA-256(position + heading + content)
8. Clean up old `manifest.jsonl` to prevent UUID mismatch in resume mode

**Output Format (JSONL):**

Each line is a JSON object:
```json
{"uuid": "a1b2c3...", "heading": "2.1 Penalty Clause", "content": "If Party B delays...", "type": "text", "parent_headings": ["Chapter 2 Contract Terms"]}
{"uuid": "d4e5f6...", "heading": "Table (under: 2.1 Penalty Clause)", "content": [["Header 1", "Header 2"], ["Cell 1", "Cell 2"]], "type": "table", "parent_headings": ["Chapter 2 Contract Terms", "2.1 Penalty Clause"]}
```

**Output Format (JSON):**

```json
{
  "total_blocks": 42,
  "blocks": [
    {
      "uuid": "a1b2c3d4e5f6...",
      "heading": "2.1 Penalty Clause",
      "content": "If Party B delays payment...",
      "type": "text",
      "parent_headings": ["Chapter 2 Contract Terms"]
    }
  ]
}
```

### 4. Run Audit

Execute LLM-based audit on each text block against audit rules:

```bash
# Basic usage with auto model selection
python scripts/run_audit.py \
  --document .claude-work/doc-audit/blocks.jsonl \
  --rules .claude-work/doc-audit/default_rules.json

# Specify model explicitly
python scripts/run_audit.py \
  --document blocks.jsonl \
  --rules custom_rules.json \
  --model gemini-2.5-flash

# Process specific block range
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --start-block 10 \
  --end-block 50

# Resume from previous interrupted run
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --resume

# Dry run to preview prompts without calling LLM
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --dry-run
```

**Key Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--document` / `-d` | path | Yes | Path to document blocks file (JSONL or JSON from `parse_document.py`) |
| `--rules` / `-r` | path | Yes | Path to audit rules JSON file |
| `--output` / `-o` | path | No | Output manifest file path (default: `manifest.jsonl`) |
| `--model` | text | No | LLM model: `auto` (default), `gemini-2.5-flash`, `gpt-5.2`, etc. |
| `--rate-limit` | float | No | Seconds to wait between API calls (default: 0.5) |
| `--start-block` | int | No | Start from this block index (0-based, default: 0) |
| `--end-block` | int | No | End at this block index (inclusive, default: last block) |
| `--resume` | flag | No | Resume from previous run (skip already-processed blocks) |
| `--dry-run` | flag | No | Print prompts without calling LLM (for debugging) |

**Model Selection (`--model`):**

- `auto` (default): Auto-select based on available API keys (Gemini preferred if both are set)
- `gemini-2.5-flash`, `gemini-3-flash`: Use Google Gemini (requires `GOOGLE_API_KEY`)
- `gpt-5.2`, `gpt-4o`, `gpt-4o-mini`: Use OpenAI (requires `OPENAI_API_KEY`)
- Model defaults are configured in `.claude-work/doc-audit/env.sh`

**Resume Functionality (Advanced):**

The `--resume` flag enables recovery from interrupted audit runs by:

1. **Loading completed UUIDs**: Reads `manifest.jsonl` to get UUIDs of already-processed blocks
2. **Skipping processed blocks**: During iteration, skips blocks whose UUIDs are in the completed set
3. **Appending new results**: New audit results are appended to existing `manifest.jsonl`

**Resume Use Cases:**

**Case 1: Simple Resume After Interruption**
```bash
# Initial run (interrupted at block 45/100)
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --output manifest.jsonl
# ... interrupted (Ctrl+C, network error, etc.)

# Resume from where it left off
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --output manifest.jsonl \
  --resume
# Automatically skips blocks 0-44, continues from block 45
```

**Case 2: Chunked Processing with Resume**

For large documents, process in chunks to avoid API rate limits or long-running sessions:

```bash
# Process first chunk (blocks 0-99)
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --start-block 0 \
  --end-block 99

# Process second chunk (blocks 100-199) - interrupted at block 150
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --start-block 100 \
  --end-block 199
# ... interrupted

# Resume second chunk (will skip 100-149, continue from 150)
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --start-block 100 \
  --end-block 199 \
  --resume

# Process third chunk (blocks 200-299)
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules rules.json \
  --start-block 200 \
  --end-block 299
```

**Case 3: Re-audit Specific Blocks (Without Resume)**

To re-audit specific blocks (e.g., after changing rules), **do NOT use `--resume`**:

```bash
# Re-audit blocks 10-20 (will overwrite those results in manifest)
python skills/doc-audit/scripts/run_audit.py \
  --document blocks.jsonl \
  --rules updated_rules.json \
  --start-block 10 \
  --end-block 20
# Without --resume, it processes all blocks 10-20 regardless of manifest
```

**Important Notes:**

- ⚠️ **UUID Consistency**: Resume relies on UUIDs. If you re-run `parse_document.py`, `manifest.jsonl` is automatically deleted by the script, a fresh audit is required.
- ✅ **Append-Only**: Resume appends to `manifest.jsonl`. If you want to start completely fresh, delete the manifest file first.
- ✅ **Block Range + Resume**: Combining `--start-block`/`--end-block` with `--resume` is valid - it will skip already-processed blocks within the specified range.

**Workflow:**

1. **Build system prompt**: Formats rules as structured instructions (cached by LLM across all blocks)
2. **Load completed UUIDs**: If `--resume` is set, loads already-processed block UUIDs from manifest
3. **Iterate blocks**: For each block in range:
   - Skip if UUID already processed (resume mode)
   - Build user prompt with heading context + content
   - Call LLM with structured output schema (Gemini or OpenAI)
   - Parse violations from LLM response
   - Add category to each violation (lookup from rule ID)
   - Save entry to manifest.jsonl (append mode)
   - Rate limit between requests
4. **Error handling**: Catches JSON parsing errors and API errors, continues to next block

**Output Format (manifest.jsonl):**

Each line is an audit result:
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "p_heading": "2.1 Penalty Clause",
  "p_content": "If Party B delays payment, they shall pay approximately 1%...",
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

**Note:** Top-level `category`, `rule_id`, `violation_reason`, and `suggestion` fields are for backward compatibility (populated from first violation).

### 5. Generate Report

Create HTML audit report from audit manifest with statistics and traceability:

```bash
# Basic usage
python scripts/generate_report.py manifest.jsonl \
  --template .claude-work/doc-audit/report_template.html \
  --rules .claude-work/doc-audit/default_rules.json \
  --output audit_report.html


# No rule descriptions in report (not recommended)
python scripts/generate_report.py manifest.jsonl \
  --template .claude-work/doc-audit/report_template.html \
  --output audit_report.html

# Also output JSON data
python skills/doc-audit/scripts/generate_report.py manifest.jsonl \
  --template .claude-work/doc-audit/report_template.html \
  --rules rules.json \
  --output report.html \
  --json

# For trusted HTML content (disables escaping, not recommended)
python skills/doc-audit/scripts/generate_report.py manifest.jsonl \
  --template .claude-work/doc-audit/report_template.html \
  --output report.html \
  --trusted-html
```

**Key Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `manifest` | path | Yes | Path to audit manifest JSONL file (from `run_audit.py`) |
| `--output` / `-o` | path | No | Output HTML file path (default: `audit_report.html`) |
| `--template` / `-t` | path | Yes | Path to Jinja2 HTML template |
| `--rules` / `-r` | path | No | Path to rules JSON file (optional, recommended for displaying full rule details in modal popups) |
| `--trusted-html` | flag | No | Disable HTML escaping (only for trusted inputs) |
| `--json` | flag | No | Also output report data as JSON (same name with `.json` extension) |

**Features:**

- **Statistics Dashboard**: Total blocks, violation count, category distribution
- **Issue Details**: Each violation with heading, content, reason, and suggestion
- **Source Tracing**: Clickable headings that show full context
- **Rule Information**: Clickable rule badges (e.g., `[R001]`) that display full rule details in modal popups (when `--rules` is provided)
- **HTML Safety**: Escapes HTML by default; use `--trusted-html` only if all inputs are trusted

**Workflow:**

1. **Load manifest**: Parse `manifest.jsonl` to get all audit results
2. **Load rules** (optional): If `--rules` provided, load rule descriptions for modal popups
3. **Generate report data**:
   - Count total blocks and violations
   - Group violations by category
   - Collect unique rules used
4. **Render HTML**: Use Jinja2 template with report data
5. **Save output**: Write HTML file (and optionally JSON)

**Output Files:**

- `<output>.html` - HTML report (always generated)
- `<output>.json` - JSON report data (if `--json` flag is used)

### 6. Workflow Script (Complete Workflow)

`workflow.sh` is a convenience script that runs all three stages automatically:

```bash
# Use default rules
./.claude-work/doc-audit/workflow.sh document.docx

# Use custom rules
./.claude-work/doc-audit/workflow.sh document.docx .claude-work/doc-audit/custom_rules.json
```

**Internal Process:**

1. **Parse document** → `.claude-work/doc-audit/blocks.jsonl` (via `parse_document.py`)
2. **Run audit** → `.claude-work/doc-audit/manifest.jsonl` (via `run_audit.py`)
3. **Generate report** → `<document_directory>/<document_name>_audit_report.html` (via `generate_report.py`)

**Features:**

- ✅ Cleans previous intermediate files (`blocks.jsonl`, `manifest.jsonl`) before starting
- ✅ Final report saved in same directory as source document
- ✅ Uses working directory's default rules if no custom rules specified
- ✅ Automatically passes rules to report generation for full rule details

**Note:** If the workflow fails at any stage, you can run individual tools (2-5 above) to debug or continue manually.

## Technical Requirements

### Dependencies

**Core Libraries:**

- `aspose-words`: Professional DOCX parsing with list label extraction
- `jinja2`: HTML report templating
- `google-genai` / `openai`: LLM API access

Enviroment Setup `setup_project_env.sh` will create Python venv and install all dependencies automatically.

### Environment Variables

```bash
# API Keys (required)
# For Gemini (If both Gemini and OpenAI are set, Gemini is used by default)
export GOOGLE_API_KEY=your_api_key

# For OpenAI
export OPENAI_API_KEY=your_api_key

# Model Configuration (optional - set in env.sh automatically)
# Override these to use different models across all scripts
export DOC_AUDIT_GEMINI_MODEL=gemini-3-flash    # Default Gemini model
export DOC_AUDIT_OPENAI_MODEL=gpt-5.2           # Default OpenAI model

# Output Language Configuration (optional - set in env.sh automatically)
# Specifies the language for LLM-generated rules and audit results
# Examples: "Chinese", "English", "Japanese", "Korean", etc.
export AUDIT_LANGUAGE=Chinese                   # Default: Chinese
```

**⚠️ OpenAI Model Compatibility:**

When using OpenAI, the scripts use Structured Outputs (`json_schema` response format), which requires:
- ✅ `gpt-4o-2024-08-06` or later
- ✅ `gpt-4o-mini` or later
- ✅ `gpt-4o` (latest)
- ✅ `gpt-5.x` series (e.g., `gpt-5.2`)

Older models are **NOT supported** and will cause API errors:
- ❌ `gpt-4-turbo`
- ❌ `gpt-4`
- ❌ `gpt-3.5-turbo`

If you encounter errors like "json_schema is not supported", ensure you're using a compatible model.

**Model Configuration:**
The default models for all scripts are centralized in `.claude-work/doc-audit/env.sh`:
- **Gemini**: `gemini-3-flash` (changeable via `DOC_AUDIT_GEMINI_MODEL`)
- **OpenAI**: `gpt-5.2` (changeable via `DOC_AUDIT_OPENAI_MODEL`)

To use different models, edit `.claude-work/doc-audit/env.sh` before running scripts:

```bash
# Example: Use a different model across all scripts
export DOC_AUDIT_GEMINI_MODEL="gemini-2.0-flash-exp"
export DOC_AUDIT_OPENAI_MODEL="gpt-4o"  # or gpt-5.2, gpt-4o-mini, etc.
```

### Failure handling

If a required package or API key is missing, do not proceed with the workflow. Provide the exact `pip install ...` command(s) and the `export ...` command(s) needed to prepare the environment.

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
  "parent_headings": ["Chapter 2 Contract Terms"]
}
```

**Note:** `parent_headings` contains only the ancestor headings hierarchy, not the current heading (which is in the `heading` field).

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

## File Structure

```
doc-audit/
├── SKILL.md                    # This file
├── scripts/
│   ├── setup_project_env.sh    # Environment setup script
│   ├── parse_rules.py          # Rule parsing
│   ├── parse_document.py       # DOCX parsing (Aspose)
│   ├── run_audit.py            # LLM audit execution
│   └── generate_report.py      # Report generation
└── assets/
    ├── default_rules.json      # Default audit rules (source)
    └── report_template.html    # Jinja2 report template (source)

# Working directory (created by setup script - all work happens here)
.claude-work/
├── venv/                          # Python virtual environment (shared across skills)
├── logs/                          # Operation logs (shared across skills)
└── doc-audit/                     # Document audit working directory
    ├── env.sh                     # Environment activation script
    ├── workflow.sh                # Convenience workflow script
    ├── README.md                  # Working directory documentation
    ├── default_rules.json         # Default rules (copied from assets)
    ├── report_template.html       # Report template (copied from assets)
    ├── blocks.jsonl               # Parsed document blocks
    ├── manifest.jsonl             # Audit results
    └── custom_rules.json          # Custom rules (optional)
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
- Use `--resume` to continue from previous run if run_audit.py is interrupted
