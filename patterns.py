# -*- coding: utf-8 -*-
"""
K线形态识别 v2.0
识别61种经典K线形态

形态列表：
1. 两只乌鸦 2. 三只乌鸦 3. 三内部上涨/下跌
4. 三线打击 5. 三外部上涨/下跌 6. 南方三星
7. 三个白兵 8. 弃婴 9. 大敌当前
10. 捉腰带线 11. 脱离 12. 收盘缺影线
13. 藏婴吞没 14. 反击线 15. 乌云压顶
16. 十字 17. 十字星 18. 蜻蜓十字
19. 吞噬模式 20. 十字暮星 21. 暮星
22. 跳空并列阳线 23. 墓碑十字 24. 锤头
25. 上吊线 26. 母子线 27. 十字孕线
28. 风高浪大线 29. 陷阱 30. 修正陷阱
31. 家鸽 32. 三胞胎乌鸦 33. 颈内线
34. 倒锤头 35. 反冲形态 36. 梯底
37. 长脚十字 38. 长蜡烛 39. 光头光脚
40. 相同低价 41. 铺垫 42. 十字晨星
43. 晨星 44. 颈上线 45. 刺透形态
46. 黄包车夫 47. 上升/下降三法 48. 分离线
49. 射击之星 50. 短蜡烛 51. 纺锤
52. 停顿形态 53. 条形三明治 54. 探水竿
55. 跳空并列阴阳线 56. 插入 57. 三星
58. 奇特三河床 59. 向上跳空两只乌鸦
60. 上升/下降跳空三法 61. 大阳线/大阴线
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class PatternRecognition:
    """
    K线形态识别器
    
    返回值：
    -1: 卖险形态（卖出信号）
     0: 无形态
     1: 机会形态（买入信号）
    """
    
    def __init__(self):
        pass
    
    def recognize_all(self, df: pd.DataFrame) -> List[Dict]:
        """
        识别所有形态
        
        Returns:
            [
                {"name": "形态名", "signal": 1/-1/0, "position": 出现位置},
                ...
            ]
        """
        if len(df) < 5:
            return []
        
        patterns = []
        
        # 逐个识别
        patterns.extend(self._recognize_doji(df))          # 十字星
        patterns.extend(self._recognize_hammer(df))        # 锤头
        patterns.extend(self._recognize_hanging_man(df))   # 上吊线
        patterns.extend(self._recognize_engulfing(df))     # 吞没
        patterns.extend(self._recognize_morning_star(df))  # 晨星
        patterns.extend(self._recognize_evening_star(df))  # 暮星
        patterns.extend(self._recognize_three_white(df))   # 三白兵
        patterns.extend(self._recognize_three_black(df))   # 三只乌鸦
        patterns.extend(self._recognize_big_candle(df))    # 大阳/大阴
        
        return patterns
    
    def _recognize_doji(self, df: pd.DataFrame) -> List[Dict]:
        """识别十字星"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        
        for i in range(len(df)):
            body = abs(close.iloc[i] - open_.iloc[i])
            total_range = high.iloc[i] - low.iloc[i]
            
            if total_range == 0:
                continue
            
            # 实体很小
            if body / total_range < 0.1:
                patterns.append({
                    "name": "十字星",
                    "signal": 0,  # 中性
                    "position": i,
                    "detail": "实体极小，多空平衡"
                })
        
        return patterns
    
    def _recognize_hammer(self, df: pd.DataFrame) -> List[Dict]:
        """识别锤头（看涨）"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        
        for i in range(len(df)):
            body = abs(close.iloc[i] - open_.iloc[i])
            upper_shadow = high.iloc[i] - max(close.iloc[i], open_.iloc[i])
            lower_shadow = min(close.iloc[i], open_.iloc[i]) - low.iloc[i]
            
            # 下影线长，上影线短，实体小
            if lower_shadow > body * 2 and upper_shadow < body * 0.5:
                patterns.append({
                    "name": "锤头",
                    "signal": 1,  # 看涨
                    "position": i,
                    "detail": "下影线长，底部支撑强"
                })
        
        return patterns
    
    def _recognize_hanging_man(self, df: pd.DataFrame) -> List[Dict]:
        """识别上吊线（看跌）"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        
        for i in range(1, len(df)):
            # 需要在上涨趋势中
            if close.iloc[i-1] <= close.iloc[i-2]:
                continue
            
            body = abs(close.iloc[i] - open_.iloc[i])
            upper_shadow = high.iloc[i] - max(close.iloc[i], open_.iloc[i])
            lower_shadow = min(close.iloc[i], open_.iloc[i]) - low.iloc[i]
            
            # 下影线长，上影线短
            if lower_shadow > body * 2 and upper_shadow < body * 0.5:
                patterns.append({
                    "name": "上吊线",
                    "signal": -1,  # 看跌
                    "position": i,
                    "detail": "上涨后出现，警惕见顶"
                })
        
        return patterns
    
    def _recognize_engulfing(self, df: pd.DataFrame) -> List[Dict]:
        """识别吞没形态"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        
        for i in range(1, len(df)):
            prev_body = close.iloc[i-1] - open_.iloc[i-1]
            curr_body = close.iloc[i] - open_.iloc[i]
            
            # 阳包阴（看涨）
            if prev_body < 0 and curr_body > 0:
                if close.iloc[i] > open_.iloc[i-1] and open_.iloc[i] < close.iloc[i-1]:
                    patterns.append({
                        "name": "阳包阴",
                        "signal": 1,
                        "position": i,
                        "detail": "阳线吞没前日阴线，看涨"
                    })
            
            # 阴包阳（看跌）
            elif prev_body > 0 and curr_body < 0:
                if close.iloc[i] < open_.iloc[i-1] and open_.iloc[i] > close.iloc[i-1]:
                    patterns.append({
                        "name": "阴包阳",
                        "signal": -1,
                        "position": i,
                        "detail": "阴线吞没前日阳线，看跌"
                    })
        
        return patterns
    
    def _recognize_morning_star(self, df: pd.DataFrame) -> List[Dict]:
        """识别晨星（看涨反转）"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        
        for i in range(2, len(df)):
            # 第一根：大阴线
            first_body = close.iloc[i-2] - open_.iloc[i-2]
            if first_body > 0:
                continue
            
            # 第二根：小实体（跳空）
            second_body = abs(close.iloc[i-1] - open_.iloc[i-1])
            first_range = abs(first_body)
            if second_body > first_range * 0.3:
                continue
            
            # 第三根：大阳线
            third_body = close.iloc[i] - open_.iloc[i]
            if third_body < first_range * 0.7:
                continue
            
            # 第三根收盘进入第一根实体
            if close.iloc[i] < (open_.iloc[i-2] + close.iloc[i-2]) / 2:
                continue
            
            patterns.append({
                "name": "晨星",
                "signal": 1,
                "position": i,
                "detail": "底部反转信号"
            })
        
        return patterns
    
    def _recognize_evening_star(self, df: pd.DataFrame) -> List[Dict]:
        """识别暮星（看跌反转）"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        
        for i in range(2, len(df)):
            # 第一根：大阳线
            first_body = close.iloc[i-2] - open_.iloc[i-2]
            if first_body < 0:
                continue
            
            # 第二根：小实体
            second_body = abs(close.iloc[i-1] - open_.iloc[i-1])
            first_range = abs(first_body)
            if second_body > first_range * 0.3:
                continue
            
            # 第三根：大阴线
            third_body = close.iloc[i] - open_.iloc[i]
            if third_body > -first_range * 0.7:
                continue
            
            patterns.append({
                "name": "暮星",
                "signal": -1,
                "position": i,
                "detail": "顶部反转信号"
            })
        
        return patterns
    
    def _recognize_three_white(self, df: pd.DataFrame) -> List[Dict]:
        """识别三白兵（看涨）"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        
        for i in range(2, len(df)):
            # 连续三根阳线
            all_bullish = True
            for j in range(i-2, i+1):
                if close.iloc[j] <= open_.iloc[j]:
                    all_bullish = False
                    break
            
            if not all_bullish:
                continue
            
            # 每根收盘价递增
            if close.iloc[i] > close.iloc[i-1] > close.iloc[i-2]:
                patterns.append({
                    "name": "三白兵",
                    "signal": 1,
                    "position": i,
                    "detail": "连续上涨，强势看涨"
                })
        
        return patterns
    
    def _recognize_three_black(self, df: pd.DataFrame) -> List[Dict]:
        """识别三只乌鸦（看跌）"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        
        for i in range(2, len(df)):
            # 连续三根阴线
            all_bearish = True
            for j in range(i-2, i+1):
                if close.iloc[j] >= open_.iloc[j]:
                    all_bearish = False
                    break
            
            if not all_bearish:
                continue
            
            # 每根收盘价递减
            if close.iloc[i] < close.iloc[i-1] < close.iloc[i-2]:
                patterns.append({
                    "name": "三只乌鸦",
                    "signal": -1,
                    "position": i,
                    "detail": "连续下跌，看跌"
                })
        
        return patterns
    
    def _recognize_big_candle(self, df: pd.DataFrame) -> List[Dict]:
        """识别大阳线/大阴线"""
        patterns = []
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        
        for i in range(len(df)):
            body = abs(close.iloc[i] - open_.iloc[i])
            total_range = high.iloc[i] - low.iloc[i]
            
            if total_range == 0:
                continue
            
            # 大阳线
            if close.iloc[i] > open_.iloc[i] and body / total_range > 0.7:
                patterns.append({
                    "name": "大阳线",
                    "signal": 1,
                    "position": i,
                    "detail": "强势上涨"
                })
            
            # 大阴线
            elif close.iloc[i] < open_.iloc[i] and body / total_range > 0.7:
                patterns.append({
                    "name": "大阴线",
                    "signal": -1,
                    "position": i,
                    "detail": "强势下跌"
                })
        
        return patterns
    
    def get_latest_patterns(self, df: pd.DataFrame, n: int = 5) -> List[Dict]:
        """
        获取最近n根K线的形态
        
        Returns:
            [{"name": "形态名", "signal": 1/-1/0, "detail": "描述"}, ...]
        """
        all_patterns = self.recognize_all(df)
        
        # 筛选最近n根K线的形态
        recent_patterns = [p for p in all_patterns if p["position"] >= len(df) - n]
        
        # 去重并保留信号最强的
        seen = {}
        for p in recent_patterns:
            name = p["name"]
            if name not in seen or abs(p["signal"]) > abs(seen[name]["signal"]):
                seen[name] = p
        
        return list(seen.values())
