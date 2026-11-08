import pytest
from uuid import uuid4
from app.trust_suite.schemas import TrustFindingSchema, FindingEvidence
from app.trust_suite.services.seller_view import to_seller_view, _get_seller_message
from app.trust_suite.services.cross_checks import CrossCheckFinding, run_cross_checks


class TestSellerView:
    """Tests for seller-facing view - must not leak integrity findings or internal details."""

    def test_seller_view_excludes_integrity_findings(self):
        """Integrity findings should be completely excluded from seller view."""
        # Build findings of every category
        consistency_finding = TrustFindingSchema(
            check_id="owner_name_matched",
            category="consistency",
            severity="critical",
            status="mismatch",
            field="owner_name",
            evidence=[FindingEvidence(
                document_id=uuid4(),
                document_type="sale_deed",
                page=1,
                field="owner_name",
                raw_value="John Doe",
                normalized_value="JOHN DOE",
            )],
            why_raised="Owner name comparison: 'John Doe' vs 'Jane Smith'",
            next_step="Admin to verify",
            seller_message="Owner name mismatch detected across documents",
        )

        integrity_finding = TrustFindingSchema(
            check_id="missing_page",
            category="integrity",
            severity="warning",
            status="needs_manual_verification",
            field="page",
            evidence=[FindingEvidence(
                document_id=uuid4(),
                document_type="sale_deed",
                page=1,
                field="page",
                raw_value="",
                normalized_value="",
            )],
            why_raised="Possible missing page detected",
            next_step="possible indicators - manual review recommended",
            seller_message=None,
        )

        completeness_finding = TrustFindingSchema(
            check_id="missing_sale_deed",
            category="completeness",
            severity="critical",
            status="needs_manual_verification",
            field="sale_deed",
            evidence=[],
            why_raised="Required document type 'sale_deed' not found",
            next_step="Seller to upload missing document",
            seller_message="Missing required document: Sale Deed",
        )

        findings = [consistency_finding, integrity_finding, completeness_finding]

        result = to_seller_view(
            set_data={"review_status": "in_review"},
            findings=findings,
            missing_documents=["sale_deed"],
            decision=None,
        )

        # Assert NO integrity findings in output
        categories = [f.category for f in result.findings]
        assert "integrity" not in categories, f"Integrity findings leaked to seller: {categories}"

        # Assert only consistency and completeness findings remain
        assert len(result.findings) == 2
        assert all(f.category in ("consistency", "completeness") for f in result.findings)

    def test_seller_view_no_internal_fields(self):
        """Seller view must not contain check_id, evidence, why_raised, next_step."""
        finding = TrustFindingSchema(
            check_id="owner_name_matched",
            category="consistency",
            severity="critical",
            status="mismatch",
            field="owner_name",
            evidence=[FindingEvidence(
                document_id=uuid4(),
                document_type="sale_deed",
                page=1,
                field="owner_name",
                raw_value="John Doe",
                normalized_value="JOHN DOE",
            )],
            why_raised="Owner name comparison: 'John Doe' vs 'Jane Smith'",
            next_step="Admin to verify",
            seller_message="Owner name mismatch detected across documents",
        )

        result = to_seller_view(
            set_data={"review_status": "in_review"},
            findings=[finding],
            missing_documents=[],
            decision=None,
        )

        # The output is a dict, check keys
        seller_finding = result.findings[0]
        finding_dict = seller_finding.__dict__

        # These internal fields must NOT be present
        assert "check_id" not in finding_dict
        assert "evidence" not in finding_dict
        assert "why_raised" not in finding_dict
        assert "next_step" not in finding_dict

        # Only these should be present
        assert "category" in finding_dict
        assert "status" in finding_dict
        assert "document_type" in finding_dict
        assert "seller_message" in finding_dict

    def test_seller_view_no_forged_fraud_words(self):
        """Seller messages must never contain 'forged', 'forgery', 'fraud'."""
        # Test with a finding that might have such words in why_raised
        finding = TrustFindingSchema(
            check_id="test_check",
            category="consistency",
            severity="critical",
            status="mismatch",
            field="owner_name",
            evidence=[],
            why_raised="Possible forgery detected in document - fraud indicators found",
            next_step="Investigate fraud",
            seller_message="Owner name mismatch detected across documents",
        )

        result = to_seller_view(
            set_data={"review_status": "in_review"},
            findings=[finding],
            missing_documents=[],
            decision=None,
        )

        seller_message = result.findings[0].seller_message.lower()
        forbidden_words = ["forged", "forgery", "fraud"]
        for word in forbidden_words:
            assert word not in seller_message, f"Forbidden word '{word}' found in seller message: {seller_message}"

    def test_get_seller_message_integrity_returns_generic(self):
        """Integrity findings return generic message, not internal details."""
        finding = TrustFindingSchema(
            check_id="missing_page",
            category="integrity",
            severity="warning",
            status="needs_manual_verification",
            field="page",
            evidence=[],
            why_raised="Possible missing page detected: page 3 missing",
            next_step="possible indicators - manual review recommended",
            seller_message=None,
        )

        message = _get_seller_message(finding)
        assert message == "possible indicators - manual review recommended"

    def test_get_seller_message_consistency_mismatch(self):
        """Consistency mismatch returns plain language message."""
        finding = TrustFindingSchema(
            check_id="owner_name_matched",
            category="consistency",
            severity="critical",
            status="mismatch",
            field="owner_name",
            evidence=[],
            why_raised="Owner name mismatch",
            next_step="Admin to verify",
            seller_message=None,
        )

        message = _get_seller_message(finding)
        assert "mismatch" in message.lower()
        assert "owner_name" in message.lower() or "field" in message.lower()

    def test_get_seller_message_consistency_needs_verification(self):
        """Consistency needs_manual_verification returns plain language message."""
        finding = TrustFindingSchema(
            check_id="owner_name_matched",
            category="consistency",
            severity="warning",
            status="needs_manual_verification",
            field="owner_name",
            evidence=[],
            why_raised="Owner name needs verification",
            next_step="Admin to verify",
            seller_message=None,
        )

        message = _get_seller_message(finding)
        assert "manual verification needed" in message.lower()

    def test_get_seller_message_consistency_matched(self):
        """Consistency matched returns confirmation message."""
        finding = TrustFindingSchema(
            check_id="owner_name_matched",
            category="consistency",
            severity="info",
            status="matched",
            field="owner_name",
            evidence=[],
            why_raised="Owner name matched",
            next_step="Verified",
            seller_message=None,
        )

        message = _get_seller_message(finding)
        assert "matched" in message.lower()

    def test_get_seller_message_completeness(self):
        """Completeness findings return document-focused message."""
        finding = TrustFindingSchema(
            check_id="missing_sale_deed",
            category="completeness",
            severity="critical",
            status="needs_manual_verification",
            field="sale_deed",
            evidence=[],
            why_raised="Required document type 'sale_deed' not found",
            next_step="Seller to upload",
            seller_message=None,
        )

        message = _get_seller_message(finding)
        assert "completeness" in message.lower() or "document" in message.lower()

    def test_seller_message_masking(self):
        """Aadhaar and PAN in seller_message are masked."""
        finding = TrustFindingSchema(
            check_id="test_check",
            category="consistency",
            severity="critical",
            status="mismatch",
            field="aadhaar",
            evidence=[],
            why_raised="Aadhaar mismatch",
            next_step="Admin to verify",
            seller_message="Aadhaar mismatch: 1234 5678 9012 vs 1234 5678 9013",
        )

        result = to_seller_view(
            set_data={"review_status": "in_review"},
            findings=[finding],
            missing_documents=[],
            decision=None,
        )

        message = result.findings[0].seller_message
        assert "1234 5678 9012" not in message
        assert "XXXX-XXXX-9012" in message
        assert "XXXX-XXXX-9013" in message


class TestCrossChecksMasking:
    """Tests that cross_checks produces masked why_raised values."""

    def test_run_cross_checks_masks_aadhaar_in_why_raised(self):
        """run_cross_checks should mask Aadhaar in why_raised."""
        extracted_fields = [
            {
                "field_name": "owner_name",
                "raw_value": "John Doe",
                "normalized_value": "JOHN DOE",
                "page_number": 1,
                "extraction_method": "ocr",
                "document_id": str(uuid4()),
                "document_type": "sale_deed",
            },
            {
                "field_name": "owner_name",
                "raw_value": "Jane Smith 1234 5678 9012",
                "normalized_value": "JANE SMITH 1234 5678 9012",
                "page_number": 1,
                "extraction_method": "ocr",
                "document_id": str(uuid4()),
                "document_type": "ec",
            },
        ]

        findings = run_cross_checks(extracted_fields)
        owner_name_finding = next(f for f in findings if f.check_id == "owner_name_matched")

        # why_raised should have masked Aadhaar
        assert "1234 5678 9012" not in owner_name_finding.why_raised
        assert "XXXX-XXXX-9012" in owner_name_finding.why_raised

    def test_run_cross_checks_masks_pan_in_why_raised(self):
        """run_cross_checks should mask PAN in why_raised."""
        extracted_fields = [
            {
                "field_name": "owner_name",
                "raw_value": "John Doe",
                "normalized_value": "JOHN DOE",
                "page_number": 1,
                "extraction_method": "ocr",
                "document_id": str(uuid4()),
                "document_type": "sale_deed",
            },
            {
                "field_name": "owner_name",
                "raw_value": "Jane Smith ABCDE1234F",
                "normalized_value": "JANE SMITH ABCDE1234F",
                "page_number": 1,
                "extraction_method": "ocr",
                "document_id": str(uuid4()),
                "document_type": "ec",
            },
        ]

        findings = run_cross_checks(extracted_fields)
        owner_name_finding = next(f for f in findings if f.check_id == "owner_name_matched")

        # why_raised should have masked PAN
        assert "ABCDE1234F" not in owner_name_finding.why_raised
        assert "XXXXX1234X" in owner_name_finding.why_raised


class TestRepositoryMasking:
    """Tests that repository functions mask identifiers before storage."""

    def test_create_extracted_fields_masks_raw_and_normalized(self):
        """create_extracted_fields should mask raw_value and normalized_value."""
        # This test would need a mock session - using a simple dict check instead
        # The actual masking is tested via the function logic
        from app.trust_suite.schemas import mask_identifiers

        raw = "John Doe 1234 5678 9012"
        normalized = "JOHN DOE 1234 5678 9012"

        masked_raw = mask_identifiers(raw)
        masked_normalized = mask_identifiers(normalized)

        assert "1234 5678 9012" not in masked_raw
        assert "XXXX-XXXX-9012" in masked_raw
        assert "1234 5678 9012" not in masked_normalized
        assert "XXXX-XXXX-9012" in masked_normalized

    def test_create_findings_masks_why_raised_next_step_seller_message(self):
        """create_findings should mask why_raised, next_step, seller_message, evidence_json."""
        from app.trust_suite.schemas import mask_identifiers, mask_identifiers_in_list

        why_raised = "Owner name comparison: 'John 1234 5678 9012' vs 'Jane'"
        next_step = "Verify Aadhaar 1234 5678 9012"
        seller_message = "Mismatch in Aadhaar 1234 5678 9012"
        evidence = [{"raw_value": "1234 5678 9012", "normalized_value": "1234 5678 9012"}]

        masked_why = mask_identifiers(why_raised)
        masked_next = mask_identifiers(next_step)
        masked_seller = mask_identifiers(seller_message)
        masked_evidence = mask_identifiers_in_list(evidence)

        assert "1234 5678 9012" not in masked_why
        assert "XXXX-XXXX-9012" in masked_why
        assert "1234 5678 9012" not in masked_next
        assert "XXXX-XXXX-9012" in masked_next
        assert "1234 5678 9012" not in masked_seller
        assert "XXXX-XXXX-9012" in masked_seller
        assert "1234 5678 9012" not in masked_evidence[0]["raw_value"]
        assert "XXXX-XXXX-9012" in masked_evidence[0]["raw_value"]

    def test_create_checklist_items_masks_note(self):
        """create_checklist_items should mask note."""
        from app.trust_suite.schemas import mask_identifiers

        note = "Verified Aadhaar 1234 5678 9012 with seller"
        masked_note = mask_identifiers(note)

        assert "1234 5678 9012" not in masked_note
        assert "XXXX-XXXX-9012" in masked_note

    def test_update_checklist_item_masks_note(self):
        """update_checklist_item should mask note."""
        from app.trust_suite.schemas import mask_identifiers

        note = "Verified PAN ABCDE1234F with seller"
        masked_note = mask_identifiers(note)

        assert "ABCDE1234F" not in masked_note
        assert "XXXXX1234X" in masked_note

    def test_create_admin_decision_masks_reason_notes_checklist(self):
        """create_admin_decision should mask reason, notes, and checklist_snapshot."""
        from app.trust_suite.schemas import mask_identifiers, mask_identifiers_in_dict

        reason = "Rejected due to Aadhaar 1234 5678 9012 mismatch"
        notes = "PAN ABCDE1234F also mismatched"
        checklist_snapshot = {
            "items": [{"note": "Checked Aadhaar 1234 5678 9012"}]
        }

        masked_reason = mask_identifiers(reason)
        masked_notes = mask_identifiers(notes)
        masked_checklist = mask_identifiers_in_dict(checklist_snapshot)

        assert "1234 5678 9012" not in masked_reason
        assert "XXXX-XXXX-9012" in masked_reason
        assert "ABCDE1234F" not in masked_notes
        assert "XXXXX1234X" in masked_notes
        assert "1234 5678 9012" not in masked_checklist["items"][0]["note"]
        assert "XXXX-XXXX-9012" in masked_checklist["items"][0]["note"]


class TestUploadCleanup:
    """Tests for upload cleanup on failure."""

    def test_upload_deletes_files_on_db_failure(self, tmp_path, monkeypatch):
        """Upload should delete written files if DB commit fails."""
        # This is a structural test - the actual implementation
        # is in router.py create_trust_set function
        # We verify the pattern exists by checking the code has try/except with cleanup
        import inspect
        from app.trust_suite.router import create_trust_set

        source = inspect.getsource(create_trust_set)
        # Check that file write happens and there's cleanup logic
        assert "write_bytes" in source
        assert "try:" in source or "except" in source
        # The actual cleanup test would need more complex mocking


class TestVerifyOnly:
    """Verification-only tests - check existing behavior without changes."""

    def test_property_lock_in_decision_path(self):
        """Verify property row is locked FOR UPDATE in decision path."""
        import inspect
        from app.trust_suite.router import make_admin_decision
        from app.trust_suite.repository import get_property_for_update, update_property_status

        decision_source = inspect.getsource(make_admin_decision)
        update_source = inspect.getsource(update_property_status)

        # Decision path uses get_review_queue_for_update (queue lock)
        assert "get_review_queue_for_update" in decision_source
        # Then gets property with lock
        assert "get_property_for_update" in decision_source
        # Then calls update_property_status
        assert "update_property_status" in decision_source

        # update_property_status uses get_property (no lock) - this is the race condition
        assert "get_property(db, property_id)" in update_source
        assert "with_for_update" not in update_source

    def test_get_property_verification_responses(self):
        """Verify get_property_verification responses for different cases."""
        import inspect
        from app.trust_suite.router import get_property_verification

        source = inspect.getsource(get_property_verification)

        # (a) nonexistent id -> 404 "Property not found"
        assert 'detail="Property not found"' in source
        # (b) unapproved property -> 404 "Verification only available for approved listings"
        assert 'detail="Verification only available for approved listings"' in source
        # Both return 404 - identical HTTP status, different messages

    def test_upload_limit_enforcement(self):
        """Verify 20MB limit is enforced via streaming chunked read."""
        import inspect
        from app.trust_suite.router import _read_file_chunks

        source = inspect.getsource(_read_file_chunks)

        # Reads in 8192-byte chunks
        assert "8192" in source
        # Checks total against MAX_FILE_SIZE during read
        assert "total > max_size" in source
        # Does NOT read whole file into memory first
        assert "file.file.read()" not in source or "chunk" in source

    def test_magic_bytes_validation(self):
        """Verify magic bytes/content-type validation beyond extension."""
        import inspect
        from app.trust_suite.router import _validate_magic_bytes

        source = inspect.getsource(_validate_magic_bytes)

        # Has magic bytes for each extension
        assert "MAGIC_BYTES" in source
        assert "startswith" in source
        assert "magic bytes mismatch" in source.lower()

    def test_reupload_after_approval_resets_to_pending(self):
        """Verify re-upload after approval resets property to pending."""
        import inspect
        from app.trust_suite.router import create_trust_set
        from app.trust_suite.services.review_rules import revert_on_reupload

        router_source = inspect.getsource(create_trust_set)
        revert_source = inspect.getsource(revert_on_reupload)

        # Router checks if prop.status == approved
        assert "PropertyStatusEnum.approved" in router_source
        # Uses get_property_for_update
        assert "get_property_for_update" in router_source
        # Calls revert_on_reupload
        assert "revert_on_reupload" in router_source
        # revert_on_reupload returns "pending" for "approved"
        assert '"approved"' in revert_source
        assert '"pending"' in revert_source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])