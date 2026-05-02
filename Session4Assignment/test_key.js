import axios from 'axios';

const GEMINI_API_KEY = "AIzaSyBlE6YnVqYclmde7ZgDPve4TIzkgYEAtUQ";

async function testKey() {
    try {
        const res = await axios.post(
            `https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=${GEMINI_API_KEY}`,
            {
                contents: [{
                    parts: [{
                        text: "Extract stock symbol from: Analyze State Bank of India"
                    }]
                }]
            }
        );
        console.log("Success:", res.data.candidates[0].content.parts[0].text);
    } catch (e) {
        console.log("Error:", e.response ? e.response.data : e.message);
    }
}

testKey();
