@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo === 부동산 실거래가 — 증분 갱신 ===
python download_data.py
if errorlevel 1 (
    echo.
    echo [에러] 다운로드 실패. push 건너뜀.
    pause
    exit /b 1
)
echo.
echo === GitHub push (Streamlit Cloud 자동 재배포) ===
git add "데이터/거래"
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "데이터 갱신: %date% %time:~0,5%"
    git push
    echo.
    echo [완료] 1~2분 후 https://realestate-analysis.streamlit.app 에 반영됩니다.
) else (
    echo [정보] 신규 데이터 없음. push 건너뜀.
)
echo.
pause
