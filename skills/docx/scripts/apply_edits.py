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
        self.used_minidom = False  # Track if we used minidom for direct edits

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
        table_location = None

        if para_index is not None:
            # Use specified paragraph index
            target_para = self.docx_doc.paragraphs[para_index]
            target_para_idx = para_index
        else:
            # Search paragraph containing find_text (including tables)
            target_para_idx, target_para, table_location = self._find_paragraph_containing(find_text)

        if not target_para:
            raise ValueError(f"Cannot find paragraph containing text: {find_text}")

        if table_location:
            print(f"    Located in table[{table_location['table_idx']}], row[{table_location['row_idx']}], cell[{table_location['cell_idx']}], para[{table_location['para_idx']}]")
        else:
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
            if table_location:
                # Special handling for table cells: use minidom for everything
                self._apply_table_cell_edit_with_minidom(
                    table_location['table_idx'],
                    table_location['row_idx'],
                    table_location['cell_idx'],
                    delete_text,
                    insert_text
                )
                # Skip the normal XML generation path
                print(f"    ✓ Complete (table cell edit)\n")
                continue  # Move to next edit
            else:
                # Original logic for main document paragraphs
                para_node = self._find_paragraph_node(target_para_idx)
                dom_runs = self._get_run_nodes(para_node)
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
        table_location = None

        if para_index is not None:
            target_para = self.docx_doc.paragraphs[para_index]
            target_para_idx = para_index
        else:
            # Search paragraph containing find_text (including tables)
            target_para_idx, target_para, table_location = self._find_paragraph_containing(find_text)

        if not target_para:
            raise ValueError(f"Cannot find paragraph containing text: {find_text}")

        if table_location:
            print(f"    Located in table[{table_location['table_idx']}], row[{table_location['row_idx']}], cell[{table_location['cell_idx']}]")
        else:
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
        if table_location:
            para_node = self._find_table_paragraph_node(
                table_location['table_idx'],
                table_location['row_idx'],
                table_location['cell_idx'],
                delete_text
            )
        else:
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
        table_location = None

        if para_index is not None:
            target_para = self.docx_doc.paragraphs[para_index]
            target_para_idx = para_index
        else:
            # Search paragraph containing find_text (including tables)
            target_para_idx, target_para, table_location = self._find_paragraph_containing(find_text)

        if not target_para:
            raise ValueError(f"Cannot find paragraph containing text: {find_text}")

        if table_location:
            print(f"    Located in table[{table_location['table_idx']}], row[{table_location['row_idx']}], cell[{table_location['cell_idx']}]")
        else:
            print(f"    Located paragraph: #{target_para_idx}")

        # Find first Run containing the text in DOM
        if table_location:
            para_node = self._find_table_paragraph_node(
                table_location['table_idx'],
                table_location['row_idx'],
                table_location['cell_idx'],
                find_text
            )
        else:
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

    def _find_paragraph_containing(self, text):
        """
        Find paragraph containing specified text, including paragraphs in tables.

        Returns:
            For main document paragraphs: (para_index, para_obj, None)
            For table paragraphs: (None, para_obj, table_location_dict)
            Not found: (None, None, None)

        table_location_dict = {'table_idx': int, 'row_idx': int, 'cell_idx': int, 'para_idx': int}
        """
        # Search main document paragraphs
        for idx, para in enumerate(self.docx_doc.paragraphs):
            if text in para.text:
                # Try to find matching DOM paragraph
                dom = self.doc["word/document.xml"].dom
                all_para_nodes = dom.getElementsByTagName("w:p")

                para_text = para.text
                for dom_idx, node in enumerate(all_para_nodes):
                    node_text = self._get_node_text(node)
                    if node_text == para_text:
                        return dom_idx, para, None

                # If no exact match, return index anyway (may work for simple cases)
                return idx, para, None

        # Then search table paragraphs
        for table_idx, table in enumerate(self.docx_doc.tables):
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    for para_idx, para in enumerate(cell.paragraphs):
                        if text in para.text:
                            # Return table location instead of global index
                            location = {
                                'table_idx': table_idx,
                                'row_idx': row_idx,
                                'cell_idx': cell_idx,
                                'para_idx': para_idx
                            }
                            return None, para, location

        return None, None, None

    def _find_global_para_index(self, para_obj, all_para_nodes):
        """
        Find the global index of a python-docx paragraph object in the DOM node list.
        """
        # python-docx uses lxml, Document library uses xml.dom.minidom
        # We need to match by text content and position as a workaround

        # Get unique text signature of the paragraph
        para_text = para_obj.text

        # Count how many times we've seen this text before (to handle duplicates)
        seen_count = 0
        for table in self.docx_doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        if p.text == para_text:
                            if p == para_obj:
                                # Found it, now find the nth occurrence in DOM
                                current_count = 0
                                for idx, node in enumerate(all_para_nodes):
                                    node_text = self._get_node_text(node)
                                    if node_text == para_text:
                                        if current_count == seen_count:
                                            return idx
                                        current_count += 1
                            else:
                                seen_count += 1

        # Also check main paragraphs
        for p in self.docx_doc.paragraphs:
            if p.text == para_text:
                if p == para_obj:
                    current_count = 0
                    for idx, node in enumerate(all_para_nodes):
                        node_text = self._get_node_text(node)
                        if node_text == para_text:
                            if current_count == seen_count:
                                return idx
                            current_count += 1
                else:
                    seen_count += 1

        raise ValueError("Could not find paragraph in DOM")

    def _get_node_text(self, node):
        """Extract text content from a DOM paragraph node"""
        text_parts = []
        for child in node.getElementsByTagName("w:t"):
            if child.firstChild:
                text_parts.append(child.firstChild.nodeValue)
        for child in node.getElementsByTagName("w:delText"):
            if child.firstChild:
                text_parts.append(child.firstChild.nodeValue)
        return ''.join(text_parts)

    def _find_table_cell_text_location(self, table_idx, row_idx, cell_idx, search_text):
        """
        Find text location in a table cell using minidom for accurate extraction.

        Returns indices and mapping info without DOM nodes.

        Args:
            table_idx: Table index in document
            row_idx: Row index in table
            cell_idx: Cell index in row
            search_text: Text to search for

        Returns:
            tuple: (run_indices, start_char, end_char, char_to_info_simplified)
                run_indices: List of (para_idx, run_idx_in_para) tuples for affected runs
                start_char: Start position in combined text
                end_char: End position in combined text
                char_to_info_simplified: Character mapping with indices instead of nodes
        """
        # Use minidom directly for accurate text extraction
        from xml.dom import minidom
        xml_path = self.unpacked_dir / "word" / "document.xml"
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        dom = minidom.parseString(content)

        # Navigate to cell
        table_nodes = dom.getElementsByTagName("w:tbl")
        table_node = table_nodes[table_idx]
        row_nodes = table_node.getElementsByTagName("w:tr")
        row_node = row_nodes[row_idx]
        cell_nodes = row_node.getElementsByTagName("w:tc")
        cell_node = cell_nodes[cell_idx]
        para_nodes = cell_node.getElementsByTagName("w:p")

        # Build character-to-run mapping with indices
        full_text = ""
        char_to_info = []
        run_to_indices = {}  # Map run node to (para_idx, run_idx_in_para)

        for para_idx, para_node in enumerate(para_nodes):
            run_nodes = para_node.getElementsByTagName("w:r")
            for run_idx_in_para, run_node in enumerate(run_nodes):
                run_to_indices[id(run_node)] = (para_idx, run_idx_in_para)
                run_text = self._get_node_text_from_run(run_node)
                for char in run_text:
                    full_text += char
                    char_to_info.append({
                        'run_id': id(run_node),
                        'para_idx': para_idx,
                        'run_idx_in_para': run_idx_in_para,
                        'char': char
                    })

        # Find text
        if search_text not in full_text:
            raise ValueError(f"Cannot find text '{search_text[:50]}...' in table cell")

        start_idx = full_text.find(search_text)
        end_idx = start_idx + len(search_text)

        # Get affected run indices
        run_indices = []
        seen = set()
        for i in range(start_idx, end_idx):
            info = char_to_info[i]
            key = (info['para_idx'], info['run_idx_in_para'])
            if key not in seen:
                run_indices.append(key)
                seen.add(key)

        return run_indices, start_idx, end_idx, char_to_info

    def _get_table_cell_runs_from_doc_dom(self, table_idx, row_idx, cell_idx, run_indices):
        """
        Get DOM run nodes from Document library's DOM using run indices.

        Args:
            table_idx, row_idx, cell_idx: Table location
            run_indices: List of (para_idx, run_idx_in_para) tuples

        Returns:
            tuple: (first_para_node, list of run_nodes)
        """
        dom = self.doc["word/document.xml"].dom

        # Navigate to cell
        table_nodes = dom.getElementsByTagName("w:tbl")
        table_node = table_nodes[table_idx]
        row_nodes = table_node.getElementsByTagName("w:tr")
        row_node = row_nodes[row_idx]
        cell_nodes = row_node.getElementsByTagName("w:tc")
        cell_node = cell_nodes[cell_idx]
        para_nodes = cell_node.getElementsByTagName("w:p")

        # Get run nodes by indices
        affected_runs = []
        first_para = None

        for para_idx, run_idx_in_para in run_indices:
            para_node = para_nodes[para_idx]
            if first_para is None:
                first_para = para_node

            run_nodes = para_node.getElementsByTagName("w:r")
            run_node = run_nodes[run_idx_in_para]
            affected_runs.append(run_node)

        return first_para, affected_runs

    def _get_node_text_from_run(self, run_node):
        """Extract text from a single run node (not recursive)"""
        text_parts = []
        for child in run_node.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == "w:t" and child.firstChild:
                    text_parts.append(child.firstChild.nodeValue)
                elif child.tagName == "w:delText" and child.firstChild:
                    text_parts.append(child.firstChild.nodeValue)
        return ''.join(text_parts)

    def _apply_table_cell_edit_with_minidom(self, table_idx, row_idx, cell_idx,
                                            delete_text, insert_text):
        """
        Apply tracked changes edit to table cell using minidom directly.

        This bypasses Document library's DOM which has text extraction issues.

        Args:
            table_idx, row_idx, cell_idx: Table location
            delete_text: Text to delete
            insert_text: Text to insert
        """
        from xml.dom import minidom

        # Load XML with minidom
        xml_path = self.unpacked_dir / "word" / "document.xml"
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        dom = minidom.parseString(content)

        # Navigate to cell
        tables = dom.getElementsByTagName("w:tbl")
        table = tables[table_idx]
        rows = table.getElementsByTagName("w:tr")
        row = rows[row_idx]
        cells = row.getElementsByTagName("w:tc")
        cell = cells[cell_idx]
        paras = cell.getElementsByTagName("w:p")

        # Find paragraph containing delete_text
        target_para = None
        target_para_idx = None

        for p_idx, para in enumerate(paras):
            para_text = ''.join([t.firstChild.nodeValue for t in para.getElementsByTagName("w:t") if t.firstChild])
            if delete_text in para_text:
                target_para = para
                target_para_idx = p_idx
                break

        if not target_para:
            raise ValueError(f"Cannot find text in table cell paragraphs")

        # Get paragraph text and find match position
        para_text = ''.join([t.firstChild.nodeValue for t in target_para.getElementsByTagName("w:t") if t.firstChild])
        match_start = para_text.find(delete_text)
        if match_start < 0:
            raise ValueError(f"Text found in cell but not in specific paragraph")

        match_end = match_start + len(delete_text)

        # Get runs in paragraph
        runs = target_para.getElementsByTagName("w:r")

        # Build character-to-run mapping at paragraph level
        char_to_run = []
        for run in runs:
            run_text = self._get_node_text_from_run(run)
            for char in run_text:
                char_to_run.append(run)

        # Find affected runs
        affected_runs = []
        for i in range(match_start, match_end):
            if i < len(char_to_run):
                run = char_to_run[i]
                if not affected_runs or affected_runs[-1] != run:
                    affected_runs.append(run)

        if not affected_runs:
            raise ValueError("No runs found for text range")

        # Build edit for the run(s)
        # For simplicity: assume single run contains all text (verified earlier)
        first_run = affected_runs[0]
        run_text = self._get_node_text_from_run(first_run)

        # Find position in run
        run_match_pos = run_text.find(delete_text)
        if run_match_pos < 0:
            raise ValueError(f"Text not found in run")

        before = run_text[:run_match_pos]
        after = run_text[run_match_pos + len(delete_text):]

        # Get run properties
        rpr_node = None
        for child in first_run.childNodes:
            if child.nodeType == child.ELEMENT_NODE and child.tagName == "w:rPr":
                rpr_node = child
                break

        rpr_xml = rpr_node.toxml() if rpr_node else ""
        rsid = first_run.getAttribute("w:rsidR") if first_run.hasAttribute("w:rsidR") else ""

        # Build replacement XML with tracked changes
        rev_config = self.config['revision']
        author = rev_config['author']
        rsid_edit = rev_config.get('rsid') or rsid

        parts = []

        # Before part (unchanged)
        if before:
            parts.append(f'<w:r w:rsidR="{rsid}">{rpr_xml}{t_tag(before)}</w:r>')

        # Deleted part
        parts.append(f'<w:del w:id="0" w:author="{author}" w:date="2025-12-28T00:00:00Z">')
        parts.append(f'<w:r w:rsidDel="{rsid_edit}">{rpr_xml}{del_text_tag(delete_text)}</w:r>')
        parts.append('</w:del>')

        # Inserted part
        parts.append(f'<w:ins w:id="1" w:author="{author}" w:date="2025-12-28T00:00:00Z">')
        parts.append(f'<w:r w:rsidR="{rsid_edit}">{rpr_xml}{t_tag(insert_text)}</w:r>')
        parts.append('</w:ins>')

        # After part (unchanged)
        if after:
            parts.append(f'<w:r w:rsidR="{rsid}">{rpr_xml}{t_tag(after)}</w:r>')

        replacement_xml = ''.join(parts)

        # Replace the run in DOM
        # Parse with namespace declaration
        ns_xml = f'''<root xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                          xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
                          xmlns:w16du="http://schemas.microsoft.com/office/word/2016/wordml/du">
            {replacement_xml}
        </root>'''

        temp_doc = minidom.parseString(ns_xml)

        # Insert new nodes before first run
        for child in temp_doc.documentElement.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                # Use importNode to properly handle namespaces
                imported_node = dom.importNode(child, True)
                target_para.insertBefore(imported_node, first_run)

        # Remove first run
        target_para.removeChild(first_run)

        # Remove other affected runs
        for run in affected_runs[1:]:
            target_para.removeChild(run)

        # Write back to file (preserve formatting)
        with open(xml_path, 'w', encoding='utf-8') as f:
            # Use toprettyxml() might add extra whitespace, use toxml() instead
            f.write(dom.toxml(encoding='utf-8').decode('utf-8'))

        # Mark that we've used minidom for direct edits
        self.used_minidom = True
        print(f"    [INFO] Applied edit directly to XML file using minidom")

    def _build_run_edits_from_char_mapping(self, affected_runs, start_char, end_char,
                                           delete_text, insert_text, char_to_info):
        """
        Build run_edits structure from character mapping for table cells.

        Matches the format expected by build_cross_run_replacement:
        {'run_idx', 'before', 'delete', 'insert', 'after', 'is_first', 'run'}

        Args:
            affected_runs: List of DOM run nodes involved in the match
            start_char: Start index in combined text
            end_char: End index in combined text
            delete_text: Text to delete
            insert_text: Text to insert
            char_to_info: Character mapping (with run_idx_in_para field)

        Returns:
            List of run edit operations compatible with build_cross_run_replacement
        """
        run_edits = []
        is_first = True

        for run_idx, run_node in enumerate(affected_runs):
            # Get full text of this run
            run_text = self._get_node_text_from_run(run_node)

            # Find characters from this run that are in the match range
            # We need to match by index since char_to_info uses indices not nodes
            chars_before_match = 0
            chars_in_match = 0
            chars_after_match = 0

            # Count characters in each section
            for i, info in enumerate(char_to_info):
                # Match run by checking if it's at the same position in affected_runs list
                # (This is a simplification - in practice we'd match by run index)
                if i < start_char:
                    chars_before_match += 1
                elif i < end_char:
                    chars_in_match += 1
                else:
                    chars_after_match += 1

            # For table cells, we simplified: assume single run contains all text
            # Split run text based on match position
            if run_idx == 0:  # First and likely only run
                # Find where delete_text starts in run_text
                match_pos = run_text.find(delete_text)
                print(f"    [DEBUG] run_text length: {len(run_text)}, first 80 chars: {run_text[:80]}")
                print(f"    [DEBUG] delete_text length: {len(delete_text)}, content: {delete_text}")
                print(f"    [DEBUG] match_pos: {match_pos}")
                if match_pos >= 0:
                    before = run_text[:match_pos]
                    delete = delete_text
                    after = run_text[match_pos + len(delete_text):]
                    print(f"    [DEBUG] before: {len(before)} chars, delete: {len(delete)} chars, after: {len(after)} chars")
                else:
                    # Fallback
                    print(f"    [DEBUG] WARNING: delete_text not found in run_text, using fallback")
                    before = ""
                    delete = run_text
                    after = ""
            else:
                before = ""
                delete = run_text
                after = ""

            run_edits.append({
                'run_idx': run_idx,
                'before': before,
                'delete': delete,
                'insert': insert_text if is_first else '',
                'after': after,
                'is_first': is_first,
                'run': None  # Not used for table cells
            })

            is_first = False

        return run_edits

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
        if self.used_minidom:
            print("Saving document...")
            print("✓ Document saved (minidom edits already written to file)")
        else:
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
