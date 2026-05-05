import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="추세 반전 스캐너", layout="wide")
st.title("🔄 S&P 500 추세 반전 포착")

@st.cache_data
def get_tickers():
    if os.path.exists("tickers.txt"):
        with open("tickers.txt", "r") as f:
            return [line.strip().upper() for line in f.readlines() if line.strip()]
    return []

def scan_stock(ticker):
    try:
        # EMA 200과 전날 지표 확인을 위해 1년치 데이터 다운로드
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        if df is None or df.empty or len(df) < 201:
            return None

        # 컬럼 구조 단순화 (Multi-index 해제)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')

        # 1. EMA 200 계산
        df['EMA200'] = ta.ema(df['Close'], length=200)

        # 2. SuperTrend 계산 (10, 3)
        sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        if sti is None: return None
        
        df = pd.concat([df, sti], axis=1)
        trend_col = [col for col in df.columns if 'SUPERTd' in col][0]
        
        # 마지막 두 행 추출 (어제와 오늘)
        prev_row = df.iloc[-2]
        last_row = df.iloc[-1]

        # 🎯 반전 조건 설정
        # 조건 1: 오늘 종가가 EMA 200보다 위 (장기 상승 추세 내림목)
        above_ema = float(last_row['Close']) > float(last_row['EMA200'])
        # 조건 2: 어제는 하락(-1)이었는데 오늘 상승(1)으로 반전
        is_reversal = float(prev_row[trend_col]) == -1 and float(last_row[trend_col]) == 1

        if above_ema and is_reversal:
            return {
                "Ticker": ticker,
                "현재가": round(float(last_row['Close']), 2),
                "EMA200": round(float(last_row['EMA200']), 2),
                "신호": "🔴 하락에서 상승으로 반전"
            }
    except Exception:
        return None
    return None

tickers = get_tickers()

if tickers:
    st.write(f"총 {len(tickers)}개 종목을 대상으로 스캔합니다.")
    
    if st.button('🔄 반전 신호 포착 시작'):
        results = []
        progress = st.progress(0)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            total = len(tickers)
            for i, res in enumerate(executor.map(scan_stock, tickers)):
                if res:
                    results.append(res)
                progress.progress((i + 1) / total)

        if results:
            st.success(f"총 {len(results)}개의 반전 종목이 포착되었습니다.")
            result_df = pd.DataFrame(results)
            st.table(result_df)
        else:
            st.warning("현재 반전 신호가 발생한 종목이 없습니다.")
