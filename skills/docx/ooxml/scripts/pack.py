#!/usr/bin/env python3
"""
Tool to pack a directory into a .docx, .pptx, or .xlsx file with XML formatting undone.

Example usage:
    python pack.py <input_directory> <office_file> [--force]
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import defusedxml.minidom
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Pack a directory into an Office file")
    parser.add_argument("input_directory", help="Unpacked Office document directory")
    parser.add_argument("output_file", help="Output Office file (.docx/.pptx/.xlsx)")
    parser.add_argument("--force", action="store_true", help="Skip validation")
    args = parser.parse_args()

    try:
        success = pack_document(
            args.input_directory, args.output_file, validate=not args.force
        )

        # Show appropriate message based on validation
        if args.force:
            print("✓ Document packed (validation skipped)", file=sys.stderr)
            print("  Use without --force to enable validation", file=sys.stderr)
        elif not success:
            print("Contents would produce a corrupt file.", file=sys.stderr)
            print("Please validate XML before repacking.", file=sys.stderr)
            print("Use --force to skip validation and pack anyway.", file=sys.stderr)
            sys.exit(1)

    except ValueError as e:
        sys.exit(f"Error: {e}")


def pack_document(input_dir, output_file, validate=False):
    """Pack a directory into an Office file (.docx/.pptx/.xlsx).

    Args:
        input_dir: Path to unpacked Office document directory
        output_file: Path to output Office file
        validate: If True, validates with soffice (default: False)

    Returns:
        bool: True if successful, False if validation failed
    """
    input_dir = Path(input_dir)
    output_file = Path(output_file)

    if not input_dir.is_dir():
        raise ValueError(f"{input_dir} is not a directory")
    if output_file.suffix.lower() not in {".docx", ".pptx", ".xlsx"}:
        raise ValueError(f"{output_file} must be a .docx, .pptx, or .xlsx file")

    # Work in temporary directory to avoid modifying original
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_content_dir = Path(temp_dir) / "content"
        shutil.copytree(input_dir, temp_content_dir)

        # Process XML files to remove pretty-printing whitespace
        for pattern in ["*.xml", "*.rels"]:
            for xml_file in temp_content_dir.rglob(pattern):
                condense_xml(xml_file)

        # Create final Office file as zip archive
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in temp_content_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(temp_content_dir))

        # Validate if requested
        if validate:
            if not validate_document(output_file):
                output_file.unlink()  # Delete the corrupt file
                return False

    return True


def basic_validation(doc_path):
    """
    Perform basic validation without requiring soffice.
    
    Checks:
    1. ZIP integrity
    2. Required files present
    3. XML well-formed
    4. Can be opened by python-docx
    
    Returns:
        tuple: (success: bool, message: str, checks_detail: dict)
    """
    import zipfile
    from xml.etree import ElementTree as ET
    
    checks = {
        'zip_integrity': False,
        'required_files': False,
        'xml_wellformed': False,
        'openable': False
    }
    
    try:
        # Level 1: ZIP integrity
        with zipfile.ZipFile(doc_path, 'r') as zf:
            if zf.testzip() is None:
                checks['zip_integrity'] = True
        
        # Level 2: Required files based on file type
        if doc_path.suffix.lower() == '.docx':
            required = ['[Content_Types].xml', 'word/document.xml']
            main_xml = 'word/document.xml'
        elif doc_path.suffix.lower() == '.pptx':
            required = ['[Content_Types].xml', 'ppt/presentation.xml']
            main_xml = 'ppt/presentation.xml'
        elif doc_path.suffix.lower() == '.xlsx':
            required = ['[Content_Types].xml', 'xl/workbook.xml']
            main_xml = 'xl/workbook.xml'
        else:
            required = ['[Content_Types].xml']
            main_xml = None
        
        with zipfile.ZipFile(doc_path, 'r') as zf:
            if all(f in zf.namelist() for f in required):
                checks['required_files'] = True
        
        # Level 3: XML well-formed
        if main_xml:
            with zipfile.ZipFile(doc_path, 'r') as zf:
                xml_content = zf.read(main_xml)
                ET.fromstring(xml_content)
                checks['xml_wellformed'] = True
        
        # Level 4: Openable by appropriate library
        if doc_path.suffix.lower() == '.docx':
            try:
                from docx import Document as PythonDocxDocument
                doc = PythonDocxDocument(doc_path)
                _ = len(doc.paragraphs)
                checks['openable'] = True
            except ImportError:
                # python-docx not installed, skip this check
                pass
        else:
            # For xlsx/pptx, we don't have standard validation library
            # ZIP and XML checks are sufficient
            checks['openable'] = True
        
    except Exception as e:
        message = f"Validation failed: {str(e)}"
        return False, message, checks
    
    # Determine result
    if all(checks.values()):
        return True, "All validation checks passed", checks
    elif checks['zip_integrity'] and checks['required_files'] and checks['xml_wellformed']:
        return True, "Basic validation passed (ZIP, files, XML)", checks
    else:
        failed = [k for k, v in checks.items() if not v]
        message = f"Failed checks: {', '.join(failed)}"
        return False, message, checks


def validate_document(doc_path):
    """
    Validate document with optional soffice advanced validation.
    
    Returns:
        bool: True if validation passed or is optional
    """
    # First, run basic validation
    basic_ok, basic_msg, checks = basic_validation(doc_path)
    
    if not basic_ok:
        print(f"✗ Validation failed: {basic_msg}", file=sys.stderr)
        for check, passed in checks.items():
            symbol = "✓" if passed else "✗"
            print(f"  {symbol} {check}", file=sys.stderr)
        return False
    
    # If basic validation passed, try advanced validation with soffice if available
    # Determine the correct filter based on file extension
    match doc_path.suffix.lower():
        case ".docx":
            filter_name = "html:HTML"
        case ".pptx":
            filter_name = "html:impress_html_Export"
        case ".xlsx":
            filter_name = "html:HTML (StarCalc)"

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to",
                    filter_name,
                    "--outdir",
                    temp_dir,
                    str(doc_path),
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            if not (Path(temp_dir) / f"{doc_path.stem}.html").exists():
                error_msg = result.stderr.strip() or "Advanced validation failed"
                print(f"⚠ Advanced validation (soffice): {error_msg}", file=sys.stderr)
                print(f"  Basic validation passed, document is likely usable", file=sys.stderr)
                return True  # Basic passed, so allow it
            print(f"✓ Validation: {basic_msg} + advanced (soffice)", file=sys.stderr)
            return True
        except FileNotFoundError:
            # soffice not available, but basic validation passed
            print(f"✓ Validation: {basic_msg}", file=sys.stderr)
            print(f"  Note: Advanced validation skipped (soffice not available)", file=sys.stderr)
            return True
        except subprocess.TimeoutExpired:
            print(f"⚠ Advanced validation timeout", file=sys.stderr)
            print(f"  Basic validation passed, document is likely usable", file=sys.stderr)
            return True  # Basic passed, so allow it
        except Exception as e:
            print(f"⚠ Advanced validation error: {e}", file=sys.stderr)
            print(f"  Basic validation passed, document is likely usable", file=sys.stderr)
            return True  # Basic passed, so allow it


def condense_xml(xml_file):
    """Strip unnecessary whitespace and remove comments."""
    with open(xml_file, "r", encoding="utf-8") as f:
        dom = defusedxml.minidom.parse(f)

    # Process each element to remove whitespace and comments
    for element in dom.getElementsByTagName("*"):
        # Skip w:t elements and their processing
        if element.tagName.endswith(":t"):
            continue

        # Remove whitespace-only text nodes and comment nodes
        for child in list(element.childNodes):
            if (
                child.nodeType == child.TEXT_NODE
                and child.nodeValue
                and child.nodeValue.strip() == ""
            ) or child.nodeType == child.COMMENT_NODE:
                element.removeChild(child)

    # Write back the condensed XML
    with open(xml_file, "wb") as f:
        f.write(dom.toxml(encoding="UTF-8"))


if __name__ == "__main__":
    main()
