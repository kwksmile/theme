import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime

# ---------------------------------------------------------
# 1. 테마 맵핑 함수: 상위 15개 주도테마를 스캔하여 종목별 테마 기억
# ---------------------------------------------------------
def get_theme_mapping():
    url = "https://finance.naver.com/sise/theme.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    theme_map = {}
    try:
        res = requests.get(url, headers=headers)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 상위 15개 주도 테마만 빠르게 가져오기 (프로그램 속도 유지)
        theme_links = soup.select('.theme .col_type1 a')[:15]
        
        for link_tag in theme_links:
            theme_name = link_tag.text.strip()
            link = "https://finance.naver.com" + link_tag['href']
            
            t_res = requests.get(link, headers=headers)
            t_res.encoding = 'euc-kr'
            t_soup = BeautifulSoup(t_res.text, 'html.parser')
            
            rows = t_soup.select('.type_5 tbody tr')
            for row in rows:
                name_col = row.select_one('.name a')
                if not name_col: continue
                stock_name = name_col.text.strip()
                
                # 종목이 2개 이상의 테마에 속할 수 있으므로, 이미 있으면 쉼표로 연결
                if stock_name in theme_map:
                    if theme_name not in theme_map[stock_name]:
                        theme_map[stock_name] += f", {theme_name}"
                else:
                    theme_map[stock_name] = theme_name
    except:
        pass
    return theme_map

# ---------------------------------------------------------
# 2. 데이터 수집 함수: 코스피+코스닥 통합 급등주 40개 추출 & 테마 매칭
# ---------------------------------------------------------
def get_realtime_rising_stocks(theme_map):
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_stocks = []
    
    # sosok=0 (코스피), sosok=1 (코스닥) 두 페이지를 모두 순회
    for sosok in [0, 1]:
        url = f"https://finance.naver.com/sise/sise_rise.naver?sosok={sosok}"
        try:
            res = requests.get(url, headers=headers)
            res.encoding = 'euc-kr'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            rows = soup.select('table.type_2 tr')
            
            for row in rows:
                name_tag = row.select_one('a.tltle')
                if not name_tag: continue
                
                name = name_tag.text.strip()
                stock_link = "https://finance.naver.com" + name_tag['href']
                stock_code = name_tag['href'].split('code=')[-1]
                
                chart_day_url = f"https://ssl.pstatic.net/imgfinance/chart/item/candle/day/{stock_code}.png"
                chart_month_url = f"https://ssl.pstatic.net/imgfinance/chart/item/candle/month/{stock_code}.png"
                news_url = f"https://search.naver.com/search.naver?where=news&query={name}"
                
                tds = row.select('td')
                try:
                    rate_raw = tds[4].text.strip().replace('%', '').replace('+', '').replace(',', '')
                    rate = float(rate_raw)
                except: 
                    rate = 0.0
                
                # [핵심 추가] 기억해둔 테마 맵핑 정보에서 테마 찾기 (없으면 '-')
                theme_info = theme_map.get(name, "-")
                
                all_stocks.append({
                    "종목명": name,
                    "관련 테마": theme_info,  # 새로 추가된 테마 컬럼
                    "일봉": chart_day_url,
                    "월봉": chart_month_url,
                    "등락률(%)": rate,
                    "급등이슈": news_url,
                    "페이지 이동": stock_link
                })
        except: 
            continue
            
    # 코스피, 코스닥 통합 후 '등락률(%)' 기준으로 내림차순 정렬하여 최상위 40개 추출
    all_stocks.sort(key=lambda x: x['등락률(%)'], reverse=True)
    top_40_stocks = all_stocks[:40]
    
    return pd.DataFrame(top_40_stocks)

# ---------------------------------------------------------
# 3. 스트림릿 화면 및 UI 설정
# ---------------------------------------------------------
st.set_page_config(page_title="실시간 급등주 대시보드", layout="wide")

st.title("🚀 통합 실시간 급등주 TOP 40")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (15초마다 갱신 / 코스피·코스닥 통합)")
st.markdown("---")

# ---------------------------------------------------------
# 4. 데이터 로드 및 표 출력
# ---------------------------------------------------------
with st.spinner("주도테마 매칭 및 급등주 40종목 분석 중... (약 2~3초 소요)"):
    # 1. 테마 맵핑 먼저 가져오기
    theme_mapping = get_theme_mapping()
    # 2. 급등주 수집 시 테마 정보 넘겨주기
    df_rising = get_realtime_rising_stocks(theme_mapping)

if not df_rising.empty:
    st.dataframe(
        df_rising,
        column_config={
            # 추가된 테마 컬럼을 보기 좋게 넓이 설정
            "관련 테마": st.column_config.TextColumn("소속 테마", width="medium"),
            "일봉": st.column_config.ImageColumn("일봉"),
            "월봉": st.column_config.ImageColumn("월봉"),
            "등락률(%)": st.column_config.NumberColumn(format="%.2f%%"),
            "급등이슈": st.column_config.LinkColumn("이슈 확인", display_text="📰뉴스보기"),
            "페이지 이동": st.column_config.LinkColumn("네이버 금융", display_text="🌐열기")
        },
        hide_index=True,
        use_container_width=True,
        height=1400 
    )
else:
    st.error("급등주 데이터를 불러오는 중 문제가 발생했습니다.")

# ---------------------------------------------------------
# 5. 15초 자동 새로고침 타이머
# ---------------------------------------------------------
st.markdown("---")
placeholder = st.empty()
for t in range(15, 0, -1):
    placeholder.caption(f"⏳ **{t}초** 후 실시간 데이터로 갱신됩니다...")
    time.sleep(1)
st.rerun()