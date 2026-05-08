# -*- coding: utf-8 -*-
"""
数据源管理 v3.0
- 新浪财经HTTP（主力）：实时行情 + K线
- 腾讯HTTP（备用）：实时行情
- 东方财富HTTP（备用）：板块数据
- 自动降级 + 60秒缓存 + 频率限制
"""
import requests
import pandas as pd
import numpy as np
import time
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  常量 & 全局缓存
# ──────────────────────────────────────────────
_SINA_HQ   = "https://hq.sinajs.cn/list={}"
_SINA_KLINE = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
_TENCENT_HQ = "https://qt.gtimg.cn/q={}"
_EM_QUOTE   = "https://push2.eastmoney.com/api/qt/stock/get"
_EM_SECTOR  = "https://push2.eastmoney.com/api/qt/clist/get"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn",
}

# 全局缓存（进程内）
_CACHE: Dict[str, tuple] = {}   # key → (data, timestamp)
_CACHE_TTL = 60                # 秒


def _get_cache(key: str) -> Optional[any]:
    """读取缓存"""
    if key not in _CACHE:
        return None
    data, ts = _CACHE[key]
    if time.time() - ts < _CACHE_TTL:
        return data
    del _CACHE[key]
    return None


def _set_cache(key: str, data: any):
    """写入缓存"""
    _CACHE[key] = (data, time.time())


# ──────────────────────────────────────────────
#  数据源类
# ──────────────────────────────────────────────
class DataSource:
    """
    数据源管理器 v3.0

    策略：新浪主力 → 腾讯备用 → 东财备用（板块）
    特点：
    - 自动降级（一个失败换下一个）
    - 60秒缓存
    - 批量请求（减少网络开销）
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        # 流量控制：滑动窗口，每分钟最多60次
        self._requests: List[float] = []

    # ──────────────────────────────────────────
    #  实时行情
    # ──────────────────────────────────────────
    def get_realtime(self, codes: List[str]) -> List[Dict]:
        """获取实时行情"""
        logger.info(f"=== DataSource.get_realtime called, codes={codes}")
        if not codes:
            logger.info("=== 空代码列表，返回[]")
            return []

        cache_key = f"rt_{','.join(codes[:20])}"
        cached = _get_cache(cache_key)
        if cached is not None:
            logger.info("=== 命中缓存")
            return cached

        # ── 方法1: 新浪批量（最多重试2次）
        logger.info("=== 尝试新浪数据源...")
        for attempt in range(2):
            logger.info(f"=== 新浪尝试 {attempt+1}/2")
            result = self._realtime_sina(codes)
            logger.info(f"=== 新浪结果: {len(result) if result else 0} items")
            if result:
                _set_cache(cache_key, result)
                return result
            if attempt < 1:
                logger.warning(f"新浪实时行情第{attempt+1}次失败，重试...")
                time.sleep(0.5)

        # ── 方法2: 腾讯备用 ──
        logger.warning("新浪实时行情失败，切换腾讯...")
        result = self._realtime_tencent(codes)
        if result:
            _set_cache(cache_key, result)
            return result

        # ── 方法3: akshare兜底 ──
        logger.warning("腾讯也失败，尝试akshare...")
        result = self._realtime_akshare(codes)
        if result:
            _set_cache(cache_key, result)
            return result

        logger.error(f"所有实时行情接口均失败: {codes[:5]}")
        return []

    def _realtime_sina(self, codes: List[str]) -> Optional[List[Dict]]:
        """新浪财经批量实时行情"""
        logger.info(f"=== _realtime_sina called, codes={codes}")
        try:
            self._rate_limit()
            symbols = [self._to_sina_symbol(c) for c in codes]
            batch = ",".join(symbols)
            logger.info(f"=== 新浪请求URL: {_SINA_HQ.format(batch[:50])}...")

            resp = self._session.get(
                _SINA_HQ.format(batch),
                timeout=15
            )
            logger.info(f"=== 新浪响应: status={resp.status_code}, len={len(resp.text)}")
            if resp.status_code != 200 or not resp.text.strip():
                return None

            results = []
            for line in resp.text.strip().split("\n"):
                if '="' not in line:
                    continue
                code_part = line.split('="')[0].replace("var hq_str_", "")
                raw = line.split('="')[1].rstrip('";\r\n ')
                fields = raw.split(",")

                if len(fields) < 32:
                    continue

                # 解析字段
                name = fields[0]
                pre_close = float(fields[2]) if fields[2] else 0
                price = float(fields[3]) if fields[3] else 0
                open_ = float(fields[1]) if fields[1] else 0
                high = float(fields[4]) if fields[4] else 0
                low = float(fields[5]) if fields[5] else 0
                vol = float(fields[8]) if fields[8] else 0    # 成交量(手)
                amount = float(fields[9]) if fields[9] else 0  # 成交额(元)
                bid1 = float(fields[11]) if fields[11] else 0
                ask1 = float(fields[21]) if fields[21] else 0

                change_pct = ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0

                # 提取原始6位代码
                code = code_part.replace("sh", "").replace("sz", "")

                results.append({
                    "code": code,
                    "name": name,
                    "price": price,
                    "pre_close": pre_close,
                    "change_pct": round(change_pct, 2),
                    "open": open_,
                    "high": high,
                    "low": low,
                    "volume": vol,
                    "amount": amount,
                    "bid1": bid1,
                    "ask1": ask1,
                })

            return results if results else None

        except Exception as e:
            logger.error(f"新浪实时行情异常: {e}")
            return None

    def _realtime_akshare(self, codes: List[str]) -> Optional[List[Dict]]:
        """akshare兜底实时行情（备用中的备用）"""
        try:
            import akshare as ak
            self._rate_limit()

            results = []
            # akshare需要逐个或小批量获取
            for code in codes:
                try:
                    symbol = f"{code}" if code.startswith("6") else f"{code}"
                    df = ak.stock_zh_a_spot_em()
                    row = df[df['代码'] == code]
                    if not row.empty:
                        r = row.iloc[0]
                        results.append({
                            "code": code,
                            "name": r.get("名称", code),
                            "price": float(r.get("最新价", 0) or 0),
                            "pre_close": float(r.get("昨收", 0) or 0),
                            "change_pct": round(float(r.get("涨跌幅", 0) or 0), 2),
                            "open": float(r.get("今开", 0) or 0),
                            "high": float(r.get("最高", 0) or 0),
                            "low": float(r.get("最低", 0) or 0),
                            "volume": float(r.get("成交量", 0) or 0),
                            "amount": float(r.get("成交额", 0) or 0),
                            "bid1": float(r.get("买一价", 0) or 0),
                            "ask1": float(r.get("卖一价", 0) or 0),
                        })
                except:
                    continue
            return results if results else None
        except ImportError:
            logger.debug("akshare未安装，跳过")
            return None
        except Exception as e:
            logger.error(f"akshare实时行情异常: {e}")
            return None

    def _realtime_tencent(self, codes: List[str]) -> Optional[List[Dict]]:
        """腾讯财经备用实时行情"""
        try:
            self._rate_limit()
            symbols = [self._to_tencent_symbol(c) for c in codes]
            batch = ",".join(symbols)

            resp = self._session.get(
                _TENCENT_HQ.format(batch),
                timeout=15
            )
            if resp.status_code != 200 or not resp.text.strip():
                return None

            results = []
            for line in resp.text.strip().split("\n"):
                if "~" not in line:
                    continue
                fields = line.strip().split("~")
                if len(fields) < 45:
                    continue

                code = fields[2]
                name = fields[1]
                price = float(fields[3]) if fields[3] else 0
                pre_close = float(fields[4]) if fields[4] else 0
                open_ = float(fields[5]) if fields[5] else 0
                vol = float(fields[6]) if fields[6] else 0
                high = float(fields[33]) if fields[33] else 0
                low = fields[34] if len(fields) > 34 else "0"
                low = float(low) if low else 0
                amount = float(fields[37]) if fields[37] else 0
                bid1 = float(fields[9]) if fields[9] else 0
                ask1 = float(fields[19]) if fields[19] else 0

                change_pct = ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0

                results.append({
                    "code": code,
                    "name": name,
                    "price": price,
                    "pre_close": pre_close,
                    "change_pct": round(change_pct, 2),
                    "open": open_,
                    "high": high,
                    "low": low,
                    "volume": vol,
                    "amount": amount,
                    "bid1": bid1,
                    "ask1": ask1,
                })

            return results if results else None

        except Exception as e:
            logger.error(f"腾讯实时行情异常: {e}")
            return None

    # ──────────────────────────────────────────
    #  K线数据
    # ──────────────────────────────────────────
    def get_kline(self, code: str, period: str = "daily", count: int = 120) -> Optional[pd.DataFrame]:
        """
        获取K线数据（新浪 → akshare备用）

        Args:
            code: 股票代码（6位）
            period: daily / weekly / monthly
            count: 数据条数

        Returns:
            DataFrame: date, open, high, low, close, volume, amount
        """
        cache_key = f"kl_{code}_{period}_{count}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        # ── 方法1: 新浪（重试2次）┐─
        for attempt in range(2):
            df = self._kline_sina(code, period, count)
            if df is not None:
                _set_cache(cache_key, df)
                return df
            if attempt < 1:
                time.sleep(0.5)

        # ── 方法2: akshare备用 ──
        logger.warning(f"新浪K线失败，尝试akshare {code}")
        df = self._kline_akshare(code, period, count)
        if df is not None:
            _set_cache(cache_key, df)
            return df

        logger.error(f"获取K线失败 {code}: 所有数据源均失败")
        return None

    def _kline_sina(self, code: str, period: str = "daily", count: int = 120) -> Optional[pd.DataFrame]:
        """新浪K线"""
        try:
            self._rate_limit()
            symbol = self._to_sina_symbol(code)

            scale_map = {"daily": 5, "weekly": 240, "monthly": 5}
            scale = scale_map.get(period, 5)

            resp = self._session.get(
                _SINA_KLINE,
                params={
                    "symbol": symbol,
                    "scale": scale,
                    "ma": "no",
                    "datalen": count,
                },
                timeout=20,
            )

            if resp.status_code != 200:
                logger.warning(f"新浪K线HTTP {resp.status_code}: {code}")
                return None

            data = resp.json()
            if not data or not isinstance(data, list):
                return None

            df = pd.DataFrame(data)
            df.columns = ["date", "open", "high", "low", "close", "volume"]

            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df.dropna(subset=["close"])
            df["amount"] = (df["close"] * df["volume"]).round(2)
            return df

        except Exception as e:
            logger.error(f"新浪K线异常 {code}: {e}")
            return None

    def _kline_akshare(self, code: str, period: str = "daily", count: int = 120) -> Optional[pd.DataFrame]:
        """akshare K线备用"""
        try:
            import akshare as ak
            self._rate_limit()

            # akshare个股历史行情
            symbol = f"{code}" if code.startswith("6") else f"{code}"
            period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
            ak_period = period_map.get(period, "daily")

            df = ak.stock_zh_a_hist(symbol=code, period=ak_period, adjust="qfq")
            if df is None or len(df) < 10:
                return None

            # 统一列名
            rename_map = {
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount",
            }
            df = df.rename(columns=rename_map)
            keep_cols = [c for c in ["date","open","high","low","close","volume","amount"] if c in df.columns]
            df = df[keep_cols].tail(count)

            for col in ["open","high","low","close","volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df.dropna(subset=["close"])
            return df

        except ImportError:
            logger.debug("akshare未安装")
            return None
        except Exception as e:
            logger.error(f"akshare K线异常 {code}: {e}")
            return None

    # ──────────────────────────────────────────
    #  板块数据
    # ──────────────────────────────────────────
    def get_sectors(self, sector_type: str = "industry", top_n: int = 20) -> List[Dict]:
        """
        获取板块热点

        Args:
            sector_type: industry(行业) / concept(概念)
            top_n: 返回数量
        """
        cache_key = f"sec_{sector_type}"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached[:top_n]

        try:
            self._rate_limit()
            fs = "m:90 t:2" if sector_type == "industry" else "m:90 t:3"

            resp = self._session.get(
                _EM_SECTOR,
                params={
                    "pn": 1, "pz": 60, "po": 1, "np": 1,
                    "fltt": 2, "invt": 2,
                    "fid": "f3",
                    "fs": fs,
                    "fields": "f2,f3,f4,f12,f14",
                },
                timeout=15,
            )

            data = resp.json()
            sectors = []

            if data and "data" in data and "diff" in data["data"]:
                for item in data["data"]["diff"]:
                    change = float(item.get("f3", 0) or 0)
                    sectors.append({
                        "code": item.get("f12", ""),
                        "name": item.get("f14", ""),
                        "change_pct": round(change, 2),
                    })

            sectors.sort(key=lambda x: x["change_pct"], reverse=True)
            _set_cache(cache_key, sectors)
            return sectors[:top_n]

        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return []

    # ──────────────────────────────────────────
    #  热门板块个股（新增）
    # ──────────────────────────────────────────
    def get_hot_sector_stocks(self, top_n: int = 10, per_sector_n: int = 5) -> List[str]:
        """
        获取热门板块中的代表性股票代码

        Args:
            top_n: 取前n个热门板块
            per_sector_n: 每个板块取前n只个股

        Returns:
            股票代码列表
        """
        cache_key = "hot_sec_stocks"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            # 同时获取行业+概念热门
            industry = self.get_sectors("industry", top_n=top_n)
            concept = self.get_sectors("concept", top_n=top_n)
            all_sectors = industry + concept
            all_sectors.sort(key=lambda x: x["change_pct"], reverse=True)
            hot = all_sectors[:top_n]

            stock_codes = []
            # 板块代码格式: f12
            for s in hot:
                code = s["code"]
                # 东财板块详情接口
                try:
                    resp = self._session.get(
                        _EM_SECTOR,
                        params={
                            "pn": 1, "pz": per_sector_n, "po": 1, "np": 1,
                            "fltt": 2, "invt": 2,
                            "fid": "f3",
                            "fs": f"b:{code}+b:+2",
                            "fields": "f2,f3,f12,f14",
                        },
                        timeout=10,
                    )
                    data = resp.json()
                    if data and "data" in data and "diff" in data["data"]:
                        for item in data["data"]["diff"]:
                            c = item.get("f12", "")
                            if c and len(c) == 6 and c not in stock_codes:
                                stock_codes.append(c)
                except:
                    pass

            _set_cache(cache_key, stock_codes)
            return stock_codes

        except Exception as e:
            logger.error(f"获取热门板块个股失败: {e}")
            return []

    # ──────────────────────────────────────────
    #  工具方法
    # ──────────────────────────────────────────
    def _rate_limit(self):
        """滑动窗口频率限制：每分钟最多60次"""
        now = time.time()
        # 清理超过60秒的旧请求
        self._requests = [t for t in self._requests if now - t < 60]
        if len(self._requests) >= 60:
            sleep_time = 60 - (now - self._requests[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        self._requests.append(time.time())

    def _to_sina_symbol(self, code: str) -> str:
        """600519 → sh600519"""
        code = code.strip()
        if code.startswith("6") or code.startswith("5"):
            return f"sh{code}"
        return f"sz{code}"

    def _to_tencent_symbol(self, code: str) -> str:
        """600519 → sh600519"""
        code = code.strip()
        if code.startswith("6") or code.startswith("5"):
            return f"sh{code}"
        return f"sz{code}"

    def get_stock_name(self, code: str) -> str:
        """根据代码获取股票名称（从实时行情缓存）"""
        try:
            quotes = self.get_realtime([code])
            if quotes:
                return quotes[0].get("name", code)
        except:
            pass
        return code
