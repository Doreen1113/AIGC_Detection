import torch
import torch.nn as nn
import torchvision.models as tv_models


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(4),
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, out_dim),
            nn.ReLU(),
        )

    def forward(self, x):
        fft = torch.fft.fft2(x, norm="ortho")
        fft = torch.fft.fftshift(fft, dim=(-2, -1))
        mag = torch.log(torch.abs(fft) + 1e-8)
        return self.net(mag)


class MultiGranularityAttention(nn.Module):
    """
    Lightweight MAM v1.

    The module learns local, mid-range, and global attention from the final
    ShuffleNetV2 feature map, then gates the spatial feature before pooling.
    """
    def __init__(self, channels=1024, reduction=4):
        super().__init__()
        hidden = max(channels // reduction, 64)
        self.local = nn.Sequential(
            nn.Conv2d(channels, hidden, kernel_size=1),
            nn.BatchNorm2d(hidden),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, hidden, kernel_size=3, padding=1, groups=hidden),
            nn.BatchNorm2d(hidden),
            nn.ReLU(inplace=True),
        )
        self.context = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(channels, hidden, kernel_size=1),
            nn.ReLU(inplace=True),
        )
        self.mask_head = nn.Sequential(
            nn.Conv2d(hidden * 2, hidden, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, 1, kernel_size=1),
            nn.Sigmoid(),
        )

    def forward(self, feat):
        local_feat = self.local(feat)
        context_feat = self.context(feat).expand_as(local_feat)
        attn = self.mask_head(torch.cat([local_feat, context_feat], dim=1))
        return feat * (1.0 + attn), attn


class ShuffleNetMAMBranch(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()
        weights = (
            tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT
            if pretrained else None
        )
        backbone = tv_models.shufflenet_v2_x1_0(weights=weights)
        self.conv1 = backbone.conv1
        self.maxpool = backbone.maxpool
        self.stage2 = backbone.stage2
        self.stage3 = backbone.stage3
        self.stage4 = backbone.stage4
        self.conv5 = backbone.conv5
        self.mam = MultiGranularityAttention(channels=1024)
        self.pool = nn.AdaptiveAvgPool2d(1)

    def forward(self, x):
        x = self.conv1(x)
        x = self.maxpool(x)
        x = self.stage2(x)
        x = self.stage3(x)
        x = self.stage4(x)
        feat = self.conv5(x)
        attended, attn = self.mam(feat)
        pooled = self.pool(attended).flatten(1)
        return pooled, attn


class DualBranchMAMModel(nn.Module):
    def __init__(self, num_classes=3, pretrained=True):
        super().__init__()
        self.spatial_branch = ShuffleNetMAMBranch(pretrained=pretrained)
        self.fft_branch = FFTBranch(out_dim=256)
        self.classifier = nn.Sequential(
            nn.Linear(1024 + 256, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )
        self.last_attention = None

    def forward_with_attention(self, x):
        spatial, attn = self.spatial_branch(x)
        freq = self.fft_branch(x)
        logits = self.classifier(torch.cat([spatial, freq], dim=1))
        self.last_attention = attn
        return logits, attn

    def forward(self, x):
        logits, _ = self.forward_with_attention(x)
        return logits

