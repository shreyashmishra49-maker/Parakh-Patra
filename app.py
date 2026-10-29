"""
app.py - Streamlit Web Dashboard for Parakh Patra
=================================================
A local, verifiable AI model testing and cryptographic audit dashboard.
Designed for hackathon demonstrations, benchmarking, and repeatability audits.

Run with:
    streamlit run app.py
"""

import copy
import datetime
import json
import os
import sys

# Ensure local workspace modules are imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import fingerprint
import signature
import local_model
import test_runner
import report_generator


# ---------------- PAGE CONFIG & STYLING ----------------
def configure_page():
    st.set_page_config(
        page_title="Parakh Patra - Local AI Verifier",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom styling for clean, professional hackathon presentation
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1.05rem;
            color: #4B5563;
            margin-bottom: 1.2rem;
        }
        .metric-card {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px 18px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .fingerprint-box {
            font-family: 'Courier New', Courier, monospace;
            background-color: #0F172A;
            color: #38BDF8;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            word-break: break-all;
        }
        .badge-verified {
            background-color: #DCFCE7;
            color: #166534;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .badge-tampered {
            background-color: #FEE2E2;
            color: #991B1B;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)


def init_session_state():
    if "current_report" not in st.session_state:
        # Load sample report if exists in reports/ or root
        report_candidate = "reports/parakh_report.json" if os.path.exists("reports/parakh_report.json") else "parakh_report.json"
        if os.path.exists(report_candidate):
            try:
                with open(report_candidate, "r", encoding="utf-8") as f:
                    st.session_state["current_report"] = json.load(f)
            except Exception:
                st.session_state["current_report"] = None
        else:
            st.session_state["current_report"] = None

    if "test_runs" not in st.session_state:
        st.session_state["test_runs"] = []
    if "private_key" not in st.session_state:
        # Check if saved key exists in keys/
        try:
            st.session_state["private_key"] = signature.load_private_key()
        except Exception:
            st.session_state["private_key"] = None
    if "public_key" not in st.session_state:
        if st.session_state["private_key"]:
            try:
                st.session_state["public_key"] = signature.get_public_key_from_private(st.session_state["private_key"])
            except Exception:
                st.session_state["public_key"] = None
        else:
            st.session_state["public_key"] = None


def main():
    configure_page()
    init_session_state()

    # Title & Subtitle
    st.markdown('<div class="main-header">🛡️ Parakh Patra (परख पत्र)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Local AI Benchmark Auditor • Cryptographic Proof of Integrity • Reproducibility Verifier</div>',
        unsafe_allow_html=True
    )

    # Core Ethical Principle Banner
    st.info(
        "⚖️ **Foundational Principle:** A valid digital signature guarantees **evidence integrity** "
        "(the report has not been altered) and **authenticity** (who performed the test). "
        "A digital signature **never** proves that an AI model is accurate, truthful, or safe."
    )

    # ---------------- SIDEBAR: CONFIGURATION & HARDWARE ----------------
    with st.sidebar:
        st.header("⚙️ Test & Model Setup")

        # 1. Local Model Information
        st.subheader("1. Local AI Model")
        model_options = [
            "HuggingFaceTB/SmolLM2-135M-Instruct (Recommended ~270MB)",
            "Qwen/Qwen2.5-0.5B-Instruct (~1.0GB)",
            "Simulated Model (Instant Mock - No GPU/RAM Needed)",
        ]
        selected_model_option = st.selectbox("Select Model:", model_options, index=0)
        is_mock = "Simulated Model" in selected_model_option
        model_id = "mock-small-llm" if is_mock else selected_model_option.split()[0]

        # Hardware & Software Specs
        env_specs = report_generator.get_detailed_system_environment()
        with st.expander("💻 Local Hardware Specs"):
            st.caption(f"**OS:** {env_specs['os_name']} {env_specs['os_release']} ({env_specs['architecture']})")
            st.caption(f"**Processor:** {env_specs['processor']}")
            st.caption(f"**Python:** {env_specs['python_version']}")
            st.caption(f"**PyTorch:** {env_specs['torch_version']}")
            st.caption(f"**Transformers:** {env_specs['transformers_version']}")
            st.caption(f"**CUDA GPU:** {'Available' if env_specs.get('cuda_available') else 'Not Present (Using CPU)'}")

        st.divider()

        # 2. Test Dataset Selection
        st.subheader("2. Test Dataset")
        available_datasets = ["questions.jsonl"]
        if os.path.exists("questions.jsonl"):
            ds_choice = st.selectbox("Choose Dataset File:", available_datasets, index=0)
        else:
            ds_choice = st.text_input("Dataset File:", value="questions.jsonl")

        # Dataset statistics
        if os.path.exists(ds_choice):
            ds_meta = fingerprint.calculate_dataset_fingerprint(ds_choice)
            st.caption(f"📊 **Questions:** {ds_meta['total_questions']} | **Size:** {ds_meta['size_bytes']} bytes")
            st.caption(f"🔒 **SHA-256:** `{ds_meta['sha256'][:16]}...`")
        else:
            st.error(f"File '{ds_choice}' not found.")

        st.divider()

        # 3. Deterministic Settings
        st.subheader("3. Generation Parameters")
        seed = st.number_input("Random Seed:", value=42, step=1, help="Fixed seed for repeatable generations")
        temperature = st.slider(
            "Temperature:",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            help="0.0 = Deterministic (Greedy Search), >0.0 = Stochastic"
        )
        max_tokens = st.slider("Max New Tokens:", 10, 128, 40, 5)

        st.divider()
        st.caption("Parakh Patra runs 100% locally. Zero telemetry, zero cloud APIs.")

    # ---------------- MAIN CONTENT TABS ----------------
    tab_benchmark, tab_evidence, tab_repeat = st.tabs([
        "🧪 1. Run & Audit Benchmark",
        "📜 2. Cryptographic Evidence & Signatures",
        "🔄 3. Repeatability & Discrepancies Auditor"
    ])

    # =========================================================================
    # TAB 1: RUN BENCHMARK
    # =========================================================================
    with tab_benchmark:
        st.subheader("Automated Local Model Benchmark")

        # Top Action Bar: Run Test & Repeat Test Buttons
        col_btn1, col_btn2, col_info = st.columns([1.5, 1.5, 3])
        run_clicked = False
        repeat_clicked = False

        with col_btn1:
            run_clicked = st.button("🚀 Run Local Test", type="primary", use_container_width=True)
        with col_btn2:
            repeat_clicked = st.button("🔄 Repeat Test (Same Seed)", use_container_width=True)

        with col_info:
            if st.session_state.get("test_runs"):
                st.caption(f"Completed Runs in Memory: **{len(st.session_state['test_runs'])}**")

        # Execute Test if either button clicked
        if run_clicked or repeat_clicked:
            # If repeat was clicked and we have a previous run, use its exact seed
            effective_seed = seed
            if repeat_clicked and st.session_state.get("test_runs"):
                effective_seed = st.session_state["test_runs"][-1].get("generation_settings", {}).get("seed", seed)

            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_callback(current, total, record):
                pct = int(current / total * 100)
                progress_bar.progress(pct)
                status_text.text(f"Testing Question {current}/{total}: \"{record['prompt'][:45]}...\"")

            with st.spinner(f"Executing benchmark on {model_id} (Seed {effective_seed})..."):
                try:
                    bench_output = test_runner.run_benchmark(
                        questions_file=ds_choice,
                        output_file="results.jsonl",
                        model_name=model_id,
                        seed=effective_seed,
                        temperature=temperature,
                        max_new_tokens=max_tokens,
                        use_mock=is_mock,
                        progress_callback=progress_callback,
                    )

                    # Build canonical evidence report using existing module
                    report = report_generator.create_evidence_report(
                        model_name=model_id,
                        results_file="results.jsonl",
                        questions_file=ds_choice,
                        seed=effective_seed,
                        temperature=temperature,
                        notes=f"Test run on {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                    )

                    # Auto-sign if private key is available
                    if st.session_state.get("private_key"):
                        report = report_generator.sign_report(report, st.session_state["private_key"])

                    # Save in session
                    st.session_state["current_report"] = report
                    st.session_state["test_runs"].append(report)
                    report_generator.save_report_file(report, "parakh_report.json")
                    if st.session_state.get("private_key"):
                        signature.save_reports_bundle(report, st.session_state["private_key"], output_dir="reports")
                    else:
                        report_generator.save_report_file(report, "reports/parakh_report.json")

                    progress_bar.progress(100)
                    status_text.empty()
                    st.success(f"🎉 Test complete! Accuracy: **{bench_output['accuracy_pct']}%** | Avg Latency: **{bench_output['average_latency']:.2f}s**")

                except Exception as e:
                    st.error(f"❌ Execution failed: {str(e)}")

        st.markdown("---")

        # Display Live / Current Results
        current = st.session_state.get("current_report")
        if current:
            summ = current.get("summary", {})
            m_info = current.get("model", {})
            d_info = current.get("dataset", {})

            # 4. Metrics Cards
            st.markdown("### 📊 Benchmark Performance Metrics")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Accuracy Score", f"{summ.get('accuracy_pct', 0.0)}%", help="Percentage of expected answers found")
            m_col2.metric("Questions Passed", f"{summ.get('correct_count', 0)} / {summ.get('total_questions', 0)}")
            m_col3.metric("Avg Response Time", f"{summ.get('average_latency_seconds', 0.0):.3f}s")
            m_col4.metric("Total Latency", f"{summ.get('total_latency_seconds', 0.0):.2f}s")

            # 5. Model & Dataset SHA-256 Fingerprints
            st.markdown("### 🔒 Cryptographic Fingerprints")
            fp_col1, fp_col2 = st.columns(2)
            with fp_col1:
                st.markdown("**Dataset Fingerprint (SHA-256)**")
                ds_hash = d_info.get("sha256", "N/A")
                st.markdown(f'<div class="fingerprint-box">DATASET SHA-256:\n{ds_hash}</div>', unsafe_allow_html=True)
                st.caption(f"Source: `{d_info.get('path')}` ({d_info.get('size_bytes', 0)} bytes)")

            with fp_col2:
                st.markdown("**Model Fingerprint (SHA-256)**")
                mfp = m_info.get("fingerprint", {})
                m_hash = mfp.get("composite_sha256", "N/A")
                st.markdown(f'<div class="fingerprint-box">MODEL SHA-256:\n{m_hash}</div>', unsafe_allow_html=True)
                st.caption(f"Model ID: `{m_info.get('name')}` (Revision: `{m_info.get('revision', 'main')}`)")

            # Detailed Questions List
            st.markdown("### 📝 Per-Question Audit Log")
            results_list = current.get("results", [])
            for item in results_list:
                status_icon = "✅" if item.get("is_correct") else "❌"
                with st.expander(f"{status_icon} [{item.get('category', 'general').upper()}] {item.get('prompt')}"):
                    c_a, c_b = st.columns(2)
                    with c_a:
                        st.markdown(f"**Expected Answer:** `{item.get('expected_answer')}`")
                        st.markdown(f"**Model Answer:** `{item.get('model_answer')}`")
                    with c_b:
                        st.markdown(f"**Status:** {'PASS' if item.get('is_correct') else 'FAIL'}")
                        st.markdown(f"**Latency:** `{item.get('latency_seconds', 0.0)}s`")
                        st.markdown(f"**Eval Type:** `{item.get('evaluation_type')}`")
        else:
            st.info("👆 Click **'Run Local Test'** above to execute the benchmark.")

    # =========================================================================
    # TAB 2: EVIDENCE REPORT & SIGNATURES
    # =========================================================================
    with tab_evidence:
        st.subheader("Cryptographic Evidence Report & Digital Signatures")

        current_rep = st.session_state.get("current_report")

        # Step A: Ed25519 Key Pair Management
        st.markdown("#### 1. Ed25519 Signing Keys")
        k_col1, k_col2 = st.columns([1.5, 3])
        with k_col1:
            if st.button("🔑 Generate New Key Pair", use_container_width=True):
                if signature.is_cryptography_available():
                    priv, pub = signature.generate_key_pair()
                    st.session_state["private_key"] = priv
                    st.session_state["public_key"] = pub
                    signature.save_key_pair(priv, pub)
                    st.success("New Ed25519 keys generated and saved to keys/")
                else:
                    st.error("The 'cryptography' library is required.")

        with k_col2:
            if st.session_state.get("public_key"):
                st.text_input("Signer Public Key (Hex):", value=st.session_state["public_key"], disabled=True)
            else:
                st.caption("No key pair loaded. Click 'Generate New Key Pair' to create one.")

        st.markdown("---")

        # Step B: Report Status & Verification
        st.markdown("#### 2. Evidence Report Status & Integrity Check")

        if current_rep:
            # Check digital signature status using report_generator module
            ver_res = report_generator.verify_report(current_rep)
            ds_check = report_generator.verify_dataset_integrity(current_rep, ds_choice)

            col_v1, col_v2 = st.columns(2)
            with col_v1:
                if ver_res["is_valid"]:
                    st.markdown("""
                        <div class="metric-card" style="border-left: 5px solid #22C55E;">
                            <span class="badge-verified">✅ VALID SIGNATURE</span>
                            <h4 style="margin: 6px 0 2px 0;">Cryptographic Integrity Verified</h4>
                            <p style="font-size: 0.85rem; color: #4B5563; margin: 0;">
                                Report content has NOT been altered since signing.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                elif ver_res["status"] == "UNSIGNED":
                    st.markdown("""
                        <div class="metric-card" style="border-left: 5px solid #EAB308;">
                            <span style="background-color: #FEF08A; color: #854D0E; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">⚠️ UNSIGNED</span>
                            <h4 style="margin: 6px 0 2px 0;">Report Not Yet Signed</h4>
                            <p style="font-size: 0.85rem; color: #4B5563; margin: 0;">Sign this report below to attach proof of integrity.</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class="metric-card" style="border-left: 5px solid #EF4444;">
                            <span class="badge-tampered">❌ TAMPER DETECTED</span>
                            <h4 style="margin: 6px 0 2px 0;">{ver_res['status']}</h4>
                            <p style="font-size: 0.85rem; color: #DC2626; margin: 0;">{ver_res['message']}</p>
                        </div>
                    """, unsafe_allow_html=True)

            with col_v2:
                if ds_check["is_intact"]:
                    st.markdown("""
                        <div class="metric-card" style="border-left: 5px solid #22C55E;">
                            <span class="badge-verified">✅ DATASET INTACT</span>
                            <h4 style="margin: 6px 0 2px 0;">Dataset Fingerprint Verified</h4>
                            <p style="font-size: 0.85rem; color: #4B5563; margin: 0;">
                                The questions file matches the recorded SHA-256 hash.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class="metric-card" style="border-left: 5px solid #EF4444;">
                            <span class="badge-tampered">⚠️ DATASET MODIFIED</span>
                            <h4 style="margin: 6px 0 2px 0;">Hash Mismatch</h4>
                            <p style="font-size: 0.85rem; color: #DC2626; margin: 0;">{ds_check['message']}</p>
                        </div>
                    """, unsafe_allow_html=True)

            # Action Buttons: Sign & Download
            st.markdown("#### 3. Actions & Download")
            act_col1, act_col2, _ = st.columns([1.5, 2, 2.5])
            with act_col1:
                if st.button("✍️ Sign Current Report", type="primary", use_container_width=True):
                    if st.session_state.get("private_key"):
                        signed = report_generator.sign_report(current_rep, st.session_state["private_key"])
                        st.session_state["current_report"] = signed
                        signature.save_reports_bundle(signed, st.session_state["private_key"], output_dir="reports")
                        report_generator.save_report_file(signed, "parakh_report.json")
                        st.success("Report successfully signed! Saved to reports/ bundle.")
                        st.rerun()
                    else:
                        st.error("No private key available to sign. Generate one first.")

            with act_col2:
                # 6. Downloadable JSON evidence report
                report_json_str = json.dumps(current_rep, indent=2, ensure_ascii=False)
                st.download_button(
                    "📥 Download Evidence Report (.json)",
                    data=report_json_str,
                    file_name="parakh_evidence_report.json",
                    mime="application/json",
                    use_container_width=True,
                )

            # Interactive Tamper Demonstration for Judges
            with st.expander("🧪 Hackathon Interactive Tamper Demonstration"):
                st.write(
                    "Demonstrate to judges how Ed25519 detects unauthorized alterations. "
                    "Edit any character below (for example, change the accuracy score from 100 to 90) "
                    "and click **Test Tamper Detection**."
                )
                tamper_text = st.text_area(
                    "Simulate Tampered Report Content:",
                    value=json.dumps(current_rep, indent=2),
                    height=200
                )
                if st.button("🚨 Test Tamper Detection"):
                    try:
                        tampered_dict = json.loads(tamper_text)
                        t_res = report_generator.verify_report(tampered_dict)
                        if t_res["is_valid"]:
                            st.success("✅ Content verified! No alterations detected.")
                        else:
                            st.error(f"❌ TAMPER DETECTED: {t_res['message']}")
                    except Exception as err:
                        st.error(f"Invalid JSON: {err}")

            with st.expander("👁️ View Complete Raw Evidence Report JSON"):
                st.json(current_rep)
        else:
            st.info("No report generated yet. Run a benchmark in Tab 1 first.")

    # =========================================================================
    # TAB 3: REPEATABILITY & DISCREPANCY AUDITOR
    # =========================================================================
    with tab_repeat:
        st.subheader("Repeatability & Discrepancy Auditor")
        st.write(
            "Verifies whether running the same test produces deterministic answers "
            "or whether non-deterministic hardware/software variations occurred."
        )

        all_runs = st.session_state.get("test_runs", [])
        if len(all_runs) < 2:
            st.warning("⚠️ At least 2 test runs are needed for comparison. Click **'Repeat Test'** in Tab 1.")
            if st.button("🔄 Execute Second Run Now", type="primary"):
                with st.spinner("Executing comparison run..."):
                    test_runner.run_benchmark(
                        questions_file=ds_choice,
                        output_file="results.jsonl",
                        model_name=model_id,
                        seed=seed,
                        temperature=temperature,
                        max_new_tokens=max_tokens,
                        use_mock=is_mock,
                    )
                    rep_repeat = report_generator.create_evidence_report(
                        model_name=model_id,
                        results_file="results.jsonl",
                        questions_file=ds_choice,
                        seed=seed,
                        temperature=temperature,
                        notes="Repeat run for comparison",
                    )
                    if st.session_state.get("private_key"):
                        rep_repeat = report_generator.sign_report(rep_repeat, st.session_state["private_key"])
                    st.session_state["test_runs"].append(rep_repeat)
                    st.session_state["current_report"] = rep_repeat
                    st.success("Second run completed!")
                    st.rerun()
        else:
            # 8 & 9: Select runs to compare
            run_labels = [
                f"Run #{i+1} — {r.get('model', {}).get('name', 'Model')} (Seed {r.get('generation_settings', {}).get('seed')}) @ {r.get('timestamp_utc', '')[-9:-1]}"
                for i, r in enumerate(all_runs)
            ]

            comp_col1, comp_col2 = st.columns(2)
            with comp_col1:
                idx_baseline = st.selectbox("Baseline Run (Original):", range(len(all_runs)), format_func=lambda i: run_labels[i], index=0)
            with comp_col2:
                idx_repeated = st.selectbox("Repeated Run:", range(len(all_runs)), format_func=lambda i: run_labels[i], index=len(all_runs)-1)

            # Compare reports using report_generator module
            diff = report_generator.compare_reports(all_runs[idx_baseline], all_runs[idx_repeated])

            st.markdown("### 📈 Repeatability Summary")
            r_col1, r_col2, r_col3, r_col4 = st.columns(4)
            r_col1.metric("Answer Reproducibility", f"{diff['answer_reproducibility_pct']}%")
            r_col2.metric("Identical Answers", f"{diff['identical_answers']} / {diff['total_compared']}")
            r_col3.metric("Discrepancies", diff["different_answers"])
            r_col4.metric("Accuracy Variance", f"{diff['accuracy_diff']:+0.2f}%")

            if diff["different_answers"] == 0:
                st.success("✅ **100% Deterministic Reproducibility**: Every prompt produced the identical response.")
            else:
                st.warning(f"⚠️ **Discrepancy Detected**: Found {diff['different_answers']} different answer(s) between the two runs.")

            # 9. Side-by-Side Original vs Repeated Result Comparison Table
            st.markdown("### 🔍 Side-by-Side Question Comparison")
            items_base = {item["question_id"]: item for item in all_runs[idx_baseline].get("results", [])}
            items_rep = {item["question_id"]: item for item in all_runs[idx_repeated].get("results", [])}

            for qid in sorted(set(items_base.keys()) | set(items_rep.keys())):
                b_item = items_base.get(qid, {})
                r_item = items_rep.get(qid, {})
                prompt_text = b_item.get("prompt") or r_item.get("prompt")
                expected_ans = b_item.get("expected_answer") or r_item.get("expected_answer")

                ans_b = str(b_item.get("model_answer", "")).strip()
                ans_r = str(r_item.get("model_answer", "")).strip()
                is_match = (ans_b == ans_r)

                status_badge = "✅ MATCH" if is_match else "⚠️ MISMATCH"
                with st.expander(f"{status_badge} [{qid}] {prompt_text}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Baseline Run (#{idx_baseline+1}):**")
                        st.code(ans_b or "[No response]", language="text")
                        st.caption(f"Correct: {b_item.get('is_correct')} | Latency: {b_item.get('latency_seconds', 0.0)}s")
                    with c2:
                        st.markdown(f"**Repeated Run (#{idx_repeated+1}):**")
                        st.code(ans_r or "[No response]", language="text")
                        st.caption(f"Correct: {r_item.get('is_correct')} | Latency: {r_item.get('latency_seconds', 0.0)}s")

                    if not is_match:
                        st.error(f"Expected reference answer: '{expected_ans}'")


if __name__ == "__main__":
    main()
