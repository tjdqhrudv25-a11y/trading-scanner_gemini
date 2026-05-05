import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta  # 기술적 지표 계산 라이브러리
from concurrent.futures import ThreadPoolExecutor

# 페이지 설정
st.set_page_config(page_title="US Stock Strategy Scanner", layout="wide")

st.title("🇺🇸 S&P 500 전략 스캐너")
st.subheader("전략 1: EMA 200 위에서 SuperTrend 매수 신호 발생 종목")

# 1. S&P 500 종목 리스트 자동 가져오기
@st.cache_data
def get_sp500_tickers():
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    df = table[0]
    tickers = df['Symbol'].str.replace('.', '-', regex=True).tolist()
    return tickers

# 2. 개별 종목 분석 함수
def scan_stock(ticker):
    try:
        # 최근 1년치 일봉 데이터
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df) < 200: return None

        # EMA 200 계산
        df['EMA200'] = ta.ema(df['Close'], length=200)

        # SuperTrend 계산 (기본값: ATR 10, Multiplier 3)
        sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        # sti 컬럼 구성: [SUPERT_10_3.0, SUPERTd_10_3.0, SUPERTl_10_3.0, SUPERTs_10_3.0]
        # SUPERTd 가 1이면 매수(Trend Up), -1이면 매도(Trend Down)
        
        df = pd.concat([df, sti], axis=1)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        # 전략 조건: 
        # 1. 현재가가 EMA 200 위에 있음
        # 2. 전날은 매도 신호였으나 오늘 매수 신호로 전환 (Golden Cross)
        is_above_ema = last_row['Close'] > last_row['EMA200']
        is_supertrend_buy = (prev_row.iloc[-3] == -1) and (last_row.iloc[-3] == 1)

        if is_above_ema and is_supertrend_buy:
            return {
                "Ticker": ticker,
                "Price": round(float(last_row['Close']), 2),
                "EMA200": round(float(last_row['EMA200']), 2),
                "Signal": "BUY"
            }
    except:
        return None
    return None

# 3. 메인 화면 구성
tickers = get_sp500_tickers()

if st.button('S&P 500 전 종목 스캔 시작'):
    st.write(f"총 {len(tickers)}개 종목을 분석 중입니다... 잠시만 기다려주세요.")
    
    results = []
    progress_bar = st.progress(0)
    
    # 멀티쓰레딩으로 속도 향상
    with ThreadPoolExecutor(max_workers=20) as executor:
        for i, res in enumerate(executor.map(scan_stock, tickers)):
            if res:
                results.append(res)
            progress_bar.progress((i + 1) / len(tickers))
            
    if results:
        st.success(f"검색 완료! {len(results)}개의 종목이 포착되었습니다.")
        res_df = pd.DataFrame(results)
        st.table(res_df)
        
        # 트레이딩뷰 링크 생성
        for ticker in res_df['Ticker']:
            st.markdown(f"[{ticker} 차트 보기 (TradingView)](https://www.tradingview.com/symbols/NASDAQ-{ticker}/)")
    else:
        st.warning("현재 조건에 맞는 종목이 없습니다.")