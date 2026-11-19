#!/usr/bin/env python3
"""Refresh conservative public frame metadata from the canonical URLs only.

No guessed itch.io player URLs, mirrors, or private endpoint extraction. A 200
HTML response and absent restrictive headers is eligibility, not play-testing.
"""
import argparse
import concurrent.futures
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit

def parse_headers(path):
    last = {}
    for line in path.read_text(errors="replace").splitlines():
        if line.upper().startswith("HTTP/"):
            last = {}
        elif ":" in line:
            k,v = line.split(":",1)
            last.setdefault(k.lower(),[]).append(v.strip())
    return last

def check(g):
    e = dict(g["embed"])
    if g["type"] == "local":
        return e
    e["checkedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    e["status"],e["url"]= "unknown",None
    url=g["url"]
    with tempfile.TemporaryDirectory() as d:
        h=Path(d,"h"); body=Path(d,"b")
        cmd=["curl","--silent","--show-error","--location","--max-redirs","6",
            "--proto","=https","--proto-redir","=https","--user-agent",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/142.0.0.0 Safari/537.36",
            "--connect-timeout","6","--max-time","17","--range","0-65535",
            "--dump-header",str(h),"--output",str(body),"--write-out","%{http_code}\t%{url_effective}",url]
        p=subprocess.run(cmd,text=True,capture_output=True)
        if not p.stdout.strip() or not h.is_file():
            e["reason"]="No public HTTPS response could be confirmed."
            return e
        status,_,final=p.stdout.partition("\t")
        e["httpStatus"]=int(status) if status.isdigit() and status!="000" else None
        e["finalUrl"]=final or None
        headers=parse_headers(h)
        xfo=", ".join(headers.get("x-frame-options",[]))
        csp="; ".join(headers.get("content-security-policy",[]))
        ancestors=re.findall(r"(?:^|[;,])\s*frame-ancestors(?:\s+([^;,]*))?(?=\s*[;,]|\s*$)",csp,re.I)
        if xfo:e["xFrameOptions"]=xfo
        if ancestors:e["frameAncestors"]=ancestors
        if any(set(rule.lower().split())!={"*"} for rule in ancestors) or xfo:
            if any("'none'" in rule.lower().split() or set(rule.lower().split())=={"'self'"} for rule in ancestors) or bool(re.search(r"\b(?:deny|sameorigin)\b",xfo,re.I)):
                e["status"]="blocked"
                e["reason"]="The creator’s destination disallows cross-origin framing."
            else:
                e["reason"]="The destination has a frame allowlist or an unrecognized policy; this site is not verified on it."
            return e
        content_type=", ".join(headers.get("content-type",[])).lower()
        if "attachment" in ", ".join(headers.get("content-disposition",[])).lower():
            e["reason"]="The destination returns a file attachment, not a playable document."
        elif not status.startswith("2"):
            e["reason"]=f"Public HTTPS check returned HTTP {status}; use the creator link."
        elif not ("text/html" in content_type or "application/xhtml+xml" in content_type):
            e["reason"]="The destination did not return an HTML game document."
        elif any((urlsplit(u).hostname or "").endswith(".itch.io") for u in (url,final)):
            e["reason"]="An itch.io project page is not an author-published game embed."
        else:
            fragment=body.open("rb").read(65536).lower() if body.is_file() else b""
            if not fragment or any(t in fragment for t in (b"<title>just a moment",b"challenge-platform",b"checking your browser",b"enable cookies to continue")):
                e["reason"]="Received an interstitial or no usable game HTML."
            elif ("claude.ai/artifact/" in url or "wavedash.com/games/" in url or "frontier.every.to/experiments/" in url):
                e["reason"]="A player or landing page could not be confirmed to work inside this site’s frame."
            else:
                e.update(status="allowed",url=url,reason="Public HTML and no blocking frame header; actual in-frame play has not been tested.")
        return e

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("catalog",type=Path)
    a.add_argument("metadata",type=Path)
    a.add_argument("--screenshots",type=Path)
    a.add_argument("--x-views",type=Path,help="Independently verified public post-view observations; join on exact permalink.")
    args=a.parse_args()
    games=json.loads(args.catalog.read_text())["games"]
    values=json.loads(args.metadata.read_text()) if args.metadata.exists() else {}
    metrics={}
    if args.x_views:
        metrics={m["xPost"]:m for m in json.loads(args.x_views.read_text()) if isinstance(m.get("xPostViews"),int) and m["xPostViews"]>=0 and m.get("xViewsCheckedAt")}
    pictures={}
    if args.screenshots:
        pictures={g["name"]:g["image"] for g in json.loads(args.screenshots.read_text()) if g.get("image","") and g["image"].startswith("https://")}
    pictures.update({
        "Skyfire":"https://d2ol7oe51mr4n9.cloudfront.net/user_3JdxfCfYFP0Cn76oVrc3Mc5eXcF/dacc4560-6454-4974-a158-a608977bedcb.jpg",
        "FableFlight":"https://external-preview.redd.it/Y3l3MW5jOHBibjFpMR6HN24z7o3nvXO4efCwRNYgMRHqOhCHJhH44lKJuiXc.png?auto=webp&s=6c43ed4c587e5d103c9eed3ea6285ed634410a7e",
    })
    with concurrent.futures.ThreadPoolExecutor(max_workers=18) as pool:
        for g,e in zip(games,pool.map(check,games)):
            item=values.setdefault(g["id"],{})
            item["embed"]=e
            if g["title"] in pictures:item["image"]=pictures[g["title"]]
            if args.x_views and g["x"]:
                item["x"]=[]
                for x in g["x"]:
                    observation=metrics.get(x["url"])
                    if observation:
                        x={**x, "views":observation["xPostViews"], "checkedAt":observation["xViewsCheckedAt"],
                           "metric":"post_views","publishedAt":observation.get("xPublishedAt"),"author":observation.get("xAuthor")}
                    item["x"].append(x)
            print(e["status"],e.get("httpStatus",0),g["id"],flush=True)
    args.metadata.write_text(json.dumps(values,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
