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
        # 1. 데이터 다운로드
        df = yf.download(ticker, period="100d", interval="1d", progress=False)
        
        if df is None or df.empty or len(df) < 20:
            return {"Ticker": ticker, "Status": "데이터 수신 실패"}

        # [핵심 수정] 다중 인덱스(Multi-index) 해제 및 컬럼명 단순화
        # yfinance 업데이트로 인해 컬럼이 ('Close', 'AAPL') 식으로 들어오는 것을 방지합니다.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 데이터가 Series 형태인 경우를 대비해 확실히 숫자로 변환
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')

        # 2. SuperTrend 계산
        sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        
        if sti is None or sti.empty:
            return {"Ticker": ticker, "Status": "지표 계산 불가"}
        
        # 3. 데이터 합치기 및 결과 추출
        df = pd.concat([df, sti], axis=1)
        trend_col = [col for col in df.columns if 'SUPERTd' in col][0]
        
        # 마지막 유효한 값 찾기
        last_val = df[trend_col].dropna().iloc[-1]

        if float(last_val) == 1:
            return {
                "Ticker": ticker,
                "현재가": round(float(df['Close'].iloc[-1]), 2),
                "상태": "상승"
            }
    except Exception as e:
        return {"Ticker": ticker, "Status": f"에러: {str(e)[:15]}"}
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
