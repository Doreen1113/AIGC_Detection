# Browser demo (GitHub Pages)

Runs the full production stack (Layer1 v8.17 → Layer2 v8.11 → artifact head v6) **entirely in the
browser** with ONNX Runtime Web (WASM). No server, no upload — the photo never leaves the device.

- `index.html` — UI + inference (mirrors `decision_rule.decide`, JPEG q85 round-trip, 224×224).
- `models/` — four ONNX files (33 MB fp32): Layer1, Layer2, artifact-type head, patch evidence head. The DFT is baked in as constant MatMuls, so no FFT op.
- Buttons: **Load models → Analyse a face photo** (verdict, decision trace, 7x7 evidence overlay + region ranking, structured explanation text mirrored verbatim from `pipeline.py`) and **Latency benchmark** (per-stage latency on *this* device).

## Publishing
Repository Settings → Pages → Source: *Deploy from a branch*, branch `main` (or `dev`), folder
`/docs`. The page then lives at `https://<user>.github.io/<repo>/demo/`.

## Known limits of the public page
- GitHub Pages cannot send the `Cross-Origin-Opener-Policy`/`Embedder-Policy` headers, so WASM runs
  **single-threaded** — latency on Pages is an upper bound versus the `serve.py` local host.
- No MediaPipe face gate on the web path (the Android app has it); crop the face yourself.
- Reported latency is the browser's; it is not the TFLite number in the paper.
