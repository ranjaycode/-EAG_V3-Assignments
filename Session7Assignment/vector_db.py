import sys
import os

# Limit all math/deep learning libraries to a single thread to prevent deadlocks in subprocesses/threads
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Force 100% offline mode for Hugging Face and Transformers to bypass all network calls
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import logging
from pathlib import Path
import numpy as np

# Suppress loggers
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

STATE_DIR = Path(__file__).parent / "state"
INDEX_PATH = STATE_DIR / "faiss_index.bin"
METADATA_PATH = STATE_DIR / "faiss_metadata.json"

_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # Force CPU execution for stability in background processes
        _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _model

def chunk_markdown(text: str, filename: str) -> list[dict]:
    """Simple section-based chunking for markdown files."""
    sections = text.split("\n## ")
    chunks = []
    
    # First section (might have # Title and abstract)
    first = sections[0].strip()
    if first:
        chunks.append({
            "filename": filename,
            "section": "Introduction/Abstract",
            "content": first
        })
        
    for sec in sections[1:]:
        lines = sec.split("\n")
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if body:
            chunks.append({
                "filename": filename,
                "section": title,
                "content": f"## {title}\n{body}"
            })
            
    return chunks

def index_files(paths: list[Path]) -> int:
    """Index list of markdown files, compute embeddings, and persist to FAISS index."""
    import faiss
    
    STATE_DIR.mkdir(exist_ok=True)
    
    all_chunks = []
    for path in paths:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(content, path.name)
        all_chunks.extend(chunks)
        
    if not all_chunks:
        return 0
        
    # Get model and encode content
    model = _get_model()
    texts = [c["content"] for c in all_chunks]
    embeddings = model.encode(texts, convert_to_numpy=True)
    
    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension) # Inner product (Cosine similarity on normalized embeddings)
    
    # Normalize embeddings
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    
    # Save index and metadata
    faiss.write_index(index, str(INDEX_PATH))
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        
    return len(all_chunks)

def query_index(query: str, limit: int = 3) -> list[dict]:
    """Query the persisted FAISS index and return top matching chunks."""
    import faiss
    
    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        return []
        
    # Load index and metadata
    index = faiss.read_index(str(INDEX_PATH))
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    # Embed query
    model = _get_model()
    query_emb = model.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(query_emb)
    
    # Search
    distances, indices = index.search(query_emb, limit)
    
    results = []
    for idx, dist in zip(indices[0], distances[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        item = metadata[idx].copy()
        item["score"] = float(dist)
        results.append(item)
        
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vector_db.py <command> [args...]")
        print("Commands: index <file_or_dir> | query <query_text> [limit]")
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "index":
        path_str = sys.argv[2]
        p = Path(path_str)
        if p.is_dir():
            paths = list(p.glob("**/*.md"))
        else:
            paths = [p]
        total = index_files(paths)
        # Output clean JSON to stdout for parent process parsing
        print(json.dumps({"ok": True, "chunks_indexed": total}))
        
    elif cmd == "query":
        query_text = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        res = query_index(query_text, limit)
        # Output clean JSON array to stdout for parent process parsing
        print(json.dumps(res))
        
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

