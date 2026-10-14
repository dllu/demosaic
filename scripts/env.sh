# Source from the repository root. Keep every writable cache in authorized storage.
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/.cache/python"
export HF_HOME="$PWD/.cache/huggingface"
export TORCH_HOME="$PWD/.cache/torch"
export TORCHINDUCTOR_CACHE_DIR="$PWD/.cache/inductor"
export TRITON_CACHE_DIR="$PWD/.cache/triton"
export XDG_CACHE_HOME="$PWD/.cache"
export XDG_CONFIG_HOME="$PWD/.cache/config"
export MPLCONFIGDIR="$PWD/.cache/matplotlib"
export CUDA_CACHE_PATH="$PWD/.cache/cuda"
export TMPDIR="$PWD/.cache/tmp"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$TMPDIR"
