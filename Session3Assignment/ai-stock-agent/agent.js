import { getStockData, getFundamentals, getNews } from './api.js';
import { askGemini } from './gemini.js';

export async function runAgent(query, log) {

  const tickerMatch = query.match(/\b[A-Z]{2,5}\b/);
  const symbol = tickerMatch ? tickerMatch[0] : "AAPL";

  log(`🧠 Step 1: Fetching stock data for ${symbol}...`);
  const stock = await getStockData(symbol);

  log(`📊 Step 1.5: Fetching fundamentals for ${symbol}...`);
  const fundamentals = await getFundamentals(symbol);

  log(`📰 Step 2: Fetching news for ${symbol}...`);
  const news = await getNews(symbol);

  log("🔗 Step 3: Correlating data into multi-dimensional matrix...");

  const context = `
Fundamentals:
${JSON.stringify(fundamentals).slice(0, 400)}

Stock Data:
${JSON.stringify(stock).slice(0, 500)}

News:
${news.map(n => n.title).join("\n")}
`;

  log("🤖 Step 4: Calling Gemini...");

  const answer = await askGemini(query, context);

  log("✅ Done!");

  return { answer, stockData: stock, symbol };
}