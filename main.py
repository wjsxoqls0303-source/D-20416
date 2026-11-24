import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

st.set_page_config(
    page_title="다이아몬드 가격 예측 AI",
    page_icon="💎",
    layout="wide"
)

# 데이터 로드 및 모델 학습/캐싱
@st.cache_resource
def load_data_and_model():
    df = pd.read_csv("diamonds_cleaned_step3.csv")
    
    df_fe = df.copy()
    df_fe["log_carat"] = np.log(df_fe["carat"])
    df_fe["volume"] = df_fe["x"] * df_fe["y"] * df_fe["z"]
    df_fe["log_volume"] = np.log(df_fe["volume"])
    df_fe["xy_ratio"] = df_fe["x"] / df_fe["y"]

    carat_bins = pd.qcut(df_fe["carat"], q=10, labels=False)
    X = df_fe.drop(columns=["price"])
    y = df_fe["price"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=carat_bins
    )

    num_cols = ["carat", "log_carat", "depth", "table", "x", "y", "z", "log_volume", "xy_ratio"]
    cat_cols = ["cut", "color", "clarity"]

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(drop="first", sparse_output=False), cat_cols)
    ])

    model = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", Ridge(alpha=1.0))
    ])

    model.fit(X_train[num_cols + cat_cols], np.log(y_train))
    y_pred = np.exp(model.predict(X_test[num_cols + cat_cols]))

    metrics = {
        "r2": r2_score(y_test, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
        "mae": mean_absolute_error(y_test, y_pred),
        "mape": np.mean(np.abs((y_test - y_pred) / y_test)) * 100
    }
    return df, model, num_cols, cat_cols, metrics, y_test, y_pred

df, model, num_cols, cat_cols, metrics, y_test, y_pred = load_data_and_model()

# 사이드바: 다이아몬드 스펙 입력
st.sidebar.header("💎 다이아몬드 스펙 입력")

carat = st.sidebar.slider("Carat (중량, ct)", min_value=0.20, max_value=5.01, value=1.00, step=0.01)
cut = st.sidebar.selectbox("Cut (커팅 등급)", ["Ideal", "Premium", "Very Good", "Good", "Fair"], index=0)
color = st.sidebar.selectbox("Color (색상, D가 최고)", ["D", "E", "F", "G", "H", "I", "J"], index=2)
clarity = st.sidebar.selectbox("Clarity (투명도, IF가 최고)", ["IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2", "I1"], index=3)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 물리적 치수 및 비율")

# 캐럿에 비례한 기본 치수 자동 제안
est_diameter = round(6.45 * (carat ** (1/3)), 2)
est_z = round(est_diameter * 0.618, 2)

x = st.sidebar.number_input("x (길이, mm)", min_value=3.50, max_value=11.00, value=est_diameter, step=0.01)
y = st.sidebar.number_input("y (너비, mm)", min_value=3.50, max_value=11.00, value=est_diameter, step=0.01)
z = st.sidebar.number_input("z (깊이, mm)", min_value=2.00, max_value=7.50, value=est_z, step=0.01)

calc_depth = round(2 * z / (x + y) * 100, 1)
depth = st.sidebar.slider("Depth (%)", min_value=50.0, max_value=79.0, value=float(np.clip(calc_depth, 50.0, 79.0)), step=0.1)
table = st.sidebar.slider("Table (%)", min_value=43.0, max_value=79.0, value=57.0, step=0.1)

# 메인 타이틀
st.title("💎 다이아몬드 가격 예측 웹 애플리케이션")
st.markdown("정제된 **53,558건**의 다이아몬드 데이터와 **로그 변환 Ridge 선형회귀 모델**을 기반으로 시장 가치를 예측합니다.")

# 입력 데이터 구성 및 예측
input_df = pd.DataFrame([{
    "carat": carat,
    "log_carat": np.log(carat),
    "depth": depth,
    "table": table,
    "x": x,
    "y": y,
    "z": z,
    "log_volume": np.log(x * y * z),
    "xy_ratio": x / y,
    "cut": cut,
    "color": color,
    "clarity": clarity
}])

predicted_price = float(np.exp(model.predict(input_df[num_cols + cat_cols])[0]))
price_per_carat = predicted_price / carat

# 유사 스펙 실제 거래가 조회
similar_df = df[
    (df["carat"].between(carat - 0.05, carat + 0.05)) &
    (df["cut"] == cut) &
    (df["color"] == color) &
    (df["clarity"] == clarity)
]

# 상단 KPI 카드
col1, col2, col3, col4 = st.columns(4)
col1.metric("예측 시장 가격 (USD)", f"${predicted_price:,.2f}")
col2.metric("캐럿당 단가 (USD/ct)", f"${price_per_carat:,.2f}")
if len(similar_df) > 0:
    avg_sim = similar_df["price"].mean()
    diff_pct = (predicted_price - avg_sim) / avg_sim * 100
    col3.metric("동일 등급 실거래 평균가", f"${avg_sim:,.2f}", f"{diff_pct:+.1f}% (표본 {len(similar_df)}건)")
else:
    col3.metric("동일 등급 실거래 평균가", "유사 표본 없음")
col4.metric("모델 결정계수 (R²)", f"{metrics['r2']:.4f}", f"MAPE {metrics['mape']:.2f}%")

st.markdown("---")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📊 시장 분포 내 위치 분석", "🔍 유사 등급 실거래 데이터", "📈 모델 성능 및 검증"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        sample_df = df.sample(3000, random_state=42)
        fig_scatter = px.scatter(
            sample_df, x="carat", y="price", color="clarity",
            opacity=0.45, title="캐럿(Carat) 대비 가격 분포 및 현재 예측 위치",
            labels={"carat": "Carat (ct)", "price": "Price (USD)", "clarity": "Clarity"}
        )
        fig_scatter.add_trace(go.Scatter(
            x=[carat], y=[predicted_price],
            mode="markers+text",
            marker=dict(size=16, color="red", symbol="star", line=dict(width=2, color="black")),
            text=["예측 위치"], textposition="top center",
            name="현재 입력 다이아몬드"
        ))
        st.plotly_chart(fig_scatter, use_container_width=True)

    with c2:
        # 동일 캐럿대(±0.1ct) 등급별 가격 비교
        band_df = df[df["carat"].between(max(0.2, carat - 0.1), carat + 0.1)]
        if len(band_df) > 10:
            fig_box = px.box(
                band_df, x="clarity", y="price",
                category_orders={"clarity": ["I1", "SI2", "SI1", "VS2", "VS1", "VVS2", "VVS1", "IF"]},
                title=f"유사 중량({max(0.2, carat-0.1):.2f}~{carat+0.1:.2f}ct) 투명도별 가격 분포",
                labels={"clarity": "Clarity", "price": "Price (USD)"}
            )
            fig_box.add_hline(y=predicted_price, line_dash="dash", line_color="red", annotation_text="예측가")
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("해당 중량 구간의 비교 표본이 충분하지 않습니다.")

with tab2:
    st.subheader(f"동일 4C 조건 ({carat-0.05:.2f}~{carat+0.05:.2f}ct / {cut} / {color} / {clarity}) 실거래 내역")
    if len(similar_df) > 0:
        st.dataframe(similar_df.sort_values(by="price").reset_index(drop=True), use_container_width=True)
    else:
        st.warning("정확히 일치하는 4C 표본이 없습니다. 사이드바에서 조건을 조정해 보세요.")

with tab3:
    st.subheader("최종 로그 선형회귀(Ridge) 모델 검증 성능 (Test Set: 10,712건)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("R² Score", f"{metrics['r2']:.4f}")
    m2.metric("RMSE", f"${metrics['rmse']:.2f}")
    m3.metric("MAE", f"${metrics['mae']:.2f}")
    m4.metric("MAPE", f"{metrics['mape']:.2f}%")

    eval_sample = pd.DataFrame({"Actual": y_test, "Predicted": y_pred}).sample(2000, random_state=42)
    fig_eval = px.scatter(
        eval_sample, x="Actual", y="Predicted", opacity=0.4,
        title="실제 가격(Actual) vs 예측 가격(Predicted)",
        labels={"Actual": "실제 가격 (USD)", "Predicted": "예측 가격 (USD)"}
    )
    fig_eval.add_shape(type="line", x0=0, y0=0, x1=19000, y1=19000, line=dict(color="red", dash="dash"))
    st.plotly_chart(fig_eval, use_container_width=True)

