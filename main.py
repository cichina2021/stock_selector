# -*- coding: utf-8 -*-
"""
智能选股系统 v2.1 - Windows GUI版
tkinter窗口界面，无需浏览器

启动方式：
    python main.py

打包Windows EXE：
    pyinstaller build_win.spec
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("StockSelector")

# 确保工作目录
if getattr(sys, 'frozen', False):
    WORK_DIR = os.path.dirname(sys.executable)
else:
    WORK_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORK_DIR)

from selector import StockSelector


class StockSelectorApp:
    """智能选股系统 GUI"""

    # 颜色方案（深色Bloomberg风格）
    BG = "#0a0e17"
    BG2 = "#111927"
    BG3 = "#1a2332"
    FG = "#e8edf3"
    FG2 = "#8899aa"
    BLUE = "#3b82f6"
    CYAN = "#06b6d4"
    RED = "#ef4444"
    GREEN = "#22c55e"
    YELLOW = "#eab308"
    ORANGE = "#f97316"

    def __init__(self):
        self.selector = StockSelector()
        self.root = tk.Tk()
        self.root.title("智能选股系统 v2.1")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        self.root.configure(bg=self.BG)

        # 尝试设置DPI感知
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        self._build_ui()
        self._load_sectors()

    def _build_ui(self):
        """构建界面"""
        # 顶部搜索栏
        top = tk.Frame(self.root, bg=self.BG2, height=56)
        top.pack(fill=tk.X, padx=0, pady=0)
        top.pack_propagate(False)

        # Logo
        logo = tk.Label(top, text="  📊 智能选股系统", font=("Microsoft YaHei", 14, "bold"),
                        bg=self.BG2, fg=self.FG)
        logo.pack(side=tk.LEFT, padx=8)

        tk.Label(top, text="11策略 | 61形态 | 板块热点", font=("Microsoft YaHei", 9),
                 bg=self.BG2, fg=self.FG2).pack(side=tk.LEFT, padx=4)

        # 搜索框
        search_frame = tk.Frame(top, bg=self.BG2)
        search_frame.pack(side=tk.RIGHT, padx=16)

        self.code_var = tk.StringVar()
        self.code_entry = tk.Entry(search_frame, textvariable=self.code_var,
                                    font=("Consolas", 12), width=14,
                                    bg=self.BG3, fg=self.FG, insertbackground=self.FG,
                                    relief=tk.FLAT, bd=0)
        self.code_entry.pack(side=tk.LEFT, ipady=6, padx=(0, 8))
        self.code_entry.insert(0, "002539")
        self.code_entry.bind("<Return>", lambda e: self._analyze())

        self.search_btn = tk.Button(search_frame, text="🔍 分析", font=("Microsoft YaHei", 10, "bold"),
                                     bg=self.BLUE, fg="white", relief=tk.FLAT,
                                     command=self._analyze, cursor="hand2")
        self.search_btn.pack(side=tk.LEFT, ipady=4, ipadx=16)

        # 主体区域
        body = tk.Frame(self.root, bg=self.BG)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # 左侧：策略结果 + 板块
        left = tk.Frame(body, bg=self.BG, width=380)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 8))
        left.pack_propagate(False)

        # 右侧：详细分析
        right = tk.Frame(body, bg=self.BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_left(left)
        self._build_right(right)

    def _build_left(self, parent):
        """左侧面板"""
        # 板块热点
        sector_label = tk.Label(parent, text="🔥 板块热点", font=("Microsoft YaHei", 11, "bold"),
                                bg=self.BG, fg=self.FG)
        sector_label.pack(anchor=tk.W, pady=(0, 4))

        self.sector_frame = tk.Frame(parent, bg=self.BG2, bd=0)
        self.sector_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 板块列表（用Canvas+Scrollbar实现滚动）
        self.sector_canvas = tk.Canvas(self.sector_frame, bg=self.BG2,
                                        highlightthickness=0, bd=0)
        sector_scroll = ttk.Scrollbar(self.sector_frame, orient=tk.VERTICAL,
                                       command=self.sector_canvas.yview)
        self.sector_inner = tk.Frame(self.sector_canvas, bg=self.BG2)

        self.sector_inner.bind("<Configure>",
            lambda e: self.sector_canvas.configure(scrollregion=self.sector_canvas.bbox("all")))
        self.sector_canvas.create_window((0, 0), window=self.sector_inner, anchor=tk.NW)
        self.sector_canvas.configure(yscrollcommand=sector_scroll.set)

        self.sector_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sector_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部：策略快速查看
        tk.Label(parent, text="📋 策略一览", font=("Microsoft YaHei", 11, "bold"),
                 bg=self.BG, fg=self.FG).pack(anchor=tk.W, pady=(4, 4))

        strategy_frame = tk.Frame(parent, bg=self.BG2, bd=0)
        strategy_frame.pack(fill=tk.X)

        strategies = [
            ("放量上涨", "量价齐升"), ("均线多头", "趋势向上"),
            ("停机坪", "强势整理"), ("回踩年线", "长期支撑"),
            ("突破平台", "横盘突破"), ("无大幅回撤", "趋势稳健"),
            ("海龟法则", "创新高"), ("高窄旗形", "强势形态"),
            ("MACD金叉", "技术信号"), ("KDJ超卖", "短线机会"),
            ("多因子", "量化评分"),
        ]

        for i, (name, desc) in enumerate(strategies):
            row = i // 2
            col = i % 2
            f = tk.Frame(strategy_frame, bg=self.BG3, bd=0)
            f.grid(row=row, column=col, padx=2, pady=2, sticky=tk.NSEW)
            strategy_frame.columnconfigure(col, weight=1)

            tk.Label(f, text=name, font=("Microsoft YaHei", 9, "bold"),
                     bg=self.BG3, fg=self.CYAN).pack(anchor=tk.W, padx=6, pady=(4, 0))
            tk.Label(f, text=desc, font=("Microsoft YaHei", 8),
                     bg=self.BG3, fg=self.FG2).pack(anchor=tk.W, padx=6, pady=(0, 4))

    def _build_right(self, parent):
        """右侧面板：分析结果"""
        # 标题
        self.result_header = tk.Frame(parent, bg=self.BG2, bd=0)
        self.result_header.pack(fill=tk.X, pady=(0, 8))

        self.stock_name = tk.Label(self.result_header, text="请输入股票代码并点击分析",
                                    font=("Microsoft YaHei", 16, "bold"),
                                    bg=self.BG2, fg=self.FG)
        self.stock_name.pack(anchor=tk.W, padx=16, pady=12)

        # 评分条
        self.score_frame = tk.Frame(parent, bg=self.BG2, bd=0)
        self.score_frame.pack(fill=tk.X, pady=(0, 8))

        self.score_label = tk.Label(self.score_frame, text="",
                                     font=("Microsoft YaHei", 28, "bold"),
                                     bg=self.BG2, fg=self.BLUE)
        self.score_label.pack(side=tk.LEFT, padx=16, pady=8)

        self.suggestion_label = tk.Label(self.score_frame, text="",
                                          font=("Microsoft YaHei", 14),
                                          bg=self.BG2, fg=self.FG2)
        self.suggestion_label.pack(side=tk.LEFT, padx=8, pady=8)

        # 详细结果区域
        detail_label = tk.Label(parent, text="📊 策略分析结果", font=("Microsoft YaHei", 11, "bold"),
                                bg=self.BG, fg=self.FG)
        detail_label.pack(anchor=tk.W, pady=(8, 4))

        # 用Treeview展示策略结果
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview",
                        background=self.BG2,
                        foreground=self.FG,
                        fieldbackground=self.BG2,
                        borderwidth=0,
                        rowheight=32,
                        font=("Microsoft YaHei", 10))
        style.configure("Dark.Treeview.Heading",
                        background=self.BG3,
                        foreground=self.CYAN,
                        borderwidth=0,
                        font=("Microsoft YaHei", 9, "bold"))
        style.map("Dark.Treeview",
                  background=[("selected", self.BG3)],
                  foreground=[("selected", self.FG)])

        tree_frame = tk.Frame(parent, bg=self.BG)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, style="Dark.Treeview",
                                  columns=("status", "strategy", "reason", "score"),
                                  show="headings", height=11)

        self.tree.heading("status", text="状态")
        self.tree.heading("strategy", text="策略")
        self.tree.heading("reason", text="入选理由 / 未入选原因")
        self.tree.heading("score", text="评分")

        self.tree.column("status", width=50, anchor=tk.CENTER)
        self.tree.column("strategy", width=90, anchor=tk.W)
        self.tree.column("reason", width=380, anchor=tk.W)
        self.tree.column("score", width=60, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 形态识别结果
        pattern_label = tk.Label(parent, text="🎯 K线形态识别", font=("Microsoft YaHei", 11, "bold"),
                                 bg=self.BG, fg=self.FG)
        pattern_label.pack(anchor=tk.W, pady=(12, 4))

        self.pattern_text = tk.Text(parent, height=4, font=("Microsoft YaHei", 10),
                                     bg=self.BG2, fg=self.FG, relief=tk.FLAT, bd=0,
                                     wrap=tk.WORD, state=tk.DISABLED)
        self.pattern_text.pack(fill=tk.X)

        # 总结
        self.summary_label = tk.Label(parent, text="", font=("Microsoft YaHei", 11),
                                       bg=self.BG, fg=self.FG2, wraplength=600, justify=tk.LEFT)
        self.summary_label.pack(anchor=tk.W, pady=(12, 0))

    def _analyze(self):
        """分析股票"""
        code = self.code_var.get().strip()
        if not code:
            return

        self.search_btn.configure(text="⏳ 分析中...", state=tk.DISABLED)
        self.stock_name.configure(text=f"正在分析 {code}...")

        # 后台线程执行分析
        def do_analyze():
            try:
                result = self.selector.analyze(code)
                self.root.after(0, lambda: self._show_result(result))
            except Exception as e:
                self.root.after(0, lambda: self._show_error(str(e)))

        threading.Thread(target=do_analyze, daemon=True).start()

    def _show_result(self, result):
        """显示分析结果"""
        self.search_btn.configure(text="🔍 分析", state=tk.NORMAL)

        if "error" in result:
            self._show_error(result["error"])
            return

        # 更新标题
        name = result.get("name", result["code"])
        price = result.get("price", 0)
        change = result.get("change_pct", 0)
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
        change_color = self.RED if change >= 0 else self.GREEN

        self.stock_name.configure(text=f"{name}  {result['code']}")

        # 评分
        score = result.get("total_score", 0)
        score_color = self.RED if score >= 75 else (self.YELLOW if score >= 50 else self.FG2)
        self.score_label.configure(text=f"{score}分", fg=score_color)

        suggestion = result.get("suggestion", "")
        sug_color = self.RED if "买入" in suggestion else (self.YELLOW if "关注" in suggestion else self.FG2)
        self.suggestion_label.configure(text=f"建议: {suggestion}", fg=sug_color)

        # 策略结果
        for item in self.tree.get_children():
            self.tree.delete(item)

        for s in result.get("strategies", []):
            name, matched, reason, score_val = s
            status = "✅" if matched else "❌"
            score_str = f"{score_val}" if matched else "-"
            tags = ("matched",) if matched else ("unmatched",)
            self.tree.insert("", tk.END, values=(status, name, reason, score_str), tags=tags)

        self.tree.tag_configure("matched", foreground=self.GREEN)
        self.tree.tag_configure("unmatched", foreground=self.FG2)

        # 形态识别
        self.pattern_text.configure(state=tk.NORMAL)
        self.pattern_text.delete("1.0", tk.END)

        patterns = result.get("patterns", [])
        if patterns:
            for p in patterns:
                signal = "🟢" if p["signal"] == 1 else ("🔴" if p["signal"] == -1 else "⚪")
                self.pattern_text.insert(tk.END, f"{signal} {p['name']}: {p['detail']}  ")
        else:
            self.pattern_text.insert(tk.END, "暂无明确形态信号")

        self.pattern_text.configure(state=tk.DISABLED)

        # 总结
        self.summary_label.configure(text=result.get("summary", ""))

    def _show_error(self, msg):
        """显示错误"""
        self.search_btn.configure(text="🔍 分析", state=tk.NORMAL)
        self.stock_name.configure(text=f"❌ 分析失败: {msg}")
        self.score_label.configure(text="")
        self.suggestion_label.configure(text="")

    def _load_sectors(self):
        """加载板块热点"""
        def do_load():
            try:
                industry = self.selector.data.get_sectors("industry", top_n=10)
                concept = self.selector.data.get_sectors("concept", top_n=10)
                all_sectors = (industry + concept)
                all_sectors.sort(key=lambda x: x["change_pct"], reverse=True)
                self.root.after(0, lambda: self._show_sectors(all_sectors[:20]))
            except Exception as e:
                logger.error(f"加载板块失败: {e}")

        threading.Thread(target=do_load, daemon=True).start()

    def _show_sectors(self, sectors):
        """显示板块列表"""
        # 清空
        for w in self.sector_inner.winfo_children():
            w.destroy()

        if not sectors:
            tk.Label(self.sector_inner, text="暂无数据", font=("Microsoft YaHei", 10),
                     bg=self.BG2, fg=self.FG2).pack(pady=20)
            return

        for i, s in enumerate(sectors):
            row = tk.Frame(self.sector_inner, bg=self.BG3 if i % 2 == 0 else self.BG2, bd=0)
            row.pack(fill=tk.X, padx=4, pady=1)

            name_text = s["name"]
            if len(name_text) > 8:
                name_text = name_text[:8] + ".."

            tk.Label(row, text=f" {name_text}", font=("Microsoft YaHei", 9),
                     bg=row["bg"], fg=self.FG, width=10, anchor=tk.W).pack(side=tk.LEFT, padx=2)

            change = s["change_pct"]
            color = self.RED if change >= 0 else self.GREEN
            tk.Label(row, text=f"{change:+.2f}%", font=("Consolas", 9, "bold"),
                     bg=row["bg"], fg=color, width=8, anchor=tk.E).pack(side=tk.RIGHT, padx=4)

            lead = s.get("lead_stock", "--")
            if lead and len(lead) > 6:
                lead = lead[:6]
            tk.Label(row, text=lead, font=("Microsoft YaHei", 8),
                     bg=row["bg"], fg=self.FG2, width=8, anchor=tk.E).pack(side=tk.RIGHT, padx=2)

    def run(self):
        """启动应用"""
        # 窗口居中
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

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
