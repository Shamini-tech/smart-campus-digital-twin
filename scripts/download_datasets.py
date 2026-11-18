"""Download the BDG2 files used by this project into data/raw/.

The files are stored with Git LFS on GitHub, so the media.githubusercontent.com
address is used. BDG2 is licensed CC BY-SA; see docs/decisions.md.
"""
import argparse
import sys
import urllib.request
from pathlib import Path

BASE = "https://media.githubusercontent.com/media/buds-lab/building-data-genome-project-2/master/data"
FILES = {
    "metadata": ("metadata/metadata.csv", "metadata.csv"),
    "weather": ("weather/weather.csv", "weather.csv"),
    "electricity": ("meters/raw/electricity.csv", "electricity.csv"),
}
MIN_BYTES = 100_000  # an LFS pointer file is only about 130 bytes


def download(name, out_dir, force):
    remote, local = FILES[name]
    target = out_dir / local
    if target.exists() and not force:
        print(f"{local}: already exists, skipping")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"{local}: downloading ...")
    urllib.request.urlretrieve(f"{BASE}/{remote}", target)
    size = target.stat().st_size
    if size < MIN_BYTES:
        target.unlink()
        sys.exit(f"{local}: only {size} bytes, looks like an LFS pointer, not data")
    print(f"{local}: done ({size / 1e6:.1f} MB)")


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=FILES, help="download a single file")
    parser.add_argument("--out", default=str(root / "data" / "raw"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    for name in [args.only] if args.only else FILES:
        download(name, Path(args.out), args.force)


if __name__ == "__main__":
    main()