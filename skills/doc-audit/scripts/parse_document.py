#!/usr/bin/env python3
"""
ABOUTME: Parses DOCX documents into text blocks using Aspose.Words
ABOUTME: Extracts automatic numbering, splits by headings, converts tables to JSON
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import aspose.words as aw
except ImportError:
    print("Error: aspose-words not installed. Run: pip install aspose-words", file=sys.stderr)
    sys.exit(1)


def generate_content_uuid(heading: str, content: str) -> str:
    """
    Generate deterministic UUID from heading and content using SHA-256 hash.

    Args:
        heading: Block heading text
        content: Block content (text or JSON string for tables)

    Returns:
        32-character hexadecimal string (deterministic UUID)
    """
    # Combine heading and content for hashing
    if isinstance(content, list):
        # For tables, convert to JSON string for consistent hashing
        content_str = json.dumps(content, ensure_ascii=False, sort_keys=True)
    else:
        content_str = str(content)
    
    combined = f"{heading}|{content_str}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:32]


def extract_audit_blocks(file_path: str) -> list:
    """
    Extract text blocks from a DOCX file for auditing.

    Uses Aspose.Words to:
    1. Capture automatic numbering (list labels)
    2. Split document by headings
    3. Convert tables to JSON

    Args:
        file_path: Path to the DOCX file

    Returns:
        List of block dictionaries with heading, content, type, and metadata
    """
    doc = aw.Document(file_path)

    # CRITICAL: Update list labels to get rendered numbering
    doc.update_list_labels()

    blocks = []
    current_heading = "Preface/Uncategorized"
    current_heading_stack = []  # Track heading hierarchy
    current_content = []

    # Get all nodes from document body
    for section in doc.sections:
        body = section.as_section().body
        nodes = body.get_child_nodes(aw.NodeType.ANY, False)

        for node in nodes:
            if node.node_type == aw.NodeType.PARAGRAPH:
                para = node.as_paragraph()
                text = para.get_text().strip()

                if not text:
                    continue

                # Get automatic numbering label (e.g., "1.1", "Chapter 1")
                label = ""
                if para.list_label:
                    label = para.list_label.label_string or ""

                full_text = f"{label} {text}".strip() if label else text

                # Check if this is a heading (outline level is not body text)
                outline_level = para.paragraph_format.outline_level
                is_heading = outline_level != aw.OutlineLevel.BODY_TEXT

                if is_heading:
                    # Save previous block if it has content
                    if current_content:
                        content_text = "\n".join(current_content)
                        blocks.append({
                            "uuid": generate_content_uuid(current_heading, content_text),
                            "heading": current_heading,
                            "content": content_text,
                            "type": "text",
                            "parent_headings": list(current_heading_stack)
                        })
                        current_content = []

                    # Update heading stack based on outline level
                    level = int(outline_level) if outline_level != aw.OutlineLevel.BODY_TEXT else 0
                    # Truncate stack to current level
                    current_heading_stack = current_heading_stack[:level]
                    current_heading_stack.append(full_text)
                    current_heading = full_text
                else:
                    current_content.append(full_text)

            elif node.node_type == aw.NodeType.TABLE:
                # Save any pending text content
                if current_content:
                    content_text = "\n".join(current_content)
                    blocks.append({
                        "uuid": generate_content_uuid(current_heading, content_text),
                        "heading": current_heading,
                        "content": content_text,
                        "type": "text",
                        "parent_headings": list(current_heading_stack)
                    })
                    current_content = []

                # Convert table to JSON structure
                table = node.as_table()
                table_data = []

                for row in table.rows:
                    row_data = []
                    for cell in row.as_row().cells:
                        # Get cell text, remove control characters
                        cell_text = cell.get_text().strip().replace('\x07', '')
                        row_data.append(cell_text)
                    table_data.append(row_data)

                table_heading = f"Table (under: {current_heading})"
                blocks.append({
                    "uuid": generate_content_uuid(table_heading, table_data),
                    "heading": table_heading,
                    "content": table_data,
                    "type": "table",
                    "parent_headings": list(current_heading_stack)
                })

    # Don't forget the last block
    if current_content:
        content_text = "\n".join(current_content)
        blocks.append({
            "uuid": generate_content_uuid(current_heading, content_text),
            "heading": current_heading,
            "content": content_text,
            "type": "text",
            "parent_headings": list(current_heading_stack)
        })

    return blocks


def format_table_for_display(table_data: list) -> str:
    """
    Format table data as readable text for display.

    Args:
        table_data: 2D list of cell values

    Returns:
        Formatted string representation
    """
    if not table_data:
        return "(empty table)"

    # Calculate column widths
    col_widths = []
    for col_idx in range(len(table_data[0]) if table_data else 0):
        max_width = 0
        for row in table_data:
            if col_idx < len(row):
                max_width = max(max_width, len(str(row[col_idx])))
        col_widths.append(min(max_width, 40))  # Cap at 40 chars

    lines = []
    for row in table_data:
        cells = []
        for i, cell in enumerate(row):
            width = col_widths[i] if i < len(col_widths) else 20
            cells.append(str(cell)[:width].ljust(width))
        lines.append(" | ".join(cells))

    return "\n".join(lines)


def save_blocks_jsonl(blocks: list, output_path: str):
    """
    Save blocks to JSONL format (one JSON object per line).
    Also removes existing manifest.jsonl to ensure clean resume state.

    Args:
        blocks: List of block dictionaries
        output_path: Path to output file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for block in blocks:
            f.write(json.dumps(block, ensure_ascii=False) + '\n')
    
    # Clean up old manifest.jsonl to prevent UUID mismatch in resume mode
    manifest_path = Path(output_path).parent / "manifest.jsonl"
    if manifest_path.exists():
        manifest_path.unlink()
        print(f"Removed existing manifest: {manifest_path}")


def save_blocks_json(blocks: list, output_path: str):
    """
    Save blocks to regular JSON format.
    Also removes existing manifest.jsonl to ensure clean resume state.

    Args:
        blocks: List of block dictionaries
        output_path: Path to output file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total_blocks": len(blocks),
            "blocks": blocks
        }, f, indent=2, ensure_ascii=False)
    
    # Clean up old manifest.jsonl to prevent UUID mismatch in resume mode
    manifest_path = Path(output_path).parent / "manifest.jsonl"
    if manifest_path.exists():
        manifest_path.unlink()
        print(f"Removed existing manifest: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse DOCX documents into text blocks for auditing"
    )
    parser.add_argument(
        "document",
        type=str,
        help="Path to the DOCX file to parse"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: {document}_blocks.jsonl)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["jsonl", "json"],
        default="jsonl",
        help="Output format (default: jsonl)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print preview of extracted blocks"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print statistics about the document"
    )

    args = parser.parse_args()

    # Validate input file
    doc_path = Path(args.document)
    if not doc_path.exists():
        print(f"Error: File not found: {args.document}", file=sys.stderr)
        sys.exit(1)

    if doc_path.suffix.lower() != '.docx':
        print(f"Warning: File does not have .docx extension: {args.document}", file=sys.stderr)

    # Extract blocks
    print(f"Parsing document: {args.document}")
    blocks = extract_audit_blocks(args.document)
    print(f"Extracted {len(blocks)} blocks")

    # Count by type
    text_blocks = sum(1 for b in blocks if b['type'] == 'text')
    table_blocks = sum(1 for b in blocks if b['type'] == 'table')
    print(f"  - Text blocks: {text_blocks}")
    print(f"  - Table blocks: {table_blocks}")

    # Print statistics
    if args.stats:
        print("\n--- Document Statistics ---")
        headings = set()
        total_chars = 0
        for block in blocks:
            headings.add(block['heading'])
            if block['type'] == 'text':
                total_chars += len(block['content'])
            elif block['type'] == 'table':
                total_chars += sum(len(str(cell)) for row in block['content'] for cell in row)

        print(f"Unique headings: {len(headings)}")
        print(f"Total characters: {total_chars:,}")
        print(f"Average block size: {total_chars // len(blocks) if blocks else 0:,} chars")

    # Print preview
    if args.preview:
        print("\n--- Block Preview (first 5) ---")
        for i, block in enumerate(blocks[:5]):
            print(f"\n[Block {i+1}] {block['heading']}")
            print(f"Type: {block['type']}")
            if block['type'] == 'text':
                content = block['content'][:200]
                if len(block['content']) > 200:
                    content += "..."
                print(f"Content: {content}")
            else:
                print(f"Table ({len(block['content'])} rows):")
                print(format_table_for_display(block['content'][:3]))
                if len(block['content']) > 3:
                    print("...")

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = doc_path.stem + "_blocks." + args.format

    # Save output
    if args.format == "jsonl":
        save_blocks_jsonl(blocks, output_path)
    else:
        save_blocks_json(blocks, output_path)

    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
