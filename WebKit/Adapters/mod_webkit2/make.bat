@echo off

rem Batch file for generating the mod_webkit Apache 2.2 DSO module.

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

Set PATH=%Apache%\bin;%PATH%
Set INCLUDE=%Apache%\include;%INCLUDE%
Set LIB=%Apache%\lib;%LIB%

rem Compile and link mod_webkit

cl /W3 /O2 /EHsc /LD /MT ^
    /D "WIN32" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" ^
    /D "MOD_WEBKIT_EXPORTS" /D "NDEBUG" ^
    mod_webkit.c marshal.c ^
    /link libhttpd.lib libapr-1.lib libaprutil-1.lib ws2_32.lib

rem Install mod_webkit

copy mod_webkit.dll "%Apache%\modules\mod_webkit.so"
