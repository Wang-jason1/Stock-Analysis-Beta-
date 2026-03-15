from fastapi import FastAPI
import requests
import os
import re

app = FastAPI()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

def mock_ptt_search(ticker):
    """
    模擬 PTT 搜尋結果。
    實際環境中這會是一個爬蟲或透過 API 抓取 PTT Stock 版資料。
    """
    # 這裡我們模擬一些 PTT 常見的評論風格
    mock_data = {
        "2330": ["台積電無敵的吧", "又要噴了", "這波上看 1000", "外資又在倒貨", "GG 進場時機"],
        "2454": ["發哥最近很猛", "聯發科起飛", "天璣晶片強無敵", "這價位不買嗎"],
        "DEFAULT": ["這隻沒救了", "主力在出貨", "散戶進場小心", "長期看好", "底部已到"]
    }
    # 提取純數字部分
    code = re.findall(r'\d+', ticker)
    key = code[0] if code and code[0] in mock_data else "DEFAULT"
    return mock_data[key]

def analyze_forum_sentiment(comments):
    """
    使用 LLM 總結論壇情緒。
    """
    text = "\n".join(comments)
    url = f"{OLLAMA_URL}/api/generate"
    prompt = (
        f"You are a social sentiment analyst. Here are some user comments from a stock forum about a specific ticker:\n"
        f"{text}\n\n"
        f"Summarize the overall retail sentiment in Traditional Chinese (Taiwan). "
        f"Is it optimistic, pessimistic, or fearful? (Max 2 sentences)."
    )
    payload = {"model": "llama3", "prompt": prompt, "stream": False}
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.json().get('response', '無法分析情緒').strip()
    except:
        return "論壇分析暫時不可用"

@app.get("/analyze")
async def analyze_forum(q: str):
    comments = mock_ptt_search(q)
    summary = analyze_forum_sentiment(comments)
    return {
        "ticker": q,
        "forum_sentiment": summary,
        "sample_comments": comments[:3]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
