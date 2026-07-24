"""
v8.2: v79 base + Celeb-DF-v2 real 4,711 (H.264 video-compressed real faces).

Goal: fix WildDeepfake real=0/400 by teaching model that video-compressed
faces can be real, while maintaining static test performance.

Changes vs v8.1:
  - Real split: v82_train_real_fake.txt (real=92,602: v79 87,891 + CelebDF 4,711)
  - Filter split: v8_train_filter.txt (190,771)  unchanged
  - Init from v8.1, LR=3e-5, 10 epochs

python AIGuard/train_v82.py
"""
import os, random, numpy as np
from pathlib import Path
from collections import Counter
import torch, torch.nn as nn
import torchvision.models as tv_models
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.metrics import f1_score, accuracy_score, classification_report, confusion_matrix
from PIL import Image

BASE         = Path(r"C:\My_Project\AIGC")
SPLITS       = BASE / "splits"
INIT_WEIGHTS = str(BASE / "shufflenet_v2_3class_v81.pth")
WEIGHTS_PATH = str(BASE / "shufflenet_v2_3class_v82.pth")
CLASSES = ["real", "fake", "filter"]
EPOCHS = 10; BATCH_SIZE = 256; MIXUP_ALPHA = 0.2; LR = 3e-5

transform_train = transforms.Compose([
    transforms.Resize((224,224)), transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.2,0.2,0.2), transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(), transforms.Normalize([0.5]*3,[0.5]*3)])
transform_val = transforms.Compose([
    transforms.Resize((224,224)), transforms.ToTensor(), transforms.Normalize([0.5]*3,[0.5]*3)])

class FaceDataset(Dataset):
    def __init__(self,paths,labels,transform=None): self.paths,self.labels,self.transform=paths,labels,transform
    def __len__(self): return len(self.paths)
    def __getitem__(self,idx):
        img=Image.open(self.paths[idx]).convert("RGB")
        if self.transform: img=self.transform(img)
        return img,self.labels[idx]

def load_split(p):
    paths,labels=[],[]
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.startswith("path\t"): continue
        parts=line.split("\t")
        if len(parts)>=2: paths.append(parts[0]); labels.append(int(parts[1]))
    return paths,labels

class FFTBranch(nn.Module):
    def __init__(self,out_dim=256):
        super().__init__()
        self.net=nn.Sequential(
            nn.Conv2d(3,32,3,padding=1),nn.BatchNorm2d(32),nn.ReLU(),nn.MaxPool2d(4),
            nn.Conv2d(32,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1),nn.BatchNorm2d(128),nn.ReLU(),nn.AdaptiveAvgPool2d(4),
            nn.Flatten(),nn.Linear(128*16,out_dim),nn.ReLU())
    def forward(self,x):
        f=torch.fft.fft2(x,norm='ortho'); f=torch.fft.fftshift(f,dim=(-2,-1))
        return self.net(torch.log(torch.abs(f)+1e-8))

class DualBranchModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb=tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        bb.fc=nn.Identity(); self.spatial_branch=bb
        self.fft_branch=FFTBranch(256)
        self.classifier=nn.Sequential(nn.Linear(1280,512),nn.ReLU(),nn.Dropout(0.3),nn.Linear(512,3))
    def forward(self,x): return self.classifier(torch.cat([self.spatial_branch(x),self.fft_branch(x)],1))

def mixup_batch(x,y,alpha=0.2):
    lam=np.random.beta(alpha,alpha) if alpha>0 else 1.0
    idx=torch.randperm(x.size(0),device=x.device)
    return lam*x+(1-lam)*x[idx],y,y[idx],lam
def mixup_loss(crit,logits,ya,yb,lam): return lam*crit(logits,ya)+(1-lam)*crit(logits,yb)

if __name__=="__main__":
    device="cuda" if torch.cuda.is_available() else "cpu"; print(f"Device: {device}")
    tr_rf_p,tr_rf_l=load_split(SPLITS/"v82_train_real_fake.txt")
    va_rf_p,va_rf_l=load_split(SPLITS/"v6_val_real_fake.txt")
    tr_ft_p,tr_ft_l=load_split(SPLITS/"v8_train_filter.txt")
    va_ft_p,va_ft_l=load_split(SPLITS/"val_filter.txt")
    tr_p=tr_rf_p+tr_ft_p; tr_l=tr_rf_l+tr_ft_l
    va_p=va_rf_p+va_ft_p; va_l=va_rf_l+va_ft_l
    tc=Counter(tr_l); print(f"Train: {len(tr_p)}  real={tc[0]} fake={tc[1]} filter={tc[2]}")
    train_ds=FaceDataset(tr_p,tr_l,transform_train); val_ds=FaceDataset(va_p,va_l,transform_val)
    train_loader=DataLoader(train_ds,batch_size=BATCH_SIZE,shuffle=True,num_workers=8,pin_memory=True)
    val_loader=DataLoader(val_ds,batch_size=BATCH_SIZE,shuffle=False,num_workers=8,pin_memory=True)
    total=len(tr_l); auto_w=[total/(len(CLASSES)*tc[i]) for i in range(3)]
    cw=torch.tensor(auto_w,dtype=torch.float).to(device)
    print(f"Weights: real={cw[0]:.3f} fake={cw[1]:.3f} filter={cw[2]:.3f}")
    model=DualBranchModel().to(device)
    model.load_state_dict(torch.load(INIT_WEIGHTS,map_location=device)); print("Init from v8.1")
    optimizer=torch.optim.Adam(model.parameters(),lr=LR)
    criterion=nn.CrossEntropyLoss(weight=cw)
    best_f1=0.0
    for epoch in range(1,EPOCHS+1):
        model.train(); tr_loss=0.0
        for x,y in train_loader:
            x,y=x.to(device),y.to(device)
            xm,ya,yb,lam=mixup_batch(x,y,MIXUP_ALPHA)
            optimizer.zero_grad()
            loss=mixup_loss(criterion,model(xm),ya,yb,lam)
            loss.backward(); optimizer.step(); tr_loss+=loss.item()
        model.eval(); all_p,all_l=[],[]
        with torch.no_grad():
            for x,y in val_loader:
                all_p.extend(model(x.to(device)).argmax(1).cpu().tolist()); all_l.extend(y.tolist())
        acc=accuracy_score(all_l,all_p); mf1=f1_score(all_l,all_p,average='macro')
        pf=f1_score(all_l,all_p,average=None)
        print(f"[{epoch:02d}/{EPOCHS}] loss={tr_loss/len(train_loader):.4f}  Acc={acc:.4f}  F1={mf1:.4f}  [real={pf[0]:.3f} fake={pf[1]:.3f} filter={pf[2]:.3f}]")
        if mf1>best_f1: best_f1=mf1; torch.save(model.state_dict(),WEIGHTS_PATH); print(f"  -> Saved (F1={best_f1:.4f})")
    print(f"\nBest F1={best_f1:.4f}")
    model.load_state_dict(torch.load(WEIGHTS_PATH,map_location=device)); model.eval()
    all_p,all_l=[],[]
    with torch.no_grad():
        for x,y in val_loader:
            all_p.extend(model(x.to(device)).argmax(1).cpu().tolist()); all_l.extend(y.tolist())
    print(classification_report(all_l,all_p,target_names=CLASSES,digits=4))
    print("Confusion:\n",confusion_matrix(all_l,all_p))
