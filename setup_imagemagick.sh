#!/bin/bash
set -e

POLICY_FILE="/etc/ImageMagick-6/policy.xml"

if [ -f "$POLICY_FILE" ]; then
    echo "Updating ImageMagick policy to allow TextClip generation..."
    sudo sed -i 's/rights="none" pattern="@\*/rights="read|write" pattern="@\*/' "$POLICY_FILE"
    echo "ImageMagick policy updated successfully."
else
    echo "WARNING: ImageMagick policy file not found at $POLICY_FILE. Skipping update."
fi
