#!/bin/bash

cd /Users/stanchung/Markdowns/2025.6.12\ MaterialInterfaceDicussion
source .venv/bin/activate

# 用 Python 直接啟動 Flask app（指定 host 與 port）
python3 -u scroll_manage_UI.py &

# 等待 3~5 秒確保 Flask 起動
sleep 5

# 自動開啟 Safari
open -a Safari http://127.0.0.1:5000