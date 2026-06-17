import httpx
import time

queries = [
    "Go to amazon.in, search for 'gaming laptops under 80000', filter by brand 'ASUS' or 'HP' using the sidebar, sort the results by Customer Review, visit the top 3 product pages to extract their processor type, RAM size, and price, and output a comparison table.",
    "Compare the pricing pages of Cursor, Windsurf, and GitHub Copilot. Visit each pricing page, extract their Free plan limitations and Pro plan costs, and build a comparison table highlighting key differences.",
    "Go to huggingface.co/models, filter by 'text-generation' pipeline tag, filter by 'transformers' library, sort the models by 'likes', visit the details pages of the top 3 models, and output a comparison table of their name, likes, downloads, and author.",
    "Open the local shape-drawing canvas application, click inside the red circle to select it, change its fill color to green using the color picker tool, take a screenshot, and verify the color changed."
]

for idx, q in enumerate(queries, 1):
    print(f"\n--- Starting Query {idx}/4 ---")
    try:
        r = httpx.post("http://127.0.0.1:8118/api/run", json={"query": q}, timeout=10)
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
            
    except Exception as e:
        print(f"Error in execution of Query {idx}: {e}")

print("\nAll 4 queries completed sequentially!")
