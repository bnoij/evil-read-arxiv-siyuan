#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "start-my-day" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from siyuan_job_client import SiYuanJobClient


def main():
    parser = argparse.ArgumentParser(description="Upload extracted paper images to SiYuan assets")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--base-url", default="http://127.0.0.1:6806")
    parser.add_argument("--assets-dir", default="/assets/")
    args = parser.parse_args()
    client = SiYuanJobClient(args.base_url)
    print(json.dumps(client.upload_assets(args.paths, args.assets_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
