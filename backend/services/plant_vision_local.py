import json
import numpy as np
from PIL import Image
import io
import os

try:
    import onnxruntime as ort
except Exception:
    ort = None

MODEL_PATH = os.getenv("PLANT_MODEL_PATH", "models/plant_disease.onnx")
LABELS_PATH = os.getenv("PLANT_LABELS_PATH", "models/labels.json")

_session = None
_labels = None

def _load():
    global _session, _labels
    if _session is not None:
        return
    if ort is None:
        raise RuntimeError("onnxruntime not installed")

    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"Model file missing: {MODEL_PATH}")
    if not os.path.exists(LABELS_PATH):
        raise RuntimeError(f"Labels file missing: {LABELS_PATH}")

    _session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    _labels = json.loads(open(LABELS_PATH, "r", encoding="utf-8").read())

def predict_image(image_bytes: bytes) -> dict:
    _load()

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((224, 224))

    arr = np.array(img).astype("float32") / 255.0  # 224x224x3
    arr = np.transpose(arr, (2, 0, 1))            # 3x224x224
    arr = np.expand_dims(arr, 0)                  # 1x3x224x224

    inp_name = _session.get_inputs()[0].name
    out_name = _session.get_outputs()[0].name

    logits = _session.run([out_name], {inp_name: arr})[0][0]
    probs = softmax(logits)

    top_idx = int(np.argmax(probs))
    top_prob = float(probs[top_idx])
    label = _labels[top_idx] if top_idx < len(_labels) else f"class_{top_idx}"

    # return top-3 too
    top3 = np.argsort(-probs)[:3].tolist()
    top3_list = [{"label": _labels[i] if i < len(_labels) else f"class_{i}", "prob": float(probs[i])} for i in top3]

    return {"label": label, "confidence": round(top_prob, 3), "top3": top3_list}

def softmax(x):
    x = np.array(x, dtype=np.float32)
    x = x - np.max(x)
    e = np.exp(x)
    return e / np.sum(e)
