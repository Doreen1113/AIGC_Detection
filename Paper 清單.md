## **Research Domains**

### **1\. AIGC Detection**：[AIGC detection paper](https://drive.google.com/drive/folders/1ZUvRsQVZ5tjgOoc5gguynBQGLA7GrIpG?usp=drive_link) 待補

1. # [PixelProof](https://github.com/mytechnotalent/pixelproof) 可偵測Ai生成圖與修圖之圖片[https://arxiv.org/abs/2307.10642](https://arxiv.org/abs/2307.10642)

### **2\. Filter**：[filter paper](https://drive.google.com/drive/folders/1zzNmepIFPydH-sBv35TOnQKByoZJ6x3s?usp=drive_link) 待補

2. [*EleGANt: Exquisite and Locally Editable Generative Adversarial Network for Makeup Transfer* (ECCV 2022\)](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136760714.pdf) 能實現局部精準上妝，我們可以做VLM去抓取色彩分布與真實膚色之間的邊緣是否有不自然的融合痕跡   
3. [StableMakeup: When Real-World Makeup Transfer Meets Diffusion Model](https://arxiv.org/abs/2403.07764)  不用 GAN 他們用 Stable Diffusion 擴散模型幫照片上妝 能加上亮片等複雜的光影效果  
4. [Unveiling authenticity with diffusion-based face retouching reversal](https://arxiv.org/abs/2405.07582) 用 Stable Diffusion 擴散模型把一張被磨皮過的照片，並修容還原   
5. [AutoRetouch: Automatic Professional Face Retouching](https://openaccess.thecvf.com/content/WACV2021/papers/Shafaei_AutoRetouch_Automatic_Professional_Face_Retouching_WACV_2021_paper.pdf). 使用全卷積網路 (FCN) 或神經雙邊網格，做到「抹平瑕疵，但完美保留五官邊緣銳利度」的高級磨皮  
6. [Impact and Detection of Facial Beautification](https://www.researchgate.net/publication/336705492_Impact_and_Detection_of_Facial_Beautification_in_Face_Recognition_An_Overview)  統整學術界對「臉部美化」的百科全書與分類  
7. [RetouchingFFHQ: A Large-scale Dataset for Fine-grained Face Retouching Detection](https://arxiv.org/abs/2307.10642)  
   建立了一個大型、細粒度的人臉修圖資料集 **RetouchingFFHQ**，並提出一個可以加在 CNN backbone 上的 **Multi-granularity Attention Module, MAM**，用來提升人臉修圖偵測效果。  

### **3\. 輕量化和邊緣檢測：**

8. [LFFD: A Light and Fast Face Detector for Edge Devices](https://arxiv.org/abs/1904.10633)  專注於 Edge Device 上的模型輕量化設計，符合「手機平台」的資源限制要求  
9. [Detecting GANs and Retouching Based Digital Alterations via DAD-HCNN](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w39/Jain_Detecting_GANs_and_Retouching_Based_Digital_Alterations_via_DAD-HCNN_CVPRW_2020_paper.pdf) 探討如何利用 CNN 區分出「數位修圖」與「生成式 AI」的差異   
10. [Hierarchical Fine-G](https://openaccess.thecvf.com/content/CVPR2023/papers/Guo_Hierarchical_Fine-Grained_Image_Forgery_Detection_and_Localization_CVPR_2023_paper.pdf)[Detecting GANs and Retouching Based Digital Alterations via DAD-HCNN](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w39/Jain_Detecting_GANs_and_Retouching_Based_Digital_Alterations_via_DAD-HCNN_CVPRW_2020_paper.pdf)[rained Image Forgery Detection and Localization](https://openaccess.thecvf.com/content/CVPR2023/papers/Guo_Hierarchical_Fine-Grained_Image_Forgery_Detection_and_Localization_CVPR_2023_paper.pdf) 探討如何在圖片上標註出具體哪個局部被動過手腳 

11. # [MobileNetV4: Universal Models for the Mobile Ecosystem](https://link.springer.com/chapter/10.1007/978-3-031-73661-2_5) [所有 MobileNetV4 型號均可在https://github.com/tensorflow/models/blob/master/official/vision/modeling/backbones/mobilenet.py](https://github.com/tensorflow/models/blob/master/official/vision/modeling/backbones/mobilenet.py)取得。

12. # [Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531) 證明透過將整合模型中的知識提煉到單一模型中

13. # [Deep Compression: Compressing Deep Neural Networks with Pruning, Trained Quantization and Huffman Coding](https://arxiv.org/abs/1510.00149) 

    此壓縮方法有助於在行動應用中使用複雜的神經網絡，在 CPU、GPU 和行動 GPU 上的基準測試表明，壓縮後的網路逐層加速比提高了 3 到 4 倍，能源效率提高了 3 到 7 倍。

### **4\. VLM 與可解釋性** ：

1. [FakeShield: Explainable Image Forgery Detection and Localization via Multi-modal Large Language Models](https://openreview.net/pdf?id=pAQzEY7M03)  提出多模態框架，探討如何結合視覺與語言模型來解釋影像哪裡被篡改   
2. [Spot the Fake: Large Multimodal Model-Based Synthetic Image Detection with Artifact Explanation](https://arxiv.org/abs/2503.14905)  如何用 VLM 產生「自然語言特徵解釋」 

### **5\. Future Work ：生成式 Filter (optional)**  

