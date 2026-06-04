import os
import json
import uuid
import time
import glob
import sys
import threading
import asyncio
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8118
sessions_running = {}  # sid -> boolean

class DashboardHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Allow CORS for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "OK")
        self.end_headers()

    def do_GET(self):
        # Redirect api requests
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            except Exception as e:
                self.wfile.write(f"Error loading index.html: {e}".encode("utf-8"))
            return

        if self.path == "/api/sessions":
            self.handle_list_sessions()
            return

        if self.path.startswith("/api/sessions/"):
            sid = self.path.split("/")[-1]
            self.handle_get_session(sid)
            return

        # Fallback to default handler for static resources (CSS, icons)
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/run":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            query = data.get("query", "")
            if not query:
                self.send_error_json("Query is empty")
                return
            
            # Generate a fresh session ID
            sid = f"s8-{uuid.uuid4().hex[:8]}"
            
            # Run in a background thread
            t = threading.Thread(target=run_flow_thread, args=(query, sid))
            t.daemon = True
            sessions_running[sid] = True
            t.start()

            self.send_json(200, {"session_id": sid, "status": "started"})
            return

        if self.path == "/api/sessions/clear":
            import shutil
            sessions_dir = os.path.join("state", "sessions")
            if os.path.exists(sessions_dir):
                for item in os.listdir(sessions_dir):
                    item_path = os.path.join(sessions_dir, item)
                    try:
                        if os.path.isdir(item_path):
                            # Mark as soft deleted first
                            try:
                                with open(os.path.join(item_path, ".deleted"), "w") as df:
                                    df.write("1")
                            except Exception:
                                pass
                            shutil.rmtree(item_path, ignore_errors=True)
                        else:
                            os.remove(item_path)
                    except Exception as e:
                        print(f"Error clearing {item_path}: {e}")
            self.send_json(200, {"status": "cleared"})
            return

    def send_json(self, status, obj):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))

    def send_error_json(self, message):
        self.send_json(400, {"error": message})

    def handle_list_sessions(self):
        sessions_dir = os.path.join("state", "sessions")
        if not os.path.exists(sessions_dir):
            self.send_json(200, {"sessions": []})
            return
        
        session_list = []
        for sid in os.listdir(sessions_dir):
            path = os.path.join(sessions_dir, sid)
            if not os.path.isdir(path):
                continue
            if os.path.exists(os.path.join(path, ".deleted")):
                continue
            
            query = ""
            query_file = os.path.join(path, "query.txt")
            if os.path.exists(query_file):
                try:
                    with open(query_file, "r", encoding="utf-8") as f:
                        query = f.read().strip()
                except Exception:
                    pass
            
            # Parse nodes to find counts and states
            nodes_dir = os.path.join(path, "nodes")
            node_count = 0
            running = sessions_running.get(sid, False)
            
            if os.path.exists(nodes_dir):
                node_files = glob.glob(os.path.join(nodes_dir, "n_*.json"))
                node_count = len(node_files)
                for nf_path in node_files:
                    try:
                        with open(nf_path, "r", encoding="utf-8") as nf:
                            ndata = json.load(nf)
                            if ndata.get("status") == "running":
                                running = True
                    except Exception:
                        pass
            
            # Time of modification
            mtime = os.path.getmtime(path)
            
            session_list.append({
                "id": sid,
                "query": query,
                "node_count": node_count,
                "running": running,
                "modified": mtime
            })
            
        self.send_json(200, {"sessions": session_list})

    def handle_get_session(self, sid):
        sessions_dir = os.path.join("state", "sessions")
        path = os.path.join(sessions_dir, sid)
        if not os.path.exists(path) or not os.path.isdir(path) or os.path.exists(os.path.join(path, ".deleted")):
            self.send_json(404, {"error": "Session not found"})
            return
        
        query = ""
        query_file = os.path.join(path, "query.txt")
        if os.path.exists(query_file):
            try:
                with open(query_file, "r", encoding="utf-8") as f:
                    query = f.read().strip()
            except Exception:
                pass
        
        nodes = []
        nodes_dir = os.path.join(path, "nodes")
        if os.path.exists(nodes_dir):
            node_files = glob.glob(os.path.join(nodes_dir, "n_*.json"))
            # Sort node files by numeric node suffix so they appear in sequence
            node_files.sort(key=lambda x: int(os.path.basename(x).split(".")[0].split("_")[1]) if "_" in x else 0)
            for nf_path in node_files:
                try:
                    with open(nf_path, "r", encoding="utf-8") as nf:
                        nodes.append(json.load(nf))
                except Exception as e:
                    print("Error loading node file:", nf_path, e)
                    
        self.send_json(200, {
            "session_id": sid,
            "query": query,
            "nodes": nodes
        })

def run_flow_thread(query, sid):
    # Set encoding environment variables inside the thread
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONUNBUFFERED"] = "1"
    
    try:
        from flow import Executor
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(Executor().run(query, session_id=sid))
        loop.close()
    except Exception as e:
        print(f"Error executing flow in dashboard thread: {e}")
    finally:
        sessions_running[sid] = False

def main():
    # Force output encoding for Windows terminal
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    # Create states folder if it doesn't exist
    os.makedirs(os.path.join("state", "sessions"), exist_ok=True)
    
    server = HTTPServer(("127.0.0.1", PORT), DashboardHandler)
    print(f"============================================================")
    print(f"Session 8 Orchestrator Dashboard starting...")
    print(f"URL: http://localhost:{PORT}")
    print(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        server.server_close()

if __name__ == "__main__":
    main()
