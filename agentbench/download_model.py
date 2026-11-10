"""Download a pinned public model; optional MLX dependencies must be installed."""
from pathlib import Path
from huggingface_hub import snapshot_download

if __name__ == '__main__':
    snapshot_download(repo_id='mlx-community/Qwen3-4B-Instruct-2507-4bit',
                      revision='50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b',
                      local_dir=Path(__file__).resolve().parents[1]/'models/qwen3-4b')
