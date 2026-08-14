# Deprecated / Historical Candidates (Read-Only Inventory, Stage A)

> Items below appear superseded by newer versions based on CLAUDE.md/TODO.md narrative and
> repo evidence. **All items are CANDIDATE only — nothing recommends deletion, and nothing
> was deleted, moved, or renamed to produce this document.** "Still referenced?" was checked
> via grep against `.py`/`.md`/`.json`/`.yaml`/`.yml`/`.txt` files repo-wide (excluding
> `splits/*.txt` data listings).

## Checkpoints

| Checkpoint | Superseded by | Still referenced by current code? |
|---|---|---|
| `shufflenet_v2_3class_v3.pth` … `v8_train`-era flat 3-class checkpoints (already relocated to `archive/checkpoints_legacy_v3_v89/`) | v8.11 hierarchical (Layer1+Layer2) | No live production references found; `docs/research_log.md` and `README.md` still narrate their history (expected — that's the record, not a live dependency) |
| `shufflenet_v2_3class_v88.pth` | v8.11 hierarchical | **Yes, intentionally** — `phase2_p0_v811_filter_gradcam_validation.py` and `build_phase2_evidence_pack.py` load it as the explicit v8.8-vs-v8.11 comparison baseline (`V88_REFERENCE_JSON = results/xai_comparison_eye_face_white.json`). This is a legitimate historical reference, not a stray/forgotten pointer — do not remove without updating those two scripts' comparison logic. |
| `shufflenet_v2_layer1_v811.pth`, `shufflenet_v2_layer1_v811b.pth`, `shufflenet_v2_layer1_v811c.pth` | `shufflenet_v2_layer1_v811d.pth` (production) | v811c referenced by `AIGuard/train_v811_layer1c.py` and `AIGuard/train_v811_layer1d.py` (as its init source) plus doc mentions; v811/v811b referenced only by their own training scripts. `pipeline.py` uses **only** v811d. |
| `shufflenet_v2_layer2_v811b.pth`, `shufflenet_v2_layer2_v811c.pth` | `shufflenet_v2_layer2_v811.pth` (production — note: production Layer2 is the *original* v811, not a lettered variant, unlike Layer1) | `AIGuard/train_v811_layer2b.py` / `train_v811_layer2c.py` are their sole producing scripts. TODO.md documents v811c was **previously mistakenly reported as v8.11's final numbers** in at least one earlier report — flagged here as a known historical mix-up risk, already caught and corrected per TODO.md's 2026-08-11 entry. |
| `shufflenet_v2_layer1_v812.pth`, `shufflenet_v2_layer2_v812.pth` | Not promoted; `pipeline.py` stayed on v811d/v811 | Actively referenced by 20+/12+ files respectively (per `docs/CHECKPOINT_REFERENCE_MAP.csv`) — this is a **live research track**, not dead/forgotten code, despite not being production. |
| `shufflenet_v2_layer1_v813.pth`, `shufflenet_v2_layer2_v813.pth` | Judged worse than v8.12; superseded by v8.14's route-filtered approach | Still referenced by `AIGuard/train_v813_layer1.py`/`layer2.py`, `test_v813_on_known_hard_subset.py` — kept per TODO.md's explicit "保留供對照，不刪除" (retain for comparison, do not delete) instruction |
| `shufflenet_v2_layer2_v815a_v814clean.pth` | Unclear — likely an intermediate v8.15a dual-head pilot artifact | **Zero references found** by this pass's grep sweep across `.py`/`.md`/`.json`/`.yaml`/`.yml`/`.txt`. This is an **orphan checkpoint** — present on disk, undocumented, unreferenced. Flag for manual follow-up rather than assumed-safe-to-archive. |

## Scripts

| Script(s) | Superseded by | Still referenced? |
|---|---|---|
| `train_v3.py` … `train_v82.py` (already relocated to `archive/scripts_legacy_v3_v89/`) | `AIGuard/train_v811_layer1*.py` / `train_v811_layer2*.py` | No — already archived, per `archive/MOVE_LOG.txt` |
| `build_v5_splits.py` … `build_v82_splits.py`, `build_v810*_splits.py` (already relocated to `archive/scripts_legacy_v3_v89/`) | `build_v811_layer1_splits.py` onward | No — already archived |
| `AIGuard/eval_unseen_v3.py`, `AIGuard/eval_crossdataset_v3_1.py`, `AIGuard/eval_crossdataset_binary.py` | `AIGuard/eval_ali_ood_v811.py`, `eval_v811_gates.py`, `eval_truetest_paired.py` | Filenames suggest v3-era, not grepped exhaustively in this pass — recommend a follow-up check before treating as safe to archive, since AIGuard/ was only listed (not deep-read) per task instructions |
| `xai_faithfulness_test.py` | `xai_faithfulness_blur_test.py` (2026-08-13: fixed constant-fill masking → blur-based masking, per TODO.md) | The older script is not deleted and TODO.md explicitly documents *why* the newer one exists (frequency-domain confound in the old masking method) — good candidate for `docs/DEPRECATED_OR_HISTORICAL.md` tracking but should stay on disk as the documented "what we used to do and why we stopped" record |
| `region_head_v1.pth` + `AIGuard/train_region_head_v1.py` | `region_head_v4.pth` / `train_region_head_v4.py` — but **note: none of v1-v4 are used by `pipeline.py`** (removed 2026-08-02, "near-total label degeneracy" per `docs/phase2_story.md`) | v1 referenced in `docs/Dataset 清單.md`, `docs/research_log.md`, `docs/研究路線圖...md`, `pipeline.py` (only in an explanatory comment, not a live load), `TODO.md` mentions v3 |
| `mine_v811_layer1_round2.py`, `round3.py` | `mine_v811_layer1_round4_newsource.py` (the round that produced the current production Layer1d) | All three still present and referenced in their own right as the historical mining chain — round2/3 are intermediate steps, not independently superseded artifacts to discard |
| `eval_ffpp_zeroshot_v811.py` vs `analyze_ffpp_auroc_both.py` vs `analyze_ffpp_zeroshot_detail.py` | Unclear ordering — all three touch v8.11 FF++ zero-shot eval; relationship (sequential refinement vs. parallel independent analyses) not confirmed in this pass | All three referenced by fresh `results/*ffpp*` outputs dated 2026-08-11, suggesting they're a related-but-not-strictly-superseding trio, not a deprecate-one-for-another situation |

## Datasets / folders

| Folder | Superseded by / rationale | Still referenced? |
|---|---|---|
| `WildDeepfake_subset/` | Explicitly deprecated per CLAUDE.md ("⛔ eval 已棄用") — semantic overlap with `AIGuard/fake` and video-frame (H.264) domain mismatch | Referenced only in doc history and its own generation script; not in any current active eval per CLAUDE.md's own note |
| `FFHQ_four_process/` | Superseded/disqualified — 2026-08-10 audit found 859 "unused" images are NOT identity-disjoint from the already-trained `FFHQ_megvii_four_process` (same FFHQ base-index range 60002-69999) | `check_ffhq_four_identity_overlap.py`, `check_ffhq_four_process_overlap.py` are the audit scripts that determined this; CLAUDE.md flags it explicitly as "不可用作新filter OOD來源" |
| `fake_filter_hard_neg_v88_backup/` | Backup of the v8.8-era hard-neg pool, before the v8.8→v8.11 hard-neg expansion | Name suggests intentional backup, not a live dependency — no code reference found beyond its own likely-original generation |
| `v89_filter_imdbwiki/`, `v89_filter_vggface2train/`, `v89d_candidate_pool/`, `v89d_paired_mined/`, `v89d_proxy_unseen_pool/` | v8.9-era research track, entirely predates the v8.11 hierarchical redesign | Referenced by their own `v89*` split files and scripts (already relocated to `archive/scripts_legacy_v3_v89/` per MOVE_LOG for the *scripts*; the *data folders* themselves were NOT part of that move and remain at root) — **note the asymmetry**: v8.9 scripts are archived but v8.9 generated datasets are not, which is itself worth flagging for a Stage C decision |

## Not flagged (explicitly still active despite "old-looking" version numbers)

- `shufflenet_v2_3class_v88.pth` — see checkpoints table above; actively used as a comparison baseline, not dead weight.
- v8.12/v8.13/v8.14/v8.15/v8.16 checkpoints and their scripts — all are **live research track**, referenced by 2-14+ files each per `docs/CHECKPOINT_REFERENCE_MAP.csv`, and explicitly retained per CLAUDE.md as "論文研究章節證據" (paper research-chapter evidence). Not historical in the sense of "forgotten" — historical only in the sense of "not production."
