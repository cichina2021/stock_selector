# -*- coding: utf-8 -*-
"""
数据源管理 v2.0
支持多数据源降级
"""
import requests
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
import time
import logging

logger = logging.getLogger(__name__)


class DataSource:
    """
    数据源管理器
    
    支持数据源：
    1. 新浪财经（稳定快速）
    2. 东方财富（备用）
    """
    
    # 新浪K线接口
    SINA_KLINE = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    
    # 东财实时行情接口
    EM_QUOTE = "https://push2.eastmoney.com/api/qt/stock/get"
    
    # 东财板块接口
    EM_SECTOR = "https://push2.eastmoney.com/api/qt/clist/get"
    
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 60  # 缓存60秒
    
    def get_kline(self, code: str, period: str = "daily", count: int = 120) -> Optional[pd.DataFrame]:
        """
        获取K线数据
        
        Args:
            code: 股票代码（6位数字）
            period: 周期 daily/weekly
            count: 数据条数
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        cache_key = f"kline_{code}_{period}_{count}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        # 转换代码格式
        if code.startswith("6"):
            symbol = f"sh{code}"
        else:
            symbol = f"sz{code}"
        
        # 新浪接口参数
        # scale: 240=周线, 其他=日线
        scale = 240 if period == "weekly" else 5
        
        try:
            params = {
                "symbol": symbol,
                "scale": scale,
                "ma": "no",
                "datalen": count
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            resp = requests.get(self.SINA_KLINE, params=params, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                logger.warning(f"新浪K线接口返回{resp.status_code}")
                return None
            
            # 解析数据
            data = resp.json()
            
            if not data or not isinstance(data, list):
                logger.warning(f"新浪K线数据为空: {code}")
                return None
            
            # 转DataFrame
            df = pd.DataFrame(data)
            df.columns = ["date", "open", "high", "low", "close", "volume"]
            
            # 转数值类型
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # 成交额估算
            df["amount"] = df["close"] * df["volume"]
            
            self._cache[cache_key] = df
            self._cache_time[cache_key] = time.time()
            
            return df
            
        except Exception as e:
            logger.error(f"获取K线失败 {code}: {e}")
            return None
    
    def get_realtime(self, codes: List[str]) -> List[Dict]:
        """
        获取实时行情
        
        Args:
            codes: 股票代码列表
        
        Returns:
            [{"code": "代码", "name": "名称", "price": 价格, "change_pct": 涨幅}, ...]
        """
        if not codes:
            return []
        
        cache_key = f"realtime_{','.join(codes[:10])}"  # 只缓存前10个
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        results = []
        
        try:
            # 东财接口
            secids = []
            for code in codes:
                if code.startswith("6"):
                    secids.append(f"1.{code}")
                else:
                    secids.append(f"0.{code}")
            
            params = {
                "secid": ",".join(secids[:50]),  # 最多50个
                "fields": "f12,f14,f2,f3,f4,f5,f6",
                "ut": "fa5fd1943c747d9b1f1"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            resp = requests.get(self.EM_QUOTE, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            if data and "data" in data:
                diff = data["data"].get("diff", [])
                for item in diff:
                    results.append({
                        "code": item.get("f12", ""),
                        "name": item.get("f14", ""),
                        "price": float(item.get("f2", 0) or 0),
                        "change_pct": float(item.get("f3", 0) or 0),
                        "volume": float(item.get("f5", 0) or 0),
                        "amount": float(item.get("f6", 0) or 0),
                    })
            
            self._cache[cache_key] = results
            self._cache_time[cache_key] = time.time()
            
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
        
        return results
    
    def get_sectors(self, sector_type: str = "industry", top_n: int = 20) -> List[Dict]:
        """
        获取板块数据
        
        Args:
            sector_type: industry(行业) / concept(概念)
            top_n: 返回数量
        """
        cache_key = f"sectors_{sector_type}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][:top_n]
        
        try:
            # fs: m:90 t:2=行业, t:3=概念
            fs = "m:90 t:2" if sector_type == "industry" else "m:90 t:3"
            
            params = {
                "pn": 1,
                "pz": 50,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",  # 按涨幅排序
                "fs": fs,
                "fields": "f1,f2,f3,f4,f5,f6,f7,f12,f14,f128"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            resp = requests.get(self.EM_SECTOR, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            sectors = []
            if data and "data" in data and "diff" in data["data"]:
                for item in data["data"]["diff"]:
                    sectors.append({
                        "code": item.get("f12", ""),
                        "name": item.get("f14", ""),
                        "change_pct": float(item.get("f3", 0) or 0),
                        "lead_stock": item.get("f128", ""),
                        "amount": float(item.get("f6", 0) or 0) / 1e8,
                    })
            
            # 按涨幅排序
            sectors.sort(key=lambda x: x["change_pct"], reverse=True)
            
            self._cache[cache_key] = sectors
            self._cache_time[cache_key] = time.time()
            
            return sectors[:top_n]
            
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return []
    
    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._cache_time:
            return False
        return (time.time() - self._cache_time[key]) < self._cache_ttl
