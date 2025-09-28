#!/usr/bin/env bash
set -e

echo "=== Updating system packages ==="
sudo apt update -y && sudo apt upgrade -y

echo "=== Installing system dependencies ==="
# Build tools + Python headers
sudo apt install -y python3-dev python3-venv python3-pip build-essential

# Libraries needed for cffi, llvmlite, numba
sudo apt install -y libffi-dev

# Libraries needed for Pillow, matplotlib
sudo apt install -y libjpeg-dev zlib1g-dev libfreetype6-dev libpng-dev

# FFmpeg (required by moviepy, imageio-ffmpeg)
sudo apt install -y ffmpeg

echo "=== Creating virtual environment ==="
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "=== Activating virtual environment ==="
source .venv/bin/activate

echo "=== Upgrading pip and setuptools ==="
pip install --upgrade pip setuptools wheel

echo "=== Installing Python requirements ==="
if [ -f requirementsGemini1.txt ]; then
    pip install -r requirementsGemini1.txt
else
    echo "requirementsGemini1.txt not found!"
    exit 1
fi

echo "=== Setup completed successfully! ==="
echo "Activate the venv with: source .venv/bin/activate"