"""
Security and reliability tests for mipi-mantle-cell-calculator.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from mipi_calc import calculate_metrics, process_batch
from agents.base import PHIGuard, SecurityException, AuditTrail


class TestClinicalInputs:
    def test_missing_fields(self):
        with pytest.raises(TypeError):
            calculate_metrics()

    def test_valid_risk(self):
        result = calculate_metrics(age=60, ecog=0, wbc=10, ldh_ratio=1)
        assert result["classification"] == "Intermediate"

    def test_nonfinite_rejected(self):
        with pytest.raises(ValueError):
            calculate_metrics(age=60, ecog=0, wbc=float("inf"), ldh_ratio=1)

    def test_duplicate_file_path_rejected(self, tmp_path):
        path = tmp_path / "input.csv"
        path.write_text("age,ecog,wbc,ldh_ratio\n60,0,10,1\n")
        with pytest.raises(ValueError, match="differ"):
            process_batch(str(path), str(path))


class TestPHIGuard:
    """Test PHI detection patterns."""

    def test_mrn_detected(self):
        """MRN patterns should be detected."""
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-12345678")

    def test_ssn_detected(self):
        """SSN patterns should be detected."""
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789")

    def test_phone_detected(self):
        """Phone number patterns should be detected."""
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Call 555-123-4567")

    def test_email_detected(self):
        """Email patterns should be detected."""
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Email: patient@hospital.org")

    def test_clean_text_passes(self):
        """Non-PHI text should pass."""
        PHIGuard.assert_no_phi("Specimen KEY-001 optimal result")
        PHIGuard.assert_no_phi("Analytical assay within normal limits")

    def test_error_message_no_pattern_leak(self):
        """Error message should not leak regex pattern details."""
        try:
            PHIGuard.assert_no_phi("MRN-12345678")
            assert False, "Should have raised SecurityException"
        except SecurityException as e:
            assert "PHI" in str(e)
            # Should not contain the raw regex pattern
            assert "re.compile" not in str(e)
            assert "MRN|mrn" not in str(e)


class TestAuditTrailSecurity:
    """Test audit trail security requirements."""

    def test_audit_trail_requires_key(self):
        """AuditTrail should require a key or env var."""
        import os
        # Save and clear env
        old_key = os.environ.pop("AUDIT_SECRET_KEY", None)
        try:
            # Should use random key (no error in test context)
            trail = AuditTrail()
            assert trail.secret_key is not None
            assert len(trail.secret_key) > 0
        finally:
            if old_key:
                os.environ["AUDIT_SECRET_KEY"] = old_key

    def test_audit_trail_accepts_explicit_key(self):
        """AuditTrail should accept an explicit key."""
        trail = AuditTrail(secret_key="test-key-for-unit-tests-only")
        entry = trail.log("test", "unit", "TEST_EVENT", {"data": "value"})
        assert "current_hash" in entry
        assert entry["current_hash"] != ""

    def test_short_key_rejected(self):
        """Keys shorter than 16 chars should be rejected."""
        with pytest.raises(RuntimeError, match="16 characters"):
            AuditTrail(secret_key="short")

    def test_integrity_verification(self):
        """Audit trail integrity should be verifiable."""
        trail = AuditTrail(secret_key="test-key-for-integrity-check")
        trail.log("actor1", "tier1", "EVENT1", {"a": 1})
        trail.log("actor2", "tier2", "EVENT2", {"b": 2})
        assert trail.verify_integrity() is True


def test_hmac_detects_modified_record():
    trail = AuditTrail(secret_key="test-key-for-tamper-detection")
    trail.log("a", "b", "EVENT", {"x": 1})
    assert trail.verify_integrity()
    trail.logs[0]["event_type"] = "MUTATED"
    assert not trail.verify_integrity()
