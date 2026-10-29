"""
fingerprint.py - Cryptographic Fingerprinting for Parakh Patra
=============================================================
What is a SHA-256 fingerprint?
A SHA-256 fingerprint (hash) is a unique, fixed-length 64-character
hexadecimal string calculated from binary data.
Even a change of 1 single bit in a gigabyte of data produces an entirely
different hash (the avalanche effect).

In Parakh Patra, SHA-256 is used to:
1. Fingerprint the questions dataset (proves which questions were used).
2. Fingerprint the model weights and configuration files.
3. Compute a canonical hash of test report content before signing.
"""

import hashlib
import json
import os
import sys
from typing import Dict, Any, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def calculate_file_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """
    Computes the SHA-256 hash of a file by streaming it in 64 KB chunks.
    This prevents memory exhaustion when hashing large model weights.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found for hashing: '{file_path}'")

    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)

    return hasher.hexdigest()


def calculate_text_sha256(text: str) -> str:
    """Computes the SHA-256 hash of a string (UTF-8 encoded)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def calculate_dataset_fingerprint(dataset_path: str = "questions.jsonl") -> Dict[str, Any]:
    """
    Computes a comprehensive fingerprint of the benchmark dataset,
    including file size, line count, and SHA-256 hash.
    """
    if not os.path.exists(dataset_path):
        return {
            "path": dataset_path,
            "status": "missing",
            "sha256": None,
        }

    sha256 = calculate_file_sha256(dataset_path)
    file_size = os.path.getsize(dataset_path)

    # Count questions
    line_count = 0
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                line_count += 1

    return {
        "path": os.path.basename(dataset_path),
        "status": "verified",
        "sha256": sha256,
        "size_bytes": file_size,
        "total_questions": line_count,
    }


def find_cached_huggingface_model_files(model_name: str) -> Optional[str]:
    """
    Attempts to locate locally cached Hugging Face model snapshot files
    in the standard cache directory (~/.cache/huggingface/hub/).
    """
    cache_dir = os.path.expanduser(os.path.join("~", ".cache", "huggingface", "hub"))
    # Format e.g. "models--HuggingFaceTB--SmolLM2-135M-Instruct"
    repo_folder = "models--" + model_name.replace("/", "--")
    full_repo_path = os.path.join(cache_dir, repo_folder, "snapshots")

    if os.path.exists(full_repo_path):
        snapshots = os.listdir(full_repo_path)
        if snapshots:
            # Use the latest snapshot folder
            return os.path.join(full_repo_path, snapshots[-1])
    return None


def calculate_model_fingerprint(model_identifier: str) -> Dict[str, Any]:
    """
    Calculates SHA-256 fingerprints for all relevant model files:
    - Weight files (.safetensors, .bin)
    - Configuration files (config.json, tokenizer.json, generation_config.json)
    
    If the model is stored in a local folder or Hugging Face local cache,
    individual file hashes are recorded alongside a composite hash.
    """
    # 1. Check if model_identifier is a direct local path
    target_dir = None
    if os.path.isdir(model_identifier):
        target_dir = model_identifier
    else:
        # Check local HF cache
        cached_path = find_cached_huggingface_model_files(model_identifier)
        if cached_path and os.path.isdir(cached_path):
            target_dir = cached_path

    if target_dir:
        relevant_extensions = (
            ".safetensors",
            ".bin",
            ".json",
            ".model",
            ".txt"
        )
        file_hashes = {}
        for root, _, files in os.walk(target_dir):
            for filename in sorted(files):
                if filename.endswith(relevant_extensions):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, target_dir)
                    try:
                        file_hashes[rel_path] = calculate_file_sha256(full_path)
                    except Exception:
                        pass

        # Create a deterministic composite hash of all file hashes
        sorted_pairs = sorted(file_hashes.items())
        composite_input = json.dumps(sorted_pairs, sort_keys=True)
        composite_hash = calculate_text_sha256(composite_input)

        return {
            "identifier": model_identifier,
            "type": "local_snapshot",
            "snapshot_path": target_dir,
            "composite_sha256": composite_hash,
            "files_count": len(file_hashes),
            "files": file_hashes,
        }

    # Fallback for remote / mock models
    return {
        "identifier": model_identifier,
        "type": "identifier_reference",
        "composite_sha256": calculate_text_sha256(model_identifier),
        "files_count": 0,
        "files": {},
    }


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Parakh Patra - SHA-256 Fingerprinter Demonstration")
    print("=" * 60)

    # Test on questions.jsonl
    q_file = "questions.jsonl"
    if os.path.exists(q_file):
        ds_info = calculate_dataset_fingerprint(q_file)
        print(f"Dataset File:   {ds_info['path']}")
        print(f"SHA-256 Hash:   {ds_info['sha256']}")
        print(f"Size:           {ds_info['size_bytes']} bytes")
        print(f"Questions:      {ds_info['total_questions']}")
    else:
        print(f"File '{q_file}' not found.")

    # Demonstration of avalanche effect
    text_a = "Parakh Patra Test Report"
    text_b = "Parakh Patra Test Report."  # Just one single period added
    print("\nDemonstrating the Avalanche Effect (Changing 1 character):")
    print(f"Hash A: {calculate_text_sha256(text_a)}")
    print(f"Hash B: {calculate_text_sha256(text_b)}")
    print("=" * 60)
