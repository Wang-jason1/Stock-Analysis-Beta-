from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import os

app = FastAPI()

# Mount static files for the UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# Service URLs
NEWS_AGENT_URL = os.getenv("NEWS_AGENT_URL", "http://news-agent:8001")
STOCK_AGENT_URL = os.getenv("STOCK_AGENT_URL", "http://stock-agent:8002")
FORUM_AGENT_URL = os.getenv("FORUM_AGENT_URL", "http://forum-agent:8003")

@app.get("/")
def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/macro")
async def get_macro():
    # 這裡暫時維持原本的 macro_analyzer 邏輯，
    # 或者未來也可以拆分一個 macro_agent
    from macro_analyzer import get_macro_summary
    return get_macro_summary()

@app.get("/api/search")
async def search_ticker(q: str):
    import yfinance as yf
    # 支援台股搜尋
    results = yf.Search(q, max_results=8).quotes
    return [{
        "symbol": r.get("symbol"),
        "name": r.get("shortname") or r.get("longname") or r.get("symbol"),
        "exchange": r.get("exchange")
    } for r in results]

@app.get("/api/stocks")
def get_stocks():
    # 為使用者整理台股專區
    return [
        {
            "market": "台股 (Taiwan)",
            "sectors": [
                {
                    "name": "半導體",
                    "industries": [
                        {"name": "晶圓代工", "tickers": [{"symbol": "2330.TW", "name": "台積電"}, {"symbol": "2303.TW", "name": "聯電"}]},
                        {"name": "IC 設計", "tickers": [{"symbol": "2454.TW", "name": "聯發科"}]}
                    ]
                },
                {
                    "name": "電子代工",
                    "industries": [
                        {"name": "組裝", "tickers": [{"symbol": "2317.TW", "name": "鴻海"}, {"symbol": "2382.TW", "name": "廣達"}]}
                    ]
                }
            ]
        }
    ]

async def call_agent(url, ticker):
    async with httpx.AsyncClient() as client:
        try:
            # 增加超時上限至 60 秒
            resp = await client.get(f"{url}/analyze?q={ticker}", timeout=60.0)
            return resp.json()
        except Exception as e:
            print(f"[Gateway 警告] 代理人通訊失敗 ({url}): {e}")
            return {"error": f"通訊失敗: {str(e)}"}

@app.post("/api/analyze")
async def analyze_stocks(request: Request):
    data = await request.json()
    tickers = data.get("tickers", [])
    
    all_results = []
    for ticker in tickers:
        # 並行呼叫三個 Agent
        news_task = call_agent(NEWS_AGENT_URL, ticker)
        stock_task = call_agent(STOCK_AGENT_URL, ticker)
        forum_task = call_agent(FORUM_AGENT_URL, ticker)
        
        n_res, s_res, f_res = await asyncio.gather(news_task, stock_task, forum_task)
        
        # 確保皆為字典格式，避免 AttributeError
        n_res = n_res if isinstance(n_res, dict) else {"error": str(n_res)}
        s_res = s_res if isinstance(s_res, dict) else {"error": str(s_res)}
        f_res = f_res if isinstance(f_res, dict) else {"error": str(f_res)}
        
        b, d, u = 0.33, 0.33, 0.34 # 預設
        advice = "觀望控制風險"
        
        # 技術面影響 (Stock Agent)
        tech_data = s_res.get("technical_analysis")
        if isinstance(tech_data, dict):
            trend = tech_data.get("trend", "")
            if "多頭" in trend: b += 0.2; u -= 0.1
            if "空頭" in trend: d += 0.2; u -= 0.1
            
        all_results.append({
            "ticker": ticker,
            "b": b, "d": d, "u": u,
            "advice": advice,
            "details": {
                "news": n_res,
                "technical": s_res,
                "forum": f_res
            }
        })
        
    return {"results": all_results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
