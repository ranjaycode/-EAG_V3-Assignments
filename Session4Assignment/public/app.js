const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}`;
const socket = new WebSocket(wsUrl);

const waitingState = document.getElementById('waiting-state');
const dashboardContent = document.getElementById('dashboard-content');
const displayTicker = document.getElementById('display-ticker');
const displayPrice = document.getElementById('display-price');
const displayTrend = document.getElementById('display-trend');
const displaySummary = document.getElementById('display-summary');
const agentLogs = document.getElementById('agent-logs');
const newsTimeline = document.getElementById('news-timeline');
const reportsList = document.getElementById('reports-list');
const aiPrompt = document.getElementById('ai-prompt');
const researchBtn = document.getElementById('research-btn');
const reportSearch = document.getElementById('report-search');

let priceChart = null;
let allReports = [];

socket.onopen = () => console.log('Connected to WebSocket');

socket.onmessage = (event) => {
    try {
        const message = JSON.parse(event.data);
        if (message.type === 'update') {
            updateDashboard(message.data);
            refreshHistory(); // Refresh list when new data arrives
            resetResearchButton(); // Reset button when agent completes
        }
    } catch (err) {}
};

window.addEventListener('DOMContentLoaded', () => {
    initPersistence();
    setupFilters();
    
    researchBtn.addEventListener('click', () => {
        const prompt = aiPrompt.value.trim();
        if (prompt) {
            triggerResearch(prompt);
        } else {
            alert("Please enter a research prompt (e.g. 'Analyze Tata Motors...')");
        }
    });
});

async function triggerResearch(prompt) {
    researchBtn.innerHTML = '<span class="loader"></span> Agent Thinking...';
    researchBtn.disabled = true;
    researchBtn.style.opacity = "0.7";
    agentLogs.innerHTML = '<span><span class="prompt-cursor">></span> Initiating Agentic Workflow...</span>';

    try {
        const res = await fetch(`/api/research`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        const result = await res.json();
        if (!result.success) {
            alert("Research failed to start: " + result.error);
            resetResearchButton();
        }
        // Button will be reset by the WebSocket 'update' message
    } catch (err) {
        alert("Error connecting to server");
        resetResearchButton();
    }
}

function resetResearchButton() {
    researchBtn.innerHTML = "Execute AI Agent 🚀";
    researchBtn.disabled = false;
    researchBtn.style.opacity = "1";
}

async function initPersistence() {
    try {
        const res = await fetch('/api/latest');
        const data = await res.json();
        if (data && data.ticker) updateDashboard(data);
        refreshHistory();
    } catch (err) {}
}

function updateDashboard(data) {
    if (!data) return;
    waitingState.classList.add('hidden');
    dashboardContent.classList.remove('hidden');

    const ticker = data.ticker || data.symbol || '';
    const isIndian = ticker.endsWith('.NS') || ticker.endsWith('.BO') || ticker === 'TTM' || ticker === 'AXISBANK';
    const currency = isIndian ? '₹' : '$';

    displayTicker.textContent = ticker || 'N/A';
    displayPrice.textContent = `${currency}${parseFloat(data.price || 0).toFixed(2)}`;
    displayTrend.textContent = (data.trend || 'neutral').toUpperCase();
    displayTrend.className = `trend-badge ${data.trend || 'neutral'}`;
    displaySummary.innerHTML = formatSummary(data.summary || data.analysis || '');
    
    // Render Logs
    if (data.logs && data.logs.length > 0) {
        console.group(`Agent Execution Logs: ${data.ticker}`);
        agentLogs.innerHTML = '';
        data.logs.forEach(logLine => {
            console.log(`[Agent] ${logLine}`);
            const span = document.createElement('span');
            span.innerHTML = `<span class="prompt-cursor">></span> ${logLine}`;
            agentLogs.appendChild(span);
        });
        console.groupEnd();
        agentLogs.scrollTop = agentLogs.scrollHeight;
    }

    // Handle News Timeline
    renderNews(data.news || data.recentNews || []);

    updateChart(data.ticker || data.symbol, data.price);
}

function renderNews(newsItems) {
    newsTimeline.innerHTML = '';
    if (!newsItems || newsItems.length === 0) {
        newsTimeline.innerHTML = '<p class="text-muted">No news updates for this period.</p>';
        return;
    }

    newsItems.forEach(item => {
        const div = document.createElement('div');
        div.className = 'timeline-item';
        div.innerHTML = `
            <span class="date">Latest Update</span>
            <p>${item}</p>
        `;
        newsTimeline.appendChild(div);
    });
}

function updateChart(ticker, currentPrice) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    const labels = ['6d ago', '5d ago', '4d ago', '3d ago', '2d ago', 'Yesterday', 'Today'];
    
    const base = parseFloat(currentPrice);
    const dataPoints = [
        base * 0.985, base * 0.992, base * 0.988, base * 0.995, base * 1.002, base * 0.998, base
    ];

    if (priceChart) priceChart.destroy();

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${ticker} Price Trend`,
                data: dataPoints,
                borderColor: '#00f5d4',
                backgroundColor: 'rgba(0, 245, 212, 0.1)',
                fill: true,
                tension: 0.4,
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: '#9d4edd'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#adb5bd' } },
                x: { grid: { display: false }, ticks: { color: '#adb5bd' } }
            }
        }
    });
}

async function refreshHistory() {
    try {
        const res = await fetch('/api/history');
        allReports = await res.json();
        renderReports(allReports);
    } catch (err) {
        console.warn("Could not load history");
    }
}

function renderReports(reports) {
    reportsList.innerHTML = '';
    reports.slice().reverse().forEach(r => {
        const li = document.createElement('li');
        li.dataset.id = r.id;
        const ticker = r.symbol || r.ticker || '';
        const isIndian = ticker.endsWith('.NS') || ticker.endsWith('.BO') || ticker === 'TTM';
        const currency = isIndian ? '₹' : '$';

        li.innerHTML = `
            <div class="report-header">
                <div>
                    <strong>${ticker}</strong>
                    <span class="report-date">${new Date(r.timestamp || Date.now()).toLocaleDateString()}</span>
                </div>
                <span class="trend-badge ${r.trend || 'neutral'}">${(r.trend || 'neutral').toUpperCase()}</span>
            </div>
            <p class="report-summary-text">${(r.analysis || r.summary || '').substring(0, 100)}...</p>
            <div class="report-meta">
                <span>Price: ${currency}${parseFloat(r.price || 0).toFixed(2)}</span>
            </div>
        `;
        li.addEventListener('click', () => {
            updateDashboard({
                trend: report.trend,
                news: report.recentNews || report.news
            });
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
        reportsList.appendChild(li);
    });
}

function setupFilters() {
    reportSearch.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allReports.filter(r => 
            (r.symbol || r.ticker || '').toLowerCase().includes(term) || 
            (r.analysis || r.summary || '').toLowerCase().includes(term)
        );
        renderReports(filtered);
    });

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const filter = btn.dataset.filter;
            const filtered = filter === 'all' 
                ? allReports 
                : allReports.filter(r => r.trend === filter);
            renderReports(filtered);
        });
    });
}

function formatSummary(text) {
    if (!text) return '';
    return text.replace(/\n\n/g, '</p><p>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}
