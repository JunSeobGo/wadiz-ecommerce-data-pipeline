from __future__ import annotations

from pathlib import Path
from typing import Any
import html

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TABLE_LABELS = {
    "campaign_kpi": "캠페인 핵심 KPI",
    "campaign_daily_kpi": "일자별 캠페인 KPI",
    "campaign_conversion_kpi": "전환 KPI",
    "comment_nlp_kpi": "댓글/NLP KPI",
    "comment_word_kpi": "댓글 키워드 KPI",
    "campaign_category_benchmark": "카테고리 벤치마크",
    "campaigns": "원천 캠페인",
    "daily_metrics": "원천 일별 지표",
    "comments": "원천 댓글",
    "wishes": "원천 관심등록",
    "fundings": "원천 펀딩",
}
TABLE_ORDER = list(TABLE_LABELS.keys())

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = ["#2563EB", "#0F766E", "#F97316", "#7C3AED", "#DC2626", "#0891B2"]

st.set_page_config(page_title="Wadiz Seller Demo Dashboard", layout="wide")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root{--bg:#f4f7fb;--card:#fff;--border:#dce5f2;--main:#0f172a;--sub:#334155;--muted:#64748b;--red:#e11d48;--blue:#2563eb;--teal:#0f766e;--orange:#ea580c;--shadow:0 10px 28px rgba(15,23,42,.08)}
        html,body,[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--main)}
        .block-container{padding-top:1.2rem;padding-bottom:3rem;max-width:1540px}
        [data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--border)}
        .hero{border:1px solid var(--border);border-radius:26px;padding:26px 30px;margin-bottom:18px;background:linear-gradient(135deg,#fff 0%,#f8fbff 100%);box-shadow:var(--shadow)}
        .hero-top{display:flex;align-items:stretch;justify-content:space-between;gap:22px}.hero-copy{flex:1;min-width:0}
        .hero h1{margin:0;font-size:2.02rem;line-height:1.25;letter-spacing:-.04em;color:var(--main)}.hero p{margin:9px 0 0;color:var(--sub);font-size:.98rem;line-height:1.6}
        .deadline-card{width:172px;border:1px solid #c7d2fe;background:linear-gradient(180deg,#eef2ff 0%,#fff 100%);border-radius:22px;padding:18px 16px;text-align:center;box-shadow:0 8px 20px rgba(37,99,235,.10);display:flex;flex-direction:column;justify-content:center}
        .deadline-label{color:#475569;font-size:.86rem;font-weight:800;margin-bottom:4px}.deadline-value{color:#1d4ed8;font-size:2.15rem;line-height:1.05;font-weight:950;letter-spacing:-.04em}
        .pill-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}.pill{display:inline-flex;border:1px solid #bfdbfe;background:#eff6ff;color:#1d4ed8;padding:6px 10px;border-radius:999px;font-size:.82rem;font-weight:760}
        .kpi-card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:15px 17px 13px;min-height:116px;box-shadow:var(--shadow)}
        .kpi-label{color:var(--muted);font-size:.84rem;font-weight:800;margin-bottom:8px}.kpi-value{color:var(--main);font-size:1.55rem;line-height:1.18;font-weight:920;letter-spacing:-.03em;white-space:nowrap}.kpi-delta{margin-top:8px;font-size:.86rem;font-weight:850}
        .delta-up{color:var(--red)}.delta-down{color:var(--blue)}.delta-flat{color:#64748b}
        .checkpoint-wrap{margin-top:14px;margin-bottom:8px}.checkpoint-card{background:#fff;border:1px solid var(--border);border-radius:18px;padding:15px 17px;min-height:122px;box-shadow:0 6px 18px rgba(15,23,42,.055)}
        .checkpoint-title{color:var(--main);font-size:.94rem;font-weight:900;margin-bottom:8px}.checkpoint-body{color:var(--sub);font-size:.9rem;line-height:1.58}
        .num-red{color:var(--red);font-weight:900}.num-blue{color:var(--blue);font-weight:900}.num-green{color:var(--teal);font-weight:900}.num-orange{color:var(--orange);font-weight:900}
        .section-title{margin-top:14px;margin-bottom:6px;font-size:1.16rem;font-weight:900;color:var(--main);letter-spacing:-.02em}.section-caption{color:var(--muted);font-size:.89rem;margin-bottom:10px}
        div[data-testid="stExpander"]{background:var(--card);border:1px solid var(--border);border-radius:14px;box-shadow:0 5px 18px rgba(15,23,42,.04)}hr{border-color:#e5edf7}
        @media(max-width:900px){.hero-top{flex-direction:column}.deadline-card{width:100%}}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 데이터 유틸
# =============================================================================
def _date(s: pd.Series) -> pd.Series:
    sample = s.dropna().astype(str).str.strip()
    sample = sample[sample != ""]
    if not sample.empty and sample.str.fullmatch(r"\d{8}").mean() > 0.8:
        return pd.to_datetime(s.astype(str).str.strip(), format="%Y%m%d", errors="coerce")
    return pd.to_datetime(s, errors="coerce")


def coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        low = c.lower()
        if low in {
            "dt",
            "date",
            "base_dt",
            "event_date",
            "created_date",
            "when_created",
            "start_datetime",
            "end_datetime",
            "collected_at",
        } or low.endswith(("_date", "_datetime", "_ts")):
            try:
                out[c] = _date(out[c])
            except Exception:
                pass
    return out


@st.cache_data(show_spinner=False)
def load_table(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    return coerce_dates(df)


@st.cache_data(show_spinner=True)
def load_data() -> dict[str, pd.DataFrame]:
    return {name: load_table(name) for name in TABLE_ORDER}


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    if df.empty:
        return None
    cols = list(df.columns)
    lower = {c.lower(): c for c in cols}
    for x in candidates:
        if x in cols:
            return x
        if x.lower() in lower:
            return lower[x.lower()]
    for x in candidates:
        for c in cols:
            if x.lower() in c.lower():
                return c
    return None


def campaign_col(df: pd.DataFrame) -> str | None:
    return find_col(df, ["campaign_id", "campaignId", "project_id", "projectId"])


def date_col(df: pd.DataFrame) -> str | None:
    return find_col(df, ["date", "dt", "base_dt", "event_date", "when_created"])


def first(df: pd.DataFrame, cols: list[str], default: Any = None) -> Any:
    c = find_col(df, cols)
    if c is None or df.empty:
        return default
    v = df[c].dropna()
    return default if v.empty else v.iloc[0]


def num(df: pd.DataFrame, cols: list[str], default: float = 0.0) -> float:
    c = find_col(df, cols)
    if c is None or df.empty:
        return default
    v = pd.to_numeric(df[c], errors="coerce").dropna()
    return default if v.empty else float(v.iloc[0])


def krw(v: float | int) -> str:
    v = 0 if pd.isna(v) else float(v)
    if abs(v) >= 100_000_000:
        return f"{v / 100_000_000:,.1f}억 원"
    if abs(v) >= 10_000:
        return f"{v / 10_000:,.0f}만 원"
    return f"{v:,.0f}원"


def number(v: float | int) -> str:
    return f"{0 if pd.isna(v) else float(v):,.0f}"


def pct(v: float | int) -> str:
    v = 0 if pd.isna(v) else float(v)
    if abs(v) <= 1:
        v *= 100
    return f"{v:.1f}%"


def pp(v: float | int) -> str:
    v = 0 if pd.isna(v) else float(v)
    if abs(v) <= 1:
        v *= 100
    return f"{v:.1f}%p"


def date_text(v: Any) -> str:
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except Exception:
        return "-" if pd.isna(v) else str(v)


def dday(v: Any) -> str:
    try:
        n = int(float(v))
        return f"D-{n}" if n >= 0 else f"D+{abs(n)}"
    except Exception:
        return "D-"


def latest_prev(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    dc = date_col(df)
    if dc is None:
        return df.tail(1).copy(), pd.DataFrame()
    x = df.copy()
    x[dc] = _date(x[dc])
    x = x.dropna(subset=[dc]).sort_values(dc)
    if x.empty:
        return pd.DataFrame(), pd.DataFrame()
    latest_d = x[dc].max()
    latest = x[x[dc] == latest_d].tail(1).copy()
    prev_dates = x[x[dc] < latest_d][dc]
    if prev_dates.empty:
        return latest, pd.DataFrame()
    prev_d = prev_dates.max()
    return latest, x[x[dc] == prev_d].tail(1).copy()


def style_fig(fig: go.Figure, height: int = 400) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font_color="#0f172a",
        title_font_color="#0f172a",
        legend_title_text="",
        margin=dict(l=20, r=20, t=58, b=34),
        height=height,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#edf2f7")
    fig.update_yaxes(showgrid=True, gridcolor="#edf2f7")
    return fig


def filter_campaign(data: dict[str, pd.DataFrame], cid: str | None) -> dict[str, pd.DataFrame]:
    if cid is None:
        return data
    out = {}
    for name, df in data.items():
        c = campaign_col(df)
        out[name] = df if df.empty or c is None else df[df[c].astype(str) == str(cid)].copy()
    return out


# =============================================================================
# 사이드바 / 헤더 / KPI
# =============================================================================
def campaign_label(row: pd.Series) -> str:
    return f"{row.get('title', '캠페인명 없음')} · {row.get('campaign_id', '')} · {row.get('status_simplified', '')} · {dday(row.get('remaining_day', ''))}"


def sidebar(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    st.sidebar.title("메이커 대시보드")
    st.sidebar.caption("메이커와 캠페인을 선택하면 핵심 지표를 한 화면에서 확인합니다.")
    st.sidebar.divider()

    df = data.get("campaign_kpi", pd.DataFrame()).copy()
    if df.empty:
        st.sidebar.error("campaign_kpi.csv를 찾을 수 없습니다.")
        return {"campaign_id": None, "maker": None}

    cc = campaign_col(df)
    if cc is None:
        st.sidebar.error("campaign_id 컬럼을 찾을 수 없습니다.")
        return {"campaign_id": None, "maker": None}
    df = df.rename(columns={cc: "campaign_id"})

    mc = find_col(df, ["maker_name", "corp_name", "nick_name", "nickName", "maker"])
    if mc:
        makers = sorted(df[mc].dropna().astype(str).unique().tolist())
        maker = st.sidebar.selectbox("메이커명", makers, index=0)
        df = df[df[mc].astype(str) == maker].copy()
    else:
        maker = "전체"
        st.sidebar.warning("메이커명 컬럼을 찾지 못했습니다.")

    sort_cols = [c for c in ["status_simplified", "remaining_day", "total_funding_amount"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, ascending=[False, False, False][: len(sort_cols)])

    opts = df.drop_duplicates("campaign_id").reset_index(drop=True)
    opts["label"] = opts.apply(campaign_label, axis=1)
    label = st.sidebar.selectbox("캠페인명", opts["label"].tolist(), index=0)
    row = opts[opts["label"] == label].iloc[0]

    st.sidebar.divider()
    if st.sidebar.button("데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.caption("데이터 새로고침은 파일을 다시 불러오는 작업입니다. \n 파일이 업데이트된 경우 이 버튼을 눌러주세요.")

    return {"campaign_id": str(row["campaign_id"]), "maker": maker}


def render_header(selected: dict[str, Any], data: dict[str, pd.DataFrame]) -> None:
    src = data.get("campaign_kpi", pd.DataFrame()).head(1)
    title = first(src, ["title", "campaign_title", "project_title"], "캠페인명 없음")
    maker = selected.get("maker") or first(src, ["maker_name", "corp_name", "nick_name", "nickName"], "-")
    category = first(src, ["category_name", "category"], "-")
    biz = first(src, ["biz_model", "product_type"], "-")
    status = first(src, ["status_simplified", "status"], "-")
    remain = first(src, ["remaining_day", "remain_day"], "-")
    cid = selected.get("campaign_id") or first(src, ["campaign_id", "campaignId"], "-")
    end = date_text(first(src, ["end_datetime", "end_date"], None))

    st.markdown(
        f"""
        <div class="hero"><div class="hero-top"><div class="hero-copy">
        <h1>{html.escape(str(title))}</h1>
        <p>펀딩 성과, 일별 증감, 관심 행동, 댓글 감성, 카테고리 벤치마크를 한 화면에서 확인합니다.</p>
        <div class="pill-row">
        <span class="pill">메이커: {html.escape(str(maker))}</span><span class="pill">캠페인 ID: {html.escape(str(cid))}</span>
        <span class="pill">카테고리: {html.escape(str(category))}</span><span class="pill">유형: {html.escape(str(biz))}</span>
        <span class="pill">진행상태: {html.escape(str(status))}</span><span class="pill">종료일: {end}</span>
        </div></div><div class="deadline-card"><div class="deadline-label">마감일</div><div class="deadline-value">{dday(remain)}</div></div></div></div>
        """,
        unsafe_allow_html=True,
    )


def snapshot(data: dict[str, pd.DataFrame]) -> dict[str, float]:
    camp = data.get("campaign_kpi", pd.DataFrame())
    daily = data.get("campaign_daily_kpi", pd.DataFrame())
    comments = data.get("comment_nlp_kpi", pd.DataFrame())
    latest, prev = latest_prev(daily)

    amount = num(latest, ["total_funding_amount"], num(camp, ["total_funding_amount", "total_backed_amount"]))
    ach = num(latest, ["achievement_rate"], num(camp, ["achievement_rate"]))
    part = num(latest, ["participation_cnt", "supporter_count"], num(camp, ["participation_cnt", "supporter_count"]))
    sign = num(latest, ["signature_cnt"], num(camp, ["signature_cnt"]))
    views = num(latest, ["detail_views", "detail_view_cnt"], 0)
    conv = num(latest, ["daily_conversion_rate"], 0)
    comm = num(latest, ["comment_cnt", "comment_count"], num(camp, ["comment_cnt", "comment_count"]))

    p_amount = num(prev, ["total_funding_amount"], amount)
    p_ach = num(prev, ["achievement_rate"], ach)
    p_part = num(prev, ["participation_cnt", "supporter_count"], part)
    p_sign = num(prev, ["signature_cnt"], sign)
    p_views = num(prev, ["detail_views", "detail_view_cnt"], views)
    p_conv = num(prev, ["daily_conversion_rate"], conv)
    p_comm = num(prev, ["comment_cnt", "comment_count"], comm)

    if comments.empty:
        pos_rate = num(camp, ["positive_rate"], 0)
        neg_rate = num(camp, ["negative_rate"], 0)
    else:
        pos = pd.to_numeric(comments.get("positive_comment_cnt", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
        neg = pd.to_numeric(comments.get("negative_comment_cnt", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
        total = pd.to_numeric(comments.get("comment_cnt", comments.get("comment_count", pd.Series(dtype=float))), errors="coerce").fillna(0).sum()
        pos_rate = pos / total if total else 0
        neg_rate = neg / total if total else 0

    return {
        "amount": amount,
        "amount_delta": amount - p_amount,
        "achievement": ach,
        "achievement_delta": ach - p_ach,
        "participation": part,
        "participation_delta": part - p_part,
        "signature": sign,
        "signature_delta": sign - p_sign,
        "daily_views": views,
        "daily_views_delta": views - p_views,
        "daily_conversion": conv,
        "daily_conversion_delta": conv - p_conv,
        "comment_cnt": comm,
        "comment_delta": comm - p_comm,
        "positive_rate": pos_rate,
        "negative_rate": neg_rate,
    }


def delta_html(delta: float, kind: str) -> str:
    text = krw(abs(delta)) if kind == "krw" else pp(abs(delta)) if kind in {"pct", "rate"} else number(abs(delta))
    if delta > 0:
        return f'<span class="delta-up">▲ +{text}</span>'
    if delta < 0:
        return f'<span class="delta-down">▼ -{text}</span>'
    return '<span class="delta-flat">- 0</span>'


def card(label: str, value: str, delta: float, kind: str) -> str:
    return f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-delta">{delta_html(delta, kind)} <span class="delta-flat">전일 대비</span></div></div>'


def render_kpis(data: dict[str, pd.DataFrame]) -> None:
    s = snapshot(data)
    items = [
        ("총 펀딩금액", krw(s["amount"]), s["amount_delta"], "krw"),
        ("달성률", pct(s["achievement"]), s["achievement_delta"], "pct"),
        ("참여자 수", number(s["participation"]), s["participation_delta"], "number"),
        ("지지서명 수", number(s["signature"]), s["signature_delta"], "number"),
        ("일일 상세조회", number(s["daily_views"]), s["daily_views_delta"], "number"),
        ("일일 전환율", pct(s["daily_conversion"]), s["daily_conversion_delta"], "rate"),
    ]
    for col, item in zip(st.columns(6), items):
        with col:
            st.markdown(card(*item), unsafe_allow_html=True)


def render_checkpoints(data: dict[str, pd.DataFrame]) -> None:
    st.markdown('<div class="checkpoint-wrap"><div class="section-title">운영 체크포인트</div>', unsafe_allow_html=True)
    s = snapshot(data)
    camp = data.get("campaign_kpi", pd.DataFrame())
    gap = max(num(camp, ["target_amount"], 0) - s["amount"], 0)
    conv_cls = "num-red" if s["daily_conversion_delta"] > 0 else "num-blue" if s["daily_conversion_delta"] < 0 else "num-green"
    neg_cls = "num-red" if s["negative_rate"] >= 0.15 else "num-blue"
    fund_cls = "num-red" if s["amount_delta"] > 0 else "num-blue"

    cards = [
        ("펀딩 모멘텀", f"전일 펀딩 증감액은 <span class='{fund_cls}'>{krw(s['amount_delta'])}</span>입니다. 유입이 몰린 채널과 댓글 반응을 함께 확인하세요."),
        ("전환 흐름", f"일일 전환율은 <span class='{conv_cls}'>{pct(s['daily_conversion'])}</span> 수준입니다. 상단 혜택, 배송 조건, 가격 설득 문구를 점검하세요."),
        ("댓글 리스크", f"부정 댓글 비율은 <span class='{neg_cls}'>{pct(s['negative_rate'])}</span> 수준입니다. 품질, 배송, 가격 관련 문의를 우선 모니터링하세요."),
        ("목표 달성 관리", f"목표금액까지 남은 금액은 <span class='num-orange'>{krw(gap)}</span>입니다. 마감일이 가까울수록 리마인드 메시지와 인기 리워드 노출을 강화하세요."),
    ]
    for col, (title, body) in zip(st.columns(4), cards):
        with col:
            st.markdown(f'<div class="checkpoint-card"><div class="checkpoint-title">{title}</div><div class="checkpoint-body">{body}</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# 차트 영역
# =============================================================================
def render_performance(data: dict[str, pd.DataFrame]) -> None:
    st.markdown('<div class="section-title">1. 캠페인 성과 추이</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">누적 펀딩금액과 일별 증감액을 함께 확인합니다.</div>', unsafe_allow_html=True)
    df = data.get("campaign_daily_kpi", pd.DataFrame()).copy()
    if df.empty:
        st.info("일자별 캠페인 KPI 데이터가 없습니다.")
        return
    dc = date_col(df)
    if dc is None:
        st.info("날짜 컬럼을 찾지 못했습니다.")
        return
    df[dc] = _date(df[dc])
    df = df.dropna(subset=[dc]).sort_values(dc)
    if "funding_amount_dod" not in df.columns and "total_funding_amount" in df.columns:
        df["funding_amount_dod"] = pd.to_numeric(df["total_funding_amount"], errors="coerce").diff().fillna(0)

    left, right = st.columns([1.18, 0.82])
    with left:
        if {"total_funding_amount", "funding_amount_dod"}.issubset(df.columns):
            fig = go.Figure()
            fig.add_bar(x=df[dc], y=df["funding_amount_dod"], name="일별 펀딩 증감액", marker_color="#93C5FD", yaxis="y2")
            fig.add_scatter(x=df[dc], y=df["total_funding_amount"], mode="lines+markers", name="누적 펀딩금액", line=dict(color="#2563EB", width=3))
            fig.update_layout(title="누적 펀딩금액 + 일별 증감액", yaxis=dict(title="누적 펀딩금액"), yaxis2=dict(title="일별 증감액", overlaying="y", side="right", showgrid=False))
            st.plotly_chart(style_fig(fig, 410), use_container_width=True)
        else:
            st.info("펀딩금액 추이를 그릴 컬럼이 부족합니다.")
    with right:
        metric_cols = [c for c in ["detail_views", "participation_dod", "wish_dod", "comment_dod"] if c in df.columns]
        if metric_cols:
            label = {"detail_views": "상세조회", "participation_dod": "신규 참여", "wish_dod": "관심등록", "comment_dod": "신규 댓글"}
            long = df[[dc] + metric_cols].rename(columns=label).melt(id_vars=[dc], var_name="지표", value_name="값")
            fig = px.line(long, x=dc, y="값", color="지표", markers=True, title="일별 행동 지표 증감")
            st.plotly_chart(style_fig(fig, 410), use_container_width=True)
        else:
            st.info("행동 지표 추이를 그릴 컬럼이 부족합니다.")


def render_conversion(data: dict[str, pd.DataFrame]) -> None:
    st.markdown('<div class="section-title">2. 관심 → 참여 전환 흐름</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">상세조회, 관심등록, 참여 단계에서 어느 구간의 전환이 약한지 확인합니다.</div>', unsafe_allow_html=True)
    daily = data.get("campaign_daily_kpi", pd.DataFrame())
    camp = data.get("campaign_kpi", pd.DataFrame())
    latest, _ = latest_prev(daily)
    src = latest if not latest.empty else camp.head(1)

    # 지지서명 단계는 제외한다.
    funnel = pd.DataFrame(
        [
            ("상세조회", num(src, ["detail_view_cnt", "detail_views", "total_detail_views"])),
            ("관심등록", num(src, ["wish_cnt", "wish_count", "wish_adds", "total_wish_cnt", "wish_dod"])),
            ("참여", num(src, ["participation_cnt", "supporter_count", "participation_dod"])),
        ],
        columns=["stage", "value"],
    )
    funnel = funnel[funnel["value"] > 0]

    left, right = st.columns([0.92, 1.08])
    with left:
        if len(funnel) >= 2:
            fig = go.Figure(
                go.Funnel(
                    y=funnel["stage"],
                    x=funnel["value"],
                    textinfo="value+percent initial",
                    marker={"color": ["#2563EB", "#0F766E", "#DC2626"][: len(funnel)]},
                )
            )
            fig.update_layout(title="전환 퍼널")
            st.plotly_chart(style_fig(fig, 410), use_container_width=True)
        else:
            st.info("퍼널 생성을 위한 데이터가 부족합니다.")
    with right:
        df = daily.copy()
        dc = date_col(df)
        if dc:
            df[dc] = _date(df[dc])
            df = df.dropna(subset=[dc]).sort_values(dc)
            rate_cols = [c for c in ["daily_conversion_rate", "cumulative_conversion_rate"] if c in df.columns]
            if rate_cols:
                rate = df[[dc] + rate_cols].copy()
                for c in rate_cols:
                    rate[c] = pd.to_numeric(rate[c], errors="coerce")
                    if rate[c].dropna().abs().max() <= 1:
                        rate[c] *= 100
                long = rate.rename(columns={"daily_conversion_rate": "일일 전환율", "cumulative_conversion_rate": "누적 전환율"}).melt(id_vars=[dc], var_name="지표", value_name="전환율")
                fig = px.line(long, x=dc, y="전환율", color="지표", markers=True, title="전환율 추이")
                fig.update_yaxes(ticksuffix="%")
                st.plotly_chart(style_fig(fig, 410), use_container_width=True)
            else:
                st.info("전환율 컬럼을 찾지 못했습니다.")
        else:
            st.info("전환율 추이를 그릴 날짜 컬럼을 찾지 못했습니다.")

    s = snapshot(data)
    arppu = s["amount"] / s["participation"] if s["participation"] else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("조회 → 참여", pct(num(camp, ["view_to_participation_rate"], 0)))
    c2.metric("관심 → 참여", pct(num(camp, ["wish_to_participation_rate"], 0)))
    c3.metric("참여자 1명당 펀딩", krw(arppu))
    c4.metric("최신 일일 전환율", pct(s["daily_conversion"]))




def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """#RRGGBB 색상값을 RGB 튜플로 변환한다."""
    x = str(hex_color).strip().lstrip("#")
    if len(x) != 6:
        return 15, 23, 42
    try:
        return int(x[0:2], 16), int(x[2:4], 16), int(x[4:6], 16)
    except ValueError:
        return 15, 23, 42


def sentiment_words(words: pd.DataFrame, target: str) -> pd.DataFrame:
    """긍정/부정 키워드만 분리한다."""
    if words.empty or "sentiment" not in words.columns:
        return pd.DataFrame()
    s = words["sentiment"].astype(str).str.lower().str.strip()
    if target == "positive":
        mask = s.isin(["positive", "pos", "긍정"]) | s.str.contains("positive|긍정", regex=True, na=False)
    else:
        mask = s.isin(["negative", "neg", "부정"]) | s.str.contains("negative|부정", regex=True, na=False)
    return words[mask].copy()


def wordcloud_component_html(words: pd.DataFrame, title: str, color_hex: str) -> str:
    """
    Streamlit components.html()로 렌더링할 댓글 키워드 클라우드 HTML.

    기존 st.markdown 방식은 환경에 따라 HTML 코드가 그대로 노출될 수 있어 iframe 컴포넌트 방식으로 변경했다.
    - 빈도 높은 단어: 더 크게, 더 진하게, 더 진한 배경으로 표시
    - 빈도 낮은 단어: 더 작고 연하게 표시
    - 너무 낮은 빈도: 제외
    - flex-wrap 카드형 배치로 단어 겹침 방지
    """
    r, g, b = hex_to_rgb(color_hex)

    def empty_body(message: str) -> str:
        return f"""
        <div class="wc-card">
            <div class="wc-title">{html.escape(title)}</div>
            <div class="wc-empty">{html.escape(message)}</div>
        </div>
        """

    body = empty_body("표시할 키워드가 없습니다.")

    if not words.empty and "word" in words.columns and "count" in words.columns:
        df = words.copy()
        df["word"] = df["word"].astype(str).str.strip()
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0)
        df = df[(df["word"] != "") & (df["count"] > 0)]

        if not df.empty:
            df = (
                df.groupby("word", as_index=False)["count"]
                .sum()
                .sort_values("count", ascending=False)
                .reset_index(drop=True)
            )

            max_count = float(df["count"].max())
            # 최대 빈도의 18% 미만이거나 2회 미만인 키워드는 운영 판단에 노이즈가 커 제외한다.
            min_count = max(2.0, np.ceil(max_count * 0.18))
            df = df[df["count"] >= min_count].head(28).reset_index(drop=True)

            if df.empty:
                body = empty_body("반복적으로 등장한 키워드가 아직 충분하지 않습니다.")
            else:
                min_c = float(df["count"].min())
                max_c = float(df["count"].max())
                denom = max(max_c - min_c, 1.0)

                # 큰 키워드가 한쪽에 몰리지 않도록 순서를 섞는다.
                first = df.iloc[::2].copy()
                second = df.iloc[1::2].copy()
                df = pd.concat([second.iloc[::-1], first], ignore_index=True)

                tokens: list[str] = []
                for _, row in df.iterrows():
                    word = str(row["word"])
                    count = float(row["count"])
                    weight = (count - min_c) / denom

                    font_size = 13 + weight * 15
                    font_weight = int(520 + weight * 330)
                    opacity = 0.38 + weight * 0.60
                    bg_alpha = 0.035 + weight * 0.115
                    border_alpha = 0.08 + weight * 0.20
                    shadow_alpha = 0.025 + weight * 0.060

                    tokens.append(
                        f"""
                        <span class="wc-token" title="빈도 {int(count):,}" style="
                            --size:{font_size:.1f}px;
                            --weight:{font_weight};
                            --color:rgba({r},{g},{b},{opacity:.3f});
                            --bg:rgba({r},{g},{b},{bg_alpha:.3f});
                            --border:rgba({r},{g},{b},{border_alpha:.3f});
                            --shadow:rgba({r},{g},{b},{shadow_alpha:.3f});
                        ">{html.escape(word)}</span>
                        """
                    )

                body = f"""
                <div class="wc-card">
                    <div class="wc-title">{html.escape(title)}</div>
                    <div class="wc-wrap">{''.join(tokens)}</div>
                </div>
                """

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8" />
        <style>
            * {{ box-sizing:border-box; }}
            html, body {{
                margin:0;
                padding:0;
                background:transparent;
                font-family:Pretendard, "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", Arial, sans-serif;
                -webkit-font-smoothing:antialiased;
                text-rendering:optimizeLegibility;
            }}
            .wc-card {{
                height:360px;
                width:100%;
                background:#ffffff;
                border:1px solid #e2e8f0;
                border-radius:18px;
                padding:18px 20px;
                box-shadow:0 6px 18px rgba(15,23,42,0.045);
                overflow:hidden;
            }}
            .wc-title {{
                font-size:16px;
                line-height:1.25;
                font-weight:900;
                color:#0f172a;
                letter-spacing:-0.03em;
                margin-bottom:14px;
            }}
            .wc-wrap {{
                height:286px;
                width:100%;
                display:flex;
                flex-wrap:wrap;
                align-content:center;
                justify-content:center;
                gap:10px 11px;
                overflow:hidden;
                padding:4px 2px;
            }}
            .wc-token {{
                display:inline-flex;
                align-items:center;
                justify-content:center;
                max-width:100%;
                padding:7px 11px 8px;
                border-radius:999px;
                border:1px solid var(--border);
                background:var(--bg);
                color:var(--color);
                font-size:var(--size);
                font-weight:var(--weight);
                line-height:1.08;
                letter-spacing:-0.045em;
                white-space:nowrap;
                box-shadow:0 6px 16px var(--shadow);
            }}
            .wc-empty {{
                height:286px;
                display:flex;
                align-items:center;
                justify-content:center;
                color:#94a3b8;
                font-size:14px;
                font-weight:700;
                text-align:center;
            }}
        </style>
    </head>
    <body>{body}</body>
    </html>
    """


def render_wordcloud(words: pd.DataFrame, title: str, color_hex: str) -> None:
    """HTML이 텍스트로 노출되지 않도록 Streamlit iframe 컴포넌트로 렌더링한다."""
    components.html(
        wordcloud_component_html(words, title, color_hex),
        height=372,
        scrolling=False,
    )


def render_comments(data: dict[str, pd.DataFrame]) -> None:
    st.markdown('<div class="section-title">3. 댓글 / NLP 반응</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">긍정·부정 키워드와 감성 비중을 함께 보며 댓글 대응 우선순위를 잡습니다.</div>',
        unsafe_allow_html=True,
    )

    comments = data.get("comment_nlp_kpi", pd.DataFrame())
    words = data.get("comment_word_kpi", pd.DataFrame())

    if comments.empty:
        st.info("댓글/NLP 데이터가 없습니다.")
        return

    left, center, right = st.columns([1, 0.82, 1])

    with left:
        render_wordcloud(
            sentiment_words(words, "positive"),
            "긍정 워드클라우드",
            "#e11d48",
        )

    with center:
        pos = pd.to_numeric(
            comments.get("positive_comment_cnt", pd.Series(dtype=float)),
            errors="coerce",
        ).fillna(0).sum()

        neu = pd.to_numeric(
            comments.get("neutral_comment_cnt", pd.Series(dtype=float)),
            errors="coerce",
        ).fillna(0).sum()

        neg = pd.to_numeric(
            comments.get("negative_comment_cnt", pd.Series(dtype=float)),
            errors="coerce",
        ).fillna(0).sum()

        fig = px.pie(
            pd.DataFrame(
                {
                    "감성": ["긍정", "중립", "부정"],
                    "댓글 수": [pos, neu, neg],
                }
            ),
            names="감성",
            values="댓글 수",
            title="댓글 감성 비중",
            hole=0.46,
        )
        st.plotly_chart(style_fig(fig, 360), use_container_width=True)

    with right:
        render_wordcloud(
            sentiment_words(words, "negative"),
            "부정 워드클라우드",
            "#2563eb",
        )

    dc = date_col(comments)
    if dc:
        df = comments.copy()
        df[dc] = _date(df[dc])
        df = df.dropna(subset=[dc]).sort_values(dc)

        cols = [
            c
            for c in [
                "positive_comment_cnt",
                "neutral_comment_cnt",
                "negative_comment_cnt",
            ]
            if c in df.columns
        ]

        if cols:
            label = {
                "positive_comment_cnt": "긍정",
                "neutral_comment_cnt": "중립",
                "negative_comment_cnt": "부정",
            }

            long = (
                df[[dc] + cols]
                .rename(columns=label)
                .melt(id_vars=[dc], var_name="감성", value_name="댓글 수")
            )

            fig = px.line(
                long,
                x=dc,
                y="댓글 수",
                color="감성",
                markers=True,
                title="일자별 댓글 감성 추이",
            )
            st.plotly_chart(style_fig(fig, 360), use_container_width=True)


def render_benchmark(data: dict[str, pd.DataFrame], raw: dict[str, pd.DataFrame]) -> None:
    st.markdown('<div class="section-title">4. 카테고리 내 성과 비교</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">카테고리 평균을 100으로 둔 성과지수로 비교합니다.</div>', unsafe_allow_html=True)
    selected = data.get("campaign_kpi", pd.DataFrame())
    all_df = raw.get("campaign_kpi", pd.DataFrame())
    bench = raw.get("campaign_category_benchmark", pd.DataFrame())
    if selected.empty or all_df.empty:
        st.info("카테고리 비교에 필요한 데이터가 없습니다.")
        return

    cat_col = find_col(all_df, ["category_name", "category"])
    selected_cat_col = find_col(selected, ["category_name", "category"])
    category = first(selected, [selected_cat_col] if selected_cat_col else ["category_name", "category"], None)
    if cat_col is None or category is None:
        st.info("카테고리 컬럼을 찾지 못했습니다.")
        return

    same = all_df[all_df[cat_col].astype(str) == str(category)].copy()
    bench_row = pd.DataFrame()
    bench_cat = find_col(bench, ["category_name", "category"])
    if not bench.empty and bench_cat:
        bench_row = bench[bench[bench_cat].astype(str) == str(category)].head(1).copy()

    configs = [
        ("총 펀딩금액", "total_funding_amount", "avg_funding_amount", "krw", True),
        ("달성률", "achievement_rate", "avg_achievement_rate", "pct", True),
        ("참여자 수", "participation_cnt", "avg_participation_cnt", "num", True),
        ("지지서명 수", "signature_cnt", "avg_signature_cnt", "num", True),
        ("긍정 댓글 비율", "positive_rate", "avg_positive_rate", "pct", True),
        ("부정 댓글 비율", "negative_rate", "avg_negative_rate", "pct", False),
    ]

    rows = []
    for label, s_col, b_col, kind, higher in configs:
        sc = find_col(selected, [s_col])
        if sc is None:
            continue
        sv = num(selected, [sc], 0)
        bv = np.nan
        bc = find_col(bench_row, [b_col]) if not bench_row.empty else None
        if bc:
            bv = num(bench_row, [bc], np.nan)
        if pd.isna(bv) or bv == 0:
            ac = find_col(same, [s_col])
            if ac:
                bv = pd.to_numeric(same[ac], errors="coerce").dropna().mean()
        if pd.isna(bv) or bv == 0:
            continue
        idx = (sv / bv * 100) if higher else (bv / sv * 100 if sv else 160)
        fmt = krw if kind == "krw" else pct if kind == "pct" else number
        rows.append(
            {
                "지표": label,
                "성과지수": idx,
                "라벨": f"{idx:.0f}",
                "선택 캠페인": fmt(sv),
                "카테고리 평균": fmt(bv),
                "평균 대비": f"{idx - 100:+.1f}%",
                "해석": "높을수록 좋음" if higher else "낮을수록 좋음",
            }
        )

    comp = pd.DataFrame(rows)
    if comp.empty:
        st.info("비교 가능한 숫자 지표가 없습니다.")
        return
    comp = comp.sort_values("성과지수")
    fig = px.bar(
        comp,
        x="성과지수",
        y="지표",
        orientation="h",
        text="라벨",
        title=f"선택 캠페인 vs {category} 카테고리 평균 · 평균=100",
        hover_data={
            "성과지수": ":.1f",
            "선택 캠페인": True,
            "카테고리 평균": True,
            "평균 대비": True,
            "해석": True,
            "라벨": False,
        },
    )
    fig.add_vline(x=100, line_width=2, line_dash="dash", line_color="#64748b")
    fig.update_traces(textposition="outside", cliponaxis=False, marker_color="#2563EB")
    fig.update_xaxes(range=[0, max(160, float(comp["성과지수"].max()) * 1.25)])
    fig.update_layout(xaxis_title="카테고리 평균=100 기준 성과지수", yaxis_title="", showlegend=False)
    st.plotly_chart(style_fig(fig, 430), use_container_width=True)

    with st.expander("성과 비교 원본 값", expanded=False):
        st.dataframe(
            comp.sort_values("성과지수", ascending=False)[["지표", "선택 캠페인", "카테고리 평균", "성과지수", "평균 대비", "해석"]],
            use_container_width=True,
            hide_index=True,
        )
    with st.expander("동일 카테고리 캠페인 목록", expanded=False):
        show = ["campaign_id", "title", "maker_name", cat_col, "total_funding_amount", "achievement_rate", "participation_cnt", "signature_cnt"]
        st.dataframe(same[[c for c in show if c in same.columns]].head(200), use_container_width=True, hide_index=True)


def render_raw(data: dict[str, pd.DataFrame], raw: dict[str, pd.DataFrame]) -> None:
    with st.expander("선택 캠페인 데이터 확인", expanded=False):
        available = [t for t in TABLE_ORDER if t in data and not data[t].empty]
        if available:
            table = st.selectbox("확인할 데이터", available, format_func=lambda x: f"{x} · {TABLE_LABELS.get(x, x)}")
            st.dataframe(data[table].head(500), use_container_width=True, hide_index=True)
            st.download_button(
                f"{table}.csv 다운로드",
                data[table].to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"{table}_selected_campaign.csv",
                mime="text/csv",
                use_container_width=True,
            )
    with st.expander("데이터 로딩 상태", expanded=False):
        rows = [
            {
                "table": t,
                "name": TABLE_LABELS.get(t, t),
                "rows": len(raw.get(t, pd.DataFrame())),
                "columns": len(raw.get(t, pd.DataFrame()).columns) if not raw.get(t, pd.DataFrame()).empty else 0,
                "status": "OK" if not raw.get(t, pd.DataFrame()).empty else "EMPTY",
            }
            for t in TABLE_ORDER
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    inject_css()
    raw = load_data()
    selected = sidebar(raw)
    cid = selected.get("campaign_id")
    if cid is None:
        st.warning("캠페인을 선택할 수 없습니다. data/campaign_kpi.csv를 확인하세요.")
        st.stop()

    data = filter_campaign(raw, cid)
    if data.get("campaign_kpi", pd.DataFrame()).empty:
        st.warning("선택한 캠페인의 KPI 데이터가 없습니다.")
        st.stop()

    render_header(selected, data)
    render_kpis(data)
    render_checkpoints(data)

    st.divider()
    render_performance(data)

    st.divider()
    render_conversion(data)

    st.divider()
    render_comments(data)

    st.divider()
    render_benchmark(data, raw)

    render_raw(data, raw)


if __name__ == "__main__":
    main()