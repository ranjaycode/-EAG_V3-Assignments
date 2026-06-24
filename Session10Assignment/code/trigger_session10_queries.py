import httpx
import time

queries = [
    "Say hello in one short sentence.",
    "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory.",
    "Find the populations of Paris, London, and Berlin. Use the Coder skill to calculate the difference between the sum of Paris and Berlin populations and the population of London, and output the final value.",
    "List files in directory '/nonexistent' and let me know what you found.",
    "Analyze the sentiment of this text: 'I absolutely love this new automated orchestrator! It is incredibly fast and works perfectly every time.'",
    "Check the current system state and report the active window and mouse position.",
    "Calculate 15 * 6 using the Calculator app.",
    "Connect to VS Code on port 9222 and verify the editor container exists.",
    "Open the local shape-drawing canvas application, click inside the red circle to select it, change its fill color to green using the color picker tool, take a screenshot, and verify the color changed."
]

def main():
    # 1. Clear existing sessions first to ensure a clean slate
    print("Clearing dashboard session history...")
    try:
        r = httpx.post("http://127.0.0.1:8118/api/sessions/clear", timeout=10)
        print("Sessions cleared:", r.json())
    except Exception as e:
        print("Warning: failed to clear sessions:", e)

    # 2. Run all queries sequentially
    for idx, q in enumerate(queries, 1):
        print(f"\n--- Starting Query {idx}/{len(queries)} ---")
        print(f"Query: {q}")
        try:
            r = httpx.post("http://127.0.0.1:8118/api/run", json={"query": q}, timeout=15)
            if r.status_code != 200:
                print(f"Failed to submit: {r.status_code} - {r.text}")
                continue
            sid = r.json()["session_id"]
            print(f"Submitted successfully. Session ID: {sid}")
            
            # Wait 3 seconds for the backend thread to start and update state
            time.sleep(3)
            
            # Poll until complete
            start_time = time.time()
            while True:
                try:
                    r_status = httpx.get("http://127.0.0.1:8118/api/sessions", timeout=10)
                    sessions = r_status.json().get("sessions", [])
                    current = next((s for s in sessions if s['id'] == sid), None)
                    
                    # If the session is no longer marked as running, it means it's complete
                    if current and not current.get('running', False):
                        print(f"Query {idx} completed successfully! (Session: {sid}, Time taken: {int(time.time() - start_time) + 3}s)")
                        break
                    
                    print(f"Running... (Elapsed: {int(time.time() - start_time) + 3}s)")
                except Exception as e:
                    print(f"Error checking status: {e}")
                time.sleep(5)
                
            # Wait a few seconds between tasks for visual transition on dashboard
            time.sleep(4)
            
        except Exception as e:
            print(f"Error in execution of Query {idx}: {e}")

    print("\nAll 9 queries completed sequentially!")

if __name__ == "__main__":
    main()
