# python-docx Usage Guide for Document Analysis

## Overview

The `python-docx` library is included in the virtual environment for **document analysis and verification**. It provides a high-level, Pythonic API for reading Word documents.

**Key Use Cases:**
1. 🔍 Understanding document structure before editing
2. ✅ Verifying edits were applied correctly
3. 📊 Generating analysis reports
4. 🎯 Finding precise locations for YAML targeting

**Important**: Use python-docx for **reading and analysis only**. For editing with tracked changes, use the YAML workflow.

## Quick Start

```bash
# Activate the project's virtual environment
source .claude-work/venv/bin/activate

# Use python-docx in a Python script or interactive session
python3
>>> from docx import Document
>>> doc = Document('document.docx')
>>> print(f"Total paragraphs: {len(doc.paragraphs)}")
```

## Common Analysis Tasks

### 1. Document Structure Overview

```python
from docx import Document

doc = Document('document.docx')

# Basic structure
print(f"📄 Document Structure:")
print(f"   Paragraphs: {len(doc.paragraphs)}")
print(f"   Tables: {len(doc.tables)}")
print(f"   Sections: {len(doc.sections)}")
print(f"   Styles: {len(doc.styles)}")

# Detailed paragraph analysis
list_items = sum(1 for p in doc.paragraphs if 'List' in p.style.name)
headings = sum(1 for p in doc.paragraphs if p.style.name.startswith('Heading'))
print(f"   List items: {list_items}")
print(f"   Headings: {headings}")
```

### 2. Finding Text and Context

```python
from docx import Document

doc = Document('document.docx')

# Find all occurrences with context
search_term = "错误文本"

print(f"🔍 Searching for: '{search_term}'")
for i, para in enumerate(doc.paragraphs):
    if search_term in para.text:
        print(f"\n📍 Occurrence at paragraph {i}:")
        print(f"   Style: {para.style.name}")
        print(f"   Text: {para.text[:100]}...")

        # Show context (previous and next paragraphs)
        if i > 0:
            print(f"   [Before]: {doc.paragraphs[i-1].text[:50]}...")
        if i < len(doc.paragraphs) - 1:
            print(f"   [After]: {doc.paragraphs[i+1].text[:50]}...")
```

### 3. Table Analysis

```python
from docx import Document

doc = Document('document.docx')

print(f"📊 Table Analysis:")
for table_idx, table in enumerate(doc.tables):
    print(f"\nTable {table_idx + 1}:")
    print(f"   Rows: {len(table.rows)}")
    print(f"   Columns: {len(table.columns)}")

    # Show first row (often headers)
    first_row = table.rows[0]
    headers = [cell.text for cell in first_row.cells]
    print(f"   Headers: {headers}")

    # Search in table
    search_term = "目标文本"
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            if search_term in cell.text:
                print(f"   Found '{search_term}' at Row {row_idx}, Col {col_idx}")
```

### 4. Style Analysis

```python
from docx import Document
from collections import Counter

doc = Document('document.docx')

# Analyze styles used
style_counts = Counter([p.style.name for p in doc.paragraphs])

print("📝 Style Usage:")
for style, count in style_counts.most_common(10):
    print(f"   {style}: {count} times")

# Find all headings
print("\n📑 Document Outline:")
for para in doc.paragraphs:
    if para.style.name.startswith('Heading'):
        level = para.style.name.replace('Heading', '')
        indent = "  " * (int(level) if level.isdigit() else 0)
        print(f"{indent}{para.text}")
```

### 5. Text Formatting Analysis

```python
from docx import Document

doc = Document('document.docx')

print("🎨 Formatting Analysis:")

# Find bold text
bold_texts = []
for para in doc.paragraphs:
    for run in para.runs:
        if run.bold:
            bold_texts.append(run.text)

print(f"Bold text occurrences: {len(bold_texts)}")
for text in bold_texts[:5]:  # Show first 5
    print(f"   • {text}")

# Find italic text
italic_texts = []
for para in doc.paragraphs:
    for run in para.runs:
        if run.italic:
            italic_texts.append(run.text)

print(f"\nItalic text occurrences: {len(italic_texts)}")

# Find specific font
print(f"\nFont usage:")
font_counts = Counter()
for para in doc.paragraphs:
    for run in para.runs:
        if run.font.name:
            font_counts[run.font.name] += 1

for font, count in font_counts.most_common(5):
    print(f"   {font}: {count} runs")
```

## Pre-Edit Analysis Workflow

Before creating YAML configuration, analyze the document to understand its structure:

```python
from docx import Document

doc = Document('original.docx')

# Step 1: Find all errors to fix
errors = [
    "recieve",
    "seperate",
    "occured",
]

print("🔍 Error Analysis:")
for error in errors:
    occurrences = []
    for i, para in enumerate(doc.paragraphs):
        if error in para.text:
            occurrences.append({
                'para_idx': i,
                'text': para.text,
                'style': para.style.name,
            })

    print(f"\n'{error}' found {len(occurrences)} time(s):")
    for occ in occurrences:
        print(f"   Paragraph {occ['para_idx']} ({occ['style']})")
        print(f"   {occ['text'][:80]}...")

# Step 2: Check if same text appears in tables
print("\n📊 Checking tables...")
for table_idx, table in enumerate(doc.tables):
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            for error in errors:
                if error in cell.text:
                    print(f"   '{error}' in Table {table_idx}, Row {row_idx}, Col {col_idx}")

# Step 3: Generate YAML targeting info
print("\n📝 YAML Configuration Suggestions:")
print("""
Use these findings to create accurate YAML:
- Use full sentence as find_text for unique matching
- Include enough context to uniquely identify the location
- For table cells, use surrounding context
""")
```

## Post-Edit Verification

After applying YAML edits, verify the changes:

```python
from docx import Document

# Define expected changes
expected_changes = [
    {"old": "recieve", "new": "receive"},
    {"old": "seperate", "new": "separate"},
    {"old": "occured", "new": "occurred"},
]

# Load revised document
doc = Document('document_revised.docx')

print("✅ Verification Report:")
all_text = '\n'.join([p.text for p in doc.paragraphs])

# Also check tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            all_text += '\n' + cell.text

for change in expected_changes:
    old_found = change["old"] in all_text
    new_found = change["new"] in all_text

    if new_found and not old_found:
        print(f"✓ '{change['old']}' → '{change['new']}': Success")
    elif old_found:
        print(f"✗ '{change['old']}' still present: Change not applied")
    elif not new_found:
        print(f"⚠ '{change['new']}' not found: Verify manually")
    else:
        print(f"? Uncertain status for '{change['old']}' → '{change['new']}'")
```

## Investigating Specific Issues

### Issue: List Numbering Problems

```python
from docx import Document

doc = Document('document.docx')

print("📋 List Structure Analysis:")

current_list = None
list_items = []

for i, para in enumerate(doc.paragraphs):
    if 'List' in para.style.name:
        # Check numbering properties
        if para._element.pPr is not None:
            numPr = para._element.pPr.numPr
            if numPr is not None:
                ilvl = numPr.ilvl.val if numPr.ilvl is not None else 0
                numId = numPr.numId.val if numPr.numId is not None else None

                list_items.append({
                    'para_idx': i,
                    'text': para.text[:50],
                    'style': para.style.name,
                    'level': ilvl,
                    'numId': numId,
                })

# Analyze list structure
from collections import defaultdict
by_numId = defaultdict(list)
for item in list_items:
    by_numId[item['numId']].append(item)

print(f"\nFound {len(list_items)} list items in {len(by_numId)} separate lists:")
for numId, items in by_numId.items():
    print(f"\nList ID {numId}: {len(items)} items")
    for item in items[:3]:  # Show first 3
        print(f"   Level {item['level']}: {item['text']}...")
```

### Issue: Tracking Down Formatting Inconsistencies

```python
from docx import Document

doc = Document('document.docx')

print("🎯 Formatting Consistency Check:")

# Check font consistency
fonts_used = set()
for para in doc.paragraphs:
    for run in para.runs:
        if run.font.name:
            fonts_used.add(run.font.name)

print(f"Fonts used: {', '.join(sorted(fonts_used))}")

# Check font sizes
from collections import Counter
sizes = Counter()
for para in doc.paragraphs:
    for run in para.runs:
        if run.font.size:
            sizes[run.font.size] += 1

print(f"\nFont sizes:")
for size, count in sizes.most_common():
    print(f"   {size.pt}pt: {count} times")

# Find paragraphs with mixed formatting
print(f"\n⚠ Paragraphs with mixed formatting:")
for i, para in enumerate(doc.paragraphs):
    if len(para.runs) > 1:
        formats = set()
        for run in para.runs:
            formats.add((run.bold, run.italic, run.font.name))

        if len(formats) > 1:
            print(f"   Paragraph {i}: {len(formats)} different formats")
            print(f"      {para.text[:60]}...")
```

## Creating Analysis Scripts

Create reusable analysis scripts in `.claude-work/`:

```bash
# Create analysis script
cat > .claude-work/analyze.py << 'EOF'
#!/usr/bin/env python3
"""Document analysis script"""
import sys
from docx import Document

if len(sys.argv) < 2:
    print("Usage: python analyze.py document.docx")
    sys.exit(1)

doc = Document(sys.argv[1])

print("=" * 60)
print(f"Document Analysis: {sys.argv[1]}")
print("=" * 60)

print(f"\n📊 Structure:")
print(f"   Paragraphs: {len(doc.paragraphs)}")
print(f"   Tables: {len(doc.tables)}")
print(f"   Sections: {len(doc.sections)}")

# Add your custom analysis here

print("\n" + "=" * 60)
EOF

# Make it executable
chmod +x .claude-work/analyze.py

# Run it
source .claude-work/venv/bin/activate
python .claude-work/analyze.py document.docx
```

## Integration with YAML Workflow

**Complete workflow example:**

```bash
# 1. Activate environment
source .claude-work/venv/bin/activate

# 2. Analyze document
python << 'EOF'
from docx import Document
doc = Document('report.docx')

# Find all typos
typos = ["recieve", "seperate"]
for typo in typos:
    for i, p in enumerate(doc.paragraphs):
        if typo in p.text:
            print(f"Found '{typo}' at paragraph {i}")
            print(f"Context: {p.text[:80]}")
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
    description: "Fix: recieve → receive"
    find_text: "I will recieve the package"
    changes:
      - delete: "recieve"
        insert: "receive"
EOF

# 4. Apply edits
./.claude-work/workflow.sh report.docx .claude-work/edits/corrections.yaml

# 5. Verify
python << 'EOF'
from docx import Document
doc = Document('report_corrected.docx')
text = '\n'.join(p.text for p in doc.paragraphs)
print("✓ receive found" if "receive" in text else "✗ receive not found")
print("✓ recieve gone" if "recieve" not in text else "✗ recieve still present")
EOF
```

## Best Practices

### DO ✅

- **Use for analysis before editing**: Understand structure first
- **Verify after editing**: Confirm changes were applied
- **Generate reports**: Document analysis helps debugging
- **Find precise locations**: Use to create accurate YAML
- **Check tables separately**: Tables require special attention

### DON'T ❌

- **Don't use for editing**: No tracked changes support
- **Don't modify document**: Read-only analysis
- **Don't rely on line numbers**: Paragraph indices change
- **Don't skip verification**: Always verify after editing

## Limitations of python-docx

**What python-docx CAN'T do:**

1. ❌ Create tracked changes (insertions/deletions)
2. ❌ Access revision history details
3. ❌ Modify complex OOXML structures reliably
4. ❌ Handle all Word features (some are unsupported)

**For these tasks, use:**
- **Tracked changes**: YAML workflow
- **Complex OOXML**: Direct XML manipulation (ooxml.md)
- **Revision history**: pandoc with `--track-changes=all`

## Examples Library

### Example 1: Find Duplicate Text

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

### Example 2: Extract All URLs

```python
from docx import Document
import re

doc = Document('document.docx')
url_pattern = r'https?://[^\s]+'

print("🔗 URLs found:")
for para in doc.paragraphs:
    urls = re.findall(url_pattern, para.text)
    for url in urls:
        print(f"   {url}")
```

### Example 3: Word Count by Section

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

# Last section
print(f"   {current_heading}: {word_count} words")
```

## Summary

**python-docx Role in Workflow:**

```
┌─────────────────────────────────────────────┐
│ 1. ANALYZE (python-docx)                    │
│    • Understand structure                   │
│    • Find errors                            │
│    • Identify patterns                      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ 2. PLAN (Generate YAML)                     │
│    • Create configuration                   │
│    • Define edits                           │
│    • Set targeting                          │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ 3. EDIT (YAML Workflow)                     │
│    • Apply tracked changes                  │
│    • Preserve formatting                    │
│    • Generate revised document              │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ 4. VERIFY (python-docx)                     │
│    • Check changes applied                  │
│    • Validate content                       │
│    • Generate report                        │
└─────────────────────────────────────────────┘
```

Use python-docx as your **analysis and verification tool**, not as an editing tool!
