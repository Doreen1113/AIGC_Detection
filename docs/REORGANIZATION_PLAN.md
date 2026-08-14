# Reorganization Plan (Proposal Only — Stage A of a 3-Stage Plan)

> **This document proposes a future target structure. Nothing described below has been
> executed.** This task's only actions were: reading files, running read-only git/grep/glob
> commands, and writing the 7 documentation files listed in `docs/PROJECT_CATALOG.md`'s
> companion set. No file was moved, renamed, copied, or deleted.

## Proposed future target structure (not yet built)

```
AIGC/
├── pipeline.py                      # stays at root — production entry point
├── CLAUDE.md, TODO.md, README.md    # stay at root
├── *.pth (production only)          # stays at root: layer1_v811d, layer2_v811, artifact_classifier_v3
├── face_landmarker.task             # stays at root
├── docs/                            # unchanged
├── splits/                          # unchanged (heavily path-referenced)
├── scripts/
│   ├── train/                       # active train_v8xx.py scripts
│   ├── eval/                        # active eval_*.py scripts
│   ├── audit/                       # audit_*/check_*/diagnose_*/verify_*.py
│   ├── xai/                         # xai_*/phase2_*/gradcam-related scripts
│   ├── deployment/                  # mobile_fft.py, export/benchmark/verify scripts
│   ├── splits_builders/             # build_v*_splits.py generators
│   └── data_prep/                   # download_/dedup_/extract_/generate_ scripts
├── checkpoints/
│   ├── production/                  # symlink or copy pointer, NOT the source of truth
│   └── research/                    # v8.12-v8.16 checkpoints
├── datasets/
│   ├── real/, fake/, filter/, df40/, eval/, hardneg/, base/, phase2/, phase3/
├── results/                         # unchanged structurally, possibly sub-grouped by phase
└── archive/                         # unchanged — already the destination of a prior legacy move
```

This structure is a proposal for discussion, not a commitment. The exact grouping (e.g.
whether `scripts/audit/` and `scripts/xai/` should merge) should be revisited once Stage B
is actually scoped with the user.

## Three-stage rollout

### Stage A — Documents + manifests (**this round, already done**)

- Created `docs/PROJECT_CATALOG.md`, `docs/ACTIVE_ARTIFACTS.md`, `docs/RESULTS_PROVENANCE.md`,
  `docs/ROOT_FILE_MANIFEST.csv`, `docs/REORGANIZATION_PLAN.md` (this file),
  `docs/DEPRECATED_OR_HISTORICAL.md`, `docs/CHECKPOINT_REFERENCE_MAP.csv`.
- Zero files moved, renamed, deleted, or modified outside of `docs/`.
- Pre-check: none needed (read-only).
- Migration: N/A.
- Smoke test: N/A — no runtime behavior changed. (Optional sanity check: confirm `pipeline.py`
  still runs unmodified — not performed in this pass per the read-only constraint, but nothing
  in this stage could have affected it.)
- Rollback: `git status` should show only new untracked files under `docs/`; if unwanted,
  `git clean` or manual deletion of the 7 new files fully reverts this stage. (Not executed
  automatically — left for the user.)

### Stage B — Low-risk scripts + historical figures (**NOT executed this round**)

Candidates (from `docs/ACTIVE_ARTIFACTS.md`'s "safe low-risk tidy-up" list): one-off
diagnostic/audit scripts whose results are already captured in `results/*.json`, one-off
chart/figure generators, and already-run download/extraction scripts.

- **Pre-check steps**:
  1. For each candidate file, grep the entire repo (root, `AIGuard/`, `docs/`, `results/`)
     for its filename to confirm nothing else `import`s it or shells out to it by relative path.
  2. Confirm the script's outputs (if any) are already materialized in `results/` (i.e., the
     script is not the sole record of a still-needed computation).
  3. Snapshot `git status` and `git log -1` before starting, so the starting state is recorded.
- **Migration steps**:
  1. `git mv` (not raw `mv`) each file to its proposed `scripts/<category>/` destination, to
     preserve history.
  2. Do this in small batches (e.g. by category), not one giant move, so any breakage is
     easy to bisect.
  3. Update any cross-references found in step 1 (docs mentioning the script's root-relative
     path) in the same commit.
- **Smoke test steps**:
  1. Re-run `git status` — should show only the intended renames.
  2. Spot-run 2-3 moved scripts with `--help` or a dry-run flag if available, to confirm they
     still import correctly from the new location (most use absolute `BASE = r"C:\My_Project\AIGC"`
     paths for data, so relocation of the *script* itself should not break data access — but the
     script's own directory-relative assumptions, if any, must be checked).
- **Rollback method**: `git mv` back to original location (or `git revert` the migration commit
  if it was a single commit per batch, which is the recommended approach specifically so
  rollback is one command).

### Stage C — Checkpoints, results, datasets (**only after full reference-check**)

This is the highest-risk stage: checkpoints and datasets are the two categories where a
silent breakage (e.g. `pipeline.py` failing to find a `.pth` file) is worst, and where a
100+-file reference sweep (as partially done for checkpoints in this task's Step 2) must be
fully exhaustive first — including references from `AIGuard/*.py`, any user-run ad hoc
notebooks not tracked in this repo, and the N-drive backup scripts in CLAUDE.md's "Backup"
section (which hardcode source paths too).

- **Pre-check steps**:
  1. Full checkpoint reference sweep (extend `docs/CHECKPOINT_REFERENCE_MAP.csv` to
     100% coverage — this task's sweep covered `.py`/`.md`/`.json`/`.yaml`/`.yml`/`.txt`
     but did not exhaustively verify every possible dynamic path construction, e.g.
     `os.path.join(BASE, f"shufflenet_v2_layer1_{tag}.pth")` patterns where `tag` is a
     CLI argument — those require reading each such script's argument-parsing logic).
  2. Confirm the N-drive backup robocopy commands in `CLAUDE.md` still function against
     the proposed new layout (they currently exclude several dataset dirs by exact name).
  3. Confirm no dataset directory is referenced by a hardcoded absolute path that assumes
     the CURRENT root-level location in more than one place with inconsistent assumptions.
- **Migration steps**:
  1. Move (not copy — repo is large, avoid doubling disk usage) one dataset/checkpoint
     family at a time, starting with the lowest-reference-count, lowest-risk items
     (e.g. `archive/`'s own already-archived legacy checkpoints, which are already isolated).
  2. Update `pipeline.py`'s `BASE`/weights paths ONLY as an explicit, separately-reviewed
     change — this task's instructions forbid touching `pipeline.py`, and that constraint
     should carry into Stage C planning: moving production checkpoints requires a
     `pipeline.py` update in the same breath, which is a materially different and higher-risk
     change than Stage A/B.
  3. Update every script identified in `docs/CHECKPOINT_REFERENCE_MAP.csv` for the moved
     checkpoint(s), and every dataset-path reference identified via a fresh grep pass.
- **Smoke test steps**:
  1. Run `pipeline.py --image <known test image>` end-to-end and confirm output matches
     a previously recorded golden result (e.g. compare against `pipeline_test_output/`
     if present).
  2. Re-run at least one Freeze Gate eval script (e.g. `eval_v811_gates.py`) and confirm
     numbers match the TODO.md-documented Freeze Gate table exactly.
  3. Re-run `AIGuard/stress_test_v811_pipeline.py` and confirm the 3.71% fake+filter
     misclassification figure reproduces — this script has documented history of being
     the exact place where checkpoint-version mix-ups were caught before, so it's a good
     regression canary.
- **Rollback method**: Because Stage C touches `pipeline.py`, rollback must restore both the
  file layout AND the exact prior `pipeline.py` content — use `git revert` on the specific
  commit(s), not a manual undo, and re-verify with the same smoke tests before considering
  the rollback complete.

## Explicit gate

**Stage B / C 未經使用者確認不得執行 (Stage B and Stage C must not be executed without
explicit user confirmation).** This plan is a proposal for discussion only.
