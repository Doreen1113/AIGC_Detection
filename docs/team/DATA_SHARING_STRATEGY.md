# Data Sharing Strategy（資料共享架構決策）— Hybrid Architecture

> 建立於 2026-08-14，中文撰寫。本文件記錄一項真實的團隊決策：專案程式碼、文件、
> manifest、與資料未來要如何分散在不同儲存層之間。這是一份前瞻性的設計筆記——
> **撰寫本文件過程中沒有建立任何資料註冊表（registry）、沒有建立任何 Hugging Face
> repo、也沒有任何資料集檔案被搬移、複製或上傳。**

## 五個層級

### 1. GitHub — 程式碼、文件、manifest、hash、registry、工具程式。不放資料集圖片。

GitHub 存放所有體積小、以文字為主、且版本歷史很重要的內容：

- 所有原始碼（`*.py`、`filters/`、`AIGuard/` 等）
- 所有文件（`docs/`，包含本文件）
- Split manifest（`splits/*.txt`、`*.tsv`）——這些是路徑與標籤的清單，不是圖片本身，
  放在這裡既安全又對版本追蹤很有價值
- Pair manifest（例如 `splits/v815_replication_set.tsv` 的 `source_stem` 配對欄、
  `results/phase2/filter_data_xai_provenance_audit_20260814/FILTER_DATA_PROVENANCE.csv`）
- Checkpoint／資料集的 **hash**（SHA256 紀錄，例如
  `docs/releases/v8.11_production/RELEASE_MANIFEST.json` 的 checkpoint hash 欄位）——
  hash 是一段很小的文字，能讓任何人驗證從別處取得的大型二進位檔是否正確，不需要
  該二進位檔本身進 git
- **資料 registry**（提議中，尚未建立——見下）：把每個資料集家族對應到目前實際的
  存放位置（N-drive 路徑／HF repo／外接 SSD 標籤）與驗證用 hash，讓「X 去哪裡拿」
  有一個唯一標準答案
- 下載／驗證工具——從 HF／N-drive 拉取資料、並在使用前核對 hash 是否符合 registry
  的腳本

**在這個架構下，資料集圖片永遠不進 GitHub**——連小圖也不例外。需要以版控方式追蹤的
極小型 demo／regression 素材屬於第 2 層（Git LFS），不屬於一般 git。

### 2. Git LFS — 不是主要的資料集共享機制；只放極小型 demo／regression 素材

Git LFS 可以用來放少量真正非常小、但值得跟著 `git clone` 一起走的檔案——例如目前
pipeline smoke test 已經在用的小型範例圖（`pipeline_test_input/`），或少量
regression-test 用的圖片。Git LFS **絕對不能**被當成完整訓練資料集的存放處——它撐不住
本專案實際的資料規模（依 `FILTER_DATA_PROVENANCE.csv` 的樣本數，每個家族動輒上萬張），
其存取模式本來就不是為此設計。若某批「資料集」開始感覺值得放進 LFS、且超出少量
demo／regression 圖片的規模，那就是該挪到第 3 層或第 4 層的訊號，而不是繼續往 LFS
裡塞的理由。

### 3. Hugging Face（private Dataset repo）— 規劃中，依優先順序推進

Hugging Face private Dataset repo 是規劃中的存放處，放置那些 (a) 對團隊共用或重現
實驗有價值、且 (b) 已確認可安全轉散布的資料。等這一層真的要建置時，優先順序如下：

1. **Manifest** — 跟第 1 層一樣的 split/pair manifest，可能會在這裡跟它們描述的
   實際資料放在一起以方便使用，但 GitHub 仍是版控的正本。
2. **小型 benchmark 素材** — 例如 True Test set、DF40-cdf replication set
   （`v815_replication_set/`，994 張）——體積小、對全隊的可重現性價值高。
3. **iOS package** — `ios_benchmark/` 的測試圖子集（`ios_benchmark/TEST_ASSET_MANIFEST.csv`
   中已鎖定的 40 張圖），待實際裝箱後。
4. **XAI 樣本** — 用於 Tier A GT 驗證的 before/after 配對樣本
   （`filter_data/` 子集、`fake_filter_hard_neg/` 子集）——自建產生，不涉及第三方
   轉散布的問題。
5. **確認可安全轉散布的自建衍生資料** — 任何本專案自己的程式碼從擁有轉散布權利的
   來源圖片產生出來的資料集（例如對 AIGuard/real 或 LFW 套用濾鏡的輸出，前提是
   LFW 本身的條款確實允許轉散布衍生裁切結果——這點要逐來源確認，不能假設）。

### 4. N-drive／Google Drive／外接 SSD — 大型資料的主要交接機制

這仍然是所有大型、及／或尚未通過第 3 層審核的資料的主要機制：

- **大型 A/B 訓練資料**（完整的自建 `filter_data/` 家族、`AIGuard/real`、
  `AIGuard/fake`、DF40 各來源等）
- **清洗後資料**（Step1/Step2 清洗後的輸出，專案內各處的 `clean_output/` 資料夾）
- **Composite 資料**（`fake_filter_hard_neg/`、`v816_composite/` 及類似的生成
  composite pool）
- **原始第三方資料集**（RetouchingFFHQ four/megvii/ali 各區塊、DF40、CelebA、
  VGGFace2、IMDB-WIKI 等）——見下方硬性規則，說明為什麼這些特別要留在這一層、
  不會自動流向第 3 層

`CLAUDE.md` 中已經記載的 N-drive 備份慣例（`N:\2603055\AIGC\`）就是這一層目前
實際在用的具體例子。

### 硬性規則：原始第三方資料集絕不自動上傳到 Hugging Face

**原始第三方資料集絕對不能自動重新上傳到 Hugging Face。** 任何第三方來源的資料
（相對於本專案自己衍生／生成的資料），在放進共享的 HF repo（不論是否為 private）
之前，都必須先逐資料集完成授權／轉散布審查。這件事對本專案很具體：
`results/phase2/filter_data_xai_provenance_audit_20260814/FILTER_DATA_PROVENANCE.csv`
已經記載 RetouchingFFHQ（家族 B/C/D）是一份公開學術資料集、有自己的授權條款，
而 DF40／CelebA／VGGFace2／IMDB-WIKI／LFW 各自也有各自的條款——本專案先前的任何
工作都從未對它們做過轉散布權利的審查。「Private repo」不能取代授權審查——即使是
private，若從未做過審查，「私下分享不當」依然違反大多數學術／研究資料集的授權條款。
截至本文件建立為止，本專案沒有對任何一個資料集做過這樣的審查；在完成之前，
所有原始第三方資料一律留在第 4 層。

---

## 若採用此架構，哪些地方需要 path／config 變更

這確實是一個全新的分散層：registry 與 manifest（第 1 層）描述的資料，其實際位元組
存放在別處（第 3 層或第 4 層），而不是固定的本機路徑。本節純屬前瞻性設計筆記——
**本文件不實作、也不排程下方任何一項**；只是記錄未來若真的要實作，會牽動哪些範圍。

### 核心問題：幾乎全專案都寫死了絕對路徑

Stage A 的全 repo 盤點（`docs/ROOT_FILE_MANIFEST.csv`）已經確立：**149 支 root 層級
Python 腳本中有 148 支**在檔案開頭寫死 `BASE = r"C:\My_Project\AIGC"`（或等價的
Windows 路徑字面值），之後所有資料集／checkpoint／split 路徑都是拿這個常數字串拼接
出來的。這一點在 P0 Production Evaluation Integrity Repair
（`docs/releases/v8.11_production/EVALUATION_INTEGRITY_REPAIR.md`）與 Phase 2
provenance audit 中都獨立再次確認過（audit 過程中讀過的每一支濾鏡生成腳本——
`filters/generate_filter_dataset.py`、`filters/generate_lfw_filters.py`、
`generate_vggface2_filters.py`、`generate_imdbwiki_filters.py`——全部遵循一模一樣的
`BASE = r"C:\My_Project\AIGC"` 慣例）。這正是決定遷移規模的關鍵事實：幾乎整個
codebase 都假設在同一台機器上有固定的絕對路徑，而不是一個可解析／可下載的參照。

### 未來若要建置間接層，需要涵蓋的範圍

- **一個 config／環境變數層**（例如一個 `AIGC_DATA_ROOT` 環境變數，或一個在 import
  時讀取的小型 `config.py`），讓每支腳本的 `BASE` 常數改成透過它解析，而不是寫死的
  字面值——這是一個機制上直接、但影響範圍很廣（148 支以上檔案）的變更，可以一次性
  全域取代，也可以隨著新腳本採用、舊腳本逐步遷移。
- **一個 sync／fetch 步驟**：根據第 1 層的 registry＋manifest，在任何腳本執行前，
  先把本機的 `AIGC_DATA_ROOT` 從第 3 層（HF）或第 4 層（N-drive/Drive/SSD）填好——
  目前完全不存在任何形式的這種機制。
- **fetch 時的 hash 驗證** — registry 裡每個家族的 hash（第 1 層）需要在第 3/4 層
  實際送來的資料上被核對，補上目前只存在於人工檢查的這個環節（例如本次協作過程中
  對照 `RELEASE_MANIFEST.json` 手動核對 checkpoint SHA256）。
- **Split manifest 路徑改寫** — `splits/*.txt`/`*.tsv` 檔案目前每一列都存的是完整的
  Windows 絕對路徑（例如 `C:\My_Project\AIGC\lfw\...`），這點在本次協作讀過的
  `splits/v815_replication_set.tsv`、`splits/v86_train_filter.txt` 等檔案中都已確認——
  這些需要改成相對於 root 的路徑（在載入時對照 `AIGC_DATA_ROOT` 解析），manifest 才能
  真正在不同機器／不同儲存層之間可攜。
- **濾鏡生成腳本本身**（`filters/*.py`、`generate_*_filters.py`）同時讀取與寫入
  `BASE` 相對路徑，所以輸入端（讀取已同步的第三方資料集）與輸出端（把生成資料寫到
  之後會被註冊／重新分享的位置）都需要加上間接層——這是同一個問題的雙面版本，
  不是單純唯讀端的小修改。

以上皆非目前正在實作或排程中的項目。本節存在的目的，是讓團隊日後若決定要建置
registry 與 sync 工具時，能事先知道對應的程式碼遷移範圍有多大，而不是做到一半才
發現。
