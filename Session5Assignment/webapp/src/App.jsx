import React, { useState, useEffect, useRef } from 'react';
import { 
  Brain, 
  ChevronRight, 
  Send, 
  Activity, 
  Terminal, 
  HelpCircle, 
  RefreshCcw,
  ShieldCheck,
  Zap,
  Layout,
  MessageSquare
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function App() {
  const [puzzles, setPuzzles] = useState([]);
  const [activePuzzle, setActivePuzzle] = useState(null);
  const [reasoningSteps, setReasoningSteps] = useState([]);
  const [customProblem, setCustomProblem] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(`session_${Math.random().toString(36).substr(2, 9)}`);
  const [error, setError] = useState(null);

  const endOfLogRef = useRef(null);

  useEffect(() => {
    fetchPuzzles();
  }, []);

  useEffect(() => {
    endOfLogRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [reasoningSteps]);

  const fetchPuzzles = async () => {
    try {
      const res = await fetch('http://localhost:8000/puzzles');
      const data = await res.json();
      setPuzzles(data);
      if (data.length > 0) setActivePuzzle(data[0]);
    } catch (err) {
      console.error("Failed to fetch puzzles", err);
    }
  };

  const parseReasoningSteps = (text) => {
    // Basic parser for the structured output
    const steps = [];
    const parts = text.split(/STEP \d+:/);
    
    // First part is usually REASONING_CHAIN header
    parts.slice(1).forEach((part, index) => {
      const typeMatch = part.match(/\[(.*?)\]/);
      const observationMatch = part.match(/Observation: ([\s\S]*?)(?=Deduction:|$)/);
      const deductionMatch = part.match(/Deduction: ([\s\S]*?)(?=Confidence:|$)/);
      const confidenceMatch = part.match(/Confidence: ([\s\S]*?)(?=SELF_CHECK|STEP|FINAL_ANSWER|$)/);
      
      steps.push({
        id: index + 1,
        type: typeMatch ? typeMatch[1] : 'DEDUCTION',
        observation: observationMatch ? observationMatch[1].trim() : '',
        deduction: deductionMatch ? deductionMatch[1].trim() : '',
        confidence: confidenceMatch ? confidenceMatch[1].trim() : 'HIGH'
      });
    });

    const finalMatch = text.match(/FINAL_ANSWER:([\s\S]*)/);
    const solution = finalMatch ? finalMatch[1].trim() : null;

    return { steps, solution };
  };

  const handleSolve = async (problemText) => {
    setIsLoading(true);
    setReasoningSteps([]);
    setError(null);
    
    try {
      const res = await fetch('http://localhost:8000/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          problem: problemText || activePuzzle.problem,
          session_id: sessionId
        })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Solver failed to respond");
      
      if (data.solution && data.solution.startsWith("ERROR:")) {
        throw new Error(data.solution);
      }

      const parsed = parseReasoningSteps(data.solution);
      setReasoningSteps(parsed.steps);
      setActivePuzzle(prev => ({ ...prev, solution: parsed.solution }));
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFollowUp = async () => {
    if (!customProblem.trim()) return;
    
    const question = customProblem;
    setCustomProblem('');
    setIsLoading(true);
    
    try {
      const res = await fetch('http://localhost:8000/follow-up', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          session_id: sessionId
        })
      });
      
      const data = await res.json();
      const parsed = parseReasoningSteps(data.solution);
      setReasoningSteps(prev => [...prev, ...parsed.steps]);
      if (parsed.solution) {
        setActivePuzzle(prev => ({ ...prev, solution: parsed.solution }));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <Brain className="text-primary" size={28} />
          <span className="logo-text">LogiSolve</span>
        </div>

        <div className="nav-section">
          <h3 className="section-title">Built-in Puzzles</h3>
          {puzzles.map(p => (
            <div 
              key={p.id}
              className={`puzzle-item ${activePuzzle?.id === p.id ? 'active' : ''}`}
              onClick={() => {
                setActivePuzzle(p);
                setReasoningSteps([]);
              }}
            >
              <span className="puzzle-name">{p.name}</span>
              <div className="puzzle-meta">
                <span className={`badge badge-${p.difficulty}`}>{p.difficulty}</span>
                <span>{p.category}</span>
              </div>
            </div>
          ))}
          
          <div 
            className={`puzzle-item ${activePuzzle?.id === 'custom' ? 'active' : ''}`}
            onClick={() => {
              setActivePuzzle({ id: 'custom', name: 'Custom Problem', problem: '', difficulty: 'variable' });
              setReasoningSteps([]);
            }}
          >
            <span className="puzzle-name">Custom Problem</span>
            <div className="puzzle-meta">
              <MessageSquare size={12} />
              <span>User defined</span>
            </div>
          </div>
        </div>

        <div className="sidebar-footer" style={{ marginTop: 'auto', paddingTop: '20px' }}>
          <div className="card-label">
            <ShieldCheck size={14} /> Security
          </div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
            Gemini/Claude API active via backend. All reasoning is performed on-cloud.
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="top-bar">
          <div className="status-ticker">
            <div className="status-dot"></div>
            <span>Reasoning Engine: Online</span>
            <span style={{ margin: '0 10px', color: 'var(--border)' }}>|</span>
            <Zap size={14} className="text-secondary" />
            <span>CoT v5.0 Active</span>
          </div>
          
          <div style={{ display: 'flex', gap: '12px' }}>
            <button 
              className="send-btn" 
              style={{ position: 'relative', width: 'auto', padding: '0 20px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)' }}
              onClick={() => {
                setSessionId(`session_${Math.random().toString(36).substr(2, 9)}`);
                setReasoningSteps([]);
              }}
            >
              <RefreshCcw size={16} style={{ marginRight: '8px' }} />
              Reset Session
            </button>
            <button 
              className="send-btn" 
              style={{ position: 'relative', width: 'auto', padding: '0 20px' }}
              onClick={() => handleSolve()}
              disabled={isLoading || !activePuzzle}
            >
              <Zap size={16} style={{ marginRight: '8px' }} />
              Solve Now
            </button>
          </div>
        </header>

        <div className="solver-view">
          {activePuzzle && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="problem-card"
            >
              <div className="card-label">
                <Terminal size={14} /> Problem Statement
              </div>
              {activePuzzle.id === 'custom' ? (
                <textarea 
                  className="chat-input"
                  style={{ background: 'transparent', border: 'none', padding: 0, height: '120px', resize: 'none' }}
                  placeholder="Paste your logic puzzle here..."
                  value={customProblem}
                  onChange={(e) => setCustomProblem(e.target.value)}
                />
              ) : (
                <p className="problem-text">{activePuzzle.problem}</p>
              )}
            </motion.div>
          )}

          <div className="reasoning-log">
            <AnimatePresence>
              {reasoningSteps.map((step) => (
                <motion.div 
                  key={step.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="step-card"
                >
                  <div className="step-header">
                    <span className="step-type">{step.type}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Step {step.id}</span>
                    <div style={{ marginLeft: 'auto', display: 'flex', gap: '4px' }}>
                      {[...Array(3)].map((_, i) => (
                        <div key={i} className="status-dot" style={{ width: '4px', height: '4px', background: step.confidence === 'HIGH' ? '#4ade80' : '#facc15', boxShadow: 'none' }}></div>
                      ))}
                    </div>
                  </div>
                  <div className="step-content">
                    <p style={{ marginBottom: '8px' }}><b>Observation:</b> {step.observation}</p>
                    <p><b>Deduction:</b> {step.deduction}</p>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {activePuzzle?.solution && !isLoading && (
              <motion.div 
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="final-answer"
              >
                <div className="card-label" style={{ color: '#4ade80' }}>
                  <ShieldCheck size={14} /> Final Verification Complete
                </div>
                <div style={{ fontSize: '1.2rem', color: 'white', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                  {activePuzzle.solution.replace('Solution:', '').replace('FINAL_ANSWER:', '').trim()}
                </div>
              </motion.div>
            )}

            {isLoading && (
              <div className="step-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px' }}>
                <div className="status-ticker">
                  <Activity className="animate-pulse" size={20} />
                  <span className="animate-pulse">Claude/Gemini is processing reasoning chains...</span>
                </div>
              </div>
            )}
            
            {error && (
              <div className="step-card" style={{ borderColor: 'var(--accent)', background: 'rgba(244, 63, 94, 0.05)' }}>
                <div className="card-label" style={{ color: 'var(--accent)' }}>
                  <HelpCircle size={14} /> Solver Error
                </div>
                <p style={{ color: 'var(--text-main)' }}>{error}</p>
              </div>
            )}
            
            <div ref={endOfLogRef} />
          </div>
        </div>

        {/* Custom Input Area for Follow-ups */}
        <div className="input-area">
          <div className="input-container">
            <input 
              type="text" 
              className="chat-input"
              placeholder={activePuzzle?.solution ? "Ask a follow-up question..." : "Enter problem context or click Solve..."}
              value={customProblem}
              onChange={(e) => setCustomProblem(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (activePuzzle?.id === 'custom' && !activePuzzle.solution ? handleSolve(customProblem) : handleFollowUp())}
            />
            <button 
              className="send-btn"
              onClick={() => activePuzzle?.id === 'custom' && !activePuzzle.solution ? handleSolve(customProblem) : handleFollowUp()}
              disabled={isLoading}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
