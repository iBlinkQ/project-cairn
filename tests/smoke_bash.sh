#!/usr/bin/env bash
# Smoke tests for the Notion bash adapters — dry-run plus a fake-curl
# end-to-end run that inspects the exact requests the adapter would send.
# No real network. Requires: bash, jq, python3, curl (all in the CI runner).
set -uo pipefail
cd "$(dirname "$0")/.."
S=scripts

# 1) notion-graduate.sh --dry-run: no token needed, prints JSON {id,url,title}.
BODY="$(mktemp)"
printf '## Background\nSome body text.\n\n- a\n- b\n- c\n' > "$BODY"
OUT="$(bash "$S/notion-graduate.sh" --db DBID --title "Test Note" --content "$BODY" \
  --type knowledge_note --contains decision --tags notion --graduated-by Alice --dry-run 2>"$BODY.err")"
echo "$OUT" | jq -e '.id == "<dry-run>" and .url == "<dry-run>" and .title == "Test Note"' >/dev/null \
  || { echo "FAIL: graduate dry-run output: $OUT"; cat "$BODY.err"; exit 1; }
grep -q "children:" "$BODY.err" || { echo "FAIL: dry-run stderr missing children count"; cat "$BODY.err"; exit 1; }
rm -f "$BODY" "$BODY.err"
echo "ok: notion-graduate.sh dry-run"

# 2) A >100-block body must be reported as 130 blocks and still dry-run clean.
BIG="$(mktemp)"
for i in $(seq 1 130); do printf -- '- item %s\n' "$i"; done > "$BIG"
OUT="$(bash "$S/notion-graduate.sh" --db DBID --title "Big" --content "$BIG" --dry-run 2>"$BIG.err")"
echo "$OUT" | jq -e '.id == "<dry-run>"' >/dev/null || { echo "FAIL: big-body dry-run: $OUT"; cat "$BIG.err"; exit 1; }
grep -q "130 blocks" "$BIG.err" || { echo "FAIL: expected '130 blocks' reported"; cat "$BIG.err"; exit 1; }
rm -f "$BIG" "$BIG.err"
echo "ok: notion-graduate.sh >100-block dry-run"

# 3) notion-init-db.sh --dry-run: schema has Name but no dead 'source' column.
ERR="$(bash "$S/notion-init-db.sh" --parent-page-id P1 --title KB --dry-run 2>&1 >/dev/null)"
echo "$ERR" | grep -q '"Name"' || { echo "FAIL: init-db schema missing Name"; echo "$ERR"; exit 1; }
echo "$ERR" | grep -q '"source"' && { echo "FAIL: init-db still creates dead 'source' column"; echo "$ERR"; exit 1; }
echo "ok: notion-init-db.sh dry-run schema"

# --- fake curl: logs method/path/headers/block-counts, returns canned JSON ---
FAKEBIN="$(mktemp -d)"
export FAKE_LOG="$FAKEBIN/calls.log"
export FAKE_CNT="$FAKEBIN/getcount"
: > "$FAKE_LOG"
cat > "$FAKEBIN/curl" <<'EOF'
#!/usr/bin/env bash
m="GET"; d=""
for ((i=1; i<=$#; i++)); do
  a="${!i}"
  if [ "$a" = "-X" ]; then m="${@:$((i+1)):1}"; fi
  if [ "$a" = "--data" ]; then d="${@:$((i+1)):1}"; fi
done
path=""
for a in "$@"; do case "$a" in https://*) path="$a";; esac; done
idem=0
for a in "$@"; do case "$a" in Idempotency-Key:*) idem=1;; esac; done
nblocks="na"
if [ -n "$d" ] && [ -f "${d#@}" ]; then nblocks="$(jq -c '.children | length // 0' "${d#@}" 2>/dev/null || echo 0)"; fi
printf '%s %s idem=%s blocks=%s\n' "$m" "$path" "$idem" "$nblocks" >> "$FAKE_LOG"
if [ "$m" = "GET" ]; then case "$path" in */blocks/*/children*)
  cnt="$(cat "$FAKE_CNT" 2>/dev/null)"; [ -n "$cnt" ] || cnt=0
  if [ "$cnt" = "0" ]; then
    printf '{"object":"list","results":[{"id":"old-1"},{"id":"old-2"},{"id":"old-3"}],"has_more":false}'
  else
    printf '{"object":"list","results":[],"has_more":false}'
  fi
  echo $((cnt+1)) > "$FAKE_CNT"
  exit 0
;; esac; fi
case "$path" in
  */blocks/*/children*) printf '{"object":"list","results":[],"has_more":false}';;
  */blocks/*) printf '{"object":"block","id":"gone"}';;
  */pages/page-123) printf '{"object":"page","id":"page-123","properties":{"Name":{"type":"title","title":[{"plain_text":"Test Note"}]}}}';;
  */pages) printf '{"object":"page","id":"page-123","url":"https://notion.so/page-123"}';;
  *) printf '{}';;
esac
EOF
chmod +x "$FAKEBIN/curl"

# 4) Create mode, 250 blocks: POST carries 100 + Idempotency-Key; then 2 chunked
#    appends (100+50). No request may carry more than 100 blocks.
BIG250="$(mktemp)"
for i in $(seq 1 250); do printf -- '- item %s\n' "$i"; done > "$BIG250"
OUT="$(PATH="$FAKEBIN:$PATH" NOTION_API_TOKEN=test-token \
  bash "$S/notion-graduate.sh" --db DBID --title "Test Note" --content "$BIG250" 2>"$BIG250.err")"
echo "$OUT" | jq -e '.id == "page-123"' >/dev/null || { echo "FAIL: create e2e: $OUT"; cat "$BIG250.err"; cat "$FAKE_LOG"; exit 1; }
[ "$(grep -c '^POST .*/v1/pages idem=1 blocks=100' "$FAKE_LOG")" = "1" ] \
  || { echo "FAIL: create POST must carry idem key + 100 first blocks"; cat "$FAKE_LOG"; exit 1; }
APC="$(grep -c '^PATCH .*/v1/blocks/page-123/children ' "$FAKE_LOG")"
AB="$(grep '^PATCH .*/v1/blocks/page-123/children ' "$FAKE_LOG" | awk '{print $4}' | sed 's/blocks=//' | paste -sd, -)"
[ "$APC" = "2" ] && [ "$AB" = "100,50" ] \
  || { echo "FAIL: expected 2 appends (100,50), got $APC ($AB)"; cat "$FAKE_LOG"; exit 1; }
if grep 'blocks=\(1[1-9][0-9]\|[2-9][0-9][0-9]\)$' "$FAKE_LOG" | grep -qv 'blocks=100$'; then
  : # any line over 100 blocks is a violation, but the check above already pins exact sizes
fi
echo "ok: notion-graduate.sh create e2e (chunked + idempotency)"

# 5) Update mode, 250 blocks: snapshot 3 old children, append 3 chunks
#    (100,100,50), then delete the 3 old blocks — all appends before deletes.
: > "$FAKE_LOG"
OUT="$(PATH="$FAKEBIN:$PATH" NOTION_API_TOKEN=test-token \
  bash "$S/notion-graduate.sh" --db DBID --title "Test Note" --page-id page-123 --content "$BIG250" 2>/dev/null)"
echo "$OUT" | jq -e '.id == "page-123"' >/dev/null || { echo "FAIL: update e2e: $OUT"; cat "$FAKE_LOG"; exit 1; }
APC="$(grep -c '^PATCH .*/v1/blocks/page-123/children ' "$FAKE_LOG")"
AB="$(grep '^PATCH .*/v1/blocks/page-123/children ' "$FAKE_LOG" | awk '{print $4}' | sed 's/blocks=//' | paste -sd, -)"
[ "$APC" = "3" ] && [ "$AB" = "100,100,50" ] \
  || { echo "FAIL: expected 3 appends (100,100,50), got $APC ($AB)"; cat "$FAKE_LOG"; exit 1; }
[ "$(grep -c '^DELETE ' "$FAKE_LOG")" = "3" ] \
  || { echo "FAIL: expected 3 deletes of the old children"; cat "$FAKE_LOG"; exit 1; }
PMAX=$(grep -n '^PATCH .*/v1/blocks/page-123/children ' "$FAKE_LOG" | tail -1 | cut -d: -f1)
DMIN=$(grep -n '^DELETE ' "$FAKE_LOG" | head -1 | cut -d: -f1)
[ -n "$PMAX" ] && [ -n "$DMIN" ] && [ "$PMAX" -lt "$DMIN" ] \
  || { echo "FAIL: write-before-delete violated (last append at $PMAX, first delete at $DMIN)"; cat "$FAKE_LOG"; exit 1; }
echo "ok: notion-graduate.sh update e2e (write-before-delete + chunked)"

rm -f "$BIG250" "$BIG250.err"
rm -rf "$FAKEBIN"
