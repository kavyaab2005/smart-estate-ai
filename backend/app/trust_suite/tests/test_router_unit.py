"""
Unit tests for trust_suite router (no DB).
Tests validation logic, path traversal, magic bytes, file size limits, and auth checks.
"""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.trust_suite.router import (
    _validate_extension,
    _validate_magic_bytes,
    _read_file_chunks,
    _resolve_safe_path,
    _get_upload_dir,
    _process_uploaded_file,
    download_document,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    MAGIC_BYTES,
)
from app.models.user import User, RoleEnum
from app.trust_suite.models import TrustDocument, TrustDocumentSet
from app.models.property import Property


class TestExtensionValidation(unittest.TestCase):
    """Test file extension whitelist validation."""

    def test_allowed_extensions(self):
        for ext in [".pdf", ".jpg", ".jpeg", ".png", ".PDF", ".JPG", ".JPEG", ".PNG"]:
            result = _validate_extension(f"test{ext}")
            self.assertEqual(result, ext.lower())

    def test_rejected_extensions(self):
        for ext in [".html", ".exe", ".svg", ".php", ".js", ".txt", ".doc", ".docx", ""]:
            with self.assertRaises(HTTPException) as cm:
                _validate_extension(f"test{ext}")
            self.assertEqual(cm.exception.status_code, 400)
            self.assertIn("not allowed", cm.exception.detail)


class TestMagicBytesValidation(unittest.TestCase):
    """Test magic byte validation for file type verification."""

    def test_pdf_magic_bytes_valid(self):
        pdf_bytes = b"%PDF-1.4\n%...\x00"
        _validate_magic_bytes(pdf_bytes, ".pdf")

    def test_jpg_magic_bytes_valid(self):
        jpg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        _validate_magic_bytes(jpg_bytes, ".jpg")
        _validate_magic_bytes(jpg_bytes, ".jpeg")

    def test_png_magic_bytes_valid(self):
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        _validate_magic_bytes(png_bytes, ".png")

    def test_pdf_magic_bytes_invalid(self):
        fake_pdf = b"not a pdf"
        with self.assertRaises(HTTPException) as cm:
            _validate_magic_bytes(fake_pdf, ".pdf")
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("magic bytes mismatch", cm.exception.detail)

    def test_jpg_magic_bytes_invalid(self):
        fake_jpg = b"not a jpg"
        with self.assertRaises(HTTPException) as cm:
            _validate_magic_bytes(fake_jpg, ".jpg")
        self.assertEqual(cm.exception.status_code, 400)

    def test_png_magic_bytes_invalid(self):
        fake_png = b"not a png"
        with self.assertRaises(HTTPException) as cm:
            _validate_magic_bytes(fake_png, ".png")
        self.assertEqual(cm.exception.status_code, 400)

    def test_extension_mismatch_rejected(self):
        pdf_bytes = b"%PDF-1.4"
        with self.assertRaises(HTTPException) as cm:
            _validate_magic_bytes(pdf_bytes, ".jpg")
        self.assertEqual(cm.exception.status_code, 400)


class TestFileSizeLimit(unittest.TestCase):
    """Test file size limit enforcement with chunked reading."""

    def test_file_under_limit_accepted(self):
        content = b"%PDF" + b"x" * 1000
        mock_file = MagicMock(spec=UploadFile)
        mock_file.file = MagicMock()
        mock_file.file.read.side_effect = [content[:8192], content[8192:], b""]
        mock_file.filename = "test.pdf"
        
        result = _read_file_chunks(mock_file, MAX_FILE_SIZE)
        self.assertEqual(result, content)

    def test_file_at_limit_accepted(self):
        content = b"%PDF" + b"x" * (MAX_FILE_SIZE - 4)
        mock_file = MagicMock(spec=UploadFile)
        mock_file.file = MagicMock()
        chunks = [content[i:i+8192] for i in range(0, len(content), 8192)]
        chunks.append(b"")
        mock_file.file.read.side_effect = chunks
        mock_file.filename = "test.pdf"
        
        result = _read_file_chunks(mock_file, MAX_FILE_SIZE)
        self.assertEqual(result, content)

    def test_file_over_limit_rejected(self):
        content = b"%PDF" + b"x" * (MAX_FILE_SIZE + 100)
        mock_file = MagicMock(spec=UploadFile)
        mock_file.file = MagicMock()
        chunks = [content[i:i+8192] for i in range(0, len(content), 8192)]
        chunks.append(b"")
        mock_file.file.read.side_effect = chunks
        mock_file.filename = "test.pdf"
        
        with self.assertRaises(HTTPException) as cm:
            _read_file_chunks(mock_file, MAX_FILE_SIZE)
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("exceeds maximum", cm.exception.detail)

    def test_huge_file_not_fully_loaded(self):
        """Verify reading stops early and doesn't load entire huge file."""
        huge_content = b"%PDF" + b"x" * (MAX_FILE_SIZE * 2)
        mock_file = MagicMock(spec=UploadFile)
        mock_file.file = MagicMock()
        call_count = 0
        
        def read_side_effect(size):
            nonlocal call_count
            call_count += 1
            start = (call_count - 1) * size
            end = start + size
            if start >= len(huge_content):
                return b""
            return huge_content[start:end]
        
        mock_file.file.read.side_effect = read_side_effect
        mock_file.filename = "test.pdf"
        
        with self.assertRaises(HTTPException) as cm:
            _read_file_chunks(mock_file, MAX_FILE_SIZE)
        
        self.assertEqual(cm.exception.status_code, 400)
        expected_calls = (MAX_FILE_SIZE // 8192) + 2
        self.assertLessEqual(call_count, expected_calls)


class TestPathTraversalProtection(unittest.TestCase):
    """Test path traversal attack prevention in download endpoint."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_upload_dir = os.environ.get("TRUST_UPLOAD_DIR")
        os.environ["TRUST_UPLOAD_DIR"] = self.temp_dir
        # Force re-evaluation of _get_upload_dir by clearing any internal state
        import app.trust_suite.router as router_module
        # Clear any cached value
        if hasattr(router_module, '_UPLOAD_DIR_CACHE'):
            router_module._UPLOAD_DIR_CACHE = None

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if self.original_upload_dir is not None:
            os.environ["TRUST_UPLOAD_DIR"] = self.original_upload_dir
        else:
            os.environ.pop("TRUST_UPLOAD_DIR", None)

    def test_valid_path_inside_upload_dir(self):
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"%PDF test")
        
        result = _resolve_safe_path(str(test_file))
        self.assertEqual(result, test_file.resolve())

    def test_path_traversal_parent_directory(self):
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"%PDF test")
        
        traversal_path = str(Path(self.temp_dir) / ".." / "test.pdf")
        with self.assertRaises(HTTPException) as cm:
            _resolve_safe_path(traversal_path)
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("path traversal", cm.exception.detail.lower())

    def test_path_traversal_absolute_path_outside(self):
        with self.assertRaises(HTTPException) as cm:
            _resolve_safe_path("/etc/passwd")
        self.assertEqual(cm.exception.status_code, 400)

    def test_nonexistent_file_returns_404(self):
        nonexistent = Path(self.temp_dir) / "nonexistent.pdf"
        
        with self.assertRaises(HTTPException) as cm:
            _resolve_safe_path(str(nonexistent))
        self.assertEqual(cm.exception.status_code, 404)

    @unittest.skipIf(os.name == 'nt', "Symlinks require admin privileges on Windows")
    def test_symlink_outside_upload_dir_rejected(self):
        outside_dir = Path(tempfile.mkdtemp())
        try:
            target_file = outside_dir / "secret.pdf"
            target_file.write_bytes(b"%PDF secret")
            
            link_path = Path(self.temp_dir) / "link.pdf"
            link_path.symlink_to(target_file)
            
            with self.assertRaises(HTTPException) as cm:
                _resolve_safe_path(str(link_path))
            self.assertEqual(cm.exception.status_code, 400)
        finally:
            import shutil
            shutil.rmtree(outside_dir, ignore_errors=True)


class TestProcessUploadedFile(unittest.TestCase):
    """Test the _process_uploaded_file function that combines validation steps."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_upload_dir = os.environ.get("TRUST_UPLOAD_DIR")
        os.environ["TRUST_UPLOAD_DIR"] = self.temp_dir
        import app.trust_suite.router as router_module
        if hasattr(router_module, '_UPLOAD_DIR_CACHE'):
            router_module._UPLOAD_DIR_CACHE = None

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if self.original_upload_dir is not None:
            os.environ["TRUST_UPLOAD_DIR"] = self.original_upload_dir
        else:
            os.environ.pop("TRUST_UPLOAD_DIR", None)

    def test_valid_pdf_processed(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.file = MagicMock()
        content = b"%PDF valid content"
        mock_file.file.read.side_effect = [content, b""]
        
        doc_id = uuid4()
        file_path, file_bytes = _process_uploaded_file(mock_file, doc_id)
        
        self.assertEqual(file_bytes, content)
        self.assertTrue(file_path.endswith(f"{doc_id}.pdf"))
        self.assertTrue(str(Path(self.temp_dir).resolve()) in file_path)

    def test_invalid_extension_rejected(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.html"
        mock_file.file = MagicMock()
        mock_file.file.read.side_effect = [b"<html>", b""]
        
        doc_id = uuid4()
        with self.assertRaises(HTTPException) as cm:
            _process_uploaded_file(mock_file, doc_id)
        self.assertEqual(cm.exception.status_code, 400)

    def test_magic_bytes_mismatch_rejected(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.file = MagicMock()
        mock_file.file.read.side_effect = [b"not a pdf", b""]
        
        doc_id = uuid4()
        with self.assertRaises(HTTPException) as cm:
            _process_uploaded_file(mock_file, doc_id)
        self.assertEqual(cm.exception.status_code, 400)

    def test_oversize_rejected(self):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.file = MagicMock()
        content = b"%PDF" + b"x" * (MAX_FILE_SIZE + 100)
        chunks = [content[i:i+8192] for i in range(0, len(content), 8192)]
        chunks.append(b"")
        mock_file.file.read.side_effect = chunks
        
        doc_id = uuid4()
        with self.assertRaises(HTTPException) as cm:
            _process_uploaded_file(mock_file, doc_id)
        self.assertEqual(cm.exception.status_code, 400)


class TestDownloadAuthChecks(unittest.TestCase):
    """Test download endpoint authorization (owner or admin only)."""

    def setUp(self):
        self.owner_id = uuid4()
        self.other_user_id = uuid4()
        self.admin_id = uuid4()
        self.doc_id = uuid4()
        self.property_id = uuid4()
        self.doc_set_id = uuid4()

    def make_user(self, user_id, role="buyer"):
        user = MagicMock(spec=User)
        user.id = user_id
        user.role = role
        return user

    def make_property(self, agent_id):
        prop = MagicMock(spec=Property)
        prop.id = self.property_id
        prop.agent_id = agent_id
        return prop

    def make_doc_set(self):
        ds = MagicMock(spec=TrustDocumentSet)
        ds.id = self.doc_set_id
        ds.property_id = self.property_id
        return ds

    def make_trust_doc(self, file_path="/tmp/test.pdf"):
        doc = MagicMock(spec=TrustDocument)
        doc.document_id = self.doc_id
        doc.document_set_id = self.doc_set_id
        doc.file_url = file_path
        return doc

    @patch("app.trust_suite.router.get_document_set")
    @patch("app.trust_suite.router.get_property")
    @patch("app.trust_suite.router._resolve_safe_path")
    def test_owner_can_download(self, mock_resolve, mock_get_prop, mock_get_ds):
        mock_get_ds.return_value = self.make_doc_set()
        mock_get_prop.return_value = self.make_property(self.owner_id)
        mock_resolve.return_value = Path("/tmp/test.pdf")
        
        # Mock db.query for TrustDocument
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_trust_doc = self.make_trust_doc()
        mock_query.filter.return_value.first.return_value = mock_trust_doc
        mock_db.query.return_value = mock_query
        
        current_user = self.make_user(self.owner_id, "buyer")
        
        result = download_document(self.doc_id, mock_db, current_user)
        
        self.assertIsInstance(result, FileResponse)
        self.assertEqual(result.headers["Content-Disposition"], 'attachment; filename="test.pdf"')
        self.assertEqual(result.headers["X-Content-Type-Options"], "nosniff")

    @patch("app.trust_suite.router.get_document_set")
    @patch("app.trust_suite.router.get_property")
    @patch("app.trust_suite.router._resolve_safe_path")
    def test_admin_can_download(self, mock_resolve, mock_get_prop, mock_get_ds):
        mock_get_ds.return_value = self.make_doc_set()
        mock_get_prop.return_value = self.make_property(self.owner_id)
        mock_resolve.return_value = Path("/tmp/test.pdf")
        
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_trust_doc = self.make_trust_doc()
        mock_query.filter.return_value.first.return_value = mock_trust_doc
        mock_db.query.return_value = mock_query
        
        current_user = self.make_user(self.admin_id, "admin")
        
        result = download_document(self.doc_id, mock_db, current_user)
        
        self.assertIsInstance(result, FileResponse)

    @patch("app.trust_suite.router.get_document_set")
    @patch("app.trust_suite.router.get_property")
    def test_non_owner_non_admin_rejected(self, mock_get_prop, mock_get_ds):
        mock_get_ds.return_value = self.make_doc_set()
        mock_get_prop.return_value = self.make_property(self.owner_id)
        
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_trust_doc = self.make_trust_doc()
        mock_query.filter.return_value.first.return_value = mock_trust_doc
        mock_db.query.return_value = mock_query
        
        current_user = self.make_user(self.other_user_id, "buyer")
        
        with self.assertRaises(HTTPException) as cm:
            download_document(self.doc_id, mock_db, current_user)
        
        self.assertEqual(cm.exception.status_code, 403)

    @patch("app.trust_suite.router.get_document_set")
    def test_nonexistent_document_returns_404(self, mock_get_ds):
        mock_get_ds.return_value = None
        
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        current_user = self.make_user(self.owner_id, "buyer")
        
        with self.assertRaises(HTTPException) as cm:
            download_document(self.doc_id, mock_db, current_user)
        
        self.assertEqual(cm.exception.status_code, 404)


class TestLazyUploadDirCreation(unittest.TestCase):
    """Test that upload directory is created lazily, not at import time."""

    def test_upload_dir_not_created_at_import(self):
        """Verify _get_upload_dir creates directory when called, not at module load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "lazy_test_dir"
            os.environ["TRUST_UPLOAD_DIR"] = str(test_dir)
            
            from importlib import reload
            import app.trust_suite.router as router_module
            reload(router_module)
            
            self.assertFalse(test_dir.exists(), "Directory should not exist at import")
            
            result = router_module._get_upload_dir()
            
            self.assertTrue(test_dir.exists(), "Directory should exist after first call")
            self.assertEqual(result, test_dir.resolve())


if __name__ == "__main__":
    unittest.main()