#!/usr/bin/env python3
"""notion-graduate-batch.py — batch graduation of interlinked notes into a Notion DB.

Two-pass so `[[wikilinks]]` between the graduated notes become REAL Notion page
mentions (a single-note adapter can't resolve forward/circular refs):
  Pass 1: create every page (properties only), collect title -> page id.
  Pass 2: append each body, resolving [[Title]] -> page mention when Title is
          one of the batch (else bold text fallback).

Why python (not the bash adapter): the two-pass needs a title->id graph and
mention injection into rich_text — awkward in bash/jq. Uses urllib (honors
HTTPS_PROXY) + per-request retry to ride out SSL EOF flakiness, same transport
lesson as notion-graduate.sh. `ntn` CLI is NOT used (proxy-unreliable).

Title of each note = its filename stem (matches how wikilinks reference it).
Frontmatter maps to DB properties. Notion-Version pinned to 2022-06-28.

Requires: python3 + PyYAML. Token in env NOTION_API_TOKEN.

Usage:
  notion-graduate-batch.py --db DATABASE_ID --graduated-at YYYY-MM-DD \
      [--src-dir DIR | FILE.md ...] [--repo-prefix PATH] [--dry-run]
Output (stdout): JSON { "<title>": "<page id>", ... }
"""
import os, re, sys, glob, json, time, ssl, argparse, urllib.request, urllib.error

NV = os.environ.get("NOTION_API_VERSION", "2022-06-28")
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")


def api(method, path, body=None, tries=8, token=None):
    url = f"https://api.notion.com/v1/{path}"
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for k in range(tries):
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {token}", "Notion-Version": NV,
            "Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            return {"__err__": e.code, "body": e.read().decode()[:300]}
        except (ssl.SSLError, urllib.error.URLError, TimeoutError) as e:
            last = e; time.sleep(1.5 * (k + 1))   # backoff for SSL EOF flakiness
    raise SystemExit(f"NET give up {method} {path}: {type(last).__name__} {str(last)[:120]}")


def parse_note(fp):
    import yaml
    raw = open(fp, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"no frontmatter: {fp}")
    return os.path.splitext(os.path.basename(fp))[0], yaml.safe_load(m.group(1)), m.group(2)


def gfrom_text(gf, repo_prefix):
    if isinstance(gf, str):
        return gf
    out = []
    for e in gf or []:
        p = e.get("path", "")
        if repo_prefix and p.startswith(repo_prefix):
            p = p[len(repo_prefix):]
        out.append(f"{e.get('project','')}: {p}".strip(": "))
    return "\n".join(out)


def rich(text, idmap):
    out, pos = [], 0
    for m in WIKILINK.finditer(text):
        if m.start() > pos:
            out.append({"type": "text", "text": {"content": text[pos:m.start()]}})
        t = m.group(1)
        if t in idmap:
            out.append({"type": "mention", "mention": {"type": "page", "page": {"id": idmap[t]}}})
        else:
            out.append({"type": "text", "text": {"content": t}, "annotations": {"bold": True}})
        pos = m.end()
    if pos < len(text):
        out.append({"type": "text", "text": {"content": text[pos:]}})
    return out or [{"type": "text", "text": {"content": ""}}]


def md_to_blocks(body, idmap):
    blocks, lines, i = [], body.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            lang = ln[3:].strip() or "plain text"
            if lang == "text":
                lang = "plain text"
            buf = []; i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            blocks.append({"type": "code", "code": {
                "rich_text": [{"type": "text", "text": {"content": "\n".join(buf)}}], "language": lang}})
            continue
        if ln.startswith("# "):
            i += 1; continue
        if ln.startswith("## "):
            blocks.append({"type": "heading_2", "heading_2": {"rich_text": rich(ln[3:], idmap)}})
        elif ln.startswith("### "):
            blocks.append({"type": "heading_3", "heading_3": {"rich_text": rich(ln[4:], idmap)}})
        elif ln.startswith("- "):
            blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rich(ln[2:], idmap)}})
        elif ln.strip():
            blocks.append({"type": "paragraph", "paragraph": {"rich_text": rich(ln, idmap)}})
        i += 1
    return blocks


def props(title, fm, grad_at, repo_prefix, idmap):
    p = {"Name": {"title": [{"type": "text", "text": {"content": title}}]}}
    if grad_at:
        p["graduated_at"] = {"date": {"start": grad_at}}
    if fm.get("type"):
        p["type"] = {"select": {"name": fm["type"]}}
    if fm.get("contains"):
        p["contains"] = {"multi_select": [{"name": c} for c in fm["contains"]]}
    if fm.get("tags"):
        p["tags"] = {"multi_select": [{"name": t} for t in fm["tags"]]}
    if fm.get("authoring_mode"):
        p["authoring_mode"] = {"select": {"name": fm["authoring_mode"]}}
    gf = gfrom_text(fm.get("graduated_from"), repo_prefix)
    if gf:
        p["graduated_from"] = {"rich_text": rich(gf, idmap)}
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--graduated-at", default="")
    ap.add_argument("--src-dir", default="")
    ap.add_argument("--repo-prefix", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("files", nargs="*")
    a = ap.parse_args()

    token = os.environ.get("NOTION_API_TOKEN")
    if not a.dry_run and not token:
        raise SystemExit("NOTION_API_TOKEN not set")

    files = list(a.files)
    if a.src_dir:
        files += [f for f in sorted(glob.glob(os.path.join(a.src_dir, "*.md")))
                  if os.path.basename(f) != "INDEX.md"]
    if not files:
        raise SystemExit("no input notes (pass files or --src-dir)")

    notes = [parse_note(f) for f in files]

    if a.dry_run:
        for title, fm, body in notes:
            idmap_preview = {t for t, _, _ in notes}
            nblocks = len(md_to_blocks(body, {}))
            print(f"DRY-RUN would graduate: {title}  ({nblocks} blocks, props from frontmatter)", file=sys.stderr)
        print(json.dumps({t: "<dry-run>" for t, _, _ in notes}, ensure_ascii=False))
        return

    # idempotency: existing (non-archived) titles
    existing = {}
    q = api("POST", f"databases/{a.db}/query", {"page_size": 100}, token=token)
    if "__err__" not in q:
        for r in q["results"]:
            nm = "".join(x["plain_text"] for x in r["properties"]["Name"]["title"])
            existing[nm] = r["id"]

    # Pass 1: create pages (properties only)
    idmap = dict(existing)
    for title, fm, body in notes:
        if title in idmap:
            print(f"  skip(existing) {title}", file=sys.stderr); continue
        res = api("POST", "pages",
                  {"parent": {"database_id": a.db}, "properties": props(title, fm, a.graduated_at, a.repo_prefix, {})},
                  token=token)
        if "__err__" in res:
            raise SystemExit(f"create failed {title}: {res}")
        idmap[title] = res["id"]
        print(f"  created {title} -> {res['id']}", file=sys.stderr)

    # Pass 2: append bodies with mentions resolved
    for title, fm, body in notes:
        pid = idmap[title]
        kids = api("GET", f"blocks/{pid}/children?page_size=1", token=token)
        if "__err__" not in kids and kids.get("results"):
            print(f"  body-exists skip {title}", file=sys.stderr); continue
        r = api("PATCH", f"blocks/{pid}/children", {"children": md_to_blocks(body, idmap)}, token=token)
        if "__err__" in r:
            raise SystemExit(f"append failed {title}: {r}")
        print(f"  body -> {title}", file=sys.stderr)

    print(json.dumps({t: idmap[t] for t, _, _ in notes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
