#!/usr/bin/env python3
"""
Aspose Watermark Removal Tool

This script removes Aspose evaluation watermarks from Word documents.
It handles both text watermarks and image watermarks added by Aspose.Words.

Features:
- Removes "Created with an evaluation copy of Aspose" text watermarks
- Removes "Evaluation Only. Created with Aspose" footer watermarks
- Removes Aspose image watermarks in headers (identified by specific characteristics)

Usage:
    python remove_watermark.py <input_file> [work_directory]

Note:
    This script modifies the input file in-place (overwrites the original file).

Examples:
    python remove_watermark.py document.docx
    python remove_watermark.py document.docx .claude-work
"""

import sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

# ============================================================================
# Custom Exceptions
# ============================================================================

class DocumentNotFoundError(Exception):
    """Exception for document not found with detailed suggestions"""
    pass


# ============================================================================
# Watermark Removal Functions
# ============================================================================

def delete_element(element):
    """
    Generic function: Remove element from XML tree
    """
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)


def remove_text_watermarks(doc):
    """
    Remove Aspose text watermarks from document body and footers
    
    Targets:
    - "Created with an evaluation copy of Aspose" in body
    - "Evaluation Only. Created with Aspose" in footers
    """
    print("Scanning for text watermarks...")
    count = 0

    # 1. Process document body
    paragraphs_to_delete = []
    for p in doc.paragraphs:
        if p.text.startswith("Created with an evaluation copy of Aspose"):
            paragraphs_to_delete.append(p)
    
    for p in paragraphs_to_delete:
        delete_element(p._element)
        count += 1

    # 2. Process all section footers
    # Check three footer types: default (footer), first page, even page
    for section in doc.sections:
        footers = [section.footer, section.first_page_footer, section.even_page_footer]
        for footer in footers:
            if footer is None: 
                continue
            
            footer_paragraphs_to_delete = []
            for p in footer.paragraphs:
                if p.text.startswith("Evaluation Only. Created with Aspose"):
                    footer_paragraphs_to_delete.append(p)
            
            for p in footer_paragraphs_to_delete:
                delete_element(p._element)
                count += 1
                
    print(f"  - Removed {count} text watermark paragraph(s)")


def remove_image_watermarks(doc):
    """
    Remove Aspose image watermarks from headers
    
    Handles two formats:
    1. DrawingML format (w:drawing) - Modern Office XML
    2. VML format (w:pict) - Legacy Vector Markup Language (used by Aspose)
    
    Identification characteristics:
    - Run node has no rsidRPr attribute (not manually edited)
    - DrawingML: Image wp:docPr name attribute is empty
    - VML: v:imagedata o:title attribute is empty or has watermark characteristics
    """
    print("Scanning for image watermarks (DrawingML and VML formats)...")
    count = 0

    for section in doc.sections:
        # Check three header types: default (header), first page, even page
        headers = [section.header, section.first_page_header, section.even_page_header]
        
        for header in headers:
            if header is None: 
                continue
            
            for paragraph in header.paragraphs:
                runs_to_delete = []
                
                for run in paragraph.runs:
                    r_element = run._element
                    
                    # --- Characteristic check 1: Check for rsidRPr existence ---
                    # Normal edits usually have rsidRPr, Aspose-generated ones often don't
                    rPr = r_element.find(qn('w:rPr'))
                    has_rsidRPr = False
                    if rPr is not None:
                        if rPr.find(qn('w:rsidRPr')) is not None:
                            has_rsidRPr = True
                    
                    # If has revision record, treat as normal user content, skip
                    if has_rsidRPr:
                        continue

                    is_target_image = False
                    
                    # --- Check DrawingML format (w:drawing) ---
                    drawings = r_element.findall('.//w:drawing', namespaces=r_element.nsmap)
                    for drawing in drawings:
                        # Find docPr attributes
                        docPrs = drawing.findall('.//wp:docPr', namespaces=drawing.nsmap)
                        for docPr in docPrs:
                            name_attr = docPr.get('name')
                            # If name doesn't exist or is empty string
                            if name_attr is None or not name_attr.strip():
                                is_target_image = True
                                break
                        if is_target_image:
                            break
                    
                    # --- Check VML format (w:pict) - Aspose watermarks often use this ---
                    if not is_target_image:
                        # Define VML namespace
                        vml_ns = 'urn:schemas-microsoft-com:vml'
                        office_ns = 'urn:schemas-microsoft-com:office:office'
                        
                        # Find w:pict elements
                        picts = r_element.findall(qn('w:pict'))
                        for pict in picts:
                            # Find v:imagedata within the pict
                            imagedata_elements = pict.findall('.//{%s}imagedata' % vml_ns)
                            for imagedata in imagedata_elements:
                                # Check o:title attribute (Aspose watermarks often have empty title)
                                title = imagedata.get('{%s}title' % office_ns)
                                
                                # Also check for typical watermark characteristics:
                                # - gain/blacklevel attributes (transparency/brightness adjustments)
                                # - empty or missing title
                                gain = imagedata.get('gain')
                                blacklevel = imagedata.get('blacklevel')
                                
                                # Identify as watermark if:
                                # 1. Title is empty/missing, OR
                                # 2. Has gain/blacklevel adjustments (typical for watermarks)
                                if (title is None or not title.strip()) or (gain or blacklevel):
                                    is_target_image = True
                                    break
                            if is_target_image:
                                break
                    
                    if is_target_image:
                        runs_to_delete.append(run)
                
                # Execute deletion
                for run in runs_to_delete:
                    delete_element(run._element)
                    count += 1

    print(f"  - Removed {count} image watermark(s) matching characteristics")


# ============================================================================
# Path Resolution
# ============================================================================

def resolve_document_path(doc_input, work_dir):
    """
    Resolve document path with smart fallback logic.
    
    Search order:
    1. If absolute path, use directly
    2. Relative to work_dir (.claude-work/)
    3. Relative to project root (parent of work_dir)
    4. Current working directory
    """
    work_dir = Path(work_dir)
    doc_input_path = Path(doc_input)
    
    attempted_locations = []
    
    # 1. If absolute path, use directly
    if doc_input_path.is_absolute():
        if doc_input_path.exists():
            return doc_input_path
        attempted_locations.append((str(doc_input_path), "absolute path"))
    else:
        # 2. Relative to work_dir (.claude-work/)
        work_relative = work_dir / doc_input_path
        if work_relative.exists():
            return work_relative.resolve()
        attempted_locations.append((str(work_relative), "relative to work_dir"))
        
        # 3. Relative to project root (parent of work_dir)
        project_root = work_dir.parent
        root_relative = project_root / doc_input_path
        if root_relative.exists():
            return root_relative.resolve()
        attempted_locations.append((str(root_relative), "relative to project root"))
        
        # 4. Current working directory
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
        "", "Suggestions:",
        f"  • Use absolute path: \"{Path(doc_input).resolve()}\"",
        f"  • Place file in work_dir: {work_dir / doc_input}",
        f"  • Place file in project root: {work_dir.parent / doc_input}",
    ])
    
    raise DocumentNotFoundError("\n".join(error_msg))


# ============================================================================
# Main Processing Function
# ============================================================================

def clean_doc(input_path, work_dir='.'):
    """
    Clean Aspose watermarks from document (in-place modification)
    
    Args:
        input_path: Path to input document (can be relative or absolute)
                    Will be modified in-place
        work_dir: Working directory for path resolution (default: current directory)
    """
    try:
        # Resolve input path
        resolved_input = resolve_document_path(input_path, work_dir)
        print(f"✓ Input document: {resolved_input}")
        print(f"⚠ Note: Modifying file in-place")
        
        # Load document
        doc = Document(str(resolved_input))
        
        # Execute cleanup steps
        remove_text_watermarks(doc)
        remove_image_watermarks(doc)
        
        # Save back to the same file (in-place modification)
        doc.save(str(resolved_input))
        print(f"✓ Processing successful! File modified: {resolved_input}")
        
        # Validate output
        if resolved_input.exists():
            file_size = resolved_input.stat().st_size
            print(f"✓ File size: {file_size:,} bytes")
        
    except DocumentNotFoundError:
        raise
    except Exception as e:
        print(f"✗ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_watermark.py <input_file> [work_directory]")
        print()
        print("Note: This script modifies the input file in-place (overwrites the original file).")
        print()
        print("Examples:")
        print("  python remove_watermark.py document.docx")
        print("  python remove_watermark.py document.docx .claude-work")
        print()
        print("Parameters:")
        print("  input_file       Input Word document (with Aspose watermarks) - will be modified")
        print("  work_directory   Optional: Working directory for path resolution (default: current directory)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    work_directory = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    print("=" * 60)
    print("Aspose Watermark Removal Tool")
    print("=" * 60)
    print()
    
    clean_doc(input_file, work_directory)
    
    print()
    print("=" * 60)
    print("✓ Watermark removal complete!")
    print("=" * 60)
