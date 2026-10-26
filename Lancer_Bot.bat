@echo off
title Mon Agence IA - Bot Telegram
echo ========================================================
echo   Lancement du Bot Telegram Interactif (Agent IA)
echo ========================================================
cd /d "%~dp0"
echo.
echo Le bot va demarrer et ecouter vos messages Telegram.
echo Laissez cette fenetre ouverte tant que vous souhaitez utiliser le bot.
echo.
py -3.12 bot.py
pause
