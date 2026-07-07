@echo off
title OpenDataLoader PDF to Markdown Converter
echo Dang khoi dong ung dung GUI...
python "%~dp0convert_gui.py"
if %errorlevel% neq 0 (
    echo.
    echo Da co loi xay ra khi khoi chay ung dung.
    pause
)
