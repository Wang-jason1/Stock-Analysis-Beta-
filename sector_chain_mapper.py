import requests
import json
import os

def map_sectors_and_tickers(macro_summary):
    """
    根據宏觀局勢摘要，透過 Ollama 推理出短/長期受惠產業，
    並列出對應的產業鏈與代表 Tickers (格式為 JSON)。
    """
    print("[產業推演] 正在根據局勢映射受惠產業與個股...")
    
    prompt = f"""
Given the following macro-economic summary:
"{macro_summary}"

Identify the short-term and long-term benefiting sectors and specific supply chains.
For each sector, provide a few representative stock tickers (prefer US stocks like NVDA, AAPL or Taiwan stocks with .TW like 2330.TW).

Return ONLY a valid JSON object with the following structure. Do NOT include markdown blocks like ```json :
{{
    "short_term": [
        {{
            "sector": "Sector Name",
            "reason": "Why it benefits short-term",
            "chain": ["Upstream", "Midstream", "Downstream"],
            "tickers": ["TICKER1", "TICKER2"]
        }}
    ],
    "long_term": [
        {{
            "sector": "Sector Name",
            "reason": "Why it benefits long-term",
            "chain": ["Upstream", "Midstream"],
            "tickers": ["TICKER3", "TICKER4"]
        }}
    ]
}}

Make sure the output can be parsed directly by Python's json.loads(). Use Traditional Chinese for text fields except tickers.
"""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    url = f"{ollama_url}/api/generate"
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()
        response_text = result.get('response', '').strip()
        
        # 簡單防禦 markdown 標籤
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        data = json.loads(response_text)
        return data
        
    except json.JSONDecodeError as je:
        print(f"[警告] LLM 輸出的格式非有效 JSON: {je}")
        print(f"原始回傳內容: {response_text[:200]}...")
        return _fallback_mapping()
    except Exception as e:
        print(f"[警告] 呼叫 Ollama 推演產業鏈失敗: {e}")
        return _fallback_mapping()

def _fallback_mapping():
    """當 LLM 失敗時的預設備用輸出行"""
    return {
        "short_term": [
            {
                "sector": "能源與原物料",
                "reason": "地緣政治不確定性推升避險情緒與物價",
                "chain": ["原油開採", "黃金"],
                "tickers": ["XOM", "GLD"]
            }
        ],
        "long_term": [
            {
                "sector": "AI 與半導體",
                "reason": "長期算力需求不可逆，基礎建設持續成長",
                "chain": ["晶片設計", "晶圓代工", "伺服器組裝"],
                "tickers": ["NVDA", "2330.TW", "2382.TW"]
            }
        ]
    }

if __name__ == "__main__":
    test_summary = "目前全球局勢圍繞在 AI 發展與中東地緣政治緊張。通膨有緩和跡象，聯準會考慮降息。"
    res = map_sectors_and_tickers(test_summary)
    print(json.dumps(res, indent=2, ensure_ascii=False))
