import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime

# ---------------------------------------------------------
# 1. 네이버 금융 데이터 수집 함수
# ---------------------------------------------------------
def get_naver_themes():
    url = "https://finance.naver.com/sise/theme.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        res.encoding = 'euc-kr' 
        soup = BeautifulSoup(res.text, 'html.parser')
        themes = []
        for row in soup.select('.theme .col_type1 a')[:6]:
            themes.append({'테마': row.text.strip(), 'link': "https://finance.naver.com" + row['href']})
        return themes
    except:
        return []

def get_theme_stocks(theme_link):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(theme_link, headers=headers)
        res.encoding = 'euc-kr' 
        soup = BeautifulSoup(res.text, 'html.parser')
        stocks = []
        rows = soup.select('.type_5 tbody tr')
        
        for row in rows:
            if len(stocks) >= 5: break
            name_col = row.select_one('.name a')
            if not name_col: continue
                
            name = name_col.text.strip()
            stock_url = "https://finance.naver.com" + name_col['href']
            
            # 종목 코드를 추출하여 차트 이미지 주소 만들기
            stock_code = name_col['href'].split('code=')[-1] 
            chart_day_url = f"https://ssl.pstatic.net/imgfinance/chart/item/candle/day/{stock_code}.png" 
            chart_month_url = f"https://ssl.pstatic.net/imgfinance/chart/item/candle/month/{stock_code}.png" 
            
            rate = 0.0
            for td in row.select('td'):
                if '%' in td.text:
                    try:
                        clean_text = td.text.replace('%', '').replace('+', '').replace(',', '').strip()
                        rate = float(clean_text)
                    except:
                        rate = 0.0
                    break 

            # [수정된 부분] 15자 제한을 없애고 전체 텍스트를 그대로 가져옵니다.
            info = row.select_one('.info_txt')
            issue = info.text.strip() if info else "이슈 없음"

            stocks.append({
                "종목명": name,
                "일봉": chart_day_url,
                "월봉": chart_month_url,
                "등락률(%)": rate, 
                "급등이슈": issue, 
                "링크": stock_url
            })
            
        return pd.DataFrame(stocks)
    except:
        return pd.DataFrame()

# ---------------------------------------------------------
# 2. 스트림릿 화면 설정
# ---------------------------------------------------------
st.set_page_config(page_title="주도주 대시보드", layout="wide")
st.title("🏆 실시간 주도테마 및 종목 차트")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ---------------------------------------------------------
# 3. 데이터 로드 및 화면 출력
# ---------------------------------------------------------
themes_data = get_naver_themes()

if themes_data:
    for theme in themes_data:
        st.subheader(f"🔹 {theme['테마']}")
        df = get_theme_stocks(theme['link'])
        
        if not df.empty:
            st.dataframe(
                df,
                column_config={
                    "일봉": st.column_config.ImageColumn("일봉"),
                    "월봉": st.column_config.ImageColumn("월봉"),
                    "링크": st.column_config.LinkColumn("페이지 이동", display_text="🌐열기"),
                    "등락률(%)": st.column_config.NumberColumn(format="%.2f%%"),
                    # [수정된 부분] 글씨가 길어져 표가 깨지지 않게 너비를 중간(medium)으로 고정하고 안내 문구를 추가합니다.
                    "급등이슈": st.column_config.TextColumn(
                        "급등이슈", 
                        width="medium", 
                        help="셀을 더블클릭하거나 마우스를 올리면 전체 뉴스를 볼 수 있습니다."
                    )
                },
                hide_index=True,
                use_container_width=True
            )
        st.write("")
else:
    st.error("데이터를 불러오는 중 문제가 발생했습니다.")

# ---------------------------------------------------------
# 4. 15초 자동 새로고침
# ---------------------------------------------------------
placeholder = st.empty()
for t in range(15, 0, -1):
    placeholder.caption(f"⏳ {t}초 후 데이터 갱신...")
    time.sleep(1)
st.rerun()
