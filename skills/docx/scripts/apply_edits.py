#!/usr/bin/env python3
"""
Word Document Editing Tool v3.0 (Unified Edition)

Replaces v2.0 with enhanced cross-run matching while maintaining full backward compatibility.

Key Features:
- ✅ Cross-run string matching (handles text spanning multiple formats)
- ✅ Backward compatible with v2.0 YAML configurations
- ✅ Supports all v2.0 operations: replace_partial, delete, comment
- ✅ Paragraph-level logical view + Run-level physical mapping
- ✅ Track changes mode for all modifications
- ✅ Format inheritance (preserves formatting from deleted text)

Supported Edit Types:
- replace_partial / replace_partial_cross_run: Replace text (single or cross-run)
- delete: Delete text with track changes
- comment: Add review comments
"""
import sys
import os
import yaml
from pathlib import Path
from xml.sax.saxutils import escape

# python-docx for paragraph-level analysis
from docx import Document as PythonDocxDocument

# Document library for tracked changes editing
DOCX_SKILLS_PATH = os.environ.get('DOCX_SKILLS_PATH') or \
                   '/Users/ydh/.claude/plugins/cache/anthropic-agent-skills/document-skills/69c0b1a06741/skills/docx'
sys.path.insert(0, DOCX_SKILLS_PATH)
from scripts.document import Document


# ============================================================================
# Helper Functions: XML Operations
# ============================================================================

def t_tag(text):
    """Create <w:t> tag with automatic XML escaping and space preservation"""
    text = escape(text)
    if text.startswith(" ") or text.endswith(" "):
        return f'<w:t xml:space="preserve">{text}</w:t>'
    return f"<w:t>{text}</w:t>"


def del_text_tag(text):
    """Create <w:delText> tag with escaping and space handling"""
    text = escape(text)
    if text.startswith(" ") or text.endswith(" "):
        return f'<w:delText xml:space="preserve">{text}</w:delText>'
    return f"<w:delText>{text}</w:delText>"


def rpr_xml(node):
    """Extract run properties <w:rPr> from node"""
    tags = node.getElementsByTagName("w:rPr")
    return tags[0].toxml() if tags else ""


def node_text(node):
    """Extract text content from all <w:t> elements in node"""
    texts = []
    for t in node.getElementsByTagName("w:t"):
        for child in t.childNodes:
            if child.nodeType == child.TEXT_NODE:
                texts.append(child.data)
    return "".join(texts)


# ============================================================================
# Core Algorithm: Cross-Run Matching and Mapping
# ============================================================================

class RunMapper:
    """
    Paragraph Run Mapper

    Responsibilities:
    1. Get complete paragraph text using python-docx (logical view)
    2. Build Run offset mapping table (physical view)
    3. Map logical match range to physical Run list
    """

    def __init__(self, paragraph_text, runs_info):
        """
        Args:
            paragraph_text: Complete paragraph text (all Runs merged)
            runs_info: Run info list [{'text': '...', 'run': run_obj}, ...]
        """
        self.paragraph_text = paragraph_text
        self.runs_info = runs_info
        self.run_offsets = self._calculate_offsets()

    def _calculate_offsets(self):
        """
        Calculate character offsets for each Run

        Returns: [
            {'idx': 0, 'start': 0, 'end': 8, 'text': 'This is ', 'run': ...},
            {'idx': 1, 'start': 8, 'end': 17, 'text': 'important', 'run': ...},
            ...
        ]
        """
        offsets = []
        position = 0

        for idx, info in enumerate(self.runs_info):
            text = info['text']
            offsets.append({
                'idx': idx,
                'start': position,
                'end': position + len(text),
                'text': text,
                'run': info['run']
            })
            position += len(text)

        return offsets

    def find_text(self, search_text):
        """
        Find string in paragraph text

        Returns: (match_start, match_end) or None
        """
        idx = self.paragraph_text.find(search_text)
        if idx == -1:
            return None
        return (idx, idx + len(search_text))

    def map_to_runs(self, match_start, match_end, delete_text, insert_text):
        """
        Map logical match range to physical Run edit operations

        Args:
            match_start: Match start position (logical offset)
            match_end: Match end position (logical offset)
            delete_text: Text to delete
            insert_text: Text to insert

        Returns: [
            {
                'run_idx': 0,
                'before': 'Unchanged before part',
                'delete': 'Deleted portion in this Run',
                'insert': 'Inserted text (only in first Run)',
                'after': 'Unchanged after part',
                'is_first': True/False,
                'run': run object
            },
            ...
        ]
        """
        edits = []
        is_first = True

        for offset in self.run_offsets:
            # Calculate overlap between this Run and match range
            overlap_start = max(offset['start'], match_start)
            overlap_end = min(offset['end'], match_end)

            if overlap_start >= overlap_end:
                continue  # This Run is not affected

            # Calculate local offset (relative to Run start)
            local_start = overlap_start - offset['start']
            local_end = overlap_end - offset['start']

            # Split this Run's text
            before = offset['text'][:local_start]
            delete_portion = offset['text'][local_start:local_end]
            after = offset['text'][local_end:]

            # Only first affected Run inserts new text
            insert_portion = insert_text if is_first else ''

            edits.append({
                'run_idx': offset['idx'],
                'before': before,
                'delete': delete_portion,
                'insert': insert_portion,
                'after': after,
                'is_first': is_first,
                'run': offset['run']
            })

            is_first = False

        return edits


# ============================================================================
# Run Node Reconstruction: Generate Track Changes XML
# ============================================================================

def build_cross_run_replacement(edits, dom_runs):
    """
    Build complete XML for cross-run replacement

    Args:
        edits: RunMapper.map_to_runs() edit operation list returned by RunMapper.map_to_runs()
        dom_runs: Corresponding DOM <w:r> node list

    Returns:
        Complete XML string (replaces all affected Runs)
    """
    parts = []

    for edit, dom_run in zip(edits, dom_runs):
        rpr = rpr_xml(dom_run)
        rsid = dom_run.getAttribute("w:rsidR") if dom_run.hasAttribute("w:rsidR") else ""

        # Unchanged before part
        if edit['before']:
            parts.append(f'<w:r w:rsidR="{rsid}">{rpr}{t_tag(edit["before"])}</w:r>')

        # Delete part (using track changes)
        if edit['delete']:
            # If first Run, deleted text determines insert format
            if edit['is_first']:
                # First character format inherited from here
                parts.append(f'<w:del><w:r>{rpr}{del_text_tag(edit["delete"])}</w:r></w:del>')

                # Insert part uses same format (inherited from delete)
                if edit['insert']:
                    parts.append(f'<w:ins><w:r>{rpr}{t_tag(edit["insert"])}</w:r></w:ins>')
            else:
                # Subsequent Runs only delete, no insert
                parts.append(f'<w:del><w:r>{rpr}{del_text_tag(edit["delete"])}</w:r></w:del>')

        # Unchanged after part
        if edit['after']:
            parts.append(f'<w:r w:rsidR="{rsid}">{rpr}{t_tag(edit["after"])}</w:r>')

    return "".join(parts)


# ============================================================================
# Word Editor v3.0
# ============================================================================

class WordEditorV3:
    """Cross-Run String Replacement Editor"""

    def __init__(self, config_file):
        self.config = self._load_config(config_file)
        self.doc = None  # Document library instance
        self.docx_doc = None  # python-docx instance

    def _load_config(self, config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def setup(self, work_dir):
        """Setup work environment"""
        self.work_dir = Path(work_dir)
        self.unpacked_dir = self.work_dir / 'unpacked'

        # Initialize Document library (for track changes)
        doc_config = self.config['document']
        rev_config = self.config['revision']

        self.doc = Document(
            str(self.unpacked_dir),
            author=rev_config['author'],
            track_revisions=rev_config['track_changes'],
            rsid=rev_config.get('rsid') or None
        )

        # Initialize python-docx (for paragraph analysis)
        input_path = self.work_dir / doc_config['input']
        self.docx_doc = PythonDocxDocument(str(input_path))

        print(f"✓ Document loaded: {doc_config['input']}")
        print(f"✓ Author: {rev_config['author']}")
        print(f"✓ Track changes mode: {'Enabled' if rev_config['track_changes'] else 'Disabled'}")

    def apply_edits(self):
        """Apply all edit operations"""
        edits = self.config.get('edits', [])

        if not edits:
            print("⚠ ⚠ No edit operations found")
            return

        print(f"\nStarting to apply {len(edits)} edit operations...\n")

        for i, edit in enumerate(edits, 1):
            try:
                self._apply_cross_run_edit(i, edit)
            except Exception as e:
                print(f"✗ Operation {i} failed: {e}")
                raise

    def _apply_cross_run_edit(self, index, edit):
        """
        Apply cross-run edit operation

        Step:
        1. Use python-docx to locate paragraph and find string
        2. Build Run offset mapping
        3. Use Document library to locate corresponding DOM nodes
        4. Generate track changes XML and replace
        """
        edit_type = edit['type']
        desc = edit.get('description', f'Operation {index}')

        print(f"[{index}] {desc}")
        print(f"    Type: {edit_type}")

        # Route to appropriate handler based on edit type
        # Support both new cross-run types and legacy v2.0 types for backward compatibility
        if edit_type in ('replace_partial_cross_run', 'replace_partial'):
            # 'replace_partial' from v2.0 is now handled by cross-run algorithm
            self._apply_replace_cross_run(index, edit)
        elif edit_type == 'delete':
            self._apply_delete_cross_run(index, edit)
        elif edit_type == 'comment':
            self._apply_comment_cross_run(index, edit)
        else:
            raise ValueError(f"Unsupported edit type: {edit_type}")

    def _apply_replace_cross_run(self, _index, edit):
        """
        Apply cross-run replacement operation
        """
        find_text = edit['find_text']
        changes = edit['changes']
        para_index = edit.get('paragraph_index')  # Specify paragraph index (optional)

        # Step 1: Use python-docx to locate paragraph
        target_para = None
        target_para_idx = None

        if para_index is not None:
            # Use specified paragraph index
            target_para = self.docx_doc.paragraphs[para_index]
            target_para_idx = para_index
        else:
            # Search paragraph containing find_text
            for idx, para in enumerate(self.docx_doc.paragraphs):
                if find_text in para.text:
                    target_para = para
                    target_para_idx = idx
                    break

        if not target_para:
            raise ValueError(f"Cannot find paragraph containing text: {find_text}")

        print(f"    Located paragraph: #{target_para_idx}")
        print(f"    Paragraph text: {target_para.text[:80]}...")

        # Step 2: Build Run mapping
        runs_info = [{'text': run.text, 'run': run} for run in target_para.runs]
        mapper = RunMapper(target_para.text, runs_info)

        # Step 3: Apply all changes
        for change in changes:
            delete_text = change['delete']
            insert_text = change['insert']

            # Find match
            match = mapper.find_text(delete_text)
            if not match:
                raise ValueError(f"Cannot find text in paragraph: '{delete_text}'")

            match_start, match_end = match

            # Map to Run edit operations
            run_edits = mapper.map_to_runs(match_start, match_end, delete_text, insert_text)

            print(f"    Delete: '{delete_text}'")
            print(f"    Insert: '{insert_text}'")
            print(f"    Affects {len(run_edits)} Runs")

            # Step 4: Use Document library to get corresponding DOM nodes
            # Locate paragraph node
            para_node = self._find_paragraph_node(target_para_idx)

            # Get all <w:r> child nodes of paragraph
            dom_runs = self._get_run_nodes(para_node)

            # Get affected DOM Run nodes
            affected_dom_runs = [dom_runs[edit['run_idx']] for edit in run_edits]

            # Step 5: Generate track changes XML
            replacement_xml = build_cross_run_replacement(run_edits, affected_dom_runs)

            # Step 6: Replace nodes
            # Delete old Run nodes, insert new XML
            first_run = affected_dom_runs[0]

            # Delete all affected Runs (except first)
            for run_node in affected_dom_runs[1:]:
                para_node.removeChild(run_node)

            # Replace first Run
            self.doc["word/document.xml"].replace_node(first_run, replacement_xml)

            # Update paragraph text (for subsequent matches)
            updated_text = target_para.text[:match_start] + insert_text + target_para.text[match_end:]
            # Rebuild mapper (text has changed)
            # Note: simplified handling, production should reload python-docx document
            mapper.paragraph_text = updated_text

        print(f"    ✓ Complete\n")

    def _apply_delete_cross_run(self, _index, edit):
        """
        Apply cross-run deletion operation (delete text without inserting)
        """
        find_text = edit['find_text']
        delete_text = edit['delete']
        para_index = edit.get('paragraph_index')

        # Locate paragraph using python-docx
        target_para = None
        target_para_idx = None

        if para_index is not None:
            target_para = self.docx_doc.paragraphs[para_index]
            target_para_idx = para_index
        else:
            for idx, para in enumerate(self.docx_doc.paragraphs):
                if find_text in para.text:
                    target_para = para
                    target_para_idx = idx
                    break

        if not target_para:
            raise ValueError(f"Cannot find paragraph containing text: {find_text}")

        print(f"    Located paragraph: #{target_para_idx}")

        # Build Run mapping
        runs_info = [{'text': run.text, 'run': run} for run in target_para.runs]
        mapper = RunMapper(target_para.text, runs_info)

        # Find match
        match = mapper.find_text(delete_text)
        if not match:
            raise ValueError(f"Cannot find text in paragraph: '{delete_text}'")

        match_start, match_end = match

        # Map to Run edit operations (insert is empty for deletion)
        run_edits = mapper.map_to_runs(match_start, match_end, delete_text, '')

        print(f"    Delete: '{delete_text}'")
        print(f"    Affects {len(run_edits)} Runs")

        # Get DOM nodes
        para_node = self._find_paragraph_node(target_para_idx)
        dom_runs = self._get_run_nodes(para_node)
        affected_dom_runs = [dom_runs[edit['run_idx']] for edit in run_edits]

        # Generate track changes XML
        replacement_xml = build_cross_run_replacement(run_edits, affected_dom_runs)

        # Replace nodes
        first_run = affected_dom_runs[0]
        for run_node in affected_dom_runs[1:]:
            para_node.removeChild(run_node)
        self.doc["word/document.xml"].replace_node(first_run, replacement_xml)

        print(f"    ✓ Complete\n")

    def _apply_comment_cross_run(self, _index, edit):
        """
        Add comment to text (works across runs)
        """
        find_text = edit['find_text']
        comment_text = edit['comment']
        para_index = edit.get('paragraph_index')

        # Locate paragraph
        target_para = None
        target_para_idx = None

        if para_index is not None:
            target_para = self.docx_doc.paragraphs[para_index]
            target_para_idx = para_index
        else:
            for idx, para in enumerate(self.docx_doc.paragraphs):
                if find_text in para.text:
                    target_para = para
                    target_para_idx = idx
                    break

        if not target_para:
            raise ValueError(f"Cannot find paragraph containing text: {find_text}")

        print(f"    Located paragraph: #{target_para_idx}")

        # Find first Run containing the text in DOM
        para_node = self._find_paragraph_node(target_para_idx)
        dom_runs = self._get_run_nodes(para_node)

        # Find first run that contains part of find_text
        target_run = None
        for run in dom_runs:
            run_text = node_text(run)
            if find_text[:min(10, len(find_text))] in run_text or run_text in find_text:
                target_run = run
                break

        if not target_run:
            # Fallback: use first run in paragraph
            target_run = dom_runs[0] if dom_runs else para_node

        # Add comment using Document library
        self.doc.add_comment(start=target_run, end=target_run, text=comment_text)

        print(f"    Comment: '{comment_text}'")
        print(f"    ✓ Complete\n")

    def _find_paragraph_node(self, para_index):
        """
        Find paragraph node at specified index in DOM

        Note: need to find Nth <w:p> node (N = para_index)
        """
        dom = self.doc["word/document.xml"].dom
        paragraphs = dom.getElementsByTagName("w:p")

        if para_index >= len(paragraphs):
            raise ValueError(f"Paragraph index {para_index} out of range (total {len(paragraphs)} paragraphs)")

        return paragraphs[para_index]

    def _get_run_nodes(self, para_node):
        """
        Get all direct <w:r> child nodes of paragraph node

        Note: only get direct child nodes, excluding Runs nested in other elements
        """
        runs = []
        for child in para_node.childNodes:
            if child.nodeType == child.ELEMENT_NODE and child.tagName == "w:r":
                runs.append(child)
        return runs

    def save(self):
        """Save document"""
        print("Saving document...")
        self.doc.save(validate=False)
        print("✓ Document saved")


# ============================================================================
# macOS Compatibility
# ============================================================================

def remove_macos_metadata(unpacked_path):
    """Remove macOS system files (.DS_Store)"""
    for rel_path in (".DS_Store", os.path.join("word", ".DS_Store")):
        ds_store = os.path.join(unpacked_path, rel_path)
        if os.path.exists(ds_store):
            os.remove(ds_store)
            print(f"  Cleanup: {rel_path}")


# ============================================================================
# Main function
# ============================================================================

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python apply_edits_v3_cross_run.py <yaml_config_file> [work_directory]")
        print("Example: python apply_edits_v3_cross_run.py .claude-work/edits/my_edit.yaml .claude-work")
        sys.exit(1)

    config_file = sys.argv[1]
    work_dir = sys.argv[2] if len(sys.argv) > 2 else '.'

    if not os.path.exists(config_file):
        print(f"Error: Config file does not exist: {config_file}")
        sys.exit(1)

    print("=" * 60)
    print("Word Document Editing Tool v3.0 (Unified Edition)")
    print("=" * 60)
    print()

    # Cleanup macOS metadata
    unpacked_path = os.path.join(work_dir, 'unpacked')
    if os.path.exists(unpacked_path):
        remove_macos_metadata(unpacked_path)

    try:
        editor = WordEditorV3(config_file)
        editor.setup(work_dir)
        editor.apply_edits()
        editor.save()

        print()
        print("=" * 60)
        print("✓ All operations completed")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
