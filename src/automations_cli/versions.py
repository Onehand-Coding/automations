"""Single source of truth for toolchain versions baked into generated projects.

Bump NODE_MAJOR when adopting a new Node LTS; every template that references
Node (engines field, Dockerfile, CI workflow) reads it from here so a bump is
one edit instead of a repo-wide hunt.

FLUTTER_BUILD_IMAGE pins the Docker image used to build Flutter web assets in
prod images and CI. Pinned by tag for reproducibility — bump deliberately,
not passively.
"""

NODE_MAJOR = "24"

# Upper bound rejects accidental next-major runs (Node 25 ships breaking
# changes on its own schedule); engines + Dockerfile + CI all derive from
# these two strings.
NODE_ENGINES = ">=24 <25"
NODE_DOCKER_IMAGE = f"node:{NODE_MAJOR}-alpine"

# @types/node versions track Node releases but are published on their own
# cadence, so it gets its own spec instead of being derived from NODE_MAJOR
# (deriving produced ^24.14.0, which does not exist).
NODE_TYPES_SPEC = "^24.13"

# cirruslabs publishes versioned tags per Flutter release but the registry
# lags stable (newest tag verified 2026-08-26 was 3.44.0 while stable is
# 3.47.x). Pinned by tag for reproducible frontend builds — bump deliberately
# after checking https://github.com/cirruslabs/docker-images-flutter/pkgs/container/flutter
FLUTTER_BUILD_IMAGE = "ghcr.io/cirruslabs/flutter:3.44.0"
