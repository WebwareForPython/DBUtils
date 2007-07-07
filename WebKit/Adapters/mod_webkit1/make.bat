@echo off

rem Batch file for generating the mod_webkit Apache 1.3 DSO module

rem You need to have the following freely available tools installed:
rem - Microsoft Visual C++ Toolkit 2003
rem   (2005 Express Edition is not compatible with Apache 1.3 binaries)
rem - Microsoft Windows Server 2003 SP1 Platform SDK
rem   (or Microsoft Windows Server 2003 R2 Platform SDK)

rem Set environment variables

set VC=%ProgramFiles%\Microsoft Visual C++ Toolkit 2003
set SDK=%ProgramFiles%\Microsoft Platform SDK
set APACHE=%ProgramFiles%\Apache Group\Apache

call "%VC%\vcvars32"
call "%SDK%\setenv"

Set PATH=%Apache%\bin;%PATH%
Set INCLUDE=%Apache%\include;%INCLUDE%
Set LIB=%Apache%\libexec;%LIB%

rem Compile and link mod_webkit

cl /W3 /O2 /EHsc /LD /MT ^
    /D "WIN32" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" ^
    /D "MOD_WEBKIT_EXPORTS" /D "NDEBUG" ^
    mod_webkit.c marshal.c ^
    /link ApacheCore.lib ws2_32.lib

rem Install mod_webkit

copy mod_webkit.dll "%Apache%\modules\mod_webkit.so"
