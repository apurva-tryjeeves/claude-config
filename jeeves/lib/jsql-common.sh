#!/usr/bin/env bash
# Shared configuration for `jsql` and `jsql-pull-secrets`.
# Sourced by both, never executed on its own.
#
# Environment overrides honoured by both commands:
#   JEEVES_SECRETS_DIR  directory holding the per-env <env>.env credential files
#   JEEVES_DB_HOST      endpoint hostname
#   JEEVES_DB_PORT      endpoint port
#
# Each command documents the overrides that apply to it alone.

# The single definition of where credentials live. Kept outside any source tree
# so they stay clear of git, editor indexers, and workspace-wide searches.
JEEVES_SECRETS_DIR="${JEEVES_SECRETS_DIR:-$HOME/.config/jeeves/mysql}"

# Locate this library from a script in the sibling bin/ directory. Resolves via
# the caller's own path, so it works from any working directory and whether or
# not CLAUDE_PLUGIN_ROOT is set.
#
# Usage from bin/<script>:
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/jsql-common.sh"
