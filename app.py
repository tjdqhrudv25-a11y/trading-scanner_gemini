import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# 페이지 설정
st.set_page_config(page_title="US Stock Test Scanner", layout="wide")

st.title("🧪 스캐너 작동 테스트 (상위 10개 종목)")

# 1. S&P 500 종목 리스트 가져오기 (차단 방지 헤더 추가)
@st.cache_data
def get_sp500_tickers():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        table = pd.read_html(response)
    df = table[0]
    tickers = df['Symbol'].str.replace('.', '-', regex=True).tolist()
    return tickers

# 2. 개별 종목 분석 함수 (로직 단순화 & 에러 트래킹)
def scan_stock(ticker):
    try:
        # 데이터 기간 대폭 축소 (최근 60일)
        df = yf.download(ticker, period="60d", interval="1d", progress=False)
        
        if df.empty or len(df) < 20: 
            return {"Ticker": ticker, "Status": "데이터 없음"}

        # SuperTrend 계산
        sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        if sti is None: 
            return {"Ticker": ticker, "Status": "지표 계산 실패"}
        
        df = pd.concat([df, sti], axis=1)
        
        # SuperTrend 방향 컬럼 찾기
        direction_col = [col for col in df.columns if 'SUPERTd' in col][0]
        last_row = df.iloc[-1]

        # EMA 200 조건 없이 SuperTrend가 상승(1)이기만 하면 추출
        is_supertrend_buy = float(last_row[direction_col]) == 1

        if is_supertrend_buy:
            return {
                "Ticker": ticker,
                "Price": round(float(last_row['Close']), 2),
                "Signal": "상승 추세(BUY)"
            }
        else:
            return {"Ticker": ticker, "Status": "하락 추세"}
            
    except Exception as e:
        return {"Ticker": ticker, "Status": f"에러: {str(e)[:20]}"}

# 3. 실행부
tickers_all = get_sp500_tickers()
# 테스트를 위해 상위 10개만 슬라이싱
tickers = tickers_all[:10]

st.write(f"테스트 대상 종목: {tickers}")

if st.button('10개 종목 스캔 시작'):
    results = []
    status_list = []
    
    with ThreadPoolExecutor(max_workers=5) as executor: # 차단 방지를 위해 워커 수 제한
        for res in executor.map(scan_stock, tickers):
            if res:
                if "Signal" in res:
                    results.append(res)
                else:
                    status_list.append(res)
            
    if results:
        st.success(f"분석 완료! {len(results)}개 종목이 상승 추세입니다.")
        st.table(pd.DataFrame(results))
    
    with st.expander("전체 분석 로그 확인"):
        st.write(pd.DataFrame(status_list))
