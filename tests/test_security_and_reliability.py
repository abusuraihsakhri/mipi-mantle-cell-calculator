"""
Security and reliability tests for mipi-mantle-cell-calculator.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from mipi_calc import calculate_metrics, _validate_file_path
from agents.base import PHIGuard, SecurityException, AuditTrail


class TestCalculateMetricsEdgeCases:
    """Test calculate_metrics with edge cases and boundary conditions."""

    def test_empty_input(self):
        """Should handle no inputs gracefully."""
        res = calculate_metrics()
        assert res["score"] == 0.0
        assert res["classification"] == "Unknown"
        assert "warning" in res

    def test_none_values_filtered(self):
        """None values should be filtered out."""
        res = calculate_metrics(v1=None, v2=None)
        assert res["score"] == 0.0
        assert res["classification"] == "Unknown"

    def test_empty_string_values_filtered(self):
        """Empty string values should be filtered out."""
        res = calculate_metrics(v1="", v2="")
        assert res["score"] == 0.0

    def test_single_value(self):
        """Single numeric value should return that value as score."""
        res = calculate_metrics(v1=15.0)
        assert res["score"] == 15.0
        assert res["classification"] == "Moderate / Intermediate"

    def test_multiple_values_weighted(self):
        """Multiple values should be weighted correctly."""
        # score = 10 + 5*(1/2) + 2*(1/3) = 10 + 2.5 + 0.67 = 13.17
        res = calculate_metrics(v1=10.0, v2=5.0, v3=2.0)
        assert res["score"] == pytest.approx(13.17, abs=0.01)

    def test_string_values_ignored_in_scoring(self):
        """Non-numeric string values should not contribute to score."""
        res = calculate_metrics(v1=10.0, name="test_patient")
        assert res["score"] == 10.0
        assert res["inputs_evaluated"] == 2

    def test_classification_low(self):
        """Score < 10 should be Low/Standard."""
        res = calculate_metrics(v1=5.0)
        assert res["classification"] == "Low / Standard"

    def test_classification_moderate(self):
        """Score 10-24.99 should be Moderate."""
        res = calculate_metrics(v1=15.0)
        assert res["classification"] == "Moderate / Intermediate"

    def test_classification_high(self):
        """Score >= 25 should be High/Severe."""
        res = calculate_metrics(v1=30.0)
        assert res["classification"] == "High / Severe"

    def test_extreme_values_handled(self):
        """Very large values should not cause overflow issues."""
        res = calculate_metrics(v1=1e308, v2=1e308)
        assert isinstance(res["score"], float)


class TestPathValidation:
    """Test file path validation for security."""

    def test_normal_path_accepted(self):
        """Normal file paths should be accepted."""
        assert _validate_file_path("data.csv") == "data.csv"
        assert _validate_file_path("output/results.csv") == "output\\results.csv"  # Windows

    def test_path_traversal_rejected(self):
        """Paths with .. should be rejected."""
        with pytest.raises(ValueError, match="traversal"):
            _validate_file_path("../etc/passwd")

    def test_nested_traversal_rejected(self):
        """Nested traversal paths should be rejected."""
        with pytest.raises(ValueError, match="traversal"):
            _validate_file_path("foo/../../../etc/passwd")

    def test_null_byte_rejected(self):
        """Paths with null bytes should be rejected."""
        with pytest.raises(ValueError, match="null bytes"):
            _validate_file_path("foo\x00bar.csv")


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
