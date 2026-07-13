#!/bin/bash
# Ensure the tbd CLI is available and run `tbd prime`.
# Installed by: tbd setup --auto. Runs on SessionStart and PreCompact.
#
# Local-first, then a VERSION-PINNED zero-install fallback. Pinning is both a
# supply-chain control (an unpinned runner re-resolves to latest on every run
# and bypasses any cool-off) and a consistency control (every teammate and agent
# runs the same tbd version).

# Prefer common local bin locations.
export PATH="$HOME/.local/bin:$HOME/bin:/usr/local/bin:$PATH"

# Local-first: use tbd if it is already on PATH.
if command -v tbd &> /dev/null; then
    tbd prime "$@"
    exit $?
fi

# Pinned zero-install fallback. Never use an unpinned runner here.
# Supply-chain cool-off EXCEPTION (on the record per policy): get-tbd@0.4.0 was
# published 2026-07-12, inside the 14-day window. Approved by @jlevy (the package's
# author and this repo's owner) on 2026-07-13 to dogfood his own release across the
# kash repos. Provenance verified: npm trusted publisher (GitHub Actions OIDC);
# integrity sha512-hFZb0cgq7FH6Zp/rsj1ri7o6gSqoGPU13QYfy/wpc1QXIMkUV5wtT+fYevWlur8SlmT2l/0fLgeETy6TbS4g1Q==
# Follow-up: exception expires once 0.4.0 clears the window (2026-07-26).
if command -v npx &> /dev/null; then
    npx --yes get-tbd@0.4.0 prime "$@"
    exit $?
fi

echo "[tbd] tbd CLI not found and npx is unavailable."
echo "[tbd] Install it with: npm install -g get-tbd@0.4.0"
exit 1
