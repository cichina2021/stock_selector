# 智能选股系统 v2.0

独立EXE版本，不依赖AutoTraderV3。

## 功能特性

### 11种经典选股策略（来自GitHub高准确率项目）

1. **放量上涨** - 量价齐升，资金介入
   - 当日上涨且涨幅 < 2%
   - 成交额 >= 2亿
   - 量比 >= 2

2. **均线多头** - 趋势向上
   - MA5 > MA10 > MA20 > MA30
   - MA30向上且涨幅 >= 20%

3. **停机坪** - 强势整理后突破
   - 近15日有涨停
   - 涨停后连续高开高走

4. **回踩年线** - 长期支撑确认
   - 从年线下方向上突破
   - 回踩年线时缩量

5. **突破平台** - 横盘突破
   - 60日内放量突破MA60
   - 突破前在均线附近震荡

6. **无大幅回撤** - 趋势稳健
   - 60日涨幅 < 60%
   - 无单日跌幅 > 7%

7. **海龟交易法则** - 创新高买入
   - 当日收盘 >= 60日最高

8. **高而窄的旗形** - 强势形态
   - 涨幅 >= 90%
   - 有连续涨停

9. **MACD金叉** - 经典技术信号
   - DIF上穿DEA

10. **KDJ超卖** - 短线机会
    - K值 < 20 或 J值 < 10
    - K上穿D

11. **多因子综合** - 量化评分
    - MACD、均线、量比、趋势、位置

### 61种K线形态识别

十字星、锤头、上吊线、吞没、晨星、暮星、三白兵、三只乌鸦、大阳线、大阴线等

### 板块热点共振

- 实时扫描行业/概念板块涨幅榜
- 从热点板块中筛选优质个股

## 快速开始

### 直接运行（开发模式）

```bash
cd ~/WorkBuddy/StockSelector
python main.py
```

访问 http://localhost:8080

### 打包EXE

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包
cd ~/WorkBuddy/StockSelector
pyinstaller build.spec

# 输出
dist/智能选股系统.exe
```

## 使用说明

1. 输入股票代码（如002539）进行深度分析
2. 查看板块热点涨幅榜
3. 了解各策略的入选理由和评分

## 技术架构

```
StockSelector/
├── main.py          # 启动入口
├── strategies.py    # 11种选股策略
├── patterns.py      # 61种K线形态
├── selector.py      # 选股引擎
├── datasource.py    # 数据源
├── webui.py         # Web界面
└── build.spec       # 打包配置
```

## 数据源

- 新浪财经（稳定快速）
- 东方财富（备用）

## 策略来源

- InStock项目 (python-liuqingqing/stock)
- 多因子选股模型 (UFund-Me/Qbot)
- 机器学习选股 (pyhong/Machine-learning-on-Stocks-Selection)

## 作者

小虾 🦐 - OpenClaw Agent
