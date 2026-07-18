# Fix Server to Support Dynamic Project Paths

## Problem
The server ignores `X-Project-Path` header for file operations. It only uses `self.project_root` set at startup.

## Solution
Modify file API endpoints to support a `root` parameter that temporarily overrides `self.project_root`.

## Changes Needed

### 1. Modify `list_files()` method
Add optional `root` parameter that temporarily changes the project root:

```python
def list_files(self, path="", recursive=False, root=None):
    """List files in project directory."""
    # Use provided root or fall back to project_root
    effective_root = root if root else self.project_root
    
    # Use effective_root instead of self.project_root in _get_safe_path
    # ...
```

### 2. Modify `_get_safe_path()` method
Add optional `root` parameter:

```python
def _get_safe_path(self, requested_path, root=None):
    """Get safe absolute path within project root."""
    base_root = root if root else self.project_root
    # ... use base_root instead of self.project_root
```

### 3. Modify API handlers
Extract `X-Project-Path` header and pass to file methods:

```python
def _handle_file_list(self):
    # Get optional root override from header
    root_override = self.headers.get('X-Project-Path')
    
    result = self.ai_server.list_files(path, recursive, root=root_override)
```

## Implementation Order
1. Modify `_get_safe_path()` to accept optional `root` parameter
2. Modify `list_files()` to accept optional `root` parameter  
3. Modify `read_file()` to accept optional `root` parameter
4. Modify `write_file()` to accept optional `root` parameter
5. Update API handlers to extract header and pass to methods
6. Test with editor client

## Backward Compatibility
- All changes are optional parameters
- Existing behavior preserved when header not provided
