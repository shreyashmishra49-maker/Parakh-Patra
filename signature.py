"""
signature.py - Ed25519 Cryptographic Signatures & Secure Key Management
=======================================================================
What is Ed25519?
Ed25519 is a state-of-the-art public-key signature system based on
Curve25519. It offers high cryptographic security (128-bit level) with
tiny 32-byte public keys and 64-byte signatures.

Role in Parakh Patra:
1. Authenticity: Proves WHICH tester/lab generated the report.
2. Integrity: Proves that NOT A SINGLE CHARACTER of the report was altered.
3. Tamper Detection: Changing an answer, a timestamp, or accuracy score
   immediately causes verification to FAIL.

CRITICAL ETHICAL & SCIENTIFIC PRINCIPLE:
A digital signature NEVER proves that the AI model's answers are factually
true, accurate, fair, or unbiased. It only proves that the report was signed
by the key holder and has not been modified.
"""

import os
import stat
import sys
from typing import Tuple, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.exceptions import InvalidSignature
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


ETHICAL_DISCLAIMER = (
    "DISCLAIMER: An Ed25519 digital signature certifies report integrity "
    "(tamper-evidence) and signer identity. A VALID SIGNATURE DOES NOT PROVE "
    "THAT THE AI MODEL'S ANSWERS ARE ACCURATE, TRUTHFUL, OR SAFE."
)


def is_cryptography_available() -> bool:
    """Returns True if the cryptography library is installed."""
    return CRYPTOGRAPHY_AVAILABLE


def generate_key_pair() -> Tuple[str, str]:
    """
    Generates a new cryptographically secure Ed25519 key pair.
    Returns:
        (private_key_hex, public_key_hex)
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError(
            "The 'cryptography' library is required for Ed25519 signatures. "
            "Install using: pip install cryptography"
        )

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_hex = private_key.private_bytes_raw().hex()
    public_hex = public_key.public_bytes_raw().hex()

    return private_hex, public_hex


def save_key_pair(
    private_key_hex: str,
    public_key_hex: str,
    keys_dir: str = "keys",
    private_key_file: str = "private_key.hex",
    public_key_file: str = "public_key.hex",
) -> Tuple[str, str]:
    """
    Saves key pairs securely to disk:
    - Creates the 'keys/' directory.
    - Sets strict read/write permissions on the private key file (0o600 on Unix).
    - Leaves public key shareable.
    """
    os.makedirs(keys_dir, exist_ok=True)
    priv_path = os.path.join(keys_dir, private_key_file)
    pub_path = os.path.join(keys_dir, public_key_file)

    # 1. Save private key with restricted permissions
    with open(priv_path, "w", encoding="utf-8") as f:
        f.write(private_key_hex.strip())

    # Restrict permissions on Unix/Linux/macOS so only the file owner can read
    try:
        if os.name != "nt":
            os.chmod(priv_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass

    # 2. Save public key
    with open(pub_path, "w", encoding="utf-8") as f:
        f.write(public_key_hex.strip())

    print(f"🔒 Private key saved to: {priv_path} (KEEP SECRET - DO NOT COMMIT)")
    print(f"📢 Public key saved to:  {pub_path} (Shareable)")

    return priv_path, pub_path


def load_private_key(
    file_path: Optional[str] = "keys/private_key.hex",
    env_var_name: str = "PARAKH_PATRA_PRIVATE_KEY",
) -> str:
    """
    Securely loads the private key:
    1. Checks environment variable first (preferred in automated CI/CD pipelines).
    2. Falls back to reading from local file path.
    """
    # 1. Check environment variable
    env_key = os.environ.get(env_var_name)
    if env_key and len(env_key.strip()) == 64:
        return env_key.strip()

    # 2. Check local file
    if file_path and os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            key_hex = f.read().strip()
            if len(key_hex) == 64:
                return key_hex
            else:
                raise ValueError(f"Invalid private key format in '{file_path}'. Expected 64-character hex.")

    raise FileNotFoundError(
        f"Private key not found! Set environment variable '{env_var_name}' "
        f"or ensure '{file_path}' exists. Run 'python signature.py --generate' to create one."
    )


def sign_data(private_key_hex: str, data: str) -> str:
    """
    Signs a message string using the Ed25519 private key.
    Returns:
        64-byte signature encoded as a 128-character hexadecimal string.
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("The 'cryptography' library is required to sign data.")

    try:
        private_bytes = bytes.fromhex(private_key_hex.strip())
        if len(private_bytes) != 32:
            raise ValueError(f"Ed25519 private key must be 32 bytes (64 hex characters), got {len(private_bytes)} bytes.")

        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        signature = priv_key.sign(data.encode("utf-8"))
        return signature.hex()
    except Exception as e:
        raise RuntimeError(f"Failed to sign data: {e}")


def verify_signature(public_key_hex: str, data: str, signature_hex: str) -> bool:
    """
    Verifies that the signature was created by the owner of public_key_hex
    over the exact string 'data'.
    Returns:
        True if signature is valid and data is completely unaltered.
        False if tampered, corrupted, or key does not match.
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("The 'cryptography' library is required to verify signatures.")

    try:
        public_bytes = bytes.fromhex(public_key_hex.strip())
        sig_bytes = bytes.fromhex(signature_hex.strip())
        data_bytes = data.encode("utf-8")

        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        pub_key.verify(sig_bytes, data_bytes)
        return True
    except (InvalidSignature, ValueError):
        return False


def get_public_key_from_private(private_key_hex: str) -> str:
    """Derives the 32-byte public key (in hex) from the private key."""
    if not CRYPTOGRAPHY_AVAILABLE:
        raise RuntimeError("The 'cryptography' library is required.")
    private_bytes = bytes.fromhex(private_key_hex.strip())
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
    return priv_key.public_key().public_bytes_raw().hex()


def export_public_key_pem(public_key_hex: str) -> str:
    """
    Exports a 32-byte Ed25519 public key hex into standard RFC 8410 PEM format:
    -----BEGIN PUBLIC KEY-----
    ...
    -----END PUBLIC KEY-----
    """
    if CRYPTOGRAPHY_AVAILABLE:
        from cryptography.hazmat.primitives import serialization
        pub_bytes = bytes.fromhex(public_key_hex.strip())
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        pem_bytes = pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem_bytes.decode("utf-8")
    else:
        # RFC 8410 SubjectPublicKeyInfo prefix for Ed25519 in DER: 12 bytes prefix + 32 bytes raw key
        import base64
        prefix = bytes.fromhex("302a300506032b6570032100")
        raw_key = bytes.fromhex(public_key_hex.strip())
        der = prefix + raw_key
        b64 = base64.b64encode(der).decode("ascii")
        return f"-----BEGIN PUBLIC KEY-----\n{b64}\n-----END PUBLIC KEY-----\n"


def parse_public_key_pem(pem_str: str) -> str:
    """
    Extracts the 64-character raw hex from an Ed25519 public key PEM string.
    """
    if CRYPTOGRAPHY_AVAILABLE:
        from cryptography.hazmat.primitives import serialization
        pub_key = serialization.load_pem_public_key(pem_str.encode("utf-8"))
        if not isinstance(pub_key, ed25519.Ed25519PublicKey):
            raise ValueError("Expected an Ed25519 public key.")
        return pub_key.public_bytes_raw().hex()
    else:
        import base64
        lines = [line.strip() for line in pem_str.strip().splitlines() if not line.startswith("-----")]
        der = base64.b64decode("".join(lines))
        # Last 32 bytes is the Ed25519 raw public key
        raw_key = der[-32:]
        return raw_key.hex()


def save_reports_bundle(
    report_data: dict,
    private_key_hex: str,
    output_dir: str = "reports",
) -> Tuple[str, str, str]:
    """
    Produces the standard Parakh Patra reports bundle:
    1. reports/parakh_report.json  (Canonical JSON evidence report)
    2. reports/report_signature.bin (Raw 64-byte Ed25519 binary signature)
    3. reports/public_key.pem       (RFC 8410 PEM Public Key for auditors)
    """
    import json
    os.makedirs(output_dir, exist_ok=True)

    # 1. Sign data if not already signed
    content_hash = report_data.get("report_content_sha256")
    if not content_hash:
        from fingerprint import calculate_text_sha256
        body_to_hash = {k: v for k, v in report_data.items() if k not in ("digital_signature", "report_content_sha256")}
        content_hash = calculate_text_sha256(json.dumps(body_to_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        report_data["report_content_sha256"] = content_hash

    sig_hex = sign_data(private_key_hex, content_hash)
    pub_hex = get_public_key_from_private(private_key_hex)

    report_data["digital_signature"] = {
        "algorithm": "Ed25519",
        "public_key_hex": pub_hex,
        "signature_hex": sig_hex,
        "signed_content_hash": content_hash,
    }

    # 1. Save parakh_report.json
    json_path = os.path.join(output_dir, "parakh_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    # 2. Save report_signature.bin (raw 64 bytes)
    bin_path = os.path.join(output_dir, "report_signature.bin")
    with open(bin_path, "wb") as f:
        f.write(bytes.fromhex(sig_hex))

    # 3. Save public_key.pem
    pem_path = os.path.join(output_dir, "public_key.pem")
    pem_str = export_public_key_pem(pub_hex)
    with open(pem_path, "w", encoding="utf-8") as f:
        f.write(pem_str)

    print(f"📁 Report Bundle Saved to '{output_dir}/':")
    print(f"   1. {json_path}")
    print(f"   2. {bin_path} (64-byte signature)")
    print(f"   3. {pem_path} (PEM public key)")

    return json_path, bin_path, pem_path


if __name__ == "__main__":
    print("=" * 60)
    print("🛡️  Parakh Patra - Ed25519 Signature Demo & Key Generator")
    print("=" * 60)

    if not CRYPTOGRAPHY_AVAILABLE:
        print("❌ 'cryptography' library is not installed.")
        print("Install it with: pip install cryptography")
        sys.exit(1)

    # Self-test demonstration
    priv, pub = generate_key_pair()
    save_key_pair(priv, pub)

    sample_doc = "Parakh Patra Benchmark Report - SmolLM2-135M Accuracy: 100%"
    signature_hex = sign_data(priv, sample_doc)

    print(f"\nOriginal Document:  '{sample_doc}'")
    print(f"Ed25519 Signature:  {signature_hex[:32]}... (length {len(signature_hex)})")

    # 1. Valid test
    is_valid = verify_signature(pub, sample_doc, signature_hex)
    print(f"Verification Check: {'✅ VALID' if is_valid else '❌ INVALID'}")

    # 2. Tampering test
    tampered_doc = "Parakh Patra Benchmark Report - SmolLM2-135M Accuracy: 99%"
    tamper_check = verify_signature(pub, tampered_doc, signature_hex)
    print(f"Tampered Doc Check: {'✅ VALID' if tamper_check else '❌ TAMPER DETECTED (Expected)'}")
    print("=" * 60)
