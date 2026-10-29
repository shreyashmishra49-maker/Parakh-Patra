"""
report_generator.py - Verifiable Evidence Reports & Integrity Auditor
====================================================================
This module:
1. Compiles benchmark test results, hardware/software environment,
   model revision, and SHA-256 fingerprints into an auditable JSON report.
2. Canonicalizes JSON for deterministic, cross-platform hashing.
3. Cryptographically signs the report with Ed25519.
4. Verifies signatures and detects any tampering with reports or test files.

CRITICAL ETHICAL & SCIENTIFIC PRINCIPLE:
A digital signature certifies that this report was produced by the signer
and has not been altered since generation. It DOES NOT prove or guarantee
that the AI model's answers are factually true, unbiased, or safe.
"""

import argparse
import datetime
import json
import os
import platform
import sys
from typing import Dict, Any, Tuple, Optional, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import fingerprint
import signature


REPORT_DISCLAIMER = (
    "ETHICAL NOTICE: This digital signature certifies document integrity and "
    "signer identity. A valid signature DOES NOT prove that the AI model's answers "
    "are factually true, unbiased, or safe."
)

HARDWARE_REPRODUCIBILITY_NOTICE = (
    "HARDWARE REPRODUCIBILITY NOTICE: Floating-point arithmetic variations across "
    "different CPU/GPU architectures, linear algebra libraries (BLAS/MKL), and driver "
    "versions can produce subtle differences in model generation even with identical "
    "random seeds and deterministic settings (temperature = 0.0)."
)


def get_detailed_system_environment() -> Dict[str, Any]:
    """
    Captures complete hardware, operating system, and software versions
    so benchmarks can be verified and reproduced on other systems.
    """
    env = {
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }

    # PyTorch and CUDA versions
    try:
        import torch
        env["torch_version"] = torch.__version__
        env["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            env["cuda_device_name"] = torch.cuda.get_device_name(0)
            env["cuda_capability"] = torch.cuda.get_device_capability(0)
    except ImportError:
        env["torch_version"] = "Not Installed"
        env["cuda_available"] = False

    # Transformers version
    try:
        import transformers
        env["transformers_version"] = transformers.__version__
    except ImportError:
        env["transformers_version"] = "Not Installed"

    return env


def canonical_json(data: Dict[str, Any]) -> str:
    """
    Produces deterministic, sorted, whitespace-trimmed JSON string.
    Ensures identical SHA-256 hashing across different operating systems.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def create_evidence_report(
    model_name: str,
    results_file: str = "results.jsonl",
    questions_file: str = "questions.jsonl",
    model_revision: str = "main",
    seed: int = 42,
    temperature: float = 0.0,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Assembles a complete, auditable verification report.
    """
    # 1. Dataset Fingerprint
    dataset_info = fingerprint.calculate_dataset_fingerprint(questions_file)

    # 2. Model Fingerprint
    model_info = fingerprint.calculate_model_fingerprint(model_name)
    model_info["revision"] = model_revision

    # 3. Load Results
    if not os.path.exists(results_file):
        raise FileNotFoundError(f"Results file '{results_file}' not found.")

    test_records = []
    correct_count = 0
    total_latency = 0.0

    with open(results_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            test_records.append(item)
            if item.get("is_correct", False):
                correct_count += 1
            total_latency += item.get("latency_seconds", 0.0)

    total_questions = len(test_records)
    accuracy_pct = (correct_count / total_questions * 100.0) if total_questions > 0 else 0.0
    avg_latency = (total_latency / total_questions) if total_questions > 0 else 0.0

    # 4. Hardware and Software Environment
    environment = get_detailed_system_environment()

    # 5. Assemble Structured Report Body
    report = {
        "title": "Parakh Patra AI Verification Report",
        "spec_version": "1.0",
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "notes": notes,
        "disclaimers": {
            "ethical_disclaimer": REPORT_DISCLAIMER,
            "hardware_reproducibility_limitation": HARDWARE_REPRODUCIBILITY_NOTICE,
        },
        "model": {
            "name": model_name,
            "revision": model_revision,
            "fingerprint": model_info,
        },
        "dataset": dataset_info,
        "generation_settings": {
            "seed": seed,
            "temperature": temperature,
        },
        "environment": environment,
        "summary": {
            "total_questions": total_questions,
            "correct_count": correct_count,
            "incorrect_count": total_questions - correct_count,
            "accuracy_pct": round(accuracy_pct, 2),
            "average_latency_seconds": round(avg_latency, 4),
            "total_latency_seconds": round(total_latency, 4),
        },
        "results": test_records,
    }

    # 6. Calculate Canonical Content Hash
    canonical_body = canonical_json(report)
    report["report_content_sha256"] = fingerprint.calculate_text_sha256(canonical_body)

    return report


def sign_report(report: Dict[str, Any], private_key_hex: str) -> Dict[str, Any]:
    """
    Signs the report's canonical content SHA-256 hash using Ed25519.
    Attaches the digital signature and public key to the report.
    """
    content_hash = report.get("report_content_sha256")
    if not content_hash:
        body_to_hash = {k: v for k, v in report.items() if k not in ("digital_signature", "report_content_sha256")}
        content_hash = fingerprint.calculate_text_sha256(canonical_json(body_to_hash))
        report["report_content_sha256"] = content_hash

    signature_hex = signature.sign_data(private_key_hex, content_hash)
    public_key_hex = signature.get_public_key_from_private(private_key_hex)

    report["digital_signature"] = {
        "algorithm": "Ed25519",
        "public_key_hex": public_key_hex,
        "signature_hex": signature_hex,
        "signed_content_hash": content_hash,
        "signed_at_utc": datetime.datetime.utcnow().isoformat() + "Z",
    }

    return report


def verify_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies that:
    1. The report contains a valid Ed25519 digital signature.
    2. The report content has not been modified (hash comparison).
    3. The signature matches the public key and content hash.
    """
    if "digital_signature" not in report_data:
        return {
            "status": "UNSIGNED",
            "is_valid": False,
            "message": "Report has no digital signature.",
        }

    sig_block = report_data["digital_signature"]
    pub_key_hex = sig_block.get("public_key_hex")
    sig_hex = sig_block.get("signature_hex")
    expected_hash = report_data.get("report_content_sha256")

    if not pub_key_hex or not sig_hex or not expected_hash:
        return {
            "status": "MALFORMED",
            "is_valid": False,
            "message": "Signature block is missing required fields.",
        }

    # Step 1: Recompute content hash (excluding signature and hash metadata fields)
    body_copy = {k: v for k, v in report_data.items() if k not in ("digital_signature", "report_content_sha256")}
    recomputed_hash = fingerprint.calculate_text_sha256(canonical_json(body_copy))

    if recomputed_hash != expected_hash:
        return {
            "status": "TAMPERED",
            "is_valid": False,
            "message": (
                "TAMPER DETECTED: Report content hash mismatch! "
                "One or more fields inside the report have been altered."
            ),
            "expected_hash": expected_hash,
            "recomputed_hash": recomputed_hash,
        }

    # Step 2: Verify Ed25519 cryptographic signature
    if not signature.is_cryptography_available():
        return {
            "status": "UNVERIFIED",
            "is_valid": False,
            "message": "The 'cryptography' library is required to verify Ed25519 signatures.",
        }

    sig_valid = signature.verify_signature(pub_key_hex, expected_hash, sig_hex)
    if not sig_valid:
        return {
            "status": "TAMPERED",
            "is_valid": False,
            "message": "TAMPER DETECTED: Ed25519 cryptographic signature is INVALID.",
        }

    return {
        "status": "VALID",
        "is_valid": True,
        "message": "Signature is VALID. The report content has NOT been altered.",
        "signer_public_key": pub_key_hex,
        "content_sha256": expected_hash,
    }


def verify_dataset_integrity(report_data: Dict[str, Any], dataset_path: str = "questions.jsonl") -> Dict[str, Any]:
    """
    Checks if the dataset currently on disk matches the dataset fingerprint
    recorded when the report was originally produced.
    """
    recorded_ds = report_data.get("dataset", {})
    recorded_hash = recorded_ds.get("sha256")

    if not recorded_hash:
        return {
            "status": "NO_FINGERPRINT",
            "is_intact": False,
            "message": "No dataset fingerprint recorded in this report.",
        }

    if not os.path.exists(dataset_path):
        return {
            "status": "FILE_MISSING",
            "is_intact": False,
            "message": f"Dataset file '{dataset_path}' was not found on disk.",
        }

    current_hash = fingerprint.calculate_file_sha256(dataset_path)
    if current_hash == recorded_hash:
        return {
            "status": "INTACT",
            "is_intact": True,
            "message": f"Dataset '{dataset_path}' matches the recorded fingerprint exactly.",
            "sha256": current_hash,
        }
    else:
        return {
            "status": "MODIFIED",
            "is_intact": False,
            "message": (
                f"Dataset '{dataset_path}' has been MODIFIED since this report was signed!\n"
                f"  Recorded SHA-256: {recorded_hash}\n"
                f"  Current  SHA-256: {current_hash}"
            ),
        }


def compare_reports(report_a: Dict[str, Any], report_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares two benchmark reports to verify test repeatability.
    Returns:
        Dictionary with reproducibility percentage, accuracy diff,
        and list of specific question answer discrepancies.
    """
    summary_a = report_a.get("summary", {})
    summary_b = report_b.get("summary", {})
    config_a = report_a.get("generation_settings", {})
    config_b = report_b.get("generation_settings", {})

    items_a = {item["question_id"]: item for item in report_a.get("results", [])}
    items_b = {item["question_id"]: item for item in report_b.get("results", [])}

    all_ids = sorted(set(items_a.keys()) | set(items_b.keys()))
    differences = []
    identical_count = 0
    total_compared = 0

    for qid in all_ids:
        in_a = items_a.get(qid)
        in_b = items_b.get(qid)

        if not in_a or not in_b:
            differences.append({
                "question_id": qid,
                "type": "missing_question",
                "in_run_a": bool(in_a),
                "in_run_b": bool(in_b),
            })
            continue

        total_compared += 1
        ans_a = str(in_a.get("model_answer", "")).strip()
        ans_b = str(in_b.get("model_answer", "")).strip()

        if ans_a == ans_b:
            identical_count += 1
        else:
            differences.append({
                "question_id": qid,
                "category": in_a.get("category", "general"),
                "prompt": in_a.get("prompt"),
                "expected": in_a.get("expected_answer"),
                "run_a_answer": ans_a,
                "run_b_answer": ans_b,
                "run_a_correct": in_a.get("is_correct"),
                "run_b_correct": in_b.get("is_correct"),
                "run_a_latency": in_a.get("latency_seconds"),
                "run_b_latency": in_b.get("latency_seconds"),
            })

    reproducibility_pct = (identical_count / total_compared * 100.0) if total_compared > 0 else 0.0

    return {
        "total_compared": total_compared,
        "identical_answers": identical_count,
        "different_answers": len(differences),
        "answer_reproducibility_pct": round(reproducibility_pct, 2),
        "accuracy_a": summary_a.get("accuracy_pct", 0.0),
        "accuracy_b": summary_b.get("accuracy_pct", 0.0),
        "accuracy_diff": round(summary_b.get("accuracy_pct", 0.0) - summary_a.get("accuracy_pct", 0.0), 2),
        "seed_identical": config_a.get("seed") == config_b.get("seed"),
        "temp_identical": config_a.get("temperature") == config_b.get("temperature"),
        "differences": differences,
    }


def save_report_file(report: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """Saves the report as formatted JSON on disk."""
    if output_path is None:
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join("reports", f"parakh_report_{timestamp}.json")
    else:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"📄 Report written to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Parakh Patra Evidence Report Generator")
    parser.add_argument("--results", default="results.jsonl", help="Results JSONL file")
    parser.add_argument("--questions", default="questions.jsonl", help="Questions dataset file")
    parser.add_argument("--model", default="HuggingFaceTB/SmolLM2-135M-Instruct", help="Model name")
    parser.add_argument("--seed", type=int, default=42, help="Seed")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature")
    parser.add_argument("--output", default="parakh_report.json", help="Output JSON path")
    parser.add_argument("--sign", action="store_true", help="Digitally sign using local private key")
    parser.add_argument("--verify", help="Verify an existing report JSON file")

    args = parser.parse_args()

    # Verification Mode
    if args.verify:
        if not os.path.exists(args.verify):
            print(f"❌ File not found: {args.verify}", file=sys.stderr)
            sys.exit(1)
        with open(args.verify, "r", encoding="utf-8") as f:
            data = json.load(f)

        print("\n" + "=" * 65)
        print(f"🛡️  VERIFYING REPORT: {args.verify}")
        print("=" * 65)
        res = verify_report(data)
        if res["is_valid"]:
            print(f"Status:  ✅ {res['status']}")
            print(f"Message: {res['message']}")
            print(f"Signer:  {res.get('signer_public_key')}")
        else:
            print(f"Status:  ❌ {res['status']}")
            print(f"Message: {res['message']}")

        # Dataset check
        ds_res = verify_dataset_integrity(data, args.questions)
        print(f"\nDataset Check: {ds_res['message']}")
        print("=" * 65 + "\n")
        sys.exit(0 if res["is_valid"] else 1)

    # Generation Mode
    print("\n" + "=" * 65)
    print("🛡️  PARAKH PATRA - EVIDENCE REPORT GENERATOR")
    print("=" * 65)
    report = create_evidence_report(
        model_name=args.model,
        results_file=args.results,
        questions_file=args.questions,
        seed=args.seed,
        temperature=args.temperature,
    )

    if args.sign:
        try:
            priv_key = signature.load_private_key()
            report = sign_report(report, priv_key)
            print("✍️  Report digitally signed with Ed25519.")
        except Exception as e:
            print(f"⚠️  Signing skipped: {e}")

    save_report_file(report, args.output)

    # Quick summary print
    s = report["summary"]
    print(f"\nReport Summary:")
    print(f"  Questions: {s['total_questions']} | Accuracy: {s['accuracy_pct']}% | Avg Latency: {s['average_latency_seconds']}s")
    print(f"  Dataset SHA-256: {report['dataset'].get('sha256')}")
    print(f"  Content SHA-256: {report['report_content_sha256']}")
    if "digital_signature" in report:
        print(f"  Ed25519 Signature: {report['digital_signature']['signature_hex'][:32]}...")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
