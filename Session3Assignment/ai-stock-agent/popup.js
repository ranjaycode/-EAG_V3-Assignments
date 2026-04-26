import { runAgent } from './agent.js';

let stockChartInstance = null;

document.getElementById("fullscreen-btn").addEventListener("click", () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("popup.html") });
});

document.getElementById("analyze").addEventListener("click", async () => {
  const query = document.getElementById("query").value;
  if (!query) return;

  const logsDiv = document.getElementById("logs");
  const resultDiv = document.getElementById("result");
  const chartContainer = document.getElementById("chart-container");

  logsDiv.innerHTML = "⏳ Initializing Agent...";
  resultDiv.innerHTML = "";
  chartContainer.style.display = "none";

  try {
    const { answer, stockData, symbol } = await runAgent(query, (logText) => {
      logsDiv.innerHTML += `<br/>${logText}`; // Append logs multiline
      console.log("[AI Agent]:", logText); // Safely push to Chrome Dev Console!
    });
    
    if (stockData && stockData["Time Series (Daily)"]) {
      renderChart(stockData["Time Series (Daily)"], symbol);
      chartContainer.style.display = "block";
    }

    let parsedAnswer;
    try {
      // Sometimes Gemini wraps JSON in markdown block even when told not to. Clean it up just in case.
      const cleaned = answer.replace(/```json/g, "").replace(/```/g, "").trim();
      parsedAnswer = JSON.parse(cleaned);
    } catch (e) {
      // Fallback if parsing fails
      parsedAnswer = { sentiment: "NEUTRAL", analysis: answer };
    }

    // Print massive, highly professional data structures to the dev console for the assignment!
    console.log("%c----- AI EXECUTION COMPLETE -----", "color: #0ea5e9; font-weight: bold; font-size: 14px;");
    console.log("%cSymbol Analyzed:", "color: #10b981", symbol);
    if (stockData && stockData["Time Series (Daily)"]) {
        console.log("%cStock Price Engine (Last 30 Days):", "color: #10b981");
        console.table(stockData["Time Series (Daily)"]);
    }
    console.log("%cExtracted Gemini AI Payload:", "color: #10b981");
    console.dir(parsedAnswer);

    // Update Badge
    const badge = document.getElementById("sentiment-badge");
    badge.style.display = "inline-block";
    badge.innerText = parsedAnswer.sentiment;
    badge.className = parsedAnswer.sentiment.toLowerCase();
    
    // Setup Voice
    const voiceBtn = document.getElementById("voice-btn");
    voiceBtn.style.display = "inline-block";
    voiceBtn.innerText = "🔊 Listen"; // Reset text safely
    
    voiceBtn.onclick = () => {
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        voiceBtn.innerText = "🔊 Listen";
      } else {
        const textToSpeak = parsedAnswer.analysis.replace(/[*#_]/g, '');
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        
        utterance.onend = () => {
          voiceBtn.innerText = "🔊 Listen";
        };
        
        window.speechSynthesis.speak(utterance);
        voiceBtn.innerText = "🔇 Stop";
      }
    };

    const formattedAnswer = parsedAnswer.analysis.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>');
    resultDiv.innerHTML = `<h4>🤖 Agent Analysis:</h4><p>${formattedAnswer}</p>`;
  } catch (error) {
    logsDiv.innerHTML = `<span style="color:#ef4444">❌ Error: ${error.message}</span>`;
  }
});

function renderChart(timeSeries, symbol) {
  const ctx = document.getElementById('stockChart').getContext('2d');
  
  if (stockChartInstance) {
    stockChartInstance.destroy();
  }

  const dates = Object.keys(timeSeries).slice(0, 30).reverse();
  const prices = dates.map(date => parseFloat(timeSeries[date]["4. close"]));

  stockChartInstance = new window.Chart(ctx, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [{
        label: `${symbol} Price`,
        data: prices,
        borderColor: '#38bdf8',
        backgroundColor: 'rgba(56, 189, 248, 0.2)',
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 3,
        pointBackgroundColor: '#0ea5e9'
      }]
    },
    options: {
      responsive: true,
      color: '#cbd5e1',
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#38bdf8',
          callbacks: {
            label: function(context) { return `$${context.parsed.y}`; }
          }
        }
      },
      scales: {
        x: { ticks: { color: '#64748b', maxTicksLimit: 6 }, grid: { display: false } },
        y: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } }
      }
    }
  });
}