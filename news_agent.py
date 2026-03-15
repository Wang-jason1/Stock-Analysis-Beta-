from fastapi import FastAPI, Request
import yfinance as yf
import os
import requests
import asyncio

app = FastAPI()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

def analyze_sentiment_ollama(text, model="llama3"):
    url = f"{OLLAMA_URL}/api/generate"
    prompt = (
        f"You are a financial sentiment analyzer. Read the following news title and output ONLY a single float number between -1 and 1 "
        f"representing its sentiment (e.g., 0.8 for very positive, -0.5 for somewhat negative, 0 for neutral).\n\n"
        f"News Title: {text}\n\n"
        f"Output (just the number):"
    )
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return float(response.json().get('response', '0').strip())
    except:
        return 0.0

async def get_consensus_score(text):
    # Run in parallel to save time
    loop = asyncio.get_event_loop()
    f1 = loop.run_in_executor(None, analyze_sentiment_ollama, text, "llama3")
    f2 = loop.run_in_executor(None, analyze_sentiment_ollama, text, "mistral")
    scores = await asyncio.gather(f1, f2)
    valid_scores = [s for s in scores if s is not None]
    return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

@app.get("/analyze")
async def analyze_news(q: str):
    """
    獲取全球新聞並分析情緒。
    """
    ticker = yf.Ticker(q)
    news = ticker.news[:3] # 縮減為 3 則以提升速度
    
    results = []
    for n in news:
        title = n.get('title', '')
        score = await get_consensus_score(title) # 內部已有 10s timeout
        results.append({
            "title": title,
            "score": score,
            "link": n.get('link')
        })
    
    return {"ticker": q, "news_analysis": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
