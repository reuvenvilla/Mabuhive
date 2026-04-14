#!/usr/bin/env bash
# scripts/push.sh
# Push mabuhive:latest and mabuhive:release images to Google Cloud Artifact Registry.
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Docker images mabuhive:latest and/or mabuhive:release exist
#
# Usage:
#   ./scripts/push.sh [--pid=PROJECT_ID] [--region=REGION]
#   Defaults: PROJECT_ID=pies-mabuhive, REGION=us-central1

set -euo pipefail
cd "$(dirname "$0")/.."          # always run from project root

# Default values
PROJECT_ID="pies-mabuhive"
REGION="us-central1"

# Parse command-line arguments
for arg in "$@"; do
  case "$arg" in
    --pid=*)
      PROJECT_ID="${arg#*=}"
      ;;
    --region=*)
      REGION="${arg#*=}"
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [--pid=PROJECT_ID] [--region=REGION]"
      exit 1
      ;;
  esac
done

REPO_NAME="mabuhive"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"

# Check gcloud authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 >/dev/null; then
  echo "Error: Not authenticated with gcloud. Run 'gcloud auth login' first."
  exit 1
fi

# Configure Docker to use gcloud as a credential helper
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

IMAGES_TO_PUSH=()

# Check and prepare latest image
if docker image inspect mabuhive:latest &>/dev/null; then
  echo "Preparing mabuhive:latest for push..."
  docker tag mabuhive:latest "${REGISTRY}/mabuhive:latest"
  IMAGES_TO_PUSH+=("${REGISTRY}/mabuhive:latest")
else
  echo "Warning: mabuhive:latest not found, skipping."
fi

# Check and prepare release image
if docker image inspect mabuhive:release &>/dev/null; then
  echo "Preparing mabuhive:release for push..."
  docker tag mabuhive:release "${REGISTRY}/mabuhive:release"
  IMAGES_TO_PUSH+=("${REGISTRY}/mabuhive:release")
else
  echo "Warning: mabuhive:release not found, skipping."
fi

if [[ ${#IMAGES_TO_PUSH[@]} -eq 0 ]]; then
  echo "Error: No images to push. Tag images first with ./scripts/tag.sh"
  exit 1
fi

# Push images
for image in "${IMAGES_TO_PUSH[@]}"; do
  echo "Pushing $image..."
  docker push "$image"
done

echo "All images pushed successfully to ${REGISTRY}"