"""
Unit tests for trust_suite repository functions (no DB).
Tests verify locking behavior and function signatures using mocks.
"""
import unittest
from unittest.mock import MagicMock, patch, call
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.trust_suite.repository import (
    get_property,
    get_property_for_update,
    get_review_queue,
    get_review_queue_no_lock,
    get_review_queue_for_update,
    get_document_set,
    get_document_set_for_update,
)
from app.trust_suite.models import TrustReviewQueue, TrustDocumentSet
from app.models.property import Property


class TestRepositoryLocking(unittest.TestCase):
    """Test that repository functions use correct locking behavior."""

    def setUp(self):
        self.db = MagicMock(spec=Session)
        self.property_id = uuid4()
        self.doc_set_id = uuid4()
        self.queue_id = uuid4()

    def test_get_property_no_lock(self):
        """get_property should use db.query().filter().first() (no lock)."""
        mock_prop = MagicMock(spec=Property)
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_prop
        self.db.query.return_value = mock_query

        result = get_property(self.db, self.property_id)

        self.db.query.assert_called_once_with(Property)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()
        self.assertEqual(result, mock_prop)

    def test_get_property_for_update_uses_with_for_update(self):
        """get_property_for_update should use query().filter().with_for_update().first()."""
        mock_prop = MagicMock(spec=Property)
        mock_query = MagicMock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_prop
        self.db.query.return_value = mock_query

        result = get_property_for_update(self.db, self.property_id)

        self.db.query.assert_called_once_with(Property)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.with_for_update.assert_called_once()
        mock_query.filter.return_value.with_for_update.return_value.first.assert_called_once()
        self.assertEqual(result, mock_prop)

    def test_get_review_queue_no_lock_by_docset(self):
        """get_review_queue should use query().filter().first() (no lock, for reads)."""
        mock_queue = MagicMock(spec=TrustReviewQueue)
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_queue
        self.db.query.return_value = mock_query

        result = get_review_queue(self.db, self.doc_set_id)

        self.db.query.assert_called_once_with(TrustReviewQueue)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()
        self.assertEqual(result, mock_queue)

    def test_get_review_queue_no_lock_by_id(self):
        """get_review_queue_no_lock should use query().filter().first() (no lock, for reads)."""
        mock_queue = MagicMock(spec=TrustReviewQueue)
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_queue
        self.db.query.return_value = mock_query

        result = get_review_queue_no_lock(self.db, self.queue_id)

        self.db.query.assert_called_once_with(TrustReviewQueue)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()
        self.assertEqual(result, mock_queue)

    def test_get_review_queue_for_update_uses_lock(self):
        """get_review_queue_for_update should use with_for_update (for decision/checklist updates)."""
        mock_queue = MagicMock(spec=TrustReviewQueue)
        mock_query = MagicMock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_queue
        self.db.query.return_value = mock_query

        result = get_review_queue_for_update(self.db, self.queue_id)

        self.db.query.assert_called_once_with(TrustReviewQueue)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.with_for_update.assert_called_once()
        mock_query.filter.return_value.with_for_update.return_value.first.assert_called_once()
        self.assertEqual(result, mock_queue)

    def test_get_document_set_no_lock(self):
        """get_document_set should use query().filter().first() (no lock, for reads)."""
        mock_docset = MagicMock(spec=TrustDocumentSet)
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_docset
        self.db.query.return_value = mock_query

        result = get_document_set(self.db, self.doc_set_id)

        self.db.query.assert_called_once_with(TrustDocumentSet)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()
        self.assertEqual(result, mock_docset)

    def test_get_document_set_for_update_uses_lock(self):
        """get_document_set_for_update should use with_for_update (for writes)."""
        mock_docset = MagicMock(spec=TrustDocumentSet)
        mock_query = MagicMock()
        mock_query.filter.return_value.with_for_update.return_value.first.return_value = mock_docset
        self.db.query.return_value = mock_query

        result = get_document_set_for_update(self.db, self.doc_set_id)

        self.db.query.assert_called_once_with(TrustDocumentSet)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.with_for_update.assert_called_once()
        mock_query.filter.return_value.with_for_update.return_value.first.assert_called_once()
        self.assertEqual(result, mock_docset)


class TestRepositoryLockOrder(unittest.TestCase):
    """Test that lock order is consistent (queue first, then property)."""

    def test_lock_order_documented(self):
        """Verify lock order is documented in function docstrings."""
        self.assertIn("queue row first", get_review_queue_for_update.__doc__ or "")
        self.assertIn("queue row first", get_property_for_update.__doc__ or "")


if __name__ == "__main__":
    unittest.main()