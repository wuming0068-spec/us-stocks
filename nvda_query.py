import akshare as ak
import numpy as np
import pandas as pd
import time

print("akshare + 日本VPN 获取 NVDA 数据...")

df = None
for attempt in range(5):
    try:
        df = ak.stock_us_hist(symbol='105.NVDA', period='daily',
                              start_date='20260201', end_date='20260601', adjust='')
        if df is not None and len(df) > 20:
            print(f"第{attempt+1}次成功! {len(df)} 行")
            break
    except Exception as e:
        print(f"第{attempt+1}次失败: {type(e).__name__}")
        time.sleep(2)

if df is None or len(df) == 0:
    print("失败")
    exit()

# 重命名列
df = df.rename(columns={
    '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
    '最高': 'High', '最低': 'Low', '成交量': 'Volume',
})
df['Date'] = pd.to_datetime(df['Date'])
for col in ['Open', 'Close', 'High', 'Low', 'Volume']:
    df[col] = pd.to_numeric(df[col])
df = df.set_index('Date').sort_index()
df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
df = df[~df.index.duplicated(keep='last')]

print(f"日期范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")

# 指标
df['MA5'] = df['Close'].rolling(5).mean()
df['MA20'] = df['Close'].rolling(20).mean()

n = 9
low_min = df['Low'].rolling(n).min()
high_max = df['High'].rolling(n).max()
rsv = (df['Close'] - low_min) / (high_max - low_min) * 100

k_vals = np.zeros(len(df))
d_vals = np.zeros(len(df))
for i in range(len(df)):
    if i < n or pd.isna(rsv.iloc[i]):
        k_vals[i] = 50.0
        d_vals[i] = 50.0
    else:
        k_vals[i] = 2/3 * k_vals[i-1] + 1/3 * rsv.iloc[i]
        d_vals[i] = 2/3 * d_vals[i-1] + 1/3 * k_vals[i]

df['K'] = k_vals
df['D'] = d_vals
df['J'] = 3 * k_vals - 2 * d_vals

last5 = df.tail(5)

print()
print('=' * 105)
print("  NVDA (NVIDIA) Last 5 Trading Days - via akshare + Japan VPN")
print(f"  Period: {last5.index[0].strftime('%Y-%m-%d')} ~ {last5.index[-1].strftime('%Y-%m-%d')}")
print('=' * 105)

for idx, row in last5.iterrows():
    d = idx.strftime('%Y-%m-%d')
    k_s = "OVERBOUGHT" if row['K'] > 80 else ("OVERSOLD" if row['K'] < 20 else "NORMAL")
    d_s = "OVERBOUGHT" if row['D'] > 80 else ("OVERSOLD" if row['D'] < 20 else "NORMAL")
    j_s = "TOP?" if row['J'] > 100 else ("BOTTOM?" if row['J'] < 0 else "OK")

    print(f"\n  [ {d} ]")
    print(f"    Open: ${row['Open']:.2f}  High: ${row['High']:.2f}  Low: ${row['Low']:.2f}  Close: ${row['Close']:.2f}")
    print(f"    Volume: {row['Volume']:,.0f}")
    print(f"    MA5: ${row['MA5']:.2f}    MA20: ${row['MA20']:.2f}")
    print(f"    KDJ:  K={row['K']:.2f}[{k_s}]  D={row['D']:.2f}[{d_s}]  J={row['J']:.2f}[{j_s}]")
    print('    ' + '-' * 55)

print()
print('=' * 105)
print("  KDJ: K>80 overbought | K<20 oversold | K crosses above D = Golden Cross")
print("  MA:  Price>MA5 short-term bullish | MA5>MA20 bullish alignment")
print('=' * 105)
