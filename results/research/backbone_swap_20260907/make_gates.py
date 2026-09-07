"""Derive a full Freeze-Gate harness for the MobileNetV4 flat three-way checkpoint from
flat3class_revisit_20260828/eval_flat3_gates.py. Deltas: round name, an --arch flag, and the
spatial branch built per arch (same timm model as every other MobileNetV4 result). Run once.
ASCII-only prints.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "flat3class_revisit_20260828" / "eval_flat3_gates.py"
s = SRC.read_text(encoding="utf-8")
s = s.replace('"flat3class_revisit_20260828"', '"backbone_swap_20260907"')

old = '''class DualBranchModel(nn.Module):
    """ShuffleNetV2 spatial branch (production architecture)."""
    def __init__(self, num_classes=2):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        self.spatial_branch = bb; self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
new = '''ARCH = "shufflenet"   # set from --arch in main(); read when models are built


def _build_spatial(arch):
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k", pretrained=False, num_classes=0)
    m.eval()
    with torch.no_grad():
        dim = m(torch.zeros(2, 3, 224, 224)).shape[1]
    return m, int(dim)


class DualBranchModel(nn.Module):
    """Spatial branch per ARCH (ShuffleNetV2 = production; MobileNetV4 = backbone_swap)."""
    def __init__(self, num_classes=2):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(ARCH)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))'''
assert old in s, "model block not found"
s = s.replace(old, new)

old_arg = '    ap.add_argument("--flat3", help="flat 3-class checkpoint (mutually exclusive with --layer1/--layer2)")'
new_arg = old_arg + '\n    ap.add_argument("--arch", default="shufflenet", choices=["shufflenet", "mobilenetv4"])'
assert old_arg in s
s = s.replace(old_arg, new_arg)

old_parse = "    a = ap.parse_args()\n"
assert s.count(old_parse) == 1
s = s.replace(old_parse, old_parse + "    global ARCH\n    ARCH = a.arch\n")

(HERE / "eval_gates_flat3.py").write_text(s, encoding="utf-8")
print("eval_gates_flat3.py written")
