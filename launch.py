#!/usr/bin/env python3
"""Launch the offline notebook from any working directory."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    environment = dict(os.environ, MODEL2GDS_EXPLORER_ROOT=str(ROOT))
    raise SystemExit(subprocess.call([sys.executable, '-m', 'jupyterlab',
        '--ServerApp.root_dir=' + str(ROOT),
        '--ServerApp.default_url=/lab/tree/Explorer.ipynb', *sys.argv[1:]],
        cwd=ROOT, env=environment))
