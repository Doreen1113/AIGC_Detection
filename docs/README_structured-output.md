# Pipeline Output Specification (v2.0.0)

輸出格式已與 `pipeline.py` 中的 `build_explanation()` 及 Grad-CAM 輸出對齊，舊版的 `retouching.level` 已移除。
`pipeline.py` 中的 `build_explanation()`有做修正，多了
    if prediction == "fake":
        return TEMPLATES["ai_generated"].format(region=region_str)
    if not artifact_types:
        return TEMPLATES["unknown_filter"].format(region=region_str)

## 正確的 JSON 輸出範例

### 範例一：美顏濾鏡影像 (Filter_processed)
```json
{
  "prediction": "filter_processed",
  "confidence": 0.9521,
  "artifact_types": ["over_smoothing", "face_reshaping"],
  "suspicious_region": ["left_cheek", "jaw"],
  "explanation": "Skin texture variance significantly reduced in left cheek and jaw area. Bilateral filter artifacts detected — unnatural surface smoothness. Unnatural facial contour detected in left cheek and jaw area. Geometric compression consistent with face slimming filter."
}
```

### 範例二：真實影像 (Real)
```json
{
  "prediction": "real",
  "confidence": 0.9987,
  "artifact_types": [],
  "suspicious_region": [],
  "explanation": "No significant manipulation artifacts detected. The image appears authentic."
}

```

## 欄位定義說明
prediction: 字串，固定為 real / fake / filter_processed。

confidence: 浮點數 (0.0 ~ 1.0)。

artifact_types: 字串陣列，容許值為 eye_enlarging, face_reshaping, over_smoothing, whitening。若為 real 則回傳空陣列 []。

suspicious_region: 字串陣列，內容來自 Grad-CAM 偵測出最高分的 FACE_REGIONS 鍵值。

explanation: 自動生成的英文說明文本。