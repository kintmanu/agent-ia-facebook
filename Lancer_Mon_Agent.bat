@echo off
title Mon Agence IA - Tableau de Bord
echo ========================================================
echo   Lancement du Tableau de Bord IA Facebook (Streamlit)
echo ========================================================
cd /d "%~dp0"
echo Demarrage en cours, ouverture dans votre navigateur...
py -3.12 -m streamlit run app.py
pause
