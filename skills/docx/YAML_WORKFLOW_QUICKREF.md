# YAML Workflow Quick Reference

## Claude's Workflow for Word Document Editing

When a user asks Claude to edit a Word document, Claude should follow this workflow:

### Step 1: Setup Environment (First Time Only)

```bash
# Set the docx skills path
DOCX_SKILLS_PATH=/Users/ydh/.claude/plugins/cache/anthropic-agent-skills/document-skills/69c0b1a06741/skills/docx

# Run setup in the current project directory
cd /path/to/project
bash $DOCX_SKILLS_PATH/scripts/setup_project_env.sh
```

### Step 2: Analyze Document and Generate YAML

1. Read the document (using pandoc or direct reading)
2. Identify all errors/changes needed
3. Generate a YAML configuration file

**YAML Template:**

```yaml
version: "1.0"

document:
  input: "OriginalDocument.docx"
  output: "Document_修订版.docx"

revision:
  author: "Claude"
  track_changes: true
  rsid: ""  # Leave empty for auto-generation

edits:
  - type: replace_partial
    description: "Brief description of this change"
    find_text: "The complete text containing the error"
    changes:
      - delete: "error"
        insert: "correction"
    line_range: [start_line, end_line]  # Optional
```

### Step 3: Save YAML to Project Directory

```bash
# Save to .claude-work/edits/ directory
cat > .claude-work/edits/$(date +%Y%m%d_%H%M%S)_corrections.yaml << 'EOF'
[paste YAML content here]
EOF
```

### Step 4: Execute Workflow

```bash
# Method 1: Full path (recommended for clarity)
./.claude-work/workflow.sh OriginalDocument.docx .claude-work/edits/corrections.yaml

# Method 2: Short path (auto-completion)
./.claude-work/workflow.sh OriginalDocument.docx edits/corrections.yaml

# Output: OriginalDocument_修订版.docx with tracked changes
```

## Edit Types Reference

### 1. replace_partial (Most Common)

**Use for**: Typos, grammatical errors, word replacements

```yaml
- type: replace_partial
  description: "Fix typo: recieve → receive"
  find_text: "I will recieve the package"
  changes:
    - delete: "recieve"
      insert: "receive"
```

**Key points:**
- Marks only what changed (professional revision)
- Preserves formatting
- Can handle multiple changes in sequence

### 2. insert

**Use for**: Adding missing words or text

```yaml
- type: insert
  description: "Add missing word 'data'"
  find_text: "AI learning project"  # Anchor text
  position: before  # or 'after'
  insert: "big data"
  line_range: [100, 200]  # Optional
```

### 3. delete

**Use for**: Removing unwanted text

```yaml
- type: delete
  description: "Remove redundant phrase"
  find_text: "text to be deleted"
```

### 4. comment

**Use for**: Adding review comments

```yaml
- type: comment
  description: "Flag for verification"
  find_text: "target phrase"
  comment: "Please verify this data with Finance"
```

## Best Practices for Claude

### 1. Environment Setup

**Always check first:**
```bash
# Check if .claude-work exists
if [ ! -d ".claude-work" ]; then
    # Setup environment
    bash $DOCX_SKILLS_PATH/scripts/setup_project_env.sh
fi
```

### 2. YAML Generation

**DO:**
- ✅ Use descriptive filenames: `20250127_memo_corrections.yaml`
- ✅ Add clear descriptions for each edit
- ✅ Use `line_range` when text appears multiple times
- ✅ Group related changes in one YAML file
- ✅ Include enough context in `find_text`

**DON'T:**
- ❌ Create temporary Python scripts
- ❌ Use vague descriptions
- ❌ Split simple changes into multiple files
- ❌ Use too-short `find_text` (ambiguous matching)

### 3. Communicating with User

**Tell the user:**
1. Where the YAML file was saved
2. What changes are being made (summary)
3. The command to execute
4. Where the output will be

**Example:**
```markdown
I've created a YAML configuration with 3 corrections:
1. "对外报" → "上报" (line 1339)
2. "首棒" → "首批" (line 2280)
3. Insert "大数据" before "学项目" (line 2471)

Configuration saved to: .claude-work/edits/20250127_corrections.yaml

To execute (either syntax works):
./.claude-work/workflow.sh MemO20251215.docx .claude-work/edits/20250127_corrections.yaml
# or
./.claude-work/workflow.sh MemO20251215.docx edits/20250127_corrections.yaml

Output will be: MemO20251215_修订版.docx
```

### 4. Line Number Finding

When `find_text` appears multiple times:

```bash
# 1. Unpack first (to get line numbers)
./.claude-work/unpack.sh document.docx

# 2. Search in XML
grep -n "search text" .claude-work/unpacked/word/document.xml

# 3. Use line range in YAML
line_range: [found_line - 50, found_line + 50]
```

## Common Scenarios

### Scenario 1: Simple Typo Fixes

```yaml
version: "1.0"
document:
  input: "report.docx"
  output: "report_corrected.docx"
revision:
  author: "Claude"
  track_changes: true
edits:
  - type: replace_partial
    description: "Fix: teh → the"
    find_text: "This is teh report"
    changes:
      - delete: "teh"
        insert: "the"
```

### Scenario 2: Multiple Corrections

```yaml
edits:
  - type: replace_partial
    description: "Grammar: your → you're"
    find_text: "your going to love this"
    changes:
      - delete: "your"
        insert: "you're"

  - type: insert
    description: "Add missing 'very'"
    find_text: "This is important"
    position: before
    insert: "very "

  - type: replace_partial
    description: "Number: 2023 → 2024"
    find_text: "fiscal year 2023"
    changes:
      - delete: "2023"
        insert: "2024"
```

### Scenario 3: Complex Text with Ambiguity

```yaml
edits:
  - type: replace_partial
    description: "Fix 'project' in Introduction section"
    find_text: "The AI project was launched"
    changes:
      - delete: "AI"
        insert: "AI/ML"
    line_range: [50, 150]  # Narrow to Introduction section

  - type: replace_partial
    description: "Fix 'project' in Conclusion section"
    find_text: "The AI project achieved success"
    changes:
      - delete: "AI"
        insert: "AI/ML"
    line_range: [500, 600]  # Narrow to Conclusion section
```

## Advantages Over Python Scripts

| Task | Old Method | New Method |
|------|-----------|------------|
| Setup | Manual pip install | Automatic venv creation |
| Code | Write Python scripts | Write YAML config |
| Lines | 50-200 per script | 10-30 YAML |
| Files | 3-4 temp scripts | 1 YAML file |
| Learning | Needs Python knowledge | Simple YAML |
| Reuse | Copy-paste code | Reuse YAML structure |
| Maintenance | Update scripts | Update config |
| Cleanup | Delete temp files | Organized in .claude-work |
| Version control | Not practical | YAML in git |

## Troubleshooting

### Problem: "Cannot find text"

**Solution:**
1. Verify exact text with spaces and punctuation
2. Check if text spans multiple lines
3. Use longer context for `find_text`
4. Add `line_range` to narrow search

### Problem: "Multiple matches found"

**Solution:**
Add `line_range` to specify which occurrence:
```yaml
line_range: [1000, 1100]  # Only search in this range
```

### Problem: "Environment not found"

**Solution:**
Run setup again:
```bash
bash $DOCX_SKILLS_PATH/scripts/setup_project_env.sh
```

### Problem: "Validation failed"

**Solution:**
This is normal. The workflow scripts use `--force` to bypass validation.

## File Organization

```
project/
├── OriginalDocument.docx
├── Document_修订版.docx      # Output
├── .claude-work/             # Hidden work directory
│   ├── venv/                # Python environment
│   ├── edits/               # YAML configurations
│   │   ├── template.yaml
│   │   └── 20250127_corrections.yaml
│   ├── unpacked/            # Temporary XML files
│   ├── backups/             # Auto backups
│   │   └── OriginalDocument_20250127_120000.docx
│   ├── apply_edits.py       # Tool script
│   ├── workflow.sh          # One-command execution
│   └── README.md
└── .gitignore               # Auto-updated
```

## Integration with Git

The `.claude-work/` directory is automatically added to `.gitignore`, but keep YAML configurations:

```bash
# Add YAML configs to git for tracking
git add .claude-work/edits/*.yaml

# Ignore the rest
# (.gitignore already has .claude-work/)
```

## Using python-docx for Analysis

The virtual environment includes `python-docx` for document analysis:

### Quick Analysis Example

```bash
source .claude-work/venv/bin/activate
python << 'EOF'
from docx import Document

doc = Document('document.docx')

# Find text
search = "error text"
for i, para in enumerate(doc.paragraphs):
    if search in para.text:
        print(f"Found at paragraph {i}: {para.text[:60]}...")

# Check structure
print(f"\nStructure:")
print(f"  Paragraphs: {len(doc.paragraphs)}")
print(f"  Tables: {len(doc.tables)}")
EOF
```

### Analysis → YAML → Verification Workflow

```bash
# 1. Analyze (before editing)
python << 'EOF'
from docx import Document
doc = Document('doc.docx')
# ... find errors and locations
EOF

# 2. Generate YAML based on analysis

# 3. Apply edits
./.claude-work/workflow.sh doc.docx .claude-work/edits/corrections.yaml

# 4. Verify (after editing)
python << 'EOF'
from docx import Document
doc = Document('doc_修订版.docx')
# ... verify changes applied
EOF
```

**See PYTHON_DOCX_GUIDE.md for detailed examples.**

## Summary for Claude

When editing Word documents:

1. **First time in a project**: Run `setup_project_env.sh`
2. **Analyze** (optional): Use python-docx to understand structure
3. **Every time**: Generate YAML, don't write Python scripts
4. **Organize**: Save YAML to `.claude-work/edits/`
5. **Execute**: Use `./.claude-work/workflow.sh`
6. **Verify** (optional): Use python-docx to confirm changes
7. **Communicate**: Tell user what's in the YAML and how to run it

**This replaces the old workflow of creating temporary Python scripts!**
