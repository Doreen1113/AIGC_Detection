# BACKBONE-HIER — MobileNetV4 inside the production hierarchical architecture (pre-declared 2026-09-07)

## Why
`backbone_swap_20260907` tested MobileNetV4 only as a **flat three-way** model. On the P3 frontier it
was a KEEP (false accusation 8.84 → 2.81%, significant), but on the full Freeze-Gate battery at the
native rule it failed two gates that production v8.17 passes (fake+filter stress 11.36% vs 2.80%;
Alibaba filter recall 72.4% vs 97.7%). Two explanations are confounded there: (a) the backbone,
(b) the flat label space (flat ShuffleNetV2 also gives stress 7.25%). This round removes (b).

## Fixed before any result is read
- Architecture: production hierarchy (Layer1 real-vs-manipulated @ τ=0.5 → Layer2 fake-vs-filter),
  `decision_rule.decide` unchanged, artifact head unchanged (v6).
- Data: production v8.11/v8.17 splits (`splits/v811_layer1_train.txt`, `splits/v811_layer2_train.txt`);
  no FF++, no new mining. **The only change versus the production lineage is the spatial backbone.**
- Backbone: timm `mobilenetv4_conv_small.e2400_r224_in1k`, ImageNet init (no ShuffleNetV2 warm start
  possible); FFT branch and head fresh. Recipe = the BASE arm of `p1a1_interference_20260905` (L1) and
  `removal_ablation_20260904` CTRL recipe (L2), seed 20260907, one seed.
- Harness: `eval_gates.py` derived from `p1a1_interference_20260905/eval_gates.py`, run as `HIER_MNV4`.

## Decision rule (declared)
Compared against production v8.17 numbers in `docs/releases/v8.11_production/RELEASE_RESULTS.md` /
`EXPERIMENT_REGISTRY.md` (bootstrap CIs already on file):
- **ADOPT-CANDIDATE** only if every Freeze Gate passes (True Test fake ≥ 99%, filter ≥ 90%, AIGuard/unseen
  AUROC ≥ 0.80, CelebA ≥ 99%, StyleGAN2 ≥ 99%, Alibaba ≥ 95%, stress ≤ 3.76% = upper CI of v8.17) **and**
  at least one stretch metric (Shadow real, FF++ zero-shot AUROC, True Test real) improves beyond the
  v8.17 CI half-width. Even then a second seed is required before any production change.
- **KEEP-SHUFFLENET** otherwise. A single-seed result cannot flip production.

## What this round cannot show
Whether MobileNetV4 would also win under the SBI-augmented Layer1 recipe of v8.17 (this is the plain
BASE recipe); a positive here would motivate that follow-up, a negative closes the backbone question
for the capstone.
