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
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    
    # 브라우저인 것처럼 속이는 헤더 정보 추가
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    with urllib.request.urlopen(req) as response:
        table = pd.read_html(response)
        
    df = table[0]
    # 티커 심볼의 '.'을 '-'로 변경 (yfinance 호환성용)
    tickers = df['Symbol'].str.replace('.', '-', regex=True).tolist()
    return tickers

# 2. 개별 종목 분석 함수
def scan_stock(ticker):
    try:
        # 1. 데이터 다운로드 (데이터 양을 2년으로 늘려 EMA200 계산 안정성 확보)
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if len(df) < 200: return None

        # 2. EMA 200 계산
        df['EMA200'] = ta.ema(df['Close'], length=200)

        # 3. SuperTrend 계산
        sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        if sti is None: return None
        
        # 4. 데이터 합치기
        df = pd.concat([df, sti], axis=1)
        
        # 5. SuperTrend 방향 컬럼 찾기 (보통 'SUPERTd_10_3.0' 형태임)
        # 이름이 바뀌어도 찾을 수 있게 'SUPERTd'가 포함된 모든 컬럼명을 가져옵니다.
        trend_cols = [col for col in df.columns if 'SUPERTd' in col]
        if not trend_cols: return None
        direction_col = trend_cols[0]
        
        last_row = df.iloc[-1]

        # 6. 매수 유지 조건 (엄격한 골든크로스 대신 현재 상승 추세인 종목 모두)
        # 종가가 EMA 200보다 높고, SuperTrend 방향이 1(상승)인 경우
        is_above_ema = float(last_row['Close']) > float(last_row['EMA200'])
        is_supertrend_buy = float(last_row[direction_col]) == 1

        if is_above_ema and is_supertrend_buy:
            return {
                "Ticker": ticker,
                "Price": round(float(last_row['Close']), 2),
                "EMA200": round(float(last_row['EMA200']), 2),
                "Signal": "UP TREND"
            }
    except Exception as e:
        # 에러 확인용 (필요시 st.write(e)로 확인 가능)
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
