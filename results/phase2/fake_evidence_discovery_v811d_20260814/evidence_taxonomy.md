# Evidence Taxonomy — Phase 2F Fake Evidence Discovery (2026-08-14)

Scope note: this document defines every candidate scalar feature computed
this round. It is a companion to `results/phase2/fake_xai_level12_v811d_20260814/`
(Grad-CAM faithfulness/stability audit on v8.11d) — that work is about
whether the *model's own attention* is trustworthy; this document is about
whether *hand-computed, model-independent* signals discriminate real vs
fake at all, as candidate ingredients for a future non-templated fake
explanation sentence. No feature here is derived from v8.11 internals; the
only place v8.11 appears is as a read-only correlation reference
(`corr_with_v811_fake_prob` in `evidence_metrics_sourcewise.csv`).

All features are computed on the SAME preprocessing pipeline.py uses at
inference: `pl.preprocess_jpeg(img, quality=85)` → face gate `pl.has_face`
→ resize to 224x224 → grayscale (texture/frequency families) or MediaPipe
FaceLandmarker on the 224x224 frame (landmark/boundary families). This
means frequency/texture features describe what the model's own spatial
input actually contains post-resize, not the original-resolution image —
a deliberate choice for continuity with `FFTBranch`'s input, but see the
Known Confounds section: it also means downsampling/upsampling behavior
from wildly different native resolutions across sources becomes baked into
every one of these numbers (see `evidence_metrics_sourcewise.csv`'s
`between_source_resolution_confound_spearman` column).

## Family 1 — Global frequency irregularity

Computed via `np.fft.fft2` on the 224x224 grayscale frame (mirrors
`pipeline.py`'s `FFTBranch`'s `torch.fft.fft2` + `fftshift` + log-magnitude,
reimplemented in plain numpy for independence — see Process Notes on
avoiding circularity with the production model).

| Feature | Definition | Hypothesis | Strongest claim if it discriminates | Cannot support | Confounds |
|---|---|---|---|---|---|
| `freq_spectral_entropy` | Shannon entropy of the normalized power spectrum (power/sum(power)), log-normalized to [0,1] | GAN/diffusion upsampling and JPEG/re-encoding history can produce more "peaked" (less flat) spectra than natural sensor noise | "This evidence family's spectral flatness differs between real and this fake source" | Generalization to a generator never sampled; a claim about *which* frequency band differs (entropy is a summary over the whole spectrum) | Resolution (down/upsampling before the 224 resize changes the spectrum shape independent of authenticity); JPEG quality history of the original file before this pipeline re-encodes it |
| `freq_band_ratio_high_mid` | high-band energy / mid-band energy (bands = fractions of max radius 0.5–1.0 vs 0.15–0.5) | Some GAN upsampling paths leave characteristic checkerboard/high-frequency energy | Same as above, band-specific | Not a "GAN vs diffusion" discriminator per se — bands were fixed a priori, not tuned per generator | Same as above; also face size (more face detail concentrated in different bands depending on crop) |
| `freq_band_ratio_high_low` | high-band / low-band (0.02–0.15) energy | Same | Same | Same | Same |
| `freq_band_ratio_mid_low` | mid-band / low-band energy | Same | Same | Same | Same |
| `freq_high_energy_frac` | high-band energy / total energy | Direct high-frequency energy fraction, less ratio-noise-sensitive than the band ratios | Same | Same | Same |
| `freq_radial_powerlaw_slope` | slope of a linear fit to log(radial-avg power) vs log(radius), radii 2..max | Natural photos approximately follow a 1/f-like power-law falloff; synthetic images can deviate | "This source's radial falloff rate differs from real photos" | Deviation ≠ localization of an artifact; slope is a single global number | Resolution/native detail level shifts the effective falloff rate independent of authenticity |
| `freq_powerlaw_residual_std` | std of residuals (log_power − fitted line) across the same radii | How well a single power-law describes the spectrum; larger residual = more irregular/structured spectrum (e.g. periodic artifacts) | "This source's spectrum deviates more/less from a clean power-law than real photos" | Same | Same; also compression artifacts (JPEG blockiness itself is periodic and inflates residual) |
| `freq_logmag_mean` | mean of the log-magnitude spectrum (proxy for the same tensor `FFTBranch` feeds its CNN) | Overall spectral energy level differs with generation process and post-processing | "Global spectral energy level differs" | Not interpretable as "more/less fake", extremely resolution/compression sensitive | Very strongly confounded by resolution/upsampling |

**Family 1 verdict (see `evidence_candidate_decision_table.csv` for the
authoritative machine-checked rubric outcome):** ALL 8 features REJECTed —
every one flips sign (higher-in-fake for aiguard_unseen/stylegan2_ood/
midjourney but higher-in-real, or the reverse, for the 5 DF40 diffusion
methods). This is consistent with a resolution/rendering-pipeline artifact
rather than a "fake-ness" signal: DF40 methods share native resolution
256–1024px2 renders on a different pipeline than AIGuard/StyleGAN2/
MidJourney. Usable as a per-image score: **no**, not this round.

## Family 2 — Local texture / residual irregularity

Computed on the same 224x224 grayscale frame. Per the task's naming
requirement, none of these are called "texture artifact" — neutral names
only, until a candidate actually clears the decision-table bar (only
`tex_local_variance_std` did; see below).

| Feature | Definition | Hypothesis | Strongest claim if it discriminates | Cannot support | Confounds |
|---|---|---|---|---|---|
| `tex_local_variance_mean` | mean of a 5x5 sliding-window local variance map | Smoothing/rendering pipelines can produce systematically smoother or rougher local texture than camera sensor+skin texture | "Local texture roughness differs, on average, between real and this fake source" | Localization (this is a whole-frame mean); "smoothing artifact" specifically (not tested against ground-truth smoothing) | Resolution (upsampled sources have interpolation-smooth local texture baked in); face size (more/less skin area in frame) |
| `tex_local_variance_std` | std (across the frame) of that same local-variance map | Spatial *uniformity* of local roughness — a face with patchy texture (real skin pores, generator seams) has a different variance-of-variance than a uniformly rendered one | "This source's texture roughness is spatially more/less uniform than real photos" | Same as above | Same as above (this feature DID clear the bar — see confound discussion below, it is not confound-free, just below the CONDITIONAL-triggering bar this round) |
| `tex_lbp_entropy` | Shannon entropy of the uniform-LBP histogram (`skimage.feature.local_binary_pattern`, P=8, R=1) | Micro-pattern diversity | "LBP pattern diversity differs" | Anything about a specific artifact type | Resolution (LBP radius=1px is extremely resolution-sensitive after 224 resize) |
| `tex_lbp_uniformity` | sum of squared LBP histogram bin probabilities ("energy"/inverse of entropy) | Same, complementary framing | Same | Same | Same |
| `tex_glcm_contrast` | GLCM contrast (`skimage.feature.graycomatrix`/`graycoprops`, distance=1, 4 angles averaged, 32 gray levels, image downsized to 96x96 first) | Co-occurrence-based local contrast | "GLCM contrast differs" | Same | Same as LBP; also the 96x96 downsize adds another resolution-dependent step |
| `tex_glcm_homogeneity` | GLCM homogeneity | Same | Same | Same | Same |
| `tex_glcm_energy` | GLCM energy (angular second moment) | Same | Same | Same | Same |
| `tex_highpass_energy` | mean(abs(image − Gaussian-blur(image, sigma=2))) | Direct high-frequency residual energy, complementary to Family 1's global spectral view but spatial-domain | "High-frequency residual energy differs" | Same | Same |
| `tex_autocorr_peak_sharpness` | 2D autocorrelation of the high-pass residual: center-peak value / mean value in an annulus at radius 4–8px | Periodic/repetitive patterning (e.g. some generator upsampling artifacts) produces a flatter or secondary-peaked autocorrelation vs a natural residual's sharp single peak | "Autocorrelation peak shape differs for this source" | A "GAN checkerboard" claim specifically (never validated against a labeled checkerboard case) | Resolution very strongly (`between_source_resolution_confound_spearman`=0.63, the largest of any feature this round) |

**Family 2 verdict:** 7/9 features REJECTed (direction flips, same
AIGuard/StyleGAN2/MidJourney vs DF40 split as Family 1).
`tex_local_variance_std` is the ONLY feature in the entire round that
reached **ACCEPT_FOR_NEXT_STAGE** (direction-consistent, AUROC ≥0.60 — in
the higher-in-real direction, i.e. AUROC ≤0.40 for fake — on 6/8 fake
sources, within-source confound weak, between-source confound rho=−0.24,
below this round's 0.5 flag bar but not zero — see Known Confounds).
`tex_autocorr_peak_sharpness` is **CONDITIONAL**: direction-consistent
(higher-in-fake) but only clears the bar on 4/8 sources (aiguard_unseen,
stylegan2_ood, df40_ddim, midjourney), and its between-source resolution
confound (rho=0.63) is the strongest measured this round — treat any
"this source has more periodic patterning" claim from this feature as
resolution-contaminated until controlled.

## Family 3 — Landmark geometry anomaly

Computed from MediaPipe FaceLandmarker on the same 224x224 frame (reusing
`generate_landmark_gt.py`'s landmarker setup/singleton pattern). **Mandatory
confound framing per the task spec**: real sources (celeba_test/lfw) and
several fake sources (StyleGAN2/DF40/MidJourney) were never photographed in
the same pose/framing distribution — any geometry gap could be a pose or
crop-convention gap between sources, not a fakeness signal. This is why
every one of these features REJECTed in the decision table: no candidate
survived direction-consistency across sources, which is exactly what you'd
expect if pose/framing convention differences (not fakeness) drive the
gaps, since different fake sources have different framing conventions
relative to celeba/lfw in different directions.

| Feature | Definition | Hypothesis | Strongest claim if it discriminates | Cannot support | Confounds |
|---|---|---|---|---|---|
| `lm_symmetry_score` | mean, over 6 bilateral landmark pairs (eye outer/inner corners, mouth corners, brow points), of \|dist(left, midline) − dist(right, midline)\|, normalized by face width | Some generation/manipulation pipelines can leave subtle bilateral asymmetry beyond natural human asymmetry | "Bilateral symmetry differs for this source" | Any claim isolated from pose — yaw alone produces large apparent asymmetry (this is why `lm_pose_yaw_proxy` correlation is reported alongside) | Pose (yaw) is the dominant confound by construction; framing convention |
| `lm_interocular_over_facewidth` | interocular distance / detected face-bbox width | Standard facial proportion ratio; generation pipelines sometimes shift proportions from population norms | "Proportion ratio differs on average" | Individual identity (real human proportions vary naturally over a wide range — this was never checked against real population variance) | Face bbox itself is landmark-derived, not an independent measurement — partially circular; crop convention |
| `lm_mouthwidth_over_interocular` | mouth width / interocular distance | Same | Same | Same | Same |
| `lm_pose_yaw_proxy` | (nose-tip x − bbox-center x) / (face-width/2) | Rough proxy for yaw, used here specifically to test whether OTHER geometry features are just tracking pose | Diagnostic only — not proposed as a fakeness signal itself | Anything about fakeness (this is a confound-control variable, not a candidate) | By definition confounded with true pose; also affected by asymmetric cropping |

**Family 3 verdict:** all 4 REJECTed. `evidence_metrics_sourcewise.csv`'s
correlation-with-pose-proxy analysis (see below) supports the pose/framing
confound reading rather than a genuine geometry-anomaly signal existing and
being masked.

## Family 4 — Facial boundary / transition anomaly

Ring just outside (ellipse-distance 1.0–1.25x the landmark bbox semi-axes)
vs just inside (0.85–1.0x) the detected face-oval boundary, in the same
224x224 frame. **Per-image availability check (not per-source blanket
assumption, as required):** a row is `NaN` (`NOT_AVAILABLE` for that image)
whenever the landmark bbox comes within 10px of the frame edge on any side
(`boundary_margin_px` column in `raw_features.csv`) — this affects
1.2%–45.5% of images depending on source (worst: df40_sd21 45%, df40_pixart
35.6%, aiguard_unseen_real 34.3%; best: df40_dit/lfw 0%). No source was
found tight enough on every image to warrant a full-source NOT_AVAILABLE
blanket flag, so all 8 fake sources have a usable subset for this family
(see `n_fake`/`n_real` per row in `evidence_metrics_sourcewise.csv`).

| Feature | Definition | Hypothesis | Strongest claim if it discriminates | Cannot support | Confounds |
|---|---|---|---|---|---|
| `bnd_boundary_edge_contrast` | mean Sobel gradient magnitude within the inner+outer ring band | Face-composited/blended manipulations can leave a sharper or softer transition than an unedited photo's natural hairline/jaw edge | "Boundary edge sharpness differs for this source" | Localization to a specific splice boundary (there is no ground-truth mask this round to confirm this IS a splice edge vs just hair/background texture) | Whether the crop even includes background at all (df40_sd21/pixart approach the 10px-margin cutoff most often); hair color/style variety between sources |
| `bnd_ring_texture_diff` | \|std(inner ring pixels) − std(outer ring pixels)\| | Texture-statistic discontinuity across the boundary | Same | Same | Same |
| `bnd_ring_mean_diff` | \|mean(inner ring pixels) − mean(outer ring pixels)\| | Brightness/color discontinuity across the boundary (skin-to-hair/background) | Same | Same | Same |

**Family 4 verdict:** all 3 REJECTed (direction flips across sources).

## Family 5 — Reconstruction-based anomaly

**NOT_AVAILABLE this round.** `Glob` search of the repo for
autoencoder/denoise/VAE-related files found none suitable (only the
unrelated `mobile_fft.py` DFT-matrix work and standard classifier
checkpoints) — per task instructions, no external pretrained model was
fetched to fill this gap.

Proposed follow-up (not implemented): train or acquire a lightweight
autoencoder/denoiser on a REAL-only face corpus (e.g. LFW + CelebA train
split, disjoint from any eval set used here) at 224x224, then measure
per-image reconstruction error (pixel L1/L2, or a perceptual/LPIPS-style
distance if a pretrained perceptual net already exists in the env) on held-
out real vs the fake sources used this round. The hypothesis: an
autoencoder trained only on real faces should reconstruct real faces more
faithfully than faces containing generator-specific statistics it never
saw, giving a per-image anomaly score independent of the frequency/texture
families above (since it's data-driven rather than hand-specified). This
was explicitly out of scope this round (no model training permitted) and
would need its own leakage/generalization audit before being trusted — a
reconstruction model trained on LFW might just re-discover the same
resolution confound found in Families 1–2 if the real training corpus and
fake eval corpus differ in native resolution, so any future run of this
family MUST resolution-match its training/eval samples from the start,
unlike this round's hand-features (which could only be assessed for
confound after the fact).

## Known confounds observed across ALL families this round (cross-cutting)

1. **Between-source native resolution**: celeba_test (178x218) and lfw
   (250x250) are systematically lower native resolution than every fake
   source sampled (stylegan2/df40_dit/df40_sit=256x256, df40_sd21=512x512,
   df40_pixart/midjourney=1024x1024; aiguard_unseen ≈252px and
   aiguard_unseen_real ≈1036px median are the only sources with real
   within-source resolution variance). Every family/feature was checked for
   this via `between_source_resolution_confound_spearman`
   (`evidence_metrics_sourcewise.csv`), computed as the Spearman correlation
   between each of the 11 sources' MEDIAN feature value and that source's
   log(native resolution). `tex_autocorr_peak_sharpness` (0.63) and
   `lm_symmetry_score` (−0.76, already REJECTed on direction-inconsistency
   grounds) are the most resolution-entangled features measured.
2. **AIGuard_unseen / StyleGAN2 / MidJourney vs DF40-diffusion split**: the
   single most consistent pattern in `evidence_metrics_sourcewise.csv` and
   `figures/heatmap_auroc.png` is NOT a real-vs-fake split but a
   generator-family split — most Family 1/2 features point one direction
   for {aiguard_unseen, stylegan2_ood, midjourney} and the opposite
   direction for {df40_dit, df40_sit, df40_ddim, df40_pixart, df40_sd21}.
   This is exactly the direction-inconsistency pattern the decision rubric
   is designed to catch, and it is most parsimoniously explained by shared
   rendering/resolution/compression pipeline within each cluster rather
   than a "fake" vs "real" signal.
3. **Pose/framing convention**: real sources (celeba/lfw, frontal
   studio-ish portraits with hair+background visible) vs fake sources
   (StyleGAN2/DF40 crops, tighter face-only) differ systematically in
   framing. This is the primary suspected driver of Family 3's total
   rejection.
