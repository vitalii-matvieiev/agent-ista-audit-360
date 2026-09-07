#!/usr/bin/env python3
"""Спільне ядро: конфіг, HTTP-клієнти ScrapeCreators і Meta Graph. Тільки stdlib."""

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

HOME = os.environ.get("IG_AUDIT_HOME") or os.path.expanduser("~/.ig-audit")
CONFIG_PATH = os.environ.get("IG_AUDIT_CONFIG", os.path.join(HOME, "config.json"))
DATA_PATH = os.path.join(HOME, "data.json")
SC_BASE = "https://api.scrapecreators.com"
GRAPH = "https://graph.facebook.com/v21.0"

CREDITS = {"spent": 0, "left": None}


def log(msg):
    print("[{}] {}".format(datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def die(msg, code=1):
    print("Помилка: " + msg, file=sys.stderr)
    sys.exit(code)


def load_config():
    if not os.path.exists(CONFIG_PATH):
        die("немає {}. Запусти /ig-audit-setup — я проведу через налаштування.".format(CONFIG_PATH))
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(conf):
    os.makedirs(HOME, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(conf, f, ensure_ascii=False, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


# ---------- ScrapeCreators ----------

def sc_get(key, path, **params):
    """Публічні дані будь-якого акаунта. 1 кредит на виклик."""
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(SC_BASE + path + "?" + qs, headers={"x-api-key": key})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                CREDITS["spent"] += 1
                left = r.headers.get("x-credits-remaining")
                if left:
                    CREDITS["left"] = int(left)
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 402:
                die("на ScrapeCreators закінчились кредити. Поповни на scrapecreators.com")
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            raise


def sc_profile(key, username):
    return sc_get(key, "/v1/instagram/profile", handle=username.lstrip("@"))


def sc_posts(key, username, pages=1):
    """Одна сторінка ≈ 12 постів, 1 кредит. Курсор — next_max_id."""
    items, cursor = [], None
    for _ in range(max(1, pages)):
        raw = sc_get(key, "/v2/instagram/user/posts",
                     handle=username.lstrip("@"), next_max_id=cursor)
        items.extend(raw.get("items") or [])
        cursor = raw.get("next_max_id") or raw.get("max_id")
        if not cursor or not raw.get("more_available", True):
            break
    return {"items": items}


def sc_post(key, code):
    return sc_get(key, "/v1/instagram/post",
                  url="https://www.instagram.com/reel/{}/".format(code))


def deep_int(obj, keys):
    """Пошук першого цілого поля з переліку. Перегляди звуться video_play_count,
    а не play_count — це головна пастка ScrapeCreators."""
    if isinstance(obj, dict):
        for k in keys:
            if isinstance(obj.get(k), int):
                return obj[k]
        for v in obj.values():
            r = deep_int(v, keys)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = deep_int(v, keys)
            if r is not None:
                return r
    return None


VIEW_KEYS = ["video_play_count", "play_count", "ig_play_count", "video_view_count"]
FOLLOWER_KEYS = ["follower_count", "edge_followed_by"]


def profile_followers(raw):
    n = deep_int(raw, ["follower_count"])
    if n:
        return n
    try:
        return raw["data"]["user"]["edge_followed_by"]["count"]
    except Exception:
        return None


# ---------- Meta Graph (рівень 2) ----------

MEDIA_FIELDS = ("id,timestamp,media_type,media_product_type,permalink,caption,"
                "like_count,comments_count,thumbnail_url,media_url")

REELS_METRICS = "reach,views,likes,comments,shares,saved,total_interactions,ig_reels_avg_watch_time"
FEED_METRICS = "reach,views,likes,comments,shares,saved,total_interactions,profile_visits,follows"


def graph(token, path, **params):
    params["access_token"] = token
    url = "{}/{}?{}".format(GRAPH, path.lstrip("/"), urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=45) as r:
        return json.loads(r.read().decode())


def graph_safe(token, path, **params):
    try:
        return graph(token, path, **params)
    except Exception:
        return None


# ---------- дати ----------

def parse_ts(s):
    """Meta віддає 2026-09-06T09:44:15+0000 — fromisoformat на цьому падає."""
    if not s:
        return None
    if isinstance(s, (int, float)):
        return datetime.fromtimestamp(s, timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def now():
    return datetime.now(timezone.utc)


def median(xs, default=0):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else default


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 5:
        return None
    xs, ys = zip(*pairs)
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else None
