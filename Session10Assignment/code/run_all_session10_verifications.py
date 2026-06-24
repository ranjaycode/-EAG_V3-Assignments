import asyncio
import json
import time
import subprocess
import socket
import sys
from pathlib import Path

# Ensure code/ is in sys.path so we can import flow
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flow import Executor
from gateway import ensure_gateway

QUERIES = [
    {
        "name": "Base Task 1: Simple Hello (Orchestrator Validation)",
        "query": "Say hello in one short sentence.",
        "needs_vscode": False
    },
    {
        "name": "Base Task 2: Claude Shannon Data Retrieval (Wikipedia)",
        "query": "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory.",
        "needs_vscode": False
    },
    {
        "name": "Base Task 3: Parallel Fan-out & Sandbox Calculation",
        "query": "Find the populations of Paris, London, and Berlin. Use the Coder skill to calculate the difference between the sum of Paris and Berlin populations and the population of London, and output the final value.",
        "needs_vscode": False
    },
    {
        "name": "Base Task 4: Graceful Fail on Non-Existent Path",
        "query": "List files in directory '/nonexistent' and let me know what you found.",
        "needs_vscode": False
    },
    {
        "name": "Custom Task 5: Custom Sentiment Analyzer Skill",
        "query": "Analyze the sentiment of this text: 'I absolutely love this new automated orchestrator! It is incredibly fast and works perfectly every time.'",
        "needs_vscode": False
    },
    {
        "name": "Custom Task 6: Custom System Monitor Skill",
        "query": "Check the current system state and report the active window and mouse position.",
        "needs_vscode": False
    },
    {
        "name": "Computer-Use Task 1: Calculator Automation (Layer 2a Hotkeys)",
        "query": "Calculate 15 * 6 using the Calculator app.",
        "needs_vscode": False
    },
    {
        "name": "Computer-Use Task 2: VS Code Electron Connection (Layer 2c CDP)",
        "query": "Connect to VS Code on port 9222 and verify the editor container exists.",
        "needs_vscode": True
    },
    {
        "name": "Computer-Use Task 3: Canvas Vision Task (Layer 3 Coordinates)",
        "query": "Open the local shape-drawing canvas application, click inside the red circle to select it, change its fill color to green using the color picker tool, take a screenshot, and verify the color changed.",
        "needs_vscode": False
    }
]

def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0

async def main():
    print("======================================================================")
    print("STARTING SESSION 10 FULL AUTOMATED VERIFICATION SUITE")
    print("======================================================================")
    
    # 1. Ensure gateway is up on 8108
    print("[verify] Ensuring LLM Gateway is up on 8108...")
    ensure_gateway()
    
    # 2. Ensure dashboard is up on 8118 (or start it)
    dashboard_process = None
    if not is_port_open(8118):
        print("[verify] Dashboard/Canvas server is not running on 8118. Starting dashboard.py...")
        dashboard_process = subprocess.Popen(
            ["uv", "run", "python", "dashboard.py"],
            cwd=str(Path(__file__).resolve().parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Wait for port to open
        for _ in range(15):
            await asyncio.sleep(1.0)
            if is_port_open(8118):
                print("[verify] Dashboard/Canvas server is now up on 8118.")
                break
        else:
            print("[verify] WARNING: Dashboard/Canvas server failed to start on port 8118 within 15s.")
    else:
        print("[verify] Dashboard/Canvas server is already listening on 8118.")
        
    results = []
    
    # Focus the dashboard browser window to avoid recording code/terminal
    print("[verify] Focusing Orchestrator DAG dashboard window...")
    import pygetwindow as gw
    try:
        # Focus dashboard
        wins = gw.getWindowsWithTitle("Orchestrator DAG")
        if wins:
            wins[0].activate()
            wins[0].maximize()
            print("[verify] Dashboard window focused and maximized.")
        else:
            print("[verify] Could not find 'Orchestrator DAG' window. Please make sure http://localhost:8118 is open in browser.")
    except Exception as e:
        print("[verify] Error focusing window:", e)

    # Give a tiny buffer for window transition
    await asyncio.sleep(2.0)
    
    for idx, item in enumerate(QUERIES, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(QUERIES)}] RUNNING: {item['name']}")
        print(f"Query: {item['query']}")
        print(f"{'='*60}\n")
        
        vscode_proc = None
        if item["needs_vscode"]:
            print("[verify] Launching VS Code with remote debugging on port 9223...")
            user_data = str(Path(__file__).resolve().parent / "vscode-temp-user")
            exts_dir = str(Path(__file__).resolve().parent / "vscode-temp-exts")
            target_file = str(Path(__file__).resolve().parent / "usage.json")
            
            vscode_proc = subprocess.Popen([
                "code", 
                "--remote-debugging-port=9223", 
                f"--user-data-dir={user_data}", 
                f"--extensions-dir={exts_dir}",
                target_file
            ], shell=True)
            # Give it a moment to boot
            await asyncio.sleep(6.0)
            
        t0 = time.time()
        try:
            executor = Executor()
            ans = await executor.run(item["query"])
            duration = time.time() - t0
            print(f"\n[verify] SUCCESS: {item['name']} (took {duration:.2f}s)")
            results.append({
                "name": item["name"],
                "query": item["query"],
                "status": "PASSED",
                "answer": ans,
                "duration": duration,
                "error": None
            })
        except Exception as e:
            duration = time.time() - t0
            print(f"\n[verify] FAILED: {item['name']} (took {duration:.2f}s) - {e}")
            results.append({
                "name": item["name"],
                "query": item["query"],
                "status": "FAILED",
                "answer": None,
                "duration": duration,
                "error": str(e)
            })
            
        if vscode_proc or item["needs_vscode"]:
            print("[verify] Terminating VS Code processes...")
            subprocess.run("taskkill /f /im code.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await asyncio.sleep(2.0)
            
    # Clean up dashboard if we started it
    if dashboard_process:
        print("\n[verify] Stopping dashboard/canvas server...")
        dashboard_process.terminate()
        dashboard_process.wait()
        print("[verify] Dashboard/Canvas server stopped.")
        
    # Write report
    report_file = Path(__file__).resolve().parent / "session10_verification_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Session 10 Full Verification Report\n\n")
        f.write(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Execution Summary Table\n\n")
        f.write("| # | Task Name | Query | Status | Duration (s) |\n")
        f.write("|---|-----------|-------|--------|--------------|\n")
        for idx, r in enumerate(results, 1):
            f.write(f"| {idx} | {r['name']} | `{r['query']}` | **{r['status']}** | {r['duration']:.2f}s |\n")
            
        f.write("\n## Detailed Run Logs\n\n")
        for idx, r in enumerate(results, 1):
            f.write(f"### {idx}. {r['name']}\n")
            f.write(f"- **Query**: `{r['query']}`\n")
            f.write(f"- **Status**: **{r['status']}**\n")
            f.write(f"- **Duration**: {r['duration']:.2f} seconds\n")
            if r["status"] == "PASSED":
                f.write(f"- **Final Answer**:\n```\n{r['answer']}\n```\n")
            else:
                f.write(f"- **Error**:\n```\n{r['error']}\n```\n")
            f.write("\n---\n\n")
            
    print(f"\n[verify] Verification finished. Full report saved to {report_file}")

if __name__ == "__main__":
    asyncio.run(main())
