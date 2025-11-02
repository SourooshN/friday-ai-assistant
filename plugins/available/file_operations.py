"""
File Operations Plugin for Friday AI Assistant

Provides comprehensive file and folder management capabilities including:
- File CRUD operations (create, read, update, delete)
- Folder operations (list, create, delete, navigate)
- File search and filtering
- Metadata and permissions handling
- Safe path validation and sandboxing

Security: All file operations are policy-checked, path-validated, and logged.
"""

import fnmatch
import hashlib
import mimetypes
import os
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class FileOperationsPlugin:
    """
    File Operations Plugin for Friday AI Assistant.

    Provides secure file and folder management with comprehensive safety controls.
    """

    def __init__(self):
        self.id = "file_operations"
        self.version = "1.0.0"
        self.capabilities = ["file_crud", "folder_operations", "file_search", "metadata_handling", "path_validation"]

        # Security: Define allowed base paths
        self.allowed_base_paths = self._get_allowed_base_paths()

        # File operation history for memory integration
        self.operation_history = []

    def _get_allowed_base_paths(self) -> List[str]:
        """Get list of allowed base paths for file operations."""
        # Default allowed paths - can be configured via policy
        home_dir = str(Path.home())
        current_dir = str(Path.cwd())

        return [
            current_dir,
            os.path.join(current_dir, "data"),
            os.path.join(current_dir, "docs"),
            os.path.join(current_dir, "tests"),
            os.path.join(current_dir, "config"),
            os.path.join(home_dir, "Documents"),
            os.path.join(home_dir, "Downloads"),
            os.path.join(home_dir, "Desktop"),
            "/tmp",
            "/var/tmp",
        ]

    def describe_tools(self) -> Dict[str, Any]:
        """Describe the tools provided by this plugin."""
        return {
            # File CRUD Operations
            "create_file": {
                "description": "Create a new file with specified content",
                "parameters": {
                    "file_path": {"type": "string", "description": "Path where to create the file", "required": True},
                    "content": {"type": "string", "description": "Content to write to the file", "default": ""},
                    "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
                },
                "security_level": "safe",
            },
            "read_file": {
                "description": "Read contents of a file",
                "parameters": {
                    "file_path": {"type": "string", "description": "Path to the file to read", "required": True},
                    "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
                    "max_size_mb": {"type": "integer", "description": "Maximum file size to read in MB", "default": 10},
                },
                "security_level": "safe",
            },
            "update_file": {
                "description": "Update/modify an existing file",
                "parameters": {
                    "file_path": {"type": "string", "description": "Path to the file to update", "required": True},
                    "content": {"type": "string", "description": "New content for the file", "required": True},
                    "mode": {"type": "string", "description": "Update mode: overwrite, append, prepend", "default": "overwrite"},
                    "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
                },
                "security_level": "safe",
            },
            "delete_file": {
                "description": "Delete a file",
                "parameters": {
                    "file_path": {"type": "string", "description": "Path to the file to delete", "required": True},
                    "confirm": {"type": "boolean", "description": "Confirmation for deletion", "default": False},
                },
                "security_level": "privileged",
            },
            # Folder Operations
            "list_directory": {
                "description": "List contents of a directory",
                "parameters": {
                    "directory_path": {"type": "string", "description": "Path to the directory to list", "default": "."},
                    "show_hidden": {"type": "boolean", "description": "Include hidden files", "default": False},
                    "recursive": {"type": "boolean", "description": "List recursively", "default": False},
                    "max_depth": {"type": "integer", "description": "Maximum recursion depth", "default": 3},
                },
                "security_level": "safe",
            },
            "create_directory": {
                "description": "Create a new directory",
                "parameters": {
                    "directory_path": {"type": "string", "description": "Path where to create the directory", "required": True},
                    "parents": {"type": "boolean", "description": "Create parent directories if needed", "default": True},
                },
                "security_level": "safe",
            },
            "delete_directory": {
                "description": "Delete a directory",
                "parameters": {
                    "directory_path": {"type": "string", "description": "Path to the directory to delete", "required": True},
                    "recursive": {"type": "boolean", "description": "Delete recursively (non-empty directories)", "default": False},
                    "confirm": {"type": "boolean", "description": "Confirmation for deletion", "default": False},
                },
                "security_level": "privileged",
            },
            # File Information and Metadata
            "get_file_info": {
                "description": "Get detailed information about a file or directory",
                "parameters": {"path": {"type": "string", "description": "Path to the file or directory", "required": True}},
                "security_level": "safe",
            },
            "copy_file": {
                "description": "Copy a file or directory",
                "parameters": {
                    "source_path": {"type": "string", "description": "Source file/directory path", "required": True},
                    "destination_path": {"type": "string", "description": "Destination path", "required": True},
                    "overwrite": {"type": "boolean", "description": "Overwrite if destination exists", "default": False},
                },
                "security_level": "safe",
            },
            "move_file": {
                "description": "Move/rename a file or directory",
                "parameters": {
                    "source_path": {"type": "string", "description": "Source file/directory path", "required": True},
                    "destination_path": {"type": "string", "description": "Destination path", "required": True},
                    "overwrite": {"type": "boolean", "description": "Overwrite if destination exists", "default": False},
                },
                "security_level": "safe",
            },
            # Search and Filtering
            "search_files": {
                "description": "Search for files matching criteria",
                "parameters": {
                    "base_path": {"type": "string", "description": "Base directory to search in", "default": "."},
                    "pattern": {"type": "string", "description": "File name pattern (glob style)", "default": "*"},
                    "content_search": {"type": "string", "description": "Search for content within files", "default": None},
                    "file_type": {"type": "string", "description": "File type filter (extension)", "default": None},
                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 100},
                },
                "security_level": "safe",
            },
            # Utility Operations
            "get_file_hash": {
                "description": "Calculate hash (checksum) of a file",
                "parameters": {
                    "file_path": {"type": "string", "description": "Path to the file", "required": True},
                    "algorithm": {"type": "string", "description": "Hash algorithm (md5, sha1, sha256)", "default": "sha256"},
                },
                "security_level": "safe",
            },
        }

    def invoke(self, tool: str, **kwargs) -> Dict[str, Any]:
        """
        Invoke a tool provided by this plugin.

        Args:
            tool: Tool name to invoke
            **kwargs: Tool parameters

        Returns:
            Tool result with success status and data/error information
        """
        try:
            # Record operation for history
            operation_record = {"timestamp": datetime.utcnow().isoformat(), "tool": tool, "parameters": kwargs}

            # Route to appropriate handler
            if tool == "create_file":
                result = self._create_file(**kwargs)
            elif tool == "read_file":
                result = self._read_file(**kwargs)
            elif tool == "update_file":
                result = self._update_file(**kwargs)
            elif tool == "delete_file":
                result = self._delete_file(**kwargs)
            elif tool == "list_directory":
                result = self._list_directory(**kwargs)
            elif tool == "create_directory":
                result = self._create_directory(**kwargs)
            elif tool == "delete_directory":
                result = self._delete_directory(**kwargs)
            elif tool == "get_file_info":
                result = self._get_file_info(**kwargs)
            elif tool == "copy_file":
                result = self._copy_file(**kwargs)
            elif tool == "move_file":
                result = self._move_file(**kwargs)
            elif tool == "search_files":
                result = self._search_files(**kwargs)
            elif tool == "get_file_hash":
                result = self._get_file_hash(**kwargs)
            else:
                return {"success": False, "error": f"Unknown tool: {tool}", "available_tools": list(self.describe_tools().keys())}

            # Add to operation history
            operation_record["result"] = result
            operation_record["success"] = result.get("success", False)
            self.operation_history.append(operation_record)

            return result

        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}", "tool": tool}

    def _validate_path(self, path: str, operation: str = "access") -> bool:
        """
        Validate that a path is allowed for file operations.

        Args:
            path: Path to validate
            operation: Type of operation (access, create, delete)

        Returns:
            True if path is allowed, False otherwise
        """
        try:
            # Convert to absolute path
            abs_path = os.path.abspath(path)

            # Check if path is within allowed base paths
            for allowed_base in self.allowed_base_paths:
                abs_base = os.path.abspath(allowed_base)
                if abs_path.startswith(abs_base):
                    return True

            # Additional security checks
            # Prevent access to sensitive system directories
            forbidden_paths = ["/etc", "/root", "/boot", "/sys", "/proc", "/dev", "/var/log", "/usr/bin", "/bin", "/sbin"]

            for forbidden in forbidden_paths:
                if abs_path.startswith(forbidden):
                    return False

            return False

        except Exception:
            return False

    def _get_safe_path(self, path: str) -> Path:
        """
        Get a safe Path object with validation.

        Args:
            path: Path string to convert

        Returns:
            Path object

        Raises:
            PermissionError: If path is not allowed
        """
        if not self._validate_path(path):
            raise PermissionError(f"Access denied to path: {path}")

        return Path(path)

    # File CRUD Operations
    def _create_file(self, file_path: str, content: str = "", encoding: str = "utf-8") -> Dict[str, Any]:
        """Create a new file with specified content."""
        try:
            path = self._get_safe_path(file_path)

            # Check if file already exists
            if path.exists():
                return {"success": False, "error": f"File already exists: {file_path}"}

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            with open(path, "w", encoding=encoding) as f:
                f.write(content)

            file_size = path.stat().st_size
            return {"success": True, "data": {"file_path": str(path), "size": file_size, "encoding": encoding, "action": "created"}}

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to create file: {e}"}

    def _read_file(self, file_path: str, encoding: str = "utf-8", max_size_mb: int = 10) -> Dict[str, Any]:
        """Read contents of a file."""
        try:
            path = self._get_safe_path(file_path)

            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            # Check file size
            file_size = path.stat().st_size
            max_size_bytes = max_size_mb * 1024 * 1024

            if file_size > max_size_bytes:
                return {"success": False, "error": f"File too large: {file_size} bytes (max: {max_size_bytes})"}

            # Read file content
            with open(path, "r", encoding=encoding) as f:
                content = f.read()

            return {
                "success": True,
                "data": {"file_path": str(path), "content": content, "size": file_size, "encoding": encoding, "lines": len(content.splitlines())},
            }

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except UnicodeDecodeError as e:
            return {"success": False, "error": f"Encoding error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {e}"}

    def _update_file(self, file_path: str, content: str, mode: str = "overwrite", encoding: str = "utf-8") -> Dict[str, Any]:
        """Update/modify an existing file."""
        try:
            path = self._get_safe_path(file_path)

            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            # Get original size for comparison
            original_size = path.stat().st_size

            if mode == "overwrite":
                with open(path, "w", encoding=encoding) as f:
                    f.write(content)
            elif mode == "append":
                with open(path, "a", encoding=encoding) as f:
                    f.write(content)
            elif mode == "prepend":
                # Read existing content first
                with open(path, "r", encoding=encoding) as f:
                    existing_content = f.read()
                with open(path, "w", encoding=encoding) as f:
                    f.write(content + existing_content)
            else:
                return {"success": False, "error": f"Invalid update mode: {mode}"}

            new_size = path.stat().st_size
            return {
                "success": True,
                "data": {
                    "file_path": str(path),
                    "mode": mode,
                    "original_size": original_size,
                    "new_size": new_size,
                    "size_change": new_size - original_size,
                    "action": "updated",
                },
            }

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to update file: {e}"}

    def _delete_file(self, file_path: str, confirm: bool = False) -> Dict[str, Any]:
        """Delete a file."""
        try:
            if not confirm:
                return {"success": False, "error": "File deletion requires confirmation (set confirm=True)"}

            path = self._get_safe_path(file_path)

            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            file_size = path.stat().st_size
            path.unlink()

            return {"success": True, "data": {"file_path": str(path), "size": file_size, "action": "deleted"}}

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to delete file: {e}"}

    # Folder Operations
    def _list_directory(self, directory_path: str = ".", show_hidden: bool = False, recursive: bool = False, max_depth: int = 3) -> Dict[str, Any]:
        """List contents of a directory."""
        try:
            path = self._get_safe_path(directory_path)

            if not path.exists():
                return {"success": False, "error": f"Directory not found: {directory_path}"}

            if not path.is_dir():
                return {"success": False, "error": f"Path is not a directory: {directory_path}"}

            items = []

            def _scan_directory(dir_path: Path, current_depth: int = 0):
                if current_depth > max_depth:
                    return

                try:
                    for item in dir_path.iterdir():
                        # Skip hidden files unless requested
                        if not show_hidden and item.name.startswith("."):
                            continue

                        stat_info = item.stat()
                        item_info = {
                            "name": item.name,
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat_info.st_size if item.is_file() else None,
                            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                            "permissions": stat.filemode(stat_info.st_mode),
                            "depth": current_depth,
                        }

                        # Add MIME type for files
                        if item.is_file():
                            mime_type, _ = mimetypes.guess_type(str(item))
                            item_info["mime_type"] = mime_type

                        items.append(item_info)

                        # Recurse into subdirectories if requested
                        if recursive and item.is_dir() and current_depth < max_depth:
                            _scan_directory(item, current_depth + 1)

                except PermissionError:
                    # Skip directories we can't access
                    pass

            _scan_directory(path)

            return {
                "success": True,
                "data": {
                    "directory_path": str(path),
                    "items": items,
                    "total_items": len(items),
                    "directories": len([i for i in items if i["type"] == "directory"]),
                    "files": len([i for i in items if i["type"] == "file"]),
                    "recursive": recursive,
                    "show_hidden": show_hidden,
                },
            }

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to list directory: {e}"}

    def _create_directory(self, directory_path: str, parents: bool = True) -> Dict[str, Any]:
        """Create a new directory."""
        try:
            path = self._get_safe_path(directory_path)

            if path.exists():
                return {"success": False, "error": f"Directory already exists: {directory_path}"}

            path.mkdir(parents=parents, exist_ok=False)

            return {"success": True, "data": {"directory_path": str(path), "parents_created": parents, "action": "created"}}

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to create directory: {e}"}

    def _delete_directory(self, directory_path: str, recursive: bool = False, confirm: bool = False) -> Dict[str, Any]:
        """Delete a directory."""
        try:
            if not confirm:
                return {"success": False, "error": "Directory deletion requires confirmation (set confirm=True)"}

            path = self._get_safe_path(directory_path)

            if not path.exists():
                return {"success": False, "error": f"Directory not found: {directory_path}"}

            if not path.is_dir():
                return {"success": False, "error": f"Path is not a directory: {directory_path}"}

            # Check if directory is empty
            if not recursive and any(path.iterdir()):
                return {"success": False, "error": f"Directory is not empty: {directory_path} (use recursive=True to force)"}

            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()

            return {"success": True, "data": {"directory_path": str(path), "recursive": recursive, "action": "deleted"}}

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to delete directory: {e}"}

    # Utility Operations
    def _get_file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed information about a file or directory."""
        try:
            file_path = self._get_safe_path(path)

            if not file_path.exists():
                return {"success": False, "error": f"Path not found: {path}"}

            stat_info = file_path.stat()

            info = {
                "path": str(file_path),
                "name": file_path.name,
                "type": "directory" if file_path.is_dir() else "file",
                "size": stat_info.st_size,
                "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                "permissions": stat.filemode(stat_info.st_mode),
                "owner_uid": stat_info.st_uid,
                "group_gid": stat_info.st_gid,
                "is_hidden": file_path.name.startswith("."),
                "is_symlink": file_path.is_symlink(),
            }

            # Add file-specific information
            if file_path.is_file():
                mime_type, encoding = mimetypes.guess_type(str(file_path))
                info.update({"mime_type": mime_type, "encoding": encoding, "extension": file_path.suffix})

            # Add directory-specific information
            elif file_path.is_dir():
                try:
                    contents = list(file_path.iterdir())
                    info.update(
                        {
                            "item_count": len(contents),
                            "subdirectories": len([item for item in contents if item.is_dir()]),
                            "files": len([item for item in contents if item.is_file()]),
                        }
                    )
                except PermissionError:
                    info.update({"item_count": "Permission denied", "subdirectories": "Unknown", "files": "Unknown"})

            return {"success": True, "data": info}

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to get file info: {e}"}

    def _copy_file(self, source_path: str, destination_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Copy a file or directory."""
        try:
            src_path = self._get_safe_path(source_path)
            dst_path = self._get_safe_path(destination_path)

            if not src_path.exists():
                return {"success": False, "error": f"Source not found: {source_path}"}

            if dst_path.exists() and not overwrite:
                return {"success": False, "error": f"Destination exists: {destination_path} (use overwrite=True to replace)"}

            if src_path.is_file():
                shutil.copy2(src_path, dst_path)
                operation = "file_copy"
            elif src_path.is_dir():
                if dst_path.exists():
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                operation = "directory_copy"
            else:
                return {"success": False, "error": f"Unsupported file type: {source_path}"}

            dst_size = dst_path.stat().st_size if dst_path.is_file() else sum(f.stat().st_size for f in dst_path.rglob("*") if f.is_file())

            return {
                "success": True,
                "data": {
                    "source_path": str(src_path),
                    "destination_path": str(dst_path),
                    "operation": operation,
                    "size": dst_size,
                    "overwrite": overwrite,
                    "action": "copied",
                },
            }

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to copy: {e}"}

    def _move_file(self, source_path: str, destination_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Move/rename a file or directory."""
        try:
            src_path = self._get_safe_path(source_path)
            dst_path = self._get_safe_path(destination_path)

            if not src_path.exists():
                return {"success": False, "error": f"Source not found: {source_path}"}

            if dst_path.exists() and not overwrite:
                return {"success": False, "error": f"Destination exists: {destination_path} (use overwrite=True to replace)"}

            # Get size before moving
            if src_path.is_file():
                size = src_path.stat().st_size
                operation = "file_move"
            elif src_path.is_dir():
                size = sum(f.stat().st_size for f in src_path.rglob("*") if f.is_file())
                operation = "directory_move"
            else:
                return {"success": False, "error": f"Unsupported file type: {source_path}"}

            # Remove destination if overwrite is enabled
            if dst_path.exists() and overwrite:
                if dst_path.is_file():
                    dst_path.unlink()
                elif dst_path.is_dir():
                    shutil.rmtree(dst_path)

            shutil.move(str(src_path), str(dst_path))

            return {
                "success": True,
                "data": {
                    "source_path": str(src_path),
                    "destination_path": str(dst_path),
                    "operation": operation,
                    "size": size,
                    "overwrite": overwrite,
                    "action": "moved",
                },
            }

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to move: {e}"}

    def _search_files(
        self, base_path: str = ".", pattern: str = "*", content_search: Optional[str] = None, file_type: Optional[str] = None, max_results: int = 100
    ) -> Dict[str, Any]:
        """Search for files matching criteria."""
        try:
            search_path = self._get_safe_path(base_path)

            if not search_path.exists():
                return {"success": False, "error": f"Search path not found: {base_path}"}

            if not search_path.is_dir():
                return {"success": False, "error": f"Search path is not a directory: {base_path}"}

            results = []
            total_searched = 0

            def _search_recursive(current_path: Path):
                nonlocal total_searched

                if len(results) >= max_results:
                    return

                try:
                    for item in current_path.iterdir():
                        total_searched += 1

                        if len(results) >= max_results:
                            break

                        # Skip hidden files
                        if item.name.startswith("."):
                            continue

                        # Recurse into directories first (before pattern matching)
                        # This ensures we search subdirectories even if their names don't match the pattern
                        if item.is_dir():
                            _search_recursive(item)
                            continue  # Don't add directories to results, only files

                        # Pattern matching (only for files)
                        if not fnmatch.fnmatch(item.name, pattern):
                            continue

                        # File type filtering
                        if file_type:
                            if not item.suffix.lower().endswith(file_type.lower()):
                                continue

                        # Content search for text files
                        content_match = True
                        if content_search:
                            try:
                                with open(item, "r", encoding="utf-8", errors="ignore") as f:
                                    file_content = f.read()
                                    content_match = content_search.lower() in file_content.lower()
                            except (OSError, UnicodeDecodeError):
                                content_match = False

                        if content_match:
                            stat_info = item.stat()
                            result_item = {
                                "path": str(item),
                                "name": item.name,
                                "type": "file",
                                "size": stat_info.st_size,
                                "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                                "match_type": "pattern",
                            }

                            if content_search:
                                result_item["match_type"] = "content"
                                result_item["content_search"] = content_search

                            results.append(result_item)

                except PermissionError:
                    # Skip directories we can't access
                    pass

            _search_recursive(search_path)

            return {
                "success": True,
                "data": {
                    "search_path": str(search_path),
                    "pattern": pattern,
                    "content_search": content_search,
                    "file_type": file_type,
                    "results": results,
                    "total_found": len(results),
                    "total_searched": total_searched,
                    "max_results": max_results,
                    "truncated": len(results) >= max_results,
                },
            }

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to search files: {e}"}

    def _get_file_hash(self, file_path: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """Calculate hash (checksum) of a file."""
        try:
            path = self._get_safe_path(file_path)

            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            # Get hash algorithm
            if algorithm.lower() == "md5":
                hasher = hashlib.md5()
            elif algorithm.lower() == "sha1":
                hasher = hashlib.sha1()
            elif algorithm.lower() == "sha256":
                hasher = hashlib.sha256()
            else:
                return {"success": False, "error": f"Unsupported hash algorithm: {algorithm}"}

            # Calculate hash
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)

            hash_value = hasher.hexdigest()
            file_size = path.stat().st_size

            return {"success": True, "data": {"file_path": str(path), "algorithm": algorithm.lower(), "hash": hash_value, "file_size": file_size}}

        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to calculate hash: {e}"}


def create_plugin():
    """Factory function to create the plugin instance."""
    return FileOperationsPlugin()


# Plugin metadata for discovery
PLUGIN_METADATA = {
    "id": "file_operations",
    "name": "File Operations Plugin",
    "version": "1.0.0",
    "description": "Comprehensive file and folder management with CRUD operations, search, and metadata handling",
    "author": "Friday AI Assistant",
    "capabilities": ["file_crud", "folder_operations", "file_search", "metadata_handling", "path_validation"],
    "security_levels": ["safe", "privileged"],
    "platforms": ["linux", "windows", "darwin"],
    "entry_point": "create_plugin",
}
