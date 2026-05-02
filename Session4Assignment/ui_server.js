import express from 'express';
import { WebSocketServer } from 'ws';
import path from 'path';
import fs from 'fs/promises';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(express.json());
app.use(express.static('public'));

const port = 3005;
let latestData = null; // Store the last report in memory

app.get('/api/latest', (req, res) => {
    res.json(latestData || { message: "No data yet" });
});

app.get('/api/history', async (req, res) => {
    try {
        const filePath = path.join(__dirname, "investment_research.json");
        const data = await fs.readFile(filePath, "utf-8");
        res.json(JSON.parse(data));
    } catch (err) {
        res.json([]);
    }
});

// Endpoint to trigger agent research with a full prompt
app.post('/api/research', (req, res) => {
    const { prompt } = req.body;
    console.log(`Triggering AI Agent with prompt: ${prompt}`);
    
    // Pass the full prompt as a single argument to agent.js
    const agentProcess = spawn('node', ['agent.js', prompt], {
        cwd: __dirname,
        stdio: 'inherit'
    });

    agentProcess.on('close', (code) => {
        console.log(`Agent process exited with code ${code}`);
    });

    res.json({ success: true, message: `AI Agent started processing your prompt.` });
});

const server = app.listen(port, () => {
    console.log(`UI Server running at http://localhost:${port}`);
});

const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
    console.log('New WebSocket connection established from UI.');
    ws.send(JSON.stringify({ type: 'connected', message: 'Connected to UI updates' }));
});

// Endpoint for MCP server to push data to UI
app.post('/api/push-ui', (req, res) => {
    const data = req.body;
    latestData = data; // Save for persistence
    console.log('Received UI push update:', data);

    // Broadcast to all connected websocket clients
    wss.clients.forEach((client) => {
        if (client.readyState === 1) { // WebSocket.OPEN
            client.send(JSON.stringify({ type: 'update', data }));
        }
    });

    res.json({ success: true, message: 'Data pushed to Prefab UI' });
});
