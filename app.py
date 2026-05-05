import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os
from concurrent.futures import ThreadPoolExecutor

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="S&P 500 전략 스캐너", layout="wide")
st.title("📈 S&P 500 전략 스캐너 (파일 연동 버전)")

# 2. tickers.txt 파일에서 리스트 불러오기
@st.cache_data
def get_tickers_from_file():
    filename = "tickers.txt"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            # 줄바꿈 제거, 대문자 변환, 빈 줄 제외
            tickers = [line.strip().upper() for line in f.readlines() if line.strip()]
        return tickers
    else:
        st.error(f"⚠️ '{filename}' 파일이 없습니다! GitHub에 파일을 먼저 업로드해 주세요.")
        return []

# 3. 개별 종목 분석 함수
def scan_stock(ticker):
    try:
        # 데이터 다운로드 (EMA 200 계산을 위해 넉넉히 250일치)
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        if df.empty or len(df) < 200:
            return None

        # 지표 계산: EMA 200
        df['EMA200'] = ta.ema(df['Close'], length=200)

        # 지표 계산: SuperTrend (10, 3)
        sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        if sti is None:
            return None
        
        df = pd.concat([df, sti], axis=1)
        
        # SuperTrend 방향 컬럼 찾기 (보통 'SUPERTd_10_3.0' 형태)
        trend_col = [col for col in df.columns if 'SUPERTd' in col][0]
        
        last_row = df.iloc[-1]
        
        # 전략 조건 확인
        # 조건 1: 종가가 이평선(EMA 200) 위
        is_above_ema = float(last_row['Close']) > float(last_row['EMA200'])
        # 조건 2: SuperTrend가 상승 유지(1) 상태
        is_trend_up = float(last_row[trend_col]) == 1

        if is_above_ema and is_trend_up:
            return {
                "Ticker": ticker,
                "현재가": round(float(last_row['Close']), 2),
                "EMA200": round(float(last_row['EMA200']), 2),
                "상태": "상승 추세 유지"
            }
    except Exception:
        return None
    return None

# 4. 메인 실행 로직
tickers = get_tickers_from_file()

if tickers:
    st.info(f"✅ 'tickers.txt'를 통해 {len(tickers)}개 종목을 로드했습니다.")
    
    if st.button('S&P 500 전 종목 분석 시작'):
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        # 병렬 처리를 통해 속도 향상 (max_workers는 10~15 권장)
        with ThreadPoolExecutor(max_workers=12) as executor:
            total = len(tickers)
            for i, res in enumerate(executor.map(scan_stock, tickers)):
                if res:
                    results.append(res)
                
                # 진행률 표시
                prog = (i + 1) / total
                progress_bar.progress(prog)
                status_text.text(f"분석 중: {i+1}/{total} (포착된 종목: {len(results)}개)")

        # 결과 출력
        if results:
            st.success(f"🚀 분석 완료! 총 {len(results)}개 종목이 포착되었습니다.")
            result_df = pd.DataFrame(results)
            st.dataframe(result_df, use_container_width=True)
            
            # CSV 다운로드 버튼 추가
            csv = result_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("결과 다운로드 (CSV)", csv, "scan_results.csv", "text/csv")
        else:
            st.warning("현재 모든 조건을 만족하는 종목이 없습니다.")
