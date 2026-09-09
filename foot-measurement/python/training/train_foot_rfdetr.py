"""Fine-tune RF-DETR-Seg for the single class FOOT on a Roboflow Universe dataset.

Run on a CUDA GPU (Google Colab T4 is enough; see training/README.md):

    pip install rfdetr roboflow
    export ROBOFLOW_API_KEY=...
    python train_foot_rfdetr.py --dataset-url https://universe.roboflow.com/allard/foot-segmentation-ehn9q/1 \
        --size small --epochs 50 --output ./output

Produces  output/checkpoint_best_total.pth  and  output/classes.json  — copy both into
foot-measurement/python/weights/.  RF-DETR auto-detects the COCO layout
(train/valid/test with _annotations.coco.json containing segmentation polygons).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

SIZES = {"nano": "RFDETRSegNano", "small": "RFDETRSegSmall", "medium": "RFDETRSegMedium",
         "large": "RFDETRSegLarge", "xlarge": "RFDETRSegXLarge", "2xlarge": "RFDETRSeg2XLarge"}


def download(url: str, out_dir: str) -> str:
    from roboflow import download_dataset  # pip install roboflow ; needs ROBOFLOW_API_KEY
    ds = download_dataset(url, "coco", location=out_dir)
    return ds.location


def write_classes_json(dataset_dir: Path, out: Path) -> dict[int, str]:
    """RF-DETR fine-tuned checkpoints use 0-based indices into the COCO categories list."""
    ann = json.loads((dataset_dir / "train" / "_annotations.coco.json").read_text())
    cats = sorted(ann["categories"], key=lambda c: c["id"])
    names = {i: c["name"] for i, c in enumerate(cats)}
    out.write_text(json.dumps(names, indent=2))
    return names


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset-url", default="https://universe.roboflow.com/allard/foot-segmentation-ehn9q/1",
                   help="Roboflow Universe dataset URL (instance segmentation, class 'foot')")
    p.add_argument("--dataset-dir", default=None, help="already-downloaded COCO dataset dir (skips download)")
    p.add_argument("--size", default="small", choices=list(SIZES))
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--grad-accum-steps", type=int, default=4, help="batch_size * grad_accum_steps ~ 16")
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--output", default="./output")
    p.add_argument("--device", default=None, help="cuda (default) | mps | cpu (very slow)")
    a = p.parse_args()

    if a.dataset_dir is None:
        if not os.environ.get("ROBOFLOW_API_KEY"):
            raise SystemExit("set ROBOFLOW_API_KEY (free account: https://app.roboflow.com) or pass --dataset-dir")
        a.dataset_dir = download(a.dataset_url, "./datasets")
    ds = Path(a.dataset_dir)
    if not (ds / "train" / "_annotations.coco.json").exists():
        raise SystemExit(f"{ds} is not a COCO dataset (train/_annotations.coco.json missing)")
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    names = write_classes_json(ds, out / "classes.json")
    print("classes:", names)
    if not any(n.lower() == "foot" for n in names.values()):
        print("WARNING: no class named 'foot' — pass --class-name <name> to footmeasure later")

    import rfdetr
    model = getattr(rfdetr, SIZES[a.size])(**({"device": a.device} if a.device else {}))
    kwargs = dict(dataset_dir=str(ds), epochs=a.epochs, batch_size=a.batch_size,
                  grad_accum_steps=a.grad_accum_steps, lr=a.lr, output_dir=str(out))
    print("train:", kwargs)
    model.train(**kwargs)
    best = out / "checkpoint_best_total.pth"
    print(f"done. copy {best} and {out / 'classes.json'} to foot-measurement/python/weights/")


if __name__ == "__main__":
    main()
