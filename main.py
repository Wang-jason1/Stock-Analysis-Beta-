import yfinance as yf
import pandas as pd
import numpy as np
import torch
import requests
import json
import os
from datetime import datetime, timedelta
import macro_analyzer
import sector_chain_mapper

def get_device():
    # 檢查是否有 NVIDIA GPU
    if torch.cuda.is_available():
        print("[系統] 偵測到 NVIDIA GPU，使用 CUDA 進行運算。")
        return torch.device("cuda")
    else:
        print("[系統] 未偵測到 NVIDIA GPU，使用 CPU 進行運算。")
        return torch.device("cpu")

def analyze_sentiment_ollama(text, model="llama3"):
    """
    呼叫本地 Ollama API 進行情緒分析。
    """
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    url = f"{ollama_url}/api/generate"
    prompt = (
        f"You are a financial sentiment analyzer. Read the following news title and output ONLY a single float number between -1 and 1 "
        f"representing its sentiment (e.g., 0.8 for very positive, -0.5 for somewhat negative, 0 for neutral).\n\n"
        f"News Title: {text}\n\n"
        f"Output (just the number):"
    )
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        score_text = result.get('response', '').strip()
        score = float(score_text)
        return max(-1.0, min(1.0, score))
    except Exception:
        return None

def get_sentiment_consensus(text):
    """
    多模型共識機制：結合 Llama 3 與 Mistral 的評分。
    """
    models = ["llama3", "mistral"]
    scores = []
    
    for m in models:
        s = analyze_sentiment_ollama(text, model=m)
        if s is not None:
            scores.append(s)
            
    if not scores:
        return 0.0 # 預設中立
        
    return sum(scores) / len(scores)

def fetch_data(ticker_symbol):
    print(f"\n[資料引擎] 正在抓取 {ticker_symbol} 的數據...")
    ticker = yf.Ticker(ticker_symbol)
    
    # 抓取新聞 (yfinance 的 news 通常是最近的)
    news = getattr(ticker, 'news', [])
    recent_news = []
    
    now = datetime.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    for item in news:
        # yfinance news 格式可能不同，確保能取得時間
        if 'providerPublishTime' in item:
            pub_date = datetime.fromtimestamp(item['providerPublishTime'])
        elif 'content' in item and 'pubDate' in item['content']:
            # 新版 yfinance 結構
            d_str = item['content']['pubDate']
            try:
                # 簡單處理一般 ISO 格式
                pub_date = pd.to_datetime(d_str).replace(tzinfo=None)
            except:
                pub_date = now # 解析失敗先當作現在
        else:
            pub_date = now
            
        if pub_date >= twenty_four_hours_ago:
            recent_news.append(item)
            
    print(f"[資料引擎] 找到 {len(recent_news)} 則過去 24 小時內的新聞。")
    
    # 抓取股價與均線 (用歷史資料計算 20 日均線)
    print(f"[資料引擎] 正在抓取歷史股價...")
    hist = ticker.history(period="1mo")
    current_price = 0
    ma20 = 0
    if len(hist) > 0:
        current_price = hist['Close'].iloc[-1]
        if len(hist) >= 20:
            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        else:
            ma20 = hist['Close'].mean() # 資料不足時用平均代替
        print(f"[資料引擎] 最新收盤價: {current_price:.2f}, 20日均線: {ma20:.2f}")
    else:
        print("[警告] 無法取得股價與均線資訊。")
        
    return recent_news, current_price, ma20

def calculate_evidence(news_list, current_price, ma20):
    r_news, s_news = 0, 0
    
    print("\n[LLM 語意分析]")
    # 測試 Ollama 是否可用
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    test_score = analyze_sentiment_ollama("Test")
    if test_score is None:
        print(f"-> 無法連線至 Ollama ({ollama_url})，改用簡易關鍵字模擬情緒。")
        use_ollama = False
    else:
        print("-> 成功連線至本地 Ollama，將使用 Llama 3 進行評分。")
        use_ollama = True
        
    for item in news_list:
        title = item.get('title', '')
        if not title and 'content' in item:
            title = item['content'].get('title', '')
            
        if not title:
            continue
            
        print(f"- 新聞: {title}")
        if use_ollama:
            score = get_sentiment_consensus(title)
            if score is not None:
                if score >= 0.2:
                    r_news += 1
                    print(f"  -> 情緒得分: {score:.2f} (利多 +1)")
                elif score <= -0.2:
                    s_news += 1
                    print(f"  -> 情緒得分: {score:.2f} (利空 +1)")
                else:
                    print(f"  -> 情緒得分: {score:.2f} (中立)")
            else:
                print(f"  -> 情緒得分分析失敗 (中立)")
        else:
            # 簡易關鍵字判斷
            positive_words = ['up', 'gain', 'growth', 'positive', 'buy', 'bull', '漲', '增長', '看好', '買', '強勢', '創高', 'high', 'surge', 'jump']
            negative_words = ['down', 'loss', 'drop', 'negative', 'sell', 'bear', '跌', '衰退', '看壞', '賣', '弱勢', '破底', 'low', 'fall', 'plunge']
            t_lower = title.lower()
            if any(word in t_lower for word in positive_words):
                r_news += 1
                print("  -> 關鍵字判斷: 利多 (+1)")
            elif any(word in t_lower for word in negative_words):
                s_news += 1
                print("  -> 關鍵字判斷: 利空 (+1)")
            else:
                print("  -> 關鍵字判斷: 中立")
                
    # 結合技術面
    r_tech, s_tech = 0, 0
    if current_price > ma20 and ma20 > 0:
        r_tech = 1
    elif current_price < ma20 and ma20 > 0:
        s_tech = 1
        
    total_r = r_news + r_tech
    total_s = s_news + s_tech
    print(f"\n[證據提取] 總正面證據 (r) = 新聞({r_news}) + 技術面({r_tech}) = {total_r}")
    print(f"[證據提取] 總負面證據 (s) = 新聞({s_news}) + 技術面({s_tech}) = {total_s}")
    
    return total_r, total_s
    
def calculate_subjective_logic(r, s, device):
    """
    使用 PyTorch Tensor (支援 CUDA) 計算 Subjective Logic 公式
    b = r / (r + s + 2)
    d = s / (r + s + 2)
    u = 2 / (r + s + 2)
    """
    print(f"\n[主觀邏輯引擎] 開始計算...")
    r_tensor = torch.tensor(float(r), device=device)
    s_tensor = torch.tensor(float(s), device=device)
    two_tensor = torch.tensor(2.0, device=device)
    
    denominator = r_tensor + s_tensor + two_tensor
    
    # 進行張量運算
    b_tensor = r_tensor / denominator
    d_tensor = s_tensor / denominator
    u_tensor = two_tensor / denominator
    
    # 將結果轉回 Python float
    b = b_tensor.item()
    d = d_tensor.item()
    u = u_tensor.item()
    
    return b, d, u

def analyze_ticker(ticker_symbol, device):
    """分析單一個股並回傳 SL 指標與建議"""
    news_list, current_price, ma20 = fetch_data(ticker_symbol)
    
    if len(news_list) == 0:
         print("   [系統] 尚未抓取到近期新聞，使用預設模擬新聞。")
         news_list = [{"title": f"{ticker_symbol} market sentiment remains stable amid broader economic trends"}]
         
    r, s = calculate_evidence(news_list, current_price, ma20)
    b, d, u = calculate_subjective_logic(r, s, device)
    
    if b > 0.6 and u < 0.3:
        advice = "🟢 【買入】"
    elif d > 0.5:
        advice = "🔴 【賣出】"
    else:
        advice = "🟡 【觀望】"
        
    return b, d, u, advice, news_list

def run_analysis_for_tickers(tickers):
    """供 API 呼叫的入口點"""
    device = get_device()
    results = []
    for ticker in tickers:
        print(f"\n--- API 請求分析標的：{ticker} ---")
        try:
            b, d, u, advice, news_list = analyze_ticker(ticker, device)
            # 轉換 news_list 為簡單的主旨文字清單
            evidence = [n.get('title', '') or n.get('content', {}).get('title', '') for n in news_list]
            results.append({
                "ticker": ticker,
                "b": round(b, 4),
                "d": round(d, 4),
                "u": round(u, 4),
                "advice": advice,
                "evidence": evidence
            })
        except Exception as e:
            print(f"分析 {ticker} 時發生錯誤: {e}")
            results.append({
                "ticker": ticker,
                "error": str(e)
            })
    return results

def main():
    device = get_device()
    
    # ... (省略中間部分以保持一致性，但我們要在 main() 裡也捕獲 news_list)
    # 實際上 main() 內部的分析迴圈也需要更新
    
    print("\n" + "="*50)
    print(" 🌍 Sentin-AI 宏觀與產業鏈投資分析系統 (SASA Top-Down)")
    print("="*50)
    
    # 階段 1：宏觀局勢分析
    print("\n>>> 階段 1：獲取全球總經局勢 <<<")
    macro_summary = macro_analyzer.get_macro_summary()
    print("\n【當前世界局勢總結】:")
    print("-" * 50)
    print(macro_summary)
    print("-" * 50)
    
    # 階段 2：產業鏈推演
    print("\n>>> 階段 2：LLM 產業鏈與板塊輪動推演 <<<")
    sector_data = sector_chain_mapper.map_sectors_and_tickers(macro_summary)
    
    # 集合所有推薦標的以進行 SL 運算
    target_tickers = []
    
    print("\n【短期受惠產業】:")
    for item in sector_data.get("short_term", []):
        print(f"\n- 產業：{item.get('sector')}")
        print(f"  > 理由：{item.get('reason')}")
        print(f"  > 產業鏈：{' -> '.join(item.get('chain', []))}")
        tickers = item.get('tickers', [])
        print(f"  > 關注標的：{', '.join(tickers)}")
        target_tickers.extend(tickers)
        
    print("\n【長期趨勢產業】:")
    for item in sector_data.get("long_term", []):
        print(f"\n- 產業：{item.get('sector')}")
        print(f"  > 理由：{item.get('reason')}")
        print(f"  > 產業鏈：{' -> '.join(item.get('chain', []))}")
        tickers = item.get('tickers', [])
        print(f"  > 關注標的：{', '.join(tickers)}")
        target_tickers.extend(tickers)
        
    # 去除重複 Tickers
    target_tickers = list(set(target_tickers))
    if not target_tickers:
        print("[警告] 未成功推演出任何標的，採用預設標的測試。")
        target_tickers = ["2330.TW", "NVDA"]
        
    # 階段 3：主觀邏輯信心分析
    print("\n" + "="*50)
    print(">>> 階段 3：個股主觀邏輯信心分析 (SL Brain) <<<")
    print("="*50)
    
    results = []
    for ticker in target_tickers:
        print(f"\n--- 分析標的：{ticker} ---")
        try:
            b, d, u, advice, news_list = analyze_ticker(ticker, device)
            results.append({
                "Ticker": ticker,
                "b 確信度": b,
                "d 不相信度": d,
                "u 不確定性": u,
                "建議": advice
            })
        except Exception as e:
            print(f"分析 {ticker} 時發生錯誤: {e}")
            
    # 階段 4：綜合報告輸出
    print("\n" + "="*50)
    print(" 📊 最終決策報告總結")
    print("="*50)
    df_report = pd.DataFrame(results)
    if not df_report.empty:
        # 印出格式化表格
        print(df_report.to_string(index=False, float_format="%.4f"))
    else:
        print("無有效分析結果。")
    print("="*50)

if __name__ == "__main__":
    main()
