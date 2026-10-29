"""
test_runner.py - Automated Benchmark Execution & Evaluation
===========================================================
This module:
1. Loads test questions from 'questions.jsonl'.
2. Sends each question to the local AI model.
3. Records model answers, response times, and generation settings.
4. Compares model answers against expected answers to compute accuracy.
5. Saves all detailed results line-by-line into 'results.jsonl'.
6. Displays a clear, readable summary table in the terminal.

Run directly with:
    python test_runner.py
"""

import argparse
import datetime
import json
import os
import sys
import time
from typing import List, Dict, Any

# Ensure proper UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from local_model import load_model, TORCH_AVAILABLE


def load_questions(file_path: str = "questions.jsonl") -> List[Dict[str, Any]]:
    """
    Reads benchmark questions from a JSON Lines (.jsonl) file.
    Validates formatting and handles errors gracefully.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"❌ Questions file not found at: '{file_path}'\n"
            f"Please verify the file path exists."
        )

    questions = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue  # skip empty lines
            try:
                item = json.loads(line)
            except json.JSONDecodeError as err:
                raise ValueError(
                    f"❌ Invalid JSON format on line {line_num} in '{file_path}':\n"
                    f"   {err}\n"
                    f"   Line content: '{line}'"
                )

            # Validate essential fields
            if "prompt" not in item:
                raise KeyError(
                    f"❌ Missing required field 'prompt' on line {line_num} in '{file_path}'"
                )

            # Assign default values for optional fields if missing
            item.setdefault("id", f"q{line_num}")
            item.setdefault("category", "general")
            item.setdefault("expected_answer", "")
            item.setdefault("evaluation_type", "contains")

            questions.append(item)

    if not questions:
        raise ValueError(f"❌ '{file_path}' is empty. No questions found to run.")

    return questions


def evaluate_answer(model_answer: str, expected_answer: str, evaluation_type: str = "contains") -> bool:
    """
    Compares the model's output against the expected reference answer.
    
    - 'contains': Checks if the expected answer appears anywhere inside the model output
                  (case-insensitive, trimmed).
    - 'exact_match': Checks for exact string equality after stripping whitespace and lowercase.
    """
    cleaned_model = model_answer.strip().lower()
    cleaned_expected = expected_answer.strip().lower()

    if not cleaned_expected:
        return False

    if evaluation_type == "exact_match":
        return cleaned_model == cleaned_expected
    else:  # default to 'contains'
        return cleaned_expected in cleaned_model


def save_results_jsonl(results: List[Dict[str, Any]], output_path: str = "results.jsonl") -> None:
    """
    Saves each test result as a self-contained JSON record into a .jsonl file.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for record in results:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"\n📁 Saved {len(results)} detailed results to: {output_path}")
    except IOError as e:
        print(f"❌ Failed to write results to '{output_path}': {e}", file=sys.stderr)


def run_benchmark(
    questions_file: str = "questions.jsonl",
    output_file: str = "results.jsonl",
    model_name: str = "HuggingFaceTB/SmolLM2-135M-Instruct",
    seed: int = 42,
    temperature: float = 0.0,
    max_new_tokens: int = 40,
    use_mock: bool = False,
    progress_callback = None,
) -> Dict[str, Any]:
    """
    Executes the full test suite and prints transparent terminal logs.
    """
    print("\n" + "=" * 70)
    print("🛡️  PARAKH PATRA - LOCAL AI TEST RUNNER")
    print("=" * 70)
    print(f"Test File:       {questions_file}")
    print(f"Target Model:    {model_name}")
    print(f"Random Seed:     {seed}")
    print(f"Temperature:     {temperature} ({'Deterministic' if temperature == 0.0 else 'Stochastic'})")
    print(f"Max New Tokens:  {max_new_tokens}")
    print("=" * 70)

    # 1. Load questions
    try:
        questions = load_questions(questions_file)
        print(f"✅ Loaded {len(questions)} test question(s) from '{questions_file}'.")
    except Exception as e:
        print(f"\n{e}", file=sys.stderr)
        sys.exit(1)

    # 2. Load model
    try:
        print("\nInitializing local model...")
        model = load_model(model_name=model_name, use_mock=use_mock)
    except Exception as e:
        print(f"\n❌ Error initializing model: {e}", file=sys.stderr)
        print("Tip: If running without PyTorch installed, pass '--mock' for simulated test runs.")
        sys.exit(1)

    # 3. Execute questions
    print("\nStarting test execution:")
    print("-" * 70)

    results = []
    correct_count = 0
    total_time = 0.0
    total_questions = len(questions)

    for idx, q in enumerate(questions, start=1):
        q_id = q.get("id")
        prompt = q.get("prompt")
        expected = q.get("expected_answer")
        eval_type = q.get("evaluation_type", "contains")
        category = q.get("category", "general")

        print(f"\n[{idx}/{total_questions}] Question ID: {q_id} ({category})")
        print(f"Prompt:   \"{prompt}\"")
        print(f"Expected: \"{expected}\"")

        # Query model with fixed seed and generation settings
        try:
            gen_result = model.generate(
                prompt=prompt,
                seed=seed,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            model_answer = gen_result.get("answer", "")
            latency = gen_result.get("latency_seconds", 0.0)
        except Exception as e:
            print(f"⚠️  Generation failed for question {q_id}: {e}", file=sys.stderr)
            model_answer = f"[ERROR: {e}]"
            latency = 0.0

        total_time += latency

        # Evaluate correctness
        is_correct = evaluate_answer(model_answer, expected, eval_type)
        if is_correct:
            correct_count += 1
            status_tag = "✅ PASS"
        else:
            status_tag = "❌ FAIL"

        print(f"Answer:   \"{model_answer}\"")
        print(f"Status:   {status_tag} (Latency: {latency:.2f}s)")

        # Create record for results.jsonl
        record = {
            "question_id": q_id,
            "category": category,
            "prompt": prompt,
            "expected_answer": expected,
            "model_answer": model_answer,
            "is_correct": is_correct,
            "evaluation_type": eval_type,
            "latency_seconds": latency,
            "generation_settings": {
                "model_name": model_name,
                "seed": seed,
                "temperature": temperature,
                "max_new_tokens": max_new_tokens,
            },
            "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        }
        results.append(record)
        if progress_callback:
            try:
                progress_callback(idx, total_questions, record)
            except Exception:
                pass

    # 4. Save results to results.jsonl
    save_results_jsonl(results, output_file)

    # 5. Calculate and display summary statistics
    accuracy_pct = (correct_count / total_questions * 100.0) if total_questions > 0 else 0.0
    avg_latency = (total_time / total_questions) if total_questions > 0 else 0.0

    print("\n" + "=" * 70)
    print("📊 BENCHMARK SUMMARY REPORT")
    print("=" * 70)
    print(f"Total Questions Tested:  {total_questions}")
    print(f"Correct Answers:         {correct_count}")
    print(f"Incorrect Answers:       {total_questions - correct_count}")
    print(f"Accuracy Score:          {accuracy_pct:.2f}%")
    print(f"Average Response Time:   {avg_latency:.2f} seconds")
    print(f"Total Execution Time:    {total_time:.2f} seconds")
    print(f"Results Saved To:        {output_file}")
    print("=" * 70 + "\n")

    return {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "accuracy_pct": accuracy_pct,
        "average_latency": avg_latency,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parakh Patra - Local AI Benchmark Test Runner"
    )
    parser.add_argument(
        "--questions",
        default="questions.jsonl",
        help="Path to questions file (default: questions.jsonl)",
    )
    parser.add_argument(
        "--output",
        default="results.jsonl",
        help="Path to write results JSONL (default: results.jsonl)",
    )
    parser.add_argument(
        "--model",
        default="HuggingFaceTB/SmolLM2-135M-Instruct",
        help="Hugging Face model identifier or local path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation (default: 42)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default: 0.0 for deterministic)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=40,
        help="Maximum new tokens to generate (default: 40)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use simulated mock model for quick validation without heavy downloads",
    )

    args = parser.parse_args()

    run_benchmark(
        questions_file=args.questions,
        output_file=args.output,
        model_name=args.model,
        seed=args.seed,
        temperature=args.temperature,
        max_new_tokens=args.max_tokens,
        use_mock=args.mock,
    )


if __name__ == "__main__":
    main()


def main():
    parser = argparse.ArgumentParser(
        description="Parakh Patra - Local AI Benchmark Test Runner"
    )
    parser.add_argument(
        "--questions",
        default="questions.jsonl",
        help="Path to questions file (default: questions.jsonl)",
    )
    parser.add_argument(
        "--output",
        default="results.jsonl",
        help="Path to write results JSONL (default: results.jsonl)",
    )
    parser.add_argument(
        "--model",
        default="HuggingFaceTB/SmolLM2-135M-Instruct",
        help="Hugging Face model identifier or local path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation (default: 42)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default: 0.0 for deterministic)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=40,
        help="Maximum new tokens to generate (default: 40)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use simulated mock model for quick validation without heavy downloads",
    )

    args = parser.parse_args()

    run_benchmark(
        questions_file=args.questions,
        output_file=args.output,
        model_name=args.model,
        seed=args.seed,
        temperature=args.temperature,
        max_new_tokens=args.max_tokens,
        use_mock=args.mock,
    )


if __name__ == "__main__":
    main()

