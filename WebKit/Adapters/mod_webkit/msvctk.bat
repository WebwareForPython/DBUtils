@echo off

rem Batch file for compiling mod_webkit with
rem the free Microsoft Visual C++ 2003 Toolkit

Set PATH=C:\Progra~1\Microsoft Visual C++ Toolkit 2003\bin;%PATH%
Set INCLUDE=%ProgramFiles%\Microsoft Visual C++ Toolkit 2003\include;%INCLUDE%
Set LIB=%ProgramFiles%\Microsoft Visual C++ Toolkit 2003\lib;%LIB%

Set PATH=%ProgramFiles%\Microsoft Platform SDK\bin;%PATH%
Set INCLUDE=%ProgramFiles%\Microsoft Platform SDK\include;%INCLUDE%
Set LIB=%ProgramFiles%\Microsoft Platform SDK\lib;%LIB%

Set APACHE=%ProgramFiles%\Apache Group\Apache

cl /MT /W3 /GX /O2 /YX /FD /LD /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" /D "MOD_WEBKIT_EXPORTS" /I "%Apache%\include" mod_webkit.c marshal.c /link /libpath:"%Apache%\libexec" ApacheCore.lib ws2_32.lib

copy mod_webkit.dll "%Apache%\modules\mod_webkit.so"
