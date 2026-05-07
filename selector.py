# -*- coding: utf-8 -*-
"""
智能选股引擎 v2.0
整合所有策略和形态识别
"""
import pandas as pd
from typing import Dict, List, Optional
import logging

from strategies import ClassicStrategies
from patterns import PatternRecognition
from datasource import DataSource

logger = logging.getLogger(__name__)


class StockSelector:
    """
    智能选股引擎
    
    功能：
    1. 单股综合分析
    2. 批量筛选
    3. 板块热点选股
    """
    
    def __init__(self):
        self.strategies = ClassicStrategies()
        self.patterns = PatternRecognition()
        self.data = DataSource()
    
    def analyze(self, code: str, name: str = None) -> Dict:
        """
        单股综合分析
        
        Returns:
            {
                "code": "代码",
                "name": "名称",
                "price": 价格,
                "change_pct": 涨幅,
                "strategies": [...],  # 策略结果
                "patterns": [...],    # 形态识别
                "total_score": 综合评分,
                "suggestion": 操作建议,
                "summary": 总结,
            }
        """
        # 获取数据
        df = self.data.get_kline(code, period="daily", count=300)
        quotes = self.data.get_realtime([code])
        quote = quotes[0] if quotes else {}
        
        if df is None or len(df) < 60:
            return {
                "code": code,
                "name": name or code,
                "error": "数据不足"
            }
        
        # 策略分析
        strategy_result = self.strategies.comprehensive_select(df, quote)
        
        # 形态识别
        pattern_result = self.patterns.get_latest_patterns(df, n=10)
        
        # 综合评分
        base_score = strategy_result["total_score"]
        
        # 形态加分
        pattern_score = 0
        for p in pattern_result:
            if p["signal"] == 1:
                pattern_score += 5
            elif p["signal"] == -1:
                pattern_score -= 5
        
        total_score = max(0, min(100, base_score + pattern_score))
        
        # 操作建议
        if total_score >= 75:
            suggestion = "强烈买入"
        elif total_score >= 60:
            suggestion = "逢低买入"
        elif total_score >= 45:
            suggestion = "关注"
        else:
            suggestion = "观望"
        
        # 总结
        matched_strategies = [s[0] for s in strategy_result["strategies"] if s[1]]
        bullish_patterns = [p["name"] for p in pattern_result if p["signal"] == 1]
        bearish_patterns = [p["name"] for p in pattern_result if p["signal"] == -1]
        
        summary_parts = []
        if matched_strategies:
            summary_parts.append(f"入选策略: {', '.join(matched_strategies[:3])}")
        if bullish_patterns:
            summary_parts.append(f"看涨形态: {', '.join(bullish_patterns)}")
        if bearish_patterns:
            summary_parts.append(f"看跌形态: {', '.join(bearish_patterns)}")
        
        summary = " | ".join(summary_parts) if summary_parts else "无明确信号"
        
        return {
            "code": code,
            "name": name or quote.get("name", code),
            "price": quote.get("price", df.iloc[-1]["close"]),
            "change_pct": quote.get("change_pct", 0),
            "strategies": strategy_result["strategies"],
            "patterns": pattern_result,
            "total_score": round(total_score, 1),
            "matched_count": strategy_result["matched_count"],
            "suggestion": suggestion,
            "summary": summary,
        }
    
    def screen_pool(self, codes: List[str], top_n: int = 20) -> List[Dict]:
        """
        批量筛选股票池
        
        Returns:
            按评分排序的结果列表
        """
        results = []
        
        for i, code in enumerate(codes):
            try:
                logger.info(f"筛选 {i+1}/{len(codes)}: {code}")
                result = self.analyze(code)
                
                if "error" not in result and result["total_score"] >= 50:
                    results.append(result)
            except Exception as e:
                logger.debug(f"筛选{code}失败: {e}")
        
        # 按评分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)
        
        return results[:top_n]
    
    def select_by_sector(self, top_n: int = 10) -> List[Dict]:
        """
        板块热点选股
        
        逻辑：
        1. 找出涨幅前5的板块
        2. 从这些板块中筛选技术形态好的股票
        """
        # 获取热点板块
        industry = self.data.get_sectors("industry", top_n=10)
        concept = self.data.get_sectors("concept", top_n=10)
        
        # 合并
        hot_sectors = (industry[:5] + concept[:5])
        hot_sectors.sort(key=lambda x: x["change_pct"], reverse=True)
        
        # TODO: 获取板块成分股并筛选
        # 这里简化处理，返回板块信息
        results = []
        for s in hot_sectors[:top_n]:
            results.append({
                "sector": s["name"],
                "change_pct": s["change_pct"],
                "lead_stock": s["lead_stock"],
                "type": "热点板块"
            })
        
        return results
