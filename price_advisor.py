# -*- coding: utf-8 -*-
"""
价位建议引擎
基于技术分析计算支撑位、阻力位、买入/卖出价位

算法：
1. 支撑位：近期低点、MA均线、前次回调低点
2. 阻力位：近期高点、整数关口、前高压力
3. 买入区间：支撑位附近（-2%~0%）
4. 卖出区间：阻力位附近（0%~+3%）
5. 止损位：跌破关键支撑
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class PriceAdvisor:
    """价位建议引擎"""

    def __init__(self):
        pass

    def analyze(self, df: pd.DataFrame, quote: dict = None) -> Dict:
        """
        综合价位分析
        
        Returns:
            {
                "current_price": 当前价,
                "support_levels": [支撑位列表],
                "resistance_levels": [阻力位列表],
                "buy_zone": {"low": 买入下限, "high": 买入上限, "reason": 理由},
                "sell_zone": {"low": 卖出下限, "high": 卖出上限, "reason": 理由},
                "stop_loss": 止损价,
                "target_price": 目标价,
                "risk_reward_ratio": 风险收益比,
            }
        """
        if df is None or len(df) < 30:
            return self._empty_result(quote)

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        
        current = close.iloc[-1]
        
        # 计算各维度支撑阻力
        support = []
        resistance = []

        # 1. 近期高低点
        support.extend(self._pivot_lows(low, close))
        resistance.extend(self._pivot_highs(high, close))

        # 2. 均线支撑阻力
        ma_support, ma_resist = self._ma_levels(close)
        support.extend(ma_support)
        resistance.extend(ma_resist)

        # 3. 整数关口
        int_sup, int_res = self._integer_levels(current)
        support.extend(int_sup)
        resistance.extend(int_res)

        # 4. 前期重要价格（缺口、长上下影线）
        gap_support, gap_resist = self._gap_levels(df)
        support.extend(gap_support)
        resistance.extend(gap_resist)

        # 去重并排序
        support = self._dedupe_sort(support, current, ascending=True)
        resistance = self._dedupe_sort(resistance, current, ascending=False)

        # 只保留当前价附近的（支撑<当前价，阻力>当前价）
        near_support = [s for s in support if s < current * 1.02][:4]
        near_resistance = [r for r in resistance if r > current * 0.98][:4]

        # 如果没有找到足够的支撑阻力，补充默认值
        if not near_support:
            near_support = [round(current * 0.95, 2), round(current * 0.90, 2)]
        if not near_resistance:
            near_resistance = [round(current * 1.05, 2), round(current * 1.10, 2)]

        # ===== 买入区间：支撑位到现价之间 =====
        # 取最近的强支撑作为买入下限
        best_support = near_support[0] if near_support else round(current * 0.95, 2)
        # 买入上限：现价下方一点点（给一点回调空间）
        buy_high = round(current * 0.98, 2)  # 现价-2%，留出回调空间
        buy_low = min(best_support, buy_high * 0.97)  # 确保低 < 高

        # ===== 卖出区间：阻力位附近 =====
        sell_low = round(current * 1.02, 2)  # 现价+2%
        sell_high = near_resistance[0] if near_resistance else round(current * 1.08, 2)

        # ===== 止损位：跌破最近强支撑下方3% =====
        stop_loss = round(best_support * 0.97, 2)

        # ===== 目标价：取有意义的上涨空间 =====
        # 规则1：优先取第二阻力位（第一阻力太近没利润）
        # 规则2：如果只有一个阻力位或第一阻力涨幅<5%，用更远的目标
        if len(near_resistance) >= 2:
            # 有多个阻力位时，取第二阻力作为目标（第一阻力是短线减仓点）
            target = near_resistance[1]
        elif near_resistance:
            first_r = near_resistance[0]
            gain_pct = (first_r - current) / current * 100
            if gain_pct >= 5:
                # 第一阻力位涨幅≥5%，可以用作目标
                target = first_r
            else:
                # 涨幅太小，取更高的目标（至少5%）
                target = max(first_r, round(current * 1.05, 2))
        else:
            target = round(current * 1.08, 2)

        # 如果目标价还是太接近现价（<3%），强制拉到8%
        if (target - current) / current < 0.03:
            target = round(current * 1.08, 2)

        # 风险收益比
        risk = current - stop_loss
        reward = target - current
        ratio = round(reward / risk, 2) if risk > 0 else -1

        # 构建理由
        buy_reason = f"靠近{len(near_support)}个支撑位"
        if near_support:
            buy_reason += f"（首支撑{near_support[0]:.2f}）"

        sell_reason = f"靠近{len(near_resistance)}个阻力位"
        if near_resistance:
            sell_reason += f"（首阻力{near_resistance[0]:.2f}）"

        return {
            "current_price": round(current, 2),
            "support_levels": [round(s, 2) for s in near_support],
            "resistance_levels": [round(r, 2) for r in near_resistance],
            "buy_zone": {
                "low": round(buy_low, 2),
                "high": round(buy_high, 2),
                "reason": buy_reason,
            },
            "sell_zone": {
                "low": round(sell_low, 2),
                "high": round(sell_high, 2),
                "reason": sell_reason,
            },
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target, 2),
            "risk_reward_ratio": round(ratio, 2),
        }

    def _pivot_lows(self, low: pd.Series, close: pd.Series) -> List[float]:
        """ pivot低点作为支撑"""
        levels = []
        window = min(20, len(low) - 1)

        for i in range(window, len(low)):
            # 检查是否是局部最低点
            if low.iloc[i] == low.iloc[i - window:i + window + 1].min():
                levels.append(low.iloc[i])

        return levels[-5:]  # 最近5个

    def _pivot_highs(self, high: pd.Series, close: pd.Series) -> List[float]:
        """ pivot高点作为阻力"""
        levels = []
        window = min(20, len(high) - 1)

        for i in range(window, len(high)):
            if high.iloc[i] == high.iloc[i - window:i + window + 1].max():
                levels.append(high.iloc[i])

        return levels[-5:]

    def _ma_levels(self, close: pd.Series) -> Tuple[List[float], List[float]]:
        """均线作为动态支撑阻力"""
        supports = []
        resists = []

        for period in [5, 10, 20, 30, 60]:
            if len(close) >= period:
                ma = close.rolling(period).mean().iloc[-1]
                current = close.iloc[-1]
                if ma < current:
                    supports.append(ma)
                elif ma > current:
                    resists.append(ma)

        return supports, resists

    def _integer_levels(self, current: float) -> Tuple[List[float], List[float]]:
        """整数关口"""
        base = int(current // 10) * 10
        supports = []
        resists = []

        # 下方整数关
        for offset in [-10, -5, 0]:
            level = base + offset
            if 0 < level < current:
                supports.append(float(level))

        # 上方整数关
        for offset in [0, 5, 10]:
            level = base + offset
            if level > current:
                resists.append(float(level))

        return supports[:3], resists[:3]

    def _gap_levels(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """缺口和长影线位置"""
        supports = []
        resists = []

        close = df["close"].astype(float)
        low = df["low"].astype(float)
        high = df["high"].astype(float)

        # 跳空缺口
        for i in range(1, min(30, len(df))):
            # 向上跳空 → 缺口下方是支撑
            if low.iloc[i] > high.iloc[i - 1]:
                supports.append(high.iloc[i - 1])
            # 向下跳空 → 缺口上方是阻力
            elif high.iloc[i] < low.iloc[i - 1]:
                resists.append(low.iloc[i - 1])

        # 长下影线（锤头）→ 低点是支撑
        for i in range(max(1, len(df) - 30), len(df)):
            body = abs(close.iloc[i] - df["open"].iloc[i])
            lower_shadow = min(close.iloc[i], df["open"].iloc[i]) - low.iloc[i]
            if lower_shadow > body * 2 and body > 0:
                supports.append(low.iloc[i])

        # 长上影线（射击之星）→ 高点是阻力
        for i in range(max(1, len(df) - 30), len(df)):
            body = abs(close.iloc[i] - df["open"].iloc[i])
            upper_shadow = high.iloc[i] - max(close.iloc[i], df["open"].iloc[i])
            if upper_shadow > body * 2 and body > 0:
                resists.append(high.iloc[i])

        return supports[-3:], resists[-3:]

    def _dedupe_sort(self, levels: List[float], current: float, ascending: bool) -> List[float]:
        """去重排序，只保留有意义的级别"""
        if not levels:
            return levels

        # 去重（允许1%误差内的合并）
        unique = []
        for level in sorted(levels):
            is_dup = False
            for u in unique:
                if abs(level - u) / max(u, 0.01) < 0.01:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(level)

        # 按距离当前价排序
        unique.sort(key=lambda x: abs(x - current))

        return unique[:6]

    def _empty_result(self, quote: dict = None) -> Dict:
        price = (quote or {}).get("price", 0)
        return {
            "current_price": price,
            "support_levels": [],
            "resistance_levels": [],
            "buy_zone": {"low": 0, "high": 0, "reason": "数据不足"},
            "sell_zone": {"low": 0, "high": 0, "reason": "数据不足"},
            "stop_loss": 0,
            "target_price": 0,
            "risk_reward_ratio": 0,
        }
