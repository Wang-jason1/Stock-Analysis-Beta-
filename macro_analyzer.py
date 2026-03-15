import yfinance as yf
import requests
import os

def fetch_global_macro_news():
    """
    獲取全球總經新聞。這裡我們可以用一些重要指數或 ETF 的新聞作為代表，
    例如 SPY (S&P 500), QQQ (Nasdaq), TLT (美國公債)。
    """
    print("[宏觀分析] 正在抓取全球重大財經新聞...")
    macro_tickers = [
        "SPY", "QQQ", "TLT", # 美股大盤與債券
        "CL=F", "GC=F",      # 原油與黃金 (大宗物資)
        "^TNX",              # 十年期美債殖利率
        "BTC-USD",           # 加密貨幣 (風險情緒指標)
        "VIX"                # 波動率指數 (市場恐慌指標)
    ]
    all_news = []
    
    for symbol in macro_tickers:
        ticker = yf.Ticker(symbol)
        news = getattr(ticker, 'news', [])
        # 只取每個標的前 3 則最新新聞
        for item in news[:3]:
            title = item.get('title', '')
            if title and title not in all_news:
                all_news.append(title)
                
    return all_news

def analyze_macro_with_llm(news_list):
    """
    將新聞清單餵給 Ollama，要求總結當前世界局勢與潛在影響。
    """
    if not news_list:
        return "無法取得新聞，預設局勢為：中立平穩。"

    news_text = "\n- ".join(news_list)
    prompt = f"""
You are a top-tier macro-economic analyst. Read the following recent global financial news headlines:
- {news_text}

Based on these headlines, write a concise summary (under 150 words) of the "Current World Economic and Geopolitical Situation". 
Highlight the main driving forces (e.g., inflation, war, AI boom, fed rates).
Use Traditional Chinese (繁體中文).
"""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    url = f"{ollama_url}/api/generate"
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }
    
    print("[宏觀分析] 正在呼叫 Ollama 分析局勢...")
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()
    except Exception as e:
        print(f"[警告] 呼叫 Ollama 失敗: {e}")
        return "分析失敗，可能 Ollama 未啟動。"

def get_macro_summary():
    news = fetch_global_macro_news()
    summary = analyze_macro_with_llm(news)
    return {
        "summary": summary,
        "news": news
    }

if __name__ == "__main__":
    print(get_macro_summary())
