"""Load the selected class SLM and reproduce its character generation for Parts 2–4."""
from pathlib import Path
import hashlib
import torch
from a7.slm.class_model import TinyTransformerLM

DEFAULT_CHECKPOINT = Path(__file__).parent / 'checkpoints' / 'selected_baseline.pt'


def state_hash(model):
    digest = hashlib.sha256()
    for name, tensor in model.state_dict().items():
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def load_selected(path=DEFAULT_CHECKPOINT):
    """Return a fresh copy of the original checkpoint and its character vocabulary."""
    saved = torch.load(path, map_location='cpu', weights_only=True)
    model = TinyTransformerLM(vocab_size=len(saved['vocab']), **saved['config'])
    model.load_state_dict(saved['model_state'])
    model.eval()
    return model, saved['vocab']


@torch.no_grad()
def generate(model, vocab, prompt, max_new_tokens=100, temperature=.7, seed=42):
    """Class generation loop with explicit vocabulary, device and repeatable seed.

    Returns the original prompt plus continuation, as in the class notebook.
    Unknown characters raise an error; callers must document any normalization.
    Only the last model.context_length characters are visible at each step.
    """
    if not prompt or temperature <= 0 or max_new_tokens < 0:
        raise ValueError('Use a nonempty prompt, positive temperature and nonnegative token limit.')
    stoi = {ch: i for i, ch in enumerate(vocab)}
    unknown = sorted(set(prompt) - set(stoi))
    if unknown:
        raise ValueError(f'Characters absent from training vocabulary: {unknown!r}')
    device = next(model.parameters()).device
    if device.type != 'cpu':
        raise ValueError('Use CPU for the shared reproducible generation condition.')
    was_training = model.training
    model.eval()
    try:
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            ids = torch.tensor([[stoi[ch] for ch in prompt]], dtype=torch.long, device=device)
            for _ in range(max_new_tokens):
                logits = model(ids[:, -model.context_length:])[:, -1, :] / temperature
                next_id = torch.multinomial(torch.softmax(logits, dim=-1), num_samples=1)
                ids = torch.cat([ids, next_id], dim=1)
            return ''.join(vocab[i] for i in ids[0].tolist())
    finally:
        model.train(was_training)
