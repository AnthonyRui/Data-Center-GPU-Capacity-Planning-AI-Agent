"""Execute notebooks without modifying checked-in versions.
执行Notebook验证，不修改仓库中的版本。
"""
import os
from pathlib import Path
import tempfile
import sys
import json
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Temporary kernel uses this interpreter. / 临时内核使用当前Python解释器。
    with tempfile.TemporaryDirectory() as tmp:
        kernel = Path(tmp) / "kernels" / "capacity-check"
        kernel.mkdir(parents=True)
        (kernel / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "Capacity check", "language": "python"
        }), encoding="utf-8")
        old = os.environ.get("JUPYTER_PATH")
        os.environ["JUPYTER_PATH"] = tmp + (os.pathsep + old if old else "")
        try:
            for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
                notebook = nbformat.read(path, as_version=4)
                nbformat.validate(notebook)
                NotebookClient(notebook, timeout=180, kernel_name="capacity-check", resources={"metadata": {"path": str(ROOT / "notebooks")}}).execute()
                print("PASS / 通过:", path.name)
        finally:
            if old is None:
                os.environ.pop("JUPYTER_PATH", None)
            else:
                os.environ["JUPYTER_PATH"] = old


if __name__ == "__main__":
    main()
