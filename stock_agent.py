from fastapi import FastAPI
import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI()

def calculate_technicals(df):
    """
    計算簡單技術指標。
    """
    if len(df) < 20:
        return "數據不足以進行技術分析"
    
    # 20日均線
    ma20 = df['Close'].rolling(window=20).mean()
    current_price = df['Close'].iloc[-1]
    last_ma20 = ma20.iloc[-1]
    
    trend = "中立"
    if current_price > last_ma20 * 1.05:
        trend = "強勢多頭"
    elif current_price > last_ma20:
        trend = "微幅偏多"
    elif current_price < last_ma20 * 0.95:
        trend = "強勢空頭"
    elif current_price < last_ma20:
        trend = "微幅偏空"
        
    return {
        "current_price": round(float(current_price), 2),
        "ma20": round(float(last_ma20), 2),
        "trend": trend,
        "volume_status": "量增" if df['Volume'].iloc[-1] > df['Volume'].mean() else "量縮"
    }

@app.get("/analyze")
async def analyze_stock(q: str):
    """
    分析台股技術面。
    """
    # 如果使用者沒帶 .TW，自動補上 (針對台股專注)
    ticker_symbol = q.upper()
    if not (ticker_symbol.endswith(".TW") or ticker_symbol.endswith(".TWO")):
        ticker_symbol += ".TW"
        
    try:
        df = yf.download(ticker_symbol, period="1mo", interval="1d", progress=False)
        if df.empty:
            return {"error": "找不到該標的數據"}
            
        analysis = calculate_technicals(df)
        return {
            "ticker": ticker_symbol,
            "technical_analysis": analysis
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
