import io
import pandas as pd
import requests
import streamlit as st


@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"

    # User-Agent 헤더 추가하여 HTTP 403 / HTTPError 방지
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/110.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    # UTF-8 문자열 데이터를 pandas 읽기용 버퍼로 변환
    df = pd.read_csv(io.StringIO(response.text))

    df["openDt"] = pd.to_datetime(
        df["openDt"].astype(str), format="%Y%m%d", errors="coerce"
    )
    df["genre"] = df["genre"].fillna("미정").astype(str).str.split("|").str[0]
    df["nation"] = df["nation"].fillna("기타")

    return df
