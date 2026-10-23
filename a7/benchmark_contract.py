"""Locked model, prompt, and evaluation contract for Assignment 7."""

from collections import Counter


MODEL_REGISTRY = [
    {"model_id": "distilbert/distilgpt2", "params_b": 0.082, "category": "Ultra-light (<0.2B)", "owner": "P1"},
    {"model_id": "facebook/opt-125m", "params_b": 0.125, "category": "Ultra-light (<0.2B)", "owner": "P2"},
    {"model_id": "HuggingFaceTB/SmolLM2-135M-Instruct", "params_b": 0.135, "category": "Ultra-light (<0.2B)", "owner": "P3"},
    {"model_id": "HuggingFaceTB/SmolLM-360M-Instruct", "params_b": 0.360, "category": "Compact (0.2B–<0.6B)", "owner": "P4"},
    {"model_id": "HuggingFaceTB/SmolLM2-360M-Instruct", "params_b": 0.360, "category": "Compact (0.2B–<0.6B)", "owner": "P1"},
    {"model_id": "Qwen/Qwen2-0.5B-Instruct", "params_b": 0.494, "category": "Compact (0.2B–<0.6B)", "owner": "P2"},
    {"model_id": "Qwen/Qwen3-0.6B", "params_b": 0.600, "category": "Small (0.6B–<1.6B)", "owner": "P3"},
    {"model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "params_b": 1.100, "category": "Small (0.6B–<1.6B)", "owner": "P4"},
    {"model_id": "Qwen/Qwen2.5-1.5B-Instruct", "params_b": 1.540, "category": "Small (0.6B–<1.6B)", "owner": "P1"},
    {"model_id": "HuggingFaceTB/SmolLM2-1.7B-Instruct", "params_b": 1.700, "category": "Medium (1.6B–<3.5B)", "owner": "P2"},
    {"model_id": "Qwen/Qwen2.5-3B-Instruct", "params_b": 3.090, "category": "Medium (1.6B–<3.5B)", "owner": "P3"},
    {"model_id": "meta-llama/Llama-3.2-3B-Instruct", "params_b": 3.210, "category": "Medium (1.6B–<3.5B)", "owner": "P4", "access": "gated"},
    {"model_id": "microsoft/Phi-3.5-mini-instruct", "params_b": 3.820, "category": "Large (≥3.5B)", "owner": "P1"},
    {"model_id": "mistralai/Mistral-7B-Instruct-v0.3", "params_b": 7.250, "category": "Large (≥3.5B)", "owner": "P2"},
    {"model_id": "Qwen/Qwen2.5-7B-Instruct", "params_b": 7.620, "category": "Large (≥3.5B)", "owner": "P3"},
]

for model in MODEL_REGISTRY:
    model["model_card"] = f"https://huggingface.co/{model['model_id']}"


PROMPTS = [
    # Structured extraction
    {"prompt_id": "extraction-01", "prompt_type": "structured_extraction", "input": "Guests arrive tomorrow. Clean the kitchen, buy snacks, and fix the leaking bathroom tap."},
    {"prompt_id": "extraction-02", "prompt_type": "structured_extraction", "input": "This week I need to book the dentist, replace smoke-detector batteries, return a library book by Friday, and wash the guest sheets."},
    {"prompt_id": "extraction-03", "prompt_type": "structured_extraction", "input": "Before Saturday, vacuum the living room and pick up the birthday cake. The loose stair rail also needs repair."},
    {"prompt_id": "extraction-04", "prompt_type": "structured_extraction", "input": "Please remind us to pay the electricity bill tonight, schedule the dog's vet visit, and get laundry detergent."},
    {"prompt_id": "extraction-05", "prompt_type": "structured_extraction", "input": "The refrigerator is making noise. Also organize the hall closet and mail the tax documents before Monday."},
    # Classification
    {"prompt_id": "classification-01", "prompt_type": "classification", "input": "Buy milk and rice after work."},
    {"prompt_id": "classification-02", "prompt_type": "classification", "input": "Call the plumber about the dripping kitchen pipe."},
    {"prompt_id": "classification-03", "prompt_type": "classification", "input": "Schedule a yearly dental cleaning."},
    {"prompt_id": "classification-04", "prompt_type": "classification", "input": "Submit the apartment renewal form by Friday."},
    {"prompt_id": "classification-05", "prompt_type": "classification", "input": "Sweep the porch and empty the recycling."},
    # Priority prediction
    {"prompt_id": "priority-01", "prompt_type": "priority_prediction", "input": "The smoke detector is chirping because its battery is low."},
    {"prompt_id": "priority-02", "prompt_type": "priority_prediction", "input": "Sort the photo drawer whenever there is free time."},
    {"prompt_id": "priority-03", "prompt_type": "priority_prediction", "input": "Return the library book tomorrow to avoid a fee."},
    {"prompt_id": "priority-04", "prompt_type": "priority_prediction", "input": "Water is rapidly leaking under the bathroom sink."},
    {"prompt_id": "priority-05", "prompt_type": "priority_prediction", "input": "Buy coffee sometime this week; enough remains for two days."},
    # Summarization
    {"prompt_id": "summary-01", "prompt_type": "summarization", "input": "The pantry shelves have crumbs and expired cans. Remove old food, wipe each shelf, and group the remaining items."},
    {"prompt_id": "summary-02", "prompt_type": "summarization", "input": "Call the pediatric clinic, ask for an appointment after 3 PM next week, and write the confirmed time on the family calendar."},
    {"prompt_id": "summary-03", "prompt_type": "summarization", "input": "Compare the electricity statements from the last three months and contact the provider if the unexplained increase continues."},
    {"prompt_id": "summary-04", "prompt_type": "summarization", "input": "Gather the borrowed books from the bedrooms, check their due dates, and return everything due this weekend."},
    {"prompt_id": "summary-05", "prompt_type": "summarization", "input": "Before the guests arrive, replace the guest-room sheets, add clean towels, empty the bin, and check the bedside lamp."},
    # Action planning
    {"prompt_id": "planning-01", "prompt_type": "action_planning", "input": "Prepare the apartment for overnight guests tomorrow."},
    {"prompt_id": "planning-02", "prompt_type": "action_planning", "input": "Organize a weekly grocery trip while staying under a $90 budget."},
    {"prompt_id": "planning-03", "prompt_type": "action_planning", "input": "Deep-clean the kitchen safely in one afternoon."},
    {"prompt_id": "planning-04", "prompt_type": "action_planning", "input": "Get ready for a move to a new apartment next month."},
    {"prompt_id": "planning-05", "prompt_type": "action_planning", "input": "Create a simple plan for reducing household electricity use this week."},
]


EVALUATION_CRITERIA = [
    {"criterion": "task_accuracy", "max_points": 3, "description": "Correctly addresses the household request without changing its meaning."},
    {"criterion": "instruction_adherence", "max_points": 2, "description": "Follows the requested task and output instructions."},
    {"criterion": "completeness", "max_points": 2, "description": "Includes all essential requested information."},
    {"criterion": "clarity", "max_points": 2, "description": "Produces concise, understandable, usable text."},
    {"criterion": "no_unsupported_details", "max_points": 1, "description": "Avoids invented facts, dates, people, or requirements."},
]


OUTPUT_INSTRUCTIONS = {
    "structured_extraction": (
        'Return JSON only: {"tasks":[{"title":"...","task_type":"CHORE|APPOINTMENT|DEADLINE|ERRAND|MAINTENANCE|SHOPPING|OTHER",'
        '"priority":"LOW|MEDIUM|HIGH|URGENT","description":"..."}]}. Create one task per concern.'
    ),
    "classification": "Return exactly one label: CHORE, APPOINTMENT, DEADLINE, ERRAND, MAINTENANCE, SHOPPING, or OTHER.",
    "priority_prediction": "Return exactly one label: LOW, MEDIUM, HIGH, or URGENT. Use urgency and safety risk, not dramatic wording.",
    "summarization": 'Return JSON only: {"title":"short action title","summary":"one concise sentence"}.',
    "action_planning": 'Return JSON only: {"steps":["step 1","step 2","step 3"]}. Use 3 to 5 practical ordered steps.',
}


def render_prompt(prompt: dict[str, str]) -> str:
    """Render one fixed benchmark prompt without model-specific changes."""
    return (
        "You are Hestia, a household coordination assistant. "
        "Do not invent private details or claim that an action is complete.\n"
        f"{OUTPUT_INSTRUCTIONS[prompt['prompt_type']]}\n"
        f"Household request: {prompt['input']}\n"
        "Answer:"
    )


def validate_contract() -> None:
    """Raise AssertionError if the shared experiment matrix drifts."""
    assert len(MODEL_REGISTRY) == 15
    assert len({model["model_id"] for model in MODEL_REGISTRY}) == 15
    assert set(Counter(model["category"] for model in MODEL_REGISTRY).values()) == {3}
    assert Counter(model["owner"] for model in MODEL_REGISTRY) == {"P1": 4, "P2": 4, "P3": 4, "P4": 3}
    assert len(PROMPTS) == 25
    assert len({prompt["prompt_id"] for prompt in PROMPTS}) == 25
    assert set(Counter(prompt["prompt_type"] for prompt in PROMPTS).values()) == {5}
    assert set(OUTPUT_INSTRUCTIONS) == {prompt["prompt_type"] for prompt in PROMPTS}
    assert sum(item["max_points"] for item in EVALUATION_CRITERIA) == 10


validate_contract()
