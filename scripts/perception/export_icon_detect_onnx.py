import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default=str(Path("icon_detect") / "model.pt"),
    )
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--opset", type=int, default=20)
    parser.add_argument("--simplify", type=int, choices=[0, 1], default=1)
    parser.add_argument("--dynamic", type=int, choices=[0, 1], default=0)
    parser.add_argument("--project", default=str(Path("icon_detect") / "onnx"))
    parser.add_argument("--name", default="icon_detect")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).expanduser().resolve()
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    output_dir = Path(args.project).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(model_path))
    model.export(
        format="onnx",
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=bool(args.simplify),
        dynamic=bool(args.dynamic),
        project=str(output_dir),
        name=args.name,
    )
    exported = model_path.with_suffix(".onnx")
    if exported.exists():
        target = output_dir / f"{args.name}.onnx"
        if target.exists():
            target.unlink()
        shutil.move(str(exported), str(target))


if __name__ == "__main__":
    main()
