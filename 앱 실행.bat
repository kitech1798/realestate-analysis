@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo === 부동산 실거래가 분석 (포트 8502) ===
echo 브라우저에서 http://localhost:8502 접속
echo 종료: Ctrl+C
echo.
streamlit run rt_app.py --server.port 8502
pause
