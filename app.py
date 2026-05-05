import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="최종 병기 스캐너", layout="wide")
st.title("🔥 데이터 강제 호출 스캐너")

@st.cache_data
def get_tickers():
    if os.path.exists("tickers.txt"):
        with open("tickers.txt", "r") as f:
            return [line.strip().upper() for line in f.readlines() if line.strip()]
    return []

def scan_stock(ticker):
    try:
        # EMA 200 계산을 위해 데이터를 넉넉히 250일치 가져옵니다.
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        if df is None or df.empty or len(df) < 200:
            return None

        # 컬럼 구조 단순화 (필수)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 숫자형 변환
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')

        # 1. EMA 200 계산
        df['EMA200'] = ta.ema(df['Close'], length=200)

        # 2. SuperTrend 계산
        sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        if sti is None: return None
        
        df = pd.concat([df, sti], axis=1)
        trend_col = [col for col in df.columns if 'SUPERTd' in col][0]
        
        last_row = df.iloc[-1]

        # 🎯 최종 필터 조건
        # 조건 A: 현재가가 200일 이평선보다 위에 있음 (정배열 초입/유지)
        is_above_ema = float(last_row['Close']) > float(last_row['EMA200'])
        # 조건 B: SuperTrend가 상승(1) 신호 유지 중
        is_trend_up = float(last_row[trend_col]) == 1

        if is_above_ema and is_trend_up:
            return {
                "Ticker": ticker,
                "현재가": round(float(last_row['Close']), 2),
                "EMA200": round(float(last_row['EMA200']), 2),
                "상태": "강세 추세 포착"
            }
    except Exception:
        return None
    return None

tickers = get_tickers()

if tickers:
    st.write(f"현재 {len(tickers)}개 종목 준비 완료.")
    if st.button('🚀 데이터 강제 스캔 시작'):
        results = []
        logs = []
        progress = st.progress(0)
        
        # [중요] 속도보다는 안정성을 위해 workers를 5로 낮춥니다.
        with ThreadPoolExecutor(max_workers=5) as executor:
            for i, res in enumerate(executor.map(scan_stock, tickers)):
                if res:
                    if "상태" in res:
                        results.append(res)
                    else:
                        logs.append(res)
                progress.progress((i + 1) / len(tickers))

        if results:
            st.success(f"드디어 {len(results)}개 종목을 찾아냈습니다!")
            st.table(pd.DataFrame(results))
        else:
            st.error("이번에도 결과가 0개입니다. 아래 로그를 확인하세요.")
            with st.expander("데이터 수신 상태 로그"):
                st.write(pd.DataFrame(logs))
