import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ---------------------------------------------------------
# 1. 데이터 수집 함수: 코스닥 시가총액 상위 200종목 추출
# ---------------------------------------------------------
# @st.cache_data를 사용하여 200개 종목 데이터를 1시간(3600초) 동안 메모리에 저장해 로딩 속도를 높입니다.
@st.cache_data(ttl=3600)
def get_kosdaq200_data():
    headers = {'User-Agent': 'Mozilla/5.0'}
    stocks = []
    
    # 네이버 금융 시가총액 페이지 코스닥(sosok=1) 1~4페이지(한 페이지당 50개 * 4 = 200개)를 순회합니다.
    for page in range(1, 5):
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=1&page={page}"
        try:
            res = requests.get(url, headers=headers)
            res.encoding = 'euc-kr' # 한글 깨짐 방지
            soup = BeautifulSoup(res.text, 'html.parser')
            
            rows = soup.select('table.type_2 tbody tr')
            
            for row in rows:
                if len(stocks) >= 200: break # 정확히 200개에서 멈춤
                
                name_tag = row.select_one('a.tltle')
                if not name_tag: continue
                
                name = name_tag.text.strip()
                
                # 종목 고유 페이지 주소 및 종목 코드 추출
                stock_link = "https://finance.naver.com" + name_tag['href']
                stock_code = name_tag['href'].split('code=')[-1]
                
                # 네이버 제공 차트 이미지 주소 생성
                chart_day_url = f"https://ssl.pstatic.net/imgfinance/chart/item/candle/day/{stock_code}.png"
                chart_week_url = f"https://ssl.pstatic.net/imgfinance/chart/item/candle/week/{stock_code}.png"
                chart_month_url = f"https://ssl.pstatic.net/imgfinance/chart/item/candle/month/{stock_code}.png"
                
                # 등락률 추출 (4번째 td)
                tds = row.select('td')
                try:
                    rate_raw = tds[4].text.strip().replace('%', '').replace('+', '').replace(',', '')
                    rate = float(rate_raw)
                except: 
                    rate = 0.0
                
                # 딕셔너리에 데이터 저장
                stocks.append({
                    "종목명": name,
                    "일봉": chart_day_url,
                    "주봉": chart_week_url,
                    "월봉": chart_month_url,
                    "등락률(%)": rate,
                    "페이지 이동": stock_link
                })
        except: 
            continue
            
    return pd.DataFrame(stocks)

# ---------------------------------------------------------
# 2. 스트림릿 화면 및 UI 설정
# ---------------------------------------------------------
st.set_page_config(page_title="코스닥 200 대시보드", layout="wide")

st.title("🚀 코스닥 시가총액 상위 200종목 다중 차트")
st.caption(f"최초 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (※ 속도 최적화를 위해 데이터는 1시간 단위로 갱신됩니다.)")
st.markdown("**전문가의 팁:** 공식적인 대표 지수는 '코스닥 150'이지만, 시장의 자금 흐름을 더 넓게 파악하기 위해 요청하신 대로 상위 200개 종목을 넉넉하게 추출했습니다.")
st.markdown("---")

# ---------------------------------------------------------
# 3. 데이터 로드 및 표 출력
# ---------------------------------------------------------
# 200개의 종목을 긁어오기 때문에 최초 실행 시 약간의 대기 시간이 필요합니다.
with st.spinner("코스닥 200종목 분석 및 600개의 차트를 로딩 중입니다... (최초 1회 5~10초 소요)"):
    df_kosdaq = get_kosdaq200_data()

if not df_kosdaq.empty:
    st.dataframe(
        df_kosdaq,
        column_config={
            "일봉": st.column_config.ImageColumn("일봉"),
            "주봉": st.column_config.ImageColumn("주봉"),
            "월봉": st.column_config.ImageColumn("월봉"),
            "등락률(%)": st.column_config.NumberColumn(format="%.2f%%"),
            "페이지 이동": st.column_config.LinkColumn("네이버 금융", display_text="🌐열기")
        },
        hide_index=True,
        use_container_width=True,
        height=1000 # 200개 종목을 여유 있게 스크롤해서 볼 수 있도록 높이를 늘렸습니다.
    )
else:
    st.error("코스닥 데이터를 불러오는 중 문제가 발생했습니다.")