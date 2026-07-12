# Paper 清單

---

## 核心使用中

| 論文 | 用途 | 狀態 |
|------|------|------|
| [ShuffleNet V2: Practical Guidelines for Efficient CNN Architecture Design](https://arxiv.org/abs/1807.11164) (ECCV 2018) | 主 backbone，空間分支 | ✅ 使用中 |
| [RetouchingFFHQ: A Large-scale Dataset for Fine-grained Face Retouching Detection](https://arxiv.org/abs/2307.10642) | Filter 訓練資料 + MAM 架構參考 | ✅ 使用中 |
| [Grad-CAM++: Improved Visual Explanations for Deep Convolutional Networks](https://arxiv.org/abs/1710.11063) | 可解釋性熱力圖，target layer: conv5 | ✅ 使用中 |
| [Thinking in Frequency: Face Forgery Detection by Mining Frequency-aware Clues](https://arxiv.org/abs/2007.09355) (ECCV 2020) | FFT branch 設計依據 | ✅ 使用中 |

---

## 參考 / 引用中

| 論文 | 用途 | 狀態 |
|------|------|------|
| [DF40: Toward Next-Generation Deepfake Detection](https://arxiv.org/abs/2406.13495) (NeurIPS 2024) | Cross-dataset eval protocol；Domain gap 是公認難題的依據 | ✅ 參考中 |
| [FakeShield: Explainable Image Forgery Detection and Localization via Multi-modal LLMs](https://openreview.net/pdf?id=pAQzEY7M03) (ICLR 2025) | 輸出格式設計 + FakeShield mask 概念 | ✅ 參考中 |
| [HEIE: MLLM-Based Hierarchical Explainable AIGC Image Evaluation](https://arxiv.org/abs/2412.10667) (CVPR 2025) | 可解釋 AIGC 偵測，我們的目標方向（輕量版） | ✅ 參考中 |
| [Deceptive Beauty: The Risks of AI-Enhanced Appearance](https://arxiv.org/abs/2409.00375) (2024) | Filter 偵測任務學術依據 | ✅ 參考中 |
| [Impact and Detection of Facial Beautification in Face Recognition: An Overview](https://www.researchgate.net/publication/336705492) (IEEE Access 2019) | Filter 分類定義依據（磨皮/美白/大眼/瘦臉） | ✅ 參考中 |
| [Detecting GANs and Retouching Based Digital Alterations via DAD-HCNN](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w39/Jain_Detecting_GANs_and_Retouching_Based_Digital_Alterations_via_DAD-HCNN_CVPRW_2020_paper.pdf) (CVPRW 2020) | 相關工作；同時偵測 GAN 與 retouching | ✅ 參考中 |
| [Hierarchical Fine-Grained Image Forgery Detection and Localization](https://openaccess.thecvf.com/content/CVPR2023/papers/Guo_Hierarchical_Fine-Grained_Image_Forgery_Detection_and_Localization_CVPR_2023_paper.pdf) (CVPR 2023) | 局部偽造定位，Grad-CAM 區域標注的相關方法 | ✅ 參考中 |

---

## 計劃使用（第二階段）

| 論文 | 用途 | 狀態 |
|------|------|------|
| [FakeVLM: Towards a Multimodal Deepfake Detection Model](https://arxiv.org/abs/2503.14905) (2025) | 知識蒸餾 teacher model；FakeClue dataset 來源 | ⏳ 計劃使用 |
| [DeFakeQ: Deepfake Detection via Quantization](https://arxiv.org/abs/2412.01799) | INT8 量化部署 | ⏳ 計劃使用 |
| [Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531) (Hinton 2015) | 知識蒸餾方法論 | ⏳ 計劃使用 |
| [Deep Compression](https://arxiv.org/abs/1510.00149) | 模型壓縮（剪枝 + 量化） | ⏳ 計劃使用 |
| [MobileNetV4: Universal Models for the Mobile Ecosystem](https://arxiv.org/abs/2404.10518) | Edge 部署備選 backbone | ⏳ 評估中 |

---

## 其他相關（已閱，暫不使用）

| 論文 | 備注 |
|------|------|
| [LFFD: A Light and Fast Face Detector for Edge Devices](https://arxiv.org/abs/1904.10633) | 輕量人臉偵測，若需要 face detection 模組可參考 |
| [EleGANt: Exquisite and Locally Editable GAN for Makeup Transfer](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136760714.pdf) (ECCV 2022) | Makeup transfer，不在目前偵測範圍 |
| [Unveiling Authenticity with Diffusion-based Face Retouching Reversal](https://arxiv.org/abs/2405.07582) | 修圖還原方向，非目前任務 |
| [AutoRetouch: Automatic Professional Face Retouching](https://openaccess.thecvf.com/content/WACV2021/papers/Shafaei_AutoRetouch_Automatic_Professional_Face_Retouching_WACV_2021_paper.pdf) (WACV 2021) | 生成美顏資料可參考，暫無計劃 |
