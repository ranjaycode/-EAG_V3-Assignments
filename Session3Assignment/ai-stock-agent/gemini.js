const GEMINI_API_KEY = "AIzaSyBlE6YnVqYclmde7ZgDPve4TIzkgYEAtUQ";

export async function askGemini(query, context) {
    if (!GEMINI_API_KEY || GEMINI_API_KEY === "[ENCRYPTION_KEY]") {
        throw new Error("Missing Gemini API Key. Please update gemini.js.");
    }

    const modelsToTry = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-lite-001"
    ];

    let lastError = null;

    for (const model of modelsToTry) {
        const res = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${GEMINI_API_KEY}`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    contents: [{
                        parts: [{
                            text: `
You are an expert stock analyst AI.

User Query: ${query}

Context:
${context}

You MUST return your response as a raw JSON string formatted exactly like this:
{
  "sentiment": "BULLISH", // or BEARISH or NEUTRAL Based on data
  "analysis": "Your highly detailed markdown analysis combining math & sentiment..."
}
IMPORTANT: Do NOT wrap the JSON in markdown code blocks like \`\`\`json. Return JUST the raw JSON string.
            `
                        }]
                    }]
                })
            }
        );

        if (res.ok) {
            const data = await res.json();
            return data.candidates && data.candidates[0] ? data.candidates[0].content.parts[0].text : "No response generated.";
        } else {
            const errContext = await res.text();
            lastError = new Error(`Gemini API Error: ${res.status} - ${errContext}`);
            // If it's a 503 high demand, we loop and try the next model.
            // For other severe errors (like 400 Bad Request), we could break, but let's just keep trying fallbacks.
            console.warn(`Model ${model} failed, trying next...`, lastError.message);
        }
    }

    throw lastError;
}