"""Derive this round's trainer and evaluator from ternary_necessity_20260906.

Deltas, and only these:
  1. round name -> backbone_swap_20260907
  2. --arch {shufflenet,mobilenetv4}; mobilenetv4 comes from timm via train_ffpp_improve's
     build_backbone, so the spatial branch is exactly the one benchmarked on FF++.
  3. the FFT branch, fusion width, classifier head, recipe and seed are untouched.
Run once. ASCII-only prints.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "ternary_necessity_20260906"

# ---------------------------------------------------------------- trainer
s = (SRC / "train_arm.py").read_text(encoding="utf-8")
s = s.replace('"ternary_necessity_20260906"', '"backbone_swap_20260907"')
s = s.replace('ap.add_argument("--arm", required=True, choices=["BIN_N", "BIN_R", "BIN_F", "TERN"])',
              'ap.add_argument("--arm", required=True, choices=["BIN_N", "BIN_R", "BIN_F", "TERN"])\n'
              '    ap.add_argument("--arch", default="shufflenet", choices=["shufflenet", "mobilenetv4"])')

old_model = '''class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights="IMAGENET1K_V1")
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
new_model = '''def _build_spatial(arch, pretrained=True):
    """Same spatial backbones as AIGuard/train_ffpp_improve.py, so the MobileNetV4 branch is
    exactly the one benchmarked on FF++ and cross-dataset (timm
    mobilenetv4_conv_small.e2400_r224_in1k, 960-d features)."""
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights="IMAGENET1K_V1" if pretrained else None)
        bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k",
                          pretrained=pretrained, num_classes=0)
    m.eval()
    with torch.no_grad():                     # num_features is the pre-head width (960);
        dim = m(torch.zeros(2, 3, 224, 224)).shape[1]   # the forward output is 1280
    return m, int(dim)


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3, arch="shufflenet"):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(arch)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
assert old_model in s, "trainer model block not found"
s = s.replace(old_model, new_model)
s = s.replace("model = DualBranchModel(NC).to(device)", "model = DualBranchModel(NC, a.arch).to(device)")

# a MobileNetV4 spatial branch cannot load the ShuffleNetV2 warm start
old_ws = '''    sd = torch.load(WARMSTART, map_location=device)'''
new_ws = '''    sd = torch.load(WARMSTART, map_location=device) if a.arch == "shufflenet" else {}'''
assert old_ws in s
s = s.replace(old_ws, new_ws)
s = s.replace('CKPT_DIR / f"tern_{a.arm}_seed{a.seed}.pth"',
              'CKPT_DIR / f"tern_{a.arm}_{a.arch}_seed{a.seed}.pth"')
(HERE / "train_arm.py").write_text(s, encoding="utf-8")
print("train_arm.py written")

# ---------------------------------------------------------------- evaluator
e = (SRC / "eval_frontier.py").read_text(encoding="utf-8")
e = e.replace('"ternary_necessity_20260906"', '"backbone_swap_20260907"')
e = e.replace('ARMS = ["BIN_N", "BIN_R", "BIN_F", "TERN"]', 'ARMS = ["TERN_MNV4"]')
e = e.replace('BASELINES = ["univfd", "npr", "sbi", "xception", "effnb4", "spsl", "f3net", "ucf", "recce", "core", "srm"]',
              'BASELINES = []   # the control comes from the necessity round, re-used verbatim')
e = e.replace('''    ck = CKPT / f"tern_{arm}_seed{SEED}.pth"''',
              '''    ck = CKPT / f"tern_TERN_mobilenetv4_seed{SEED}.pth"''')
old_build = '''    m = DualBranchModel(nc).to(device); m.load_state_dict(sd); m.eval()'''
new_build = '''    m = DualBranchModel(nc, "mobilenetv4").to(device); m.load_state_dict(sd); m.eval()'''
assert old_build in e
e = e.replace(old_build, new_build)
old_cls = '''class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
new_cls = '''def _build_spatial(arch):
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k",
                          pretrained=False, num_classes=0)
    return m, int(m.num_features)


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3, arch="shufflenet"):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(arch)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
assert old_cls in e
e = e.replace(old_cls, new_cls)
(HERE / "eval_frontier.py").write_text(e, encoding="utf-8")
print("eval_frontier.py written")
