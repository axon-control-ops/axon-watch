#!/usr/bin/env bash
set -euo pipefail
LOG=/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-9e41d8.log
{
  echo "{\"sessionId\":\"9e41d8\",\"runId\":\"post-fix\",\"timestamp\":$(date +%s000),\"location\":\"post-reboot-freeze-check.sh\",\"message\":\"post-reboot driver check\",\"hypothesisId\":\"A\",\"data\":{\"uname\":\"$(uname -r)\",\"nvidia_smi\":\"$(command -v nvidia-smi || true)\",\"lsmod_nvidia\":\"$(lsmod | awk '/^nvidia/{print $1}' | tr '\n' ',')\",\"lsmod_nouveau\":\"$(lsmod | awk '/^nouveau/{print $1}' | tr '\n' ',')\",\"data_errors\":$(journalctl -b 0 -k --no-pager 2>/dev/null | rg -c 'nouveau.*DATA_ERROR' || echo 0),\"disk\":\"$(df -P / | awk 'NR==2{print $5}')\"}}"
} >>"$LOG"
nvidia-smi || true
lsmod | awk '/^nvidia|^nouveau/{print}'
journalctl -b 0 -k --no-pager 2>/dev/null | rg -c 'DATA_ERROR' || echo 0
FREEZE_RUN_ID=post-fix python3 /home/edp/axon-nvme/repos/axon-watch/scripts/ops/freeze-sentinel.py &
echo "sentinel_pid=$!"
