@echo off

rem WebKit application server launch script for Windows.
rem This wrapper script is needed for the AutoReload mechanism.

rem You may want to use a specific Python executable:
set PYTHON=python

rem Check whether this is a cmd-like shell
set CMD=cmd
if "%~n0"=="~n0" set CMD=dos

rem Prefer using %* instead of positional parameters,
rem because the latter have equals signs removed:
if %CMD%==cmd set ARGS=%*

rem You may give the following Python parameters in advance,
rem followed by the parameters passed on to ThreadedAppServer:
rem   -O with optimization (.pyo instead of .pyc)
rem   -u unbuffered output (useful for debugging)
set PY_OPTS=
:getopt
if (%1)==(-O) goto setopt
if (%1)==(-u) goto setopt
goto continue
:setopt
set PY_OPTS=%PY_OPTS% %1
if %CMD%==dos goto shift3
rem %* is not affected by shift, so shift manually:
:shift1
if "%ARGS:~0,2%"=="%1" goto shift2
set ARGS=%ARGS:~1%
goto shift1
:shift2
set ARGS=%ARGS:~3%
:shift3
shift
goto getopt
:continue

rem If %* not available, use positional parameters:
if %CMD%==dos set ARGS=%1 %2 %3 %4 %5 %6 %7 %8 %9

rem Make the directory where this script lives the current directory:
if %CMD%==cmd pushd %~dp0

rem As long as the app server returns a 3, it wants to be restarted:
:restart
%PYTHON%%PY_OPTS% Launch.py ThreadedAppServer %ARGS%
if errorlevel 3 goto restart

rem Change back to old working directory:
if %CMD%==cmd popd
