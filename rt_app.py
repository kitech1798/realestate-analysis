# coding: utf-8
"""
부동산 실거래가 분석 — Streamlit 인터페이스 (다크 테크 톤).
탭 2개: ① 지역 분석 ② 아파트 비교
실행: streamlit run "rt_app.py"
"""
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rt_logic import (
    load_sales, load_rents, apply_filters,
    monthly_stats, size_summary, dong_summary,
    SIZE_LABELS,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '데이터')
SALE_DIR = os.path.join(DATA_DIR, '거래', '매매')
RENT_DIR = os.path.join(DATA_DIR, '거래', '전월세')
CODE_PATH = os.path.join(DATA_DIR, '시군구코드.csv')

# 딥블랙 + 바이올렛 톤 (FuseDash 스타일)
BG = '#0b0b14'              # 거의 흑색, 미세한 보라 기운
SURFACE = '#13131f'         # 사이드/탭 표면
CARD = '#181826'            # 카드 표면
CARD_HOVER = '#1f1f30'
BORDER = '#2a2a40'          # 보라톤 보더
BORDER_STRONG = '#3a3a5a'
TEXT = '#f5f5fa'
TEXT_MUTED = '#9ca3af'
TEXT_DIM = '#6b7280'

# 액센트
VIOLET = '#a855f7'
VIOLET_DARK = '#8b5cf6'
INDIGO = '#6366f1'
PINK = '#ec4899'
CYAN = '#06b6d4'
AMBER = '#f59e0b'
EMERALD = '#10b981'

# 그라데이션
GRAD_PURPLE_PINK = 'linear-gradient(135deg, #a855f7 0%, #ec4899 100%)'
GRAD_INDIGO_VIOLET = 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)'

SIZE_COLORS = {
    '20평 이하': '#64748b',
    '20평대': '#6366f1',     # indigo
    '30평대': '#a855f7',     # violet (국평 — 메인 톤)
    '40평대': '#ec4899',     # pink
    '50평+': '#f59e0b',      # amber
}

# 아파트 비교 — 보라/핑크 그라데이션 시퀀스
APT_PALETTE = ['#a855f7', '#ec4899', '#6366f1', '#06b6d4', '#f59e0b', '#10b981']

st.set_page_config(page_title='부동산 실거래가 분석', layout='wide', page_icon='🏠')

st.markdown(f"""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, button, input, select, textarea {{
    font-family: 'Pretendard Variable', Pretendard, 'Inter', -apple-system, BlinkMacSystemFont,
        'SF Pro Display', 'Segoe UI', system-ui, sans-serif !important;
    font-feature-settings: 'tnum' 1, 'ss01' 1;
    -webkit-font-smoothing: antialiased;
}}

.stApp {{
    background:
        radial-gradient(1200px 600px at 90% -10%, rgba(168,85,247,0.08), transparent 60%),
        radial-gradient(900px 500px at -10% 110%, rgba(99,102,241,0.06), transparent 60%),
        {BG};
    color: {TEXT};
}}
.block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1500px; }}

h1, h2, h3, h4 {{
    color: {TEXT};
    letter-spacing: -0.02em;
    font-weight: 700;
}}
h1 {{ font-size: 28px; }}
h2 {{ font-size: 20px; }}
h3 {{ font-size: 16px; }}
h4 {{ font-size: 13px; color: {TEXT_MUTED}; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; }}

/* 메트릭 카드 — 그라데이션 보더 + 살짝 글로우 */
[data-testid="stMetric"] {{
    background: linear-gradient({CARD}, {CARD}) padding-box,
                linear-gradient(135deg, rgba(168,85,247,0.45), rgba(236,72,153,0.25) 50%, rgba(99,102,241,0.35)) border-box;
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px -12px rgba(168,85,247,0.25);
}}
[data-testid="stMetricLabel"] {{ color: {TEXT_MUTED} !important; font-size: 11.5px !important;
    font-weight: 500 !important; letter-spacing: 0.04em; text-transform: uppercase; }}
[data-testid="stMetricValue"] {{ color: {TEXT} !important; font-size: 26px !important;
    font-weight: 700 !important; letter-spacing: -0.02em; }}
[data-testid="stMetricDelta"] {{ font-size: 12px !important; }}

[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
hr {{ border-color: {BORDER}; opacity: 0.6; }}

.stExpander {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
[data-testid="stDataFrame"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}

/* 탭 */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{
    background: transparent; border: none; border-radius: 10px 10px 0 0;
    padding: 10px 22px; color: {TEXT_MUTED}; font-weight: 500;
    transition: color .15s ease;
}}
.stTabs [data-baseweb="tab"]:hover {{ color: {TEXT}; }}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(180deg, rgba(168,85,247,0.12), rgba(168,85,247,0));
    color: {TEXT}; font-weight: 600;
    box-shadow: inset 0 -2px 0 {VIOLET};
}}

/* 입력 위젯 */
.stSelectbox > div > div, .stMultiSelect > div > div, .stTextInput input, .stNumberInput input {{
    background: {CARD} !important; border: 1px solid {BORDER} !important;
    border-radius: 10px !important; color: {TEXT} !important;
}}
.stSelectbox > div > div:hover, .stMultiSelect > div > div:hover {{
    border-color: {BORDER_STRONG} !important;
}}
.stRadio [role="radiogroup"] label {{ color: {TEXT_MUTED}; }}
.stRadio [role="radiogroup"] label:has(input:checked) {{ color: {VIOLET}; font-weight: 600; }}

/* 버튼 */
.stButton > button {{
    background: linear-gradient(135deg, {VIOLET} 0%, {PINK} 100%);
    color: white; border: none; border-radius: 10px;
    font-weight: 600; letter-spacing: -0.01em;
    box-shadow: 0 4px 14px -4px rgba(168,85,247,0.5);
    transition: transform .12s ease, box-shadow .12s ease;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 18px -4px rgba(168,85,247,0.65);
}}
.stButton > button:active {{ transform: translateY(0); }}

/* 슬라이더 */
.stSlider [role="slider"] {{ background: {VIOLET} !important; }}

/* 데이터프레임 헤더 */
[data-testid="stDataFrame"] thead th {{
    background: {SURFACE} !important; color: {TEXT_MUTED} !important;
    font-weight: 600 !important; font-size: 11px !important;
    text-transform: uppercase; letter-spacing: 0.04em;
}}

.compare-item {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 12px 16px; margin: 6px 0; }}

/* 인포 메시지 */
.stAlert {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}

/* 코드/숫자 모노 */
code, pre {{ font-family: 'JetBrains Mono', ui-monospace, monospace; }}

/* ── Top 10 리더보드 ───────────────────────── */
.tt-board {{ display: flex; flex-direction: column; margin: -4px -4px 0; }}
.tt-head {{
    display: grid;
    grid-template-columns: 44px 1fr 120px 92px;
    align-items: center;
    padding: 4px 10px 8px;
    color: {TEXT_DIM}; font-size: 10.5px; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase;
    border-bottom: 1px solid {BORDER};
}}
.tt-head .r {{ text-align: right; }}
.tt-row {{
    display: grid;
    grid-template-columns: 44px 1fr 120px 92px;
    align-items: center;
    padding: 9px 10px;
    border-bottom: 1px solid rgba(58,58,90,0.25);
    transition: background .15s ease;
}}
.tt-row:last-child {{ border-bottom: none; }}
.tt-row:hover {{ background: rgba(168,85,247,0.05); }}
.tt-row.top1 {{ background: linear-gradient(90deg, rgba(245,158,11,0.10), transparent 55%); }}
.tt-row.top2 {{ background: linear-gradient(90deg, rgba(203,213,225,0.07), transparent 55%); }}
.tt-row.top3 {{ background: linear-gradient(90deg, rgba(217,119,6,0.09), transparent 55%); }}
.tt-row.top1:hover {{ background: linear-gradient(90deg, rgba(245,158,11,0.14), rgba(168,85,247,0.05) 55%); }}
.tt-row.top2:hover {{ background: linear-gradient(90deg, rgba(203,213,225,0.10), rgba(168,85,247,0.05) 55%); }}
.tt-row.top3:hover {{ background: linear-gradient(90deg, rgba(217,119,6,0.13), rgba(168,85,247,0.05) 55%); }}

.tt-medal {{
    width: 28px; height: 28px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: #1b1b28;
    font-family: 'Inter', sans-serif;
    box-shadow: 0 2px 8px -2px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.35);
}}
.tt-medal.gold   {{ background: linear-gradient(135deg, #fde68a 0%, #f59e0b 60%, #b45309 100%); }}
.tt-medal.silver {{ background: linear-gradient(135deg, #f1f5f9 0%, #cbd5e1 55%, #64748b 100%); }}
.tt-medal.bronze {{ background: linear-gradient(135deg, #fdba74 0%, #d97706 55%, #7c2d12 100%); color: #fff7ed; }}
.tt-rank {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px;
    font-family: 'JetBrains Mono', monospace; font-size: 13px;
    font-weight: 500; color: {TEXT_DIM};
}}

.tt-name {{ overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
    padding-right: 12px; font-size: 13.5px; color: {TEXT}; font-weight: 500; }}
.tt-region {{ color: {TEXT_MUTED}; font-size: 11.5px; font-weight: 400; margin-right: 6px; }}

.tt-value {{ text-align: right; font-family: 'JetBrains Mono', monospace;
    font-size: 15px; font-weight: 700; color: {TEXT}; letter-spacing: -0.01em; }}
.tt-value .unit {{ font-size: 10.5px; color: {TEXT_MUTED}; font-weight: 500;
    margin-left: 3px; font-family: 'Pretendard Variable', sans-serif; }}
.tt-count {{ text-align: right; font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px; color: {TEXT_MUTED}; }}
.tt-count .unit {{ font-size: 10px; color: {TEXT_DIM}; margin-left: 2px;
    font-family: 'Pretendard Variable', sans-serif; }}

/* Top 10 expander 내부 패딩 살짝 줄이기 */
.stExpander details > div:nth-child(2) {{ padding-top: 4px !important; }}

/* ── Maker 배지 (우측 상단 각인) ───────────────────── */
.maker-badge {{
    display: inline-flex; align-items: center; gap: 9px;
    padding: 7px 14px 7px 11px; border-radius: 999px;
    background: linear-gradient({CARD}, {CARD}) padding-box,
                linear-gradient(135deg, rgba(168,85,247,0.55), rgba(236,72,153,0.35) 50%, rgba(99,102,241,0.5)) border-box;
    border: 1px solid transparent;
    text-decoration: none !important;
    box-shadow: 0 6px 18px -10px rgba(168,85,247,0.55),
                inset 0 1px 0 rgba(255,255,255,0.05);
    transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    white-space: nowrap;
}}
.maker-badge:hover {{
    transform: translateY(-1px);
    box-shadow: 0 10px 24px -10px rgba(168,85,247,0.75),
                inset 0 1px 0 rgba(255,255,255,0.07);
}}
.maker-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: linear-gradient(135deg, {VIOLET} 0%, {PINK} 100%);
    box-shadow: 0 0 10px rgba(168,85,247,0.9), 0 0 2px rgba(236,72,153,0.8);
    animation: maker-pulse 2.6s ease-in-out infinite;
    flex-shrink: 0;
}}
@keyframes maker-pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50%      {{ opacity: 0.45; transform: scale(0.78); }}
}}
.maker-label {{
    font-size: 10px; color: {TEXT_DIM}; font-weight: 600;
    letter-spacing: 0.14em; text-transform: uppercase;
    font-family: 'Inter', sans-serif;
}}
.maker-name {{
    font-size: 12.5px; font-weight: 800; letter-spacing: -0.01em;
    background: linear-gradient(135deg, #f5f5fa 0%, #d8b4fe 45%, #f9a8d4 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_codes():
    return pd.read_csv(CODE_PATH, encoding='utf-8-sig', dtype={'시군구코드': str})


@st.cache_data(ttl=3600)
def load_district(lawd_cd: str, kind: str):
    """매매 or 전월세 데이터 로드"""
    if kind == '매매':
        path = os.path.join(SALE_DIR, f'{lawd_cd}.parquet')
        return load_sales(path) if os.path.exists(path) else pd.DataFrame()
    else:
        path = os.path.join(RENT_DIR, f'{lawd_cd}.parquet')
        return load_rents(path) if os.path.exists(path) else pd.DataFrame()


@st.cache_data(ttl=3600)
def list_apartments(lawd_cd: str, kind: str):
    """해당 시군구의 아파트명 리스트 (거래 빈도 내림차순)"""
    df = load_district(lawd_cd, kind)
    if df.empty:
        return []
    return df['아파트'].value_counts().index.tolist()


@st.cache_data(ttl=3600, show_spinner='전국 매매 데이터 집계 중...')
def compute_national_top10():
    """전국 매매 최근 1년 기준 Top 10 동·Top 10 아파트 (평균 거래금액 내림차순).
    동 거래수 ≥ 30, 아파트 거래수 ≥ 5 임계치로 1~2건 이상치 배제."""
    codes = load_codes()
    cutoff = pd.Timestamp(datetime.now() - timedelta(days=365))
    rows = []
    for _, r in codes.iterrows():
        df = load_district(r['시군구코드'], '매매')
        if df.empty:
            continue
        df = df[df['거래일'] >= cutoff]
        if df.empty:
            continue
        df = df.assign(시도=r['시도'], 시군구=r['시군구'])
        rows.append(df[['시도', '시군구', '동', '아파트', '거래금액']])
    if not rows:
        return pd.DataFrame(), pd.DataFrame()

    all_df = pd.concat(rows, ignore_index=True)

    dong = (all_df.groupby(['시도', '시군구', '동'], observed=True)
            .agg(평균=('거래금액', 'mean'), 거래수=('거래금액', 'count'))
            .reset_index())
    dong = (dong[dong['거래수'] >= 30]
            .sort_values('평균', ascending=False).head(10).reset_index(drop=True))
    dong.insert(0, '순위', range(1, len(dong) + 1))
    dong['지역'] = dong['시도'] + ' ' + dong['시군구'] + ' · ' + dong['동']
    dong['평균 (억)'] = (dong['평균'] / 10000).round(2)
    dong_view = dong[['순위', '지역', '평균 (억)', '거래수']]

    apt = (all_df.groupby(['시도', '시군구', '동', '아파트'], observed=True)
           .agg(평균=('거래금액', 'mean'), 거래수=('거래금액', 'count'))
           .reset_index())
    apt = (apt[apt['거래수'] >= 5]
           .sort_values('평균', ascending=False).head(10).reset_index(drop=True))
    apt.insert(0, '순위', range(1, len(apt) + 1))
    apt['단지'] = (apt['시도'] + ' ' + apt['시군구'] + ' ' + apt['동']
                   + ' · ' + apt['아파트'])
    apt['평균 (억)'] = (apt['평균'] / 10000).round(2)
    apt_view = apt[['순위', '단지', '평균 (억)', '거래수']]

    return dong_view, apt_view


def render_top10(df: pd.DataFrame, name_col: str, leaf_label: str):
    """Top 10 리더보드 — 메달 뱃지 + 압축 행 HTML 렌더링."""
    if df.empty:
        st.caption('데이터 없음')
        return
    import html as _html
    rows = []
    for _, r in df.iterrows():
        rank = int(r['순위'])
        full = str(r[name_col])
        if ' · ' in full:
            region, leaf = full.rsplit(' · ', 1)
        else:
            region, leaf = '', full
        avg = f"{r['평균 (억)']:.2f}"
        cnt = f"{int(r['거래수']):,}"

        if rank == 1:
            badge = '<span class="tt-medal gold">1</span>'
            row_cls = 'tt-row top1'
        elif rank == 2:
            badge = '<span class="tt-medal silver">2</span>'
            row_cls = 'tt-row top2'
        elif rank == 3:
            badge = '<span class="tt-medal bronze">3</span>'
            row_cls = 'tt-row top3'
        else:
            badge = f'<span class="tt-rank">{rank}</span>'
            row_cls = 'tt-row'

        region_html = (f'<span class="tt-region">{_html.escape(region)}</span>'
                       if region else '')
        rows.append(
            f'<div class="{row_cls}">'
            f'<div>{badge}</div>'
            f'<div class="tt-name">{region_html}{_html.escape(leaf)}</div>'
            f'<div class="tt-value">{avg}<span class="unit">억</span></div>'
            f'<div class="tt-count">{cnt}<span class="unit">건</span></div>'
            f'</div>'
        )
    head = (
        '<div class="tt-head">'
        '<div>순위</div>'
        f'<div>{_html.escape(leaf_label)}</div>'
        '<div class="r">평균</div>'
        '<div class="r">거래수</div>'
        '</div>'
    )
    st.markdown('<div class="tt-board">' + head + ''.join(rows) + '</div>',
                unsafe_allow_html=True)


def fig_layout(fig, height=380):
    fig.update_layout(
        height=height, margin=dict(l=12, r=12, t=36, b=12),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=TEXT, size=12,
                  family="'Pretendard Variable', Pretendard, 'Inter', system-ui, sans-serif"),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
                    bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_MUTED, size=11),
                    itemsizing='constant'),
        title=dict(font=dict(color=TEXT, size=13, weight=600), x=0.01),
        hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER, font=dict(color=TEXT, size=12)),
        colorway=APT_PALETTE,
    )
    fig.update_xaxes(gridcolor='rgba(58,58,90,0.35)', linecolor=BORDER,
                     color=TEXT_MUTED, zerolinecolor='rgba(58,58,90,0.5)',
                     showgrid=True, gridwidth=1)
    fig.update_yaxes(gridcolor='rgba(58,58,90,0.35)', linecolor=BORDER,
                     color=TEXT_MUTED, zerolinecolor='rgba(58,58,90,0.5)',
                     showgrid=True, gridwidth=1)
    return fig


# ───────────────────── 탭 1: 지역 분석 ─────────────────────
def render_region(codes):
    dong_top, _ = compute_national_top10()
    if not dong_top.empty:
        with st.expander('🏆 전국 동 Top 10 — 최근 1년 매매 평균 거래금액 (거래수 30건↑)',
                         expanded=True):
            render_top10(dong_top, name_col='지역', leaf_label='지역')

    st.markdown('#### 필터')
    f1, f2, f3, f4 = st.columns([1.2, 1.8, 1.5, 2])
    sido = f1.selectbox('시/도', sorted(codes['시도'].unique()), key='r_sido')
    sub = codes[codes['시도'] == sido]
    sigungu = f2.selectbox('시/군/구', sorted(sub['시군구'].tolist()), key='r_sgg')
    lawd_cd = sub[sub['시군구'] == sigungu]['시군구코드'].iloc[0]
    kind = f3.radio('거래 유형', ['매매', '전세', '월세'], horizontal=True, key='r_kind')
    period_label = f4.radio('기간', ['최근 3개월', '최근 6개월', '최근 1년', '최근 3년', '전체'],
                            index=2, horizontal=True, key='r_period')

    period_days = {'최근 3개월': 90, '최근 6개월': 180,
                   '최근 1년': 365, '최근 3년': 365 * 3, '전체': 99999}[period_label]
    today = datetime.now()
    start_date = today - timedelta(days=period_days)

    raw_kind = '매매' if kind == '매매' else '전월세'
    df_all = load_district(lawd_cd, raw_kind)
    if df_all.empty:
        st.error(f'{sido} {sigungu} 데이터가 없습니다. 다운로드를 먼저 실행하세요.')
        return

    if kind == '전세':
        df_all = df_all[df_all['임대유형'] == '전세']
    elif kind == '월세':
        df_all = df_all[df_all['임대유형'] == '월세']

    f5, f6 = st.columns([1.5, 3])
    dong_options = ['전체'] + sorted(df_all['동'].dropna().unique().tolist())
    dong = f5.selectbox('동(읍면동)', dong_options, key='r_dong')
    sizes = f6.multiselect('평수 구간', SIZE_LABELS, default=SIZE_LABELS, key='r_sizes')

    df = apply_filters(df_all, dong=dong, sizes=sizes,
                       start=start_date if period_days < 99999 else None)

    st.subheader(f"{sido} {sigungu}" + (f" · {dong}" if dong != '전체' else '') + f" · {kind}")
    st.caption(f"{period_label} · 기준일 {today.strftime('%Y-%m-%d')}")

    if df.empty:
        st.warning('선택한 조건의 거래가 없습니다.')
        return

    value_col = '거래금액' if kind == '매매' else '보증금'
    h1, h2, h3, h4 = st.columns(4)
    h1.metric('거래 건수', f"{len(df):,}건")
    h2.metric(f'평균 {value_col}', f"{df[value_col].mean()/10000:.2f}억")
    h3.metric(f'중위 {value_col}', f"{df[value_col].median()/10000:.2f}억")
    if kind == '매매':
        h4.metric('평균 평당가', f"{df['평당가'].mean():,.0f}만원/평")
    elif kind == '월세':
        h4.metric('평균 월세', f"{df['월세'].mean():,.0f}만원")
    else:
        h4.metric('평균 전용면적', f"{df['전용면적'].mean():.1f}㎡")

    # 월별 추이
    st.markdown('### 월별 평균가 추이 (평수구간별)')
    ms = monthly_stats(df, value_col=value_col, group_by='평수구간')
    if not ms.empty:
        ms['평균_억'] = (ms['mean'] / 10000).round(2)
        fig = px.line(ms, x='년월', y='평균_억', color='평수구간',
                      color_discrete_map=SIZE_COLORS,
                      labels={'평균_억': f'평균 {value_col} (억원)', '년월': ''},
                      markers=True)
        fig.update_traces(line=dict(width=2.2), marker=dict(size=7))
        st.plotly_chart(fig_layout(fig, 400), use_container_width=True)

    # 면적-가격 산점도
    st.markdown('### 면적-가격 분포')
    scatter_df = df.copy()
    scatter_df['금액_억'] = scatter_df[value_col] / 10000
    fig2 = px.scatter(
        scatter_df, x='공급평수', y='금액_억', color='평수구간',
        color_discrete_map=SIZE_COLORS,
        hover_data=['아파트', '동', '거래일', '층', '건축년도'],
        labels={'금액_억': f'{value_col} (억원)', '공급평수': '공급면적(평, 추정)'},
        opacity=0.6,
    )
    fig2.update_traces(marker=dict(size=7, line=dict(width=0)))
    st.plotly_chart(fig_layout(fig2, 440), use_container_width=True)

    # 동별 비교
    if dong == '전체':
        st.markdown('### 동(읍면동)별 평균 비교 — 거래 많은 상위 15개')
        ds = dong_summary(df, value_col=value_col, top_n=15)
        if not ds.empty:
            ds['평균_억'] = (ds['평균'] / 10000).round(2)
            ds = ds.sort_values('평균_억', ascending=True)
            fig3 = go.Figure(go.Bar(
                x=ds['평균_억'], y=ds['동'], orientation='h',
                marker=dict(color=ds['평균_억'],
                            colorscale=[[0, INDIGO], [0.5, VIOLET], [1, PINK]]),
                text=ds['평균_억'].apply(lambda v: f'{v}억'),
                textposition='outside',
                hovertemplate='%{y}<br>평균 %{x:.2f}억<br>거래 %{customdata}건<extra></extra>',
                customdata=ds['거래수'],
            ))
            fig3.update_layout(xaxis_title=f'평균 {value_col} (억원)', yaxis_title='')
            st.plotly_chart(fig_layout(fig3, max(340, 30 * len(ds))), use_container_width=True)

    # 평수구간 요약
    st.markdown('### 평수구간별 통계')
    ss = size_summary(df, value_col=value_col)
    if not ss.empty:
        disp = ss.copy()
        for c in ['평균', '중위', '최저', '최고']:
            disp[c] = (disp[c] / 10000).round(2)
        disp.columns = ['평수구간', '평균(억)', '중위(억)', '최저(억)', '최고(억)', '거래수']
        st.dataframe(disp, hide_index=True, use_container_width=True)

    # 최근 거래
    st.markdown('### 최근 거래 (상위 30건)')
    recent = df.sort_values('거래일', ascending=False).head(30).copy()
    recent['거래일'] = recent['거래일'].dt.strftime('%Y-%m-%d')
    if kind == '매매':
        cols = ['거래일', '아파트', '동', '전용면적', '공급평수', '평수구간',
                '거래금액_억', '평당가', '층', '건축년도', '거래유형']
    elif kind == '월세':
        cols = ['거래일', '아파트', '동', '전용면적', '공급평수', '평수구간',
                '보증금_억', '월세', '층', '건축년도', '갱신유형']
    else:
        cols = ['거래일', '아파트', '동', '전용면적', '공급평수', '평수구간',
                '보증금_억', '층', '건축년도', '갱신유형']
    cols = [c for c in cols if c in recent.columns]
    st.dataframe(recent[cols], hide_index=True, use_container_width=True)


# ───────────────────── 탭 2: 아파트 비교 ─────────────────────
def render_compare(codes):
    _, apt_top = compute_national_top10()
    if not apt_top.empty:
        with st.expander('🏆 전국 아파트 Top 10 — 최근 1년 매매 평균 거래금액 (거래수 5건↑)',
                         expanded=True):
            render_top10(apt_top, name_col='단지', leaf_label='단지')

    st.markdown('#### 비교 설정')
    c1, c2, c3 = st.columns([1.5, 2.5, 1.5])
    kind = c1.radio('거래 유형', ['매매', '전세'], horizontal=True, key='c_kind')
    size_mode = c2.radio('평형 기준',
                         ['국평 (전용 78~85㎡)', '중대형 (전용 100~135㎡)', '전체', '직접 입력'],
                         horizontal=False, key='c_size_mode')
    period_yr = c3.selectbox('기간', [3, 5, 10, 15],
                             index=2, format_func=lambda x: f'최근 {x}년', key='c_period')

    if size_mode == '국평 (전용 78~85㎡)':
        size_min, size_max = 78, 85
    elif size_mode == '중대형 (전용 100~135㎡)':
        size_min, size_max = 100, 135
    elif size_mode == '전체':
        size_min, size_max = 0, 1e9
    else:
        size_min, size_max = st.slider('전용면적 범위 (㎡)', 30, 250, (75, 95), step=5,
                                       key='c_size_range')

    metric_mode = st.radio('지표', ['평균 거래가 (억원)', '평당가 (만원/평)'],
                           horizontal=True, key='c_metric')

    st.divider()
    st.markdown('#### 비교 아파트 추가 (최대 6개)')

    if 'compare_list' not in st.session_state:
        st.session_state.compare_list = []

    a1, a2, a3 = st.columns([2, 3.5, 1])
    codes_sorted = codes.sort_values(['시도', '시군구']).reset_index(drop=True)
    sigungu_options = [f"{r['시도']} {r['시군구']}" for _, r in codes_sorted.iterrows()]
    sgg_choice = a1.selectbox('시군구', sigungu_options, key='c_sgg')
    sgg_row = codes_sorted.iloc[sigungu_options.index(sgg_choice)]
    lawd_cd = sgg_row['시군구코드']

    raw_kind = '매매' if kind == '매매' else '전월세'
    apt_list = list_apartments(lawd_cd, raw_kind)
    if apt_list:
        apt_choice = a2.selectbox(f'아파트명 ({len(apt_list):,}개)', apt_list, key='c_apt')
    else:
        a2.selectbox('아파트명', ['(이 지역 데이터 없음 — 다운로드 필요)'], key='c_apt')
        apt_choice = None

    a3.markdown('<br>', unsafe_allow_html=True)
    if a3.button('➕ 추가', use_container_width=True, key='c_add'):
        if apt_choice and len(st.session_state.compare_list) < 6:
            item = {'sgg': sgg_choice, 'apt': apt_choice, 'lawd_cd': lawd_cd}
            if item not in st.session_state.compare_list:
                st.session_state.compare_list.append(item)

    # 현재 비교 목록
    if st.session_state.compare_list:
        st.markdown('#### 현재 비교 목록')
        for i, item in enumerate(st.session_state.compare_list):
            color = APT_PALETTE[i % len(APT_PALETTE)]
            cols = st.columns([0.3, 7, 1])
            cols[0].markdown(
                f'<div style="width:14px;height:14px;background:{color};'
                f'border-radius:3px;margin-top:8px;"></div>',
                unsafe_allow_html=True,
            )
            cols[1].markdown(f"**{item['sgg']}** — {item['apt']}")
            if cols[2].button('🗑️', key=f'c_del_{i}', use_container_width=True):
                st.session_state.compare_list.pop(i)
                st.rerun()

        st.divider()
        # 비교 차트
        today = datetime.now()
        start_date = today - timedelta(days=365 * period_yr)
        value_col = '거래금액' if kind == '매매' else '보증금'

        all_monthly = []
        for i, item in enumerate(st.session_state.compare_list):
            df = load_district(item['lawd_cd'], raw_kind)
            if df.empty:
                continue
            if kind == '전세':
                df = df[df['임대유형'] == '전세']
            df = df[df['아파트'] == item['apt']]
            df = df[df['전용면적'].between(size_min, size_max)]
            df = df[df['거래일'] >= pd.Timestamp(start_date)]
            if df.empty:
                continue
            df = df.copy()
            df['년월'] = df['거래일'].dt.to_period('M').dt.to_timestamp()
            agg = df.groupby('년월').agg(
                평균금액=(value_col, 'mean'),
                평당가=('평당가' if kind == '매매' else value_col, 'mean'),
                거래수=(value_col, 'count'),
            ).reset_index()
            agg['금액_억'] = (agg['평균금액'] / 10000).round(2)
            if kind != '매매':
                agg['평당가'] = (agg['평균금액'] / (df.groupby('년월')['공급평수'].mean().values)).round(0)
            agg['라벨'] = f"{item['sgg']} {item['apt']}"
            agg['색번호'] = i
            # 대표 평형 (가장 거래 많은 전용면적)
            top_size = df['전용면적'].round(1).mode().iloc[0]
            top_supply = round(top_size * 0.3025 * 1.33, 1)
            agg.attrs['대표전용'] = top_size
            agg.attrs['대표공급평'] = top_supply
            all_monthly.append(agg)

        if not all_monthly:
            st.warning('선택한 조건의 거래가 없습니다. 평형 범위·기간을 조정하거나 다른 아파트 시도.')
            return

        big = pd.concat(all_monthly, ignore_index=True)

        st.markdown(f'### 시세 비교 — {size_mode} · 최근 {period_yr}년')

        y_col = '금액_억' if '거래가' in metric_mode else '평당가'
        y_label = '평균 거래가 (억원)' if y_col == '금액_억' else '평균 평당가 (만원/평)'

        fig = go.Figure()
        for i, monthly_df in enumerate(all_monthly):
            color = APT_PALETTE[i % len(APT_PALETTE)]
            fig.add_trace(go.Scatter(
                x=monthly_df['년월'], y=monthly_df[y_col],
                mode='lines+markers',
                name=monthly_df['라벨'].iloc[0],
                line=dict(color=color, width=2.5),
                marker=dict(size=7),
                customdata=monthly_df['거래수'],
                hovertemplate='%{x|%Y-%m}<br>'
                              + ('%{y:.2f}억' if y_col == '금액_억' else '%{y:,.0f}만원/평')
                              + '<br>거래 %{customdata}건<extra>'
                              + monthly_df['라벨'].iloc[0]
                              + '</extra>',
            ))
        fig.update_layout(yaxis_title=y_label, xaxis_title='')
        st.plotly_chart(fig_layout(fig, 480), use_container_width=True)

        # 요약 표
        st.markdown('#### 비교 요약')
        rows = []
        for monthly_df in all_monthly:
            if len(monthly_df) < 1:
                continue
            first = monthly_df.iloc[0]
            last = monthly_df.iloc[-1]
            pct = ((last[y_col] / first[y_col] - 1) * 100) if first[y_col] else 0
            전용 = monthly_df.attrs.get('대표전용', None)
            공급평 = monthly_df.attrs.get('대표공급평', None)
            평형 = f"{전용:.1f}㎡ ({공급평:.0f}평형)" if 전용 is not None else ''
            rows.append({
                '아파트': monthly_df['라벨'].iloc[0],
                '평형': 평형,
                '거래월수': len(monthly_df),
                '총 거래수': int(monthly_df['거래수'].sum()),
                '첫 거래월': first['년월'].strftime('%Y-%m'),
                '첫 평균': round(first[y_col], 2),
                '최근 거래월': last['년월'].strftime('%Y-%m'),
                '최근 평균': round(last[y_col], 2),
                '변화율(%)': round(pct, 1),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info('위에서 아파트를 추가하면 비교 차트가 표시됩니다. 최대 6개.')


# ───────────────────── 메인 ─────────────────────
def main():
    st.markdown(
        f"""
        <div style='display:flex;align-items:center;justify-content:space-between;
              gap:16px;margin-bottom:4px;flex-wrap:wrap;'>
          <div style='display:flex;align-items:center;gap:14px;'>
            <div style='width:38px;height:38px;border-radius:11px;
                  background:linear-gradient(135deg,{VIOLET} 0%, {PINK} 100%);
                  display:flex;align-items:center;justify-content:center;
                  box-shadow:0 8px 22px -8px rgba(168,85,247,0.6);
                  font-size:20px;'>🏠</div>
            <h1 style='margin:0;font-size:30px;font-weight:800;letter-spacing:-0.03em;
                  background:linear-gradient(135deg,#f5f5fa 0%, #c4b5fd 60%, #ec4899 100%);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  background-clip:text;'>부동산 실거래가 분석</h1>
          </div>
          <a href='https://blog.naver.com/metauniv' target='_blank' rel='noopener'
             class='maker-badge' title='돈돈정보통 블로그로 이동'>
            <span class='maker-dot'></span>
            <span class='maker-label'>Made by</span>
            <span class='maker-name'>돈돈정보통</span>
          </a>
        </div>
        <p style='color:{TEXT_MUTED};margin:0 0 18px 52px;font-size:12.5px;
              letter-spacing:0.01em;'>
          국토교통부 실거래가 · 서울 25 + 경기 44 + 충남 2 시군구 · 10년치 ·
          <span style='color:{VIOLET_DARK};'>해제·취소 제외</span> · 공급평수 추정(전용 × 1.33)
        </p>
        """,
        unsafe_allow_html=True,
    )

    codes = load_codes()

    tab1, tab2 = st.tabs(['📊 지역 분석', '🏘️ 아파트 비교'])
    with tab1:
        render_region(codes)
    with tab2:
        render_compare(codes)

    st.markdown(
        f"<p style='color:{TEXT_MUTED};font-size:11.5px;margin-top:24px;'>"
        f"국토교통부 실거래가 공개 API 기반. 평수구간은 공급평수 추정(전용평수 × 1.33). "
        f"단지별 실제 공급/전용 비율은 1.25~1.50으로 ±1평 오차 가능. "
        f"해제·취소 거래는 자동 제외. 분석은 참고용, 거래 판단 책임은 본인에게.</p>",
        unsafe_allow_html=True,
    )


if __name__ == '__main__':
    main()
