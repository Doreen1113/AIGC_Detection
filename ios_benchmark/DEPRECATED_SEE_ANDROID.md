# ⚠️ 已停用 — 請改用 android_benchmark/

> 新增於 2026-08-14。本檔案是新增的說明檔，**未修改本目錄下任何既有檔案**。

`ios_benchmark/` 目錄是在錯誤的裝置平台假設（iOS／iPhone）下建立的。Member C
負責 on-device deployment benchmark，但實際使用的是 **Android** 裝置，不是
iPhone。

正確的交接套件在 `android_benchmark/`，內容包含：`README.md`、
`DEVICE_BENCHMARK_PROTOCOL.md`、`PRODUCTION_ROUTING_SPEC.md`、
`EXPECTED_OUTPUT_SCHEMA.json`、`TEST_ASSET_MANIFEST.csv`、`golden_outputs/`、
`app_stub/`（Kotlin 骨架，非 Swift）。

本目錄（`ios_benchmark/`）依規則不可刪除，僅作為歷史紀錄保留——其中的分析內容
（例如從 `pipeline.py` 抽取出的前處理／routing 規格）在方法論上仍然正確，
`android_benchmark/PRODUCTION_ROUTING_SPEC.md` 也是基於同樣的原始碼重新確認過的，
但本目錄的檔案本身（`swift_stub/`、以 Xcode/iOS 為前提撰寫的協定文件等）**不應
再被使用**於任何實際的裝置 benchmark 工作。
