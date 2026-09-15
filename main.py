import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(
    page_title="영화 박스오피스 분석 데이터 Dashboard", page_icon="🎬", layout="wide"
)


@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/keep-growing-park/data-science/refs/heads/main/dataset/kobis_1year_boxoffice.csv"
    df = pd.read_csv(url)
    df = df.dropna()
    df["기준일자"] = pd.to_datetime(df["기준일자"])
    df = df.sort_values(by="기준일자").reset_index(drop=True)
    return df


df = load_data()

st.title("🎬 1개년 박스오피스 영화 관객수 분석 앱")
st.markdown("---")

movie_max_audi = df.groupby("영화명")["누적관객수"].max().sort_values(ascending=False)
top_1_movie = movie_max_audi.index[0]

movie_df = df[df["영화명"] == top_1_movie]

st.header(f"1. 최다 흥행작 ({top_1_movie}) 일별 관객수 변화 추이")

if HAS_PLOTLY:
    fig1 = px.line(
        movie_df,
        x="기준일자",
        y="해당일관객수",
        title=f"<{top_1_movie}> 일별 관객수 추이",
        labels={"기준일자": "날짜", "해당일관객수": "해당일 관객수(명)"},
        markers=True,
    )
    fig1.update_traces(
        line_color="#FF4B4B", hovertemplate="%{x|%Y-%m-%d}<br>관객수: %{y:,}명"
    )
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.warning(
        "⚠️ `plotly` 라이브러리를 불러올 수 없어 기본 차트로 출력합니다."
        " `requirements.txt` 설정을 확인해 주세요."
    )
    chart_df1 = movie_df.set_index("기준일자")[["해당일관객수"]]
    st.line_chart(chart_df1)

st.info(
    f"💡 **이 그래프로 알 수 있는 것:** 최다 흥행작 {top_1_movie}의 개봉 후 날짜별"
    " 관객수 증감 변화 추이와 관객수가 가장 많이 몰린 피크(Peak) 시점을 확인할 수"
    " 있습니다."
)

st.markdown("---")

st.header(f"2. 최다 흥행작 ({top_1_movie}) 누적 관객수 변화 추이")

if HAS_PLOTLY:
    fig2 = px.area(
        movie_df,
        x="기준일자",
        y="누적관객수",
        title=f"<{top_1_movie}> 누적 관객수 추이",
        labels={"기준일자": "날짜", "누적관객수": "누적 관객수(명)"},
    )
    fig2.update_traces(
        line_color="#2E86C1", hovertemplate="%{x|%Y-%m-%d}<br>누적 관객수: %{y:,}명"
    )
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)
else:
    chart_df2 = movie_df.set_index("기준일자")[["누적관객수"]]
    st.area_chart(chart_df2)

st.info(
    f"💡 **이 그래프로 알 수 있는 것:** 시간 경과에 따른 {top_1_movie}의 총 누적 관객수"
    " 누적 완만도 및 흥행 정체/상승 구간을 한눈에 알 수 있습니다."
)

st.markdown("---")

st.header("3. 상위 5개 흥행 영화 누적 관객수 비교")

top5_movies = movie_max_audi.head(5).index.tolist()
top5_df = df[df["영화명"].isin(top5_movies)]

if HAS_PLOTLY:
    fig3 = px.line(
        top5_df,
        x="기준일자",
        y="누적관객수",
        color="영화명",
        title="TOP 5 흥행 영화 누적 관객수 추이 비교",
        labels={"기준일자": "날짜", "누적관객수": "누적 관객수(명)", "영화명": "영화 제목"},
    )
    fig3.update_traces(hovertemplate="%{x|%Y-%m-%d}<br>누적 관객수: %{y:,}명")
    fig3.update_layout(hovermode="x unified")
    st.plotly_chart(fig3, use_container_width=True)
else:
    chart_df3 = top5_df.pivot(
        index="기준일자", columns="영화명", values="누적관객수"
    )
    st.line_chart(chart_df3)

st.info(
    "💡 **이 그래프로 알 수 있는 것:** 가장 흥행한 상위 5개 영화 간의 누적 관객수 증가"
    " 속도 비교와 최종 흥행 스코어 달성에 걸린 기간 차이를 시각적으로 비교할 수 있습니다."
)

st.markdown("---")

st.header("4. 전체 TOP 10 영화 관객수 7일 이동평균 추이")

daily_top10_sum = df.groupby("기준일자")["해당일관객수"].sum().reset_index()
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
    "💡 **이 그래프로 알 수 있는 것:** 주말/평일 반복에 따른 단기 변동성을 제거하여"
    " 전체 극장가 박스오피스 시장의 거시적인 성수기/비수기 흐름과 흐름 전환점을 파악할 수"
    " 있습니다."
)

st.markdown("---")

st.header("5. 월별 전체 관객수 합계 추이")

daily_top10_sum["연월"] = daily_top10_sum["기준일자"].dt.strftime("%Y-%m")
monthly_sum = daily_top10_sum.groupby("연월")["해당일관객수"].sum().reset_index()

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
    "💡 **이 그래프로 알 수 있는 것:** 월 단위 총 관객수를 집계하여 1년 중"
    " 영화관 방문객이 가장 많은 최성수기 월과 비수기 월을 직관적으로 비교·파악할 수"
    " 있습니다."
)

st.markdown("---")
