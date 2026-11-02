"""Checks every stream in free.m3u: fetches the playlist, follows the first variant and downloads a
segment, like a player would. Writes a Markdown report and exits 1 when any channel is broken.

Channels named in scripts/geo_blocked.txt are reported but never fail the run.

Usage: python scripts/check_links.py free.m3u report.md
"""
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
ATTEMPTS = 3  # live servers hiccup; only a channel that fails every attempt is reported


def get(url, headers, limit=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **headers})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.geturl(), r.read(limit) if limit else r.read()


def check_once(url, headers):
    for _ in range(3):
        final, body = get(url, headers)
        text = body.decode("utf-8", "replace")
        if "#EXTM3U" not in text:
            return "not an HLS playlist"
        uris = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
        if not uris:
            return "empty playlist"
        if "#EXT-X-STREAM-INF" in text:
            url = urljoin(final, uris[0])
            continue
        _, seg = get(urljoin(final, uris[-1]), headers, 65536)
        return None if len(seg) > 1000 else "segment too small"
    return "too many nested playlists"


def check(channel):
    name, url, headers = channel
    problem = None
    for attempt in range(ATTEMPTS):
        try:
            problem = check_once(url, headers)
        except Exception as e:  # noqa: BLE001 - any failure is a finding
            problem = f"{type(e).__name__}: {str(e)[:80]}"
        if problem is None:
            return name, url, None
        time.sleep(5 * (attempt + 1))
    return name, url, problem


def parse(path):
    channels, name, headers = [], None, {}
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("#EXTINF"):
            name, headers = line.rsplit(",", 1)[-1].strip(), {}
        elif line.startswith("#EXTVLCOPT:"):
            key, _, value = line[len("#EXTVLCOPT:"):].partition("=")
            if key.strip() == "http-user-agent":
                headers["User-Agent"] = value.strip()
            elif key.strip() in ("http-referrer", "http-referer"):
                headers["Referer"] = value.strip()
        elif line and not line.startswith("#") and name:
            channels.append((name, line.strip(), headers))
            name = None
    return channels


def main():
    playlist, report = sys.argv[1], sys.argv[2]
    channels = parse(playlist)
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(check, channels))
    geo_file = os.path.join(os.path.dirname(__file__), "geo_blocked.txt")
    geo = {l.strip() for l in open(geo_file, encoding="utf-8") if l.strip() and not l.startswith("#")}
    blocked = [r for r in results if r[2] and r[0] in geo]
    broken = [r for r in results if r[2] and r[0] not in geo]
    for name, url, problem in results:
        print(("BROKEN " if problem else "ok     ") + name + (f"  ({problem})" if problem else ""))
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"{len(channels) - len(broken) - len(blocked)} of {len(channels)} channels work from the US.\n\n")
        if blocked:
            f.write("Not reachable from the US, as expected (scripts/geo_blocked.txt): "
                    + ", ".join(r[0] for r in blocked) + "\n\n")
        if broken:
            f.write("| Channel | Problem | Link |\n|---|---|---|\n")
            for name, url, problem in broken:
                f.write(f"| {name} | {problem} | `{url}` |\n")
            f.write("\nChecked from a GitHub server in the US: a channel that is geo-blocked there may still work in the Arab world.\n")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
