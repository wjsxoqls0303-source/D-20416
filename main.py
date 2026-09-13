import streamlit as st
st.title("나의 데이터 과학 포트폴리오")
st.write("반갑습니다! 이제부터 여기에 제 작업을 기록합니다.")
# -*- coding: utf-8 -*-
"""
어제자 KOBIS 일별 박스오피스를 보여주는 스트림릿 앱입니다.
초보자를 위해 각 단계마다 한국어 주석을 달아두었습니다.
"""

import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------
# 1. 기본 설정
# ----------------------------------------------------------------
st.set_page_config(page_title="어제의 박스오피스", page_icon="🎬", layout="wide")

KOBIS_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"

# 표/카드에서 사용할 컬럼 이름을 미리 한글로 정의해둡니다.
COLUMN_LABELS = {
    "rank": "순위",
    "movieNm": "영화명",
    "openDt": "개봉일",
    "audiCnt": "관객수",
    "audiAcc": "누적관객",
    "scrnCnt": "스크린수",
}

# 문자열로 오는 숫자 항목들 (콤마가 섞여 올 수도 있어서 함께 처리합니다)
NUMERIC_COLUMNS = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]


# ----------------------------------------------------------------
# 2. "어제" 날짜를 한국 시간(KST) 기준으로 계산하는 함수
#    - 배포 서버의 시계가 한국 시간이 아닐 수 있으므로,
#      UTC 기준 현재 시각에 9시간을 더해 KST로 직접 변환합니다.
#    - zoneinfo/pytz 같은 외부 시간대 라이브러리를 쓰지 않아서
#      배포 환경에 tzdata가 없어도 안전하게 동작합니다.
# ----------------------------------------------------------------
def get_yesterday_kst_str() -> str:
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)                  # 현재 한국 시각
    yesterday_kst = now_kst - timedelta(days=1)   # 어제(한국 시각 기준)
    return yesterday_kst.strftime("%Y%m%d")       # yyyymmdd 형태 문자열로 변환


# ----------------------------------------------------------------
# 3. KOBIS API 호출 함수
#    - st.cache_data(ttl=3600) 덕분에, 같은 target_dt로 다시 호출하면
#      1시간(3600초) 동안은 실제 API를 부르지 않고 저장된 결과를 재사용합니다.
#    - 성공하면 (영화 리스트, None) 을 반환하고,
#      문제가 생기면 (None, "한국어 안내 문구") 를 반환합니다.
# ----------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office(target_dt: str, api_key: str):
    params = {"key": api_key, "targetDt": target_dt}

    # (1) 네트워크 요청 자체가 실패하는 경우 (인터넷 문제, 타임아웃 등)
    try:
        response = requests.get(KOBIS_URL, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        return None, f"KOBIS 서버에 요청하는 중 오류가 발생했습니다: {e}\n인터넷 연결 상태를 확인해 주세요."

    # (2) 응답은 왔지만 상태코드가 200이 아닌 경우
    if response.status_code != 200:
        return None, f"KOBIS 서버가 오류 상태코드({response.status_code})를 반환했습니다. 잠시 후 다시 시도해 주세요."

    # (3) 응답이 JSON 형식이 아닌 경우
    try:
        data = response.json()
    except ValueError:
        return None, "KOBIS 응답이 올바른 JSON 형식이 아닙니다. API 주소나 서버 상태를 확인해 주세요."

    # (4) 인증키가 틀리면 상태코드는 200이어도 faultInfo 상자가 옵니다.
    if "faultInfo" in data:
        fault = data["faultInfo"]
        message = fault.get("message", "알 수 없는 오류")
        return None, (
            f"KOBIS API 오류 응답을 받았습니다: {message}\n"
            "Streamlit Cloud의 Secrets에 등록한 KOBIS_KEY 값이 올바른지 확인해 주세요."
        )

    # (5) boxOfficeResult 자체가 없는 경우 (응답 구조가 예상과 다른 경우)
    box_office_result = data.get("boxOfficeResult")
    if not box_office_result:
        return None, "응답에 boxOfficeResult 항목이 없습니다. targetDt 값이나 API 문서를 다시 확인해 주세요."

    # (6) 영화 목록이 비어 있는 경우 (예: 아직 집계되지 않은 날짜를 조회한 경우)
    movie_list = box_office_result.get("dailyBoxOfficeList")
    if not movie_list:
        return None, (
            "조회한 날짜의 박스오피스 데이터가 비어 있습니다.\n"
            "targetDt(조회 날짜)가 아직 집계되지 않았거나, 너무 과거/미래 날짜는 아닌지 확인해 주세요."
        )

    return movie_list, None


# ----------------------------------------------------------------
# 4. 문자열 숫자를 실제 숫자(int)로 바꿔주는 함수
#    - API 응답의 숫자 항목은 전부 문자열로 오기 때문에,
#      정렬이나 그래프에 쓰려면 반드시 숫자로 변환해야 합니다.
#    - 혹시 콤마(,)가 섞여 오더라도 안전하게 처리합니다.
# ----------------------------------------------------------------
def to_int_safe(value) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


# ----------------------------------------------------------------
# 5. 화면 그리기 시작
# ----------------------------------------------------------------
st.title("🎬 어제의 박스오피스")

target_dt = get_yesterday_kst_str()
st.caption(f"조회 날짜(한국 시간 기준 어제): {target_dt}")

# (1) 인증키를 secrets에서 불러옵니다. 코드에는 절대 키를 직접 쓰지 않습니다.
try:
    api_key = st.secrets["KOBIS_KEY"]
except (KeyError, FileNotFoundError):
    st.error(
        "인증키(KOBIS_KEY)를 찾을 수 없습니다.\n"
        "Streamlit Cloud의 [Manage app] → [Settings] → [Secrets] 메뉴에서\n"
        'KOBIS_KEY = "발급받은_인증키" 형태로 등록해 주세요.'
    )
    st.stop()

# (2) API 호출 (캐시가 적용되어 있어, 같은 target_dt면 1시간 내 재호출하지 않습니다)
movie_list, error_message = fetch_box_office(target_dt, api_key)

# (3) 오류가 있으면 안내 문구만 보여주고 종료합니다.
if error_message:
    st.error(error_message)
    st.stop()

# ----------------------------------------------------------------
# 6. 데이터프레임으로 변환하고 숫자형 컬럼을 정리합니다.
# ----------------------------------------------------------------
df = pd.DataFrame(movie_list)

for col in NUMERIC_COLUMNS:
    if col in df.columns:
        df[col] = df[col].apply(to_int_safe)

# 순위(rank) 기준으로 정렬 (숫자로 변환했으므로 정확하게 정렬됩니다)
df = df.sort_values("rank").reset_index(drop=True)

# ----------------------------------------------------------------
# 7. 1위 영화를 지표 카드 3장으로 크게 보여주기
# ----------------------------------------------------------------
top_movie = df.iloc[0]

st.subheader(f"🥇 1위: {top_movie['movieNm']}")

col1, col2, col3 = st.columns(3)
col1.metric("어제 관객수", f"{top_movie['audiCnt']:,}명")
col2.metric("누적 관객수", f"{top_movie['audiAcc']:,}명")
col3.metric("스크린수", f"{top_movie['scrnCnt']:,}개")

st.divider()

# ----------------------------------------------------------------
# 8. 관객수 상위 5편 막대그래프
# ----------------------------------------------------------------
st.subheader("📊 관객수 상위 5편")

top5 = df.sort_values("audiCnt", ascending=False).head(5)
chart_data = top5.set_index("movieNm")[["audiCnt"]]
chart_data = chart_data.rename(columns={"audiCnt": "관객수"})

st.bar_chart(chart_data)

st.divider()

# ----------------------------------------------------------------
# 9. 전체 순위표
# ----------------------------------------------------------------
st.subheader("📋 전체 박스오피스 순위")

table_df = df[list(COLUMN_LABELS.keys())].rename(columns=COLUMN_LABELS)
st.dataframe(table_df, use_container_width=True, hide_index=True)
