# -*- coding: utf-8 -*-
"""
Web界面 v2.0
专业级金融终端风格
"""

def get_html() -> str:
    return """<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>智能选股系统 v2.0</title>
<style>
:root, [data-theme="dark"] {
    --bg-primary: #080c14;
    --bg-secondary: #0f1923;
    --bg-card: #141e2b;
    --text-primary: #e8edf3;
    --text-secondary: #8899aa;
    --accent-blue: #3b82f6;
    --accent-cyan: #06b6d4;
    --price-up: #ef4444;
    --price-down: #22c55e;
}

[data-theme="light"] {
    --bg-primary: #f0f4f8;
    --bg-secondary: #ffffff;
    --bg-card: #ffffff;
    --text-primary: #1e293b;
    --text-secondary: #64748b;
    --accent-blue: #2563eb;
    --accent-cyan: #0891b2;
    --price-up: #dc2626;
    --price-down: #16a34a;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
}

.header {
    background: linear-gradient(135deg, #0c1622 0%, #111d2e 100%);
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding: 0 24px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.logo {
    font-size: 18px;
    font-weight: 700;
    color: #f0f6fc;
    display: flex;
    align-items: center;
    gap: 10px;
}

.logo-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 900; color: #fff;
}

.main-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
}

.card {
    background: var(--bg-card);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    margin-bottom: 20px;
    overflow: hidden;
}

.card-header {
    padding: 14px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.card-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-secondary);
}

.card-body { padding: 20px; }

.search-box {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.search-input {
    flex: 1;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 14px;
}

.search-btn {
    padding: 12px 24px;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
    border: none;
    border-radius: 8px;
    color: #fff;
    font-weight: 600;
    cursor: pointer;
}

.search-btn:hover { transform: scale(1.05); }

.result-card {
    background: var(--bg-secondary);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
    border-left: 4px solid var(--accent-blue);
}

.result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}

.result-code {
    font-weight: 700;
    font-size: 15px;
}

.result-name {
    color: var(--text-secondary);
    font-size: 12px;
    margin-left: 8px;
}

.result-score {
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
    color: #fff;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 700;
}

.result-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    font-size: 12px;
    color: var(--text-secondary);
}

.result-strategies {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px dashed rgba(255,255,255,0.1);
    font-size: 12px;
}

.strategy-tag {
    display: inline-block;
    padding: 2px 8px;
    margin: 2px;
    border-radius: 4px;
    font-size: 11px;
}

.strategy-tag.matched {
    background: rgba(34,197,94,0.15);
    color: #4ade80;
}

.strategy-tag.unmatched {
    background: rgba(100,116,139,0.15);
    color: #94a3b8;
}

.result-suggestion {
    margin-top: 8px;
    padding: 8px 12px;
    background: rgba(59,130,246,0.1);
    border-radius: 6px;
    font-size: 12px;
    color: var(--accent-blue);
    font-weight: 500;
}

.sector-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 12px;
}

.sector-card {
    background: var(--bg-secondary);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 14px;
    cursor: pointer;
    transition: all 0.2s;
}

.sector-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.sector-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
}

.sector-name { font-weight: 600; }
.sector-change { font-weight: 700; }
.price-up { color: var(--price-up); }
.price-down { color: var(--price-down); }

.empty-state {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
}

.loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px;
}

.loading::after {
    content: '';
    width: 30px;
    height: 30px;
    border: 3px solid var(--accent-blue);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<header class="header">
    <div class="logo">
        <div class="logo-icon">选</div>
        智能选股系统 v2.0
    </div>
    <div style="color: var(--text-secondary); font-size: 13px;">
        11种经典策略 | 61种K线形态 | 板块热点共振
    </div>
</header>

<main class="main-content">
    <!-- 搜索区 -->
    <div class="card">
        <div class="card-header">
            <div class="card-title">🔍 股票分析</div>
        </div>
        <div class="card-body">
            <div class="search-box">
                <input type="text" class="search-input" id="codeInput" placeholder="输入股票代码，如：002539">
                <button class="search-btn" onclick="analyzeStock()">分析</button>
            </div>
            <div id="analysisResult"></div>
        </div>
    </div>
    
    <!-- 板块热点 -->
    <div class="card">
        <div class="card-header">
            <div class="card-title">🔥 板块热点</div>
            <button style="background: rgba(255,255,255,0.1); border: none; padding: 6px 12px; border-radius: 6px; color: var(--text-secondary); cursor: pointer;" onclick="loadSectors()">刷新</button>
        </div>
        <div class="card-body">
            <div class="sector-grid" id="sectorGrid">
                <div class="loading"></div>
            </div>
        </div>
    </div>
    
    <!-- 策略说明 -->
    <div class="card">
        <div class="card-header">
            <div class="card-title">📊 策略说明</div>
        </div>
        <div class="card-body" style="font-size: 13px; color: var(--text-secondary); line-height: 1.8;">
            <p><strong>11种经典选股策略：</strong></p>
            <p>1. 放量上涨 - 量价齐升，资金介入</p>
            <p>2. 均线多头 - 趋势向上，MA5>MA10>MA20>MA30</p>
            <p>3. 停机坪 - 涨停后强势整理，回调买入机会</p>
            <p>4. 回踩年线 - 长期支撑确认，缩量回踩</p>
            <p>5. 突破平台 - 横盘整理后放量突破</p>
            <p>6. 无大幅回撤 - 趋势稳健，无暴跌</p>
            <p>7. 海龟交易法则 - 创新高买入</p>
            <p>8. 高而窄的旗形 - 强势形态，连续涨停后整理</p>
            <p>9. MACD金叉 - 经典技术信号</p>
            <p>10. KDJ超卖 - 短线反弹机会</p>
            <p>11. 多因子综合 - 量化评分</p>
            <p style="margin-top: 12px;"><strong>61种K线形态识别：</strong>十字星、锤头、吞没、晨星、暮星、三白兵、三只乌鸦等</p>
        </div>
    </div>
</main>

<script>
async function analyzeStock() {
    const code = document.getElementById('codeInput').value.trim();
    if (!code) {
        alert('请输入股票代码');
        return;
    }
    
    const resultDiv = document.getElementById('analysisResult');
    resultDiv.innerHTML = '<div class="loading"></div>';
    
    try {
        const resp = await fetch(`/api/analyze?code=${code}`);
        const data = await resp.json();
        
        if (data.error) {
            resultDiv.innerHTML = `<div class="empty-state">${data.error}</div>`;
            return;
        }
        
        // 渲染结果
        const strategies = data.strategies || [];
        const matchedStrategies = strategies.filter(s => s[1]);
        const unmatchedStrategies = strategies.filter(s => !s[1]);
        
        let html = `
            <div class="result-card">
                <div class="result-header">
                    <div>
                        <span class="result-code">${data.code}</span>
                        <span class="result-name">${data.name}</span>
                    </div>
                    <span class="result-score">${data.total_score}分</span>
                </div>
                <div class="result-details">
                    <div>价格: <span class="${data.change_pct >= 0 ? 'price-up' : 'price-down'}">${data.price.toFixed(2)}</span></div>
                    <div>涨跌: <span class="${data.change_pct >= 0 ? 'price-up' : 'price-down'}">${data.change_pct >= 0 ? '+' : ''}${data.change_pct.toFixed(2)}%</span></div>
                    <div>入选策略: ${data.matched_count}个</div>
                    <div>形态: ${(data.patterns || []).length}个</div>
                </div>
                <div class="result-strategies">
                    <div style="margin-bottom: 8px;">策略结果：</div>
                    ${matchedStrategies.map(s => `<span class="strategy-tag matched">${s[0]}(${s[3]}分)</span>`).join('')}
                    ${unmatchedStrategies.slice(0, 5).map(s => `<span class="strategy-tag unmatched">${s[0]}</span>`).join('')}
                </div>
                <div class="result-suggestion">${data.suggestion} - ${data.summary}</div>
            </div>
        `;
        
        resultDiv.innerHTML = html;
        
    } catch (e) {
        resultDiv.innerHTML = `<div class="empty-state">分析失败: ${e.message}</div>`;
    }
}

async function loadSectors() {
    const grid = document.getElementById('sectorGrid');
    grid.innerHTML = '<div class="loading"></div>';
    
    try {
        const resp = await fetch('/api/sectors');
        const data = await resp.json();
        
        if (!data || data.length === 0) {
            grid.innerHTML = '<div class="empty-state">暂无数据</div>';
            return;
        }
        
        grid.innerHTML = data.map(s => `
            <div class="sector-card">
                <div class="sector-header">
                    <span class="sector-name">${s.name}</span>
                    <span class="sector-change ${s.change_pct >= 0 ? 'price-up' : 'price-down'}">${s.change_pct >= 0 ? '+' : ''}${s.change_pct.toFixed(2)}%</span>
                </div>
                <div style="font-size: 11px; color: var(--text-secondary);">
                    领涨: ${s.lead_stock || '--'} | 成交: ${s.amount.toFixed(1)}亿
                </div>
            </div>
        `).join('');
        
    } catch (e) {
        grid.innerHTML = '<div class="empty-state">加载失败</div>';
    }
}

// 初始化
loadSectors();
</script>

</body>
</html>
"""
