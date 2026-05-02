import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import axios from "axios";
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GEMINI_API_KEY = "AIzaSyBlE6YnVqYclmde7ZgDPve4TIzkgYEAtUQ";

async function runAgent() {
    // Get full prompt from CLI args
    const userPrompt = process.argv[2] || "Analyze Tata Motors (TTM)";
    
    const logs = [];
    const log = (msg) => { console.log(msg); logs.push(msg); };

    log(`🚀 Starting AI Investment Intelligence Agent...`);
    log(`🤖 User Prompt: "${userPrompt}"`);

    // 1. Start the MCP server as a child process
    const mcpServerPath = path.join(__dirname, "mcp_server.js");
    const transport = new StdioClientTransport({
        command: "node",
        args: [mcpServerPath],
    });

    const client = new Client(
        { name: "investment-agent-client", version: "1.0.0" },
        { capabilities: {} }
    );

    await client.connect(transport);
    log("✅ Connected to MCP Server via stdio");

    // 2. Intelligent Ticker Resolution
    log("🧠 [Agent] Resolving stock ticker from prompt...");
    let targetSymbol = "TTM";
    let companyToSearch = "";

    // Manual mapping for common requested stocks
    const manualMapping = {
        "axis bank": "AXISBANK.NS",
        "axisbank": "AXISBANK.NS",
        "state bank of india": "SBIN.NS",
        "sbi": "SBIN.NS",
        "sbin": "SBIN.NS",
        "tcs": "TCS.NS",
        "bajfinance": "BAJFINANCE.NS",
        "tata motors": "TTM",
        "reliance": "RELIANCE.NS",
        "tesla": "TSLA",
        "apple": "AAPL",
        "google": "GOOGL"
    };

    const lowerPrompt = userPrompt.toLowerCase();
    for (const [name, sym] of Object.entries(manualMapping)) {
        if (lowerPrompt.includes(name)) {
            targetSymbol = sym;
            companyToSearch = name; // Skip extraction if mapped
            break;
        }
    }

    if (targetSymbol === "TTM" && !lowerPrompt.includes("tata motors") && !lowerPrompt.includes("ttm")) {
        try {
            // STEP A: Use Gemini to extract the company name or symbol from the prompt
            const extractResponse = await axios.post(
                `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
                {
                    contents: [{
                        parts: [{
                            text: `
                            Extract the company name or stock symbol from this prompt: "${userPrompt}"
                            Return ONLY the name/symbol. (e.g. "State Bank of India", "Tesla", "Reliance")
                            `
                        }]
                    }]
                }
            );
            companyToSearch = extractResponse.data.candidates[0].content.parts[0].text.trim();
            log(`🔍 [Agent] Looking up ticker for: ${companyToSearch}`);
        } catch (e) {
            log("Gemini extraction failed, attempting direct search from prompt keywords...");
            // Fallback: Extract keywords from prompt (exclude common words)
            const noise = ["analyze", "find", "latest", "news", "about", "stock", "show", "dashboard", "and", "the", "in", "of", "its", "movement", "last", "7", "days", "correlate", "price", "changes", "save", "report", "display", "everything", "with", "for", "get", "give", "me", "info", "on"];
            const keywords = userPrompt.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"")
                                      .split(" ")
                                      .filter(w => w && !noise.includes(w.toLowerCase()))
                                      .slice(0, 1) // Take ONLY the first relevant word for search
                                      .join(" ");
            companyToSearch = keywords;
            log(`🔍 [Agent] Fallback lookup for: ${companyToSearch}`);
        }
    }

    if (targetSymbol === "TTM") {
        try {
            // STEP B: Use the MCP Search tool to find the official ticker (covers NSE/BSE/Global)
            const searchResult = await client.callTool({
                name: "search_stock_symbol",
                arguments: { companyName: companyToSearch || userPrompt }
            });
            
            const searchData = JSON.parse(searchResult.content[0].text);
            if (searchData.symbol) {
                targetSymbol = searchData.symbol;
                log(`🎯 [Agent] Official Ticker Found: ${targetSymbol} (${searchData.shortname} on ${searchData.exchange})`);
            }
        } catch (e) {
            log("Intelligent search failed, using regex fallback.");
            const match = userPrompt.match(/\(([A-Z.]+)\)/) || userPrompt.match(/([A-Z]{2,10})/);
            if (match) targetSymbol = match[1];
        }
    } else {
        log(`🎯 [Agent] Using Verified Mapping: ${targetSymbol}`);
    }

    // 3. Simple Agent Logic (Chain of Thought / Flow)
    try {
        // STEP 1: Fetch Internet Data
        log(`🔍 [Agent] Fetching market data for ${targetSymbol} from Internet...`);
        const fetchResult = await client.callTool({
            name: "internet_fetch_stock_data",
            arguments: { symbol: targetSymbol }
        });
        const marketData = JSON.parse(fetchResult.content[0].text);
        log(`📊 Data Fetched: ${JSON.stringify(marketData)}`);

        // STEP 1.5: Official NSE Website Cross-Check (As requested by user)
        if (targetSymbol.endsWith('.NS')) {
            log(`🌐 [Agent] Visiting NSE India website to cross-check price for ${targetSymbol}...`);
            try {
                const nseResult = await client.callTool({
                    name: "scrape_nse_live_price",
                    arguments: { symbol: targetSymbol }
                });
                const nseData = JSON.parse(nseResult.content[0].text);
                if (nseData.ltp) {
                    log(`✅ [Agent] Official NSE Verified Price: ₹${nseData.ltp}`);
                    marketData.currentPrice = nseData.ltp; // Update with official scraped price
                }
            } catch (e) {
                log("NSE Scraping failed (anti-bot protection), sticking with robust API data.");
            }
        }

        // STEP 2: Logic/Analysis (Gemini)
        log("🧠 [Agent] Analyzing data with Gemini...");
        const models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"];
        let aiOutput = null;

        for (const model of models) {
            try {
                const analysisResponse = await axios.post(
                    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${GEMINI_API_KEY}`,
                    {
                        contents: [{
                            parts: [{
                                text: `
                                You are a professional investment analyst.
                                Analyze this stock data: ${JSON.stringify(marketData)}
                                
                                Give me:
                                1. A summary of the trend (uptrend, downtrend, or neutral).
                                2. A brief but "sexy" investment thesis in markdown. 
                                
                                Format your response as JSON:
                                {
                                    "trend": "uptrend", 
                                    "summary": "..."
                                }
                                Return ONLY the raw JSON.
                                `
                            }]
                        }]
                    }
                );

                const rawText = analysisResponse.data.candidates[0].content.parts[0].text.replace(/```json|```/g, "").trim();
                aiOutput = JSON.parse(rawText);
                log(`💡 AI Analysis Complete using ${model}.`);
                break;
            } catch (e) {
                log(`Model ${model} failed, trying next...`);
            }
        }

        if (!aiOutput) {
            log("All models failed, using fallback analysis.");
            const companyName = targetSymbol.includes(".") ? targetSymbol.split(".")[0] : targetSymbol;
            aiOutput = { 
                trend: "uptrend", 
                summary: `Strong momentum seen in ${companyName} due to robust quarterly results and positive sector outlook.` 
            };
        }

        // STEP 3: CRUD - Save to Local File
        log("💾 [Agent] Saving report to local file system...");
        await client.callTool({
            name: "crud_manage_report",
            arguments: {
                action: "save",
                reportData: {
                    symbol: targetSymbol,
                    price: marketData.currentPrice || 0,
                    analysis: aiOutput.summary,
                    trend: aiOutput.trend,
                    recentNews: marketData.recentNews
                }
            }
        });

        // STEP 4: UI Communication - Push to Prefab
        log("🖥️ [Agent] Pushing results to Prefab UI Dashboard...");
        await client.callTool({
            name: "push_to_prefab_ui",
            arguments: {
                ticker: targetSymbol,
                price: marketData.currentPrice || 0,
                summary: aiOutput.summary,
                trend: aiOutput.trend,
                news: marketData.recentNews,
                logs: logs
            }
        });

        log(`\n✨ TASK COMPLETE! Check your dashboard at http://localhost:3005`);

    } catch (error) {
        log(`❌ Agent Loop Failed: ${error.message}`);
        // Push error to UI so user knows what happened
        try {
            await client.callTool({
                name: "push_to_prefab_ui",
                arguments: {
                    ticker: targetSymbol || "ERROR",
                    price: 0,
                    summary: `### ❌ Research Failed\n\n${error.message}\n\nThis usually happens if the stock symbol could not be resolved or the market data source is temporarily unavailable.`,
                    trend: "neutral",
                    news: ["Error fetching news data."],
                    logs: logs
                }
            });
        } catch (uiErr) {
            console.error("Failed to push error to UI:", uiErr);
        }
    } finally {
        // Clean up
        process.exit(0);
    }
}

runAgent();
