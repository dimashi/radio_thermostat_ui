#!/bin/bash
# Build script for creating Docker image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="${1:-radio-thermostat-ui}"
IMAGE_TAG="${2:-latest}"

echo "📦 Radio Thermostat UI - Docker Build"
echo "======================================"

# Step 1: Analyze dependencies
echo ""
echo "🔍 Step 1: Analyzing dependencies..."
cd "$ROOT_DIR"
python build/build_docker.py

# Step 2: Build Docker image
echo ""
echo "🐳 Step 2: Building Docker image..."
docker build -f build/Dockerfile -t "$IMAGE_NAME:$IMAGE_TAG" .

# Step 3: Display results
echo ""
echo "✅ Build complete!"
echo ""
echo "Image details:"
docker images "$IMAGE_NAME:$IMAGE_TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
echo ""
echo "To run the container:"
echo "  docker run -p 8080:8080 $IMAGE_NAME:$IMAGE_TAG"
echo ""
echo "To run with environment variable for thermostat IP:"
echo "  docker run -p 8080:8080 -e THERMOSTAT_HOST=192.168.1.100 $IMAGE_NAME:$IMAGE_TAG"
