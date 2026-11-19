#!/usr/bin/env python3
"""Export canonical CATALOG.md Markdown into the public PlayForge JSON contract."""
import argparse
import hashlib
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

CANONICAL = "https://github.com/ZeroLu/awesome-claude-games/blob/main/CATALOG.md"
LINK = re.compile(r"\[([^\]]+)\]\((https://[^()\s]+)\)")
SECTION = re.compile(r"^## (.+?)(?: \(\d+\))?$")
BULLET = re.compile(r"^- \*\*(.+?)\*\* · (.+)$")

def parse(markdown):
    games = []
    section = ""
    for line in markdown.splitlines():
        heading = SECTION.match(line)
        if heading:
            section = heading.group(1)
            continue
        if line.startswith("| ["):
            head, description, tail = re.split(r" (?<!\\)\| ", line[2:].strip().removesuffix(" |"), maxsplit=2)
            title, url = LINK.fullmatch(head).groups()
            pairs = LINK.findall(tail)
            game_type = "browser"
            attribution = re.split(r"\s*\[(?:Creator source|Creator notes)\]", tail, maxsplit=1)[0]
        else:
            bullet = BULLET.match(line)
            if not bullet:
                continue
            title, tail = bullet.groups()
            game_type = "local" if section == "Local builds" else "demo"
            pairs = LINK.findall(tail)
            url = pairs[0][1]
            description = tail[:tail.find("[")].strip()
            attribution = description
        if not urlsplit(url).hostname or not pairs:
            raise ValueError(f"Missing canonical URL or creator source: {title}")
        source = next((link for label,link in reversed(pairs) if "creator" in label.lower()), pairs[-1][1])
        stem = re.sub(r"[^a-z0-9]+","-",unicodedata.normalize("NFKD",title).encode("ascii","ignore").decode().lower()).strip("-")
        identity = stem or "game-" + hashlib.sha256(url.encode()).hexdigest()[:10]
        if any(g["id"] == identity for g in games):
            raise ValueError(f"Duplicate game identifier: {identity}")
        playability = "download" if game_type == "local" and "download" in pairs[0][0].lower() else "source" if game_type == "local" else "browser"
        games.append(dict(id=identity,title=title,description=description,category=section,type=game_type,
            url=url,sourceUrl=source,attribution=attribution,playability=playability,links=[dict(label=a,url=b) for a,b in pairs],
            image=None,x=[dict(url=link,views=None,checkedAt=None) for _,link in pairs
                          if (urlsplit(link).hostname or "").lower() in {"x.com","www.x.com","twitter.com","www.twitter.com"}
                          and re.search(r"/status/\d+",urlsplit(link).path)],embed=dict(status="not_applicable" if game_type=="local" else "unknown",url=None,
            reason="Requires a download or local setup." if game_type=="local" else "Frame policy not yet checked.",checkedAt=None)))
    expected = re.search(r"\*\*(\d+) browser games\*\*, plus (\d+) local builds and (\d+) interactive demos",markdown)
    counts = Counter(g["type"] for g in games)
    if not expected or [counts[t] for t in ("browser","local","demo")] != list(map(int,expected.groups())):
        raise ValueError(f"Catalog entry count does not match the directory heading: {dict(counts)}")
    return dict(version=1,source=CANONICAL,sourceSha256=hashlib.sha256(markdown.encode()).hexdigest(),counts=dict(counts),games=games)

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("catalog",type=Path)
    cli.add_argument("output",type=Path)
    cli.add_argument("--metadata",type=Path,help="Optional verification and presentation map keyed by game id.")
    args=cli.parse_args()
    catalog=parse(args.catalog.read_bytes().decode("utf-8"))
    if args.metadata:
        extras=json.loads(args.metadata.read_text(encoding="utf-8"))
        for g in catalog["games"]:
            for key in ("embed","image","x","recommended"):
                if key in extras.get(g["id"],{}):
                    g[key]=extras[g["id"]][key]
    args.output.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
