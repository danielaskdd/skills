---
name: docx
description: "Comprehensive document creation, editing, and analysis with support for tracked changes, comments, formatting preservation, and text extraction. When Claude needs to work with professional documents (.docx files) for: (1) Creating new documents, (2) Modifying or editing content, (3) Working with tracked changes, (4) Adding comments, or any other document tasks"
license: Proprietary. LICENSE.txt has complete terms
---

# DOCX creation, editing, and analysis

## Overview

A user may ask you to create, edit, or analyze the contents of a .docx file. A .docx file is essentially a ZIP archive containing XML files and other resources that you can read or edit. You have different tools and workflows available for different tasks.

## Workflow Decision Tree

### Reading/Analyzing Content
Use "Text extraction" or "Raw XML access" sections below

### Creating New Document
Use "Creating a new Word document" workflow

### Editing Existing Document
- **Your own document + simple changes**
  Use "Basic OOXML editing" workflow

- **Someone else's document**
  Use **"Redlining workflow"** (recommended default)

- **Legal, academic, business, or government docs**
  Use **"Redlining workflow"** (required)

## Reading and analyzing content

### Text extraction
If you just need to read the text contents of a document, you should convert the document to markdown using pandoc. Pandoc provides excellent support for preserving document structure and can show tracked changes:

```bash
# Convert document to markdown with tracked changes
pandoc --track-changes=all path-to-file.docx -o output.md
# Options: --track-changes=accept/reject/all
```

### Raw XML access
You need raw XML access for: comments, complex formatting, document structure, embedded media, and metadata. For any of these features, you'll need to unpack a document and read its raw XML contents.

#### Unpacking a file
`python ooxml/scripts/unpack.py <office_file> <output_directory>`

#### Key file structures
* `word/document.xml` - Main document contents
* `word/comments.xml` - Comments referenced in document.xml
* `word/media/` - Embedded images and media files
* Tracked changes use `<w:ins>` (insertions) and `<w:del>` (deletions) tags

## Creating a new Word document

When creating a new Word document from scratch, use **docx-js**, which allows you to create Word documents using JavaScript/TypeScript.

### Workflow
1. **MANDATORY - READ ENTIRE FILE**: Read [`docx-js.md`](docx-js.md) (~500 lines) completely from start to finish. **NEVER set any range limits when reading this file.** Read the full file content for detailed syntax, critical formatting rules, and best practices before proceeding with document creation.
2. Create a JavaScript/TypeScript file using Document, Paragraph, TextRun components (You can assume all dependencies are installed, but if not, refer to the dependencies section below)
3. Export as .docx using Packer.toBuffer()

## Editing an existing Word document

**RECOMMENDED WORKFLOW**: Use the YAML-based editing workflow below. This is the preferred method for document editing as it's more maintainable, clearer, and avoids creating temporary Python scripts.

### YAML-based Editing Workflow (RECOMMENDED)

This modern workflow uses declarative YAML configuration instead of temporary Python scripts. All work is done in an isolated project directory with a Python virtual environment.

**When to use**: All document editing tasks, especially:
- Correcting typos and grammatical errors
- Making tracked changes for document review
- Batch editing multiple similar changes
- Any scenario where you would previously write temporary Python scripts

#### Quick Start

```bash
# 1. Setup environment (first time only per project)
bash /path/to/docx/skills/scripts/setup_project_env.sh

# 2. Create YAML configuration (or let Claude generate it)
cat > .claude-work/edits/corrections.yaml << 'EOF'
version: "1.0"
document:
  input: "document.docx"
  output: "document_revised.docx"
revision:
  author: "Claude"
  track_changes: true
edits:
  - type: replace_partial
    description: "Fix typo"
    find_text: "the complete sentence with error"
    changes:
      - delete: "wong"
        insert: "wrong"
EOF

# 3. Run one-command workflow
./.claude-work/workflow.sh document.docx .claude-work/edits/corrections.yaml
```

#### Detailed Workflow

**Step 1: Environment Setup** (once per project)

```bash
# In the project directory, run the setup script
DOCX_SKILLS_PATH=/path/to/docx/skills bash /path/to/docx/skills/scripts/setup_project_env.sh
```

This creates:
- `.claude-work/` - Hidden working directory
- `.claude-work/venv/` - Python virtual environment with all dependencies
- `.claude-work/edits/` - Directory for YAML configurations
- `.claude-work/edits/template.yaml` - YAML template
- Quick-access shell scripts (workflow.sh, unpack.sh, pack.sh)

**Step 2: Create YAML Configuration**

Create a YAML file in `.claude-work/edits/` defining your edits. Supported operation types:

```yaml
version: "1.0"

document:
  input: "original.docx"
  output: "revised.docx"

revision:
  author: "Claude"
  track_changes: true  # Enables Word's Track Changes
  rsid: ""            # Leave empty for auto-generation

edits:
  # Type 1: Partial replacement (RECOMMENDED for corrections)
  - type: replace_partial
    description: "Fix typo: recieve → receive"
    find_text: "I will recieve the package tomorrow"
    changes:
      - delete: "recieve"
        insert: "receive"
    line_range: [100, 200]  # Optional: narrow search scope

  # Type 2: Insert text
  - type: insert
    description: "Add missing word"
    find_text: "anchor text"
    position: before  # or 'after'
    insert: "missing text"
    line_range: [300, 400]

  # Type 3: Delete text
  - type: delete
    description: "Remove redundant text"
    find_text: "text to delete"

  # Type 4: Add comment
  - type: comment
    description: "Add review comment"
    find_text: "target text"
    comment: "Please verify this data"
```

**Step 3: Execute Editing**

```bash
# Method A: One-command workflow (recommended)
./.claude-work/workflow.sh document.docx .claude-work/edits/my_corrections.yaml

# Method B: Step by step (manual approach - only needed for advanced OOXML editing)
./.claude-work/unpack.sh document.docx
# Manually edit XML in .claude-work/unpacked/
./.claude-work/pack.sh .claude-work/unpacked document_revised.docx

# Note: For YAML-based editing, use workflow.sh (Method A) which calls apply_edits.py directly

# Note: Both scripts support path auto-completion:
./.claude-work/workflow.sh document.docx edits/my_corrections.yaml  # Also works!
```

After execution completes, the script automatically outputs a formatted edit report showing:
- Document information (input/output paths, author, track changes status)
- Detailed status for each operation (success/warning/error)
- Summary statistics (total operations, success rate)

**⚠️ Important**: After reviewing the report, the workflow is complete. Do not retry failed operations automatically - review the warnings/errors and decide whether manual intervention is needed.

#### Benefits Over Traditional Python Scripts

| Aspect | Old Method (Python Scripts) | New Method (YAML) | Improvement |
|--------|---------------------------|-------------------|-------------|
| Code volume | ~200 lines per task | ~30 lines | 85% reduction |
| Files created | 3-4 temp scripts | 1 YAML config | 75% fewer |
| Maintainability | Low | High | Easier to modify |
| Readability | Python code | Declarative config | Much clearer |
| Reusability | None | High | Works for all docs |
| Learning curve | Requires Python | Just YAML | Lower barrier |
| Environment | Ad-hoc | Isolated venv | Cleaner |

#### Tips

1. **Template available**: Copy `.claude-work/edits/template.yaml` as a starting point
2. **Line ranges**: Use `line_range: [start, end]` to narrow search when text appears multiple times
3. **Batch operations**: Include multiple edits in one YAML file - they execute sequentially
4. **Auto-backup**: Original documents are automatically backed up to `.claude-work/backups/`

#### Best Practices for `find_text`

**⚠️ CRITICAL: `find_text` Guidelines**

When creating YAML edits, **`find_text` is the most important field** for ensuring accurate replacements. Follow these guidelines:

**1. Include Sufficient Context (Recommended)**

`find_text` should include enough surrounding text to uniquely identify the location, but not too much to risk matching failures due to formatting changes.

```yaml
# ✗ TOO SHORT - May match multiple locations
- type: replace_partial
  find_text: "the error"
  changes:
    - delete: "error"
      insert: "issue"

# ✓ GOOD - Includes surrounding context
- type: replace_partial
  find_text: "We found the error in the configuration file"
  changes:
    - delete: "error"
      insert: "issue"

# ⚠️ TOO LONG - May break if text is reformatted
- type: replace_partial
  find_text: "We found the error in the configuration file that was created last week during the initial setup process"
  changes:
    - delete: "error"
      insert: "issue"
```

**Recommended context length:** 5-15 words surrounding the target text.

**2. NEVER Include Auto-Numbering**

If a document uses Word's automatic numbering feature (numbered lists, outline numbering), **DO NOT include the numbers** in `find_text` or `delete` operations.

Why? Auto-numbering is generated by Word dynamically and is not part of the actual text content. When you convert the document to markdown with pandoc or analyze with python-docx, you may see the numbers, but they don't exist in the underlying XML.

```yaml
# ✗ WRONG - Includes auto-number
- type: replace_partial
  description: "Fix item 3"
  find_text: "3. Complete the annual report"
  changes:
    - delete: "annual report"
      insert: "quarterly report"

# ✓ CORRECT - Excludes auto-number, includes context
- type: replace_partial
  description: "Fix item 3"
  find_text: "Complete the annual report by end of quarter"
  changes:
    - delete: "annual report"
      insert: "quarterly report"
```

**3. Handle Multiple Occurrences**

If the same text appears multiple times, make `find_text` more specific:

```yaml
# If "submit report" appears 3 times in the document:

# ✗ RISKY - Will replace all occurrences
- type: replace_partial
  find_text: "submit report"
  changes:
    - delete: "report"
      insert: "documentation"

# ✓ BETTER - Include context to target specific instance
- type: replace_partial
  find_text: "Please submit report to the finance department"
  changes:
    - delete: "report"
      insert: "documentation"
```

**4. Cross-Run Text (Handled Automatically)**

Text with different formatting (bold, italic, different colors) is split into separate "runs" internally. The editing tool handles this automatically - you don't need to do anything special.

```yaml
# Even if "important" is bold in the document, this works:
- type: replace_partial
  find_text: "This is an important consideration"
  changes:
    - delete: "important"
      insert: "critical"
```

**5. Real-World Examples**

```yaml
edits:
  # Example: Fix typo in a specific sentence
  - type: replace_partial
    description: "Fix 'recieve' typo in notification message"
    find_text: "You will recieve a confirmation email within 24 hours"
    changes:
      - delete: "recieve"
        insert: "receive"

  # Example: Update date in contract clause
  - type: replace_partial
    description: "Update contract termination notice period"
    find_text: "Either party may terminate this agreement with 30 days written notice"
    changes:
      - delete: "30 days"
        insert: "60 days"

  # Example: Fix term in definition section (avoiding auto-numbering)
  - type: replace_partial
    description: "Correct definition of 'Effective Date'"
    find_text: "Effective Date means the date of contract execution"
    changes:
      - delete: "contract execution"
      insert: "final signature"
```

#### Common Pitfalls

**How to verify if a document uses auto-numbering:**

```python
# Activate venv: source .claude-work/venv/bin/activate
from docx import Document

doc = Document('document.docx')
for para in doc.paragraphs:
    # Check if paragraph has numbering
    if para._element.pPr is not None:
        numPr = para._element.pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr')
        if numPr is not None:
            print(f"Auto-numbered: {para.text}")
```

**Other common issues:**

1. **Unique context**: Ensure `find_text` is unique enough to avoid false matches
   - ✗ RISKY: `find_text: "the"` (matches thousands of times)
   - ✓ SAFE: `find_text: "the system administrator"` (includes context)

2. **Cross-run formatting**: Text with different formatting creates separate "runs"
   - This is handled automatically by the YAML workflow
   - No action needed, but be aware bold/italic/underline create run boundaries

3. **Path handling**: Documents can be referenced with:
   - Absolute paths: `"/full/path/to/document.docx"` (always works)
   - Relative paths: `"document.docx"` (searches project root, YAML directory, etc.)
   - If document not found, you'll get clear error messages with search locations

#### Using python-docx for Document Analysis

The virtual environment includes `python-docx` for document structure analysis and verification. Use it to:

**1. Understand Document Structure**

```python
from docx import Document

# Activate venv first: source .claude-work/venv/bin/activate
doc = Document('document.docx')

# Analyze structure
print(f"Paragraphs: {len(doc.paragraphs)}")
print(f"Tables: {len(doc.tables)}")
print(f"Sections: {len(doc.sections)}")

# Find specific content
for i, para in enumerate(doc.paragraphs):
    if "search term" in para.text:
        print(f"Found in paragraph {i}: {para.text[:50]}...")

# Investigate list numbering
for para in doc.paragraphs:
    if para.style.name.startswith('List'):
        print(f"List item: {para.text}")
        print(f"  Style: {para.style.name}")
```

**2. Verify Edits After Applying Changes**

```python
from docx import Document

# Read the revised document
doc = Document('document_revised.docx')

# Verify changes
expected_changes = [
    ("old text", "new text"),
    ("error", "correction"),
]

for old, new in expected_changes:
    found = False
    for para in doc.paragraphs:
        if new in para.text:
            found = True
            print(f"✓ Found: '{new}'")
            break
    if not found:
        print(f"✗ Missing: '{new}'")

# Check tracked changes
for para in doc.paragraphs:
    for run in para.runs:
        # python-docx can access revision info
        if hasattr(run, '_element'):
            # Check for tracked insertions/deletions
            pass
```

**3. Generate Analysis Report**

```python
from docx import Document
from collections import Counter

doc = Document('document.docx')

# Text statistics
all_text = '\n'.join([p.text for p in doc.paragraphs])
words = all_text.split()

report = {
    'total_paragraphs': len(doc.paragraphs),
    'total_tables': len(doc.tables),
    'total_words': len(words),
    'styles_used': Counter([p.style.name for p in doc.paragraphs]),
}

print("Document Analysis Report:")
for key, value in report.items():
    print(f"  {key}: {value}")
```

**4. Pre-Edit Analysis (Recommended Workflow)**

Before generating YAML configuration:

```python
from docx import Document

doc = Document('original.docx')

# Step 1: Find all occurrences
search_term = "error text"
occurrences = []

for i, para in enumerate(doc.paragraphs):
    if search_term in para.text:
        occurrences.append({
            'paragraph_index': i,
            'text': para.text,
            'style': para.style.name,
        })

# Step 2: Generate YAML with precise targeting
print(f"Found {len(occurrences)} occurrence(s)")
for occ in occurrences:
    print(f"Paragraph {occ['paragraph_index']}: {occ['text'][:60]}...")

# Use this info to create accurate YAML with line_range or unique context
```

**5. Common Tasks**

```python
from docx import Document

doc = Document('document.docx')

# Task: Find text in tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            if "search" in cell.text:
                print(f"Found in table: {cell.text}")

# Task: Extract all headings
headings = []
for para in doc.paragraphs:
    if para.style.name.startswith('Heading'):
        headings.append({
            'level': para.style.name,
            'text': para.text,
        })

# Task: Check formatting
for para in doc.paragraphs:
    for run in para.runs:
        if run.bold:
            print(f"Bold text: {run.text}")
        if run.italic:
            print(f"Italic text: {run.text}")
```

**Best Practice: Analysis → YAML → Verification**

1. **Analyze** with python-docx to understand structure
2. **Generate** YAML based on analysis
3. **Apply** edits using YAML workflow
4. **Verify** results with python-docx

**Note**: python-docx is for analysis and verification only. For actual editing with tracked changes, use the YAML workflow.

**See [`PYTHON_DOCX_GUIDE.md`](PYTHON_DOCX_GUIDE.md) for detailed examples, analysis scripts, and comprehensive usage guide.**

## Redlining workflow for document review

This workflow allows you to plan comprehensive tracked changes using markdown before implementing them in OOXML. **CRITICAL**: For complete tracked changes, you must implement ALL changes systematically.

**Batching Strategy**: Group related changes into batches of 3-10 changes. This makes debugging manageable while maintaining efficiency. Test each batch before moving to the next.

**Principle: Minimal, Precise Edits**
When implementing tracked changes, only mark text that actually changes. Repeating unchanged text makes edits harder to review and appears unprofessional. Break replacements into: [unchanged text] + [deletion] + [insertion] + [unchanged text]. Preserve the original run's RSID for unchanged text by extracting the `<w:r>` element from the original and reusing it.

Example - Changing "30 days" to "60 days" in a sentence:
```python
# BAD - Replaces entire sentence
'<w:del><w:r><w:delText>The term is 30 days.</w:delText></w:r></w:del><w:ins><w:r><w:t>The term is 60 days.</w:t></w:r></w:ins>'

# GOOD - Only marks what changed, preserves original <w:r> for unchanged text
'<w:r w:rsidR="00AB12CD"><w:t>The term is </w:t></w:r><w:del><w:r><w:delText>30</w:delText></w:r></w:del><w:ins><w:r><w:t>60</w:t></w:r></w:ins><w:r w:rsidR="00AB12CD"><w:t> days.</w:t></w:r>'
```

### Tracked changes workflow

1. **Get markdown representation**: Convert document to markdown with tracked changes preserved:
   ```bash
   pandoc --track-changes=all path-to-file.docx -o current.md
   ```

2. **Identify and group changes**: Review the document and identify ALL changes needed, organizing them into logical batches:

   **Location methods** (for finding changes in XML):
   - Section/heading numbers (e.g., "Section 3.2", "Article IV")
   - Paragraph identifiers if numbered
   - Grep patterns with unique surrounding text
   - Document structure (e.g., "first paragraph", "signature block")
   - **DO NOT use markdown line numbers** - they don't map to XML structure

   **Batch organization** (group 3-10 related changes per batch):
   - By section: "Batch 1: Section 2 amendments", "Batch 2: Section 5 updates"
   - By type: "Batch 1: Date corrections", "Batch 2: Party name changes"
   - By complexity: Start with simple text replacements, then tackle complex structural changes
   - Sequential: "Batch 1: Pages 1-3", "Batch 2: Pages 4-6"

3. **Read documentation and unpack**:
   - **MANDATORY - READ ENTIRE FILE**: Read [`ooxml.md`](ooxml.md) (~600 lines) completely from start to finish. **NEVER set any range limits when reading this file.** Pay special attention to the "Document Library" and "Tracked Change Patterns" sections.
   - **Unpack the document**: `python ooxml/scripts/unpack.py <file.docx> <dir>`
   - **Note the suggested RSID**: The unpack script will suggest an RSID to use for your tracked changes. Copy this RSID for use in step 4b.

4. **Implement changes in batches**: Group changes logically (by section, by type, or by proximity) and implement them together in a single script. This approach:
   - Makes debugging easier (smaller batch = easier to isolate errors)
   - Allows incremental progress
   - Maintains efficiency (batch size of 3-10 changes works well)

   **Suggested batch groupings:**
   - By document section (e.g., "Section 3 changes", "Definitions", "Termination clause")
   - By change type (e.g., "Date changes", "Party name updates", "Legal term replacements")
   - By proximity (e.g., "Changes on pages 1-3", "Changes in first half of document")

   For each batch of related changes:

   **a. Map text to XML**: Grep for text in `word/document.xml` to verify how text is split across `<w:r>` elements.

   **b. Create and run script**: Use `get_node` to find nodes, implement changes, then `doc.save()`. See **"Document Library"** section in ooxml.md for patterns.

   **Note**: Always grep `word/document.xml` immediately before writing a script to get current line numbers and verify text content. Line numbers change after each script run.

5. **Pack the document**: After all batches are complete, convert the unpacked directory back to .docx:
   ```bash
   python ooxml/scripts/pack.py unpacked reviewed-document.docx
   ```

6. **Final verification**: Do a comprehensive check of the complete document:
   - Convert final document to markdown:
     ```bash
     pandoc --track-changes=all reviewed-document.docx -o verification.md
     ```
   - Verify ALL changes were applied correctly:
     ```bash
     grep "original phrase" verification.md  # Should NOT find it
     grep "replacement phrase" verification.md  # Should find it
     ```
   - Check that no unintended changes were introduced


## Converting Documents to Images

To visually analyze Word documents, convert them to images using a two-step process:

1. **Convert DOCX to PDF**:
   ```bash
   soffice --headless --convert-to pdf document.docx
   ```

2. **Convert PDF pages to JPEG images**:
   ```bash
   pdftoppm -jpeg -r 150 document.pdf page
   ```
   This creates files like `page-1.jpg`, `page-2.jpg`, etc.

Options:
- `-r 150`: Sets resolution to 150 DPI (adjust for quality/size balance)
- `-jpeg`: Output JPEG format (use `-png` for PNG if preferred)
- `-f N`: First page to convert (e.g., `-f 2` starts from page 2)
- `-l N`: Last page to convert (e.g., `-l 5` stops at page 5)
- `page`: Prefix for output files

Example for specific range:
```bash
pdftoppm -jpeg -r 150 -f 2 -l 5 document.pdf page  # Converts only pages 2-5
```

## Code Style Guidelines
**IMPORTANT**: When generating code for DOCX operations:
- Write concise code
- Avoid verbose variable names and redundant operations
- Avoid unnecessary print statements

## Dependencies

### System Dependencies

Required system tools (install if not available):

- **pandoc**: `sudo apt-get install pandoc` (for text extraction and markdown conversion)
- **LibreOffice**: `sudo apt-get install libreoffice` (for PDF conversion)
- **Poppler**: `sudo apt-get install poppler-utils` (for pdftoppm to convert PDF to images)

### Node.js Dependencies

- **docx**: `npm install -g docx` (for creating new documents with docx-js)

### Python Dependencies

When using the YAML workflow, all Python dependencies are **automatically installed** in the project's virtual environment (`.claude-work/venv/`):

- **aspose-words**: High-performance document editing library (commercial, evaluation version available)
- **PyYAML**: YAML configuration file parsing
- **python-docx**: High-level document analysis and verification

**Manual installation** (only needed outside YAML workflow):
```bash
pip install aspose-words PyYAML python-docx
```

**Note**: The YAML workflow's `setup_project_env.sh` script automatically creates a virtual environment and installs all Python dependencies, so manual installation is typically not needed.

**About Aspose.Words**: The document editing tool uses Aspose.Words for Python, which is a commercial library. The evaluation version works fully but adds a watermark to output documents. For production use without watermark, an Aspose.Words license is required (~$999/year for developer license).
