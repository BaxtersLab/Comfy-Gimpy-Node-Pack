"""
Tests for Marketplace Packaging System (Phase 9)
"""

import pytest
import json
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from gimp_comfy_bridge.packs import (
    MarketplacePackager,
    PackManifest,
    PackMetadata,
    PackFile,
    PackType,
    PackStatus,
    ValidationResult
)
from shared.types import PackInfo, ValidationInfo


class TestPackFile:
    """Test the PackFile class."""

    def test_file_creation(self):
        """Test creating a pack file."""
        pack_file = PackFile(
            path="templates/test_template.json",
            content_type="application/json",
            size=1024,
            checksum="abc123"
        )

        assert pack_file.path == "templates/test_template.json"
        assert pack_file.content_type == "application/json"
        assert pack_file.size == 1024
        assert pack_file.checksum == "abc123"

    def test_file_to_dict(self):
        """Test converting file to dictionary."""
        pack_file = PackFile("test.json", "application/json", 512, "def456")

        file_dict = pack_file.to_dict()
        assert file_dict["path"] == "test.json"
        assert file_dict["content_type"] == "application/json"
        assert file_dict["size"] == 512


class TestPackMetadata:
    """Test the PackMetadata class."""

    def test_metadata_creation(self):
        """Test creating pack metadata."""
        metadata = PackMetadata(
            name="Test Pack",
            version="1.0.0",
            description="A test pack",
            author="Test Author",
            tags=["test", "template"],
            dependencies={"gimp": ">=2.10"},
            homepage="https://example.com"
        )

        assert metadata.name == "Test Pack"
        assert metadata.version == "1.0.0"
        assert metadata.description == "A test pack"
        assert metadata.author == "Test Author"
        assert metadata.tags == ["test", "template"]

    def test_metadata_validation(self):
        """Test metadata validation."""
        # Valid metadata
        valid_metadata = PackMetadata(
            name="Valid Pack",
            version="1.0.0",
            description="Valid description",
            author="Author"
        )
        assert valid_metadata.validate() is True

        # Invalid - missing required fields
        invalid_metadata = PackMetadata(name="", version="", description="", author="")
        assert invalid_metadata.validate() is False

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = PackMetadata(
            name="Test Pack",
            version="1.0.0",
            description="Test description",
            author="Test Author"
        )

        metadata_dict = metadata.to_dict()
        assert metadata_dict["name"] == "Test Pack"
        assert metadata_dict["version"] == "1.0.0"


class TestPackManifest:
    """Test the PackManifest class."""

    def test_manifest_creation(self):
        """Test creating a pack manifest."""
        files = [
            PackFile("template.json", "application/json", 1024, "abc123"),
            PackFile("style.css", "text/css", 512, "def456")
        ]

        metadata = PackMetadata(
            name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="Test Author"
        )

        manifest = PackManifest(
            pack_id="test_pack_123",
            pack_type=PackType.TEMPLATE,
            metadata=metadata,
            files=files,
            created_at="2024-01-01T00:00:00Z"
        )

        assert manifest.pack_id == "test_pack_123"
        assert manifest.pack_type == PackType.TEMPLATE
        assert len(manifest.files) == 2

    def test_manifest_validation(self):
        """Test manifest validation."""
        files = [PackFile("test.json", "application/json", 100, "checksum")]
        metadata = PackMetadata("Test", "1.0.0", "Description", "Author")

        # Valid manifest
        valid_manifest = PackManifest(
            pack_id="valid_123",
            pack_type=PackType.TEMPLATE,
            metadata=metadata,
            files=files
        )
        assert valid_manifest.validate() is True

        # Invalid - empty files
        invalid_manifest = PackManifest(
            pack_id="invalid_123",
            pack_type=PackType.TEMPLATE,
            metadata=metadata,
            files=[]
        )
        assert invalid_manifest.validate() is False

    def test_manifest_to_dict(self):
        """Test converting manifest to dictionary."""
        files = [PackFile("test.json", "application/json", 100, "checksum")]
        metadata = PackMetadata("Test", "1.0.0", "Description", "Author")

        manifest = PackManifest(
            pack_id="test_123",
            pack_type=PackType.TEMPLATE,
            metadata=metadata,
            files=files
        )

        manifest_dict = manifest.to_dict()
        assert manifest_dict["pack_id"] == "test_123"
        assert manifest_dict["pack_type"] == "template"
        assert len(manifest_dict["files"]) == 1


class TestMarketplacePackager:
    """Test the marketplace packager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.packager = MarketplacePackager()

    def test_packager_initialization(self):
        """Test packager initializes correctly."""
        assert self.packager.max_pack_size == 100 * 1024 * 1024  # 100MB
        assert self.packager.supported_types == [PackType.TEMPLATE, PackType.STYLE, PackType.WORKFLOW]

    @patch('builtins.open')
    @patch('json.dump')
    def test_create_pack_from_directory(self, mock_json_dump, mock_open):
        """Test creating a pack from directory."""
        # Mock directory structure
        with patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch('os.path.getsize') as mock_getsize:

            mock_listdir.return_value = ["template.json", "style.css", "manifest.json"]
            mock_isfile.return_value = True
            mock_getsize.return_value = 1024

            # Create pack
            pack_path = self.packager.create_pack_from_directory(
                source_dir="/test/source",
                pack_type=PackType.TEMPLATE,
                metadata=PackMetadata("Test Pack", "1.0.0", "Description", "Author")
            )

            assert pack_path is not None
            # Verify manifest was written
            assert mock_json_dump.called

    def test_validate_pack_file(self):
        """Test pack file validation."""
        # Create a valid pack file in memory
        manifest = PackManifest(
            pack_id="test_123",
            pack_type=PackType.TEMPLATE,
            metadata=PackMetadata("Test", "1.0.0", "Description", "Author"),
            files=[PackFile("test.json", "application/json", 100, "checksum")]
        )

        # Create zip file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # Add manifest
            manifest_json = json.dumps(manifest.to_dict())
            zf.writestr("manifest.json", manifest_json)
            # Add a file
            zf.writestr("test.json", '{"test": "data"}')

        zip_buffer.seek(0)

        # Validate the pack
        with patch('builtins.open', return_value=zip_buffer):
            result = self.packager.validate_pack_file("test.zip")

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_pack_validation(self):
        """Test validation of invalid pack."""
        # Create invalid zip (missing manifest)
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("some_file.txt", "content")

        zip_buffer.seek(0)

        with patch('builtins.open', return_value=zip_buffer):
            result = self.packager.validate_pack_file("invalid.zip")

        assert result.is_valid is False
        assert len(result.errors) > 0

    @patch('zipfile.ZipFile')
    def test_extract_pack(self, mock_zipfile):
        """Test extracting a pack."""
        # Mock zip file
        mock_zf = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zf
        mock_zf.namelist.return_value = ["manifest.json", "template.json"]
        mock_zf.read.return_value = b'{"test": "data"}'

        # Extract pack
        extract_path = self.packager.extract_pack("test.zip", "/extract/to")

        assert extract_path == "/extract/to"
        mock_zf.extractall.assert_called_once_with("/extract/to")

    def test_get_pack_info(self):
        """Test getting pack information."""
        # Create test manifest
        manifest = PackManifest(
            pack_id="info_test_123",
            pack_type=PackType.STYLE,
            metadata=PackMetadata("Info Test", "2.0.0", "Info description", "Info Author"),
            files=[PackFile("style.css", "text/css", 2048, "hash123")]
        )

        # Mock reading manifest from zip
        with patch('zipfile.ZipFile') as mock_zipfile:
            mock_zf = Mock()
            mock_zipfile.return_value.__enter__.return_value = mock_zf
            mock_zf.read.return_value = json.dumps(manifest.to_dict()).encode()

            pack_info = self.packager.get_pack_info("test.zip")

            assert isinstance(pack_info, PackInfo)
            assert pack_info.id == "info_test_123"
            assert pack_info.name == "Info Test"
            assert pack_info.version == "2.0.0"

    def test_pack_type_validation(self):
        """Test pack type validation."""
        # Valid types
        assert self.packager._validate_pack_type(PackType.TEMPLATE) is True
        assert self.packager._validate_pack_type(PackType.STYLE) is True
        assert self.packager._validate_pack_type(PackType.WORKFLOW) is True

        # Invalid type
        assert self.packager._validate_pack_type("invalid_type") is False

    def test_file_size_validation(self):
        """Test file size validation."""
        # Valid size
        assert self.packager._validate_file_size(1024) is True

        # Too large
        assert self.packager._validate_file_size(200 * 1024 * 1024) is False  # 200MB

    @patch('hashlib.md5')
    def test_checksum_calculation(self, mock_md5):
        """Test checksum calculation."""
        mock_hash = Mock()
        mock_hash.hexdigest.return_value = "test_checksum"
        mock_md5.return_value = mock_hash

        checksum = self.packager._calculate_checksum(b"test data")

        assert checksum == "test_checksum"
        mock_md5.assert_called_once_with(b"test data")

    def test_dependency_resolution(self):
        """Test dependency resolution."""
        # Mock dependencies
        dependencies = {
            "gimp": ">=2.10",
            "python": ">=3.8"
        }

        # Mock system info
        system_info = {
            "gimp_version": "2.10.34",
            "python_version": "3.9.0"
        }

        with patch.object(self.packager, '_get_system_info', return_value=system_info):
            result = self.packager._check_dependencies(dependencies)

        assert result is True

    def test_dependency_conflict(self):
        """Test dependency conflict detection."""
        dependencies = {
            "gimp": ">=3.0"  # Requires newer version than available
        }

        system_info = {
            "gimp_version": "2.10.34"
        }

        with patch.object(self.packager, '_get_system_info', return_value=system_info):
            result = self.packager._check_dependencies(dependencies)

        assert result is False

    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_pack_installation(self, mock_makedirs, mock_exists):
        """Test pack installation."""
        mock_exists.return_value = False

        # Mock pack extraction
        with patch.object(self.packager, 'extract_pack') as mock_extract:
            mock_extract.return_value = "/install/path"

            install_path = self.packager.install_pack("test.zip", "/install/dir")

            assert install_path == "/install/path"
            mock_makedirs.assert_called()
            mock_extract.assert_called_once_with("test.zip", "/install/dir/test_pack")

    def test_pack_listing(self):
        """Test listing installed packs."""
        # Mock installed packs directory
        with patch('os.listdir') as mock_listdir, \
             patch('os.path.isdir') as mock_isdir:

            mock_listdir.return_value = ["pack1", "pack2", "not_a_pack"]
            mock_isdir.return_value = True

            # Mock manifest reading
            with patch.object(self.packager, 'get_pack_info') as mock_get_info:
                mock_get_info.return_value = PackInfo(
                    id="pack1",
                    name="Pack 1",
                    version="1.0.0",
                    pack_type="template",
                    description="Test pack",
                    author="Author"
                )

                packs = self.packager.list_installed_packs("/packs/dir")

                assert len(packs) == 2  # Should find 2 packs
                assert all(isinstance(p, PackInfo) for p in packs)

    def test_pack_update_check(self):
        """Test pack update checking."""
        # Mock current and latest versions
        current_version = "1.0.0"
        latest_version = "1.1.0"

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"version": latest_version}
            mock_get.return_value = mock_response

            needs_update = self.packager.check_for_updates("test_pack", current_version)

            assert needs_update is True

    def test_pack_backup(self):
        """Test pack backup creation."""
        with patch('shutil.copy2') as mock_copy:
            backup_path = self.packager.create_backup("/pack/path", "/backup/dir")

            assert backup_path is not None
            mock_copy.assert_called()

    def test_error_handling(self):
        """Test error handling in packager."""
        # Test with invalid zip file
        with patch('zipfile.ZipFile', side_effect=zipfile.BadZipFile):
            result = self.packager.validate_pack_file("invalid.zip")

            assert result.is_valid is False
            assert "Invalid zip file" in str(result.errors)

    def test_manifest_parsing(self):
        """Test manifest parsing from pack."""
        manifest_data = {
            "pack_id": "parse_test_123",
            "pack_type": "template",
            "metadata": {
                "name": "Parse Test",
                "version": "1.0.0",
                "description": "Parsing test",
                "author": "Parser"
            },
            "files": [{
                "path": "test.json",
                "content_type": "application/json",
                "size": 100,
                "checksum": "parse_checksum"
            }]
        }

        manifest = self.packager._parse_manifest(manifest_data)

        assert manifest.pack_id == "parse_test_123"
        assert manifest.pack_type == PackType.TEMPLATE
        assert manifest.metadata.name == "Parse Test"
        assert len(manifest.files) == 1