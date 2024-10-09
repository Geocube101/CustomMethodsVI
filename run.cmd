@ECHO OFF
./run/terminal.py
IF %ERRORLEVEL% neq 0 (
ECHO EXIT_STATUS=%ERRORLEVEL%
pause
)