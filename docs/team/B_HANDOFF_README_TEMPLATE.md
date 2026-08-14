# Member B 交接包 README 範本

> 隨 Member B 交接包一起提供的 README 範本。實際打包時複製本文件、填入當次的日期與
> 實際內容，放進交接包根目錄。

## Baseline checkpoint 身分

本套件中的 production checkpoint 對應**凍結的 v8.11 production release**：

- **Layer1**：`shufflenet_v2_layer1_v811d.pth`
  SHA256：`3C61CF6886D2F9D4871B52749A15FD4E1B979D121C664BA85D9B069194C290B7`
- **Layer2**：`shufflenet_v2_layer2_v811.pth`
  SHA256：`8470AD52DADCDB44A6789067EFBBD7FBC20715CB3F4E3339630191889A55057E`
- **Artifact classifier**：`artifact_classifier_v3.pth`
  SHA256：（見隨附的 `B_handoff_dry_run_report.json`）
- 來源：`docs/releases/v8.11_production/RELEASE_MANIFEST.json`

## 允許的使用方式

- 讀取這些 checkpoint 做推論、產生新的評測結果（例如對 `FFHQ_ali_process` 跑
  `artifact_classifier_v3`）。
- 依 `TEAM_WORK_ALLOCATION.md` §D 範圍內的任務使用隨附的 XAI 樣本／manifest。
- 產生新的研究結果、新的政策提案文件。

## 禁止的使用方式

- **不得修改**收到的任何 checkpoint 檔案。
- **不得**把收到的 checkpoint 或本套件任何內容宣告為新的 production 版本——任何
  production 變更都必須走 `PRODUCTION_CHANGE_CONTROL.md`。
- **不得**把 `FFHQ_ali_process` 的 `COARSE_OR_MIXED`/`UNVERIFIABLE` 資料夾（除
  `Whitening_60`/`90` 以外的全部）算進 exact-type accuracy 指標——只能用於
  prediction-distribution／overclaim 稽核，見 `TEAM_WORK_ALLOCATION.md` §D 的範圍
  收斂說明。
- **不得**把 fake 說明文字改成自由生成的 MLLM 輸出取代目前的 evidence pipeline。
- **不得**在完成授權審查前，把本套件中任何第三方資料（`face_landmarker.task`、
  `FFHQ_ali_process` 子集）再次轉散布給套件接收者以外的任何人。

## 收到後應執行的驗證指令

對每個 checkpoint／TFLite 檔案，現場重新計算 SHA256 並核對：

```powershell
Get-FileHash -Path "shufflenet_v2_layer1_v811d.pth" -Algorithm SHA256
Get-FileHash -Path "shufflenet_v2_layer2_v811.pth" -Algorithm SHA256
Get-FileHash -Path "artifact_classifier_v3.pth" -Algorithm SHA256
Get-FileHash -Path "face_landmarker.task" -Algorithm SHA256
```

比對結果是否與本 README 上方（及 `B_handoff_dry_run_report.json`）記錄的值完全一致。
若有任何一項不一致，**停止使用該檔案**，回報給 Member A，不要假設「應該沒差」而
繼續往下做。

也建議重跑一次 `scripts/build_member_handoff_dry_run.py`（指向自己收到的路徑），
確認 `missing_required_count` 為 0、`forbidden_pattern_flags` 為空。

## 輸出路徑規則

自己產生的任何新結果，一律放進**新的、有日期**的資料夾，格式比照
`results/research/p1_r1_cross_source_failure_anatomy_20260814/` 的慣例（任務名稱＋
日期），**絕對不要覆寫**收到套件裡的任何檔案，也不要覆寫任何既有的 `results/` 內容。

## 升級／交還給 Member A 的規則

- 任何觸及 `PRODUCTION_CHANGE_CONTROL.md` 涵蓋清單的發現或提案，一律先走該流程的
  提案格式，不要直接動手改。
- 若在驗證過程中發現任何 hash 不一致、檔案缺漏、或本 README「禁止使用」清單中的
  情況，立即回報，不要自行決定如何處理後再告知結果。

## 回報結果時要用的格式

依 `EXPERIMENT_HANDOFF_TEMPLATE.md` 格式，每個實驗一份，包含 claim／non-claim／
limitations／對 production 的影響。整合審查時會依這個格式檢查。
