document.addEventListener('DOMContentLoaded', () => {
    const stockTree = document.getElementById('stockTree');
    const searchInput = document.getElementById('searchInput');
    const dynamicResults = document.getElementById('dynamicSearchResults');
    const selectedList = document.getElementById('selectedList');
    const selectedCount = document.getElementById('selectedCount');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const analyzeBtnText = analyzeBtn.querySelector('span');
    const spinner = analyzeBtn.querySelector('.spinner');
    const resultsContainer = document.getElementById('resultsContainer');
    const errorMsg = document.getElementById('errorMsg');
    const macroContent = document.getElementById('macroContent');
    const refreshMacroBtn = document.getElementById('refreshMacroBtn');

    let allStockData = [];
    let selectedTickers = new Set();
    const checkboxMap = new Map();
    let searchTimer;

    init();

    async function init() {
        fetchMacro(); // 異步獲取宏觀分析
        try {
            const res = await fetch('/api/stocks');
            if (!res.ok) throw new Error('無法取得股票清單。');
            allStockData = await res.json();
            renderTree(allStockData);
        } catch (err) {
            stockTree.innerHTML = `<div class="error-msg">${err.message}</div>`;
        }
    }

    function renderTree(data) {
        stockTree.innerHTML = '';
        data.forEach(market => {
            const marketNode = createTreeNode(market.market, 'fa-globe');
            const marketContent = marketNode.querySelector('.tree-content');
            
            market.sectors.forEach(sector => {
                const sectorNode = createTreeNode(sector.name, 'fa-industry');
                const sectorContent = sectorNode.querySelector('.tree-content');
                
                sector.industries.forEach(industry => {
                    const industryNode = createTreeNode(industry.name, 'fa-microchip');
                    const industryContent = industryNode.querySelector('.tree-content');
                    
                    industry.tickers.forEach(stock => {
                        const tickerItem = createTickerItem(stock);
                        industryContent.appendChild(tickerItem);
                    });
                    sectorContent.appendChild(industryNode);
                });
                marketContent.appendChild(sectorNode);
            });
            marketNode.classList.add('expanded');
            stockTree.appendChild(marketNode);
        });
    }

    function createTreeNode(title, iconClass) {
        const node = document.createElement('div');
        node.className = 'tree-node';
        node.innerHTML = `
            <div class="tree-title">
                <i class="fa-solid fa-chevron-right"></i>
                <i class="fa-solid ${iconClass}" style="margin-left: 0.5rem; margin-right: 0.5rem; color: var(--text-secondary)"></i>
                ${title}
            </div>
            <div class="tree-content"></div>
        `;
        node.querySelector('.tree-title').addEventListener('click', () => {
            node.classList.toggle('expanded');
        });
        return node;
    }

    function createTickerItem(stock) {
        const item = document.createElement('label');
        item.className = 'ticker-item';
        item.dataset.search = `${stock.symbol.toLowerCase()} ${stock.name.toLowerCase()}`;
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = stock.symbol;
        checkbox.addEventListener('change', (e) => handleSelection(e.target.checked, stock));
        
        checkboxMap.set(stock.symbol, checkbox);
        item.appendChild(checkbox);
        
        const symbolSpan = document.createElement('span');
        symbolSpan.className = 'ticker-symbol';
        symbolSpan.textContent = stock.symbol;
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'ticker-name';
        nameSpan.textContent = stock.name;

        item.appendChild(symbolSpan);
        item.appendChild(nameSpan);
        
        return item;
    }

    function handleSelection(isChecked, stock) {
        if (isChecked) {
            // Check if ticker already exists in set (by symbol)
            let existing = Array.from(selectedTickers).find(s => s.symbol === stock.symbol);
            if (!existing) selectedTickers.add(stock);
        } else {
            selectedTickers.forEach(s => {
                if (s.symbol === stock.symbol) selectedTickers.delete(s);
            });
        }
        updateSelectionUI();
    }

    function updateSelectionUI() {
        selectedList.innerHTML = '';
        selectedCount.textContent = selectedTickers.size;
        
        if (selectedTickers.size === 0) {
            selectedList.innerHTML = '<li class="empty-msg">尚未選擇任何股票</li>';
            analyzeBtn.disabled = true;
            return;
        }

        analyzeBtn.disabled = false;
        
        selectedTickers.forEach(stock => {
            const chip = document.createElement('li');
            chip.className = 'selected-chip';
            chip.innerHTML = `
                ${stock.symbol}
                <i class="fa-solid fa-xmark"></i>
            `;
            chip.querySelector('i').addEventListener('click', () => {
                selectedTickers.delete(stock);
                const cb = checkboxMap.get(stock.symbol);
                if (cb) cb.checked = false;
                updateSelectionUI();
            });
            selectedList.appendChild(chip);
        });
    }

    // 全局即時搜尋：跨樹查找 + 動態 API 搜尋
    searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toUpperCase().trim();
        const items = document.querySelectorAll('.ticker-item');
        
        // 1. 本地清單過濾
        if (!term) {
            items.forEach(item => {
                item.classList.remove('hidden');
                item.style.display = 'flex';
            });
            document.querySelectorAll('.tree-node').forEach(node => {
                node.style.display = 'block';
                if(node.parentElement.id === 'stockTree') node.classList.add('expanded');
                else node.classList.remove('expanded');
            });
            dynamicResults.classList.remove('visible');
            dynamicResults.innerHTML = '';
            return;
        }

        let foundLocal = false;
        items.forEach(item => {
            const searchContent = item.dataset.search.toUpperCase();
            if (searchContent.includes(term)) {
                item.classList.remove('hidden');
                item.style.display = 'flex';
                foundLocal = true;
                // 展開父層
                let parent = item.closest('.tree-node');
                while (parent) {
                    parent.classList.add('expanded');
                    parent.style.display = 'block';
                    parent = parent.parentElement.closest('.tree-node');
                }
            } else {
                item.classList.add('hidden');
                item.style.display = 'none';
            }
        });

        // 隱藏沒有結果的分類
        document.querySelectorAll('.tree-node').forEach(node => {
            const content = node.querySelector('.tree-content');
            const hasVisible = content.querySelector('.ticker-item:not(.hidden)') || 
                               content.querySelector('.tree-node[style*="display: block"]');
            if (!hasVisible) node.style.display = 'none';
            else node.style.display = 'block';
        });

        // 2. 動態 API 搜尋 (Debounced)
        clearTimeout(searchTimer);
        if (term.length >= 2) {
            searchTimer = setTimeout(() => performDynamicSearch(term), 500);
        } else {
            dynamicResults.classList.remove('visible');
            dynamicResults.innerHTML = '';
        }
    });

    async function performDynamicSearch(query) {
        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            if (!res.ok) return;
            const data = await res.json();
            renderDynamicResults(data);
        } catch (err) {
            console.error('Search error:', err);
        }
    }

    function renderDynamicResults(results) {
        dynamicResults.innerHTML = '';
        if (results.length === 0) {
            dynamicResults.classList.remove('visible');
            return;
        }

        dynamicResults.classList.add('visible');
        results.forEach(stock => {
            if (checkboxMap.has(stock.symbol)) return;

            const div = document.createElement('div');
            div.className = 'dynamic-item';
            div.innerHTML = `
                <div class="ticker-symbol">${stock.symbol}</div>
                <div class="ticker-info">
                    <span class="ticker-name">${stock.name}</span>
                    <span class="ticker-meta">${stock.exchange} | ${stock.sector}</span>
                </div>
                <div class="add-icon"><i class="fa-solid fa-plus"></i></div>
            `;
            div.addEventListener('click', () => {
                handleSelection(true, stock);
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('input'));
            });
            dynamicResults.appendChild(div);
        });
    }

    analyzeBtn.addEventListener('click', async () => {
        if (selectedTickers.size === 0) return;
        const tickers = Array.from(selectedTickers).map(s => s.symbol);
        
        analyzeBtn.disabled = true;
        analyzeBtnText.innerHTML = '<i class="fa-solid fa-robot"></i> 分析中...';
        spinner.classList.remove('hidden');
        errorMsg.classList.add('hidden');
        resultsContainer.innerHTML = '<div class="empty-msg">SASA 正在調用 GPU 與主觀邏輯引擎分析中...</div>';

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tickers })
            });
            if (!res.ok) throw new Error('後端錯誤');
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            renderResults(data.results);
        } catch (err) {
            errorMsg.textContent = `錯誤: ${err.message}`;
            errorMsg.classList.remove('hidden');
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtnText.innerHTML = '<i class="fa-solid fa-robot"></i> 開始 AI 分析';
            spinner.classList.add('hidden');
        }
    });

    function renderResults(results) {
        resultsContainer.innerHTML = '';
        results.forEach((res, index) => {
            const card = document.createElement('div');
            card.className = `result-card ${res.b > res.d ? 'buy' : (res.d > res.b ? 'sell' : 'hold')}`;
            card.style.animationDelay = `${index * 0.1}s`;
            
            const newsHtml = res.details.news.news_analysis ? res.details.news.news_analysis.map(n => `<li>${n.title} (情緒: ${n.score.toFixed(1)})</li>`).join('') : '無新聞數據';
            const tech = res.details.technical.technical_analysis || {};
            const forum = res.details.forum || {};

            card.innerHTML = `
                <div class="res-header">
                    <span class="res-ticker">${res.ticker}</span>
                    <span class="res-advice">信賴度指標: b=${res.b.toFixed(2)} d=${res.d.toFixed(2)} u=${res.u.toFixed(2)}</span>
                </div>
                
                <div class="agent-insights">
                    <div class="insight-group">
                        <div class="insight-header"><i class="fa-solid fa-earth-americas"></i> 全球新聞情報 (News Agent)</div>
                        <ul class="evidence-list">${newsHtml}</ul>
                    </div>
                    <div class="insight-group">
                        <div class="insight-header"><i class="fa-solid fa-chart-line"></i> 台股技術面 (Stock Agent)</div>
                        <div class="evidence-item">趨勢: ${tech.trend || '未知'} | 目前價格: ${tech.current_price || 'N/A'} | 成交量: ${tech.volume_status || '未知'}</div>
                    </div>
                    <div class="insight-group">
                        <div class="insight-header"><i class="fa-solid fa-comments"></i> 零售情緒 (Forum Agent)</div>
                        <div class="evidence-item">${forum.forum_sentiment || '暫無討論'}</div>
                    </div>
                </div>
            `;
            resultsContainer.appendChild(card);
        });
    }

    refreshMacroBtn.addEventListener('click', fetchMacro);

    async function fetchMacro() {
        macroContent.innerHTML = '<div class="loading">正在分析總經局勢...</div>';
        refreshMacroBtn.disabled = true;
        try {
            const res = await fetch('/api/macro');
            const data = await res.json();
            renderMacro(data);
        } catch (err) {
            macroContent.innerHTML = '分析失敗';
        } finally {
            refreshMacroBtn.disabled = false;
        }
    }

    function renderMacro(data) {
        macroContent.innerHTML = `
            <div class="summary-box">
                <div style="font-weight:700; color:var(--accent-blue)">全球局勢總結</div>
                ${data.summary}
                <div class="macro-news">
                    <div class="macro-news-title">參考新聞來源</div>
                    <div class="macro-news-list">${data.news.map(n => `<div>• ${n}</div>`).join('')}</div>
                </div>
            </div>
            <div class="recommendations-box">
                <div class="rec-group">
                    <h3>短期受惠</h3>
                    ${data.mapping.short_term.map(item => renderRecCard(item)).join('')}
                </div>
                <div class="rec-group">
                    <h3>長期成長</h3>
                    ${data.mapping.long_term.map(item => renderRecCard(item)).join('')}
                </div>
            </div>
        `;
        macroContent.querySelectorAll('.quick-add-btn').forEach(btn => {
            btn.addEventListener('click', () => quickAddTicker(btn.dataset.symbol));
        });
    }

    function renderRecCard(item) {
        return `<div class="rec-card"><span>${item.sector}</span><div class="rec-tickers">${item.tickers.map(s => `<button class="quick-add-btn" data-symbol="${s}">${s}</button>`).join('')}</div></div>`;
    }

    function quickAddTicker(symbol) {
        // Simple search in allStockData or create dummy
        let stock = { symbol: symbol, name: symbol };
        handleSelection(true, stock);
        const cb = checkboxMap.get(symbol);
        if (cb) cb.checked = true;
    }
});
