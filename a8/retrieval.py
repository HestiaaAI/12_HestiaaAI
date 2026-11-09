"""Shared A8 sentence-transformer embeddings and exact cosine retrieval."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from time import perf_counter
import numpy as np


MODELS = {
    'small': {'model_id': 'sentence-transformers/all-MiniLM-L6-v2',
              'dimension': 384, 'license': 'Apache-2.0', 'max_seq_length': 256, 'query_prefix': ''},
    'medium': {'model_id': 'sentence-transformers/all-mpnet-base-v2',
               'dimension': 768, 'license': 'Apache-2.0', 'max_seq_length': 384, 'query_prefix': ''},
    'large': {'model_id': 'BAAI/bge-large-en-v1.5',
              'dimension': 1024, 'license': 'MIT', 'max_seq_length': 512,
              'query_prefix': 'Represent this sentence for searching relevant passages: '},
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_encoder(size='small', device='cpu', revision=None):
    """Resolve an immutable HF revision. No model weights are stored in the repo."""
    from huggingface_hub import model_info
    from sentence_transformers import SentenceTransformer
    spec = MODELS[size]
    if not re.fullmatch(r'[0-9a-f]{40}', revision or ''):
        revision = model_info(spec['model_id'], revision=revision).sha
    encoder = SentenceTransformer(spec['model_id'], revision=revision, device=device)
    encoder.max_seq_length = spec['max_seq_length']
    if encoder.get_sentence_embedding_dimension() != spec['dimension']:
        raise ValueError('Loaded embedding dimension does not match registry')
    encoder.a8_metadata = {**spec, 'revision': revision, 'device': device,
                           'normalization': 'l2', 'dtype': 'float32'}
    return encoder


def token_lengths(texts, encoder):
    if not hasattr(encoder, 'tokenizer'):
        return []  # Deterministic test encoders do not tokenize.
    return [len(ids) for ids in encoder.tokenizer(
        texts, truncation=False, padding=False)['input_ids']]


def encode_texts(texts, encoder):
    lengths = token_lengths(texts, encoder)
    if lengths and max(lengths) > encoder.max_seq_length:
        raise ValueError(f'Text exceeds embedding context: {max(lengths)} > {encoder.max_seq_length}; '
                         'agree a corpus/model policy before running, do not silently truncate')
    vectors = np.asarray(encoder.encode(texts, convert_to_numpy=True,
                                       show_progress_bar=False), dtype=np.float32)
    if vectors.ndim != 2 or len(vectors) != len(texts) or vectors.shape[1] == 0:
        raise ValueError('Expected one nonempty embedding vector per input')
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.isfinite(vectors).all() or not np.isfinite(norms).all() or (norms == 0).any():
        raise ValueError('Embeddings must be finite and nonzero')
    return vectors / norms


@dataclass
class RetrievalIndex:
    chunks: list[dict]
    vectors: np.ndarray
    manifest: dict


def build_index(chunks, encoder, model_metadata):
    if not chunks:
        raise ValueError('Cannot index empty chunks')
    records = [asdict(c) if not isinstance(c, dict) else dict(c) for c in chunks]
    records = json.loads(json.dumps(records))  # Canonical JSON-safe paragraph ID lists.
    if len({c['id'] for c in records}) != len(records) or any(not c['text'].strip() for c in records):
        raise ValueError('Chunk IDs must be unique and texts nonempty')
    vectors = encode_texts([c['text'] for c in records], encoder)
    if model_metadata.get('dimension', vectors.shape[1]) != vectors.shape[1]:
        raise ValueError('Embedding dimensions do not match model metadata')
    manifest = {**model_metadata, 'dimension': int(vectors.shape[1]),
                'chunk_count': len(records), 'chunks_sha256': fingerprint(records),
                'vectors_sha256': hashlib.sha256(vectors.tobytes()).hexdigest()}
    return RetrievalIndex(records, vectors, manifest)


def synchronize(encoder):
    device = str(getattr(encoder, 'device', 'cpu'))
    if device.startswith(('cuda', 'mps')):
        import torch
        if device.startswith('cuda'):
            torch.cuda.synchronize()
        else:
            torch.mps.synchronize()


def search(index, query, encoder, top_k=3, timings=None):
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Query must not be empty')
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError('top_k must be a positive integer')
    metadata = getattr(encoder, 'a8_metadata', None)
    if metadata and any(index.manifest.get(k) != v for k, v in metadata.items()):
        raise ValueError('Query encoder does not match index model/settings')
    synchronize(encoder)
    start = perf_counter()
    vector = encode_texts([index.manifest.get('query_prefix', '') + query], encoder)[0]
    synchronize(encoder)
    embedded = perf_counter()
    if index.vectors.shape[1] != len(vector):
        raise ValueError('Query/index dimension mismatch')
    scores = index.vectors @ vector
    order = np.argsort(-scores, kind='stable')[:top_k]
    if timings is not None:
        timings.update(query_embedding_ms=(embedded-start)*1000,
                       similarity_search_ms=(perf_counter()-embedded)*1000)
    return [{'rank': rank, 'chunk_id': index.chunks[i]['id'],
             **{k: v for k, v in index.chunks[i].items() if k != 'id'},
             'score': float(scores[i])} for rank, i in enumerate(order, 1)]


def save_index(index, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(directory / 'vectors.npz', vectors=index.vectors)
    (directory / 'chunks.json').write_text(json.dumps(index.chunks, indent=2), encoding='utf-8')
    (directory / 'manifest.json').write_text(json.dumps(index.manifest, indent=2), encoding='utf-8')


def load_index(directory, expected_manifest):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if any(manifest.get(k) != v for k, v in expected_manifest.items()):
        raise ValueError('Index manifest does not match expected inputs/settings')
    chunks = json.loads((directory / 'chunks.json').read_text(encoding='utf-8'))
    with np.load(directory / 'vectors.npz', allow_pickle=False) as data:
        vectors = data['vectors']
    if (fingerprint(chunks) != manifest['chunks_sha256'] or
            hashlib.sha256(vectors.tobytes()).hexdigest() != manifest['vectors_sha256'] or
            vectors.shape != (len(chunks), manifest['dimension']) or
            len(chunks) != manifest['chunk_count']):
        raise ValueError('Index artifacts are corrupt or misaligned')
    return RetrievalIndex(chunks, vectors, manifest)


def score_retrieval(hits, query_record):
    """Source diagnostics and exact evidence coverage, not subjective quality."""
    expected = set(query_record['supporting_paragraph_ids'])
    retrieved = {p for h in hits for p in h['paragraph_ids']}
    first = next((h['rank'] for h in hits if expected.intersection(h['paragraph_ids'])), None)
    normalize = lambda s: re.sub(r'\s+', ' ', s).strip().casefold()
    texts = [normalize(h['text']) for h in hits]
    quotes = query_record['supporting_quotes']
    covered = [any(normalize(q) in t for t in texts) for q in quotes]
    return {'source_recall_at_k': len(expected & retrieved) / len(expected) if expected else None,
            'source_reciprocal_rank': 1 / first if first else 0.,
            'evidence_quote_coverage': sum(covered) / len(covered) if covered else None,
            'evidence_quotes_found': covered}
