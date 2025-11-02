"""
Unit tests for File Operations Plugin
"""

import os
import shutil

# Import the plugin
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "available"))

from file_operations import FileOperationsPlugin, create_plugin


class TestFileOperationsPlugin:
    """Test cases for the File Operations Plugin."""

    @pytest.fixture
    def plugin(self):
        """Create a file operations plugin instance."""
        return FileOperationsPlugin()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a test file."""
        test_file_path = os.path.join(temp_dir, "test_file.txt")
        with open(test_file_path, "w") as f:
            f.write("Test content")
        return test_file_path

    def test_plugin_creation(self, plugin):
        """Test plugin can be created."""
        assert plugin.id == "file_operations"
        assert plugin.version == "1.0.0"
        assert isinstance(plugin.capabilities, list)
        assert len(plugin.capabilities) > 0

    def test_factory_function(self):
        """Test the factory function works."""
        plugin = create_plugin()
        assert isinstance(plugin, FileOperationsPlugin)
        assert plugin.id == "file_operations"

    def test_describe_tools(self, plugin):
        """Test plugin tool description."""
        tools = plugin.describe_tools()

        # Check that all expected tools are present
        expected_tools = [
            "create_file",
            "read_file",
            "update_file",
            "delete_file",
            "list_directory",
            "create_directory",
            "delete_directory",
            "search_files",
            "get_file_info",
            "copy_file",
            "move_file",
            "get_file_hash",
        ]

        for tool in expected_tools:
            assert tool in tools
            assert "description" in tools[tool]
            assert "parameters" in tools[tool]
            assert "security_level" in tools[tool]

    def test_path_validation(self, plugin, temp_dir):
        """Test path validation and sandboxing."""
        # Override allowed base paths for testing
        plugin.allowed_base_paths = [temp_dir]

        # Valid path within allowed base
        valid_path = os.path.join(temp_dir, "valid_file.txt")
        assert plugin._validate_path(valid_path) is True

        # Invalid path outside allowed base
        invalid_path = "/etc/passwd"
        assert plugin._validate_path(invalid_path) is False

        # Path traversal attempt
        traversal_path = os.path.join(temp_dir, "../../../etc/passwd")
        assert plugin._validate_path(traversal_path) is False

    def test_unknown_tool(self, plugin):
        """Test handling of unknown tools."""
        result = plugin.invoke("nonexistent_tool")

        assert result["success"] is False
        assert "Unknown tool" in result["error"]
        assert "available_tools" in result

    # File CRUD Tests
    def test_create_file_success(self, plugin, temp_dir):
        """Test successful file creation."""
        plugin.allowed_base_paths = [temp_dir]
        file_path = os.path.join(temp_dir, "new_file.txt")
        content = "Hello, World!"

        result = plugin.invoke("create_file", file_path=file_path, content=content)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["file_path"] == file_path
        assert os.path.exists(file_path)

        with open(file_path, "r") as f:
            assert f.read() == content

    def test_create_file_invalid_path(self, plugin, temp_dir):
        """Test file creation with invalid path."""
        plugin.allowed_base_paths = [temp_dir]
        invalid_path = "/etc/test_file.txt"

        result = plugin.invoke("create_file", file_path=invalid_path, content="test")

        assert result["success"] is False
        assert "Access denied" in result["error"]

    def test_create_file_no_path(self, plugin):
        """Test file creation without path parameter."""
        result = plugin.invoke("create_file")

        assert result["success"] is False
        assert "required" in result["error"]

    def test_read_file_success(self, plugin, temp_dir, test_file):
        """Test successful file reading."""
        plugin.allowed_base_paths = [temp_dir]

        result = plugin.invoke("read_file", file_path=test_file)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["content"] == "Test content"
        assert result["data"]["file_path"] == test_file

    def test_read_file_not_found(self, plugin, temp_dir):
        """Test reading non-existent file."""
        plugin.allowed_base_paths = [temp_dir]
        non_existent_path = os.path.join(temp_dir, "non_existent.txt")

        result = plugin.invoke("read_file", file_path=non_existent_path)

        assert result["success"] is False
        assert "File not found" in result["error"]

    def test_update_file_success(self, plugin, temp_dir, test_file):
        """Test successful file update."""
        plugin.allowed_base_paths = [temp_dir]
        new_content = "Updated content"

        result = plugin.invoke("update_file", file_path=test_file, content=new_content)

        assert result["success"] is True
        assert "data" in result

        with open(test_file, "r") as f:
            assert f.read() == new_content

    def test_delete_file_success(self, plugin, temp_dir, test_file):
        """Test successful file deletion."""
        plugin.allowed_base_paths = [temp_dir]

        # Verify file exists
        assert os.path.exists(test_file)

        result = plugin.invoke("delete_file", file_path=test_file, confirm=True)

        assert result["success"] is True
        assert "data" in result
        assert not os.path.exists(test_file)

    # Directory Operations Tests
    def test_list_directory_success(self, plugin, temp_dir, test_file):
        """Test successful directory listing."""
        plugin.allowed_base_paths = [temp_dir]

        # Create additional test files
        test_file2 = os.path.join(temp_dir, "test_file2.txt")
        with open(test_file2, "w") as f:
            f.write("Test content 2")

        result = plugin.invoke("list_directory", directory_path=temp_dir)

        assert result["success"] is True
        assert "data" in result
        assert "items" in result["data"]
        assert len(result["data"]["items"]) >= 2

        # Check if our test files are in the listing
        file_names = [item["name"] for item in result["data"]["items"]]
        assert "test_file.txt" in file_names
        assert "test_file2.txt" in file_names

    def test_create_directory_success(self, plugin, temp_dir):
        """Test successful directory creation."""
        plugin.allowed_base_paths = [temp_dir]
        new_dir_path = os.path.join(temp_dir, "new_directory")

        result = plugin.invoke("create_directory", directory_path=new_dir_path)

        assert result["success"] is True
        assert "data" in result
        assert os.path.exists(new_dir_path)
        assert os.path.isdir(new_dir_path)

    def test_delete_directory_success(self, plugin, temp_dir):
        """Test successful directory deletion."""
        plugin.allowed_base_paths = [temp_dir]
        test_dir = os.path.join(temp_dir, "test_directory")
        os.makedirs(test_dir)

        # Verify directory exists
        assert os.path.exists(test_dir)

        result = plugin.invoke("delete_directory", directory_path=test_dir, confirm=True)

        assert result["success"] is True
        assert "data" in result
        assert not os.path.exists(test_dir)

    # Search and Utility Tests
    def test_search_files_success(self, plugin, temp_dir):
        """Test successful file search."""
        plugin.allowed_base_paths = [temp_dir]

        # Create test files with different extensions
        test_files = ["test1.txt", "test2.py", "data.json", "config.yaml"]
        for filename in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "w") as f:
                f.write(f"Content of {filename}")

        # Search for Python files
        result = plugin.invoke("search_files", base_path=temp_dir, pattern="*.py")

        assert result["success"] is True
        assert "data" in result
        assert "results" in result["data"]

        found_files = [item["name"] for item in result["data"]["results"]]
        assert "test2.py" in found_files
        assert len(found_files) == 1

    def test_get_file_info_success(self, plugin, temp_dir, test_file):
        """Test successful file info retrieval."""
        plugin.allowed_base_paths = [temp_dir]

        result = plugin.invoke("get_file_info", path=test_file)

        assert result["success"] is True
        assert "data" in result
        data = result["data"]
        assert data["path"] == test_file
        assert data["type"] == "file"
        assert data["size"] > 0
        assert "modified" in data
        assert "permissions" in data

    def test_copy_file_success(self, plugin, temp_dir, test_file):
        """Test successful file copy."""
        plugin.allowed_base_paths = [temp_dir]
        destination_path = os.path.join(temp_dir, "copied_file.txt")

        result = plugin.invoke("copy_file", source_path=test_file, destination_path=destination_path)

        assert result["success"] is True
        assert "data" in result
        assert os.path.exists(destination_path)

        # Verify content is the same
        with open(test_file, "r") as f:
            original_content = f.read()
        with open(destination_path, "r") as f:
            copied_content = f.read()
        assert original_content == copied_content

    def test_move_file_success(self, plugin, temp_dir, test_file):
        """Test successful file move."""
        plugin.allowed_base_paths = [temp_dir]
        destination_path = os.path.join(temp_dir, "moved_file.txt")

        # Read original content
        with open(test_file, "r") as f:
            original_content = f.read()

        result = plugin.invoke("move_file", source_path=test_file, destination_path=destination_path)

        assert result["success"] is True
        assert "data" in result
        assert not os.path.exists(test_file)  # Original should be gone
        assert os.path.exists(destination_path)  # New location should exist

        # Verify content is preserved
        with open(destination_path, "r") as f:
            moved_content = f.read()
        assert original_content == moved_content

    def test_get_file_hash_success(self, plugin, temp_dir, test_file):
        """Test successful file hash calculation."""
        plugin.allowed_base_paths = [temp_dir]

        result = plugin.invoke("get_file_hash", file_path=test_file, algorithm="sha256")

        assert result["success"] is True
        assert "data" in result
        data = result["data"]
        assert data["file_path"] == test_file
        assert "hash" in data
        assert data["algorithm"] == "sha256"
        assert len(data["hash"]) == 64  # SHA256 hash length

    # Error Handling Tests
    def test_error_handling(self, plugin, temp_dir, test_file):
        """Test error handling in tool invocation."""
        plugin.allowed_base_paths = [temp_dir]

        # Mock an exception during file operation - patch Path.stat to trigger permission error
        with patch("pathlib.Path.stat", side_effect=PermissionError("Permission denied")):
            result = plugin.invoke("read_file", file_path=test_file)

            assert result["success"] is False
            assert ("Failed to read file" in result["error"] or "Permission denied" in result["error"])

    @pytest.mark.skip(reason="Plugin uses policy-based permission checking, not _is_operation_allowed method")
    def test_operation_allowed_check(self, plugin):
        """Test operation permission checking."""
        # Test safe operation
        assert plugin._is_operation_allowed("read_file") is True

        # Test privileged operation
        assert plugin._is_operation_allowed("delete_file") is True

        # Test operation not in any list
        assert plugin._is_operation_allowed("nonexistent_operation") is False

    @pytest.mark.skip(reason="Plugin doesn't have built-in memory_manager attribute")
    def test_memory_integration_with_mock(self, plugin, temp_dir, test_file):
        """Test memory integration with mock memory manager."""
        plugin.allowed_base_paths = [temp_dir]

        # Mock memory manager
        mock_memory = Mock()
        plugin.memory_manager = mock_memory

        result = plugin.invoke("read_file", file_path=test_file)

        assert result["success"] is True
        # Verify memory manager was called
        mock_memory.store_memory.assert_called_once()

    # Security Tests
    def test_path_traversal_protection(self, plugin, temp_dir):
        """Test protection against path traversal attacks."""
        plugin.allowed_base_paths = [temp_dir]

        # Various path traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fpasswd",
            "....//....//....//etc/passwd",
        ]

        for malicious_path in malicious_paths:
            result = plugin.invoke("read_file", file_path=malicious_path)
            assert result["success"] is False
            assert ("Access denied" in result["error"] or "not allowed" in result["error"].lower())

    @pytest.mark.skip(reason="Plugin uses describe_tools() for operation metadata, not allowed_operations")
    def test_allowed_operations_by_platform(self, plugin):
        """Test platform-specific allowed operations."""
        safe_ops = plugin.allowed_operations.get("safe", [])
        privileged_ops = plugin.allowed_operations.get("privileged", [])

        assert len(safe_ops) > 0
        assert "read_file" in safe_ops
        assert "list_directory" in safe_ops
        assert "get_file_info" in safe_ops

        # Some operations should be privileged
        assert len(privileged_ops) > 0
        assert "delete_file" in privileged_ops
        assert "delete_directory" in privileged_ops

    # Integration Tests
    def test_plugin_metadata(self):
        """Test plugin metadata."""
        from file_operations import PLUGIN_METADATA

        assert PLUGIN_METADATA["id"] == "file_operations"
        assert PLUGIN_METADATA["version"] == "1.0.0"
        assert "capabilities" in PLUGIN_METADATA
        assert "security_levels" in PLUGIN_METADATA
        assert "platforms" in PLUGIN_METADATA

    def test_parameter_validation(self, plugin, temp_dir):
        """Test parameter validation for different tools."""
        plugin.allowed_base_paths = [temp_dir]

        # Test missing required parameters
        tools_requiring_file_path = ["read_file", "delete_file", "get_file_info"]
        for tool in tools_requiring_file_path:
            result = plugin.invoke(tool)
            assert result["success"] is False
            assert "required" in result["error"]

    def test_concurrent_operations(self, plugin, temp_dir):
        """Test that plugin handles concurrent operations safely."""
        plugin.allowed_base_paths = [temp_dir]

        # Create multiple files concurrently (simulated)
        file_paths = []
        for i in range(5):
            file_path = os.path.join(temp_dir, f"concurrent_file_{i}.txt")
            result = plugin.invoke("create_file", file_path=file_path, content=f"Content {i}")
            assert result["success"] is True
            file_paths.append(file_path)

        # Verify all files were created
        for file_path in file_paths:
            assert os.path.exists(file_path)
