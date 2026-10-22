#!/usr/bin/env bash
# AZOS image_sha256: sha256 of a sorted manifest of every entry in an initramfs tree:
# "type mode path content-sha256|link-target" (f=file, d=dir incl. empty, l=symlink).
# Excludes only ./etc/azos-image-sha256 (a file cannot contain its own hash).
set -euo pipefail
cd "$1"
find . ! -path ./etc/azos-image-sha256 -print0 | LC_ALL=C sort -z | while IFS= read -r -d '' p; do
  m=$(stat -c %a "$p")
  if [ -L "$p" ]; then printf 'l %s %s %s\n' "$m" "$p" "$(readlink "$p")"
  elif [ -d "$p" ]; then printf 'd %s %s -\n' "$m" "$p"
  else printf 'f %s %s %s\n' "$m" "$p" "$(sha256sum < "$p" | cut -d' ' -f1)"; fi
done | sha256sum | cut -d' ' -f1
