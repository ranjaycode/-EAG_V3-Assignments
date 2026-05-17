from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from solver import LogiSolver
from puzzles import PUZZLES

# Load environment variables
load_dotenv()

app = FastAPI(title="LogiSolve API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global solver instance (or we can create per session)
# For simplicity, we'll keep a reference to active solvers
solvers = {}

class SolveRequest(BaseModel):
    problem: str
    session_id: str = "default"

class FollowUpRequest(BaseModel):
    question: str
    session_id: str = "default"

@app.get("/puzzles")
async def get_puzzles():
    return [{"id": pid, **data} for pid, data in PUZZLES.items()]

@app.post("/solve")
async def solve(request: SolveRequest):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key not found in environment.")
    
    solver = LogiSolver(api_key=api_key, silent=True)
    solvers[request.session_id] = solver
    
    try:
        response = solver.solve(request.problem)
        return {"solution": response, "session_id": request.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/follow-up")
async def follow_up(request: FollowUpRequest):
    if request.session_id not in solvers:
        raise HTTPException(status_code=404, detail="Session not found. Please solve a problem first.")
    
    solver = solvers[request.session_id]
    try:
        response = solver.follow_up(request.question)
        return {"solution": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
