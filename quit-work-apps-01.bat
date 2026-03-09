@echo off
echo Closing work applications...

:: List of applications to close
set "apps=zoom.exe CamoStudio.exe"

:: Loop through each app
for %%a in (%apps%) do (
	echo Attempting to close %%a...
	taskkill /F /IM %%a /T
	if %ERRORLEVEL% EQU 0 (
		echo Successfully closed %%a
	) else (
		echo %%a was not running
	)
)