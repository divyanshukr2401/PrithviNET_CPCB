#!/bin/bash
# Auto-restart wrapper for CPCB data download.
# The download script tends to silently die after ~20-30 stations.
# This wrapper restarts it automatically until all 591 stations are done.
#
# Usage: bash scripts/download_loop.sh

PYTHON="D:/Coding/PRITHVINET/venv/Scripts/python.exe"
SCRIPT="scripts/download_cpcb_historical.py"
LOG="data/download_all_india.log"
MAX_RESTARTS=50

echo "[download_loop] Starting auto-restart download loop (max $MAX_RESTARTS restarts)"
echo "[download_loop] Log: $LOG"

for i in $(seq 1 $MAX_RESTARTS); do
    echo ""
    echo "[download_loop] ===== Run #$i ($(date)) ====="
    "$PYTHON" -u "$SCRIPT" --delay 1.0 --years 2024,2025 2>&1 | tee -a "$LOG"
    EXIT_CODE=$?
    
    # Count downloaded files
    FILE_COUNT=$(find data/raw/hourly/ -name "*.xlsx" 2>/dev/null | wc -l)
    echo "[download_loop] Exit code: $EXIT_CODE, Files so far: $FILE_COUNT"
    
    # Check if download completed normally (the script prints summary at the end)
    if grep -q "^Files downloaded:" "$LOG" 2>/dev/null; then
        # Check if the last run was a clean finish (all stations processed)
        LAST_STATION=$(grep "^\[" "$LOG" | tail -1 | grep -oP '^\[\K\d+')
        if [ "$LAST_STATION" = "591" ] || [ "$LAST_STATION" -ge 590 ]; then
            echo "[download_loop] All stations processed! Done."
            break
        fi
    fi
    
    echo "[download_loop] Download died or completed partially. Restarting in 10s..."
    sleep 10
done

echo "[download_loop] Loop finished. Total XLSX files: $(find data/raw/hourly/ -name '*.xlsx' | wc -l)"
