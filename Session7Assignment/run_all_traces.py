import subprocess
import os
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
TRACES_DIR = BASE_DIR / "traces"
TRACES_DIR.mkdir(exist_ok=True)

# Define queries to run
QUERIES = [
    # Base Queries A-H
    {"id": "A", "args": ["--query-id", "A"]},
    {"id": "B", "args": ["--query-id", "B"]},
    {"id": "C1", "args": ["--clear-memory", "--query-id", "C1"]},
    {"id": "C2", "args": ["--query-id", "C2"]},
    {"id": "D", "args": ["--query-id", "D"]},
    {"id": "E", "args": ["--query-id", "E"]},
    {"id": "F1", "args": ["--query-id", "F1"]},
    {"id": "F2", "args": ["--query-id", "F2"]},
    {"id": "G", "args": ["--query-id", "G"]},
    {"id": "H", "args": ["--query-id", "H"]},
    
    # Custom RAG Queries (RAG mode vs Closed-book mode)
    {"id": "RAG_A_enabled", "args": ["--query-id", "RAG_A"]},
    {"id": "RAG_A_disabled", "args": ["--query-id", "RAG_A", "--disable-rag"]},
    
    {"id": "RAG_B_enabled", "args": ["--query-id", "RAG_B"]},
    {"id": "RAG_B_disabled", "args": ["--query-id", "RAG_B", "--disable-rag"]},
    
    {"id": "RAG_C_enabled", "args": ["--query-id", "RAG_C"]},
    {"id": "RAG_C_disabled", "args": ["--query-id", "RAG_C", "--disable-rag"]},
    
    {"id": "RAG_D_enabled", "args": ["--query-id", "RAG_D"]},
    {"id": "RAG_D_disabled", "args": ["--query-id", "RAG_D", "--disable-rag"]},
    
    {"id": "RAG_E_enabled", "args": ["--query-id", "RAG_E"]},
    {"id": "RAG_E_disabled", "args": ["--query-id", "RAG_E", "--disable-rag"]},
]

def run_one(q):
    print(f"Running {q['id']} with args {q['args']}...", flush=True)
    uv_path = shutil.which("uv") or "uv"
    cmd = [uv_path, "run", "python", "-u", "agent7.py"] + q["args"]
    
    # Run with unbuffered environment variables
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    res = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        errors="replace"
    )
    
    # Save trace file
    out_file = TRACES_DIR / f"trace_{q['id']}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"=== QUERY {q['id']} ===\n")
        f.write(f"Command: {' '.join(cmd)}\n")
        f.write(f"Exit Code: {res.returncode}\n")
        f.write("-" * 60 + "\n")
        f.write(res.stdout)
        if res.stderr:
            f.write("\n" + "=" * 20 + " STDERR " + "=" * 20 + "\n")
            f.write(res.stderr)
            
    print(f"Completed {q['id']}. Saved to {out_file.name}", flush=True)

def main():
    print("Starting collection of all 18 traces...", flush=True)
    for q in QUERIES:
        try:
            run_one(q)
        except Exception as e:
            print(f"Error running {q['id']}: {e}", flush=True)
    print("Trace collection complete!", flush=True)

if __name__ == "__main__":
    main()
