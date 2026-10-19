"""Load a local Hugging Face causal LM and extract Brain Dump task drafts."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from workflows.services.brain_dump import (
    SYSTEM_INSTRUCTION,
    BrainDumpError,
    build_user_prompt,
    parse_tasks_payload,
)

logger = logging.getLogger(__name__)

_MODEL = None
_TOKENIZER = None
_MODEL_KEY: tuple[str, str] | None = None


def _config() -> dict[str, Any]:
    return {
        "model_id": getattr(
            settings,
            "HF_BRAIN_DUMP_MODEL",
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        ),
        "device": getattr(settings, "HF_BRAIN_DUMP_DEVICE", "cpu"),
        "max_new_tokens": int(getattr(settings, "HF_BRAIN_DUMP_MAX_NEW_TOKENS", 220)),
        "token": getattr(settings, "HF_TOKEN", "") or None,
        "shot_mode": getattr(settings, "HF_BRAIN_DUMP_SHOT_MODE", "few"),
    }


def reset_pipeline() -> None:
    """Clear the cached model (tests / model id changes)."""
    global _MODEL, _TOKENIZER, _MODEL_KEY
    _MODEL = None
    _TOKENIZER = None
    _MODEL_KEY = None


def _torch_device(device: str):
    import torch

    if device == "cuda" and torch.cuda.is_available():
        return "cuda"
    if device == "mps" and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_model():
    """Lazily load and cache tokenizer + causal LM."""
    global _MODEL, _TOKENIZER, _MODEL_KEY
    cfg = _config()
    key = (cfg["model_id"], cfg["device"])
    if _MODEL is not None and _MODEL_KEY == key:
        return _TOKENIZER, _MODEL

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise BrainDumpError(
            "torch/transformers are not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    model_id = cfg["model_id"]
    device = _torch_device(cfg["device"])
    dtype = torch.float16 if device in {"cuda", "mps"} else torch.float32
    logger.info("Loading Brain Dump model %s on %s", model_id, device)
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id, token=cfg["token"])
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=dtype,
            token=cfg["token"],
        )
        model.to(device)
        model.eval()
    except Exception as exc:  # noqa: BLE001
        raise BrainDumpError(f"Failed to load model {model_id}: {exc}") from exc
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    _TOKENIZER, _MODEL, _MODEL_KEY = tokenizer, model, key
    return tokenizer, model


def _format_for_model(tokenizer, user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_prompt},
    ]
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    return (
        f"Instruction:\n{SYSTEM_INSTRUCTION}\n\n"
        f"User:\n{user_prompt}\n\nAssistant:\n"
    )


def _generate_raw(user_prompt: str) -> str:
    import torch

    cfg = _config()
    tokenizer, model = get_model()
    device = next(model.parameters()).device
    prompt = _format_for_model(tokenizer, user_prompt)
    encoded = tokenizer(prompt, return_tensors="pt").to(device)
    try:
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                max_new_tokens=cfg["max_new_tokens"],
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )
    except Exception as exc:  # noqa: BLE001
        raise BrainDumpError(f"Model generation failed: {exc}") from exc
    new_tokens = generated[0, encoded["input_ids"].shape[1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def extract_tasks(
    brain_dump: str,
    *,
    examples: str = "",
    model_id: str | None = None,
    shot_mode: str | None = None,
) -> dict[str, Any]:
    """
    Run local HF extraction using the shared notebook contract.

    Returns tasks, warnings, model_id, and raw model text.
    """
    del examples  # shared EXAMPLES are selected via shot_mode
    previous_model = None
    if model_id:
        previous_model = getattr(settings, "HF_BRAIN_DUMP_MODEL", None)
        settings.HF_BRAIN_DUMP_MODEL = model_id
        reset_pipeline()
    try:
        mode = shot_mode or _config()["shot_mode"]
        user_prompt = build_user_prompt(brain_dump, shot_mode=mode)
        raw = _generate_raw(user_prompt)
        tasks, warnings = parse_tasks_payload(raw)
        return {
            "tasks": tasks,
            "warnings": warnings,
            "model_id": _config()["model_id"],
            "raw": raw,
            "shot_mode": mode,
        }
    finally:
        if model_id is not None and previous_model is not None:
            settings.HF_BRAIN_DUMP_MODEL = previous_model
            reset_pipeline()
