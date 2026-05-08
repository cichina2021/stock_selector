# -*- coding: utf-8 -*-
"""
智能选股引擎 v3.0
整合策略、形态识别、价位建议
"""
import pandas as pd
from typing import Dict, List, Optional
import logging

from strategies import ClassicStrategies
from patterns import PatternRecognition
from datasource import DataSource
from price_advisor import PriceAdvisor

logger = logging.getLogger(__name__)


class StockSelector:
    """
    智能选股引擎 v3.0
    
    功能：
    1. 单股综合分析（含价位建议）
    2. 股票池批量扫描
    3. 板块热点选股
    """

    def __init__(self):
        self.strategies = ClassicStrategies()
        self.patterns = PatternRecognition()
        self.data = DataSource()
        self.price = PriceAdvisor()

        # 加载股票池
        self.pool_codes = []
        self.pool_names = {}
        self._load_stock_pool()

    # ════════════════════════════════════════
    #  内置股票池（108只，打包后无需外部文件）
    # ════════════════════════════════════════
    BUILTIN_POOL = {
        "600016": "民生银行", "600032": "浙江新能", "600039": "四川路桥", "600292": "电投水电",
        "600332": "白云山", "600353": "旭光电子", "600392": "盛和资源", "600410": "华胜天成",
        "600444": "国机通用", "600468": "百利电气", "600478": "科力远", "600487": "亨通光电",
        "600498": "烽火通信", "600506": "统一股份", "600522": "中天科技", "600550": "保变电气",
        "600577": "精达股份", "600601": "方正科技", "600602": "云赛智联", "600673": "东阳光",
        "600690": "海尔智家", "600789": "鲁抗医药", "600810": "神马股份", "600859": "王府井",
        "600877": "电科芯片", "600993": "马应龙", "601086": "国芳集团", "601099": "太平洋",
        "601108": "财通证券", "601138": "工业富联", "601162": "天风证券", "601606": "长城军工",
        "601669": "中国电建", "601800": "中国交建", "601901": "方正证券", "601933": "永辉超市",
        "603072": "天和磁材", "603118": "共进股份", "603131": "上海沪工", "603212": "赛伍技术",
        "603220": "中贝通信", "603359": "东珠生态", "603636": "南威软件", "603686": "福龙马",
        "603712": "七一二", "603788": "宁波高发", "603928": "兴业股份", "605033": "美邦股份",
        "000002": "万科A", "000025": "特力A", "000063": "中兴通讯", "000158": "常山北明",
        "000333": "美的集团", "000410": "沈阳机床", "000555": "神州信息", "000561": "烽火电子",
        "000564": "供销大集", "000625": "长安汽车", "000670": "盈方微", "000682": "东方电子",
        "000859": "国风新材", "000880": "潍柴重机", "000901": "航天科技", "000905": "厦门港务",
        "000936": "华西股份", "001287": "中电港", "002015": "协鑫能科", "002074": "国轩高科",
        "002083": "孚日股份", "002094": "青岛金王", "002104": "恒宝股份", "002117": "东港股份",
        "002124": "天邦食品", "002130": "沃尔核材", "002131": "利欧股份", "002165": "红宝丽",
        "002173": "创新医疗", "002184": "海得控制", "002185": "华天科技", "002189": "中光学",
        "002209": "达意隆", "002212": "天融信", "002241": "歌尔股份", "002261": "拓维信息",
        "002265": "建设工业", "002276": "万马股份", "002278": "神开股份", "002279": "久其软件",
        "002366": "融发核电", "002369": "卓翼科技", "002415": "海康威视", "002465": "海格通信",
        "002472": "双环传动", "002474": "榕基软件", "002510": "天汽模", "002512": "ST达华",
        "002520": "日发精机", "002539": "云图控股", "002594": "比亚迪", "002611": "东方精工",
        "002639": "雪人集团", "002729": "好利科技", "002730": "电光科技", "002861": "瀛通通讯",
        "002927": "泰永长征", "002946": "新乳业", "003015": "日久光电", "159525": "红利低波ETF富国",
    }

    def _load_stock_pool(self):
        """加载自选股票池（内置优先 → 外部文件覆盖）"""
        import os

        # 1. 先加载内置股票池
        self.pool_codes = list(self.BUILTIN_POOL.keys())
        self.pool_names = dict(self.BUILTIN_POOL)
        logger.info(f"内置股票池: {len(self.pool_codes)}只")

        # 2. 尝试从外部文件追加（开发环境用）
        pool_files = [
            os.path.expanduser("~/.qclaw/workspace/stock_pool.md"),
            "/Volumes/macos/stock_analysis/自选股详细分析/原始数据/实时行情_20260412_1039.csv",
        ]

        for pf in pool_files:
            if not os.path.exists(pf):
                continue
            try:
                if pf.endswith(".csv"):
                    import csv
                    with open(pf, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            code = row.get("代码", "").strip()
                            name = row.get("名称", "").strip()
                            if code and len(code) == 6 and code not in self.pool_names:
                                self.pool_codes.append(code)
                                self.pool_names[code] = name
                else:
                    with open(pf, "r", encoding="utf-8") as f:
                        for line in f:
                            stripped = line.strip()
                            if not stripped or stripped.startswith("#") or stripped.startswith(">"):
                                continue
                            if "代码" in stripped or "---" in stripped:
                                continue
                            parts = [p.strip() for p in stripped.split("|")]
                            code_parts = [p for p in parts if p and len(p) == 6 and p.isdigit()]
                            if code_parts:
                                code = code_parts[0]
                                if code not in self.pool_names:
                                    name_idx = parts.index(code) + 1
                                    name = parts[name_idx].strip() if name_idx < len(parts) else code
                                    self.pool_codes.append(code)
                                    self.pool_names[code] = name
                    logger.info(f"从{pf}追加了股票")
                    break
            except Exception as e:
                logger.warning(f"加载外部股票池失败 {pf}: {e}")

    def analyze(self, code: str, name: str = None) -> Dict:
        """
        单股深度分析（含价位建议）
        
        Returns:
            完整分析结果，包含strategies/patterns/price_advice等
        """
        df = self.data.get_kline(code, period="daily", count=300)
        quotes = self.data.get_realtime([code])
        quote = quotes[0] if quotes else {}

        if df is None or len(df) < 60:
            return {
                "code": code,
                "name": name or quote.get("name", code),
                "error": "数据不足"
            }

        stock_name = name or self.pool_names.get(code, quote.get("name", code))

        # 策略分析
        strategy_result = self.strategies.comprehensive_select(df, quote)

        # 形态识别
        pattern_result = self.patterns.get_latest_patterns(df, n=10)

        # 价位建议
        price_result = self.price.analyze(df, quote)

        # 综合评分（策略+形态）
        base_score = strategy_result["total_score"]
        pattern_bonus = sum(5 if p["signal"] == 1 else (-5 if p["signal"] == -1 else 0) for p in pattern_result)
        total_score = max(0, min(100, base_score + pattern_bonus))

        # 操作建议（结合价位）
        if total_score >= 75 and price_result["risk_reward_ratio"] >= 2:
            suggestion = "强烈买入"
        elif total_score >= 60 and price_result["risk_reward_ratio"] >= 1.5:
            suggestion = "逢低买入"
        elif total_score >= 45:
            suggestion = "关注"
        else:
            suggestion = "观望"

        # 总结
        matched = [s[0] for s in strategy_result["strategies"] if s[1]]
        bullish_p = [p["name"] for p in pattern_result if p["signal"] == 1]
        bearish_p = [p["name"] for p in pattern_result if p["signal"] == -1]

        parts = []
        if matched:
            parts.append(f"入选: {', '.join(matched[:4])}")
        if bullish_p:
            parts.append(f"看涨: {', '.join(bullish_p[:3])}")
        if bearish_p:
            parts.append(f"看跌: {', '.join(bearish_p[:2])}")
        
        buy_zone = price_result.get("buy_zone", {})
        sell_zone = price_result.get("sell_zone", {})
        if buy_zone.get("low"):
            parts.append(f"买入区间: {buy_zone['low']}-{buy_zone['high']}")

        summary = " | ".join(parts) if parts else "无明确信号"

        return {
            "code": code,
            "name": stock_name,
            "price": quote.get("price", round(df.iloc[-1]["close"], 2)),
            "change_pct": round(quote.get("change_pct", 0), 2),
            "volume": quote.get("volume", 0),
            "amount": quote.get("amount", 0),
            "strategies": strategy_result["strategies"],
            "patterns": pattern_result,
            "total_score": round(total_score, 1),
            "matched_count": strategy_result["matched_count"],
            "suggestion": suggestion,
            "summary": summary,
            **price_result,
        }

    def scan_pool(self, top_n: int = 30) -> List[Dict]:
        """
        扫描整个股票池
        
        Returns:
            按评分排序的结果列表
        """
        results = []

        for i, code in enumerate(self.pool_codes):
            try:
                logger.info(f"[{i+1}/{len(self.pool_codes)}] 扫描 {code} {self.pool_names.get(code,'')}")
                result = self.analyze(code)

                if "error" not in result:
                    results.append(result)
                    
                # 避免请求过快
                import time
                time.sleep(0.15)

            except Exception as e:
                logger.debug(f"扫描{code}失败: {e}")

        # 按评分排序
        results.sort(key=lambda x: x["total_score"], reverse=True)

        return results[:top_n]

    def get_pool_realtime(self, include_hot_sectors: bool = True) -> List[Dict]:
        """
        获取股票池实时行情（快速，只获取行情不分析）

        Args:
            include_hot_sectors: 是否包含热门板块个股

        Returns:
            [{"code","name","price","change_pct","amount","source"}, ...]
            source: "pool"=自选股池, "hot_sector"=热门板块
        """
        if not self.pool_codes:
            return []

        all_quotes = []

        # ── 1. 自选股池 ──
        batch_size = 50
        for i in range(0, len(self.pool_codes), batch_size):
            batch = self.pool_codes[i:i + batch_size]
            try:
                quotes = self.data.get_realtime(batch)
                for q in quotes:
                    q["source"] = "pool"
                    code = q.get("code", "")
                    if not q.get("name") and code in self.pool_names:
                        q["name"] = self.pool_names[code]
                all_quotes.extend(quotes)
            except Exception as e:
                logger.warning(f"获取自选股实时行情失败: {e}")

        # ── 2. 热门板块个股 ──
        if include_hot_sectors:
            try:
                hot_codes = self.data.get_hot_sector_stocks(top_n=15, per_sector_n=5)
                # 只取不在自选股池中的
                new_codes = [c for c in hot_codes if c not in set(self.pool_codes)]
                # 最多加20只
                new_codes = new_codes[:20]

                if new_codes:
                    for batch in [new_codes[i:i+50] for i in range(0, len(new_codes), 50)]:
                        try:
                            hot_quotes = self.data.get_realtime(batch)
                            for q in hot_quotes:
                                q["source"] = "hot_sector"
                            all_quotes.extend(hot_quotes)
                        except Exception as e:
                            logger.warning(f"获取热门板块行情失败: {e}")

            except Exception as e:
                logger.warning(f"获取热门板块失败: {e}")

        # 按涨幅排序
        all_quotes.sort(key=lambda x: x.get("change_pct", 0), reverse=True)

        return all_quotes

    def get_sectors(self) -> List[Dict]:
        """获取板块热点"""
        industry = self.data.get_sectors("industry", top_n=15)
        concept = self.data.get_sectors("concept", top_n=15)
        all_s = (industry + concept)
        all_s.sort(key=lambda x: x["change_pct"], reverse=True)
        return all_s[:25]
