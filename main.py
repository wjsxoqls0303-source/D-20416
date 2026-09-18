import zoneinfo
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(
    page_title="영화 박스오피스 통합 대시보드",
    page_icon="🎬",
    layout="wide",
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
        return response.json(), None
    except Exception as e:
        return None, str(e)


@st.cache_data
def load_historical_data():
    url = "https://raw.githubusercontent.com/keep-growing-park/data-science/refs/heads/main/dataset/kobis_1year_boxoffice.csv"
    df = pd.read_csv(url)
    df = df.dropna()
    df["기준일자"] = pd.to_datetime(df["기준일자"])
    df = df.sort_values(by="기준일자").reset_index(drop=True)
    return df


def format_rank_change(val):
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔹 {abs(val)}"
    else:
        return "-"


st.sidebar.title("📌 메뉴 선택")
page = st.sidebar.radio(
    "원하는 분석 페이지를 선택하세요:",
    ["일별 박스오피스 실시간 조회", "1개년 박스오피스 추이 분석"],
)

st.sidebar.markdown("---")


if page == "일별 박스오피스 실시간 조회":
    st.title("🎬 일별 박스오피스 순위 조회")

    if "KOBIS_KEY" not in st.secrets:
        st.error(
            "❌ Streamlit Secrets에 `KOBIS_KEY`가 설정되지 않았습니다. Secrets 설정을 확인해 주세요."
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
    st.write(f"기준 일자: **{formatted_date}**")

    data, error_msg = fetch_daily_boxoffice(api_key, target_date_str)
    box_office_result = data.get("boxOfficeResult", {}) if data else {}
    daily_list = box_office_result.get("dailyBoxOfficeList", [])
    fault_info = data.get("faultInfo", None) if data else None

    if error_msg or fault_info or not daily_list:
        st.warning("⚠️ 데이터를 가져오지 못했습니다.")
        if fault_info:
            st.error(
                f"🔑 API 인증 오류: {fault_info.get('message', '인증키가 유효하지 않습니다.')}"
            )
        elif error_msg:
            st.error(f"🌐 통신 오류: {error_msg}")
        elif not daily_list:
            st.info("📭 해당 날짜의 박스오피스 데이터가 존재하지 않습니다.")
        st.stop()

    df = pd.DataFrame(daily_list)
    numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
    for col in numeric_cols:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        )

    df = df.sort_values("rank").reset_index(drop=True)
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
    col1.metric("일별 관객수", f"{top_movie['audiCnt']:,} 명")
    col2.metric("누적 관객수", f"{top_movie['audiAcc']:,} 명")
    col3.metric("스크린수", f"{top_movie['scrnCnt']:,} 개")

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


else:
    st.title("📈 1개년 박스오피스 영화 관객수 분석")

    df_hist = load_historical_data()

    movie_max_audi = (
        df_hist.groupby("영화명")["누적관객수"]
        .max()
        .sort_values(ascending=False)
    )
    movie_list = movie_max_audi.index.tolist()

    selected_movie = st.sidebar.selectbox(
        "관람 추이를 확인할 영화를 선택하세요:",
        movie_list,
        key="hist_movie_select",
    )

    movie_df = df_hist[df_hist["영화명"] == selected_movie]

    st.header("1. 일별 관객수 변화 추이")
    if HAS_PLOTLY:
        fig1 = px.line(
            movie_df,
            x="기준일자",
            y="해당일관객수",
            title=f"<{selected_movie}> 일별 관객수 추이",
            labels={"기준일자": "날짜", "해당일관객수": "해당일 관객수(명)"},
            markers=True,
        )
        fig1.update_traces(
            line_color="#FF4B4B",
            hovertemplate="%{x|%Y-%m-%d}<br>관객수: %{y:,}명",
        )
        fig1.update_layout(hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.line_chart(movie_df.set_index("기준일자")[["해당일관객수"]])

    st.info(
        f"💡 **분석 포인트:** {selected_movie}의 개봉 후 날짜별 관객수 증감 변화 추이와 관객수가 가장 많이 몰린 피크(Peak) 시점을 확인할 수 있습니다."
    )
    st.markdown("---")

    st.header("2. 누적 관객수 변화 추이")
    if HAS_PLOTLY:
        fig2 = px.area(
            movie_df,
            x="기준일자",
            y="누적관객수",
            title=f"<{selected_movie}> 누적 관객수 추이",
            labels={"기준일자": "날짜", "누적관객수": "누적 관객수(명)"},
        )
        fig2.update_traces(
            line_color="#2E86C1",
            hovertemplate="%{x|%Y-%m-%d}<br>누적 관객수: %{y:,}명",
        )
        fig2.update_layout(hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.area_chart(movie_df.set_index("기준일자")[["누적관객수"]])

    st.info(
        f"💡 **분석 포인트:** 시간 경과에 따른 {selected_movie}의 총 누적 관객수 증가 곡선과 흥행 정체/상승 구간을 파악할 수 있습니다."
    )
    st.markdown("---")

    st.header("3. long-run 영화 (20일 이상 등장) TOP 5 누적 관객수 비교")

    movie_days = df_hist.groupby("영화명")["기준일자"].nunique()
    qualified_movies = movie_days[movie_days >= 20].index

    top5_qualified_movies = (
        df_hist[df_hist["영화명"].isin(qualified_movies)]
        .groupby("영화명")["누적관객수"]
        .max()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )

    top5_qualified_df = df_hist[df_hist["영화명"].isin(top5_qualified_movies)]

    if HAS_PLOTLY:
        fig3 = px.line(
            top5_qualified_df,
            x="기준일자",
            y="누적관객수",
            color="영화명",
            title="TOP 10 20일 이상 진입 영화 중 흥행 TOP 5 누적 관객수 비교",
            labels={
                "기준일자": "날짜",
                "누적관객수": "누적 관객수(명)",
                "영화명": "영화 제목",
            },
        )
        fig3.update_traces(
            hovertemplate="%{x|%Y-%m-%d}<br>누적 관객수: %{y:,}명"
        )
        fig3.update_layout(hovermode="x unified")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        chart_df3 = top5_qualified_df.pivot(
            index="기준일자", columns="영화명", values="누적관객수"
        )
        st.line_chart(chart_df3)

    st.info(
        "💡 **이 그래프로 알 수 있는 것:** 단기 깜짝 흥행에 그치지 않고 20일 이상 장기 흥행(Long-run)을 이어간 최상위 영화들의 누적 관객수 가파름과 스코어 변화 양상을 비교해볼 수 있습니다."
    )
    st.markdown("---")

    # 4. 전체 TOP 10 영화 관객수 7일 이동평균 추이
    st.header("4. 전체 TOP 10 영화 관객수 7일 이동평균 추이")

    daily_top10_sum = (
        df_hist.groupby("기준일자")["해당일관객수"].sum().reset_index()
    )
    daily_top10_sum["7일_이동평균"] = (
        daily_top10_sum["해당일관객수"].rolling(window=7, min_periods=1).mean()
    )

    if HAS_PLOTLY:
        fig4 = go.Figure()

        fig4.add_trace(
            go.Scatter(
                x=daily_top10_sum["기준일자"],
                y=daily_top10_sum["해당일관객수"],
                mode="lines",
                name="일별 총관객수 (원본)",
                line=dict(color="rgba(255, 154, 162, 0.4)", width=1.5),
                hovertemplate="%{x|%Y-%m-%d}<br>일별 관객수: %{y:,}명",
            )
        )

        fig4.add_trace(
            go.Scatter(
                x=daily_top10_sum["기준일자"],
                y=daily_top10_sum["7일_이동평균"],
                mode="lines",
                name="7일 이동평균",
                line=dict(color="#D90429", width=3),
                hovertemplate="%{x|%Y-%m-%d}<br>7일 이동평균: %{y:,.0f}명",
            )
        )

        fig4.update_layout(
            title="일별 TOP 10 영화 총 관객수 및 7일 이동평균 추이",
            xaxis_title="날짜",
            yaxis_title="관객수(명)",
            hovermode="x unified",
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        chart_df4 = daily_top10_sum.set_index("기준일자")[
            ["해당일관객수", "7일_이동평균"]
        ]
        st.line_chart(chart_df4)

    st.info(
        "💡 **이 그래프로 알 수 있는 것:** 주말과 평일 간의 반복적인 단기 관객수 변동을 보정하여, 전체 극장가 박스오피스 시장의 거시적인 성수기·비수기 흐름과 추세 전환점을 직관적으로 파악할 수 있습니다."
    )
    st.markdown("---")

    # 5. 월별 전체 관객수 합계 추이 (막대그래프)
    st.header("5. 월별 전체 관객수 합계 추이")

    daily_top10_sum["연월"] = daily_top10_sum["기준일자"].dt.strftime("%Y-%m")
    monthly_sum = (
        daily_top10_sum.groupby("연월")["해당일관객수"].sum().reset_index()
    )

    if HAS_PLOTLY:
        fig5 = px.bar(
            monthly_sum,
            x="연월",
            y="해당일관객수",
            title="월별 극장가 전체 관객수 합계",
            labels={"연월": "조회 월", "해당일관객수": "월간 총 관객수(명)"},
            text_auto=",.0f",
        )
        fig5.update_traces(
            marker_color="#27AE60",
            hovertemplate="%{x}<br>월간 총 관객수: %{y:,}명",
            textposition="outside",
        )
        st.plotly_chart(fig5, use_container_width=True)
    else:
        chart_df5 = monthly_sum.set_index("연월")[["해당일관객수"]]
        st.bar_chart(chart_df5)

    st.info(
        "💡 **이 그래프로 알 수 있는 것:** 월 단위로 집계된 총 관객수를 통해 1년 중 극장가 이용객이 집중되는 최성수기 월과 비수기 월을 한눈에 비교 및 분석할 수 있습니다."
    )
    st.markdown("---")

  # 6. 캘린더 히트맵 (월별/주차별 × 요일별 관객수 분포)
    st.header("6. 요일 및 주차별 관객수 분포 (캘린더 히트맵)")

    heatmap_df = daily_top10_sum.copy()
    
    # 요일 순서 지정 (월요일 ~ 일요일)
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days_ko = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    day_map = dict(zip(days_order, days_ko))

    # 요일 변환 및 YYYY-MM-DD 문자열 생성
    heatmap_df["요일명"] = heatmap_df["기준일자"].dt.day_name().map(day_map)
    heatmap_df["주차"] = (
        heatmap_df["기준일자"].dt.strftime("%Y-%m")
        + " "
        + ((heatmap_df["기준일자"].dt.day - 1) // 7 + 1).astype(str)
        + "주차"
    )
    heatmap_df["YYYY-MM-DD"] = heatmap_df["기준일자"].dt.strftime("%Y-%m-%d")

    if HAS_PLOTLY:
        # custom_data 대신 hover_data를 사용하여 TypeError 방지
        fig6 = px.density_heatmap(
            heatmap_df,
            x="요일명",
            y="주차",
            z="해당일관객수",
            color_continuous_scale="Reds",
            title="날짜별 관객수 히트맵 (월~일 순서)",
            labels={
                "요일명": "요일",
                "주차": "월 / 주차",
                "해당일관객수": "관객수(명)",
                "YYYY-MM-DD": "날짜"
            },
            category_orders={"요일명": days_ko}, # 요일 순서 강제 고정
            hover_data={"YYYY-MM-DD": True}
        )

        fig6.update_traces(
            hovertemplate="<b>날짜: %{customdata[0]}</b><br>요일: %{x}<br>일관객수: %{z:,}명<extra></extra>"
        )

        fig6.update_layout(
            xaxis_title="요일",
            yaxis_title="월 / 주차",
            yaxis=dict(autorange="reversed"),
        )

        st.plotly_chart(fig6, use_container_width=True)
    else:
        st.warning("⚠️ 캘린더 히트맵 출력을 위해 Plotly 라이브러리가 필요합니다.")


import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="영화 데이터 그래프 도감 2 - 분포와 관계",
    page_icon="🎬",
    layout="wide",
)


# 데이터 로드 및 전처리 함수
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"
    df = pd.read_csv(url)

    # 개봉일(openDt)을 문자열 변환 후 datetime 타입으로 변환
    df["openDt"] = pd.to_datetime(
        df["openDt"].astype(str), format="%Y%m%d", errors="coerce"
    )

    # 장르(genre)가 여러 개(예: '액션|드라마')인 경우 첫 번째 장르만 추출
    df["genre"] = (
        df["genre"].astype(str).apply(lambda x: x.split("|")[0] if x else x)
    )

    return df


# 데이터 불러오기
df = load_data()

# 앱 메인 타이틀
st.title("🎬 영화 데이터 그래프 도감 2 - 분포와 관계")
st.markdown("---")


# -------------------------------------------------------------------
# 그래프 1: 장르별 영화 편수 (도넛 차트)
# -------------------------------------------------------------------
st.header("1. 장르별 영화 편수 분포")

# 장르별 영화 편수 집계
genre_counts = (
    df["genre"].value_counts().reset_index(name="편수").rename(columns={"index": "장르"})
)

# Plotly 도넛 차트 생성
fig1 = px.pie(
    genre_counts,
    names="장르",
    values="편수",
    title="장르별 영화 편수 비율",
    hole=0.4,  # 도넛 형태 지정
)

# 마우스 호버 시 편수 및 비율 표기 지정
fig1.update_traces(
    hovertemplate="<b>장르: %{label}</b><br>영화 편수: %{value}편<br>비율: %{percent}<extra></extra>",
    textinfo="percent+label",
)

fig1.update_layout(hovermode="closest")

# Streamlit 화면에 차트 출력
st.plotly_chart(fig1, use_container_width=True)

# '이 그래프로 알 수 있는 것' 안내 섹션
st.info(
    "💡 **이 그래프로 알 수 있는 것:** 최근 1년간 박스오피스 상위권에 들어간 주요 영화들의 장르별 편수 비중을 파악하여, 어떤 장르가 시장을 주도하고 있는지 한눈에 확인할 수 있습니다."
)

st.markdown("---")
