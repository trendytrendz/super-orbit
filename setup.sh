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

//once we installed this we need to change the policy.xml
// sudo nano /etc/ImageMagick-6/policy.xml
// need to change policy error 
// <policy domain="path" rights="read|write" pattern="@*"/>
sudo apt-get install -y imagemagick 

echo "=== Upgrading pip and setuptools ==="
pip install --upgrade pip setuptools wheel

echo "=== Installing Python requirements ==="
if [ -f requirement.txt ]; then
    pip install -r requirement.txt
else
    echo "requirement.txt not found!"
    exit 1
fi

echo "=== Setup completed successfully! ==="