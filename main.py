# -*- coding: utf-8 -*-
"""
智能选股系统 v5.0 - 金策智算融合版
嫁接门下省风控 + 100分评分卡 + 三省六部UI风格

功能：
- 门下省风控：5条铁律一票否决
- 礼部评分卡：四维度100分制 S/A/B/C/D 评级
- 中书省策略：11策略 + 61形态 + 价位建议
- 实时全扫：一键扫描108只自选股
- 事件日志：实时显示分析过程
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os
import logging
import time
from typing import List

# 配置日志（只写文件）
log_format = '%(asctime)s [%(levelname)s] %(message)s'
log_file = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'debug.log')
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger("StockSelector")
logger.info(f"日志文件: {log_file}")

if getattr(sys, 'frozen', False):
    WORK_DIR = os.path.dirname(sys.executable)
else:
    WORK_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORK_DIR)

from selector import StockSelector


# ═══════════════════════════════════════════════════════
#  配色方案（借鉴金策智算 Slate900/Blue风格）
# ═══════════════════════════════════════════════════════
# 主背景（Slate-900系列）
C_BG       = "#0b1120"   # 最深底色
C_BG2      = "#0f172a"   # 卡片背景
C_BG3      = "#1e293b"   # 悬浮背景
C_BG4      = "#334155"   # 高亮背景

# 前景
C_FG       = "#e2e8f0"   # 主文字
C_FG2      = "#94a3b8"   # 次要文字

# 强调色（Blue-500/Emerald-500/Rose-500）
C_ACCENT   = "#3b82f6"   # 蓝色强调
C_GREEN    = "#10b981"   # 翡翠绿（盈利）
C_RED      = "#f43f5e"   # 玫瑰红（亏损）
C_YELLOW   = "#f59e0b"   # 琥珀黄（警告）
C_PURPLE   = "#a855f7"   # 紫色
C_CYAN     = "#06b6d4"   # 青色

# 边框
C_BORDER   = "#334155"   # Slate-700
C_GLOW    = "#2563eb"   # 发光蓝

# 字体（等宽字体用于数据，UI字体用于标签）
FONT_TITLE  = ("Microsoft YaHei", 14, "bold")
FONT_MAIN   = ("Microsoft YaHei", 10)
FONT_BOLD   = ("Microsoft YaHei", 10, "bold")
FONT_CODE   = ("Consolas", 10)
FONT_SMALL  = ("Microsoft YaHei", 8)
FONT_PRICE  = ("Consolas", 20, "bold")
FONT_SCORE  = ("Consolas", 28, "bold")
FONT_GRADE  = ("Arial Black", 36, "bold")
FONT_SCAN   = ("Microsoft YaHei", 12, "bold")
FONT_EVENT  = ("Consolas", 9)


# ═══════════════════════════════════════════════════════
#  主应用
# ═══════════════════════════════════════════════════════
class StockSelectorApp:
    def __init__(self):
        self.selector = StockSelector()
        self._analyzing = False
        self._scanning = False          # 全局扫描状态
        self.scan_results = {}          # code -> result dict
        self.scan_progress = (0, 0)     # (当前, 总数)
        self.root = tk.Tk()
        self.root.title("智能选股系统 v5.0")
        self.root.geometry("1600x950")
        self.root.minsize(1440, 800)
        self.root.configure(bg=C_BG)
        
        # 事件日志（实时分析过程）
        self.event_log: List[str] = []
        self._log_event("系统启动", "v5.0")

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        self._build_ui()
        self._center_window()

        # 启动：先刷新行情 → 再自动全扫
        self._refresh_pool()
        self._load_sectors()
        self._schedule_refresh()

    # ───────────────────────────────────────────────
    #  UI 布局
    # ───────────────────────────────────────────────
    def _build_ui(self):
        # ── 顶部工具栏 ──
        top = tk.Frame(self.root, bg=C_BG2, height=52)
        top.pack(fill=tk.X, padx=0, pady=0)
        top.pack_propagate(False)

        # Logo
        tk.Label(top, text="📊 智能选股系统", font=FONT_TITLE, bg=C_BG2, fg=C_ACCENT).pack(side=tk.LEFT, padx=16, pady=0)
        tk.Label(top, text="v4.0", font=FONT_SMALL, bg=C_BG2, fg=C_FG2).pack(side=tk.LEFT, padx=(2, 0), pady=14)

        # 分隔
        tk.Frame(top, bg=C_BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=10)

        # 统计标签
        self.stats_label = tk.Label(top, text="正在加载...", font=FONT_MAIN, bg=C_BG2, fg=C_FG2)
        self.stats_label.pack(side=tk.LEFT, pady=14)

        # 扫描进度条区域
        self.progress_frame = tk.Frame(top, bg=C_BG2)
        self.progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=16, pady=14)

        self.progress_label = tk.Label(self.progress_frame, text="", font=FONT_SMALL, bg=C_BG2, fg=C_ACCENT)
        self.progress_label.pack(fill=tk.X)

        # 分隔
        tk.Frame(top, bg=C_BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=10)

        # 操作按钮
        btn_frame = tk.Frame(top, bg=C_BG2)
        btn_frame.pack(side=tk.RIGHT, padx=16, pady=8)

        self.refresh_btn = tk.Button(btn_frame, text="🔄 刷新行情", font=FONT_BOLD, bg=C_ACCENT, fg="white",
                                     relief=tk.FLAT, cursor="hand2", command=self._refresh_pool)
        self.refresh_btn.pack(side=tk.LEFT, ipadx=10, ipady=3)

        self.scan_btn = tk.Button(btn_frame, text="🔍 全量扫描", font=FONT_BOLD, bg=C_GREEN, fg="white",
                                  relief=tk.FLAT, cursor="hand2", command=self._start_full_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=(6, 0), ipadx=10, ipady=3)

        self.auto_btn = tk.Button(btn_frame, text="⏸ 停止自动", font=FONT_BOLD, bg=C_YELLOW, fg="white",
                                  relief=tk.FLAT, cursor="hand2", command=self._toggle_auto)
        self.auto_btn.pack(side=tk.LEFT, padx=(6, 0), ipadx=10, ipady=3)

        # ── 主体三栏 ──
        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 左侧：股票池列表（带评分）
        self._build_pool_panel(body)
        tk.Frame(body, bg=C_BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # 右侧：分析详情（无需事件日志）
        self._build_detail_panel(body)

    def _build_pool_panel(self, body):
        """左侧：股票池列表（名称+代码+现价+涨跌幅+成交额+评分）"""
        left = tk.Frame(body, bg=C_BG, width=580)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 6))
        left.pack_propagate(False)

        # 标题栏
        hdr = tk.Frame(left, bg=C_BG2, height=36)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋 自选股票池", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).pack(side=tk.LEFT, padx=12, pady=8)
        self.pool_sort_label = tk.Label(hdr, text="按涨幅排序 | 点击查看详情", font=FONT_SMALL, bg=C_BG2, fg=C_FG2)
        self.pool_sort_label.pack(side=tk.RIGHT, padx=12, pady=8)

        # 表头
        col_hdr = tk.Frame(left, bg=C_BG3, height=30)
        col_hdr.pack(fill=tk.X)
        col_hdr.pack_propagate(False)
        self._sort_key = "change_pct"  # 默认按涨跌幅排序
        self._sort_reverse = True   # 默认降序
        headers = [
            ("名称",         0,   90),
            ("代码",         95,  70),
            ("现价",        170,  70),
            ("涨跌幅",      245,  80),
            ("成交额(万)",  330,  90),
            ("评分",        425,  60),
        ]
        for txt, x, w in headers:
            lbl = tk.Label(col_hdr, text=txt, font=FONT_SMALL, bg=C_BG3, fg=C_FG2, cursor="hand2")
            lbl.place(x=x, y=7, width=w)
            lbl.bind("<Button-1>", lambda e, t=txt: self._toggle_sort(t))

        # Canvas滚动列表
        list_frame = tk.Frame(left, bg=C_BG)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.pool_canvas = tk.Canvas(list_frame, bg=C_BG, highlightthickness=0, bd=0)
        pool_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.pool_canvas.yview)
        self.pool_inner = tk.Frame(self.pool_canvas, bg=C_BG)

        self.pool_inner.bind("<Configure>",
            lambda e: self.pool_canvas.configure(scrollregion=self.pool_canvas.bbox("all")))
        self.canvas_win = self.pool_canvas.create_window((0, 0), window=self.pool_inner, anchor=tk.NW)
        self.pool_canvas.bind("<Configure>",
            lambda e: self.pool_canvas.itemconfig(self.canvas_win, width=e.width))
        self.pool_canvas.configure(yscrollcommand=pool_scroll.set)

        self.pool_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pool_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定点击事件
        for w in [self.pool_canvas, self.pool_inner]:
            w.bind("<Button-1>", self._on_pool_click)

        self.pool_items = []
        self.pool_data = []

    def _build_detail_panel(self, body):
        """右侧：分析详情"""
        right = tk.Frame(body, bg=C_BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # ── 信息卡 ──
        self.info_card = tk.Frame(right, bg=C_BG2, height=110)
        self.info_card.pack(fill=tk.X, pady=(0, 6))
        self.info_card.pack_propagate(False)
        self._build_info_card(self.info_card)

        # ── 中部两栏 ──
        mid = tk.Frame(right, bg=C_BG)
        mid.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        left_mid = tk.Frame(mid, bg=C_BG)
        left_mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_mid = tk.Frame(mid, bg=C_BG, width=300)
        right_mid.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        right_mid.pack_propagate(False)

        self._build_strategy_panel(left_mid)
        self._build_price_panel(right_mid)

        # ── 操作建议详情 ──
        self._build_advice_panel(right)

        # ── 底部板块 ──
        self._build_sector_panel(right)

    def _build_info_card(self, parent):
        """顶部信息卡 - 四维度评分卡"""
        self.card_name = tk.Label(parent, text="👈 请从左侧选择股票查看详情",
                                   font=FONT_MAIN, bg=C_BG2, fg=C_FG2)
        self.card_name.place(x=16, y=8, width=420)

        self.card_price = tk.Label(parent, text="--", font=FONT_PRICE, bg=C_BG2, fg=C_FG)
        self.card_price.place(x=16, y=34, width=150)

        self.card_change = tk.Label(parent, text="--", font=("Consolas", 13), bg=C_BG2, fg=C_FG2)
        self.card_change.place(x=160, y=42, width=110)

        # ── 四维度评分卡（借鉴金策礼部）──────────────────
        score_bg = tk.Frame(parent, bg=C_BG3, highlightthickness=1, highlightbackground=C_BORDER)
        score_bg.place(x=320, y=8, width=480, height=95)
        
        # 等级（S/A/B/C/D）
        self.card_grade = tk.Label(score_bg, text="-", font=FONT_GRADE, bg=C_BG3, fg=C_FG2)
        self.card_grade.place(x=8, y=6, width=70, height=46)
        tk.Label(score_bg, text="评级", font=FONT_SMALL, bg=C_BG3, fg=C_FG2).place(x=24, y=46)
        
        # 四维度分数
        dim_x = 85
        self.card_profit = tk.Label(score_bg, text="盈利 --", font=FONT_SMALL, bg=C_BG3, fg=C_GREEN)
        self.card_profit.place(x=dim_x, y=8, width=75)
        self.card_risk = tk.Label(score_bg, text="风控 --", font=FONT_SMALL, bg=C_BG3, fg=C_RED)
        self.card_risk.place(x=dim_x+78, y=8, width=75)
        self.card_quality = tk.Label(score_bg, text="质量 --", font=FONT_SMALL, bg=C_BG3, fg=C_CYAN)
        self.card_quality.place(x=dim_x, y=28, width=75)
        self.card_practical = tk.Label(score_bg, text="实战 --", font=FONT_SMALL, bg=C_BG3, fg=C_YELLOW)
        self.card_practical.place(x=dim_x+78, y=28, width=75)
        
        # 总分
        self.card_score = tk.Label(score_bg, text="总分 --", font=FONT_BOLD, bg=C_BG3, fg=C_ACCENT)
        self.card_score.place(x=245, y=14, width=60)
        
        # 操作建议（大字醒目）
        self.card_suggest = tk.Label(score_bg, text="--", font=("Microsoft YaHei", 13, "bold"), bg=C_BG3, fg=C_FG2)
        self.card_suggest.place(x=308, y=6, width=120, height=28)
        self.card_matched = tk.Label(score_bg, text="", font=FONT_SMALL, bg=C_BG3, fg=C_FG2)
        self.card_matched.place(x=308, y=34, width=120)

        # 评分理由（单独一行，下方，加粗加清晰）
        self.card_reason = tk.Label(score_bg, text="", font=("Microsoft YaHei", 10, "bold"), bg=C_BG3, fg=C_FG2,
                                     anchor=tk.W, wraplength=460)
        self.card_reason.place(x=8, y=56, width=460)

        tk.Frame(parent, bg=C_BORDER, height=1).place(x=0, y=106, relwidth=1)

    def _build_strategy_panel(self, parent):
        """策略分析面板"""
        hdr = tk.Frame(parent, bg=C_BG2, height=34)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📊 策略分析  (✅通过  ❌未通过)", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).pack(side=tk.LEFT, padx=12, pady=6)

        list_container = tk.Frame(parent, bg=C_BG)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.strategy_widgets = {}

        strategies = [
            ("放量上涨", "量价齐升 | 成交额≥2亿 | 量比≥2"),
            ("均线多头", "MA5>MA10>MA20>MA30 | 趋势向上"),
            ("停机坪", "涨停后高开高走 | 强势整理"),
            ("回踩年线", "回踩MA250缩量 | 长期支撑确认"),
            ("突破平台", "放量突破MA60 | 横盘整理后启动"),
            ("无大幅回撤", "60日涨<60% | 无单日跌>7%"),
            ("海龟法则", "创N日新高 | 趋势延续"),
            ("高窄旗形", "涨幅≥90% | 有连续涨停"),
            ("MACD金叉", "DIF上穿DEA | MACD柱放大"),
            ("KDJ超卖", "K/J值<20 | 反弹信号"),
            ("多因子", "MACD+均线+量比+趋势+位置"),
        ]

        for i, (name, desc) in enumerate(strategies):
            row_bg = C_BG2 if i % 2 == 0 else C_BG
            f = tk.Frame(list_container, bg=row_bg, height=36)
            f.pack(fill=tk.X, padx=4, pady=1)
            f.pack_propagate(False)

            status = tk.Label(f, text="--", font=("Consolas", 12), bg=row_bg, fg=C_FG2, width=3, anchor=tk.CENTER)
            status.pack(side=tk.LEFT, padx=(8, 4), pady=5)

            name_lbl = tk.Label(f, text=name, font=FONT_BOLD, bg=row_bg, fg=C_FG, width=9, anchor=tk.W)
            name_lbl.pack(side=tk.LEFT, padx=(0, 6), pady=5)

            reason_lbl = tk.Label(f, text=desc, font=FONT_SMALL, bg=row_bg, fg=C_FG2, anchor=tk.W)
            reason_lbl.pack(side=tk.LEFT, padx=(0, 6), pady=5, fill=tk.X, expand=True)

            score_lbl = tk.Label(f, text="-", font=FONT_CODE, bg=row_bg, fg=C_FG2, width=5, anchor=tk.E)
            score_lbl.pack(side=tk.RIGHT, padx=10, pady=5)

            self.strategy_widgets[name] = {
                "frame": f, "status": status, "reason": reason_lbl,
                "score": score_lbl, "bg": row_bg,
            }

    def _build_price_panel(self, parent):
        """价位建议面板"""
        hdr = tk.Frame(parent, bg=C_BG2, height=34)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="💰 价位建议", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).pack(side=tk.LEFT, padx=12, pady=6)

        self.price_container = tk.Frame(parent, bg=C_BG)
        self.price_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.price_current = tk.Label(self.price_container, text="现价  --", font=("Consolas", 15, "bold"), bg=C_BG, fg=C_FG)
        self.price_current.pack(anchor=tk.W, pady=(0, 4))

        self.price_support = tk.Label(self.price_container, text="支撑位  --", font=FONT_MAIN, bg=C_BG, fg=C_GREEN)
        self.price_support.pack(anchor=tk.W, pady=1)
        self.price_resist = tk.Label(self.price_container, text="阻力位  --", font=FONT_MAIN, bg=C_BG, fg=C_RED)
        self.price_resist.pack(anchor=tk.W, pady=1)

        tk.Frame(self.price_container, bg=C_BORDER, height=1).pack(fill=tk.X, pady=5)

        self.price_buy = tk.Label(self.price_container, text="建议买入区间  --", font=FONT_BOLD, bg=C_BG, fg=C_GREEN)
        self.price_buy.pack(anchor=tk.W, pady=1)
        self.price_sell = tk.Label(self.price_container, text="建议卖出区间  --", font=FONT_BOLD, bg=C_BG, fg=C_RED)
        self.price_sell.pack(anchor=tk.W, pady=1)
        self.price_stop = tk.Label(self.price_container, text="止损价  --", font=FONT_MAIN, bg=C_BG, fg=C_YELLOW)
        self.price_stop.pack(anchor=tk.W, pady=1)
        self.price_target = tk.Label(self.price_container, text="目标价  --", font=FONT_MAIN, bg=C_BG, fg=C_ACCENT)
        self.price_target.pack(anchor=tk.W, pady=1)

        tk.Frame(self.price_container, bg=C_BORDER, height=1).pack(fill=tk.X, pady=5)

        self.price_ratio = tk.Label(self.price_container, text="风险收益比  --", font=FONT_MAIN, bg=C_BG, fg=C_FG2)
        self.price_ratio.pack(anchor=tk.W, pady=1)

        tk.Frame(self.price_container, bg=C_BORDER, height=1).pack(fill=tk.X, pady=5)

        tk.Label(self.price_container, text="🎯 K线形态", font=FONT_BOLD, bg=C_BG, fg=C_ACCENT).pack(anchor=tk.W, pady=2)
        self.price_patterns = tk.Label(self.price_container, text="暂无形态", font=FONT_SMALL, bg=C_BG, fg=C_FG2, wraplength=270, justify=tk.LEFT)
        self.price_patterns.pack(anchor=tk.W, pady=2)

    def _build_advice_panel(self, parent):
        """操作建议详情面板 - 大字醒目显示买入理由和操作建议"""
        # 标题栏
        hdr = tk.Frame(parent, bg=C_BG2, height=34)
        hdr.pack(fill=tk.X, pady=(6, 0))
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋 操作建议详情", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).pack(side=tk.LEFT, padx=12, pady=6)

        # 主体内容区
        body = tk.Frame(parent, bg=C_BG3, height=100)
        body.pack(fill=tk.X, padx=6, pady=(0, 6))
        body.pack_propagate(False)

        # 第一行：操作建议（大字）+ 风险收益比
        row1 = tk.Frame(body, bg=C_BG3)
        row1.pack(fill=tk.X, padx=12, pady=(10, 4))

        self.advice_suggest = tk.Label(row1, text="--", font=("Microsoft YaHei", 16, "bold"), bg=C_BG3, fg=C_FG2)
        self.advice_suggest.pack(side=tk.LEFT)

        self.advice_ratio = tk.Label(row1, text="风险收益比  --", font=FONT_MAIN, bg=C_BG3, fg=C_FG2)
        self.advice_ratio.pack(side=tk.RIGHT)

        # 第二行：买入理由
        row2 = tk.Frame(body, bg=C_BG3)
        row2.pack(fill=tk.X, padx=12, pady=(0, 4))

        tk.Label(row2, text="📌 买入理由：", font=("Microsoft YaHei", 10, "bold"), bg=C_BG3, fg=C_ACCENT).pack(side=tk.LEFT)
        self.advice_reasons = tk.Label(row2, text="--", font=("Microsoft YaHei", 10), bg=C_BG3, fg=C_GREEN, anchor=tk.W, wraplength=620)
        self.advice_reasons.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)

        # 第三行：关键价位
        row3 = tk.Frame(body, bg=C_BG3)
        row3.pack(fill=tk.X, padx=12, pady=(0, 10))

        self.advice_stop = tk.Label(row3, text="止损价  --", font=FONT_MAIN, bg=C_BG3, fg=C_YELLOW)
        self.advice_stop.pack(side=tk.LEFT, padx=(0, 16))
        self.advice_target = tk.Label(row3, text="目标价  --", font=FONT_MAIN, bg=C_BG3, fg=C_ACCENT)
        self.advice_target.pack(side=tk.LEFT, padx=(0, 16))
        self.advice_buyzone = tk.Label(row3, text="买入区间  --", font=FONT_MAIN, bg=C_BG3, fg=C_GREEN)
        self.advice_buyzone.pack(side=tk.LEFT, padx=(0, 16))
        self.advice_matched = tk.Label(row3, text="", font=FONT_SMALL, bg=C_BG3, fg=C_FG2)
        self.advice_matched.pack(side=tk.LEFT)

    def _build_sector_panel(self, parent):
        """底部板块热点"""
        bottom = tk.Frame(parent, bg=C_BG2, height=86)
        bottom.pack(fill=tk.X, pady=(6, 0))
        bottom.pack_propagate(False)

        tk.Label(bottom, text="🔥 板块热点", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).place(x=12, y=6)

        self.sector_container = tk.Frame(bottom, bg=C_BG2)
        self.sector_container.place(x=12, y=30, relwidth=1, relheight=1)
        self.sector_labels = []

        for i in range(22):
            lbl = tk.Label(self.sector_container, text="--", font=FONT_SMALL, bg=C_BG3, fg=C_FG, padx=8, pady=2)
            lbl.pack(side=tk.LEFT, padx=2, pady=2)
            self.sector_labels.append(lbl)

    # ───────────────────────────────────────────────
    #  全量扫描（核心功能！）
    # ───────────────────────────────────────────────
    def _start_full_scan(self):
        """启动全量扫描"""
        if self._scanning:
            logger.info("扫描进行中，忽略重复请求")
            return
        self._do_full_scan()

    def _do_full_scan(self):
        """执行全量扫描（后台线程）"""
        self._scanning = True
        self.scan_results.clear()
        self.scan_btn.configure(text="⏳ 扫描中...", state=tk.DISABLED, bg=C_YELLOW)
        self.progress_label.configure(text="🔄 开始全量扫描 108 只股票...")
        self._log_event("系统", "开始全量扫描")

        codes = list(self.selector.pool_codes)
        total = len(codes)

        def do_scan():
            ok_count = 0
            fail_count = 0
            for i, code in enumerate(codes):
                try:
                    logger.info(f"[全扫 {i+1}/{total}] 分析 {code} {self.selector.pool_names.get(code,'')}")
                    result = self.selector.analyze(code)

                    if "error" not in result:
                        self.scan_results[code] = result
                        ok_count += 1
                        # 记录分析结果
                        grade = result.get("grade", "-")
                        score = result.get("total_score", 0)
                        self._log_event(code, f"{grade}级 {score:.0f}分")
                    else:
                        fail_count += 1
                        self._log_event(code, f"失败: {result['error'][:20]}")

                    # 更新进度UI
                    pct = (i + 1) * 100 // total
                    name = self.selector.pool_names.get(code, code)
                    self.root.after(0, lambda c=code, n=name, p=pct, cur=i+1, t=total:
                        self._update_scan_progress(cur, t, c, n))

                except Exception as e:
                    fail_count += 1
                    logger.error(f"[全扫 {i+1}/{total}] {code} 异常: {e}")

                import time
                time.sleep(0.12)  # 控制频率

            # 扫描完成
            logger.info(f"=== 全量扫描完成: 成功{ok_count}, 失败{fail_count}")
            self.root.after(0, lambda: self._on_scan_complete(ok_count, fail_count))

        threading.Thread(target=do_scan, daemon=True).start()

    def _update_scan_progress(self, current, total, code, name):
        """更新扫描进度条"""
        pct = current * 100 // total
        bar_len = 25
        filled = current * bar_len // total
        bar = "█" * filled + "░" * (bar_len - filled)
        self.progress_label.configure(
            text=f"🔍 扫描中 [{bar}] {pct}% ({current}/{total})  {code} {name}"
        )

    def _on_scan_complete(self, ok_count, fail_count):
        """扫描完成回调"""
        self._scanning = False
        self.scan_btn.configure(text="🔍 全量扫描", state=tk.NORMAL, bg=C_GREEN)
        self.progress_label.configure(
            text=f"✅ 全量扫描完成! 成功{ok_count}只 | 失败{fail_count}只 | 按评分排序显示"
        )
        
        # 记录扫描完成事件
        self._log_event("系统", f"扫描完成 成功{ok_count} 失败{fail_count}")

        # 用扫描结果重新渲染股票池列表（带评分！）
        self._show_pool_with_scores()

    def _show_pool_with_scores(self):
        """用扫描结果重新渲染股票池（带评分）"""
        # 安全检查：如果没有行情数据，直接返回
        if not self.pool_data:
            logger.warning("_show_pool_with_scores: pool_data为空，跳过")
            return
        
        # 安全检查：如果没有扫描结果，返回
        if not self.scan_results:
            logger.warning("_show_pool_with_scores: scan_results为空，跳过")
            return
        
        logger.info(f"渲染评分列表: pool_data={len(self.pool_data)}条, scan_results={len(self.scan_results)}条")
        
        # 合并行情数据 + 评分数据
        scored_pool = []
        for q in self.pool_data:
            code = q.get("code", "")
            if not code:
                continue
            if code in self.scan_results:
                r = self.scan_results[code]
                q["score"] = r.get("total_score", 0)
                q["suggestion"] = r.get("suggestion", "")
                q["matched"] = r.get("matched_count", 0)
                logger.info(f"  {code}: score={q['score']}")
            else:
                q["score"] = -1  # 未扫描
                q["suggestion"] = ""
                q["matched"] = 0
            scored_pool.append(q)

        # 按评分降序排列
        scored_pool.sort(key=lambda x: x.get("score", -1), reverse=True)

        # 更新排序标签
        self.pool_sort_label.configure(text="按评分排序 ↓ | 点击查看详情")

        # 清空重新渲染
        for w in self.pool_inner.winfo_children():
            w.destroy()
        self.pool_items.clear()
        self.pool_data.clear()
        self.pool_data = scored_pool

        for i, q in enumerate(scored_pool):
            try:
                code = q.get("code", "")
                name = q.get("name", code) or code
                price = q.get("price", 0) or 0
                change = q.get("change_pct", 0) or 0
                amount = q.get("amount", 0) or 0
                amount_w = amount / 1e4 if amount else 0
                score = q.get("score", -1)
                matched = q.get("matched", 0)

                row_bg = C_BG3 if i % 2 == 0 else C_BG
                # 高分行特殊背景
                if score >= 60:
                    row_bg = "#0d2117"  # 绿底
                elif score >= 40:
                    row_bg = "#1d260d"

                f = tk.Frame(self.pool_inner, bg=row_bg, height=34, cursor="hand2")
                f.pack(fill=tk.X, padx=0, pady=0)
                f.pack_propagate(False)

                # 名称
                name_color = C_GREEN if change >= 0 else C_RED
                tk.Label(f, text=f"{name}", font=FONT_BOLD, bg=row_bg, fg=name_color,
                         width=9, anchor=tk.W).place(x=6, y=7)

                # 代码
                tk.Label(f, text=f"{code}", font=FONT_CODE, bg=row_bg, fg=C_FG2,
                         width=7, anchor=tk.W).place(x=96, y=9)

                # 现价
                price_color = C_GREEN if change >= 0 else C_RED
                price_str = f"{price:.2f}" if price else "--"
                tk.Label(f, text=price_str, font=FONT_CODE, bg=row_bg, fg=price_color,
                         width=8, anchor=tk.E).place(x=170, y=8)

                # 涨跌幅
                change_str = f"{change:+.2f}%" if change else "--"
                tk.Label(f, text=change_str, font=("Consolas", 9, "bold"), bg=row_bg, fg=price_color,
                         width=9, anchor=tk.E).place(x=248, y=8)

                # 成交额
                amount_str = f"{amount_w:.0f}" if amount_w else "--"
                tk.Label(f, text=amount_str, font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                         width=10, anchor=tk.E).place(x=332, y=8)

                # 评分（核心！）- 确保总是显示
                if score is None:
                    score = -1
                
                if score >= 0:
                    if score >= 70:
                        sc_color = C_GREEN
                        sc_text = f"{score}"
                    elif score >= 45:
                        sc_color = C_YELLOW
                        sc_text = f"{score}"
                    elif score >= 20:
                        sc_color = C_FG2
                        sc_text = f"{score}"
                    else:
                        sc_color = C_RED
                        sc_text = f"{score}"
                else:
                    sc_color = C_FG2
                    sc_text = "-"
                
                # 评分数字
                sc_lbl = tk.Label(f, text=sc_text, font=FONT_BOLD, bg=row_bg, fg=sc_color,
                                  width=5, anchor=tk.CENTER)
                sc_lbl.place(x=430, y=7)

                # 通过数小标记
                if matched > 0:
                    m_lbl = tk.Label(f, text=f"+{matched}", font=FONT_SMALL, bg=row_bg, fg=C_GREEN,
                                     width=4, anchor=tk.W)
                    m_lbl.place(x=462, y=10)

                # 绑定事件
                f.code_ref = code
                f.bind("<Button-1>", lambda e, c=code: self._select_and_show(c))
                for child in f.winfo_children():
                    child.bind("<Button-1>", lambda e, c=code: self._select_and_show(c))

                self.pool_items.append(f)

            except Exception as e:
                logger.error(f"渲染第{i}行失败: {e}")
                continue

        # 更新Canvas
        self.pool_inner.update_idletasks()
        self.pool_canvas.configure(scrollregion=self.pool_canvas.bbox("all"))

        # 更新统计
        high_score = len([q for q in scored_pool if q.get("score", 0) >= 50])
        self.stats_label.configure(
            text=f"股票池: {len(scored_pool)} 只  |  ⭐ ≥50分: {high_score}只  |  扫描完成 {time.strftime('%H:%M:%S')}"
        )

    # ───────────────────────────────────────────────
    #  行情刷新 & 事件
    # ───────────────────────────────────────────────
    def _refresh_pool(self):
        """刷新股票池实时行情"""
        self.refresh_btn.configure(text="⏳ 刷新中...", state=tk.DISABLED)
        self.stats_label.configure(text="股票池: --  |  正在加载行情...")

        def do_refresh():
            try:
                quotes = self.selector.get_pool_realtime()
                logger.info(f"get_pool_realtime 返回 {len(quotes)} 只")
                self.root.after(0, lambda: self._show_pool(quotes))
            except Exception as e:
                logger.error(f"刷新行情失败: {e}")
                self.root.after(0, lambda: self._show_error(f"刷新失败: {e}"))
                self.root.after(0, lambda: self.refresh_btn.configure(text="🔄 刷新行情", state=tk.NORMAL))

        threading.Thread(target=do_refresh, daemon=True).start()

    def _show_pool(self, quotes):
        """显示股票池列表 - 自动保留已扫描的评分"""
        try:
            self.refresh_btn.configure(text="🔄 刷新行情", state=tk.NORMAL)
            self.stats_label.configure(text=f"股票池: {len(quotes)} 只  |  更新时间 {time.strftime('%H:%M:%S')}")

            for w in self.pool_inner.winfo_children():
                w.destroy()
            self.pool_items.clear()
            self.pool_data.clear()

            if not quotes:
                tk.Label(self.pool_inner, text="暂无数据，请检查网络", font=FONT_MAIN, bg=C_BG, fg=C_RED).pack(pady=20)
                return

            try:
                quotes.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
            except Exception:
                pass

            for i, q in enumerate(quotes):
                try:
                    code = q.get("code", "")
                    name = q.get("name", code) or code
                    price = q.get("price", 0) or 0
                    change = q.get("change_pct", 0) or 0
                    amount = q.get("amount", 0) or 0
                    amount_w = amount / 1e4 if amount else 0

                    row_bg = C_BG3 if i % 2 == 0 else C_BG
                    f = tk.Frame(self.pool_inner, bg=row_bg, height=34, cursor="hand2")
                    f.pack(fill=tk.X, padx=0, pady=0)
                    f.pack_propagate(False)

                    name_color = C_GREEN if change >= 0 else C_RED
                    tk.Label(f, text=f"{name}", font=FONT_BOLD, bg=row_bg, fg=name_color,
                             width=9, anchor=tk.W).place(x=6, y=7)
                    tk.Label(f, text=f"{code}", font=FONT_CODE, bg=row_bg, fg=C_FG2,
                             width=7, anchor=tk.W).place(x=96, y=9)

                    price_color = C_GREEN if change >= 0 else C_RED
                    price_str = f"{price:.2f}" if price else "--"
                    tk.Label(f, text=price_str, font=FONT_CODE, bg=row_bg, fg=price_color,
                             width=8, anchor=tk.E).place(x=170, y=8)

                    change_str = f"{change:+.2f}%" if change else "--"
                    tk.Label(f, text=change_str, font=("Consolas", 9, "bold"), bg=row_bg, fg=price_color,
                             width=9, anchor=tk.E).place(x=248, y=8)

                    amount_str = f"{amount_w:.0f}" if amount_w else "--"
                    tk.Label(f, text=amount_str, font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                             width=10, anchor=tk.E).place(x=332, y=8)

                    # 保留已扫描的评分（如果scan_results中有）
                    if hasattr(self, 'scan_results') and code in self.scan_results:
                        r = self.scan_results[code]
                        s = r.get("total_score", -1)
                        matched = r.get("matched_count", 0)
                        if s >= 0:
                            if s >= 70:
                                sc_color = C_GREEN
                            elif s >= 45:
                                sc_color = C_YELLOW
                            elif s >= 20:
                                sc_color = C_FG2
                            else:
                                sc_color = C_RED
                            tk.Label(f, text=f"{s}", font=FONT_BOLD, bg=row_bg, fg=sc_color,
                                     width=5, anchor=tk.CENTER).place(x=430, y=7)
                            if matched > 0:
                                tk.Label(f, text=f"+{matched}", font=FONT_SMALL, bg=row_bg, fg=C_GREEN,
                                         width=4, anchor=tk.W).place(x=462, y=10)
                        else:
                            tk.Label(f, text="-", font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                                     width=5, anchor=tk.CENTER).place(x=430, y=8)
                    else:
                        tk.Label(f, text="-", font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                                 width=5, anchor=tk.CENTER).place(x=430, y=8)

                    q["row_bg"] = row_bg
                    self.pool_data.append(q)

                    f.code_ref = code
                    f.bind("<Button-1>", lambda e, c=code: self._select_and_show(c))
                    for child in f.winfo_children():
                        child.bind("<Button-1>", lambda e, c=code: self._select_and_show(c))

                    self.pool_items.append(f)
                except Exception as e:
                    logger.error(f"渲染第{i}行失败: {e}")
                    continue

            self.pool_inner.update_idletasks()
            self.pool_canvas.configure(scrollregion=self.pool_canvas.bbox("all"))
            logger.info(f"_show_pool 渲染完成: {len(self.pool_items)} 行")

        except Exception as e:
            logger.error(f"_show_pool 失败: {e}")

    def _select_and_show(self, code):
        """选中股票并显示分析结果"""
        # 如果已经扫描过，直接显示
        if code in self.scan_results:
            self._select_stock(code)
            self._show_analysis(self.scan_results[code])
        else:
            # 没扫描过，现场分析
            self._select_stock(code)
            self._analyze_single(code)

    def _analyze_single(self, code):
        """分析单只股票"""
        if self._analyzing:
            return
        self._analyzing = True
        self.card_name.configure(text=f"正在分析 {code}...", fg=C_FG2)

        def do_analyze():
            try:
                result = self.selector.analyze(code)
                self.scan_results[code] = result  # 缓存
                self.root.after(0, lambda: self._show_analysis(result))
            except Exception as e:
                self.root.after(0, lambda: self._show_error(str(e)))
            finally:
                self._analyzing = False

        threading.Thread(target=do_analyze, daemon=True).start()

    def _select_stock(self, code):
        """选中高亮"""
        for f in self.pool_items:
            try:
                bg = C_BG3 if self.pool_items.index(f) % 2 == 0 else C_BG
                # 检查是否有高分背景
                idx = self.pool_items.index(f)
                if idx < len(self.pool_data):
                    sc = self.pool_data[idx].get("score", -1)
                    if sc >= 60:
                        bg = "#0d2117"
                    elif sc >= 40:
                        bg = "#1d260d"
                f.configure(bg=bg)
                for ch in f.winfo_children():
                    try:
                        ch.configure(bg=bg)
                    except:
                        pass
            except:
                pass

        idx = next((i for i, q in enumerate(self.pool_data) if q.get("code") == code), -1)
        if idx >= 0:
            f = self.pool_items[idx]
            f.configure(bg=C_BG4)
            for ch in f.winfo_children():
                try:
                    ch.configure(bg=C_BG4)
                except:
                    pass

        self.selected_code = code

    def _on_pool_click(self, event):
        """单击事件"""
        cy = event.y
        for i, f in enumerate(self.pool_items):
            if f.winfo_exists() and f.winfo_ismapped():
                h = f.winfo_height()
                if 0 <= cy <= h:
                    code = getattr(f, 'code_ref', None)
                    if code:
                        self._select_and_show(code)
                    break
            cy -= f.winfo_height() if (f.winfo_exists() and f.winfo_ismapped()) else 0

    def _show_analysis(self, result):
        """显示分析结果到右侧面板"""
        if "error" in result:
            self._show_error(result["error"])
            return

        name = result.get("name", result["code"])
        code = result["code"]
        price = result.get("price", 0)
        change = result.get("change_pct", 0)
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
        price_color = C_GREEN if change >= 0 else C_RED

        # 信息卡
        self.card_name.configure(text=f"{name}  ({code})", font=FONT_TITLE, fg=C_FG)
        self.card_price.configure(text=f"¥{price:.2f}" if price else "¥--", fg=price_color)
        self.card_change.configure(text=change_str, fg=price_color)

        # ── 四维度评分卡 ────────────────────────────────
        score_card = result.get("score_card", {})
        grade = result.get("grade", "-")
        grade_color = score_card.get("grade_color", C_FG2)
        
        self.card_grade.configure(text=grade, fg=grade_color)
        
        profit_sc = score_card.get("profit_score", 0)
        risk_sc = score_card.get("risk_score", 0)
        quality_sc = score_card.get("quality_score", 0)
        practical_sc = score_card.get("practical_score", 0)
        
        self.card_profit.configure(text=f"盈利 {profit_sc:.0f}", fg=C_GREEN if profit_sc >= 15 else (C_YELLOW if profit_sc >= 8 else C_RED))
        self.card_risk.configure(text=f"风控 {risk_sc:.0f}", fg=C_GREEN if risk_sc >= 25 else (C_YELLOW if risk_sc >= 15 else C_RED))
        self.card_quality.configure(text=f"质量 {quality_sc:.0f}", fg=C_GREEN if quality_sc >= 15 else (C_YELLOW if quality_sc >= 8 else C_FG2))
        self.card_practical.configure(text=f"实战 {practical_sc:.0f}", fg=C_GREEN if practical_sc >= 10 else (C_YELLOW if practical_sc >= 6 else C_FG2))
        
        total_score = result.get("total_score", 0)
        if total_score >= 75:
            score_color = C_GREEN
        elif total_score >= 50:
            score_color = C_YELLOW
        else:
            score_color = C_FG2
        self.card_score.configure(text=f"总分 {total_score:.0f}", fg=score_color)

        sug = result.get("suggestion", "")
        if "买入" in sug:
            sug_color = C_GREEN
        elif "关注" in sug:
            sug_color = C_YELLOW
        else:
            sug_color = C_FG2
        self.card_suggest.configure(text=sug, fg=sug_color)

        matched = result.get("matched_count", 0)
        self.card_matched.configure(text=f"通过{matched}/11")

        # 评分理由：汇总通过和未通过的策略
        reasons_pass = []
        reasons_fail = []
        for s in result.get("strategies", []):
            sname, matched_s, reason, score_val = s
            if matched_s:
                reasons_pass.append(sname)
            else:
                reasons_fail.append(sname)
        reason_parts = []
        if reasons_pass:
            reason_parts.append(f"通过: {', '.join(reasons_pass)}")
        if reasons_fail:
            reason_parts.append(f"未过: {', '.join(reasons_fail[:5])}")
        self.card_reason.configure(text=" | ".join(reason_parts))

        # 记录事件日志
        self._log_event(code, f"分析完成 {grade}级 总分{total_score:.0f} {sug}")

        # 策略列表
        for sname_s, s_info in self.strategy_widgets.items():
            orig_bg = s_info["bg"]
            s_info["status"].configure(text="--", fg=C_FG2)
            s_info["reason"].configure(text="未分析", fg=C_FG2)
            s_info["score"].configure(text="-", fg=C_FG2)
            s_info["frame"].configure(bg=orig_bg)
            for ch in s_info["frame"].winfo_children():
                try:
                    ch.configure(bg=orig_bg)
                except:
                    pass

        for s in result.get("strategies", []):
            sname, matched_s, reason, score_val = s
            if sname in self.strategy_widgets:
                w = self.strategy_widgets[sname]
                if matched_s:
                    w["status"].configure(text="✅", fg=C_GREEN)
                    w["reason"].configure(text=reason, fg=C_GREEN)
                    w["score"].configure(text=f"{score_val}", fg=C_GREEN)
                    w["frame"].configure(bg="#0d2117")
                    for ch in w["frame"].winfo_children():
                        try:
                            ch.configure(bg="#0d2117")
                        except:
                            pass
                else:
                    w["status"].configure(text="❌", fg=C_RED)
                    w["reason"].configure(text=reason, fg=C_FG2)
                    w["score"].configure(text="-", fg=C_FG2)

        # 价位建议
        self.price_current.configure(text=f"现价  ¥{price:.2f}" if price else "现价  --")

        sup_levels = result.get("support_levels", [])
        self.price_support.configure(text=f"支撑位  {' / '.join([f'{s:.2f}' for s in sup_levels])}" if sup_levels else "支撑位  --")

        res_levels = result.get("resistance_levels", [])
        self.price_resist.configure(text=f"阻力位  {' / '.join([f'{r:.2f}' for r in res_levels])}" if res_levels else "阻力位  --")

        buy_zone = result.get("buy_zone", {})
        self.price_buy.configure(text=f"建议买入区间  ¥{buy_zone['low']:.2f} ~ ¥{buy_zone['high']:.2f}" if buy_zone and buy_zone.get("low") else "建议买入区间  --")

        sell_zone = result.get("sell_zone", {})
        self.price_sell.configure(text=f"建议卖出区间  ¥{sell_zone['low']:.2f} ~ ¥{sell_zone['high']:.2f}" if sell_zone and sell_zone.get("low") else "建议卖出区间  --")

        stop = result.get("stop_loss", 0)
        self.price_stop.configure(text=f"止损价  ¥{stop:.2f}" if stop else "止损价  --")

        target = result.get("target_price", 0)
        self.price_target.configure(text=f"目标价  ¥{target:.2f}" if target else "目标价  --")

        ratio = result.get("risk_reward_ratio", 0)
        if ratio is not None and ratio != 0:
            if ratio < 0:
                rc = "#FF4444"
                self.price_ratio.configure(text=f"风险收益比  {ratio:.2f} : 1 ⚠️追高", fg=rc)
            elif ratio >= 2:
                rc = C_GREEN
                self.price_ratio.configure(text=f"风险收益比  {ratio:.2f} : 1", fg=rc)
            elif ratio >= 1:
                rc = C_YELLOW
                self.price_ratio.configure(text=f"风险收益比  {ratio:.2f} : 1", fg=rc)
            else:
                rc = C_FG2
                self.price_ratio.configure(text=f"风险收益比  {ratio:.2f} : 1（偏低）", fg=rc)
        else:
            self.price_ratio.configure(text="风险收益比  --")

        patterns = result.get("patterns", [])
        if patterns:
            p_text = "  ".join([
                ("🟢" if p["signal"] == 1 else ("🔴" if p["signal"] == -1 else "⚪")) + p["name"]
                for p in patterns[:6]
            ])
            self.price_patterns.configure(text=p_text, fg=C_FG)
        else:
            self.price_patterns.configure(text="暂无明确形态", fg=C_FG2)

        # ── 操作建议详情面板 ─────────────────────────
        sug = result.get("suggestion", "")
        if "买入" in sug:
            sug_color = C_GREEN
            sug_icon = "🟢"
        elif "关注" in sug:
            sug_color = C_YELLOW
            sug_icon = "🟡"
        else:
            sug_color = C_FG2
            sug_icon = "⚪"
        self.advice_suggest.configure(text=f"{sug_icon} {sug}", fg=sug_color)

        ratio = result.get("risk_reward_ratio", 0)
        if ratio is not None and ratio != 0:
            if ratio < 0:
                rc = "#FF4444"  # 红色警告：追高风险
                self.advice_ratio.configure(text=f"⚠️ 风险收益比 {ratio:.2f} : 1（追高）", fg=rc)
            elif ratio >= 2:
                rc = C_GREEN
                self.advice_ratio.configure(text=f"风险收益比 {ratio:.2f} : 1", fg=rc)
            elif ratio >= 1:
                rc = C_YELLOW
                self.advice_ratio.configure(text=f"风险收益比 {ratio:.2f} : 1", fg=rc)
            else:
                rc = C_FG2
                self.advice_ratio.configure(text=f"风险收益比 {ratio:.2f} : 1（偏低）", fg=rc)
        else:
            self.advice_ratio.configure(text="风险收益比  --", fg=C_FG2)

        # 买入理由：汇总通过策略的核心逻辑
        matched_strategies = [s[0] for s in result.get("strategies", []) if s[1]]
        matched_count = len(matched_strategies)
        if matched_strategies:
            reasons_text = "、".join(matched_strategies)
            self.advice_reasons.configure(text=f"{reasons_text}", fg=C_GREEN)
        else:
            self.advice_reasons.configure(text="暂无策略通过", fg=C_FG2)

        stop = result.get("stop_loss", 0)
        self.advice_stop.configure(text=f"止损价  ¥{stop:.2f}" if stop else "止损价  --")
        target = result.get("target_price", 0)
        self.advice_target.configure(text=f"目标价  ¥{target:.2f}" if target else "目标价  --")
        buy_zone = result.get("buy_zone", {})
        if buy_zone and buy_zone.get("low"):
            self.advice_buyzone.configure(text=f"买入区间 ¥{buy_zone['low']:.2f}~¥{buy_zone['high']:.2f}")
        else:
            self.advice_buyzone.configure(text="买入区间  --")
        self.advice_matched.configure(text=f"通过 {matched_count}/11 策略")

        # ── 风控状态显示 ──────────────────────────────
        risk_approved = result.get("risk_approved", True)
        risk_warnings = result.get("risk_warnings", [])
        risk_rejected = result.get("risk_rejected_by", [])
        
        if risk_approved:
            self.risk_indicator.configure(text="● 正常", fg=C_GREEN)
        else:
            self.risk_indicator.configure(text="● 风险", fg=C_RED)
            self._log_event(result["code"], f"风控拒绝: {risk_rejected[0] if risk_rejected else '未知原因'}")
        
        if risk_warnings:
            for w in risk_warnings[:3]:
                self._log_event(result["code"], f"警告: {w}")

        self._select_stock(result["code"])

    def _show_error(self, msg):
        self.card_name.configure(text=f"❌ {msg}", fg=C_RED)

    def _load_sectors(self):
        def do_load():
            try:
                sectors = self.selector.get_sectors()
                self.root.after(0, lambda: self._show_sectors(sectors))
            except Exception as e:
                logger.error(f"加载板块失败: {e}")
        threading.Thread(target=do_load, daemon=True).start()

    def _show_sectors(self, sectors):
        for i, lbl in enumerate(self.sector_labels):
            if i < len(sectors):
                s = sectors[i]
                change = s.get("change_pct", 0)
                color = C_GREEN if change >= 0 else C_RED
                lbl.configure(text=f"{s['name']} {change:+.1f}%", fg=color)
            else:
                lbl.configure(text="--", fg=C_FG2)

    def _log_event(self, code: str, message: str):
        """记录事件到日志面板"""
        ts = time.strftime("%H:%M:%S")
        # 缩短日志消息避免截断：限制code长度
        short_code = code[:4] if len(code) > 4 else code
        entry = f"{ts} {short_code} {message}"
        self.event_log.insert(0, entry)
        self.event_log = self.event_log[:50]  # 保留最近50条
        
        # 保存到文件供调试
        try:
            with open(os.path.join(WORK_DIR, "scan_log.txt"), "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except:
            pass
        
        if hasattr(self, 'event_listbox'):
            self.root.after(0, self._update_event_display)

    def _update_event_display(self):
        """更新事件日志显示"""
        if hasattr(self, 'event_listbox'):
            self.event_listbox.delete(0, tk.END)
            for entry in self.event_log:
                self.event_listbox.insert(tk.END, entry)
            # 高亮最新条目
            if self.event_log:
                self.event_listbox.see(0)

    # ═══════════════════════════════════════════════════════
    #  事件日志面板 - 增强显示（可调边距）
    # ═══════════════════════════════════════════════════════
    def _build_event_log_panel(self, body):
        """右侧：事件日志面板（三省六部风格）"""
        # 事件日志面板（最右侧窄条）
        log_panel = tk.Frame(body, bg=C_BG2, width=220)
        log_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        log_panel.pack_propagate(False)

        # 标题
        hdr = tk.Frame(log_panel, bg=C_BG3, height=34)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📜 事件日志", font=FONT_BOLD, bg=C_BG3, fg=C_ACCENT).pack(side=tk.LEFT, padx=12, pady=8)

        # 风控状态指示灯
        risk_status = tk.Frame(log_panel, bg=C_BG3, height=40)
        risk_status.pack(fill=tk.X)
        risk_status.pack_propagate(False)

        self.risk_indicator = tk.Label(risk_status, text="● 正常", font=FONT_BOLD, bg=C_BG3, fg=C_GREEN)
        self.risk_indicator.pack(pady=8)

        # 事件列表 - 增加左右边距
        list_frame = tk.Frame(log_panel, bg=C_BG)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.event_listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 8),
            bg=C_BG,
            fg=C_FG2,
            selectbackground=C_BG4,
            selectforeground=C_FG,
            highlightthickness=0,
            bd=0,
            activestyle='none',
        )
        self.event_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 滚动条
        log_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.event_listbox.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.event_listbox.configure(yscrollcommand=log_scroll.set)

    def _toggle_sort(self, header_text):
        """点击列头排序"""
        sort_map = {
            "名称": "name", "代码": "code", "现价": "price",
            "涨跌幅": "change_pct", "成交额(万)": "amount", "评分": "score",
        }
        key = sort_map.get(header_text, "change_pct")
        if key == self._sort_key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_key = key
            self._sort_reverse = True
        self._re_render_pool()
        arrow = "↓" if self._sort_reverse else "↑"
        self.pool_sort_label.configure(text=f"按{header_text}排序 {arrow} | 点击查看详情")

    def _re_render_pool(self):
        """按当前排序重新渲染股票池"""
        if not self.pool_data:
            return
        key = self._sort_key
        if key == "score":
            # 按扫描评分排序
            def get_score(q):
                c = q.get("code", "")
                if hasattr(self, 'scan_results') and c in self.scan_results:
                    return self.scan_results[c].get("total_score", -1)
                return -1
            self.pool_data.sort(key=get_score, reverse=self._sort_reverse)
        else:
            self.pool_data.sort(key=lambda x: x.get(key, 0) or 0, reverse=self._sort_reverse)
        # 重建列表
        for w in self.pool_inner.winfo_children():
            w.destroy()
        self.pool_items.clear()
        for i, q in enumerate(self.pool_data):
            try:
                self._render_pool_row(i, q)
            except Exception as e:
                logger.error(f"重渲染第{i}行失败: {e}")
        self.pool_inner.update_idletasks()
        self.pool_canvas.configure(scrollregion=self.pool_canvas.bbox("all"))

    def _render_pool_row(self, i, q):
        """渲染单行股票（从pool_data）"""
        code = q.get("code", "")
        name = q.get("name", code) or code
        price = q.get("price", 0) or 0
        change = q.get("change_pct", 0) or 0
        amount = q.get("amount", 0) or 0
        amount_w = amount / 1e4 if amount else 0

        row_bg = C_BG3 if i % 2 == 0 else C_BG
        f = tk.Frame(self.pool_inner, bg=row_bg, height=34, cursor="hand2")
        f.pack(fill=tk.X, padx=0, pady=0)
        f.pack_propagate(False)

        name_color = C_GREEN if change >= 0 else C_RED
        tk.Label(f, text=f"{name}", font=FONT_BOLD, bg=row_bg, fg=name_color,
                 width=9, anchor=tk.W).place(x=6, y=7)
        tk.Label(f, text=f"{code}", font=FONT_CODE, bg=row_bg, fg=C_FG2,
                 width=7, anchor=tk.W).place(x=96, y=9)

        price_color = C_GREEN if change >= 0 else C_RED
        price_str = f"{price:.2f}" if price else "--"
        tk.Label(f, text=price_str, font=FONT_CODE, bg=row_bg, fg=price_color,
                 width=8, anchor=tk.E).place(x=170, y=8)

        change_str = f"{change:+.2f}%" if change else "--"
        tk.Label(f, text=change_str, font=("Consolas", 9, "bold"), bg=row_bg, fg=price_color,
                 width=9, anchor=tk.E).place(x=248, y=8)

        amount_str = f"{amount_w:.0f}" if amount_w else "--"
        tk.Label(f, text=amount_str, font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                 width=10, anchor=tk.E).place(x=332, y=8)

        if hasattr(self, 'scan_results') and code in self.scan_results:
            r = self.scan_results[code]
            s = r.get("total_score", -1)
            matched = r.get("matched_count", 0)
            sug = r.get("suggestion", "")
            if s >= 0:
                if s >= 70:
                    sc_color = C_GREEN
                elif s >= 45:
                    sc_color = C_YELLOW
                elif s >= 20:
                    sc_color = C_FG2
                else:
                    sc_color = C_RED
                tk.Label(f, text=f"{s}", font=FONT_BOLD, bg=row_bg, fg=sc_color,
                         width=5, anchor=tk.CENTER).place(x=430, y=7)
                if matched > 0:
                    tk.Label(f, text=f"+{matched}", font=FONT_SMALL, bg=row_bg, fg=C_GREEN,
                             width=4, anchor=tk.W).place(x=462, y=10)
                # 操作建议列
                if sug:
                    if "买入" in sug:
                        sug_color = C_GREEN
                        sug_text = "🟢买入"
                    elif "关注" in sug or "观望" in sug:
                        sug_color = C_YELLOW
                        sug_text = "🟡关注"
                    else:
                        sug_color = C_FG2
                        sug_text = "⚪观望"
                else:
                    sug_color = C_FG2
                    sug_text = "--"
                tk.Label(f, text=sug_text, font=("Consolas", 9), bg=row_bg, fg=sug_color,
                         width=7, anchor=tk.CENTER).place(x=495, y=8)
            else:
                tk.Label(f, text="-", font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                         width=5, anchor=tk.CENTER).place(x=430, y=8)
        else:
            tk.Label(f, text="-", font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                     width=5, anchor=tk.CENTER).place(x=430, y=8)

        q["row_bg"] = row_bg
        f.code_ref = code
        f.bind("<Button-1>", lambda e, c=code: self._select_and_show(c))
        for child in f.winfo_children():
            child.bind("<Button-1>", lambda e, c=code: self._select_and_show(c))
        self.pool_items.append(f)

    def _toggle_auto(self):
        if getattr(self, '_auto_refresh', True):
            self._auto_refresh = False
            self.auto_btn.configure(text="▶ 启动自动", bg=C_GREEN, fg="white")
        else:
            self._auto_refresh = True
            self.auto_btn.configure(text="⏸ 停止自动", bg=C_YELLOW, fg="white")
            self._schedule_refresh()

    def _schedule_refresh(self):
        if getattr(self, '_auto_refresh', True):
            self.root.after(60000, self._refresh_pool)
            self.root.after(60000, self._load_sectors)
            self.root.after(60000, self._schedule_refresh)

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = StockSelectorApp()
        app.run()
    except Exception as e:
        import traceback
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动错误", f"程序启动失败:\n{e}\n\n{traceback.format_exc()}")
        except:
            print(f"Fatal error: {e}")
            traceback.print_exc()
