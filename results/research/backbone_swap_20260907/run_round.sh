#!/bin/bash
PY="C:/Users/2603055/AppData/Local/miniconda3/python.exe"; export PYTHONIOENCODING=utf-8
cd "C:/My_Project/AIGC/results/research/backbone_swap_20260907"
log(){ echo "=== [$(date +%H:%M:%S)] $1 ===" >> run_round.log; }
log "TRAIN TERN + MobileNetV4"
"$PY" -u train_arm.py --arm TERN --arch mobilenetv4 --seed 20260906 > train_TERN_mnv4_stdout.log 2>&1
echo "  rc=$?" >> run_round.log
log "EVAL FRONTIER"
"$PY" -u eval_frontier.py > eval_frontier.log 2>&1; echo "  rc=$?" >> run_round.log
log "ROUND COMPLETE"
