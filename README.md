# 🛡️ Parakh Patra (परख पत्र)
*Local AI Model Testing & Cryptographic Reproducibility Auditor*

---

## 📌 Project Overview
**Parakh Patra** is an open-source, local AI benchmarking tool designed to help developers and researchers verify AI model performance claims, ensure test repeatability, and generate cryptographically signed evidence reports.

- **100% Local Inference**: Runs models on your own machine. No paid APIs, no subscriptions, and no cloud uploads.
- **Repeatable & Auditable**: Records random seeds, generation parameters, hardware specs, and software versions.
- **Cryptographic Integrity**:
  - **SHA-256** creates tamper-evident fingerprints of test datasets and model files.
  - **Ed25519** digital signatures verify that test reports have not been altered after generation.
- **Side-by-Side Repeatability Auditor**: Compare repeated test runs to detect non-determinism or answer drift.

> [!IMPORTANT]
> **Ethical & Scientific Principle:**
> A digital signature proves **authenticity and integrity** (that the report was created by the signer and was not altered). **It never proves that the AI model's answers are factually true or accurate.**

---

## 📁 Project Structure

```text
ParakhPatra/
│
├── questions.jsonl              # Test dataset in JSON Lines format
├── results.jsonl                # Detailed raw execution results
│
├── local_model.py               # Local Hugging Face & PyTorch model inference
├── test_runner.py               # Automated benchmark execution engine
├── fingerprint.py               # SHA-256 fingerprinting for data & model files
├── report_generator.py          # Evidence report generation & discrepancy auditing
├── signature.py                 # Ed25519 digital signatures & key management
├── app.py                       # Interactive Streamlit audit dashboard
│
├── requirements.txt             # Python dependencies
├── README.md                    # Project documentation
│
└── reports/
    ├── parakh_report.json       # Canonical JSON evidence report
    ├── report_signature.bin     # Raw 64-byte Ed25519 binary signature
    └── public_key.pem           # RFC 8410 PEM Public Key for external auditors
```

| File / Directory | Purpose |
| :--- | :--- |
| [`questions.jsonl`](questions.jsonl) | Test dataset in JSON Lines format (prompts, categories, expected answers). |
| [`results.jsonl`](results.jsonl) | Raw execution log with prompts, answers, latency, and generation settings. |
| [`local_model.py`](local_model.py) | Runs small open-weight AI models locally (includes simulated model fallback). |
| [`test_runner.py`](test_runner.py) | Executes questions, checks accuracy, and collects system environment data. |
| [`fingerprint.py`](fingerprint.py) | Computes SHA-256 hashes for datasets, models, and JSON text. |
| [`report_generator.py`](report_generator.py) | Builds canonical JSON evidence reports, signs them, and compares runs. |
| [`signature.py`](signature.py) | Generates Ed25519 key pairs, signs reports, and verifies signatures. |
| [`app.py`](app.py) | Interactive Streamlit web dashboard. |
| [`reports/parakh_report.json`](reports/parakh_report.json) | Complete evidence report with fingerprints and system provenance. |
| [`reports/report_signature.bin`](reports/report_signature.bin) | Detached 64-byte Ed25519 cryptographic signature. |
| [`reports/public_key.pem`](reports/public_key.pem) | Standard PEM public key allowing anyone to independently verify the signature. |
| [`requirements.txt`](requirements.txt) | Python dependencies. |
| [`README.md`](README.md) | Project guide and documentation. |

---

## 💡 Key Concepts Explained Simply

### 1. SHA-256 Fingerprint
Think of SHA-256 as a unique digital barcode. If you change even a single character in your `questions.jsonl` file, the hash changes completely. This proves to anyone checking your report that you tested the exact dataset you claimed.

### 2. Ed25519 Digital Signature
Like a wax seal on an official envelope, an Ed25519 digital signature uses asymmetric cryptography. The tester signs the test report with their secret Private Key. Anyone with the tester's Public Key can verify that:
1. The report was created by that tester.
2. Not a single number, word, or score inside the report has been altered.

### 3. Repeatability vs Accuracy
- **Accuracy** measures how many answers were correct.
- **Repeatability** measures whether running the exact same test with the exact same seed produces identical answers every time.

---

## 🚀 Recommended Small Local AI Models
These models run efficiently on standard consumer laptops without needing high-end GPUs:
1. **`HuggingFaceTB/SmolLM2-135M-Instruct`** (~270 MB) — Extremely lightweight, fast inference even on older CPUs.
2. **`Qwen/Qwen2.5-0.5B-Instruct`** (~1.0 GB) — High quality reasoning in a compact footprint.
3. **`TinyLlama/TinyLlama-1.1B-Chat-v1.0`** (~2.2 GB) — Popular small language model.

*Note: You can also use the built-in **Simulated Model** in `app.py` to test the entire workflow with zero downloads!*

---

## 🛠️ Step-by-Step Setup Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit Dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

