@echo off
REM NASH CLI wrapper for Windows
REM Usage: .\scripts\nash_cli\nash.bat run --preset hawk_dove --rounds 200

cd /d "%~dp0\..\.."
python -m scripts.nash_cli.main %*
