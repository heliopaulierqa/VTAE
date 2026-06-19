@echo off
REM ============================================================
REM  VTAE — Wrapper de execucao (Windows)
REM  Ativa o ambiente virtual automaticamente e repassa todos
REM  os argumentos para o comando "vtae" real.
REM
REM  Uso (identico ao comando vtae normal, so trocando o nome):
REM    vtae.bat run --jornada internacao
REM    vtae.bat run --test cadastro_paciente_jornada
REM    vtae.bat systems
REM    vtae.bat flakiness --top 5
REM ============================================================

setlocal

if not exist "%~dp0.venv\Scripts\activate.bat" (
    echo ERRO: ambiente virtual nao encontrado em .venv
    echo Rode instalar.bat primeiro.
    pause
    exit /b 1
)

call "%~dp0.venv\Scripts\activate.bat"
vtae %*

endlocal