@echo off

del /Q .\app\site.db
del /Q .\app\admin_key.dat
del /Q .\app\static\avatars\*
del /Q .\app\static\uploads\*
python3 .\initdb.py
python3 .\create_admin_key.py
pause
