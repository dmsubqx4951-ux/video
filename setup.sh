#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
command -v ffmpeg >/dev/null
test -f /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
mkdir -p assets output
archive=assets/kokoro-multi-lang-v1_0.tar.bz2
if [ ! -f "$archive" ]; then
  curl --fail --location --retry 2 --silent --show-error \
    --output "$archive" \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2
fi
printf '%s  %s\n' \
  c5f7e2d2caf082bc1d20fb70334a61d99d20b484500aad32e7cf84c128ea3298 \
  "$archive" | sha256sum --check
.venv/bin/python - <<'PY'
import tarfile
from pathlib import Path
folder=Path('assets/kokoro-multi-lang-v1_0')
required=('model.onnx','voices.bin','lexicon-zh.txt','lexicon-us-en.txt','tokens.txt','phone-zh.fst','date-zh.fst','number-zh.fst')
if not all((folder/name).is_file() for name in required):
    with tarfile.open('assets/kokoro-multi-lang-v1_0.tar.bz2') as archive:
        archive.extractall('assets',filter='data')
print('Offline drawing and Mandarin speech environment ready.')
PY

