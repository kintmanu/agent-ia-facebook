@echo off
title Mon Agence IA - Tableau de Bord
echo ========================================================
echo   Lancement de votre Mini-App IA Facebook & Telegram
echo ========================================================
cd /d "%~dp0"
pip install -r requirements.txt >nul 2>&1
echo Demarrage du tableau de bord...
streamlit run app.py
pause
