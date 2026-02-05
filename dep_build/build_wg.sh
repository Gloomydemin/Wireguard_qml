#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$ROOT_DIR/vendored"
WG_SRC="$SCRIPT_DIR/wireguard-tools/src"
WGO_SRC="$SCRIPT_DIR/wireguard-go"

mkdir -p "$OUT_DIR"

echo "==> Ensuring binfmt/qemu is available for multi-arch builds"
if ! docker run --privileged --rm tonistiigi/binfmt --install all >/dev/null 2>&1; then
  echo "Warning: failed to install binfmt. ARM builds may fail."
fi

echo "==> Building wireguard-tools (wg) for amd64/arm64/arm"
docker buildx build --platform linux/amd64 -t wgbuild-amd64 -f "$SCRIPT_DIR/Dockerfile_wg" "$SCRIPT_DIR"
docker buildx build --platform linux/arm64/v8 -t wgbuild-arm64 -f "$SCRIPT_DIR/Dockerfile_wg" "$SCRIPT_DIR"
docker buildx build --platform linux/arm/v7 -t wgbuild-arm -f "$SCRIPT_DIR/Dockerfile_wg" "$SCRIPT_DIR"

docker run --rm -v "$WG_SRC":/data wgbuild-amd64 sh -c "make -C /data clean && make -C /data -j wg"
cp "$WG_SRC/wg" "$OUT_DIR/wg-x86_64"

docker run --rm --platform linux/arm64/v8 -v "$WG_SRC":/data wgbuild-arm64 sh -c "make -C /data clean && make -C /data -j wg"
cp "$WG_SRC/wg" "$OUT_DIR/wg-arm64"

docker run --rm --platform linux/arm/v7 -v "$WG_SRC":/data wgbuild-arm sh -c "make -C /data clean && make -C /data -j wg"
cp "$WG_SRC/wg" "$OUT_DIR/wg-arm"

echo "==> Building wireguard-go (userspace) for amd64/arm64/arm"
docker build -t wgo-build -f "$SCRIPT_DIR/Dockerfile_wgo" "$SCRIPT_DIR"
docker run --rm -v "$WGO_SRC":/src -v "$OUT_DIR":/out wgo-build sh -c '\
  set -e; \
  cd /src; \
  export CGO_ENABLED=0 GOOS=linux; \
  GOARCH=amd64 go build -trimpath -ldflags "-s -w" -o /out/wireguard-x86_64 .; \
  GOARCH=arm64 go build -trimpath -ldflags "-s -w" -o /out/wireguard-arm64 .; \
  GOARCH=arm GOARM=7 go build -trimpath -ldflags "-s -w" -o /out/wireguard-arm .; \
'

HOST_UID=$(stat -c %u "$OUT_DIR")
HOST_GID=$(stat -c %g "$OUT_DIR")
chown "$HOST_UID:$HOST_GID" "$OUT_DIR"/wg-* "$OUT_DIR"/wireguard-* 2>/dev/null || true
chmod +x "$OUT_DIR"/wg-* "$OUT_DIR"/wireguard-* 2>/dev/null || true
