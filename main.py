import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="영화 데이터 그래프 도감 2 - 분포와 관계",
    page_icon="🎬",
    layout="wide",
)


@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"
    df = pd.read_csv(url)

    df["openDt"] = pd.to_datetime(
        df["openDt"].astype(str), format="%Y%m%d", errors="coerce"
    )
    df["genre"] = df["genre"].fillna("미정").astype(str).str.split("|").str[0]
    df["nation"] = df["nation"].fillna("기타")

    return df


df = load_data()

st.title("🎬 영화 데이터 그래프 도감 2 - 분포와 관계")
st.markdown("---")

st.header("1. 장르별 영화 편수 분포")

genre_counts = df["genre"].value_counts().reset_index()
genre_counts.columns = ["장르", "편수"]

fig1 = px.pie(
    genre_counts,
    names="장르",
    values="편수",
    title="장르별 영화 편수 비율",
    hole=0.4,
)

fig1.update_traces(
    hovertemplate="<b>장르: %{label}</b><br>영화 편수: %{value}편<br>비율: %{percent}<extra></extra>",
    textinfo="percent+label",
)

fig1.update_layout(hovermode="closest")

st.plotly_chart(fig1, use_container_width=True)

st.info(
    "💡 **이 그래프로 알 수 있는 것:** 최근 1년간 박스오피스 상위권에 들어간 주요 영화들의 장르별 편수 비중을 파악하여, 어떤 장르가 시장을 주도하고 있는지 한눈에 확인할 수 있습니다."
)

st.markdown("---")

st.header("2. 장르 및 영화별 총 관객 수 분포 (트리맵)")

fig2 = px.treemap(
    df,
    path=[px.Constant("전체 영화"), "genre", "movieNm"],
    values="total_audi",
    title="장르 및 영화별 총 관객 수 비중",
    color="genre",
)

fig2.update_traces(
    hovertemplate="<b>%{label}</b><br>총 관객 수: %{value:,}명<extra></extra>"
)

st.plotly_chart(fig2, use_container_width=True)

st.info(
    "💡 **이 그래프로 알 수 있는 것:** 각 장르 내부에서 어떤 영화가 전체 관객 동원을 주도했는지 직관적인 면적 크기를 통해 비교할 수 있습니다."
)

st.markdown("---")

st.header("3. 총 관객 수 분포 (히스토그램)")

fig3 = px.histogram(
    df,
    x="total_audi",
    nbins=30,
    title="영화별 총 관객 수 분포",
    labels={"total_audi": "총 관객 수(명)", "count": "영화 수"},
    color_discrete_sequence=["#3366CC"],
)

fig3.update_traces(
    hovertemplate="관객 수 구간: %{x}<br>영화 수: %{y}편<extra></extra>"
)

fig3.update_layout(
    xaxis_title="총 관객 수(명)",
    yaxis_title="영화 수(편)",
    bargap=0.1,
)

st.plotly_chart(fig3, use_container_width=True)

max_movie = df.loc[df["total_audi"].idxmax()]
max_movie_name = max_movie["movieNm"]
max_movie_audi = max_movie["total_audi"]

under_1M_count = (df["total_audi"] <= 1_000_000).sum()
under_1M_ratio = (under_1M_count / len(df)) * 100

st.info(
    f"💡 **이 그래프로 알 수 있는 것:** 대부분의 영화({under_1M_ratio:.1f}%)가 관객 수 **100만 명 이하 구간**에 밀집해 있는 반면, 가장 많은 관객을 모은 영화는 **'{max_movie_name}'**({max_movie_audi:,}명)으로 흥행 편차가 매우 큼을 알 수 있습니다."
)

st.markdown("---")

st.header("4. 개봉일 스크린 수와 총 관객 수의 관계 (산점도)")

fig4 = px.scatter(
    df,
    x="first_scrn",
    y="total_audi",
    color="genre",
    hover_name="movieNm",
    title="개봉일 스크린 수 vs 총 관객 수",
    labels={
        "first_scrn": "개봉일 스크린 수(개)",
        "total_audi": "총 관객 수(명)",
        "genre": "장르",
    },
)

fig4.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>개봉일 스크린 수: %{x:,}개<br>총 관객 수: %{y:,}명<extra></extra>"
)

fig4.update_layout(
    xaxis_title="개봉일 스크린 수(개)",
    yaxis_title="총 관객 수(명)",
)

st.plotly_chart(fig4, use_container_width=True)

st.info(
    "💡 **이 그래프로 알 수 있는 것:** 개봉일 스크린 수가 많을수록 대체로 총 관객 수가 증가하는 양의 상관관계를 보이며, 초기 상영관 확보(스크린 수)가 최종 흥행 성과에 결정적인 영향을 미침을 알 수 있습니다."
)

st.markdown("---")

st.header("5. 주요 장르별 총 관객 수 분포 (박스플롯)")

genre_counts_series = df["genre"].value_counts()
major_genres = genre_counts_series[genre_counts_series >= 10].index
df_major_genres = df[df["genre"].isin(major_genres)]

fig5 = px.box(
    df_major_genres,
    x="genre",
    y="total_audi",
    color="genre",
    hover_name="movieNm",
    points="outliers",
    title="영화 10편 이상 장르별 총 관객 수 분포 및 이상치",
    labels={
        "genre": "장르",
        "total_audi": "총 관객 수(명)",
    },
)

fig5.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>장르: %{x}<br>관객 수: %{y:,}명<extra></extra>"
)

fig5.update_layout(
    xaxis_title="장르",
    yaxis_title="총 관객 수(명)",
    showlegend=False,
)

st.plotly_chart(fig5, use_container_width=True)

st.info(
    "💡 **이 그래프로 알 수 있는 것:** 주요 장르별 관객 수의 중앙값과 범위를 비교할 수 있으며, 박스 밖으로 튀어나온 이상치(Outlier) 점들을 통해 장르의 평균적인 흥행 규모를 뛰어넘은 '대박 흥행작'들을 식별할 수 있습니다."
)

st.markdown("---")

st.header("6. 스크린 수, 총 관객 수, 개봉 첫 주 관객 수의 관계 (버블 차트)")

fig6 = px.scatter(
    df,
    x="first_scrn",
    y="total_audi",
    size="first_week_audi",
    color="genre",
    hover_name="movieNm",
    size_max=50,
    title="개봉일 스크린 수 vs 총 관객 수 (버블 크기: 개봉 첫 주 관객 수)",
    labels={
        "first_scrn": "개봉일 스크린 수(개)",
        "total_audi": "총 관객 수(명)",
        "first_week_audi": "개봉 첫 주 관객 수(명)",
        "genre": "장르",
    },
)

fig6.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>개봉일 스크린 수: %{x:,}개<br>총 관객 수: %{y:,}명<br>개봉 첫 주 관객 수: %{marker.size:,}명<extra></extra>"
)

fig6.update_layout(
    xaxis_title="개봉일 스크린 수(개)",
    yaxis_title="총 관객 수(명)",
)

st.plotly_chart(fig6, use_container_width=True)

st.info(
    "💡 **이 그래프로 알 수 있는 것:** 개봉일 스크린 수가 많을수록 개봉 첫 주 관객 수(버블 크기)와 최종 총 관객 수가 모두 증가하며, 초기 흥행(첫 주 성적)이 최종 실적으로 직결되는 패턴을 다차원적으로 파악할 수 있습니다."
)

st.markdown("---")

st.header("7. 제작 국가 및 장르별 영화 편수 분포 (선버스트)")

fig7 = px.sunburst(
    df,
    path=["nation", "genre"],
    title="제작 국가 ➔ 장르별 영화 편수 비중",
    color="nation",
)

fig7.update_traces(
    hovertemplate="<b>%{label}</b><br>영화 편수: %{value}편<extra></extra>"
)

st.plotly_chart(fig7, use_container_width=True)

st.info(
    "💡 **이 그래프로 알 수 있는 것:** 주요 제작 국가별로 공급된 영화들의 다양성 및 각 국가가 집중 생산하는 주력 장르의 분포 구성을 계층적으로 파악할 수 있습니다."
)

st.markdown("---")

st.header("8. 국가별 제작한 영화의 우리나라 스크린수는 얼마나 차지하는가")

# 1. 상단: 선버스트 그래프
fig8 = px.sunburst(
    df,
    path=["nation", "movieNm"],
    values="first_scrn",
    title="국가별 제작한 영화의 우리나라 스크린수는 얼마나 차지하는가",
    color="nation",
)

fig8.update_traces(
    textinfo="label+value",
    hovertemplate="<b>%{label}</b><br>개봉일 스크린 수: %{value:,}개<extra></extra>",
)

st.plotly_chart(fig8, use_container_width=True)

st.info(
    "💡 **이 그래프로 알 수 있는 것:** 국내 개봉 시장에서 국가별 전체 스크린 확보 비중과 함께, 각 국가 내 개별 영화가 점유한 스크린 수를 선버스트 계층 구조로 명확히 파악할 수 있습니다."
)

# 2. 하단: 영화 선택 검색 및 스크린 수/제작국가 정보 표시
st.subheader("🎬 개별 영화 스크린 수 및 제작 국가 조회")

movie_list = sorted(df["movieNm"].dropna().unique())
selected_movie = st.selectbox("정보를 확인할 영화를 선택하세요:", movie_list)

if selected_movie:
    movie_info = df[df["movieNm"] == selected_movie].iloc[0]

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="제작 국가", value=str(movie_info["nation"]))
    with col2:
        st.metric(
            label="개봉일 스크린 수", value=f"{int(movie_info['first_scrn']):,}개"
        )

st.markdown("---")
