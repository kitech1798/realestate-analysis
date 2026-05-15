# coding: utf-8
"""
국토교통부 실거래가 다운로드 — 아파트 매매 + 전월세.
매월 1회 실행: 신규 월만 증분으로 받음.
저장: 데이터/거래/매매/{시군구코드}.parquet · 데이터/거래/전월세/{시군구코드}.parquet

사용:
  python download_data.py            # 증분 (받지 않은 월만)
  python download_data.py --full     # 전체 재다운로드 (2020-01부터)
  python download_data.py --start 2024-01  # 특정 시점부터
"""
import os
import sys
import time
import argparse
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '데이터')
TRADE_DIR = os.path.join(DATA_DIR, '거래')
SALE_DIR = os.path.join(TRADE_DIR, '매매')
RENT_DIR = os.path.join(TRADE_DIR, '전월세')
CODE_PATH = os.path.join(DATA_DIR, '시군구코드.csv')
os.makedirs(SALE_DIR, exist_ok=True)
os.makedirs(RENT_DIR, exist_ok=True)


def load_api_key():
    """secrets.toml 또는 환경변수에서 키 로드"""
    secrets_path = os.path.join(SCRIPT_DIR, '.streamlit', 'secrets.toml')
    if os.path.exists(secrets_path):
        with open(secrets_path, encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('MOLIT_API_KEY'):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    if os.environ.get('MOLIT_API_KEY'):
        return os.environ['MOLIT_API_KEY']
    raise RuntimeError('MOLIT_API_KEY를 .streamlit/secrets.toml 에 설정하세요.')


API_KEY = load_api_key()

ENDPOINTS = {
    '매매': ('https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade', SALE_DIR),
    '전월세': ('https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent', RENT_DIR),
}


def call_api(url, lawd_cd, deal_ymd, page_no=1, num_rows=1000, retries=3):
    """V2 API: URL 직접 조립 + 네트워크 에러 시 재시도"""
    full = (f'{url}?serviceKey={API_KEY}&LAWD_CD={lawd_cd}&DEAL_YMD={deal_ymd}'
            f'&pageNo={page_no}&numOfRows={num_rows}')
    last_err = ''
    for attempt in range(retries):
        try:
            r = requests.get(full, timeout=25)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            last_err = f'Network: {str(e)[:80]}'
            time.sleep(1.5 * (attempt + 1))
            continue
        if not r.ok:
            return None, f'HTTP {r.status_code}'
        if '<resultCode>00' not in r.text and '<resultCode>000' not in r.text:
            return None, r.text[:200]
        try:
            root = ET.fromstring(r.text)
            items = root.findall('.//item')
            if not items:
                return [], None
            rows = []
            for it in items:
                row = {child.tag: (child.text or '').strip() for child in it}
                rows.append(row)
            total = root.findtext('.//totalCount', '0')
            return rows, int(total) if total.isdigit() else len(rows)
        except ET.ParseError as e:
            return None, f'XML 파싱 실패: {e}'
    return None, last_err


def fetch_month(category, url, lawd_cd, deal_ymd):
    """한 달치 데이터 (페이지네이션 자동)"""
    all_rows = []
    rows, total = call_api(url, lawd_cd, deal_ymd, 1, 1000)
    if rows is None:
        return None, total  # total = error message
    all_rows.extend(rows)
    if isinstance(total, int) and total > 1000:
        pages = (total + 999) // 1000
        for p in range(2, pages + 1):
            more, _ = call_api(url, lawd_cd, deal_ymd, p, 1000)
            if more:
                all_rows.extend(more)
            time.sleep(0.1)
    return all_rows, None


def existing_months(category_dir, lawd_cd):
    """이미 받은 월 set 반환 (YYYYMM)"""
    path = os.path.join(category_dir, f'{lawd_cd}.parquet')
    if not os.path.exists(path):
        return set()
    try:
        df = pd.read_parquet(path)
        if df.empty or 'dealYM' not in df.columns:
            return set()
        return set(df['dealYM'].astype(str).unique())
    except Exception:
        return set()


def save_append(category_dir, lawd_cd, deal_ymd, rows):
    """기존 parquet에 신규 월 추가 (중복 제거)"""
    if not rows:
        return 0
    df_new = pd.DataFrame(rows)
    df_new['dealYM'] = deal_ymd
    df_new['LAWD_CD'] = lawd_cd
    path = os.path.join(category_dir, f'{lawd_cd}.parquet')
    if os.path.exists(path):
        df_old = pd.read_parquet(path)
        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.drop_duplicates()
    else:
        df = df_new
    df.to_parquet(path, index=False)
    return len(df_new)


def month_range(start_ym: str, end_ym: str):
    """YYYY-MM 기간을 YYYYMM 리스트로"""
    start = datetime.strptime(start_ym, '%Y-%m')
    end = datetime.strptime(end_ym, '%Y-%m')
    out, cur = [], start
    while cur <= end:
        out.append(cur.strftime('%Y%m'))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='기존 무시하고 전체 재다운로드')
    parser.add_argument('--start', default='2020-01', help='시작 YYYY-MM (기본 2020-01)')
    parser.add_argument('--categories', nargs='+', default=['매매', '전월세'],
                        choices=['매매', '전월세'])
    args = parser.parse_args()

    codes = pd.read_csv(CODE_PATH, encoding='utf-8-sig', dtype={'시군구코드': str})
    end_ym = datetime.now().strftime('%Y-%m')
    target_months = month_range(args.start, end_ym)
    print(f'대상 기간: {args.start} ~ {end_ym} ({len(target_months)}개월)')
    print(f'대상 시군구: {len(codes)}개 · 카테고리: {args.categories}')

    total_calls, saved_rows, failed = 0, 0, []
    for cat in args.categories:
        url, cat_dir = ENDPOINTS[cat]
        print(f'\n[{cat}] {cat_dir}')
        for _, row in codes.iterrows():
            lawd_cd = row['시군구코드']
            name = f"{row['시도']} {row['시군구']}"
            done = set() if args.full else existing_months(cat_dir, lawd_cd)
            todo = [m for m in target_months if m not in done]
            if not todo:
                print(f'  {name}({lawd_cd}): 이미 최신')
                continue
            print(f'  {name}({lawd_cd}): {len(todo)}개월 다운로드...', end='', flush=True)
            cnt = 0
            for ymd in todo:
                rows, err = fetch_month(cat, url, lawd_cd, ymd)
                total_calls += 1
                if rows is None:
                    failed.append((cat, lawd_cd, ymd, err))
                    print(f'\n    {ymd} 실패: {err[:80]}', end='')
                    continue
                cnt += save_append(cat_dir, lawd_cd, ymd, rows)
                time.sleep(0.15)
            saved_rows += cnt
            print(f' → {cnt}건')

    print(f'\n총 API 호출: {total_calls} · 신규 행: {saved_rows} · 실패: {len(failed)}')
    if failed:
        for f in failed[:5]:
            print(f'  {f}')


if __name__ == '__main__':
    main()
