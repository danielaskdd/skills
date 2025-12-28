# Path Handling in YAML Workflow

## Overview

The scripts support flexible path handling for YAML configuration files, allowing both full and shortened paths.

## Supported Path Formats

### Method 1: Full Path (Recommended for Clarity)

```bash
./.claude-work/workflow.sh document.docx .claude-work/edits/corrections.yaml
./.claude-work/edit.sh .claude-work/edits/corrections.yaml
```

**Advantages:**
- ✅ Explicit and clear
- ✅ Works from any location
- ✅ No ambiguity

### Method 2: Short Path (Auto-Completion)

```bash
./.claude-work/workflow.sh document.docx edits/corrections.yaml
./.claude-work/edit.sh edits/corrections.yaml
```

**How it works:**
1. Script checks if file exists at given path
2. If not found, automatically tries `.claude-work/edits/<basename>`
3. Shows notification when auto-completion is used
4. Fails with helpful message if file still not found

**Advantages:**
- ✅ Shorter to type
- ✅ More convenient for quick edits
- ✅ Backward compatible with old examples

## Auto-Completion Logic

The scripts use this logic:

```bash
YAML_FILE="$2"

# If file doesn't exist at given path
if [ ! -f "$YAML_FILE" ]; then
    # Try .claude-work/edits/
    BASENAME_YAML=$(basename "$YAML_FILE")
    if [ -f "$SCRIPT_DIR/edits/$BASENAME_YAML" ]; then
        echo "注意: 自动将路径 '$YAML_FILE' 解析为 '$SCRIPT_DIR/edits/$BASENAME_YAML'"
        YAML_FILE="$SCRIPT_DIR/edits/$BASENAME_YAML"
    else
        echo "错误: 找不到配置文件: $YAML_FILE"
        exit 1
    fi
fi
```

## Examples

### All These Work:

```bash
# Full path
./.claude-work/workflow.sh doc.docx .claude-work/edits/my_edit.yaml

# Short path (relative to .claude-work/edits/)
./.claude-work/workflow.sh doc.docx edits/my_edit.yaml

# Just filename (searches in .claude-work/edits/)
./.claude-work/workflow.sh doc.docx my_edit.yaml

# Absolute path
./.claude-work/workflow.sh doc.docx /full/path/to/my_edit.yaml
```

### Auto-Completion Notification

When using short paths, you'll see:

```
注意: 自动将路径 'edits/corrections.yaml' 解析为 '.claude-work/edits/corrections.yaml'
```

This confirms the auto-completion worked correctly.

## Error Messages

### File Not Found

```
错误: 找不到配置文件: edits/nonexistent.yaml
请确认文件路径，或使用完整路径: .claude-work/edits/xxx.yaml
```

**Solution:**
1. Check file name spelling
2. Verify file exists: `ls .claude-work/edits/`
3. Use full path to avoid confusion

## Best Practices

### For Scripts/Automation

Use **full paths** for clarity and reliability:

```bash
#!/bin/bash
./.claude-work/workflow.sh document.docx .claude-work/edits/corrections.yaml
```

### For Interactive Use

Use **short paths** for convenience:

```bash
# Quick edits
./.claude-work/workflow.sh doc.docx edits/my_corrections.yaml
```

### For Documentation

Show **both options**:

```bash
# Full path (recommended)
./.claude-work/workflow.sh document.docx .claude-work/edits/corrections.yaml

# Short path (also works)
./.claude-work/workflow.sh document.docx edits/corrections.yaml
```

## Updated Scripts

The following scripts support auto-completion:

1. **workflow.sh** - Full workflow
2. **edit.sh** - Apply edits only

These scripts **do not** need auto-completion (they use direct paths):

1. **unpack.sh** - Takes document path only
2. **pack.sh** - Takes directory and output paths
3. **env.sh** - Environment setup

## Migration from Old Examples

Old examples used short paths without clarification:

```bash
# Old example (ambiguous)
./.claude-work/workflow.sh document.docx edits/corrections.yaml
```

Now works correctly with auto-completion. No changes needed to existing workflows!

## Troubleshooting

### "File not found" despite file existing

**Check:**
1. Current working directory: `pwd`
2. File location: `ls .claude-work/edits/`
3. File permissions: `ls -l .claude-work/edits/`

**Fix:**
Use absolute path or full relative path:
```bash
./.claude-work/workflow.sh doc.docx "$PWD/.claude-work/edits/corrections.yaml"
```

### Auto-completion picks wrong file

If multiple files with same name exist in different directories:

**Use full path** to be explicit:
```bash
./.claude-work/workflow.sh doc.docx .claude-work/edits/corrections.yaml
```

## Implementation Details

### Files Modified

1. `setup_project_env.sh`
   - Updated all examples to use full paths
   - Enhanced workflow.sh with auto-completion
   - Enhanced edit.sh with auto-completion
   - Improved help messages

2. `apply_edits.py`
   - Updated help message with correct example

3. `SKILL.md`
   - Fixed all path examples
   - Added note about auto-completion

4. `YAML_WORKFLOW_QUICKREF.md`
   - Updated all examples
   - Clarified path handling

### Backward Compatibility

✅ All old examples still work thanks to auto-completion
✅ No breaking changes to existing workflows
✅ Enhanced error messages guide users

## Summary

**For Users:**
- Both full and short paths work
- Scripts are smart and helpful
- Clear error messages when something's wrong

**For Claude:**
- Use full paths in documentation for clarity
- Mention auto-completion is available
- Show both options when explaining to users
