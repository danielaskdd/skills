# Document Audit - Algorithm Reference

This document provides implementation details and code examples for the document audit skill.

## 1. Automatic Numbering Extraction (Aspose.Words)

The key to accurate document parsing is extracting automatic numbering labels from Word documents.

### Critical: Call update_list_labels() First

```python
import aspose.words as aw

doc = aw.Document("document.docx")

# CRITICAL: Must call this to get rendered numbering
doc.update_list_labels()

for para in doc.get_child_nodes(aw.NodeType.PARAGRAPH, True):
    para = para.as_paragraph()

    # Get the rendered label (e.g., "1.1", "Chapter 1", "a)")
    label = para.list_label.label_string if para.list_label else ""

    text = para.get_text().strip()
    full_text = f"{label} {text}" if label else text

    print(full_text)
```

### Why This Matters

Without `update_list_labels()`:
- `list_label.label_string` returns empty string
- Auto-numbered headings lose their numbers
- Document structure is lost

With `update_list_labels()`:
- Returns exact numbering as displayed in Word
- Supports multi-level lists (1.1.1, 1.1.2, etc.)
- Handles various numbering formats (Arabic, Roman, alphabetic)

## 2. Heading Detection and Hierarchy

### Outline Level Detection

```python
def is_heading(paragraph):
    """Check if paragraph is a heading based on outline level."""
    outline_level = paragraph.paragraph_format.outline_level
    return outline_level != aw.OutlineLevel.BODY_TEXT

def get_heading_level(paragraph):
    """Get numeric heading level (0-8, where 0 is Heading 1)."""
    level = paragraph.paragraph_format.outline_level
    if level == aw.OutlineLevel.BODY_TEXT:
        return None
    return int(level)
```

### Building Heading Hierarchy

```python
def build_heading_stack(current_stack, new_heading, level):
    """
    Maintain a stack of parent headings for context.

    Example:
    - "Chapter 1" (level 0) → stack: ["Chapter 1"]
    - "1.1 Section" (level 1) → stack: ["Chapter 1", "1.1 Section"]
    - "1.2 Section" (level 1) → stack: ["Chapter 1", "1.2 Section"]
    - "Chapter 2" (level 0) → stack: ["Chapter 2"]
    """
    # Truncate stack to current level
    new_stack = current_stack[:level]
    new_stack.append(new_heading)
    return new_stack
```

## 3. Table to JSON Conversion

### Basic Table Extraction

```python
def table_to_json(table):
    """Convert Word table to 2D list."""
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.as_row().cells:
            # Remove control character (cell marker)
            text = cell.get_text().strip().replace('\x07', '')
            cells.append(text)
        rows.append(cells)
    return rows
```

### Structured Table (with headers)

```python
def table_to_dict_list(table):
    """Convert table to list of dicts using first row as headers."""
    rows = table_to_json(table)
    if len(rows) < 2:
        return rows  # Not enough rows for header + data

    headers = rows[0]
    data = []
    for row in rows[1:]:
        record = {}
        for i, cell in enumerate(row):
            header = headers[i] if i < len(headers) else f"col_{i}"
            record[header] = cell
        data.append(record)
    return data
```

## 4. Block Splitting Strategy

### Split Points

1. **Headings**: Each heading starts a new block
2. **Tables**: Each table is an independent block
3. **Page Breaks**: Optionally split on page breaks

### Block Context Preservation

```python
def create_block(heading, content, block_type, parent_stack):
    """Create a block with full context."""
    return {
        "uuid": str(uuid.uuid4()),
        "heading": heading,
        "content": content,
        "type": block_type,  # "text" or "table"
        "parent_headings": list(parent_stack),
        "context": " > ".join(parent_stack)  # For display
    }
```

## 5. LLM Prompt Construction

### Prompt Template

```python
AUDIT_PROMPT = """You are a professional document auditor.

## Context
Section: {heading}
Parent Hierarchy: {context}

## Content to Audit
{content}

## Audit Rules
{rules_text}

## Instructions
1. Check if this content violates any rules
2. For each violation:
   - Identify the rule ID violated
   - Quote the problematic text
   - Explain why it's a violation
   - Suggest a correction

## Output Format
Return JSON:
{
  "is_violation": true/false,
  "violations": [
    {
      "rule_id": "R001",
      "issue_type": "category",
      "violation_text": "quoted text",
      "violation_reason": "explanation",
      "suggestion": "correction"
    }
  ]
}
"""
```

### Batching Strategy

For large documents, batch multiple blocks per API call:

```python
def batch_blocks(blocks, max_tokens=4000):
    """Group blocks to fit within token limit."""
    batches = []
    current_batch = []
    current_tokens = 0

    for block in blocks:
        block_tokens = estimate_tokens(block['content'])
        if current_tokens + block_tokens > max_tokens:
            batches.append(current_batch)
            current_batch = [block]
            current_tokens = block_tokens
        else:
            current_batch.append(block)
            current_tokens += block_tokens

    if current_batch:
        batches.append(current_batch)

    return batches
```

## 6. Report Generation

### Statistics Calculation

```python
def calculate_statistics(manifest):
    """Calculate audit statistics from manifest."""
    stats = {
        "total_blocks": len(manifest),
        "violation_count": 0,
        "by_severity": Counter(),
        "by_category": Counter(),
        "by_rule": Counter()
    }

    for entry in manifest:
        if entry.get("is_violation"):
            stats["violation_count"] += 1
            for v in entry.get("violations", []):
                stats["by_severity"][determine_severity(v)] += 1
                stats["by_category"][v.get("issue_type", "other")] += 1
                stats["by_rule"][v.get("rule_id", "unknown")] += 1

    return stats
```

### Risk Score Calculation

```python
def calculate_risk_score(stats):
    """Calculate overall document risk score (0-100)."""
    weights = {"high": 10, "medium": 3, "low": 1}

    total_weight = sum(
        count * weights.get(severity, 1)
        for severity, count in stats["by_severity"].items()
    )

    max_possible = stats["total_blocks"] * 10
    risk_score = min(100, (total_weight / max_possible) * 100) if max_possible > 0 else 0

    return round(risk_score, 1)
```

## 7. Error Handling

### Common Issues and Solutions

```python
# 1. Empty paragraphs
if not text.strip():
    continue  # Skip empty paragraphs

# 2. Control characters in table cells
text = text.replace('\x07', '')  # Remove cell marker
text = text.replace('\x0b', '')  # Remove vertical tab

# 3. LLM response parsing
try:
    result = json.loads(response_text)
except json.JSONDecodeError:
    # Try to extract JSON from markdown code block
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0]
        result = json.loads(json_str)

# 4. Rate limiting
import time
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(5))
def call_llm_with_retry(prompt):
    return call_llm(prompt)
```

## 8. Performance Optimization

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def audit_blocks_parallel(blocks, rules, max_workers=4):
    """Process blocks in parallel with rate limiting."""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, block in enumerate(blocks):
            # Stagger submissions to avoid rate limits
            time.sleep(0.2)
            future = executor.submit(audit_block, block, rules)
            futures[future] = block["uuid"]

        for future in as_completed(futures):
            uuid = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error auditing {uuid}: {e}")

    return results
```

### Caching

```python
import hashlib
import json
from pathlib import Path

def get_cache_key(block, rules):
    """Generate cache key for block+rules combination."""
    content = json.dumps({
        "content": block["content"],
        "rules": [r["id"] for r in rules]
    }, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()

def check_cache(cache_dir, cache_key):
    """Check if result is cached."""
    cache_file = Path(cache_dir) / f"{cache_key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    return None
```

## 9. Validation Functions

### Rule Validation

```python
def validate_rules(rules):
    """Validate rule structure and consistency."""
    errors = []
    rule_ids = set()

    for i, rule in enumerate(rules):
        # Check required fields
        for field in ["id", "description", "severity", "category"]:
            if field not in rule:
                errors.append(f"Rule {i}: missing '{field}'")

        # Check duplicate IDs
        if rule.get("id") in rule_ids:
            errors.append(f"Duplicate rule ID: {rule['id']}")
        rule_ids.add(rule.get("id"))

        # Check severity values
        if rule.get("severity") not in ["high", "medium", "low"]:
            errors.append(f"Rule {rule['id']}: invalid severity")

    return errors
```

### Block Validation

```python
def validate_block(block):
    """Validate block structure."""
    required = ["uuid", "heading", "content", "type"]
    for field in required:
        if field not in block:
            return False, f"Missing field: {field}"

    if block["type"] not in ["text", "table"]:
        return False, f"Invalid type: {block['type']}"

    return True, None
```
