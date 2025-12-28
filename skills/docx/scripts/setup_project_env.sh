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
pip install --quiet defusedxml lxml PyYAML python-docx

echo "   ✓ Installed packages:"
pip list | grep -E "defusedxml|lxml|PyYAML|python-docx" | sed 's/^/     - /'
echo

# 4. Copy utility scripts
echo "4. Copying utility scripts..."
cp "$DOCX_SKILLS_PATH/scripts/apply_edits.py" "$WORK_DIR/"
echo "   ✓ apply_edits.py copied"
echo

# 5. Create YAML template
echo "5. Creating YAML configuration template..."
cat > "$WORK_DIR/edits/template.yaml" << 'EOF'
# Word Document Editing Configuration Template
version: "1.0"

document:
  input: "original_document.docx"
  output: "document_revised.docx"

revision:
  author: "Claude"
  track_changes: true
  rsid: ""  # Leave empty for auto-generation

edits:
  # Example 1: Partial replacement (recommended for corrections)
  - type: replace_partial
    description: "Fix typos"
    find_text: "Complete sentence or paragraph containing the error"
    changes:
      - delete: "incorrect word"
        insert: "correct word"
    line_range: [100, 200]  # Optional, narrows search range

  # Example 2: Insert text
  - type: insert
    description: "Add missing text"
    find_text: "anchor text"
    position: before  # before or after
    insert: "text to insert"

  # Example 3: Delete text
  - type: delete
    description: "Remove redundant content"
    find_text: "text to delete"

  # Example 4: Add comment
  - type: comment
    description: "Add review comment"
    find_text: "target text"
    comment: "comment content"
EOF
echo "   ✓ Template created: $WORK_DIR/edits/template.yaml"
echo

# 6. Create convenience scripts
echo "6. Creating convenience scripts..."

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

# Edit script
cat > "$WORK_DIR/edit.sh" << 'EOF'
#!/bin/bash
# Apply YAML edit configuration
if [ $# -lt 1 ]; then
    echo "Usage: $0 <yaml_config_file>"
    echo "Example: $0 .claude-work/edits/corrections.yaml"
    echo "         $0 edits/corrections.yaml  # Auto-complete path"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

YAML_FILE="$1"

# Smart path handling: auto-complete relative paths
if [ ! -f "$YAML_FILE" ]; then
    BASENAME_YAML=$(basename "$YAML_FILE")
    if [ -f "$SCRIPT_DIR/edits/$BASENAME_YAML" ]; then
        echo "Note: Auto-resolving path '$YAML_FILE' to '$SCRIPT_DIR/edits/$BASENAME_YAML'"
        YAML_FILE="$SCRIPT_DIR/edits/$BASENAME_YAML"
    else
        echo "Error: Cannot find config file: $YAML_FILE"
        echo "Please use full path: .claude-work/edits/xxx.yaml"
        exit 1
    fi
fi

python3 "$SCRIPT_DIR/apply_edits.py" "$YAML_FILE" "$SCRIPT_DIR"
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

# Complete workflow script
cat > "$WORK_DIR/workflow.sh" << 'EOF'
#!/bin/bash
# Complete Word document editing workflow
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

BASENAME=$(basename "$DOCX_FILE" .docx)
OUTPUT_FILE="${BASENAME}_revised.docx"

echo "=========================================="
echo "Word Document Editing Workflow"
echo "=========================================="
echo

echo "Document: $DOCX_FILE"
echo "Config: $YAML_FILE"
echo "Output: $OUTPUT_FILE"
echo

# 1. Backup
echo "1. Backing up original document..."
cp "$DOCX_FILE" "$SCRIPT_DIR/backups/${BASENAME}_$(date +%Y%m%d_%H%M%S).docx"
echo "   ✓ Backed up"
echo

# 2. Unpack
echo "2. Unpacking document..."
bash "$SCRIPT_DIR/unpack.sh" "$DOCX_FILE" "$SCRIPT_DIR/unpacked"
echo

# 3. Apply edits
echo "3. Applying edits..."
bash "$SCRIPT_DIR/edit.sh" "$YAML_FILE"
echo

# 4. Pack
echo "4. Packing document..."
bash "$SCRIPT_DIR/pack.sh" "$SCRIPT_DIR/unpacked" "$OUTPUT_FILE"
echo

echo "=========================================="
echo "✓ Complete! Output file: $OUTPUT_FILE"
echo "=========================================="
EOF

chmod +x "$WORK_DIR"/*.sh
echo "   ✓ Convenience scripts created:"
echo "     - env.sh       (environment variables)"
echo "     - unpack.sh    (unpack document)"
echo "     - edit.sh      (apply edits)"
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
├── unpacked/          # Unpacked Word documents
├── backups/           # Automatic backups
├── logs/              # Operation logs
├── apply_edits.py     # Editing tool
├── *.sh               # Convenience scripts
└── README.md          # This file
```

## Quick Start

### Method 1: One-Step Workflow (Recommended)

```bash
# 1. Create edit configuration (based on template)
cp .claude-work/edits/template.yaml .claude-work/edits/my_corrections.yaml
# Edit my_corrections.yaml

# 2. Execute complete workflow in one step
./.claude-work/workflow.sh document.docx .claude-work/edits/my_corrections.yaml
```

### Method 2: Step-by-Step Execution

```bash
# 1. Unpack
./.claude-work/unpack.sh document.docx

# 2. Edit (modify YAML configuration)
vim .claude-work/edits/corrections.yaml

# 3. Apply edits
./.claude-work/edit.sh .claude-work/edits/corrections.yaml

# 4. Pack
./.claude-work/pack.sh .claude-work/unpacked document_revised.docx
```

## YAML Configuration Guide

See detailed examples in `edits/template.yaml`.

Supported edit types:
- `replace_partial`: Partial replacement (recommended for corrections)
- `replace_full`: Full replacement
- `insert`: Insert text
- `delete`: Delete text
- `comment`: Add comment

## Features

- ✅ Automatic backup of original documents
- ✅ Uses Word Track Changes mode
- ✅ Isolated working environment (virtual environment)
- ✅ Temporary files don't pollute project directory
- ✅ Already added to .gitignore

## Important Notes

1. Documents are automatically backed up to `backups/` directory before editing
2. All modifications are marked using Word Track Changes mode
3. Do not manually modify files in `unpacked/` directory
4. This directory is automatically added to `.gitignore`
EOF
echo "   ✓ README.md created"
echo

# 8. Add to .gitignore
if [ -f ".gitignore" ]; then
    if ! grep -q "^.claude-work" ".gitignore" 2>/dev/null; then
        echo ".claude-work/" >> ".gitignore"
        echo "8. ✓ Added to .gitignore"
    else
        echo "8. .gitignore already contains .claude-work"
    fi
else
    echo ".claude-work/" > ".gitignore"
    echo "8. ✓ Created .gitignore"
fi
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
