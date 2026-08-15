#!/usr/bin/env bash
# notion-graduate.sh — Project Cairn graduation adapter for the Notion provider.
#
# Encodes the verified adapter constraints (see references/graduation/notion.md,
# references/provider-interface.md, and cairn Notion Provider notes):
#   - Direct REST via curl (honors HTTPS_PROXY), NOT the `ntn` CLI (unreliable
#     behind a proxy: fetches an OpenAPI spec to resolve endpoints, does not
#     honor the proxy, fails PATCH/query).
#   - Per-request retry with backoff to ride out random SSL EOF flakiness.
#   - Pin Notion-Version (default 2022-06-28: classic single-source database;
#     avoids the 2025-09-03+ data-source semantics).
#   - Create mode POSTs /v1/pages carrying an Idempotency-Key (a retry after a
#     client-side SSL EOF cannot duplicate the page). Body blocks are written
#     in <=100-block chunks (Notion request limit); long text segments are
#     split at 2000 chars. Update mode (`--page-id`) PATCHes properties,
#     appends the replacement body in chunks, THEN archives the old children —
#     a mid-flight failure degrades to a duplicated body, never an empty page.
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
#     [--page-id EXISTING_PAGE_ID]
#     [--type knowledge_note] [--contains a,b,c] [--tags a,b,c]
#     [--graduated-from TEXT] [--graduated-at YYYY-MM-DD]
#     [--contributor NAME]... [--graduated-by NAME]...
#     [--authoring-mode ai_generated] [--props-json FILE] [--dry-run]
#
# Output (stdout): JSON { id, url }
set -uo pipefail

NV="${NOTION_API_VERSION:-2022-06-28}"
DB=""; PAGE_ID=""; TITLE=""; CONTENT_FILE=""; PROPS_JSON=""
TYPE=""; CONTAINS=""; TAGS=""; GFROM=""; GAT=""; AMODE=""
CONTRIBUTOR_ENTRIES=()
GRADUATED_BY_ENTRIES=()
DRY_RUN=0

die() { echo "error: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --db) DB="${2:-}"; shift 2;;
    --page-id) PAGE_ID="${2:-}"; shift 2;;
    --title) TITLE="${2:-}"; shift 2;;
    --content) CONTENT_FILE="${2:-}"; shift 2;;
    --type) TYPE="${2:-}"; shift 2;;
    --contains) CONTAINS="${2:-}"; shift 2;;
    --tags) TAGS="${2:-}"; shift 2;;
    --graduated-from) GFROM="${2:-}"; shift 2;;
    --graduated-at) GAT="${2:-}"; shift 2;;
    --contributor)
      [ -n "${2:-}" ] || die "--contributor requires a non-empty display name"
      CONTRIBUTOR_ENTRIES+=("$2"); shift 2;;
    --graduated-by)
      [ -n "${2:-}" ] || die "--graduated-by requires a non-empty display name"
      GRADUATED_BY_ENTRIES+=("$2"); shift 2;;
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
json_string_array() {
  printf '%s\n' "$@" | jq -Rsc '
    split("\n")
    | map(select(length > 0))
    | reduce .[] as $value ([]; if index($value) == null then . + [$value] else . end)
  '
}
CONTRIBUTORS_JSON="$(json_string_array "${CONTRIBUTOR_ENTRIES[@]:-}")"
GRADUATED_BY_JSON="$(json_string_array "${GRADUATED_BY_ENTRIES[@]:-}")"

if [ -n "$PROPS_JSON" ]; then
  PROPS="$(cat "$PROPS_JSON")"
else
  PROPS="$(jq -nc \
    --arg title "$TITLE" --arg type "$TYPE" --arg gfrom "$GFROM" \
    --arg gat "$GAT" --arg amode "$AMODE" --arg contains "$CONTAINS" --arg tags "$TAGS" \
    --argjson contributors "$CONTRIBUTORS_JSON" --argjson graduated_by "$GRADUATED_BY_JSON" '
    def ms($s): ($s | select(.!="") | split(",") | map({name:(gsub("^ +| +$";""))}));
    {Name:{title:[{type:"text",text:{content:$title}}]}}
    + (if $type   !="" then {type:{select:{name:$type}}} else {} end)
    + (if $gfrom  !="" then {graduated_from:{rich_text:[{type:"text",text:{content:$gfrom}}]}} else {} end)
    + (if $gat    !="" then {graduated_at:{date:{start:$gat}}} else {} end)
    + (if $amode  !="" then {authoring_mode:{select:{name:$amode}}} else {} end)
    + (if $contains!="" then {contains:{multi_select:ms($contains)}} else {} end)
    + (if $tags   !="" then {tags:{multi_select:ms($tags)}} else {} end)
    + (if ($contributors|length)>0 then {contributors:{multi_select:($contributors|map({name:.}))}} else {} end)
    + (if ($graduated_by|length)>0 then {graduated_by:{multi_select:($graduated_by|map({name:.}))}} else {} end)
  ')"
fi

# --- body markdown -> Notion blocks ---
# Long text segments are split at 2000 chars (Notion rich_text limit).
md_to_blocks() {
  python3 - "$1" <<'PY'
import sys, json, re
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
WL = re.compile(r"\[\[([^\]]+)\]\]")
LIMIT = 2000
def text_items(t, bold=False):
    out = []
    for k in range(0, len(t), LIMIT):
        item = {"type":"text","text":{"content":t[k:k+LIMIT]}}
        if bold: item["annotations"] = {"bold": True}
        out.append(item)
    return out
def rich(t):
    out, pos = [], 0
    for m in WL.finditer(t):
        if m.start() > pos: out.extend(text_items(t[pos:m.start()]))
        out.extend(text_items(m.group(1), bold=True))
        pos = m.end()
    if pos < len(t): out.extend(text_items(t[pos:]))
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
        blocks.append({"type":"code","code":{"rich_text":(text_items("\n".join(buf)) or [{"type":"text","text":{"content":""}}]),"language":lang}}); continue
    if ln.startswith("# "): i += 1; continue
    if ln.startswith(">"):
        buf = []
        while i < len(lines) and lines[i].startswith(">"):
            buf.append(re.sub(r"^> ?", "", lines[i]))
            i += 1
        quote_text = "\n".join(buf)
        if quote_text.strip():
            blocks.append({"type":"quote","quote":{"rich_text":rich(quote_text)}})
        continue
    if ln.startswith("## "): blocks.append({"type":"heading_2","heading_2":{"rich_text":rich(ln[3:])}})
    elif ln.startswith("### "): blocks.append({"type":"heading_3","heading_3":{"rich_text":rich(ln[4:])}})
    elif ln.startswith("- "): blocks.append({"type":"bulleted_list_item","bulleted_list_item":{"rich_text":rich(ln[2:])}})
    elif ln.strip(): blocks.append({"type":"paragraph","paragraph":{"rich_text":rich(ln)}})
    i += 1
print(json.dumps(blocks, ensure_ascii=False))
PY
}
# Git Bash/Windows note: python's text-mode stdout may emit CRLF and jqlang's
# mingw jq.exe does too; CR inside JSON is legal whitespace, so stripping it
# here is safe everywhere (the tr is a no-op on Linux/WSL).
if [ -n "$CONTENT_FILE" ]; then
  CHILDREN="$(md_to_blocks "$CONTENT_FILE" | tr -d '\r')"
  [ -n "$CHILDREN" ] || die "python3 produced no output for markdown->blocks — on Windows ensure a real Python is on PATH (the Microsoft Store alias emits nothing in pipes), or run under WSL"
else
  CHILDREN="[]"
fi

# --- assemble payload: properties + the FIRST <=100-block chunk of the body.
#     The remaining blocks are appended after create in <=100-block chunks
#     (Notion's per-request block limit). ---
CHUNK=100
IDEM_KEY="cairn-$(date +%s)-$$-${RANDOM}"
TOTAL="$(printf '%s' "$CHILDREN" | jq 'length')"
FIRST_CHILDREN="$(printf '%s' "$CHILDREN" | jq -c ".[0:$CHUNK]")"
PAYLOAD_FILE="$(mktemp -t notion-grad.XXXXXX)"
TMP_FILES="$PAYLOAD_FILE"
trap 'rm -f $TMP_FILES' EXIT
jq -nc --arg db "$DB" --argjson props "$PROPS" --argjson children "$FIRST_CHILDREN" \
  '{parent:{database_id:$db}, properties:$props, children:$children}' > "$PAYLOAD_FILE"

# append_children_chunks PAGE_ID CHILDREN_JSON — append in <=100-block chunks.
append_children_chunks() {
  page_id="$1"; children_json="$2"
  total="$(printf '%s' "$children_json" | jq 'length')"
  start=0
  while [ "$start" -lt "$total" ]; do
    end=$((start + CHUNK))
    part="$(printf '%s' "$children_json" | jq -c ".[$start:$end]")"
    part_file="$(mktemp -t notion-part.XXXXXX)"
    TMP_FILES="$TMP_FILES $part_file"
    printf '%s' "{\"children\":$part}" > "$part_file"
    resp="$(napi_write PATCH "blocks/$page_id/children" "$part_file")" || die "network give-up appending body chunk (proxy/SSL); retry"
    [ "$(printf '%s' "$resp" | jq -r '.object // ""')" != "error" ] || die "Notion API error appending body chunk: $(printf '%s' "$resp" | jq -r '.code + ": " + .message')"
    rm -f "$part_file"
    start="$end"
  done
}

if [ "$DRY_RUN" -eq 1 ]; then
  REQS=$(( (TOTAL + CHUNK - 1) / CHUNK ))
  if [ -n "$PAGE_ID" ]; then
    echo "DRY-RUN: PATCH https://api.notion.com/v1/pages/$PAGE_ID properties; append $TOTAL replacement children in $REQS chunk(s); DELETE existing children afterwards  (Notion-Version $NV)" >&2
  else
    echo "DRY-RUN: POST https://api.notion.com/v1/pages (Idempotency-Key; Notion-Version $NV); append remaining children in chunks ($REQS total append request(s))" >&2
  fi
  echo "  properties: $(printf '%s' "$PROPS" | jq -c 'keys')" >&2
  echo "  children:   $TOTAL blocks" >&2
  echo "  child types: $(printf '%s' "$CHILDREN" | jq -c '[.[].type]')" >&2
  jq -nc --arg id "${PAGE_ID:-<dry-run>}" --arg t "$TITLE" '{id:$id, url:"<dry-run>", title:$t}'
  exit 0
fi

# curl+retry mutating request (rides out SSL EOF flakiness; honors HTTPS_PROXY).
# Optional 4th arg = Idempotency-Key (POST pages/databases), stable across the
# retries of this one call so a retried create cannot duplicate the object.
napi_write() { # method path [bodyfile] [idempotency-key]
  method="$1"; path="$2"; bf="${3:-}"; idem="${4:-}"; attempt=0; max=8; resp=""
  HDRS=(-H "Authorization: Bearer $NOTION_API_TOKEN" -H "Notion-Version: $NV")
  DATA=()
  [ -n "$bf" ] && { HDRS+=(-H "Content-Type: application/json"); DATA=(--data "@$bf"); }
  [ -n "$idem" ] && HDRS+=(-H "Idempotency-Key: $idem")
  while [ "$attempt" -lt "$max" ]; do
    attempt=$((attempt + 1))
    resp="$(curl -sS -X "$method" "https://api.notion.com/v1/$path" "${HDRS[@]}" "${DATA[@]}" 2>/dev/null)"; rc=$?
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

if [ -n "$PAGE_ID" ]; then
  PROPERTIES_FILE="$(mktemp -t notion-props.XXXXXX)"
  BLOCK_IDS_FILE="$(mktemp -t notion-blocks.XXXXXX)"
  TMP_FILES="$TMP_FILES $PROPERTIES_FILE $BLOCK_IDS_FILE"
  jq -nc --argjson props "$PROPS" '{properties:$props}' > "$PROPERTIES_FILE"
  RESP="$(napi_write PATCH "pages/$PAGE_ID" "$PROPERTIES_FILE")" || die "network give-up updating page properties (proxy/SSL); retry"
  if [ "$(printf '%s' "$RESP" | jq -r '.object // ""')" = "error" ]; then
    die "Notion API error updating page: $(printf '%s' "$RESP" | jq -r '.code + ": " + .message')"
  fi
  # Snapshot the current children BEFORE appending the replacement body.
  cursor=""
  while :; do
    child_path="blocks/$PAGE_ID/children?page_size=100"
    [ -z "$cursor" ] || child_path="$child_path&start_cursor=$cursor"
    existing_children="$(napi_get "$child_path")" || die "network give-up listing existing page body"
    if [ "$(printf '%s' "$existing_children" | jq -r '.object // ""')" = "error" ]; then
      die "Notion API error listing page body: $(printf '%s' "$existing_children" | jq -r '.code + ": " + .message')"
    fi
    printf '%s' "$existing_children" | jq -r '.results[]?.id' | tr -d '\r' >> "$BLOCK_IDS_FILE"
    [ "$(printf '%s' "$existing_children" | jq -r '.has_more // false')" = "true" ] || break
    cursor="$(printf '%s' "$existing_children" | jq -r '.next_cursor')"
  done
  # Append the replacement body first (chunked), THEN archive the old blocks:
  # a failure in between leaves a duplicated body, not a lost one.
  append_children_chunks "$PAGE_ID" "$CHILDREN"
  while IFS= read -r block_id; do
    [ -n "$block_id" ] || continue
    deleted="$(napi_write DELETE "blocks/$block_id")" || die "network give-up deleting existing block $block_id"
    [ "$(printf '%s' "$deleted" | jq -r '.object // ""')" != "error" ] || die "Notion API error deleting block $block_id"
  done < "$BLOCK_IDS_FILE"
  PAGE_URL="$(printf '%s' "$RESP" | jq -r '.url // ""')"
else
  RESP="$(napi_write POST "pages" "$PAYLOAD_FILE" "$IDEM_KEY")" || die "network give-up creating page (proxy/SSL); retry"
  if [ "$(printf '%s' "$RESP" | jq -r '.object // ""')" = "error" ]; then
    die "Notion API error: $(printf '%s' "$RESP" | jq -r '.code + ": " + .message')"
  fi
  PAGE_ID="$(printf '%s' "$RESP" | jq -r '.id')"
  PAGE_URL="$(printf '%s' "$RESP" | jq -r '.url')"
  # Append any body beyond the first chunk carried in the POST payload.
  REST="$(printf '%s' "$CHILDREN" | jq -c ".[$CHUNK:]")"
  append_children_chunks "$PAGE_ID" "$REST"
fi
if [ "$(printf '%s' "$RESP" | jq -r '.object // ""')" = "error" ]; then
  die "Notion API error: $(printf '%s' "$RESP" | jq -r '.code + ": " + .message')"
fi
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
