"""
test_verification.py - Cryptographic Verification & File Integrity Tests
========================================================================
Comprehensive test suite verifying:
1. SHA-256 fingerprinting accuracy and avalanche effect.
2. Ed25519 key generation and signature validity.
3. Tamper detection on modified report data.
4. Tamper detection on modified dataset files.
5. Detection of corrupted signature bytes.

Run with:
    python test_verification.py
    (or: pytest test_verification.py)
"""

import copy
import json
import os
import sys
import tempfile
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import fingerprint
import signature
import report_generator


class TestFingerprintAndSignatures(unittest.TestCase):
    """Unit tests for cryptographic fingerprinting and Ed25519 signing."""

    def test_01_sha256_text_hashing(self):
        """Tests that text hashing is deterministic and matches expected SHA-256."""
        text = "Parakh Patra"
        # Standard SHA-256 of "Parakh Patra"
        hash_val = fingerprint.calculate_text_sha256(text)
        self.assertEqual(len(hash_val), 64, "SHA-256 hex string must be 64 characters.")

        # Re-hashing the same string must yield identical hash
        self.assertEqual(hash_val, fingerprint.calculate_text_sha256(text))

    def test_02_sha256_avalanche_effect(self):
        """Tests that changing 1 character changes the hash completely."""
        text_a = "Parakh Patra Accuracy: 100%"
        text_b = "Parakh Patra Accuracy: 100%."  # Only added one trailing dot

        hash_a = fingerprint.calculate_text_sha256(text_a)
        hash_b = fingerprint.calculate_text_sha256(text_b)

        self.assertNotEqual(hash_a, hash_b)
        # Check that more than 30 characters differ (avalanche effect)
        diff_count = sum(1 for a, b in zip(hash_a, hash_b) if a != b)
        self.assertGreater(diff_count, 20)

    def test_03_file_hashing_matches_stream(self):
        """Tests file hashing on temporary files."""
        content = b"Sample dataset line 1\nSample dataset line 2\n"
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            file_hash = fingerprint.calculate_file_sha256(tmp_path)
            self.assertEqual(len(file_hash), 64)
            # Verify against in-memory hash of identical bytes
            import hashlib
            expected_hash = hashlib.sha256(content).hexdigest()
            self.assertEqual(file_hash, expected_hash)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_04_ed25519_key_generation(self):
        """Tests Ed25519 key generation."""
        if not signature.is_cryptography_available():
            self.skipTest("cryptography library not installed.")

        priv, pub = signature.generate_key_pair()
        self.assertEqual(len(priv), 64, "Private key hex must be 64 characters (32 bytes).")
        self.assertEqual(len(pub), 64, "Public key hex must be 64 characters (32 bytes).")

        # Public key derived from private key must match generated public key
        derived_pub = signature.get_public_key_from_private(priv)
        self.assertEqual(derived_pub, pub)

    def test_05_valid_signature_verification(self):
        """Tests that a signed message verifies successfully."""
        if not signature.is_cryptography_available():
            self.skipTest("cryptography library not installed.")

        priv, pub = signature.generate_key_pair()
        data = "Evidence Report Data: Hash abc123xyz"

        sig = signature.sign_data(priv, data)
        self.assertEqual(len(sig), 128, "Ed25519 signature hex must be 128 chars (64 bytes).")

        # Must verify as valid
        is_valid = signature.verify_signature(pub, data, sig)
        self.assertTrue(is_valid, "Valid signature must verify as True.")

    def test_06_tamper_detection_on_message(self):
        """Tests that modifying data causes signature verification to fail."""
        if not signature.is_cryptography_available():
            self.skipTest("cryptography library not installed.")

        priv, pub = signature.generate_key_pair()
        original_data = "Model Accuracy: 100%"
        tampered_data = "Model Accuracy: 80%"

        sig = signature.sign_data(priv, original_data)

        # Verifying tampered data must return False
        is_valid = signature.verify_signature(pub, tampered_data, sig)
        self.assertFalse(is_valid, "Tampered data MUST fail signature verification.")

    def test_07_tamper_detection_on_signature_bytes(self):
        """Tests that altering signature bytes fails verification."""
        if not signature.is_cryptography_available():
            self.skipTest("cryptography library not installed.")

        priv, pub = signature.generate_key_pair()
        data = "Test Data String"
        sig = signature.sign_data(priv, data)

        # Corrupt the last character of the signature
        corrupted_char = '0' if sig[-1] != '0' else '1'
        corrupted_sig = sig[:-1] + corrupted_char

        is_valid = signature.verify_signature(pub, data, corrupted_sig)
        self.assertFalse(is_valid, "Corrupted signature MUST fail verification.")

    def test_08_report_tamper_detection(self):
        """Tests report creation, signing, and detection of modified fields."""
        if not signature.is_cryptography_available():
            self.skipTest("cryptography library not installed.")

        priv, pub = signature.generate_key_pair()

        # Build a sample report
        report = {
            "title": "Parakh Patra AI Verification Report",
            "model": {"name": "SmolLM2-135M"},
            "summary": {"accuracy_pct": 100.0, "total_questions": 5},
            "results": [{"q": "2+2", "ans": "4"}],
        }
        # Compute canonical content hash
        body_canonical = report_generator.canonical_json(report)
        report["report_content_sha256"] = fingerprint.calculate_text_sha256(body_canonical)

        # Sign report
        signed_report = report_generator.sign_report(report, priv)

        # 1. Unaltered report must be valid
        res = report_generator.verify_report(signed_report)
        self.assertTrue(res["is_valid"], f"Authentic report must verify: {res['message']}")
        self.assertEqual(res["status"], "VALID")

        # 2. Tampered report: secretly alter the accuracy score from 100.0 to 95.0
        tampered_report = copy.deepcopy(signed_report)
        tampered_report["summary"]["accuracy_pct"] = 95.0

        tamper_res = report_generator.verify_report(tampered_report)
        self.assertFalse(tamper_res["is_valid"], "Tampered report MUST fail verification!")
        self.assertEqual(tamper_res["status"], "TAMPERED")

    def test_09_dataset_integrity_check(self):
        """Tests dataset file integrity check."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as tmp:
            tmp.write('{"prompt": "What is 2+2?", "expected": "4"}\n')
            tmp_path = tmp.name

        try:
            initial_hash = fingerprint.calculate_file_sha256(tmp_path)
            mock_report = {
                "dataset": {
                    "path": os.path.basename(tmp_path),
                    "sha256": initial_hash
                }
            }

            # 1. Check intact dataset
            check_intact = report_generator.verify_dataset_integrity(mock_report, tmp_path)
            self.assertTrue(check_intact["is_intact"])
            self.assertEqual(check_intact["status"], "INTACT")

            # 2. Modify dataset on disk
            with open(tmp_path, "a") as f:
                f.write('{"prompt": "What is 3+3?", "expected": "6"}\n')

            check_modified = report_generator.verify_dataset_integrity(mock_report, tmp_path)
            self.assertFalse(check_modified["is_intact"])
            self.assertEqual(check_modified["status"], "MODIFIED")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


def run_tests():
    """Runs tests and outputs formatted results."""
    print("\n" + "=" * 65)
    print("🧪 PARAKH PATRA - CRYPTOGRAPHIC INTEGRITY TEST SUITE")
    print("=" * 65)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestFingerprintAndSignatures)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 65)
    if result.wasSuccessful():
        print("✅ ALL CRYPTOGRAPHIC & INTEGRITY TESTS PASSED SUCCESSFULLY!")
    else:
        print("❌ SOME TESTS FAILED. PLEASE REVIEW THE LOGS ABOVE.")
    print("=" * 65 + "\n")
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)