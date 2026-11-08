"""Frozen generation contract shared by the A8 experiments."""
from functools import lru_cache
from time import perf_counter

MODEL = "Qwen/Qwen2-0.5B-Instruct"
REVISION = "c540970f9e29518b1d8f06ab8b24cba66ad77b6d"
MAX_NEW_TOKENS = 128
SYSTEM = (
    "You answer questions about the Hestia household handbook. Use only the cited passages. "
    "Answer all parts of the question directly, preserving the names, quantities and conditions "
    "in the handbook. If a detail is missing, say that the handbook does not specify it."
)


@lru_cache(maxsize=1)
def load_generator():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, dtype=torch.float32, use_safetensors=True
    ).to("cpu").eval()
    return tokenizer, model


def messages(query, hits):
    context = "\n\n".join(f"[{hit['chunk_id']}]\n{hit['text']}" for hit in hits)
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Handbook passages:\n{context}\n\nQuestion: {query}"}]


def generate_answer(query, hits):
    """Person 2 adapter interface. Only the query and ranked hits enter the prompt."""
    import torch
    tokenizer, model = load_generator()
    started = perf_counter()
    prompt = tokenizer.apply_chat_template(messages(query, hits), tokenize=False,
                                           add_generation_prompt=True)
    inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
    length = inputs.input_ids.shape[1]
    if length + MAX_NEW_TOKENS > model.config.max_position_embeddings:
        raise ValueError("Retrieved context and requested output exceed the generator window")
    with torch.inference_mode():
        output = model.generate(**inputs, do_sample=False, num_beams=1,
                                max_new_tokens=MAX_NEW_TOKENS, pad_token_id=tokenizer.eos_token_id)
    tokens = output[0, length:]
    answer = tokenizer.decode(tokens, skip_special_tokens=True).strip()
    if not answer:
        raise ValueError("Generator returned an empty answer")
    return dict(answer=answer, prompt=prompt, generation_ms=(perf_counter()-started)*1000,
                input_tokens=length, output_tokens=len(tokens), context_truncated=False,
                reached_token_cap=len(tokens) == MAX_NEW_TOKENS)
