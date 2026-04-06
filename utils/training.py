import torch
import torch.nn
import torchvision.transforms
import random
import time
import timm
import io
import logging
import uuid
import shutil #dkjh

import numpy
import onnxruntime

from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from PIL import Image
from typing import Callable, Optional
from onnxruntime.quantization import quantize_dynamic, QuantType

logger = logging.getLogger("Potataooo")

# Honestly, a lot of this file is vibecoded, mostly because I'm reeeeeeeally sick of this, anything model related has to be one of the most boring stuff ever
# It's already been 3 days and I've as of writing this rewritten this project 4 times, I will not be spending more hours on research which I'll never use
# This gets annoying really fast, sure, I'll probably not be as proud as I expected myself to be of this file but I guess it's something nonetheless..

# Hiii, potatao again, coming back here after a day, decided to tell myself how much I hate this file, I hate how a lot of it is vibecoded, especially when it's
# the citadel of the bot which I can't really "replace", I would make it myself but I could never do this better, everything here seems like magic to me,
# sure, I do know how to make a file or 2, maybe create a dir somewhere, but definitely not whatever that is, so many weird things, I didn't know what a tuple was 
# before I got into this, actually, I still don't really know what it did, there's quite a bit of the main cog/plugin thing that's just old stack overflow code

def makesurethedirsarereal():
    for subdirectory in ("positive", "negative", "pending"):
        Path(f"training_data/{subdirectory}").mkdir(parents=True, exist_ok=True)
    Path("models").mkdir(exist_ok=True)

def whatdoihave() -> tuple[int, int]:
    try:
        positives = len([file for file in Path("training_data/positive").iterdir() if file.is_file()])
        negatives = len([file for file in Path("training_data/negative").iterdir() if file.is_file()])
        return positives, negatives
    except FileNotFoundError:
        return 0,0

def newestmodelversion():
    try:
        versions = [
            int(file.stem.split("_v")[1])
            for file in Path("models").glob("model_v*.onnx")
            if "_v" in file.stem and "tmp" not in file.stem
        ]
        return max(versions) if versions else 0
    except Exception:
        return 0

def loadsomemodel(version: int = None):
    try:
        ver = version or newestmodelversion()
        if not ver:
            return None
        path = f"models/model_v{ver}.onnx"
        if not Path(path).exists():
            return None
        options = onnxruntime.SessionOptions()
        options.inter_op_num_threads = 1 # yet another github paste thanks
        options.intra_op_num_threads = 1
        options.log_severity_level = 3
        return onnxruntime.InferenceSession(path, options, providers=["CPUExecutionProvider"])
    except Exception as e:
        logger.error(f"um i don't knwo how to laod this {e}")
        return None

def predict(session, image_byes: bytes) -> float:
    try:
        image = Image.open(io.BytesIO(image_byes)).convert("RGB").resize((256, 256), Image.LANCZOS)
        arraywsas = numpy.array(image, dtype=numpy.float32) / 255.0
        arraywsas = (arraywsas - numpy.array([0.485, 0.456, 0.406])) / numpy.array([0.229, 0.224, 0.225])
        inputthing = arraywsas.transpose(2, 0, 1)[numpy.newaxis].astype(numpy.float32)
        output = session.run(None, {session.get_inputs()[0].name: inputthing})[0]
        return float(1.0 / (1.0 + numpy.exp(-float(output[0][0])))) # what even is a sigmoid
    except Exception as e:
        logger.error(f"I don't know but i failed to predict stuff {e}")
        return 0.5


# took me 2 days to figure out I was missing these thingies i will cry

def save_image(image_bytes: bytes, label: str) -> Optional[str]:
    try:
        makesurethedirsarereal()
        filename = f"{uuid.uuid4()}.png"
        Image.open(io.BytesIO(image_bytes)).convert("RGB").save(f"training_data/{label}/{filename}", "PNG")
        return filename
    except Exception as e:
        logger.error(f"i don't knwo how to save images or ur disk is stupid {e}")
        return None
    
def move_image(filename: str, fromwhere: str, towhere: str) -> bool: # why
    try:
        whereistheimagenow = Path(f"training_data/{fromwhere}/{filename}")
        whereshouldtheimagebe = Path(f"training_data/{towhere}/{filename}")
        if whereistheimagenow.exists():
            shutil.move(str(whereistheimagenow), str(whereshouldtheimagebe))
            return True
        return False
    except Exception as e:
        logger.error(f"ur image is probably dumb and can't be moved {filename} and {e}")
        return False

def delete_image(filename: str, label: str) -> bool:
    try:
        where = Path(f"training_data/{label}/{filename}")
        if where.exists():
            where.unlink() # does os not even have a .delete() thing?
            return True
        return False
    except Exception:
        return False


# 
# WARNING: HEAVILY VIBECODED STUFF BELOW
#

async def train_model(progress_cb: Callable = None) -> dict:
    makesurethedirsarereal()
    pos, neg = whatdoihave()
    if pos + neg < 128:
        raise ValueError(f"Need 128 examples, have {pos + neg} ({pos}+ / {neg}-)")

    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"[antimrbeast] training on CUDA: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        print("[antimrbeast] no GPU found, training on CPU")
 
    pos_files = sorted(Path("training_data/positive").glob("*.png"))
    neg_files = sorted(Path("training_data/negative").glob("*.png"))

    train_tf = torchvision.transforms.Compose([
        torchvision.transforms.Resize((256, 256)),
        torchvision.transforms.RandomHorizontalFlip(),
        torchvision.transforms.RandomVerticalFlip(p=0.05),
        torchvision.transforms.RandomRotation(15),
        torchvision.transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.05),
        torchvision.transforms.RandomGrayscale(p=0.05),
        torchvision.transforms.RandomApply([torchvision.transforms.GaussianBlur(3)], p=0.1),
        torchvision.transforms.RandomPerspective(distortion_scale=0.2, p=0.2),
        torchvision.transforms.RandomAdjustSharpness(sharpness_factor=2, p=0.2),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = torchvision.transforms.Compose([
        torchvision.transforms.Resize((256, 256)),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
 
    class ScamDS(Dataset):
        def __init__(self, items, tf):
            self.items, self.tf = items, tf
        def __len__(self): return len(self.items)
        def __getitem__(self, i):
            path, label = self.items[i]
            return self.tf(Image.open(path).convert("RGB")), torch.tensor(label, dtype=torch.float32)
 
    all_data = [(f, 1.0) for f in pos_files] + [(f, 0.0) for f in neg_files]
    random.shuffle(all_data)
    split = int(len(all_data) * 0.8)

    train_loader = DataLoader(ScamDS(all_data[:split], train_tf), batch_size=16, shuffle=True,  num_workers=0, pin_memory=False, drop_last=len(all_data[:split]) > 16)
    val_loader   = DataLoader(ScamDS(all_data[split:], val_tf),   batch_size=16, shuffle=False, num_workers=0, pin_memory=False)
 
    pos_weight = torch.tensor([neg / max(pos, 1)], dtype=torch.float32).to(device)
 
    model     = timm.create_model("efficientnet_lite0", pretrained=True, num_classes=1).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)
 
    EPOCHS       = 50
    best_val_acc = 0.0
    best_state   = None
    patience     = 0
    t0           = time.time()
 
    for epoch in range(1, EPOCHS + 1):
        model.train()
        tloss, correct, total = 0.0, 0, 0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device).unsqueeze(1)
            optimizer.zero_grad()
            out   = model(imgs)
            loss  = criterion(out, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            tloss   += loss.item()
            preds    = (torch.sigmoid(out) > 0.5).float()
            correct += (preds == labels).sum().item()
            total   += labels.size(0)
        scheduler.step()
 
        model.eval()
        vc, vt = 0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device).unsqueeze(1)
                preds  = (torch.sigmoid(model(imgs)) > 0.5).float()
                vc    += (preds == labels).sum().item()
                vt    += labels.size(0)
 
        val_acc   = vc / vt if vt else 0.0
        train_acc = correct / total if total else 0.0
        avg_loss  = tloss / len(train_loader)
 
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state   = {k: v.clone() for k, v in model.state_dict().items()}
            patience     = 0
        else:
            patience += 1
            if patience >= 5:
                logger.info(f"Early stopping at epoch {epoch} because val acc hasn't improved in 5 epochs")
                break
 
        if progress_cb and epoch % 1 == 0: # i didn't like how it sent updates every 5 epcoshdhsdhkjf
            elapsed = time.time() - t0
            eta     = (elapsed / epoch) * (EPOCHS - epoch)
            progress_cb(epoch, EPOCHS, avg_loss, train_acc, val_acc, elapsed, eta)
 
    if best_state:
        model.load_state_dict(best_state)
 
    next_v   = newestmodelversion() + 1
    tmp_path = "models/tmp.onnx"
    out_path = f"models/model_v{next_v}.onnx"
 
    model = model.cpu().eval()
 
    torch.onnx.export(
        model,
        torch.randn(1, 3, 256, 256),
        tmp_path,
        dynamo=False,
        opset_version=14,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "b"}, "output": {0: "b"}},
    )
 
    quantize_dynamic(tmp_path, out_path, weight_type=QuantType.QUInt8)
    Path(tmp_path).unlink(missing_ok=True)
 
    return {
        "version":   next_v,
        "accuracy":  best_val_acc,
        "positives": pos,
        "negatives": neg,
        "train_n":   len(all_data[:split]),
        "n":         len(all_data[split:]),
        "elapsed":   time.time() - t0,
    }
 
# not proud