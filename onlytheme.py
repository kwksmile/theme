import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime

# 1. 네이버 금융 데이터 수집 함수
def get_naver_themes():
    url = "https://finance.naver.com/sise/theme.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr' # 한글/기호 깨짐 방지
    soup = BeautifulSoup(res.text, 'html.parser')

    themes = []
    for row in soup.select('.theme .col_type1 a')[:6]:
        themes.append({'테마': row.text.strip(), 'link': "https://finance.naver.com" + row['href']})
    return themes

def get_theme_stocks(theme_link):
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(theme_link, headers=headers)
    res.encoding = 'euc-kr' # 한글/기호 깨짐 방지
    soup = BeautifulSoup(res.text, 'html.parser')

    stocks = []
    rows = soup.select('.type_5 tbody tr')
    
    for row in rows:
        if len(stocks) >= 5: break
        name_col = row.select_one('.name a')
        if not name_col: continue
            
        name = name_col.text.strip()
        stock_url = "https://finance.naver.com" + name_col['href']
        
        # [수정된 부분] 무조건 '%' 기호가 있는 칸을 찾아서 등락률 추출
        rate = 0.0
        for td in row.select('td'):
            if '%' in td.text:
                try:
                    # +, %, 쉼표, 공백을 모두 제거하고 순수 숫자만 추출
                    clean_text = td.text.replace('%', '').replace('+', '').replace(',', '').strip()
                    rate = float(clean_text)
                except:
                    rate = 0.0
                break # % 칸을 찾았으면 더 이상 다른 칸을 찾지 않고 종료

        info = row.select_one('.info_txt')
        issue = (info.text.strip()[:15] + "...") if info and len(info.text.strip()) > 15 else (info.text.strip() if info else "")

        stocks.append({"종목명": name, "등락률(%)": rate, "급등이슈": issue, "링크": stock_url})
        
    return pd.DataFrame(stocks)

# 2. 스트림릿 화면 설정
st.set_page_config(page_title="주도주 대시보드", layout="wide")
st.title("🏆 실시간 주도테마 및 종목 (클릭 시 이동)")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 3. 데이터 로드 및 출력
themes_data = get_naver_themes()
cols = st.columns(2)

for i, theme in enumerate(themes_data):
    with cols[i % 2]:
        st.subheader(f"🔹 {theme['테마']}")
        df = get_theme_stocks(theme['link'])
        
        if not df.empty:
            st.dataframe(
                df,
                column_config={
                    "링크": st.column_config.LinkColumn("페이지 이동", display_text="🌐열기"),
                    "등락률(%)": st.column_config.NumberColumn(format="%.2f%%")
                },
                hide_index=True,
                use_container_width=True
            )
        st.write("")

# 4. 15초 자동 새로고침
placeholder = st.empty()
for t in range(15, 0, -1):
    placeholder.caption(f"⏳ {t}초 후 데이터 갱신...")
    time.sleep(1)
st.rerun()