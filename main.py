# -*- coding: utf-8 -*-
"""
智能选股系统 v3.0 - 专业级GUI
股票池实时监控 + 策略详细分析 + 价位建议

功能：
- 108只自选股实时行情监控
- 11种选股策略详细分析（过/不过都展示原因）
- 61种K线形态识别
- 价位建议（支撑/阻力/买入/卖出/止损/目标）
- 板块热点实时追踪
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("StockSelector")

if getattr(sys, 'frozen', False):
    WORK_DIR = os.path.dirname(sys.executable)
else:
    WORK_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORK_DIR)

from selector import StockSelector


# ═══════════════════════════════════════════════════════
#  配色方案（专业深色Bloomberg风格）
# ═══════════════════════════════════════════════════════
C_BG       = "#0d1117"   # 主背景
C_BG2      = "#161b22"   # 卡片背景
C_BG3      = "#21262d"   # 行背景
C_BG4      = "#2d333b"   # 悬停/选中
C_FG       = "#e6edf3"   # 主文字
C_FG2      = "#8b949e"   # 次要文字
C_ACCENT   = "#58a6ff"   # 强调蓝
C_GREEN    = "#3fb950"   # 涨/买
C_RED      = "#f85149"   # 跌/卖
C_YELLOW   = "#d29922"   # 警示/关注
C_PURPLE   = "#bc8cff"   # 特殊标记
C_BORDER   = "#30363d"   # 边框

# 字体
FONT_TITLE = ("Microsoft YaHei", 15, "bold")
FONT_MAIN  = ("Microsoft YaHei", 10)
FONT_BOLD  = ("Microsoft YaHei", 10, "bold")
FONT_CODE  = ("Consolas", 10)
FONT_SMALL = ("Microsoft YaHei", 8)
FONT_PRICE = ("Consolas", 22, "bold")
FONT_SCORE = ("Consolas", 28, "bold")


# ═══════════════════════════════════════════════════════
#  主应用
# ═══════════════════════════════════════════════════════
class StockSelectorApp:
    def __init__(self):
        self.selector = StockSelector()
        self._analyzing = False  # 防重复点击
        self.root = tk.Tk()
        self.root.title("智能选股系统 v3.0")
        self.root.geometry("1400x850")
        self.root.minsize(1200, 700)
        self.root.configure(bg=C_BG)

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        self._build_ui()
        self._center_window()

        # 定时刷新
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

        # Logo区
        logo = tk.Label(top, text="📊 智能选股系统", font=FONT_TITLE, bg=C_BG2, fg=C_ACCENT)
        logo.pack(side=tk.LEFT, padx=16, pady=0)

        tk.Label(top, text="v3.0", font=FONT_SMALL, bg=C_BG2, fg=C_FG2).pack(side=tk.LEFT, padx=(2, 0), pady=14)

        sep = tk.Frame(top, bg=C_BORDER, width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=10)

        # 统计标签
        self.stats_label = tk.Label(top, text="股票池: -- 只  |  加载中...", font=FONT_MAIN, bg=C_BG2, fg=C_FG2)
        self.stats_label.pack(side=tk.LEFT, pady=14)

        sep2 = tk.Frame(top, bg=C_BORDER, width=1)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=10)

        # 刷新按钮
        self.refresh_btn = tk.Button(top, text="🔄 刷新行情", font=FONT_BOLD, bg=C_ACCENT, fg="white",
                                     relief=tk.FLAT, cursor="hand2", command=self._refresh_pool)
        self.refresh_btn.pack(side=tk.LEFT, pady=8, ipadx=12)

        self.auto_btn = tk.Button(top, text="⏸ 停止自动", font=FONT_BOLD, bg=C_YELLOW, fg="white",
                                  relief=tk.FLAT, cursor="hand2", command=self._toggle_auto)
        self.auto_btn.pack(side=tk.LEFT, pady=8, padx=6, ipadx=12)

        # 搜索框
        search_frame = tk.Frame(top, bg=C_BG2)
        search_frame.pack(side=tk.RIGHT, padx=16, pady=8)

        tk.Label(search_frame, text="分析股票:", font=FONT_MAIN, bg=C_BG2, fg=C_FG2).pack(side=tk.LEFT, padx=(0, 6))

        self.code_var = tk.StringVar()
        code_entry = tk.Entry(search_frame, textvariable=self.code_var, font=FONT_CODE, width=10,
                              bg=C_BG3, fg=C_FG, insertbackground=C_FG, relief=tk.FLAT, bd=0)
        code_entry.pack(side=tk.LEFT, ipady=5, padx=(0, 6))
        code_entry.insert(0, "002539")
        code_entry.bind("<Return>", lambda e: self._analyze_selected())

        self.analyze_btn = tk.Button(search_frame, text="🔍 分析", font=FONT_BOLD, bg=C_ACCENT, fg="white",
                                     relief=tk.FLAT, cursor="hand2", command=self._analyze_selected)
        self.analyze_btn.pack(side=tk.LEFT, ipadx=14, ipady=3)

        # ── 主体区域 (三栏) ──
        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 左侧：股票池列表 (35%)
        self._build_pool_panel(body)
        sep_v = tk.Frame(body, bg=C_BORDER, width=1)
        sep_v.pack(side=tk.LEFT, fill=tk.Y, padx=0)

        # 中间：分析详情 (65%)
        self._build_detail_panel(body)

    def _build_pool_panel(self, body):
        """左侧：股票池实时行情列表"""
        left = tk.Frame(body, bg=C_BG, width=480)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 6))
        left.pack_propagate(False)

        # 标题栏
        hdr = tk.Frame(left, bg=C_BG2, height=36)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋 自选股票池", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).pack(side=tk.LEFT, padx=12, pady=8)
        self.pool_sort_label = tk.Label(hdr, text="按涨幅排序", font=FONT_SMALL, bg=C_BG2, fg=C_FG2)
        self.pool_sort_label.pack(side=tk.RIGHT, padx=12, pady=8)

        # 表头
        col_hdr = tk.Frame(left, bg=C_BG3, height=30)
        col_hdr.pack(fill=tk.X)
        col_hdr.pack_propagate(False)
        headers = [("名称/代码", 0, 110), ("现价", 110, 80), ("涨跌幅", 190, 90), ("成交额(万)", 280, 100), ("评分", 380, 60)]
        for txt, x, w in headers:
            tk.Label(col_hdr, text=txt, font=FONT_SMALL, bg=C_BG3, fg=C_FG2).place(x=x, y=6, width=w)

        # 列表 (Canvas滚动)
        list_frame = tk.Frame(left, bg=C_BG)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.pool_canvas = tk.Canvas(list_frame, bg=C_BG, highlightthickness=0, bd=0)
        pool_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.pool_canvas.yview)
        self.pool_inner = tk.Frame(self.pool_canvas, bg=C_BG)

        self.pool_inner.bind("<Configure>",
            lambda e: self.pool_canvas.configure(scrollregion=self.pool_canvas.bbox("all")))
        self.pool_canvas.create_window((0, 0), window=self.pool_inner, anchor=tk.NW)
        self.pool_canvas.configure(yscrollcommand=pool_scroll.set)

        self.pool_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pool_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定双击
        self.pool_canvas.bind("<Double-Button-1>", self._on_pool_double_click)
        self.pool_inner.bind("<Double-Button-1>", self._on_pool_double_click)

        self.pool_items = []   # 存储行frame引用
        self.pool_data = []    # 存储股票数据

    def _build_detail_panel(self, body):
        """右侧：分析详情"""
        right = tk.Frame(body, bg=C_BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # ── 顶部股票信息卡 ──
        self.info_card = tk.Frame(right, bg=C_BG2, height=90)
        self.info_card.pack(fill=tk.X, pady=(0, 6))
        self.info_card.pack_propagate(False)
        self._build_info_card(self.info_card)

        # ── 中部：两栏 ──
        mid = tk.Frame(right, bg=C_BG)
        mid.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # 左侧：策略分析
        left_mid = tk.Frame(mid, bg=C_BG)
        left_mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 右侧：价位建议
        right_mid = tk.Frame(mid, bg=C_BG, width=300)
        right_mid.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        right_mid.pack_propagate(False)

        self._build_strategy_panel(left_mid)
        self._build_price_panel(right_mid)

        # ── 底部：板块热点 ──
        self._build_sector_panel(right)

    def _build_info_card(self, parent):
        """股票信息卡片"""
        self.card_name = tk.Label(parent, text="请从左侧股票池选择股票，或输入代码分析",
                                   font=FONT_MAIN, bg=C_BG2, fg=C_FG2)
        self.card_name.place(x=16, y=10, width=400)

        self.card_price = tk.Label(parent, text="--", font=FONT_PRICE, bg=C_BG2, fg=C_FG)
        self.card_price.place(x=16, y=36, width=160)

        self.card_change = tk.Label(parent, text="--", font=("Consolas", 13), bg=C_BG2, fg=C_FG2)
        self.card_change.place(x=170, y=44, width=120)

        # 评分
        score_frame = tk.Frame(parent, bg=C_BG3)
        score_frame.place(x=560, y=14, width=200, height=62)

        self.card_score = tk.Label(score_frame, text="--", font=FONT_SCORE, bg=C_BG3, fg=C_ACCENT)
        self.card_score.place(x=0, y=0, width=80)
        tk.Label(score_frame, text="综合评分", font=FONT_SMALL, bg=C_BG3, fg=C_FG2).place(x=0, y=44, width=80)

        self.card_suggest = tk.Label(score_frame, text="--", font=FONT_BOLD, bg=C_BG3, fg=C_FG2)
        self.card_suggest.place(x=90, y=16, width=100)
        tk.Label(score_frame, text="操作建议", font=FONT_SMALL, bg=C_BG3, fg=C_FG2).place(x=90, y=44, width=100)

        # 分割线
        sep = tk.Frame(parent, bg=C_BORDER, height=1)
        sep.place(x=0, y=82, relwidth=1)

    def _build_strategy_panel(self, parent):
        """策略分析面板"""
        hdr = tk.Frame(parent, bg=C_BG2, height=36)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📊 策略分析结果  (✅=通过  ❌=未通过)", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).pack(side=tk.LEFT, padx=12, pady=8)

        # 策略列表容器
        list_container = tk.Frame(parent, bg=C_BG)
        list_container.pack(fill=tk.BOTH, expand=True)

        # 策略字典: name -> {frame, status_label, reason_label, score_label}
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
            f = tk.Frame(list_container, bg=row_bg, height=38)
            f.pack(fill=tk.X, padx=4, pady=1)
            f.pack_propagate(False)

            # 状态图标
            status = tk.Label(f, text="--", font=("Consolas", 13), bg=row_bg, fg=C_FG2, width=4, anchor=tk.CENTER)
            status.pack(side=tk.LEFT, padx=(8, 4), pady=6)

            # 策略名
            name_lbl = tk.Label(f, text=name, font=FONT_BOLD, bg=row_bg, fg=C_FG, width=10, anchor=tk.W)
            name_lbl.pack(side=tk.LEFT, padx=(0, 6), pady=6)

            # 原因/条件
            reason_lbl = tk.Label(f, text=desc, font=FONT_SMALL, bg=row_bg, fg=C_FG2, anchor=tk.W)
            reason_lbl.pack(side=tk.LEFT, padx=(0, 6), pady=6, fill=tk.X, expand=True)

            # 评分
            score_lbl = tk.Label(f, text="-", font=FONT_CODE, bg=row_bg, fg=C_FG2, width=6, anchor=tk.E)
            score_lbl.pack(side=tk.RIGHT, padx=10, pady=6)

            self.strategy_widgets[name] = {
                "frame": f,
                "status": status,
                "reason": reason_lbl,
                "score": score_lbl,
                "bg": row_bg,
            }

    def _build_price_panel(self, parent):
        """价位建议面板"""
        hdr = tk.Frame(parent, bg=C_BG2, height=36)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="💰 价位建议", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).pack(side=tk.LEFT, padx=12, pady=8)

        self.price_container = tk.Frame(parent, bg=C_BG)
        self.price_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 当前价
        self.price_current = tk.Label(self.price_container, text="现价  --", font=("Consolas", 16, "bold"),
                                      bg=C_BG, fg=C_FG)
        self.price_current.pack(anchor=tk.W, pady=(0, 6))

        # 支撑位
        self.price_support = tk.Label(self.price_container, text="支撑位  --", font=FONT_MAIN,
                                      bg=C_BG, fg=C_GREEN)
        self.price_support.pack(anchor=tk.W, pady=2)

        # 阻力位
        self.price_resist = tk.Label(self.price_container, text="阻力位  --", font=FONT_MAIN,
                                    bg=C_BG, fg=C_RED)
        self.price_resist.pack(anchor=tk.W, pady=2)

        tk.Frame(self.price_container, bg=C_BORDER, height=1).pack(fill=tk.X, pady=6)

        # 买入区间
        self.price_buy = tk.Label(self.price_container, text="建议买入区间  --", font=FONT_BOLD,
                                  bg=C_BG, fg=C_GREEN)
        self.price_buy.pack(anchor=tk.W, pady=2)

        # 卖出区间
        self.price_sell = tk.Label(self.price_container, text="建议卖出区间  --", font=FONT_BOLD,
                                   bg=C_BG, fg=C_RED)
        self.price_sell.pack(anchor=tk.W, pady=2)

        # 止损位
        self.price_stop = tk.Label(self.price_container, text="止损价  --", font=FONT_MAIN,
                                   bg=C_BG, fg=C_YELLOW)
        self.price_stop.pack(anchor=tk.W, pady=2)

        # 目标价
        self.price_target = tk.Label(self.price_container, text="目标价  --", font=FONT_MAIN,
                                     bg=C_BG, fg=C_ACCENT)
        self.price_target.pack(anchor=tk.W, pady=2)

        tk.Frame(self.price_container, bg=C_BORDER, height=1).pack(fill=tk.X, pady=6)

        # 风险收益比
        self.price_ratio = tk.Label(self.price_container, text="风险收益比  --", font=FONT_MAIN,
                                    bg=C_BG, fg=C_FG2)
        self.price_ratio.pack(anchor=tk.W, pady=2)

        # 价位理由
        self.price_reason = tk.Label(self.price_container, text="", font=FONT_SMALL,
                                    bg=C_BG, fg=C_FG2, wraplength=270, justify=tk.LEFT)
        self.price_reason.pack(anchor=tk.W, pady=4)

        # K线形态
        tk.Frame(self.price_container, bg=C_BORDER, height=1).pack(fill=tk.X, pady=6)
        tk.Label(self.price_container, text="🎯 K线形态", font=FONT_BOLD, bg=C_BG, fg=C_ACCENT).pack(anchor=tk.W, pady=2)
        self.price_patterns = tk.Label(self.price_container, text="暂无形态", font=FONT_SMALL,
                                       bg=C_BG, fg=C_FG2, wraplength=270, justify=tk.LEFT)
        self.price_patterns.pack(anchor=tk.W, pady=2)

    def _build_sector_panel(self, parent):
        """底部板块热点"""
        bottom = tk.Frame(parent, bg=C_BG2, height=90)
        bottom.pack(fill=tk.X, pady=(6, 0))
        bottom.pack_propagate(False)

        tk.Label(bottom, text="🔥 板块热点", font=FONT_BOLD, bg=C_BG2, fg=C_ACCENT).place(x=12, y=8)

        # 板块容器
        self.sector_container = tk.Frame(bottom, bg=C_BG2)
        self.sector_container.place(x=12, y=32, relwidth=1, relheight=1)
        self.sector_labels = []

        # 预设20个标签槽位
        for i in range(20):
            lbl = tk.Label(self.sector_container, text="--", font=FONT_SMALL, bg=C_BG3, fg=C_FG,
                           padx=8, pady=2, relief=tk.FLAT)
            lbl.pack(side=tk.LEFT, padx=2, pady=2)
            self.sector_labels.append(lbl)

    # ───────────────────────────────────────────────
    #  事件 & 业务逻辑
    # ───────────────────────────────────────────────
    def _refresh_pool(self):
        """刷新股票池实时行情"""
        self.refresh_btn.configure(text="⏳ 刷新中...", state=tk.DISABLED)
        self.stats_label.configure(text="股票池: --  |  正在加载行情...")

        def do_refresh():
            try:
                quotes = self.selector.get_pool_realtime()
                self.root.after(0, lambda: self._show_pool(quotes))
            except Exception as e:
                logger.error(f"刷新行情失败: {e}")
                self.root.after(0, lambda: self.refresh_btn.configure(text="🔄 刷新行情", state=tk.NORMAL))

        threading.Thread(target=do_refresh, daemon=True).start()

    def _show_pool(self, quotes):
        """显示股票池列表"""
        self.refresh_btn.configure(text="🔄 刷新行情", state=tk.NORMAL)
        self.stats_label.configure(text=f"股票池: {len(quotes)} 只  |  更新时间 {time.strftime('%H:%M:%S')}")

        # 清空
        for w in self.pool_inner.winfo_children():
            w.destroy()
        self.pool_items.clear()
        self.pool_data.clear()

        if not quotes:
            tk.Label(self.pool_inner, text="暂无数据，请检查网络", font=FONT_MAIN, bg=C_BG, fg=C_RED).pack(pady=20)
            return

        # 按涨幅排序
        quotes.sort(key=lambda x: x.get("change_pct", 0), reverse=True)

        for i, q in enumerate(quotes):
            code = q.get("code", "")
            name = q.get("name", code)
            price = q.get("price", 0)
            change = q.get("change_pct", 0)
            amount = q.get("amount", 0)  # 元
            amount_w = amount / 1e4 if amount else 0

            row_bg = C_BG3 if i % 2 == 0 else C_BG
            f = tk.Frame(self.pool_inner, bg=row_bg, height=32, cursor="hand2")
            f.pack(fill=tk.X, padx=0, pady=0)
            f.pack_propagate(False)

            # 名称+代码
            name_color = C_GREEN if change >= 0 else C_RED
            tk.Label(f, text=f"{name}", font=FONT_BOLD, bg=row_bg, fg=name_color,
                     width=8, anchor=tk.W).place(x=8, y=6)
            tk.Label(f, text=f"{code}", font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                     width=8, anchor=tk.W).place(x=8, y=20)

            # 现价
            price_color = C_GREEN if change >= 0 else C_RED
            price_str = f"{price:.2f}" if price else "--"
            tk.Label(f, text=price_str, font=FONT_CODE, bg=row_bg, fg=price_color,
                     width=9, anchor=tk.E).place(x=108, y=8)

            # 涨跌幅
            change_str = f"{change:+.2f}%" if change else "--"
            change_color = C_GREEN if change >= 0 else C_RED
            tk.Label(f, text=change_str, font=("Consolas", 9, "bold"), bg=row_bg, fg=change_color,
                     width=10, anchor=tk.E).place(x=192, y=8)

            # 成交额(万)
            amount_str = f"{amount_w:.0f}" if amount_w else "--"
            tk.Label(f, text=amount_str, font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                     width=11, anchor=tk.E).place(x=280, y=8)

            # 评分占位（待分析）
            tk.Label(f, text="-", font=FONT_SMALL, bg=row_bg, fg=C_FG2,
                     width=8, anchor=tk.E).place(x=378, y=8)

            # 保存数据
            q["row_bg"] = row_bg
            self.pool_data.append(q)

            # 绑定事件
            f.bind("<Button-1>", lambda e, code=code: self._select_stock(code))
            f.bind("<Double-Button-1>", lambda e, code=code: self._analyze_stock(code))

            for child in f.winfo_children():
                child.bind("<Button-1>", lambda e, code=code: self._select_stock(code))
                child.bind("<Double-Button-1>", lambda e, code=code: self._analyze_stock(code))

            self.pool_items.append(f)

    def _select_stock(self, code):
        """选中股票"""
        # 清除之前选中
        for f, old_code in zip(self.pool_items, [q["code"] for q in self.pool_data]):
            bg = next((q["row_bg"] for q in self.pool_data if q["code"] == old_code), C_BG)
            f.configure(bg=bg)
            for child in f.winfo_children():
                try:
                    child.configure(bg=bg)
                except:
                    pass

        # 标记选中
        idx = next((i for i, q in enumerate(self.pool_data) if q["code"] == code), -1)
        if idx >= 0:
            f = self.pool_items[idx]
            f.configure(bg=C_BG4)
            for child in f.winfo_children():
                try:
                    child.configure(bg=C_BG4)
                except:
                    pass

        self.selected_code = code

    def _on_pool_double_click(self, event):
        """双击股票"""
        region = self.pool_canvas.find_overlapping(event.x, event.y, event.x, event.y)
        if region:
            item_id = self.pool_canvas.gettags(region[0])[0] if self.pool_canvas.gettags(region[0]) else None
        # 简化处理
        pass

    def _analyze_stock(self, code):
        """分析指定股票"""
        self.selected_code = code
        self._analyze_selected()

    # 防重复点击标记（在__init__中初始化）

    def _analyze_selected(self):
        """分析当前选中的或输入框的股票"""
        if self._analyzing:
            return  # 防止重复点击
        
        code = getattr(self, 'selected_code', None)
        if not code:
            code = self.code_var.get().strip()
        if not code:
            return

        self._analyzing = True
        self.analyze_btn.configure(text="⏳ 分析中...", state=tk.DISABLED)
        self.card_name.configure(text=f"正在分析 {code}...", fg=C_FG2)

        def do_analyze():
            try:
                result = self.selector.analyze(code)
                self.root.after(0, lambda: self._show_analysis(result))
            except Exception as e:
                logger.error(f"分析失败: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: self._show_error(str(e)))
            finally:
                # 确保无论成功失败都恢复状态
                self._analyzing = False

        threading.Thread(target=do_analyze, daemon=True).start()

    def _show_analysis(self, result):
        """显示分析结果"""
        self.analyze_btn.configure(text="🔍 分析", state=tk.NORMAL)

        if "error" in result:
            self._show_error(result["error"])
            return

        name = result.get("name", result["code"])
        price = result.get("price", 0)
        change = result.get("change_pct", 0)
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
        price_color = C_GREEN if change >= 0 else C_RED

        # 信息卡
        self.card_name.configure(text=f"{name}  ({result['code']})", font=FONT_TITLE, fg=C_FG)
        self.card_price.configure(text=f"¥{price:.2f}" if price else "¥--", fg=price_color)
        self.card_change.configure(text=change_str, fg=price_color)

        score = result.get("total_score", 0)
        if score >= 75:
            score_color = C_GREEN
        elif score >= 50:
            score_color = C_YELLOW
        else:
            score_color = C_FG2
        self.card_score.configure(text=f"{score}", fg=score_color)

        sug = result.get("suggestion", "")
        if "买入" in sug:
            sug_color = C_GREEN
        elif "关注" in sug:
            sug_color = C_YELLOW
        else:
            sug_color = C_FG2
        self.card_suggest.configure(text=sug, fg=sug_color)

        # 更新策略列表
        for name_s, s_info in self.strategy_widgets.items():
            s_info["status"].configure(text="--", fg=C_FG2)
            s_info["reason"].configure(text="未分析", fg=C_FG2)
            s_info["score"].configure(text="-", fg=C_FG2)
            s_info["frame"].configure(bg=s_info["bg"])
            for child in s_info["frame"].winfo_children():
                try:
                    child.configure(bg=s_info["bg"])
                except:
                    pass

        for s in result.get("strategies", []):
            sname, matched, reason, score_val = s
            if sname in self.strategy_widgets:
                w = self.strategy_widgets[sname]
                if matched:
                    w["status"].configure(text="✅", fg=C_GREEN)
                    w["reason"].configure(text=reason, fg=C_GREEN)
                    w["score"].configure(text=f"{score_val}", fg=C_GREEN)
                    w["frame"].configure(bg="#0d2117")
                    for child in w["frame"].winfo_children():
                        try:
                            child.configure(bg="#0d2117")
                        except:
                            pass
                else:
                    w["status"].configure(text="❌", fg=C_RED)
                    w["reason"].configure(text=reason, fg=C_FG2)
                    w["score"].configure(text="-", fg=C_FG2)

        # 价位建议
        self.price_current.configure(text=f"现价  ¥{price:.2f}" if price else "现价  --")

        sup_levels = result.get("support_levels", [])
        if sup_levels:
            self.price_support.configure(text=f"支撑位  {' / '.join([f'{s:.2f}' for s in sup_levels])}")
        else:
            self.price_support.configure(text="支撑位  --")

        res_levels = result.get("resistance_levels", [])
        if res_levels:
            self.price_resist.configure(text=f"阻力位  {' / '.join([f'{r:.2f}' for r in res_levels])}")
        else:
            self.price_resist.configure(text="阻力位  --")

        buy_zone = result.get("buy_zone", {})
        if buy_zone and buy_zone.get("low"):
            self.price_buy.configure(text=f"建议买入区间  ¥{buy_zone['low']:.2f} ~ ¥{buy_zone['high']:.2f}")
        else:
            self.price_buy.configure(text="建议买入区间  --")

        sell_zone = result.get("sell_zone", {})
        if sell_zone and sell_zone.get("low"):
            self.price_sell.configure(text=f"建议卖出区间  ¥{sell_zone['low']:.2f} ~ ¥{sell_zone['high']:.2f}")
        else:
            self.price_sell.configure(text="建议卖出区间  --")

        stop = result.get("stop_loss", 0)
        self.price_stop.configure(text=f"止损价  ¥{stop:.2f}" if stop else "止损价  --")

        target = result.get("target_price", 0)
        self.price_target.configure(text=f"目标价  ¥{target:.2f}" if target else "目标价  --")

        ratio = result.get("risk_reward_ratio", 0)
        if ratio:
            ratio_color = C_GREEN if ratio >= 2 else (C_YELLOW if ratio >= 1 else C_FG2)
            self.price_ratio.configure(text=f"风险收益比  {ratio:.2f} : 1", fg=ratio_color)
        else:
            self.price_ratio.configure(text="风险收益比  --")

        # 形态
        patterns = result.get("patterns", [])
        if patterns:
            p_text = "  ".join([
                ("🟢" if p["signal"] == 1 else ("🔴" if p["signal"] == -1 else "⚪")) + p["name"]
                for p in patterns[:6]
            ])
            self.price_patterns.configure(text=p_text, fg=C_FG)
        else:
            self.price_patterns.configure(text="暂无明确形态", fg=C_FG2)

        # 选中该股票在列表中的行
        self._select_stock(result["code"])

    def _show_error(self, msg):
        """显示错误"""
        self.analyze_btn.configure(text="🔍 分析", state=tk.NORMAL)
        self.card_name.configure(text=f"❌ 分析失败: {msg}", fg=C_RED)

    def _load_sectors(self):
        """加载板块热点"""
        def do_load():
            try:
                sectors = self.selector.get_sectors()
                self.root.after(0, lambda: self._show_sectors(sectors))
            except Exception as e:
                logger.error(f"加载板块失败: {e}")

        threading.Thread(target=do_load, daemon=True).start()

    def _show_sectors(self, sectors):
        """显示板块热点"""
        for i, lbl in enumerate(self.sector_labels):
            if i < len(sectors):
                s = sectors[i]
                change = s.get("change_pct", 0)
                color = C_GREEN if change >= 0 else C_RED
                lbl.configure(text=f"{s['name']} {change:+.1f}%", fg=color)
            else:
                lbl.configure(text="--", fg=C_FG2)

    def _toggle_auto(self):
        """切换自动刷新"""
        if getattr(self, '_auto_refresh', True):
            self._auto_refresh = False
            self.auto_btn.configure(text="▶ 启动自动", bg=C_GREEN, fg="white")
        else:
            self._auto_refresh = True
            self.auto_btn.configure(text="⏸ 停止自动", bg=C_YELLOW, fg="white")
            self._schedule_refresh()

    def _schedule_refresh(self):
        """定时刷新"""
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
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动错误", f"程序启动失败:\n{e}\n\n{traceback.format_exc()}")
        except:
            print(f"Fatal error: {e}")
            traceback.print_exc()
