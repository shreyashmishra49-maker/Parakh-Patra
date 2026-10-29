"""
local_model.py - Run a Small Local AI Model with Transformers & PyTorch
======================================================================
This module loads and runs open-weight AI models locally on your CPU.
No cloud APIs, no subscriptions, and 100% private.

Selected Model for this Hardware:
- Model: "HuggingFaceTB/SmolLM2-135M-Instruct"
- Size: ~270 MB (Downloads once and is cached locally)
- RAM usage: ~350 MB in memory
- Perfect for laptops with 6 GB RAM and AMD Ryzen 5 CPU.
"""

import sys
import time
from typing import Dict, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class LocalModel:
    """
    Manages loading and text generation for a local Hugging Face model.
    Loads model weights once into CPU memory for high efficiency.
    """
    def __init__(
        self,
        model_name: str = "HuggingFaceTB/SmolLM2-135M-Instruct",
        device: str = "cpu",
    ):
        if not TORCH_AVAILABLE:
            raise RuntimeError(
                "PyTorch and Transformers are required. "
                "Install with: pip install torch transformers"
            )

        self.model_name = model_name
        self.device = device

        print(f"\n[1/3] Loading Tokenizer for '{self.model_name}'...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        print(f"[2/3] Loading Model Weights into memory ({self.device.upper()})...")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        self.model.to(self.device)
        self.model.eval()
        print("[3/3] Model loaded and ready for inference!")

    def generate(
        self,
        prompt: str,
        seed: int = 42,
        temperature: float = 0.0,
        max_new_tokens: int = 40,
    ) -> Dict[str, Any]:
        """
        Generates text given a prompt and fixed seed for repeatability.
        """
        # Set seeds for deterministic generation
        torch.manual_seed(seed)

        # Format prompt with model's instruct chat template if available
        messages = [{"role": "user", "content": prompt}]
        try:
            formatted_prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            formatted_prompt = prompt

        inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.device)

        # Settings
        do_sample = temperature > 0.0
        gen_kwargs = {
            "max_new_tokens": max_new_tokens,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        if do_sample:
            gen_kwargs["temperature"] = temperature
            gen_kwargs["do_sample"] = True
        else:
            gen_kwargs["do_sample"] = False

        start_time = time.time()
        with torch.no_grad():
            output_tokens = self.model.generate(**inputs, **gen_kwargs)
        elapsed_time = time.time() - start_time

        # Slice off the prompt tokens to get only the model's new answer
        new_tokens = output_tokens[0][inputs["input_ids"].shape[1]:]
        answer = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        return {
            "answer": answer,
            "latency_seconds": round(elapsed_time, 4),
            "seed": seed,
            "temperature": temperature,
            "max_new_tokens": max_new_tokens,
        }


class MockModel:
    """
    A lightweight simulated fallback model for instant testing and debugging
    when PyTorch / Transformers are not yet loaded.
    """
    def __init__(self, model_name: str = "mock-small-llm"):
        self.model_name = model_name

    def generate(
        self,
        prompt: str,
        seed: int = 42,
        temperature: float = 0.0,
        max_new_tokens: int = 40,
    ) -> Dict[str, Any]:
        start_time = time.time()
        time.sleep(0.05)  # brief simulation delay

        p = prompt.lower()
        if "capital of france" in p:
            ans = "The capital of France is Paris."
        elif "15 plus 27" in p or "15 + 27" in p:
            ans = "15 + 27 = 42."
        elif "luna" in p:
            ans = "Yes, Luna has a tail."
        elif "red planet" in p:
            ans = "Mars is known as the Red Planet."
        elif "heavier" in p:
            ans = "They weigh the same (both are 1 kilogram)."
        elif "2 + 2" in p or "2 plus 2" in p:
            ans = "2 + 2 = 4."
        else:
            ans = f"Answer to '{prompt}'"

        elapsed = time.time() - start_time
        return {
            "answer": ans,
            "latency_seconds": round(elapsed, 4),
            "seed": seed,
            "temperature": temperature,
            "max_new_tokens": max_new_tokens,
            "is_mock": True,
        }


def load_model(
    model_name: str = "HuggingFaceTB/SmolLM2-135M-Instruct",
    use_mock: bool = False,
    device: str = "cpu",
):
    """Factory helper to load either the real local model or mock model."""
    if use_mock or not TORCH_AVAILABLE:
        return MockModel(model_name=model_name)
    return LocalModel(model_name=model_name, device=device)


def run_standalone_test():
    """Runs a quick single question test: 'What is 2 + 2?'"""
    print("=" * 60)
    print("🛡️  Parakh Patra - Local AI Model Runner")
    print("=" * 60)

    if not TORCH_AVAILABLE:
        print("\n❌ PyTorch / Transformers are not installed in the current environment.")
        print("Falling back to simulated MockModel for demonstration:")
        model = load_model(use_mock=True)
    else:
        model = load_model("HuggingFaceTB/SmolLM2-135M-Instruct")

    question = "What is 2 + 2?"
    print(f"\nQuestion: {question}")
    result = model.generate(question, seed=42, temperature=0.0)
    print(f"Answer:   {result['answer']}")
    print(f"Latency:  {result['latency_seconds']} seconds")
    print("=" * 60)


if __name__ == "__main__":
    run_standalone_test()
