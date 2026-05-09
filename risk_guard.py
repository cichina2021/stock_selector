# -*- coding: utf-8 -*-
"""
智能选股系统 - 门下属风控引擎 v1.0
嫁接自金策智算「门下省」风控体系

门下属职责：一票否决
即使策略通过，只要触发以下任一规则，信号作废并记录在案。

风控规则（5条铁律）：
R1  单笔止损上限   - 单次信号止损幅度 ≤ max_single_loss_pct（默认10%）
R2  单票仓位上限   - 单票占资金 ≤ max_position_pct（默认10%）
R3  总仓位上限     - 总持仓占资金 ≤ max_total_position_pct（默认50%）
R4  日亏损熔断     - 当日亏损 ≥ daily_loss_limit（默认5%）→ 暂停所有开仓
R5  连亏熔断       - 连续亏损次数 ≥ max_consecutive_losses → 暂停开仓

用法示例：
    guard = RiskGuard()
    result = guard.evaluate(signal=signal_dict, current_positions=positions, daily_pnl_pct=-2.5)
    if result["approved"]:
        proceed_to_execute(signal)
    else:
        rejected_reason = result["rejected_by"][0]
        log_to_audit(rejected_reason)
"""
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class RiskGuard:
    """
    门下省风控引擎

    评估逻辑：
    1. 检查信号本身是否合理（止损幅度是否合理）
    2. 模拟信号执行后，检验各规则是否触发
    3. 返回 approved=True/False 及详细原因
    """

    def __init__(
        self,
        # R1: 单笔止损上限（%）
        max_single_loss_pct: float = 10.0,
        # R2: 单票仓位上限（占总资金%）
        max_position_pct: float = 10.0,
        # R3: 总仓位上限（占总资金%）
        max_total_position_pct: float = 50.0,
        # R4: 日亏损熔断阈值（%）
        daily_loss_limit: float = 5.0,
        # R5: 连亏熔断次数
        max_consecutive_losses: int = 3,
    ):
        self.max_single_loss_pct = max_single_loss_pct
        self.max_position_pct = max_position_pct
        self.max_total_position_pct = max_total_position_pct
        self.daily_loss_limit = daily_loss_limit
        self.max_consecutive_losses = max_consecutive_losses

        # 运行时状态
        self.consecutive_losses = 0          # 当前连亏次数
        self.daily_loss_triggered = False     # 今日熔断标志
        self.rules_triggered_history: List[Dict] = []  # 历史触发记录

    def evaluate(
        self,
        signal: Dict,
        current_positions: List[Dict],
        daily_pnl_pct: float = 0.0,
        total_cash: float = 1000000.0,
    ) -> Dict:
        """
        评估一个交易信号是否通过风控

        Args:
            signal: 信号字典，结构：
                {
                    "code": str,           # 股票代码
                    "direction": str,      # "BUY" / "SELL"
                    "price": float,        # 触发价格
                    "stop_loss": float,     # 止损价（可选）
                    "qty": int,             # 数量（可选）
                    "risk_reward_ratio": float,  # 风险收益比（可选）
                    "entry_price": float,   # 买入价（可选）
                }
            current_positions: 当前持仓列表，结构：
                [
                    {"code": str, "qty": int, "cost": float, "name": str},
                    ...
                ]
            daily_pnl_pct: 当日浮动盈亏比例（%，负值表示亏损）
            total_cash: 总资金（默认100万）

        Returns:
            {
                "approved": bool,          # 是否通过
                "rejected_by": List[str],  # 触发规则列表（如被拒绝）
                "warnings": List[str],     # 警告（不阻断）
                "position_after": float,   # 预计执行后总仓位
                "single_loss_pct": float,  # 本次止损幅度
                "score_penalty": int,      # 扣分（用于评分卡）
            }
        """
        rejected_by = []
        warnings = []
        score_penalty = 0

        direction = signal.get("direction", "BUY")
        code = signal.get("code", "")
        signal_price = float(signal.get("price", 0))
        stop_loss = float(signal.get("stop_loss", 0))
        entry_price = signal.get("entry_price", signal_price)
        risk_reward_ratio = float(signal.get("risk_reward_ratio", 0))

        # ── R4: 日亏损熔断检查 ──────────────────────────
        if daily_pnl_pct <= -self.daily_loss_limit:
            rejected_by.append(
                f"R4 日亏损熔断: {daily_pnl_pct:.2f}% ≤ -{self.daily_loss_limit}%"
            )
            score_penalty += 50

        # ── R5: 连亏熔断检查 ──────────────────────────
        if self.consecutive_losses >= self.max_consecutive_losses:
            rejected_by.append(
                f"R5 连亏熔断: 连亏{self.consecutive_losses}次 ≥ {self.max_consecutive_losses}次"
            )
            score_penalty += 40

        # ── R1: 单笔止损上限 ──────────────────────────
        single_loss_pct = 0.0
        if direction == "BUY" and signal_price > 0 and stop_loss > 0:
            single_loss_pct = (signal_price - stop_loss) / signal_price * 100
        elif direction == "SELL" and signal_price > 0 and stop_loss > 0:
            single_loss_pct = (stop_loss - signal_price) / signal_price * 100

        if single_loss_pct > self.max_single_loss_pct:
            rejected_by.append(
                f"R1 单笔止损超限: {single_loss_pct:.1f}% > {self.max_single_loss_pct}%"
            )
            score_penalty += 35
        elif single_loss_pct > self.max_single_loss_pct * 0.7:
            warnings.append(
                f"R1 止损偏高: {single_loss_pct:.1f}%（建议≤{self.max_single_loss_pct}%）"
            )
            score_penalty += 10

        # ── R2: 单票仓位上限 ──────────────────────────
        current_holding_value = 0.0
        for pos in current_positions:
            if pos.get("code") == code:
                current_holding_value = float(pos.get("cost", 0)) * int(pos.get("qty", 0))
                break

        qty = int(signal.get("qty", 0))
        if direction == "BUY" and signal_price > 0 and qty > 0:
            new_position_value = current_holding_value + signal_price * qty
            position_pct = new_position_value / total_cash * 100
        elif direction == "SELL":
            position_pct = current_holding_value / total_cash * 100
        else:
            position_pct = current_holding_value / total_cash * 100

        if position_pct > self.max_position_pct:
            rejected_by.append(
                f"R2 单票仓位超限: {position_pct:.1f}% > {self.max_position_pct}%"
            )
            score_penalty += 30
        elif position_pct > self.max_position_pct * 0.8:
            warnings.append(
                f"R2 仓位偏高: {position_pct:.1f}%（建议≤{self.max_position_pct}%）"
            )
            score_penalty += 5

        # ── R3: 总仓位上限 ──────────────────────────
        total_position_value = sum(
            float(pos.get("cost", 0)) * int(pos.get("qty", 0))
            for pos in current_positions
        )
        if direction == "BUY" and signal_price > 0 and qty > 0:
            total_position_value += signal_price * qty
        elif direction == "SELL":
            for pos in current_positions:
                if pos.get("code") == code:
                    total_position_value -= float(pos.get("cost", 0)) * int(pos.get("qty", 0))
                    break

        total_position_pct = total_position_value / total_cash * 100

        if total_position_pct > self.max_total_position_pct:
            rejected_by.append(
                f"R3 总仓位超限: {total_position_pct:.1f}% > {self.max_total_position_pct}%"
            )
            score_penalty += 30
        elif total_position_pct > self.max_total_position_pct * 0.85:
            warnings.append(
                f"R3 总仓位偏高: {total_position_pct:.1f}%（建议≤{self.max_total_position_pct}%）"
            )
            score_penalty += 5

        # ── 风险收益比警告 ──────────────────────────
        if risk_reward_ratio > 0 and risk_reward_ratio < 1.5:
            warnings.append(
                f"风险收益比偏低: {risk_reward_ratio:.2f}（建议≥2.0）"
            )
            score_penalty += 15
        elif risk_reward_ratio <= 0:
            warnings.append("缺少风险收益比数据，跳过该项评估")

        approved = len(rejected_by) == 0

        return {
            "approved": approved,
            "rejected_by": rejected_by,
            "warnings": warnings,
            "position_after": total_position_pct,
            "single_loss_pct": round(single_loss_pct, 2),
            "score_penalty": score_penalty,
        }

    def on_trade_result(self, pnl_pct: float, is_loss: bool):
        """
        交易结束后通知风控层（用于更新连亏计数）

        Args:
            pnl_pct: 本次交易盈亏比例（%）
            is_loss: 是否为亏损
        """
        if is_loss:
            self.consecutive_losses += 1
            logger.warning(
                f"[门下省] 亏损记录: 连亏{self.consecutive_losses}次 "
                f"(本次亏损{pnl_pct:.2f}%)"
            )
        else:
            if self.consecutive_losses > 0:
                logger.info(
                    f"[门下省] 盈利重置连亏计数: {self.consecutive_losses}→0"
                )
            self.consecutive_losses = 0

    def reset_daily_limit(self):
        """每日开盘前重置日亏损熔断标志"""
        self.daily_loss_triggered = False

    def get_status(self) -> Dict:
        """获取当前风控状态（用于UI显示）"""
        status = "正常"
        risk_level = "低风险"

        if self.daily_loss_triggered:
            status = "熔断中"
            risk_level = "极端风险"
        elif self.consecutive_losses >= self.max_consecutive_losses:
            status = "连亏暂停"
            risk_level = "高风险"
        elif self.consecutive_losses >= 2:
            status = "连亏警告"
            risk_level = "中等风险"
        elif self.consecutive_losses >= 1:
            status = "连亏1次"
            risk_level = "偏低"

        return {
            "status": status,
            "risk_level": risk_level,
            "consecutive_losses": self.consecutive_losses,
            "daily_loss_triggered": self.daily_loss_triggered,
        }
