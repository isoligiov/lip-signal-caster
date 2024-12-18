@echo off
python -m venv env
call env\Scripts\activate
pip install -r requirements.txt

set /p appName=APP_NAME: 
set /p channelId=CHANNEL_ID: 
set outputFile=.env
(
  echo APP_NAME=%appName%
  echo CHANNEL_ID=%channelId%
) > %outputFile%

echo .env initialized