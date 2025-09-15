#!/usr/bin/env sh
set -e
: "${REGISTRY:?Set REGISTRY}"; : "${IMAGE_NAME:?Set IMAGE_NAME}"; : "${IMAGE_TAG:=latest}"
IMG="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
docker build -t "$IMG" -f docker/Dockerfile .
echo "$DOCKER_PASSWORD" | docker login "$REGISTRY" -u "$DOCKER_USERNAME" --password-stdin
docker push "$IMG"
echo "Pushed $IMG"

