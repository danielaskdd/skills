#!/usr/bin/env python3
"""
Word Document Editing Tool - Aspose.Words Edition

This is a simplified implementation using Aspose.Words for Python to handle
document editing operations with track changes. It provides a cleaner alternative
to the manual XML manipulation approach in apply_edits.py.

Key Features:
- ✅ Automatic cross-run text matching (handled by Aspose.Words)
- ✅ Built-in track changes support
- ✅ Simplified codebase (~200 lines vs ~900 lines)
- ✅ Backward compatible with v3.0 YAML configurations
- ✅ Automatic handling of tables and complex structures

Supported Edit Types:
- replace_partial: Replace text (handles cross-run automatically)
- delete: Delete text with track changes
- comment: Add review comments

Requirements:
- aspose-words: pip install aspose-words
- Note: Aspose.Words requires a license. Evaluation version adds watermark.
"""
import sys
import os
import yaml
from pathlib import Path
from datetime import datetime

try:
    import aspose.words as aw
    import aspose.words.replacing as replacing  # type: ignore
except ImportError:
    print("Error: aspose-words not installed. Install with: pip install aspose-words")
    print("Note: Aspose.Words is a commercial library. Evaluation version adds watermark.")
    sys.exit(1)


# ============================================================================
# Custom Exceptions
# ============================================================================

class DocumentNotFoundError(Exception):
    """Exception for document not found with detailed suggestions"""
    pass


# ============================================================================
# Find and Replace Callback for Comments
# ============================================================================

class CommentReplacingCallback(replacing.IReplacingCallback):
    """
    Custom callback for adding comments to matched text.
    """
    def __init__(self, doc, author, comment_text):
        self.doc = doc
        self.author = author
        self.comment_text = comment_text
        self.comment_id = 0
        
    def replacing(self, args):
        """Called when a match is found"""
        # Get the matched run
        run = args.match_node.as_run()
        para = run.parent_paragraph
        
        # Create comment
        comment = aw.Comment(self.doc, self.author, "AS", datetime.now())
        comment.set_text(self.comment_text)
        
        # Create comment range markers
        comment_range_start = aw.CommentRangeStart(self.doc, self.comment_id)
        comment_range_end = aw.CommentRangeEnd(self.doc, self.comment_id)
        self.comment_id += 1
        
        # Insert markers around the matched text
        para.insert_before(comment_range_start, run)
        para.insert_after(comment_range_end, run)
        para.insert_after(comment, comment_range_end)
        
        return replacing.ReplaceAction.SKIP


# ============================================================================
# Word Editor - Aspose.Words Edition
# ============================================================================

class WordEditorAspose:
    """Word Document Editor using Aspose.Words"""

    def __init__(self, config_file):
        self.config = self._load_config(config_file)
        self.config_file = Path(config_file)
        self.doc = None
        self.author = None
        self.track_changes = False

    def _load_config(self, config_file):
        """Load YAML configuration"""
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _resolve_document_path(self, doc_input, work_dir):
        """
        Resolve document path with smart fallback logic.
        
        Search order:
        1. If absolute path, use directly
        2. Relative to YAML config file location
        3. Relative to work_dir (.claude-work/)
        4. Relative to project root (parent of work_dir)
        5. Current working directory
        """
        work_dir = Path(work_dir)
        doc_input_path = Path(doc_input)
        
        attempted_locations = []
        
        # 1. If absolute path, use directly
        if doc_input_path.is_absolute():
            if doc_input_path.exists():
                return doc_input_path
            attempted_locations.append((str(doc_input_path), "absolute path from config"))
        else:
            # 2. Relative to YAML config file location
            yaml_dir = self.config_file.parent
            yaml_relative = yaml_dir / doc_input_path
            if yaml_relative.exists():
                return yaml_relative.resolve()
            attempted_locations.append((str(yaml_relative), "relative to YAML file"))
            
            # 3. Relative to work_dir (.claude-work/)
            work_relative = work_dir / doc_input_path
            if work_relative.exists():
                return work_relative.resolve()
            attempted_locations.append((str(work_relative), "relative to work_dir"))
            
            # 4. Relative to project root (parent of work_dir)
            project_root = work_dir.parent
            root_relative = project_root / doc_input_path
            if root_relative.exists():
                return root_relative.resolve()
            attempted_locations.append((str(root_relative), "relative to project root"))
            
            # 5. Current working directory
            cwd_relative = Path.cwd() / doc_input_path
            if cwd_relative.exists():
                return cwd_relative.resolve()
            attempted_locations.append((str(cwd_relative), "relative to current directory"))
        
        # Build error message
        error_msg = ["✗ Error: Document not found", "", "Searched locations:"]
        for i, (location, context) in enumerate(attempted_locations, 1):
            error_msg.append(f"  {i}. {location}")
            error_msg.append(f"     ({context})")
        
        error_msg.extend([
            "", "Configuration:",
            f"  document.input: \"{doc_input}\"",
            f"  YAML file: {self.config_file}",
            "", "Suggestions:",
            f"  • Use absolute path: \"{Path(doc_input).resolve()}\"",
            f"  • Place file in work_dir: {work_dir / doc_input}",
            f"  • Place file in project root: {work_dir.parent / doc_input}",
        ])
        
        raise DocumentNotFoundError("\n".join(error_msg))

    def setup(self, work_dir):
        """Setup and load document"""
        doc_config = self.config['document']
        rev_config = self.config['revision']
        
        # Resolve and load document
        try:
            input_path = self._resolve_document_path(doc_config['input'], work_dir)
            self.doc = aw.Document(str(input_path))
            print(f"✓ Document loaded: {input_path}")
        except DocumentNotFoundError:
            raise
        except Exception as e:
            error_msg = [
                "✗ Error: Failed to load document",
                f"  {str(e)}",
                "",
                f"Document path: {doc_config['input']}",
                "",
                "Possible causes:",
                "  • Document is corrupted",
                "  • Not a valid .docx file",
                "  • File permissions issue",
                "  • Aspose.Words license issue"
            ]
            print("\n".join(error_msg))
            raise
        
        # Setup revision tracking
        self.author = rev_config['author']
        self.track_changes = rev_config['track_changes']
        
        if self.track_changes:
            self.doc.start_track_revisions(self.author, datetime.now())
        
        print(f"✓ Author: {self.author}")
        print(f"✓ Track changes mode: {'Enabled' if self.track_changes else 'Disabled'}")

    def apply_edits(self):
        """Apply all edit operations"""
        edits = self.config.get('edits', [])
        
        if not edits:
            print("⚠ No edit operations found")
            return
        
        print(f"\nStarting to apply {len(edits)} edit operations...\n")
        
        for i, edit in enumerate(edits, 1):
            try:
                self._apply_edit(i, edit)
            except Exception as e:
                print(f"✗ Operation {i} failed: {e}")
                raise

    def _apply_edit(self, index, edit):
        """Apply a single edit operation"""
        edit_type = edit['type']
        desc = edit.get('description', f'Operation {index}')
        
        print(f"[{index}] {desc}")
        print(f"    Type: {edit_type}")
        
        # Route to appropriate handler
        if edit_type in ('replace_partial_cross_run', 'replace_partial'):
            self._apply_replace(edit)
        elif edit_type == 'delete':
            self._apply_delete(edit)
        elif edit_type == 'insert':
            self._apply_insert(edit)
        elif edit_type == 'comment':
            self._apply_comment(edit)
        else:
            raise ValueError(f"Unsupported edit type: {edit_type}")

    def _apply_replace(self, edit):
        """Apply replace operation using Aspose.Words"""
        # find_text is available for context but not required by Aspose.Words
        # which can search globally across the document
        changes = edit['changes']
        
        options = replacing.FindReplaceOptions()
        options.match_case = True
        options.find_whole_words_only = False
        
        for change in changes:
            delete_text = change['delete']
            insert_text = change['insert']
            
            print(f"    Delete: '{delete_text}'")
            print(f"    Insert: '{insert_text}'")
            
            # Aspose.Words automatically handles cross-run matching
            count = self.doc.range.replace(delete_text, insert_text, options)
            
            if count == 0:
                print(f"    ⚠ Warning: Text not found: '{delete_text}'")
            else:
                print(f"    ✓ Replaced {count} occurrence(s)")
        
        print(f"    ✓ Complete\n")

    def _apply_delete(self, edit):
        """Apply delete operation"""
        delete_text = edit['delete']
        
        print(f"    Delete: '{delete_text}'")
        
        options = replacing.FindReplaceOptions()
        options.match_case = True
        
        # Delete by replacing with empty string
        count = self.doc.range.replace(delete_text, "", options)
        
        if count == 0:
            print(f"    ⚠ Warning: Text not found: '{delete_text}'")
        else:
            print(f"    ✓ Deleted {count} occurrence(s)")
        
        print(f"    ✓ Complete\n")

    def _apply_insert(self, edit):
        """Apply insert operation"""
        find_text = edit['find_text']
        insert_text = edit['insert']
        position = edit.get('position', 'after')  # 'before' or 'after'
        
        print(f"    Find: '{find_text}'")
        print(f"    Insert: '{insert_text}'")
        print(f"    Position: {position}")
        
        options = replacing.FindReplaceOptions()
        options.match_case = True
        
        # Insert by replacing find_text with find_text + insert_text or vice versa
        if position == 'before':
            replacement = insert_text + find_text
        else:  # after
            replacement = find_text + insert_text
        
        count = self.doc.range.replace(find_text, replacement, options)
        
        if count == 0:
            print(f"    ⚠ Warning: Text not found: '{find_text}'")
        else:
            print(f"    ✓ Inserted at {count} location(s)")
        
        print(f"    ✓ Complete\n")

    def _apply_comment(self, edit):
        """Apply comment operation"""
        find_text = edit['find_text']
        comment_text = edit['comment']
        
        print(f"    Comment: '{comment_text}'")
        print(f"    Target: '{find_text}'")
        
        # Use callback to add comment
        callback = CommentReplacingCallback(self.doc, self.author, comment_text)
        
        options = replacing.FindReplaceOptions()
        options.replacing_callback = callback
        
        # Find and add comment (replace with same text)
        self.doc.range.replace(find_text, find_text, options)
        
        print(f"    ✓ Complete\n")

    def save(self):
        """Save document"""
        doc_config = self.config['document']
        output_path = Path(doc_config.get('output', 'output.docx'))
        
        # Make output path absolute if relative
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        
        print("Saving document...")
        
        # Stop tracking revisions before saving
        if self.track_changes:
            self.doc.stop_track_revisions()
        
        # Save document
        self.doc.save(str(output_path))
        
        print(f"✓ Document saved: {output_path}")
        
        # Validate output
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"✓ File size: {file_size:,} bytes")


# ============================================================================
# Main function
# ============================================================================

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python apply_edits_aspose.py <yaml_config_file> [work_directory]")
        print("Example: python apply_edits_aspose.py .claude-work/edits/my_edit.yaml .claude-work")
        sys.exit(1)
    
    config_file = sys.argv[1]
    work_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    if not os.path.exists(config_file):
        print(f"Error: Config file does not exist: {config_file}")
        sys.exit(1)
    
    print("=" * 60)
    print("Word Document Editing Tool - Aspose.Words Edition")
    print("=" * 60)
    print()
    
    try:
        editor = WordEditorAspose(config_file)
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
