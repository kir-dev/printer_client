cd src
python setup_win.py py2exe 2>build_error.log
cd ..
xcopy /I /Y src\res dist\res
copy CHANGES.txt dist\

rem Cleanup

rd src\build /S/Q