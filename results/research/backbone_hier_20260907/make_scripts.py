"""Hierarchical MobileNetV4 stack (Layer1 real-vs-manipulated + Layer2 fake-vs-filter), the
architecture that production v8.17 actually uses, so the backbone swap is judged with the
production decision rule and the full Freeze-Gate battery -- not the flat three-way proxy.

Derives three scripts from existing, audited rounds; deltas are the round name, an --arch flag,
the spatial branch per arch, and ImageNet init for MobileNetV4 (a ShuffleNetV2 checkpoint cannot
warm-start it). Data = the v8.11/v8.17 production splits (no FF++), so the ONLY change against
the production lineage is the backbone. Run once. ASCII-only prints.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = "backbone_hier_20260907"
SPATIAL = '''def _build_spatial(arch, pretrained=True):
    """ShuffleNetV2 (production) or MobileNetV4 (timm mobilenetv4_conv_small.e2400_r224_in1k,
    the same model benchmarked on FF++/cross-dataset). Output width measured by a forward pass."""
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT if pretrained else None)
        bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k", pretrained=pretrained, num_classes=0)
    m.eval()
    with torch.no_grad():
        dim = m(torch.zeros(2, 3, 224, 224)).shape[1]
    return m, int(dim)


'''

# ----------------------------------------------------------------- Layer1 trainer
s = (HERE.parent / "p1a1_interference_20260905" / "train_interference_layer1.py").read_text(encoding="utf-8")
s = s.replace('ROUND = "p1a1_interference_20260905"', f'ROUND = "{ROUND}"')
s = s.replace('TRAIN_SPLIT = BASE / "results" / "research" / "filter_video_20260906" / "layer1_VIDFILT_train.txt"',
              'TRAIN_SPLIT = BASE / "splits" / "v811_layer1_train.txt"')
s = s.replace('TRAIN_SPLIT = BASE / "splits" / "research" / "production_candidate_v2_20260823" / "layer1_pcand_v2b_train.txt"',
              'TRAIN_SPLIT = BASE / "splits" / "v811_layer1_train.txt"')
old = '''class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
new = SPATIAL + '''class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2, arch="shufflenet"):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(arch)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
assert old in s, "L1 model block"
s = s.replace(old, new)
s = s.replace('ap.add_argument("--arm", required=True, choices=["LWF", "FAM3", "L2SP"])',
              'ap.add_argument("--arm", required=True, choices=["LWF", "FAM3", "L2SP", "BASE"])\n'
              '    ap.add_argument("--arch", default="shufflenet", choices=["shufflenet", "mobilenetv4"])')
# BASE arm = plain 2-class production recipe, ImageNet init when the backbone changes
s = s.replace('''    prod_sd = torch.load(INIT_WEIGHTS, map_location=device)
    model = DualBranchModel(n_cls).to(device)
    model.load_state_dict(build_fam3_from_prod(prod_sd) if a.arm == "FAM3" else prod_sd)''',
'''    model = DualBranchModel(n_cls, a.arch).to(device)
    if a.arch == "shufflenet":
        prod_sd = torch.load(INIT_WEIGHTS, map_location=device)
        model.load_state_dict(build_fam3_from_prod(prod_sd) if a.arm == "FAM3" else prod_sd)
    else:
        prod_sd = None   # MobileNetV4: ImageNet-initialised spatial branch, fresh FFT branch and head
        print(f"[{tag}] arch={a.arch}: no production warm start (ImageNet init)", flush=True)''')
assert "ImageNet init" in s
s = s.replace('        teacher = DualBranchModel(2).to(device); teacher.load_state_dict(prod_sd); teacher.eval()',
              '        teacher = DualBranchModel(2, a.arch).to(device); teacher.load_state_dict(prod_sd); teacher.eval()')
s = s.replace('best_path = CKPT_DIR / f"layer1_interf_{tag}.pth"', 'best_path = CKPT_DIR / f"layer1_{tag}_{a.arch}.pth"')
s = s.replace('last_path = CKPT_DIR / f"layer1_interf_{tag}_last.pth"', 'last_path = CKPT_DIR / f"layer1_{tag}_{a.arch}_last.pth"')
(HERE / "train_l1.py").write_text(s, encoding="utf-8"); print("train_l1.py")

# ----------------------------------------------------------------- Layer2 trainer
t = (HERE.parent / "removal_ablation_20260904" / "train_layer2_arm.py").read_text(encoding="utf-8")
t = t.replace('"removal_ablation_20260904"', f'"{ROUND}"')
t = t.replace('ARM_CLASSES = dict(CTRL=2, REMOVE=2, DOWNWEIGHT=2, RELABEL3=3)', 'ARM_CLASSES = dict(BASE=2)')
t = t.replace('    TRAIN_SPLIT = ROUND / f"layer2_{ARM}_train.txt"', '    TRAIN_SPLIT = BASE / "splits" / "v811_layer2_train.txt"')
old2 = '''class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes)
        )'''
if old2 not in t:
    c2 = re.findall(r"class DualBranchModel\(nn\.Module\):\n(?:.*\n){1,10}?.*nn\.Linear\(512, num_classes\)\)", t)
    assert c2, "L2 model block"
    old2 = c2[0]
t = t.replace(old2, new)
t = t.replace('    ap.add_argument("--workers", type=int, default=8)',
              '    ap.add_argument("--workers", type=int, default=8)\n'
              '    ap.add_argument("--arch", default="shufflenet", choices=["shufflenet", "mobilenetv4"])')
t = t.replace('WEIGHTS_PATH = str(CKPT_DIR / f"shufflenet_v2_layer2_{ARM}_s{SEED}.pth")',
              'WEIGHTS_PATH = str(CKPT_DIR / f"layer2_{ARM}_{a.arch}_s{SEED}.pth")')
# model construction + warm start
assert "model = DualBranchModel(num_classes=NUM_CLASSES).to(device)" in t, "L2 ctor"
t = t.replace("model = DualBranchModel(num_classes=NUM_CLASSES).to(device)",
              "model = DualBranchModel(num_classes=NUM_CLASSES, arch=a.arch).to(device)")
old_ws = "    init_state = torch.load(INIT_WEIGHTS, map_location=device)"
assert old_ws in t
t = t.replace(old_ws, "    init_state = torch.load(INIT_WEIGHTS, map_location=device) if a.arch == \"shufflenet\" else {}")
(HERE / "train_l2.py").write_text(t, encoding="utf-8"); print("train_l2.py")

# ----------------------------------------------------------------- gate harness (2-class L1 + 2-class L2)
e = (HERE.parent / "p1a1_interference_20260905" / "eval_gates.py").read_text(encoding="utf-8")
e = e.replace('"p1a1_interference_20260905"', f'"{ROUND}"')
old_e = '''class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
if old_e not in e:
    # some harness copies build the backbone with weights="IMAGENET1K_V1" or DEFAULT
    cands = [c for c in re.findall(r"class DualBranchModel\(nn\.Module\):\n(?:.*\n){1,9}?.*nn\.Linear\(512, num_classes\)\)", e)]
    assert cands, "eval model block"
    old_e = cands[0]
e = e.replace(old_e, SPATIAL.replace("pretrained=True", "pretrained=False") + '''class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2, arch="shufflenet"):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(arch, pretrained=False)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))''')
e = e.replace('ap.add_argument("--layer1-backbone", default="shufflenet", choices=["shufflenet", "repvit", "proto"])',
              'ap.add_argument("--layer1-backbone", default="shufflenet", choices=["shufflenet", "repvit", "proto", "mobilenetv4"])')
e = e.replace('ap.add_argument("--layer2-backbone", default="shufflenet", choices=["shufflenet", "repvit"])',
              'ap.add_argument("--layer2-backbone", default="shufflenet", choices=["shufflenet", "repvit", "mobilenetv4"])')
e = e.replace("        self.l1 = L1Cls(self.l1_classes).to(device)",
              "        self.l1 = (DualBranchModel(self.l1_classes, l1_backbone) if l1_backbone == \"mobilenetv4\" else L1Cls(self.l1_classes)).to(device)")
e = e.replace("            self.l2 = L2Cls(2).to(device)",
              "            self.l2 = (DualBranchModel(2, l2_backbone) if l2_backbone == \"mobilenetv4\" else L2Cls(2)).to(device)")
assert e.count("mobilenetv4") >= 4, "eval patches"
(HERE / "eval_gates.py").write_text(e, encoding="utf-8"); print("eval_gates.py")
# 2026-09-07 post-hoc fix (applied by sed to eval_gates.py after the first gate run failed to load L2):
# the interference harness builds L2 as `self.l2 = L2Cls(3 if l2_type == "threeclass" else 2).to(device)`,
# which the replacement above did not match; L2 is now built as DualBranchModel(n, l2_backbone) when
# l2_backbone == "mobilenetv4".
