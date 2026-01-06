#!/usr/bin/env python3
"""
ABOUTME: Extracts tables from DOCX with proper merged cell handling
ABOUTME: Outputs 2D array with content in first cell of merged region
"""

from docx.table import Table
from docx.oxml.ns import qn
from typing import List, Optional

class TableExtractor:
    """
    Extract table content handling merged cells correctly.
    
    Merged cells in DOCX:
    - Horizontal: w:gridSpan specifies how many columns cell spans
    - Vertical: w:vMerge with val="restart" starts merge, subsequent cells continue
    
    Output format:
    - 2D list of strings
    - Merged cell content in top-left position only
    - Other positions in merged region are empty strings
    """
    
    @staticmethod
    def extract(table: Table, numbering_resolver=None) -> List[List[str]]:
        """
        Extract table to 2D string array.
        
        Args:
            table: python-docx Table object
            
        Returns:
            List of rows, each row is list of cell text strings
        """
        rows = list(table.rows)
        if not rows:
            return []
        
        # Build grid with proper vertical merge handling
        grid = []
        
        for row_idx, row in enumerate(rows):
            row_cells = list(row.cells)
            row_data = []
            grid_col = 0
            
            for cell_idx, cell in enumerate(row_cells):
                tc = cell._tc
                tcPr = tc.find(qn('w:tcPr'))
                
                # Check gridSpan (horizontal merge)
                grid_span = 1
                if tcPr is not None:
                    gs = tcPr.find(qn('w:gridSpan'))
                    if gs is not None:
                        grid_span = int(gs.get(qn('w:val')))
                
                # Check vMerge (vertical merge)
                vmerge_val = None
                if tcPr is not None:
                    vm = tcPr.find(qn('w:vMerge'))
                    if vm is not None:
                        vmerge_val = vm.get(qn('w:val'))  # 'restart' or None (means 'continue')
                
                # Get cell text with numbering support
                if numbering_resolver is not None:
                    # Extract text with numbering labels
                    cell_paragraphs = []
                    for para_elem in tc.findall('.//w:p', {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}):
                        # Get text content
                        para_text = ''
                        for t_elem in para_elem.findall('.//w:t', {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}):
                            if t_elem.text:
                                para_text += t_elem.text
                        
                        # Get numbering label
                        label = numbering_resolver.get_label(para_elem)
                        
                        # Combine label and text
                        if label:
                            full_text = f"{label} {para_text}".strip()
                        else:
                            full_text = para_text.strip()
                        
                        if full_text:
                            cell_paragraphs.append(full_text)
                    
                    cell_text = '\n'.join(cell_paragraphs).replace('\x07', '')
                else:
                    # Fallback to simple text extraction
                    cell_text = cell.text.strip().replace('\x07', '')
                
                # Determine if this is a vMerge continuation
                if vmerge_val is None and tcPr is not None and tcPr.find(qn('w:vMerge')) is not None:
                    # This is a vMerge continuation (no val attribute means 'continue')
                    row_data.append('')
                else:
                    # This is either: regular cell, or vMerge restart
                    row_data.append(cell_text)
                
                # Add empty strings for horizontally spanned cells
                for _ in range(grid_span - 1):
                    row_data.append('')
                
                grid_col += grid_span
            
            grid.append(row_data)
        
        # Normalize row lengths
        if grid:
            max_cols = max(len(row) for row in grid)
            for row in grid:
                while len(row) < max_cols:
                    row.append('')
        
        return grid
