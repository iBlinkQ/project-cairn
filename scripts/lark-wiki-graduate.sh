#!/usr/bin/env bash
# lark-wiki-graduate.sh — Project Cairn graduation adapter for the Lark/Feishu wiki provider.
#
# Encodes the verified adapter constraints (see references/graduation.md →
# "Provider adapter constraints"):
#   - user identity + the coarse `wiki:wiki` scope. Granular read scopes
#     (wiki:space:retrieve / wiki:space:read / wiki:node:read) may never enter
#     the user token on CLI-style apps; the write-capable wiki:wiki does.
#   - NATIVE wiki resource API only (wiki spaces get / wiki nodes create /
#     wiki spaces get_node). NOT the +space-list / +node-create shortcuts —
#     they do strict literal scope prechecks that reject wiki:wiki coverage.
#   - create_note has a read dependency: the target space is resolved (read)
#     before the node is created (write).
#
# Writes one graduated note into a Feishu wiki space and optionally links it
# into an INDEX node. Content is piped via stdin to dodge the CLI's
# cwd-relative @file path restriction.
#
# macOS Bash 3.2 compatible: no mapfile/readarray, no associative arrays.
#
# Usage:
#   lark-wiki-graduate.sh --title TITLE [--content FILE]
#       [--space-id ID|my_library] [--parent-node-token TOKEN]
#       [--index-doc OBJ_TOKEN] [--identity user|bot] [--dry-run]
#
# Output (stdout): JSON { space_id, node_token, obj_token, url }
# Requires: lark-cli (authorized; user identity with wiki:wiki), jq.

set -euo pipefail

CLI="${LARK_CLI:-lark-cli}"
IDENTITY="user"
SPACE_ID="my_library"
TITLE=""
CONTENT_FILE=""
PARENT=""
INDEX_DOC=""
DRY_RUN=0

die() { echo "error: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --title) TITLE="${2:-}"; shift 2;;
    --content) CONTENT_FILE="${2:-}"; shift 2;;
    --space-id) SPACE_ID="${2:-}"; shift 2;;
    --parent-node-token) PARENT="${2:-}"; shift 2;;
    --index-doc) INDEX_DOC="${2:-}"; shift 2;;
    --identity) IDENTITY="${2:-}"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) sed -n '2,33p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) die "unknown arg: $1";;
  esac
done

[ -n "$TITLE" ] || die "--title is required"
[ -z "$CONTENT_FILE" ] || [ -f "$CONTENT_FILE" ] || die "content file not found: $CONTENT_FILE"
command -v "$CLI" >/dev/null 2>&1 || die "$CLI not found"
command -v jq  >/dev/null 2>&1 || die "jq not found"

# lark() — wrap a JSON-returning native call with the shared identity flags.
lark() { "$CLI" "$@" --as "$IDENTITY" --json; }

# 0) Preflight: warn (don't fail) if the user token lacks wiki:wiki.
if [ "$DRY_RUN" -eq 0 ] && [ "$IDENTITY" = "user" ]; then
  scopes="$("$CLI" auth status --json 2>/dev/null | jq -r '.identities.user.scope // ""' 2>/dev/null || true)"
  case " $scopes " in
    *" wiki:wiki "*) : ;;
    *) echo "warn: user token has no wiki:wiki scope; run: $CLI auth login --scope wiki:wiki" >&2;;
  esac
fi

# 1) Resolve target space (read dependency before create).
if [ "$SPACE_ID" = "my_library" ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY-RUN: $CLI wiki spaces get --params '{\"space_id\":\"my_library\"}' --as $IDENTITY --json" >&2
    RESOLVED_SPACE="<resolved-my_library-id>"
  else
    RESOLVED_SPACE="$(lark wiki spaces get --params '{"space_id":"my_library"}' | jq -r '.data.space.space_id')"
    [ -n "$RESOLVED_SPACE" ] && [ "$RESOLVED_SPACE" != "null" ] || die "failed to resolve my_library (need wiki:wiki + user identity)"
  fi
else
  RESOLVED_SPACE="$SPACE_ID"
fi

# 2) Create node via native API (optional parent_node_token builds the tree).
data="$(jq -nc --arg t "$TITLE" --arg p "$PARENT" \
  '{node_type:"origin",obj_type:"docx",title:$t} + (if $p=="" then {} else {parent_node_token:$p} end)')"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY-RUN: $CLI wiki nodes create --params '{\"space_id\":\"$RESOLVED_SPACE\"}' --data '$data' --as $IDENTITY --json" >&2
  NODE_TOKEN="<node_token>"; OBJ_TOKEN="<obj_token>"; NODE_URL="<url>"
else
  created="$(lark wiki nodes create --params "{\"space_id\":\"$RESOLVED_SPACE\"}" --data "$data")"
  NODE_TOKEN="$(printf '%s' "$created" | jq -r '.data.node.node_token')"
  OBJ_TOKEN="$(printf '%s' "$created" | jq -r '.data.node.obj_token')"
  NODE_URL="$(printf '%s' "$created" | jq -r '.data.node.url')"
  [ -n "$NODE_TOKEN" ] && [ "$NODE_TOKEN" != "null" ] || die "node create failed: $created"
fi

# 3) Write body + frontmatter (stdin avoids the @file cwd restriction).
if [ -n "$CONTENT_FILE" ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY-RUN: cat '$CONTENT_FILE' | $CLI docs +update --doc $OBJ_TOKEN --command append --doc-format markdown --content - --as $IDENTITY --json" >&2
  else
    "$CLI" docs +update --doc "$OBJ_TOKEN" --command append --doc-format markdown \
      --content - --as "$IDENTITY" --json < "$CONTENT_FILE" >/dev/null
  fi
fi

# 4) Read-back verify (title must round-trip).
if [ "$DRY_RUN" -eq 0 ]; then
  back="$("$CLI" docs +fetch --doc "$OBJ_TOKEN" --doc-format markdown --as "$IDENTITY" 2>/dev/null || true)"
  case "$back" in
    *"$TITLE"*) : ;;
    *) echo "warn: read-back did not contain the title; verify the node manually" >&2;;
  esac
fi

# 5) Optionally append a link into the INDEX/container node (update_index).
if [ -n "$INDEX_DOC" ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY-RUN: printf -- '- [%s](%s)\\n' \"$TITLE\" \"$NODE_URL\" | $CLI docs +update --doc $INDEX_DOC --command append --doc-format markdown --content - --as $IDENTITY --json" >&2
  else
    printf -- '- [%s](%s)\n' "$TITLE" "$NODE_URL" \
      | "$CLI" docs +update --doc "$INDEX_DOC" --command append --doc-format markdown \
          --content - --as "$IDENTITY" --json >/dev/null
  fi
fi

# 6) Emit result.
jq -nc --arg sp "$RESOLVED_SPACE" --arg nt "$NODE_TOKEN" --arg ot "$OBJ_TOKEN" --arg url "$NODE_URL" \
  '{space_id:$sp, node_token:$nt, obj_token:$ot, url:$url}'
