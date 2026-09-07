#!/bin/bash
PY="C:/Users/2603055/AppData/Local/miniconda3/python.exe"; export PYTHONIOENCODING=utf-8
cd "C:/My_Project/AIGC/results/research/backbone_hier_20260907"
log(){ echo "=== [$(date +%H:%M:%S)] $1 ===" >> run_round.log; }
until grep -q "SEED2 DONE" ../backbone_swap_20260907/run_seed2.log 2>/dev/null || grep -aq "best macro F1" ../backbone_swap_20260907/train_TERN_mnv4_s2_stdout.log 2>/dev/null; do sleep 60; done
log "TRAIN L1 MobileNetV4"; "$PY" -u train_l1.py --arm BASE --arch mobilenetv4 --seed 20260907 > train_l1_stdout.log 2>&1; echo "  rc=$?" >> run_round.log
log "TRAIN L2 MobileNetV4"; "$PY" -u train_l2.py --arm BASE --arch mobilenetv4 --seed 20260907 > train_l2_stdout.log 2>&1; echo "  rc=$?" >> run_round.log
L1="C:/My_Project/AIGC/checkpoints/research/backbone_hier_20260907/layer1_BASE_mobilenetv4_last.pth"
L2="C:/My_Project/AIGC/checkpoints/research/backbone_hier_20260907/layer2_BASE_mobilenetv4_s20260907.pth"
log "GATES"; "$PY" -u eval_gates.py --arm HIER_MNV4 --layer1 "$L1" --layer2 "$L2" --layer1-backbone mobilenetv4 --layer2-backbone mobilenetv4 > eval_HIER_MNV4.log 2>&1; echo "  rc=$?" >> run_round.log
log "ROUND COMPLETE"
