"""
Ablation training script. Fine-tunes from v3, same setting as v5 (no JPEG aug).
Usage:
  python AIGuard/train_ablation.py --split ablation_a_real_fake --tag ablation_a
  python AIGuard/train_ablation.py --split ablation_b_real_fake --tag ablation_b
"""
import os, random, argparse, numpy as np
from pathlib import Path
from collections import Counter

import torch, torch.nn as nn
import torchvision.models as tv_models
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.metrics import f1_score, accuracy_score
from PIL import Image

BASE         = Path(r"C:\My_Project\AIGC")
SPLITS       = BASE / "splits"
INIT_WEIGHTS = str(BASE / "shufflenet_v2_3class_ffhq_v3.pth")
CLASSES      = ["real", "fake", "filter"]
EPOCHS       = 20
BATCH_SIZE   = 256
MIXUP_ALPHA  = 0.2
LR           = 5e-4

transform_train = transforms.Compose([
    transforms.Resize((224,224)), transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2,contrast=0.2,saturation=0.2),
    transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(), transforms.Normalize([0.5]*3,[0.5]*3)])
transform_val = transforms.Compose([
    transforms.Resize((224,224)), transforms.ToTensor(), transforms.Normalize([0.5]*3,[0.5]*3)])

class FaceDataset(Dataset):
    def __init__(self,paths,labels,transform=None):
        self.paths,self.labels,self.transform=paths,labels,transform
    def __len__(self): return len(self.paths)
    def __getitem__(self,idx):
        img=Image.open(self.paths[idx]).convert("RGB")
        if self.transform: img=self.transform(img)
        return img,self.labels[idx]

def load_split(txt_path):
    paths,labels=[],[]
    for line in Path(txt_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("path\t"): continue
        parts=line.split("\t")
        if len(parts)>=2: paths.append(parts[0]); labels.append(int(parts[1]))
    return paths,labels

class FFTBranch(nn.Module):
    def __init__(self,d=256):
        super().__init__()
        self.net=nn.Sequential(
            nn.Conv2d(3,32,3,padding=1),nn.BatchNorm2d(32),nn.ReLU(),nn.MaxPool2d(4),
            nn.Conv2d(32,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1),nn.BatchNorm2d(128),nn.ReLU(),nn.AdaptiveAvgPool2d(4),
            nn.Flatten(),nn.Linear(128*4*4,d),nn.ReLU())
    def forward(self,x):
        fft=torch.fft.fft2(x,norm='ortho'); fft=torch.fft.fftshift(fft,dim=(-2,-1))
        return self.net(torch.log(torch.abs(fft)+1e-8))

class DualBranchModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb=tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT); bb.fc=nn.Identity()
        self.spatial_branch=bb; self.fft_branch=FFTBranch(256)
        self.classifier=nn.Sequential(nn.Linear(1280,512),nn.ReLU(),nn.Dropout(0.3),nn.Linear(512,3))
    def forward(self,x): return self.classifier(torch.cat([self.spatial_branch(x),self.fft_branch(x)],dim=1))

def mixup_batch(x,y,alpha=0.2):
    lam=np.random.beta(alpha,alpha) if alpha>0 else 1.0
    idx=torch.randperm(x.size(0),device=x.device)
    return lam*x+(1-lam)*x[idx],y,y[idx],lam

def mixup_loss(c,logits,ya,yb,lam): return lam*c(logits,ya)+(1-lam)*c(logits,yb)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument("--split", required=True)
    parser.add_argument("--tag",   required=True)
    args=parser.parse_args()

    device='cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device} | Split: {args.split} | Tag: {args.tag}")

    tr_rf_p,tr_rf_l=load_split(SPLITS/f"{args.split}.txt")
    va_rf_p,va_rf_l=load_split(SPLITS/"val_real_fake.txt")
    tr_ft_p,tr_ft_l=load_split(SPLITS/"train_filter.txt")
    va_ft_p,va_ft_l=load_split(SPLITS/"val_filter.txt")

    tr_p=tr_rf_p+tr_ft_p; tr_l=tr_rf_l+tr_ft_l
    va_p=va_rf_p+va_ft_p; va_l=va_rf_l+va_ft_l
    tc=Counter(tr_l)
    print(f"Train: {len(tr_p)}  real={tc[0]} fake={tc[1]} filter={tc[2]}")

    train_ds=FaceDataset(tr_p,tr_l,transform_train)
    val_ds  =FaceDataset(va_p,va_l,transform_val)
    train_loader=DataLoader(train_ds,batch_size=BATCH_SIZE,shuffle=True, num_workers=8,pin_memory=True)
    val_loader  =DataLoader(val_ds,  batch_size=BATCH_SIZE,shuffle=False,num_workers=8,pin_memory=True)

    total=len(tr_l); auto_w=[total/(len(CLASSES)*tc[i]) for i in range(3)]
    auto_w[2]=min(auto_w[2],0.4)
    class_weights=torch.tensor(auto_w,dtype=torch.float).to(device)

    model=DualBranchModel().to(device)
    model.load_state_dict(torch.load(INIT_WEIGHTS,map_location=device))
    print(f"Init from v3 weights")

    optimizer=torch.optim.Adam(model.parameters(),lr=LR)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=EPOCHS)
    criterion=nn.CrossEntropyLoss(weight=class_weights,label_smoothing=0.1)

    ckpt_path=str(BASE/f"shufflenet_v2_3class_{args.tag}.pth")
    best_f1=0.0

    for epoch in range(1,EPOCHS+1):
        model.train(); total_loss=0.0
        for imgs,labels in train_loader:
            imgs,labels=imgs.to(device),labels.to(device); optimizer.zero_grad()
            if random.random()<0.5:
                imgs_m,ya,yb,lam=mixup_batch(imgs,labels,MIXUP_ALPHA)
                loss=mixup_loss(criterion,model(imgs_m),ya,yb,lam)
            else: loss=criterion(model(imgs),labels)
            loss.backward(); optimizer.step(); total_loss+=loss.item()*imgs.size(0)
        scheduler.step()

        model.eval(); preds,trues=[],[]
        with torch.no_grad():
            for imgs,labels in val_loader:
                preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
                trues.extend(labels.tolist())
        f1=f1_score(trues,preds,average='macro')
        f1p=f1_score(trues,preds,average=None)
        print(f"[{epoch:02d}/{EPOCHS}] loss={total_loss/len(train_ds):.4f}  F1={f1:.4f}  "
              f"[real={f1p[0]:.3f} fake={f1p[1]:.3f} filter={f1p[2]:.3f}]")
        if f1>best_f1: best_f1=f1; torch.save(model.state_dict(),ckpt_path); print(f"  -> Saved")

    print(f"\nBest F1={best_f1:.4f}  Weights: {ckpt_path}")
