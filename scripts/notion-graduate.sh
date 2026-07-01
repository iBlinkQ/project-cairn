#!/usr/bin/env bash
# notion-graduate.sh — Project Cairn graduation adapter for the Notion provider.
#
# Encodes the verified adapter constraints (see references/graduation.md →
# "Provider adapter constraints" / cairn Notion Provider notes):
#   - Direct REST via curl (honors HTTPS_PROXY), NOT the `ntn` CLI (unreliable
#     behind a proxy: fetches an OpenAPI spec to resolve endpoints, does not
#     honor the proxy, fails PATCH/query).
#   - Per-request retry with backoff to ride out random SSL EOF flakiness.
#   - Pin Notion-Version (default 2022-06-28: classic single-source database;
#     avoids the 2025-09-03+ data-source semantics).
#   - One page = one graduated note, created in a single POST /v1/pages with
#     properties + children (body) together — no PATCH needed.
#   - DB is the INDEX: there is NO update_index step (the DB's views/properties
#     are the index; nothing to append into an INDEX page).
#   - Frontmatter maps to DB PROPERTIES, not YAML. Body markdown -> Notion
#     blocks. `[[wikilinks]]` render as bold title text; turning them into real
#     page mentions needs a batch two-pass (resolve all title->id first) and is
#     out of scope for this single-note adapter.
#
# macOS Bash 3.2 compatible: no mapfile/readarray, no associative arrays.
# Requires: curl, jq, python3 (md->blocks). Token in env NOTION_API_TOKEN.
#
# Usage:
#   notion-graduate.sh --db DATABASE_ID --title TITLE [--content BODY.md]
#     [--type knowledge_note] [--contains a,b,c] [--tags a,b,c]
#     [--graduated-from TEXT] [--graduated-at YYYY-MM-DD]
#     [--authoring-mode ai_generated] [--props-json FILE] [--dry-run]
#
# Output (stdout): JSON { id, url }
set -uo pipefail

NV="${NOTION_API_VERSION:-2022-06-28}"
DB=""; TITLE=""; CONTENT_FILE=""; PROPS_JSON=""
TYPE=""; CONTAINS=""; TAGS=""; GFROM=""; GAT=""; AMODE=""
DRY_RUN=0

die() { echo "error: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --db) DB="${2:-}"; shift 2;;
    --title) TITLE="${2:-}"; shift 2;;
    --content) CONTENT_FILE="${2:-}"; shift 2;;
    --type) TYPE="${2:-}"; shift 2;;
    --contains) CONTAINS="${2:-}"; shift 2;;
    --tags) TAGS="${2:-}"; shift 2;;
    --graduated-from) GFROM="${2:-}"; shift 2;;
    --graduated-at) GAT="${2:-}"; shift 2;;
    --authoring-mode) AMODE="${2:-}"; shift 2;;
    --props-json) PROPS_JSON="${2:-}"; shift 2;;
    --notion-version) NV="${2:-}"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) die "unknown arg: $1";;
  esac
done

[ -n "$DB" ] || die "--db is required"
[ -n "$TITLE" ] || die "--title is required"
[ -z "$CONTENT_FILE" ] || [ -f "$CONTENT_FILE" ] || die "content file not found: $CONTENT_FILE"
[ -z "$PROPS_JSON" ] || [ -f "$PROPS_JSON" ] || die "props-json not found: $PROPS_JSON"
command -v curl >/dev/null 2>&1 || die "curl not found"
command -v jq   >/dev/null 2>&1 || die "jq not found"
command -v python3 >/dev/null 2>&1 || die "python3 not found (needed for md->blocks)"
[ "$DRY_RUN" -eq 1 ] || [ -n "${NOTION_API_TOKEN:-}" ] || die "NOTION_API_TOKEN not set (put it in .env; run: set -a; . ./.env; set +a — bash/POSIX syntax; PowerShell users: \$env:NOTION_API_TOKEN='...' instead)"

# --- properties ---
if [ -n "$PROPS_JSON" ]; then
  PROPS="$(cat "$PROPS_JSON")"
else
  PROPS="$(jq -nc \
    --arg title "$TITLE" --arg type "$TYPE" --arg gfrom "$GFROM" \
    --arg gat "$GAT" --arg amode "$AMODE" --arg contains "$CONTAINS" --arg tags "$TAGS" '
    def ms($s): ($s | select(.!="") | split(",") | map({name:(gsub("^ +| +$";""))}));
    {Name:{title:[{type:"text",text:{content:$title}}]}}
    + (if $type   !="" then {type:{select:{name:$type}}} else {} end)
    + (if $gfrom  !="" then {graduated_from:{rich_text:[{type:"text",text:{content:$gfrom}}]}} else {} end)
    + (if $gat    !="" then {graduated_at:{date:{start:$gat}}} else {} end)
    + (if $amode  !="" then {authoring_mode:{select:{name:$amode}}} else {} end)
    + (if $contains!="" then {contains:{multi_select:ms($contains)}} else {} end)
    + (if $tags   !="" then {tags:{multi_select:ms($tags)}} else {} end)
  ')"
fi

# --- body markdown -> Notion blocks ---
md_to_blocks() {
  python3 - "$1" <<'PY'
import sys, json, re
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
WL = re.compile(r"\[\[([^\]]+)\]\]")
def rich(t):
    out, pos = [], 0
    for m in WL.finditer(t):
        if m.start() > pos: out.append({"type":"text","text":{"content":t[pos:m.start()]}})
        out.append({"type":"text","text":{"content":m.group(1)},"annotations":{"bold":True}})
        pos = m.end()
    if pos < len(t): out.append({"type":"text","text":{"content":t[pos:]}})
    return out or [{"type":"text","text":{"content":""}}]
blocks, i = [], 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("```"):
        lang = ln[3:].strip() or "plain text"
        if lang == "text": lang = "plain text"
        buf = []; i += 1
        while i < len(lines) and not lines[i].startswith("```"): buf.append(lines[i]); i += 1
        i += 1
        blocks.append({"type":"code","code":{"rich_text":[{"type":"text","text":{"content":"\n".join(buf)}}],"language":lang}}); continue
    if ln.startswith("# "): i += 1; continue
    if ln.startswith("## "): blocks.append({"type":"heading_2","heading_2":{"rich_text":rich(ln[3:])}})
    elif ln.startswith("### "): blocks.append({"type":"heading_3","heading_3":{"rich_text":rich(ln[4:])}})
    elif ln.startswith("- "): blocks.append({"type":"bulleted_list_item","bulleted_list_item":{"rich_text":rich(ln[2:])}})
    elif ln.strip(): blocks.append({"type":"paragraph","paragraph":{"rich_text":rich(ln)}})
    i += 1
print(json.dumps(blocks, ensure_ascii=False))
PY
}
if [ -n "$CONTENT_FILE" ]; then CHILDREN="$(md_to_blocks "$CONTENT_FILE")"; else CHILDREN="[]"; fi

# --- assemble payload ---
PAYLOAD_FILE="$(mktemp -t notion-grad.XXXXXX)"
trap 'rm -f "$PAYLOAD_FILE"' EXIT
jq -nc --arg db "$DB" --argjson props "$PROPS" --argjson children "$CHILDREN" \
  '{parent:{database_id:$db}, properties:$props, children:$children}' > "$PAYLOAD_FILE"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY-RUN: POST https://api.notion.com/v1/pages  (Notion-Version $NV)" >&2
  echo "  properties: $(printf '%s' "$PROPS" | jq -c 'keys')" >&2
  echo "  children:   $(printf '%s' "$CHILDREN" | jq 'length') blocks" >&2
  jq -nc --arg t "$TITLE" '{id:"<dry-run>", url:"<dry-run>", title:$t}'
  exit 0
fi

# curl+retry POST (rides out SSL EOF flakiness; honors HTTPS_PROXY)
napi_post() { # path bodyfile
  path="$1"; bf="$2"; attempt=0; max=8; resp=""
  while [ "$attempt" -lt "$max" ]; do
    attempt=$((attempt + 1))
    resp="$(curl -sS -X POST "https://api.notion.com/v1/$path" \
      -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: $NV" \
      -H "Content-Type: application/json" --data @"$bf" 2>/dev/null)"; rc=$?
    [ "$rc" -eq 0 ] && [ -n "$resp" ] && { printf '%s' "$resp"; return 0; }
    sleep "$attempt"
  done
  return 1
}
napi_get() { # path
  path="$1"; attempt=0; max=8; resp=""
  while [ "$attempt" -lt "$max" ]; do
    attempt=$((attempt + 1))
    resp="$(curl -sS "https://api.notion.com/v1/$path" \
      -H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: $NV" 2>/dev/null)"; rc=$?
    [ "$rc" -eq 0 ] && [ -n "$resp" ] && { printf '%s' "$resp"; return 0; }
    sleep "$attempt"
  done
  return 1
}

RESP="$(napi_post "pages" "$PAYLOAD_FILE")" || die "network give-up creating page (proxy/SSL); retry"
if [ "$(printf '%s' "$RESP" | jq -r '.object // ""')" = "error" ]; then
  die "Notion API error: $(printf '%s' "$RESP" | jq -r '.code + ": " + .message')"
fi
PAGE_ID="$(printf '%s' "$RESP" | jq -r '.id')"
PAGE_URL="$(printf '%s' "$RESP" | jq -r '.url')"
[ -n "$PAGE_ID" ] && [ "$PAGE_ID" != "null" ] || die "create returned no id: $RESP"

# read-back verify (title round-trips)
BACK="$(napi_get "pages/$PAGE_ID")" || { echo "warn: read-back request failed; verify manually" >&2; BACK=""; }
if [ -n "$BACK" ]; then
  BT="$(printf '%s' "$BACK" | jq -r '[.properties[]|select(.type=="title")|.title[]?.plain_text]|join("")' 2>/dev/null || echo "")"
  case "$BT" in
    *"$TITLE"*) : ;;
    *) echo "warn: read-back title mismatch (got '$BT'); verify manually" >&2;;
  esac
fi

jq -nc --arg id "$PAGE_ID" --arg url "$PAGE_URL" '{id:$id, url:$url}'
