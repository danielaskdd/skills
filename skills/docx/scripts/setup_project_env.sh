#!/bin/bash
# Word Document Editing Project Environment Setup Script
# Creates hidden working directory and Python virtual environment in current project directory

set -e

# Configuration
WORK_DIR=".claude-work"
VENV_DIR="$WORK_DIR/venv"
DOCX_SKILLS_PATH="${DOCX_SKILLS_PATH:-/Users/ydh/.claude/plugins/cache/anthropic-agent-skills/document-skills/69c0b1a06741/skills/docx}"

echo "=========================================="
echo "Word Document Editing Environment Setup"
echo "Project Directory: $(pwd)"
echo "=========================================="
echo

# 1. Create working directory structure
echo "1. Creating working directory structure..."
mkdir -p "$WORK_DIR"/{edits,unpacked,backups,logs}
echo "   ✓ Directory created: $WORK_DIR/"
echo

# 2. Create Python virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "2. Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "   ✓ Virtual environment created: $VENV_DIR/"
else
    echo "2. Python virtual environment already exists"
fi
echo

# 3. Install dependencies
echo "3. Installing Python dependencies..."
source "$VENV_DIR/bin/activate"

pip install --quiet --upgrade pip
pip install --quiet aspose-words PyYAML python-docx defusedxml

echo "   ✓ Installed packages:"
pip list | grep -E "aspose-words|PyYAML|python-docx|defusedxml" | sed 's/^/     - /'
echo

# 4. Copy utility scripts
echo "4. Copying utility scripts..."
cp "$DOCX_SKILLS_PATH/scripts/apply_edits.py" "$WORK_DIR/apply_edits.py"
echo "   ✓ apply_edits.py copied"
echo

# 5. Create YAML template
echo "5. Creating YAML configuration template..."
rm -f "$WORK_DIR/edits/"*.yaml
cat > "$WORK_DIR/edits/template.yaml" << 'EOF'
# Word Document Editing Configuration Template
# Version: 1.0

version: "1.0"

document:
  # Path handling: The script will search for the document in multiple locations:
  #   1. Absolute path (if provided)
  #   2. Relative to this YAML file location
  #   3. Relative to .claude-work/ directory
  #   4. Relative to project root
  #
  # Recommended: Use absolute path or place document in project root
  input: "document.docx"
  output: "document_revised.docx"

revision:
  author: "Claude"
  track_changes: true  # false to apply changes directly without tracking
  rsid: ""  # Leave empty for auto-generation

edits:
  # ========================================
  # Example 1: Fix typos (Recommended Method)
  # ========================================
  - type: replace_partial
    description: "Fix spelling error: 'recieve' → 'receive'"
    find_text: "I will recieve the package tomorrow."
    changes:
      - delete: "recieve"
        insert: "receive"
    # line_range: [100, 200]  # Optional: narrow search range

  # ========================================
  # Example 2: Multiple corrections in same paragraph
  # ========================================
  - type: replace_partial
    description: "Fix multiple typos in same paragraph"
    find_text: "The sistem is not working properly"
    changes:
      - delete: "sistem"
        insert: "system"
      - delete: "not working"
        insert: "working"

  # ========================================
  # Example 3: Insert missing text
  # ========================================
  - type: insert
    description: "Add missing 'not'"
    find_text: "The system is working properly"
    position: before  # or 'after'
    insert: "not "

  # ========================================
  # Example 4: Delete redundant text
  # ========================================
  - type: delete
    description: "Remove duplicate word"
    find_text: "the the report"
    delete: "the "

  # ========================================
  # Example 5: Add review comment
  # ========================================
  - type: comment
    description: "Question about data accuracy"
    find_text: "Sales increased by 150%"
    comment: "Please verify this figure with the Q3 report"

  # ========================================
  # IMPORTANT WARNINGS
  # ========================================
  #
  # ⚠ AUTO-NUMBERING WARNING:
  #   If your document uses auto-numbering (1., 2., 3., etc.),
  #   DO NOT include the numbers in find_text or delete operations.
  #   
  #   ✗ WRONG: find_text: "3. Complete the annual report"
  #   ✓ RIGHT: find_text: "Complete the annual report"
  #   
  #   The numbering is generated automatically by Word and is not
  #   part of the actual text content.
  #
  # ⚠ CROSS-RUN TEXT:
  #   Text with different formatting is split into "runs".
  #   This is handled automatically, but be aware that:
  #   - Bold/italic/underline create separate runs
  #   - Different fonts or sizes create separate runs
  #   - The script handles this transparently
  #
  # ⚠ UNIQUE CONTEXT:
  #   Make find_text unique enough to avoid false matches.
  #   Include surrounding context if the same word appears multiple times.
  #   
  #   ✗ RISKY: find_text: "the"  (matches thousands of times)
  #   ✓ SAFE: find_text: "the system administrator"
  #
  # ⚠ PATH HANDLING:
  #   The input document path can be:
  #   - Absolute: "/full/path/to/document.docx"
  #   - Relative to YAML file: "../document.docx"
  #   - Relative to project root: "document.docx"
  #   
  #   If document is not found, you'll get clear error messages
  #   showing all locations searched.

EOF
echo "   ✓ Template created: $WORK_DIR/edits/template.yaml"
echo

# 6. Create convenience scripts
echo "6. Creating convenience shell scripts..."

# Environment setup script
cat > "$WORK_DIR/env.sh" << EOF
#!/bin/bash
# Activate virtual environment
source "$VENV_DIR/bin/activate"
export DOCX_SKILLS_PATH="$DOCX_SKILLS_PATH"
export PYTHONPATH="\$DOCX_SKILLS_PATH:\$PYTHONPATH"
EOF

# Unpack script
cat > "$WORK_DIR/unpack.sh" << 'EOF'
#!/bin/bash
# Unpack Word document
if [ $# -lt 1 ]; then
    echo "Usage: $0 <document.docx> [output_directory]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

DOCX_FILE="$1"
OUTPUT_DIR="${2:-$SCRIPT_DIR/unpacked}"

python3 "$DOCX_SKILLS_PATH/ooxml/scripts/unpack.py" "$DOCX_FILE" "$OUTPUT_DIR"
EOF

# Pack script
cat > "$WORK_DIR/pack.sh" << 'EOF'
#!/bin/bash
# Pack back to Word document
if [ $# -lt 2 ]; then
    echo "Usage: $0 <unpacked_directory> <output_document.docx>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

INPUT_DIR="$1"
OUTPUT_FILE="$2"

python3 "$DOCX_SKILLS_PATH/ooxml/scripts/pack.py" "$INPUT_DIR" "$OUTPUT_FILE" --force
EOF

# Complete workflow script (Aspose.Words version)
cat > "$WORK_DIR/workflow.sh" << 'EOF'
#!/bin/bash
# Complete Word document editing workflow (Aspose.Words)
# Note: This uses Aspose.Words which processes .docx files directly
set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <original_document.docx> <yaml_config_file>"
    echo "Example: $0 document.docx .claude-work/edits/corrections.yaml"
    echo "         $0 document.docx edits/corrections.yaml  # Auto-complete path"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCX_FILE="$1"
YAML_FILE="$2"

# Smart path handling: auto-complete relative paths
if [ ! -f "$YAML_FILE" ]; then
    # Try relative to .claude-work/edits/
    BASENAME_YAML=$(basename "$YAML_FILE")
    if [ -f "$SCRIPT_DIR/edits/$BASENAME_YAML" ]; then
        echo "Note: Auto-resolving path '$YAML_FILE' to '$SCRIPT_DIR/edits/$BASENAME_YAML'"
        YAML_FILE="$SCRIPT_DIR/edits/$BASENAME_YAML"
    else
        echo "Error: Cannot find config file: $YAML_FILE"
        echo "Please verify file path or use full path: .claude-work/edits/xxx.yaml"
        exit 1
    fi
fi

echo "=========================================="
echo "Word Document Editing Workflow"
echo "Aspose.Words Edition (Direct .docx processing)"
echo "=========================================="
echo

echo "Document: $DOCX_FILE"
echo "Config: $YAML_FILE"
echo

# 1. Backup
echo "1. Backing up original document..."
BASENAME=$(basename "$DOCX_FILE" .docx)
cp "$DOCX_FILE" "$SCRIPT_DIR/backups/${BASENAME}_$(date +%Y%m%d_%H%M%S).docx"
echo "   ✓ Backed up"
echo

# 2. Apply edits (Aspose.Words processes .docx directly)
echo "2. Applying edits (Aspose.Words)..."
source "$SCRIPT_DIR/env.sh"
python3 "$SCRIPT_DIR/apply_edits.py" "$YAML_FILE" "$SCRIPT_DIR"
echo

echo "=========================================="
echo "✓ Workflow complete!"
echo "Output file is specified in YAML config: document.output"
echo "=========================================="
EOF

chmod +x "$WORK_DIR"/*.sh
echo "   ✓ Convenience scripts created:"
echo "     - env.sh       (environment variables)"
echo "     - unpack.sh    (unpack document)"
echo "     - pack.sh      (pack document)"
echo "     - workflow.sh  (complete workflow)"
echo

# 7. Create README
echo "7. Creating documentation..."
cat > "$WORK_DIR/README.md" << 'EOF'
# Word Document Editing Working Directory

This directory is automatically created by Claude for Word document editing work.

## Directory Structure

```
.claude-work/
├── venv/              # Python virtual environment
├── edits/             # YAML edit configuration files
│   └── template.yaml  # Configuration template
├── unpacked/          # Unpacked Word documents (for manual OOXML editing)
├── backups/           # Automatic backups
├── logs/              # Operation logs
├── apply_edits.py     # Editing tool (Aspose.Words)
├── *.sh               # Convenience scripts
└── README.md          # This file
```

## Quick Start (Aspose.Words Method - Recommended)

### One-Step Workflow

```bash
# 1. Create edit configuration (based on template)
cp .claude-work/edits/template.yaml .claude-work/edits/my_corrections.yaml
# Edit my_corrections.yaml - specify document.input and document.output

# 2. Execute complete workflow
./.claude-work/workflow.sh document.docx .claude-work/edits/my_corrections.yaml
```

**How it works:**
1. Backs up original document
2. Applies edits using Aspose.Words (directly processes .docx)
3. Output file is saved as specified in YAML `document.output`

### Direct Editing (No workflow script)

```bash
# Activate environment and run apply_edits.py directly
source .claude-work/env.sh
python3 .claude-work/apply_edits.py .claude-work/edits/my_corrections.yaml
```

**Note:** The second parameter (work directory) is optional and defaults to current directory. The workflow script passes it explicitly for clarity.

The output file location is controlled by the `document.output` field in your YAML config.

## Alternative: Manual OOXML Workflow

For advanced users who need direct XML manipulation:

```bash
# 1. Unpack .docx to XML
./.claude-work/unpack.sh document.docx

# 2. Manually edit XML files in .claude-work/unpacked/

# 3. Pack back to .docx
./.claude-work/pack.sh .claude-work/unpacked document_revised.docx
```

**Note:** The standard `workflow.sh` uses Aspose.Words and does NOT use unpack/pack.

## YAML Configuration Guide

See detailed examples in `edits/template.yaml`.

**Key configuration:**
```yaml
document:
  input: "document.docx"      # Path to original document
  output: "document_revised.docx"  # Where to save edited version

revision:
  author: "Claude"
  track_changes: true          # Enable Word Track Changes
```

**Supported edit types:**
- `replace_partial`: Partial replacement (recommended for corrections)
- `insert`: Insert text
- `delete`: Delete text
- `comment`: Add review comment

## Features

- ✅ Automatic backup of original documents
- ✅ Uses Word Track Changes mode
- ✅ Direct .docx processing (no XML unpacking needed)
- ✅ Automatic cross-run text matching
- ✅ Isolated working environment (virtual environment)
- ✅ Temporary files don't pollute project directory
- ✅ Already added to .gitignore

## Important Notes

1. **Documents are automatically backed up** to `backups/` directory
2. **All modifications use Word Track Changes** (can be disabled in YAML)
3. **Output filename** is specified in YAML `document.output` field
4. **Aspose.Words** handles complex formatting automatically
5. **unpacked/ directory** is only used for manual OOXML editing
6. This directory is automatically added to `.gitignore`

## Workflow Comparison

| Method | Pros | Cons | Use Case |
|--------|------|------|----------|
| **Aspose.Words** (default) | Simple, handles cross-run text, track changes | Requires Aspose license | General editing, corrections |
| **OOXML** (manual) | Full control over XML | Complex, manual handling required | Advanced customization |
EOF
echo "   ✓ README.md created"
echo

echo "=========================================="
echo "✓ Environment setup complete!"
echo "=========================================="
echo
echo "Quick start:"
echo "1. Copy configuration template:"
echo "   cp $WORK_DIR/edits/template.yaml $WORK_DIR/edits/my_edit.yaml"
echo
echo "2. Execute in one step:"
echo "   ./$WORK_DIR/workflow.sh document.docx $WORK_DIR/edits/my_edit.yaml"
echo
echo "For detailed instructions, see: $WORK_DIR/README.md"
echo
