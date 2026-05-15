# coding: utf-8
"""
부동산 실거래가 분석 로직. RTMS raw parquet → 가공된 DataFrame + 통계.
평수 구간은 공급평수 추정(전용평수 × 1.33) 기준 — 시장에서 부르는 "34평형" 같은 통념과 일치.
"""
import os
import pandas as pd
import numpy as np

SQM_TO_PYEONG = 0.3025      # 1㎡ = 0.3025평
SUPPLY_RATIO = 1.33         # 공급면적/전용면적 평균 비율 (계단식 신축 1.25~1.32, 복도식 1.40~1.50)

# 공급평수 기준 구간 (시장 통념: 84㎡=34평형=국평)
SIZE_BINS = [0, 20, 30, 40, 50, 1e9]
SIZE_LABELS = ['20평 이하', '20평대', '30평대', '40평대', '50평+']


def _to_int(series):
    """'600,000' → 600000 (만원 단위 그대로)"""
    return (series.astype(str)
            .str.replace(',', '', regex=False)
            .str.strip()
            .replace('', '0')
            .astype(float).astype('Int64'))


def load_sales(parquet_path: str) -> pd.DataFrame:
    """매매 parquet → 가공"""
    df = pd.read_parquet(parquet_path)
    if df.empty:
        return df
    # 해제 거래 제외 (cdealType='O' 또는 cdealDay 비어있지 않음)
    if 'cdealType' in df.columns:
        df = df[df['cdealType'].astype(str).str.strip() != 'O']
    out = pd.DataFrame()
    out['거래일'] = pd.to_datetime(
        df['dealYear'].astype(str) + '-' +
        df['dealMonth'].astype(str).str.zfill(2) + '-' +
        df['dealDay'].astype(str).str.zfill(2),
        errors='coerce'
    )
    out['아파트'] = df['aptNm'].str.strip()
    out['동'] = df['umdNm'].str.strip()
    out['전용면적'] = df['excluUseAr'].astype(float)
    out['전용평수'] = (out['전용면적'] * SQM_TO_PYEONG).round(1)
    out['공급평수'] = (out['전용평수'] * SUPPLY_RATIO).round(1)
    out['평수구간'] = pd.cut(out['공급평수'], bins=SIZE_BINS, labels=SIZE_LABELS, right=False)
    out['층'] = pd.to_numeric(df['floor'], errors='coerce').astype('Int64')
    out['건축년도'] = pd.to_numeric(df['buildYear'], errors='coerce').astype('Int64')
    out['거래금액'] = _to_int(df['dealAmount'])  # 만원
    out['거래금액_억'] = (out['거래금액'] / 10000).round(2)
    out['평당가'] = (out['거래금액'] / out['공급평수']).round(0).astype('Int64')  # 만원/공급평
    out['거래유형'] = df.get('dealingGbn', '').fillna('').astype(str)
    out = out.dropna(subset=['거래일', '거래금액']).reset_index(drop=True)
    out = out[out['거래금액'] > 0]
    return out


def load_rents(parquet_path: str) -> pd.DataFrame:
    """전월세 parquet → 가공"""
    df = pd.read_parquet(parquet_path)
    if df.empty:
        return df
    out = pd.DataFrame()
    out['거래일'] = pd.to_datetime(
        df['dealYear'].astype(str) + '-' +
        df['dealMonth'].astype(str).str.zfill(2) + '-' +
        df['dealDay'].astype(str).str.zfill(2),
        errors='coerce'
    )
    out['아파트'] = df['aptNm'].str.strip()
    out['동'] = df['umdNm'].str.strip()
    out['전용면적'] = df['excluUseAr'].astype(float)
    out['전용평수'] = (out['전용면적'] * SQM_TO_PYEONG).round(1)
    out['공급평수'] = (out['전용평수'] * SUPPLY_RATIO).round(1)
    out['평수구간'] = pd.cut(out['공급평수'], bins=SIZE_BINS, labels=SIZE_LABELS, right=False)
    out['층'] = pd.to_numeric(df['floor'], errors='coerce').astype('Int64')
    out['건축년도'] = pd.to_numeric(df['buildYear'], errors='coerce').astype('Int64')
    out['보증금'] = _to_int(df['deposit'])      # 만원
    out['월세'] = _to_int(df['monthlyRent'])    # 만원
    out['임대유형'] = np.where(out['월세'] > 0, '월세', '전세')
    out['보증금_억'] = (out['보증금'] / 10000).round(2)
    out['갱신유형'] = df.get('contractType', '').fillna('').astype(str)
    out = out.dropna(subset=['거래일']).reset_index(drop=True)
    out = out[out['보증금'] > 0]
    return out


def apply_filters(df: pd.DataFrame, dong=None, sizes=None, start=None, end=None):
    """필터링 — 동, 평수 구간, 기간"""
    out = df
    if dong and dong != '전체':
        out = out[out['동'] == dong]
    if sizes:
        out = out[out['평수구간'].isin(sizes)]
    if start:
        out = out[out['거래일'] >= pd.Timestamp(start)]
    if end:
        out = out[out['거래일'] <= pd.Timestamp(end)]
    return out


def monthly_stats(df: pd.DataFrame, value_col='거래금액', group_by='평수구간'):
    """월별 × 그룹별 평균"""
    if df.empty or value_col not in df.columns:
        return pd.DataFrame()
    out = df.copy()
    out['년월'] = out['거래일'].dt.to_period('M').dt.to_timestamp()
    g = out.groupby(['년월', group_by], observed=True)[value_col].agg(['mean', 'median', 'count'])
    return g.reset_index()


def size_summary(df: pd.DataFrame, value_col='거래금액'):
    """평수구간별 평균/중위/최소/최대/거래량"""
    if df.empty:
        return pd.DataFrame()
    g = df.groupby('평수구간', observed=True)[value_col].agg(
        평균=('mean'), 중위=('median'), 최저=('min'), 최고=('max'), 거래수=('count')
    )
    return g.reset_index()


def dong_summary(df: pd.DataFrame, value_col='거래금액', top_n=15):
    """동별 평균 (거래수 많은 순)"""
    if df.empty or '동' not in df.columns:
        return pd.DataFrame()
    g = df.groupby('동', observed=True).agg(
        평균=(value_col, 'mean'),
        중위=(value_col, 'median'),
        거래수=(value_col, 'count'),
        평당가평균=('평당가' if '평당가' in df.columns else value_col, 'mean'),
    ).reset_index().sort_values('거래수', ascending=False).head(top_n)
    return g
