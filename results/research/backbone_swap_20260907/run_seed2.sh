#!/bin/bash
PY="C:/Users/2603055/AppData/Local/miniconda3/python.exe"; export PYTHONIOENCODING=utf-8
cd "C:/My_Project/AIGC/results/research/backbone_swap_20260907"
echo "=== [$(date +%H:%M:%S)] TRAIN TERN + MobileNetV4 seed2 ===" >> run_seed2.log
"$PY" -u train_arm.py --arm TERN --arch mobilenetv4 --seed 20260907 > train_TERN_mnv4_s2_stdout.log 2>&1
echo "  rc=$?" >> run_seed2.log
echo "=== [$(date +%H:%M:%S)] SEED2 DONE ===" >> run_seed2.log
