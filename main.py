import streamlit as st
st.title("나의 데이터 과학 포트폴리오")
st.write("반갑습니다! 이제부터 여기에 제 작업을 기록합니다.")

from datetime import datetime, timedelta
import zoneinfo
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="박스오피스 조회", page_icon="🎬", layout="wide"
)


def get_yesterday_date_kst():
    kst = zoneinfo.ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
    return (now_kst - timedelta(days=1)).date()


@st.cache_data(ttl=3600)
def fetch_daily_boxoffice(api_key, target_date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": api_key, "targetDt": target_date_str}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data, None
    except Exception as e:
        return None, str(e)


st.title("🎬 박스오피스 순위 조회")

if "KOBIS_KEY" not in st.secrets:
    st.error(
        "❌ Streamlit Secrets에 `KOBIS_KEY`가 설정되지 않았습니다. Secrets를 확인해 주세요."
    )
    st.stop()

api_key = st.secrets["KOBIS_KEY"]
max_selectable_date = get_yesterday_date_kst()

selected_date = st.date_input(
    "조회할 날짜를 선택하세요",
    value=max_selectable_date,
    max_value=max_selectable_date,
)

target_date_str = selected_date.strftime("%Y%m%d")
formatted_date = selected_date.strftime("%Y년 %m월 %d일")
st.write(f" 기준 일자: **{formatted_date}**")

data, error_msg = fetch_daily_boxoffice(api_key, target_date_str)

box_office_result = data.get("boxOfficeResult", {}) if data else {}
daily_list = box_office_result.get("dailyBoxOfficeList", [])
fault_info = data.get("faultInfo", None) if data else None

if error_msg or fault_info or not daily_list:
    st.warning("⚠️ 데이터를 가져오지 못했습니다. 아래 사항을 확인해 주세요.")

    if fault_info:
        st.error(
            f"🔑 API 인증 오류: {fault_info.get('message', '인증키가 유효하지 않습니다.')}"
        )
    elif error_msg:
        st.error(f"🌐 통신 오류: {error_msg}")
    elif not daily_list:
        st.info("📭 그날은 아직 집계 전입니다.")

    st.markdown("""
    ---
    **💡 확인 조치 안내:**
    1. Streamlit Cloud의 `Secrets` 설정에 **KOBIS_KEY**가 바르게 입력되었는지 확인해 주세요.
    2. KOBIS 개방형 API 포털에서 발급받은 키의 상태(사용 승인 여부)를 확인해 주세요.
    3. 잠시 후 페이지를 새로고침 해보세요.
    """)
    st.stop()

df = pd.DataFrame(daily_list)

numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

df = df.sort_values("rank").reset_index(drop=True)


def format_rank_change(val):
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔹 {abs(val)}"
    else:
        return "-"


df["순위 변동"] = df["rankInten"].apply(format_rank_change)
df["display_movieNm"] = df.apply(
    lambda row: f"🏆 {row['movieNm']}"
    if row["audiAcc"] >= 1_000_000
    else row["movieNm"],
    axis=1,
)

top_movie = df.iloc[0]

st.subheader(f"🏆 1위: {top_movie['display_movieNm']}")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="일별 관객수", value=f"{top_movie['audiCnt']:,} 명"
    )
with col2:
    st.metric(
        label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명"
    )
with col3:
    st.metric(
        label="스크린수", value=f"{top_movie['scrnCnt']:,} 개"
    )

st.divider()

st.subheader("📊 관객수 상위 5개 영화")
top5_df = df.head(5).copy()

chart_df = top5_df.set_index("movieNm")[["audiCnt"]]
chart_df.columns = ["관객수"]
st.bar_chart(chart_df)

st.divider()

st.subheader("📋 전체 순위 목록")

display_df = df[
    [
        "rank",
        "순위 변동",
        "display_movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]
].copy()
display_df.columns = [
    "순위",
    "순위 변동",
    "영화명",
    "개봉일",
    "일별 관객수",
    "누적 관객수",
    "스크린수",
]

st.dataframe(
    display_df.style.format(
        {"일별 관객수": "{:,}", "누적 관객수": "{:,}", "스크린수": "{:,}"}
    ),
    use_container_width=True,
    hide_index=True,
)
