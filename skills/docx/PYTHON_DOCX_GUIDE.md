# python-docx Analysis Guide

## Overview

The `python-docx` library is included in the virtual environment for **document analysis**. Use it to understand document structure before creating YAML edits.

**Key Use Cases:**
- 🔍 Finding text and understanding context
- 📊 Analyzing document structure (paragraphs, tables, styles)
- 🎯 Locating precise targets for YAML configuration

**Important**: Use python-docx for **analysis only**. For editing with tracked changes, use the YAML workflow.

## Quick Start

```bash
# Activate the project's virtual environment
source .claude-work/venv/bin/activate

# Use python-docx interactively
python3
>>> from docx import Document
>>> doc = Document('document.docx')
>>> print(f"Total paragraphs: {len(doc.paragraphs)}")
```

## Essential Analysis Examples

### 1. Find Text and Context

```python
from docx import Document

doc = Document('document.docx')
search_term = "error text"

print(f"🔍 Searching for: '{search_term}'")
for i, para in enumerate(doc.paragraphs):
    if search_term in para.text:
        print(f"\n📍 Found at paragraph {i}:")
        print(f"   Text: {para.text[:80]}...")
        
        # Show context
        if i > 0:
            print(f"   [Before]: {doc.paragraphs[i-1].text[:50]}...")
        if i < len(doc.paragraphs) - 1:
            print(f"   [After]: {doc.paragraphs[i+1].text[:50]}...")
```

### 2. Document Structure Overview

```python
from docx import Document
from collections import Counter

doc = Document('document.docx')

# Basic structure
print(f"📄 Document Structure:")
print(f"   Paragraphs: {len(doc.paragraphs)}")
print(f"   Tables: {len(doc.tables)}")
print(f"   Sections: {len(doc.sections)}")

# Style usage
styles = Counter([p.style.name for p in doc.paragraphs])
print(f"\n📝 Top 5 styles used:")
for style, count in styles.most_common(5):
    print(f"   {style}: {count}")

# Extract outline
print(f"\n📑 Document Outline:")
for para in doc.paragraphs:
    if para.style.name.startswith('Heading'):
        level = para.style.name.replace('Heading', '').strip()
        indent = "  " * (int(level) if level.isdigit() else 0)
        print(f"{indent}{para.text}")
```

### 3. Table Analysis

```python
from docx import Document

doc = Document('document.docx')

print(f"📊 Table Analysis:")
for table_idx, table in enumerate(doc.tables):
    print(f"\nTable {table_idx + 1}: {len(table.rows)} rows × {len(table.columns)} cols")
    
    # Show headers (first row)
    headers = [cell.text for cell in table.rows[0].cells]
    print(f"   Headers: {headers}")
    
    # Search within table
    search_term = "target text"
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            if search_term in cell.text:
                print(f"   Found at Row {row_idx}, Col {col_idx}: {cell.text[:40]}...")
```

### 4. Check for Auto-Numbering

```python
from docx import Document

doc = Document('document.docx')

print("📋 Checking for auto-numbered lists:")
auto_numbered = []

for i, para in enumerate(doc.paragraphs):
    if para._element.pPr is not None:
        numPr = para._element.pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr')
        if numPr is not None:
            auto_numbered.append(i)
            print(f"   Paragraph {i}: {para.text[:60]}...")

if auto_numbered:
    print(f"\n⚠️  Found {len(auto_numbered)} auto-numbered paragraphs")
    print("   DO NOT include numbers in YAML find_text!")
else:
    print("   No auto-numbering detected")
```

### 5. Pre-Edit Analysis

Use this before creating YAML configuration:

```python
from docx import Document

doc = Document('original.docx')

# Find all errors to fix
errors_to_fix = [
    "recieve",
    "seperate",
    "occured",
]

print("🔍 Pre-Edit Analysis:")
for error in errors_to_fix:
    occurrences = []
    
    # Check paragraphs
    for i, para in enumerate(doc.paragraphs):
        if error in para.text:
            occurrences.append({
                'location': f'Paragraph {i}',
                'text': para.text[:80],
            })
    
    # Check tables
    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                if error in cell.text:
                    occurrences.append({
                        'location': f'Table {t_idx}, Row {r_idx}, Col {c_idx}',
                        'text': cell.text[:80],
                    })
    
    if occurrences:
        print(f"\n'{error}' - {len(occurrences)} occurrence(s):")
        for occ in occurrences:
            print(f"   {occ['location']}: {occ['text']}...")
```

## Quick Analysis Script

Create a reusable analysis script:

```bash
cat > .claude-work/analyze.py << 'EOF'
#!/usr/bin/env python3
"""Quick document analysis"""
import sys
from docx import Document

if len(sys.argv) < 2:
    print("Usage: python analyze.py document.docx [search_term]")
    sys.exit(1)

doc = Document(sys.argv[1])

print("=" * 60)
print(f"Document: {sys.argv[1]}")
print("=" * 60)
print(f"\nStructure:")
print(f"  Paragraphs: {len(doc.paragraphs)}")
print(f"  Tables: {len(doc.tables)}")

if len(sys.argv) > 2:
    term = sys.argv[2]
    print(f"\nSearching for '{term}':")
    for i, p in enumerate(doc.paragraphs):
        if term in p.text:
            print(f"  Paragraph {i}: {p.text[:60]}...")
EOF

chmod +x .claude-work/analyze.py

# Usage:
# source .claude-work/venv/bin/activate
# python .claude-work/analyze.py document.docx "error text"
```

## Common Tasks

### Find Duplicates

```python
from docx import Document
from collections import Counter

doc = Document('document.docx')
texts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
duplicates = {text: count for text, count in Counter(texts).items() if count > 1}

print("🔄 Duplicate paragraphs:")
for text, count in duplicates.items():
    print(f"   {count}x: {text[:60]}...")
```

### Word Count by Section

```python
from docx import Document

doc = Document('document.docx')

print("📊 Word count by heading:")
current_heading = "Introduction"
word_count = 0

for para in doc.paragraphs:
    if para.style.name.startswith('Heading'):
        if word_count > 0:
            print(f"   {current_heading}: {word_count} words")
        current_heading = para.text
        word_count = 0
    else:
        word_count += len(para.text.split())

print(f"   {current_heading}: {word_count} words")
```

## Integration with YAML Workflow

Complete workflow:

```bash
# 1. Activate environment
source .claude-work/venv/bin/activate

# 2. Analyze document
python << 'EOF'
from docx import Document
doc = Document('report.docx')

# Find errors
for i, p in enumerate(doc.paragraphs):
    if "recieve" in p.text:
        print(f"Found 'recieve' at paragraph {i}")
        print(f"Context: {p.text}")
EOF

# 3. Create YAML based on analysis
cat > .claude-work/edits/corrections.yaml << 'EOF'
version: "1.0"
document:
  input: "report.docx"
  output: "report_corrected.docx"
revision:
  author: "Claude"
  track_changes: true
edits:
  - type: replace_partial
    description: "Fix typo: recieve → receive"
    find_text: "I will recieve the package tomorrow"
    changes:
      - delete: "recieve"
        insert: "receive"
EOF

# 4. Apply edits (automatic report generated)
./.claude-work/workflow.sh report.docx .claude-work/edits/corrections.yaml
```

## Summary

**Use python-docx for analysis before editing:**

1. **Analyze** → Find errors, understand structure
2. **Plan** → Create accurate YAML configuration
3. **Edit** → Use YAML workflow (automatic report)

The YAML workflow now provides automatic reporting, so python-docx is primarily for pre-edit analysis.
