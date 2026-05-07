# -*- coding: utf-8 -*-
"""
经典选股策略库 v2.0
来自GitHub高准确率项目（InStock等）

策略列表：
1. 放量上涨 - 量价齐升，资金介入
2. 均线多头 - 趋势向上
3. 停机坪 - 强势整理后突破
4. 回踩年线 - 长期支撑确认
5. 突破平台 - 横盘突破
6. 无大幅回撤 - 趋势稳健
7. 海龟交易法则 - 创新高买入
8. 高而窄的旗形 - 强势形态
9. MACD金叉 - 经典技术信号
10. KDJ超卖反弹 - 短线机会
11. 多因子综合 - 量化选股
"""
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ClassicStrategies:
    """
    经典选股策略集合
    
    每个策略返回：(是否入选, 入选理由, 评分)
    """
    
    def __init__(self):
        pass
    
    # ==================== 策略1: 放量上涨 ====================
    def volume_breakout(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        放量上涨策略
        
        条件：
        1. 当日上涨且涨幅 < 2%（避免追高）
        2. 成交额 >= 2亿（流动性充足）
        3. 量比 >= 2（明显放量）
        
        Returns:
            (入选, 理由, 评分)
        """
        if len(df) < 6:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        volume = df["volume"].astype(float)
        amount = df.get("amount", volume * close)  # 成交额
        
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        last_amount = amount.iloc[-1]
        
        # 涨幅
        change_pct = (last_close / prev_close - 1) * 100
        
        # 量比
        vol_ma5 = volume.iloc[-6:-1].mean()
        vol_ratio = volume.iloc[-1] / vol_ma5 if vol_ma5 > 0 else 1
        
        # 判断条件
        reasons = []
        score = 0
        
        # 条件1: 上涨但涨幅适中
        if 0 < change_pct < 2:
            reasons.append(f"涨幅{change_pct:.2f}%")
            score += 30
        elif change_pct >= 2:
            reasons.append(f"涨幅{change_pct:.2f}%（偏大）")
            score += 10
        else:
            return False, "未上涨", 0
        
        # 条件2: 成交额充足
        if last_amount >= 2e8:  # 2亿
            reasons.append(f"成交额{last_amount/1e8:.1f}亿")
            score += 30
        else:
            return False, f"成交额不足（{last_amount/1e8:.1f}亿）", 0
        
        # 条件3: 量比
        if vol_ratio >= 2:
            reasons.append(f"量比{vol_ratio:.1f}")
            score += 40
        elif vol_ratio >= 1.5:
            reasons.append(f"量比{vol_ratio:.1f}（偏小）")
            score += 20
        else:
            return False, f"量比不足（{vol_ratio:.1f}）", 0
        
        reason = "放量上涨: " + " | ".join(reasons)
        return True, reason, min(100, score)
    
    # ==================== 策略2: 均线多头 ====================
    def ma_bullish(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        均线多头排列
        
        条件：
        1. MA5 > MA10 > MA20 > MA30（完美多头）
        2. MA30向上（趋势向上）
        3. 当日MA30比30日前MA30上涨20%以上（趋势强度）
        """
        if len(df) < 60:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        
        # 计算均线
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma30 = close.rolling(30).mean()
        
        last_ma5 = ma5.iloc[-1]
        last_ma10 = ma10.iloc[-1]
        last_ma20 = ma20.iloc[-1]
        last_ma30 = ma30.iloc[-1]
        prev_ma30 = ma30.iloc[-30]
        
        reasons = []
        score = 0
        
        # 条件1: 多头排列
        if last_ma5 > last_ma10 > last_ma20 > last_ma30:
            reasons.append("完美多头排列")
            score += 50
        elif last_ma5 > last_ma10 > last_ma20:
            reasons.append("多头排列（MA30未跟上）")
            score += 30
        else:
            return False, "均线非多头排列", 0
        
        # 条件2: MA30向上
        if last_ma30 > prev_ma30:
            growth = (last_ma30 / prev_ma30 - 1) * 100
            reasons.append(f"MA30向上{growth:.1f}%")
            score += 20
            
            # 条件3: 趋势强度
            if growth >= 20:
                reasons.append("趋势强劲")
                score += 30
            elif growth >= 10:
                reasons.append("趋势中等")
                score += 15
        else:
            return False, "MA30向下", 0
        
        reason = "均线多头: " + " | ".join(reasons)
        return True, reason, min(100, score)
    
    # ==================== 策略3: 停机坪 ====================
    def helipad(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        停机坪形态
        
        条件：
        1. 最近15日有放量涨停（涨幅>9.5%）
        2. 涨停后连续3日高开高走，涨幅温和（<3%）
        3. 形态像直升机停机坪，强势整理
        
        这是强势股回调买入机会
        """
        if len(df) < 20:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        volume = df["volume"].astype(float)
        
        # 找最近15日的涨停日
        changes = close.pct_change() * 100
        vol_ma5 = volume.rolling(5).mean()
        
        zt_day = None
        for i in range(-15, -3):
            if i < -len(df):
                continue
            change = changes.iloc[i]
            vol_ratio = volume.iloc[i] / vol_ma5.iloc[i-1] if vol_ma5.iloc[i-1] > 0 else 1
            
            # 涨停且放量
            if change >= 9.5 and vol_ratio >= 1.5:
                zt_day = i
                break
        
        if zt_day is None:
            return False, "近15日无涨停", 0
        
        # 检查涨停后3日
        reasons = [f"涨停日{changes.iloc[zt_day]:.1f}%"]
        score = 40
        
        valid_days = 0
        for j in range(zt_day + 1, min(zt_day + 4, 0)):
            # 高开
            if open_.iloc[j] <= close.iloc[j-1]:
                continue
            # 高走
            if close.iloc[j] <= open_.iloc[j]:
                continue
            # 涨幅温和
            daily_change = (close.iloc[j] / close.iloc[j-1] - 1) * 100
            if daily_change >= 3:
                continue
            
            valid_days += 1
        
        if valid_days >= 2:
            reasons.append(f"涨停后{valid_days}日高开高走")
            score += 40
            reason = "停机坪形态: " + " | ".join(reasons)
            return True, reason, min(100, score)
        else:
            return False, "涨停后走势不符合", 0
    
    # ==================== 策略4: 回踩年线 ====================
    def pullback_to_ma250(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        回踩年线（MA250）
        
        条件：
        1. 前段从年线下方向上突破
        2. 后段在年线上方运行
        3. 回踩年线时缩量
        4. 当前距年线不远（回踩确认）
        """
        if len(df) < 300:
            return False, "数据不足（需300日）", 0
        
        close = df["close"].astype(float)
        volume = df["volume"].astype(float)
        
        ma250 = close.rolling(250).mean()
        
        # 找最近60日最高点
        recent_high_idx = close.iloc[-60:].idxmax()
        recent_high = close.iloc[recent_high_idx]
        recent_high_pos = len(df) - 1 - recent_high_idx
        
        if recent_high_pos <= 0 or recent_high_pos >= 60:
            return False, "最高点位置不合适", 0
        
        reasons = []
        score = 0
        
        # 前段：检查是否从年线下突破
        before_high = close.iloc[:recent_high_idx]
        before_ma250 = ma250.iloc[:recent_high_idx]
        
        # 找突破点
        cross_up = False
        for i in range(len(before_high) - 1):
            if before_high.iloc[i] < before_ma250.iloc[i] and \
               before_high.iloc[i+1] > before_ma250.iloc[i+1]:
                cross_up = True
                break
        
        if cross_up:
            reasons.append("突破年线")
            score += 30
        else:
            return False, "未突破年线", 0
        
        # 后段：在年线上方运行
        after_high = close.iloc[recent_high_idx:]
        after_ma250 = ma250.iloc[recent_high_idx:]
        
        if (after_high > after_ma250).all():
            reasons.append("年线上方运行")
            score += 30
        else:
            return False, "跌破年线", 0
        
        # 回踩缩量
        vol_at_high = volume.iloc[recent_high_idx]
        vol_now = volume.iloc[-1]
        if vol_at_high / vol_now > 2:
            reasons.append("回踩缩量")
            score += 20
        
        # 当前距年线距离
        last_close = close.iloc[-1]
        last_ma250 = ma250.iloc[-1]
        distance = (last_close / last_ma250 - 1) * 100
        
        if 0 < distance < 10:
            reasons.append(f"距年线{distance:.1f}%")
            score += 20
        
        reason = "回踩年线: " + " | ".join(reasons)
        return True, reason, min(100, score)
    
    # ==================== 策略5: 突破平台 ====================
    def break_platform(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        突破平台整理
        
        条件：
        1. 60日内某日放量突破60日均线
        2. 突破前在均线附近震荡（偏离-5%~20%）
        3. 当日或近期确认突破
        """
        if len(df) < 80:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        volume = df["volume"].astype(float)
        
        ma60 = close.rolling(60).mean()
        vol_ma5 = volume.rolling(5).mean()
        
        # 找突破日
        break_day = None
        for i in range(-60, -5):
            if i < -len(df):
                continue
            
            # 放量突破MA60
            if close.iloc[i] > ma60.iloc[i] > open_.iloc[i]:
                vol_ratio = volume.iloc[i] / vol_ma5.iloc[i-1] if vol_ma5.iloc[i-1] > 0 else 1
                if vol_ratio >= 1.5:
                    break_day = i
                    break
        
        if break_day is None:
            return False, "未找到突破日", 0
        
        reasons = []
        score = 40
        
        # 检查突破前震荡
        before_break = close.iloc[break_day-30:break_day]
        before_ma60 = ma60.iloc[break_day-30:break_day]
        
        deviation = abs((before_break / before_ma60 - 1) * 100)
        if deviation.max() < 20 and deviation.min() > -5:
            reasons.append("平台整理充分")
            score += 30
        
        # 当前是否站稳
        last_close = close.iloc[-1]
        last_ma60 = ma60.iloc[-1]
        if last_close > last_ma60 * 1.02:
            reasons.append("站稳MA60")
            score += 30
        
        reason = "突破平台: " + " | ".join(reasons)
        return True, reason, min(100, score)
    
    # ==================== 策略6: 无大幅回撤 ====================
    def no_big_drawdown(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        无大幅回撤（趋势稳健）
        
        条件：
        1. 60日涨幅 < 60%（避免追高）
        2. 无单日跌幅 > 7%
        3. 无两日累计跌幅 > 10%
        4. 无高开低走 > 7%
        """
        if len(df) < 60:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        open_ = df["open"].astype(float)
        
        # 60日涨幅
        change_60d = (close.iloc[-1] / close.iloc[-60] - 1) * 100
        if change_60d >= 60:
            return False, f"60日涨幅过大（{change_60d:.1f}%）", 0
        
        reasons = [f"60日涨{change_60d:.1f}%"]
        score = 30
        
        # 检查回撤
        changes = close.pct_change() * 100
        
        # 单日跌幅
        if changes.iloc[-60:].min() < -7:
            return False, "有单日跌幅>7%", 0
        
        # 两日累计跌幅
        for i in range(-60, -1):
            two_day_change = (close.iloc[i+2] / close.iloc[i] - 1) * 100
            if two_day_change < -10:
                return False, "有两日跌幅>10%", 0
        
        # 高开低走
        for i in range(-60, 0):
            if open_.iloc[i] > close.iloc[i-1]:  # 高开
                if close.iloc[i] < open_.iloc[i]:  # 低走
                    drop = (open_.iloc[i] / close.iloc[i] - 1) * 100
                    if drop > 7:
                        return False, "有高开低走>7%", 0
        
        reasons.append("无大幅回撤")
        score += 40
        
        reason = "趋势稳健: " + " | ".join(reasons)
        return True, reason, min(100, score)
    
    # ==================== 策略7: 海龟交易法则 ====================
    def turtle_trading(self, df: pd.DataFrame, period: int = 60) -> Tuple[bool, str, float]:
        """
        海龟交易法则（创新高买入）
        
        条件：
        当日收盘价 >= period日最高收盘价
        """
        if len(df) < period:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        
        last_close = close.iloc[-1]
        high_n = close.iloc[-period-1:-1].max()
        
        if last_close >= high_n:
            reason = f"海龟法则: 创{period}日新高"
            # 计算突破幅度
            breakthrough = (last_close / high_n - 1) * 100
            score = 60 + min(40, breakthrough * 10)
            return True, reason, min(100, score)
        else:
            return False, f"未创新高（距{high_n:.2f}）", 0
    
    # ==================== 策略8: 高而窄的旗形 ====================
    def high_narrow_flag(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        高而窄的旗形
        
        条件：
        1. 上市至少60日
        2. 当日收盘 / (24~10日前最低) >= 1.9
        3. 24~10日前有连续两天涨幅 >= 9.5%
        """
        if len(df) < 60:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        
        last_close = close.iloc[-1]
        
        # 找24~10日前最低
        low_range = close.iloc[-25:-10]
        low_price = low_range.min()
        
        if last_close / low_price < 1.9:
            return False, "涨幅不足", 0
        
        # 检查连续涨停
        changes = close.pct_change() * 100
        
        found_double_zt = False
        for i in range(-25, -11):
            if changes.iloc[i] >= 9.5 and changes.iloc[i+1] >= 9.5:
                found_double_zt = True
                break
        
        if not found_double_zt:
            return False, "无连续涨停", 0
        
        reason = f"高窄旗形: 涨幅{(last_close/low_price-1)*100:.1f}%"
        return True, reason, 80
    
    # ==================== 策略9: MACD金叉 ====================
    def macd_golden_cross(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        MACD金叉
        
        条件：
        1. DIF上穿DEA（金叉）
        2. 或DIF > DEA且MACD柱状图放大
        """
        if len(df) < 35:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        
        # 计算MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9).mean()
        macd = (dif - dea) * 2
        
        reasons = []
        score = 0
        
        # 金叉
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
            reasons.append("MACD金叉")
            score = 80
        # 多头且柱状图放大
        elif dif.iloc[-1] > dea.iloc[-1]:
            reasons.append("MACD多头")
            if macd.iloc[-1] > macd.iloc[-2]:
                reasons.append("柱状图放大")
                score = 60
            else:
                score = 40
        else:
            return False, "MACD空头", 0
        
        # DIF和DEA的位置
        if dif.iloc[-1] > 0:
            reasons.append("DIF>0")
            score += 10
        
        reason = " | ".join(reasons)
        return True, reason, min(100, score)
    
    # ==================== 策略10: KDJ超卖反弹 ====================
    def kdj_oversold(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        KDJ超卖反弹
        
        条件：
        1. K值 < 20 或 J值 < 10（超卖）
        2. K值上穿D值（反弹信号）
        """
        if len(df) < 20:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        low = df["low"].astype(float)
        high = df["high"].astype(float)
        
        # 计算KDJ
        low_n = low.rolling(9).min()
        high_n = high.rolling(9).max()
        rsv = (close - low_n) / (high_n - low_n) * 100
        rsv = rsv.fillna(50)
        
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        j = 3 * k - 2 * d
        
        reasons = []
        score = 0
        
        # 超卖判断
        if j.iloc[-1] < 10:
            reasons.append(f"J值{ j.iloc[-1]:.1f}严重超卖")
            score += 40
        elif k.iloc[-1] < 20:
            reasons.append(f"K值{k.iloc[-1]:.1f}超卖")
            score += 30
        elif j.iloc[-1] < 20:
            reasons.append(f"J值{j.iloc[-1]:.1f}超卖")
            score += 20
        else:
            return False, f"未超卖（K={k.iloc[-1]:.1f}）", 0
        
        # 反弹信号
        if k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2]:
            reasons.append("K上穿D")
            score += 40
        elif k.iloc[-1] > d.iloc[-1]:
            reasons.append("K>D")
            score += 20
        
        reason = "KDJ超卖: " + " | ".join(reasons)
        return True, reason, min(100, score)
    
    # ==================== 策略11: 多因子综合 ====================
    def multi_factor(self, df: pd.DataFrame, quote: dict = None) -> Tuple[bool, str, float]:
        """
        多因子综合评分
        
        因子：
        1. 技术因子：MACD、均线、量比
        2. 趋势因子：涨跌幅、波动率
        3. 位置因子：距高点、距低点
        """
        if len(df) < 60:
            return False, "数据不足", 0
        
        close = df["close"].astype(float)
        volume = df["volume"].astype(float)
        
        factors = {}
        
        # 1. MACD因子
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9).mean()
        
        if dif.iloc[-1] > dea.iloc[-1]:
            factors["macd"] = 1
        else:
            factors["macd"] = 0
        
        # 2. 均线因子
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        
        if ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1]:
            factors["ma"] = 1
        elif ma5.iloc[-1] > ma10.iloc[-1]:
            factors["ma"] = 0.5
        else:
            factors["ma"] = 0
        
        # 3. 量比因子
        vol_ma5 = volume.rolling(5).mean()
        vol_ratio = volume.iloc[-1] / vol_ma5.iloc[-1] if vol_ma5.iloc[-1] > 0 else 1
        
        if vol_ratio >= 2:
            factors["volume"] = 1
        elif vol_ratio >= 1.5:
            factors["volume"] = 0.5
        else:
            factors["volume"] = 0
        
        # 4. 趋势因子
        change_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100
        if 0 < change_5d < 10:
            factors["trend"] = 1
        elif change_5d >= 10:
            factors["trend"] = 0.5  # 涨太多
        else:
            factors["trend"] = 0
        
        # 5. 位置因子
        high_20 = close.iloc[-20:].max()
        low_20 = close.iloc[-20:].min()
        position = (close.iloc[-1] - low_20) / (high_20 - low_20) if high_20 != low_20 else 0.5
        
        if position < 0.3:
            factors["position"] = 1  # 低位
        elif position < 0.5:
            factors["position"] = 0.5
        else:
            factors["position"] = 0
        
        # 综合评分
        weights = {
            "macd": 0.25,
            "ma": 0.25,
            "volume": 0.2,
            "trend": 0.15,
            "position": 0.15,
        }
        
        total_score = sum(factors[k] * weights[k] for k in factors) * 100
        
        # 构建理由
        active_factors = [k for k, v in factors.items() if v > 0]
        reason = f"多因子: {', '.join(active_factors)}"
        
        if total_score >= 60:
            return True, reason, total_score
        else:
            return False, f"评分不足（{total_score:.0f}）", total_score
    
    # ==================== 综合选股 ====================
    def comprehensive_select(self, df: pd.DataFrame, quote: dict = None) -> Dict:
        """
        综合选股：运行所有策略
        
        Returns:
            {
                "strategies": [(策略名, 入选, 理由, 评分), ...],
                "total_score": 综合评分,
                "matched_count": 入选策略数,
                "suggestion": 操作建议,
            }
        """
        strategies = [
            ("放量上涨", self.volume_breakout),
            ("均线多头", self.ma_bullish),
            ("停机坪", self.helipad),
            ("回踩年线", self.pullback_to_ma250),
            ("突破平台", self.break_platform),
            ("无大幅回撤", self.no_big_drawdown),
            ("海龟法则", self.turtle_trading),
            ("高窄旗形", self.high_narrow_flag),
            ("MACD金叉", self.macd_golden_cross),
            ("KDJ超卖", self.kdj_oversold),
            ("多因子", lambda df: self.multi_factor(df, quote)),
        ]
        
        results = []
        total_score = 0
        matched_count = 0
        
        for name, func in strategies:
            try:
                matched, reason, score = func(df)
                results.append((name, matched, reason, score))
                
                if matched:
                    matched_count += 1
                    total_score += score
            except Exception as e:
                logger.debug(f"策略{name}执行失败: {e}")
                results.append((name, False, f"执行失败: {e}", 0))
        
        # 综合评分
        if matched_count > 0:
            avg_score = total_score / matched_count
        else:
            avg_score = 0
        
        # 操作建议
        if matched_count >= 5 and avg_score >= 70:
            suggestion = "强烈买入"
        elif matched_count >= 3 and avg_score >= 60:
            suggestion = "逢低买入"
        elif matched_count >= 2:
            suggestion = "关注"
        else:
            suggestion = "观望"
        
        return {
            "strategies": results,
            "total_score": round(avg_score, 1),
            "matched_count": matched_count,
            "suggestion": suggestion,
        }
