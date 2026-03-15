# SASA (Sentin-AI Sentiment Analysis)

SASA 是一個強大的、基於微服務架構的 AI 股票分析系統。它結合了大型語言模型 (LLM)、量價技術分析與社群情緒，透過**主觀邏輯 (Subjective Logic)** 來為您提供最具深度的投資見解，並特別針對**台灣股市**進行了優化。

## 🌟 核心特色

- **分散式專家微服務架構**：系統拆分為多個獨立的情報代理人 (Agents)，確保分析的專業度與系統的擴展性。
- **雙模型情緒共識機制**：新聞分析不再是「一言堂」。SASA 同時使用 **Llama 3 (Meta)** 與 **Mistral** 進行情緒判定，透過共識機制大幅降低單一AI模型的偏見與幻覺。
- **台股專屬優化**：內建台股技術面分析專家，自動對台灣股票代號補打 `.TW` / `.TWO` 標籤，並整合了在地化的散戶論壇情緒 (PTT) 模擬分析。
- **即時宏觀總經看板**：一眼掌握全球局勢，包含美股指數、債券殖利率、原物料原物料與加密貨幣，並由 AI 推薦潛在的受惠產業鏈。
- **GPU 深度加速**：完整支援 NVIDIA CUDA (特別針對 RTX 系列等顯卡優化)，將龐大的 LLM 推理與運算負載轉移至 GPU 進行極速處理。

## 🏗️ 系統架構 (Microservices)

SASA 2.0 採用了分散式的代理人 (Multi-Agent) 架構：

1. **API Gateway & Web UI (`api.py`, Port: 8000)**
   - 整個系統的總指揮。負責提供精美的 Web 介面，接收使用者指令，並協調下方三個專家代理人。最後使用主觀邏輯 (SL) 算法計算出最終的 $b$ (確信)、$d$ (不信)、$u$ (不確定) 指標。
2. **News Intelligence Agent (`news_agent.py`, Port: 8001)**
   - **全球新聞情報專家**：負責抓取標的物的最新國際新聞，並並行調用 Llama 3 與 Mistral 進行「雙模型共識」的情緒評分。
3. **Stock Technical Agent (`stock_agent.py`, Port: 8002)**
   - **台股技術分析專家**：負責分析歷史量價數據、計算移動平均線 (MA) 等技術指標，判斷當前處於多頭或空頭趨勢。
4. **Forum Sentiment Agent (`forum_agent.py`, Port: 8003)**
   - **零售情緒專家**：專門分析 PTT 等本地論壇的散戶留言，藉由 LLM 判斷當前市場是恐慌還是貪婪 (目前為模擬資料展示)。

## 🚀 快速開始

### ⚠️ 關於 AI 模型檔案 (重要)
SASA 使用的 Meta Llama 3 與 Mistral 模型檔案非常龐大 (數 GB)，**這些模型檔案「不需要」也不會被推送 (Push) 到 GitHub 代碼庫中**。

系統已經將模型的下載與安裝流程寫入 `docker-compose.yml` 的自動化腳本中。當您第一次啟動雲端容器時，系統會在背景全自動為您下載並安裝所需模型，您無需手動處理！

### 系統需求
- Docker & Docker Compose
- NVIDIA GPU (建議) 以及 NVIDIA Container Toolkit，以獲得最佳的 LLM 執行速度。

### 安裝與啟動

1. **進入專案目錄**
   確保您位於專案的根目錄下 (包含 `docker-compose.yml` 的位置)。

2. **使用 Docker Compose 啟動環境**
   一鍵編譯並啟動所有微服務與資料庫：
   ```bash
   docker-compose up -d --build
   ```
   *📌 **首次啟動提醒**：容器啟動後，Ollama 服務會在背景自動執行 `ollama pull llama3` 與 `ollama pull mistral` 下載模型。請給系統幾分鐘的時間完成下載，下載完成後 AI 分析功能即可正常運作。*

3. **開啟 Web 介面**
   待容器全部啟動完畢後，打開瀏覽器前往：
   ```text
   http://localhost:8000
   ```

## 🧠 使用教學

1. **刷新宏觀概覽**：點擊右上角的「刷新宏觀概覽」按鈕，SASA 會自動抓取總經數據並生成最新的世界局勢解讀與投資建議。
2. **快速加入清單**：在宏觀建議的卡片中，您可以直接點擊推薦的股票代號，快速將其加入追蹤清單。
3. **動態搜尋**：使用左側的搜尋列，輸入任何您想了解的股票代號 (如 `2330`)，系統會從全球資料庫中精準匹配。
4. **執行分析**：勾選您有興趣的標的後，點擊「執行分析」，SASA 就會派出三位專家代理人，為您交叉比對出一份綜合的策略報告。

## 📂 專案結構

- `api.py`: 系統的 API 閘道器與網頁後端。
- `news_agent.py`: 新聞擷取與雙模型共識分析微服務。
- `stock_agent.py`: 歷史報價技術面數據運算微服務。
- `forum_agent.py`: 論壇情緒擷取與分析微服務。
- `macro_analyzer.py`: 全球總經局勢爬蟲與 LLM 總結模組。
- `sector_chain_mapper.py`: 產業鏈與受惠股庫存資料檔。
- `static/`: 前端靜態資源 (HTML, CSS, JavaScript)。
- `docker-compose.yml`: 容器化微服務部署配置檔。
- `Dockerfile`: Python 微服務容器的建置腳本。
