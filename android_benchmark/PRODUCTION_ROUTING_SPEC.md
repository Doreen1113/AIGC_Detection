# Android Benchmark — Production Routing Spec（從 pipeline.py 讀出，非猜測）

> 本文件所有內容都是直接讀取 `pipeline.py` 原始碼得出，讓 Member C 不需要讀 Python
> 就能在 Kotlin 中精確複製同樣的邏輯。**本文件未修改 `pipeline.py` 本身。**

## 1. 模型檔案

| Layer | 訓練用 checkpoint（PyTorch） | fp32 TFLite（已驗證可部署） | 角色 |
|---|---|---|---|
| Layer1 | `shufflenet_v2_layer1_v811d.pth` | `layer1_v811d_float32.tflite` | real vs manipulated（2 類） |
| Layer2 | `shufflenet_v2_layer2_v811.pth` | `layer2_v811_float32.tflite` | fake vs filter（2 類），僅在 Layer1 判為 manipulated 時執行 |

兩者都是 `DualBranchModel(num_classes=2)`：ShuffleNetV2-x1.0 空間分支（1024 維，
ImageNet 預訓練，`fc` 換成 `Identity`）串接 256 維 FFT 分支，經過
`Linear(1280,512)→ReLU→Dropout(0.3)→Linear(512,2)`。

**合計大小**：fp32 20.91 MB（兩個 `.tflite` 檔案合計）。
**fp16**：已確認不可用（載入時失敗，`CONV_2D` prepare 錯誤）。
**int8**：已確認不可用——根因是 FFT 分支的 activation 動態範圍過大（`CLAUDE.md` 已記錄
根因分析），**Member C 不得用 int8 取代 production benchmark**。
**本次 benchmark 的 baseline 是 fp32 CPU（LiteRT/TFLite）**，NNAPI／GPU delegate
僅作為選配的對照組，不得取代 CPU baseline。

## 2. 輸入前處理（必須完全一致）

來源：`pipeline.py` 的 `preprocess_jpeg()` + `transform_infer`。

1. 讀圖，轉成 **RGB**。
2. **JPEG 標準化**：以 quality=85 重新編碼成 JPEG（記憶體內），再解碼回 RGB —— 這一步
   預設開啟，Android 端需要用等效的 JPEG 重新編碼（例如
   `Bitmap.compressToJpeg(quality=85)` 後再解碼）盡量對齊，encoder 差異視為可接受的
   微小數值飄移，非 bit-exact。
3. **Resize**：直接 resize 到 224×224（**不做** center crop，兩個維度都明確指定，
   所以是直接縮放/擠壓，不保持長寬比）。
4. **Tensor 轉換**：HWC uint8 [0,255] → CHW/NHWC float32 [0,1]（見下方通道順序說明）。
5. **標準化**：`(x - 0.5) / 0.5`，把 [0,1] 映射到 **[-1, 1]**，每個通道都一樣（不是
   ImageNet mean/std）。
6. **通道順序**：PyTorch/ONNX 端是 **NCHW**；轉成 TFLite 後（`onnx2tf`）變成
   **NHWC**（channels-last）——**Android 端必須餵給 TFLite interpreter NHWC、RGB、
   float32、範圍 [-1,1] 的 tensor**，不是 NCHW。
7. 人臉存在性 gate（`has_face()`，MediaPipe FaceLandmarker）在正式推論中會在分類器
   之前執行——40 張 benchmark 圖片預期都已經是預先篩選過的人臉裁切，本次
   benchmark 的重點是純推論延遲，是否要在 Android 端重現這一步由 Member C 依實際
   需求決定，不強制。

## 3. Layer1 輸出 → real／manipulated 判斷

`DualBranchModel(num_classes=2)` 輸出 2 個 logit。類別慣例（`CLASSES = ["real",
"fake", "filter"]`）：**index 0 = real，index 1 = manipulated**（fake 與 filter
在 Layer1 訓練時合併成一類）。

```
l1_probs = softmax(l1_logits)
p_real   = l1_probs[0]
p_manip  = l1_probs[1]
```

## 4. Layer2 輸出 → fake／filter 判斷，以及最終 routing 規則

Layer2 一樣輸出 2 個 logit，類別慣例是 **index 0 = fake，index 1 = filter**。

**Production routing 規則**（`hierarchical_predict()`，這是 Android 端必須忠實
複製的邏輯）：

```
l1_probs = softmax(layer1(x))
p_real, p_manip = l1_probs[0], l1_probs[1]

l2_probs = softmax(layer2(x))   # Layer2 一律執行，不論 Layer1 結果為何
p_fake_given_manip, p_filter_given_manip = l2_probs[0], l2_probs[1]

p_fake   = p_manip * p_fake_given_manip
p_filter = p_manip * p_filter_given_manip

prediction = argmax([p_real, p_fake, p_filter])   # 三類複合機率取 argmax
```

**注意這是一個複合機率的 argmax，不是「Layer1 說 real 就直接停」的硬性 gate**——
Layer2 一律執行，兩個模型的輸出被合併成一個三類分布後才取 argmax。絕大多數情況下
這等同於單純的 Layer1 gate（`p_real > 0.5` 幾乎總是直接勝出，因為此時兩個
manipulated 分量加總必須 `< 0.5`），但邊界情況並非完全相同。

**這對 latency benchmark 的意義**：因為 production 規則下 Layer2 一律執行，
**「real path」在嚴格意義上跟「manipulated path」的計算成本相同**（都跑兩層）。
`DEVICE_BENCHMARK_PROTOCOL.md` 仍然分開報告 real／manipulated 兩條路徑的延遲，
是為了跟桌機 benchmark（`benchmark_mobile_artifacts.py`，用的是更便宜的
strict-gate 近似規則：Layer1 判 real 就跳過 Layer2）做對照，但 Android 端的
**主要 benchmark 路徑必須實作上面這個 production 複合機率規則**，不是桌機那個
簡化版——這點原本在 iOS 版本的 spec 中是留白的待決事項，Android 版本直接定案：
一律採用 production 規則作為主路徑，strict-gate 規則若要測，需清楚標示為對照組。

## 5. 通道順序與數值範圍總結

- PyTorch/ONNX 邊界：NCHW，RGB，[-1,1]
- TFLite interpreter 邊界：**NHWC**，RGB，[-1,1]
- 沒有任何地方使用 ImageNet mean/std——全部都是 0.5/0.5，即使 backbone 是
  ImageNet 預訓練的 ShuffleNetV2 也一樣，這點已直接從 `pipeline.py` 原始碼確認。
