# Submit a game

Open an issue with the game submission template, or open a pull request that adds one entry to the appropriate genre in [CATALOG.md](CATALOG.md) and the [README gallery](README.md).

1. Give the title, creator, and a one-sentence description of what the player actually does.
2. Link to the original playable browser build or the creator's download/build instructions. Label downloads, account requirements, and browser/device limitations. A video alone does not qualify for a games section.
3. Link to a first-party source for how Claude was used: a devlog, README, commit, or creator post. If the exact model isn't listed, say “Claude Code, model not disclosed.” State Claude's role and mention other tools when disclosed. Do not infer the model from the release date or call a build “one-shot” unless the creator says so.
4. Add a source link if available. Say “open source” only if the relevant code license is clear; an asset or tool may have a different license from the game.
5. Use original links, no affiliate or tracking URLs, and don't attach other creators' artwork, GIFs or builds without permission. Submit one game per issue or PR.

Keep `CATALOG.md` as the source for the machine-readable [catalog.json](catalog.json). After changing the catalog, regenerate the JSON:

```sh
python catalog-tools/export_catalog.py CATALOG.md catalog.json --metadata catalog-tools/metadata.json
```

For a creator-published screenshot, include its original URL and attribution. If an original X post has a verified view count, record the post URL, exact count, and retrieval time in the metadata. A post view is not a game play; leave unavailable counts blank.

Experiments with little or no gameplay belong in Interactive demos. Report dead links or attribution corrections in an issue. If you're the creator and want an entry changed or removed, tell us which one and include your official project page.
