import json
import os
import numpy as np
from PIL import Image
import io
import onnxruntime as ort

RICE_MODEL_DIR  = os.getenv("RICE_MODEL_DIR",  "models/rice")
WHEAT_MODEL_DIR = os.getenv("WHEAT_MODEL_DIR", "models/wheat")

_SESS = {}
_LABELS = {}

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def _load(model_dir: str):
    if model_dir in _SESS:
        return _SESS[model_dir], _LABELS[model_dir]

    onnx_path = os.path.join(model_dir, "model.onnx")
    labels_path = os.path.join(model_dir, "labels.json")

    if not os.path.exists(onnx_path):
        raise RuntimeError(f"Missing ONNX model: {onnx_path}")
    if not os.path.exists(labels_path):
        raise RuntimeError(f"Missing labels.json: {labels_path}")

    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    labels = json.loads(open(labels_path, "r", encoding="utf-8").read())

    _SESS[model_dir] = sess
    _LABELS[model_dir] = labels
    return sess, labels

def _softmax(x):
    x = np.array(x, dtype=np.float32)
    x = x - np.max(x)
    e = np.exp(x)
    return e / np.sum(e)

def _preprocess(image_bytes: bytes, size: int = 224) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((size, size))

    arr = np.array(img).astype(np.float32) / 255.0  # HWC in [0..1]
    # Normalize exactly like training
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD      # HWC
    arr = np.transpose(arr, (2, 0, 1))              # CHW
    arr = np.expand_dims(arr, 0)                    # NCHW
    return arr

def predict(crop: str, image_bytes: bytes) -> dict:
    crop = (crop or "").lower()
    model_dir = WHEAT_MODEL_DIR if crop == "wheat" else RICE_MODEL_DIR  # paddy -> rice

    sess, labels = _load(model_dir)
    x = _preprocess(image_bytes)

    inp = sess.get_inputs()[0].name
    out = sess.get_outputs()[0].name
    logits = sess.run([out], {inp: x})[0][0]

    probs = _softmax(logits)
    top_idx = int(np.argmax(probs))
    conf = float(probs[top_idx])
    label = labels[top_idx] if top_idx < len(labels) else f"class_{top_idx}"

    top3_idx = np.argsort(-probs)[:3].tolist()
    top3 = [{"label": labels[i] if i < len(labels) else f"class_{i}", "prob": float(probs[i])} for i in top3_idx]

    return {"label": label, "confidence": round(conf, 3), "top3": top3, "model_dir": model_dir}
