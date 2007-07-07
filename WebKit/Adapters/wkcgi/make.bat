@echo off

rem Batch file for generating the wkcgi.exe CGI executable.

rem You need to have the following freely available tools installed:
rem (see http://msdn.microsoft.com/vstudio/express/downloads/):
rem - Microsoft Visual C++ 2005 Express Edition
rem - Microsoft Platform SDK for Microsoft Visual C++ 2005 Express
rem   (Microsoft Windows Server 2003 R2 Platform SDK)

rem Set environment variables

set VC=%ProgramFiles%\Microsoft Visual Studio 8\VC
set SDK=%ProgramFiles%\Microsoft Platform SDK for Windows Server 2003 R2
set APACHE=%ProgramFiles%\Apache Software Foundation\Apache2.2

call "%VC%\vcvarsall" x86
call "%SDK%\setenv" /XP32

rem Compile and link wkcgi

cl /W3 /O2 /EHsc /wd4996 ^
    /D "WIN32" /D "_CONSOLE" /D "_MBCS"  ^
    wkcgi.c ^
    ..\common\wkcommon.c ..\common\marshal.c ^
    ..\common\environ.c ..\common\parsecfg.c ^
    /link wsock32.lib /subsystem:console
