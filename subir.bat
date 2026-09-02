@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   OMNISYS PRO - Subir mudancas para o GitHub
echo ============================================
echo.

set "msg=Atualizacao"
set "extra="
set /p "extra=> Digite uma descricao (ou ENTER para padrao): "

REM Detecta se ficou vazio/espacos
set "aux=%extra%"
set "aux=%aux: =%"
if not "%aux%"=="" set "msg=%extra%"

echo.
echo [1/4] Adicionando todos os arquivos...
git add -A
if errorlevel 1 goto :erro

echo [2/4] Gerando o commit...
git commit -m "%msg%" >nul 2>nul
if errorlevel 1 goto :sem_mudanca

echo [3/4] Enviando para o GitHub...
git push origin main 2>nul
if errorlevel 1 goto :erro

echo [4/4] Concluido!
echo.
echo Pronto! Suas mudancas ja estao no GitHub.
goto :fim

:sem_mudanca
echo.
echo Nada para commitar (nenhuma mudanca detectada).
echo Se voce editou um arquivo, salve-o antes de rodar de novo.
goto :fim

:erro
echo.
echo [AVISO] Houve um erro no envio.
echo Possiveis causas:
echo   - Mudancas feitas em OUTRO computador que nao estao aqui.
echo   - O GitHub pediu login novamente.
echo Para forcar envio (so se tiver certeza), rode:
echo   git push origin main --force
goto :fim

:fim
echo.
pause
