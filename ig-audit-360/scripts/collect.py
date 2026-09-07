#!/usr/bin/env python3
"""Вигрузка: свій акаунт + конкуренти. Рівень 1 — ScrapeCreators, рівень 2 — Meta Graph.

  python3 collect.py                 # звичайна вигрузка
  python3 collect.py --reels 12      # скільки своїх рілсів перевіряти на перегляди
  python3 collect.py --skip-rivals   # заощадити кредити
"""

import argparse
import json
import os
import time

from core import (DATA_PATH, HOME, FEED_METRICS, MEDIA_FIELDS, REELS_METRICS,
                  VIEW_KEYS, CREDITS, deep_int, die, graph_safe, load_config,
                  log, now, parse_ts, profile_followers, sc_post, sc_posts,
                  sc_profile)


def collect_sc_account(key, username, reels_sample, pages=1):
    """Публічні дані одного акаунта. Вартість: 2 + reels_sample кредитів."""
    prof = sc_profile(key, username)
    followers = profile_followers(prof)
    raw = sc_posts(key, username, pages)
    items = raw.get("items") or []
    posts = []
    for it in items:
        posts.append({
            "code": it.get("code"),
            "ts": (parse_ts(it.get("taken_at")) or now()).isoformat(),
            "is_reel": it.get("media_type") == 2,
            "likes": it.get("like_count") or 0,
            "comments": it.get("comment_count") or 0,
            "caption": ((it.get("caption") or {}).get("text") or "")[:600]
                       if isinstance(it.get("caption"), dict) else "",
            "thumb": it.get("display_uri") or "",
            "views": None,
        })
    reels = [p for p in posts if p["is_reel"] and p["code"]][:reels_sample]
    for p in reels:
        try:
            p["views"] = deep_int(sc_post(key, p["code"]), VIEW_KEYS)
        except Exception as e:
            log("  {}: перегляди не дістав ({})".format(p["code"], e))
        time.sleep(0.3)
    return {"username": username.lstrip("@"), "followers": followers, "posts": posts}


def collect_meta(conf):
    """Рівень 2: справжні інсайти власного акаунта."""
    token, ig_id = conf.get("meta_token"), conf.get("meta_ig_user_id")
    if not (token and ig_id):
        return None
    prof = graph_safe(token, ig_id, fields="username,followers_count,media_count,biography")
    if not prof:
        log("Meta: токен не працює — рахую тільки на публічних даних")
        return None
    medias, url_params = [], {"fields": MEDIA_FIELDS, "limit": 100}
    page = graph_safe(token, "{}/media".format(ig_id), **url_params)
    while page and len(medias) < 600:
        medias.extend(page.get("data", []))
        nxt = (page.get("paging") or {}).get("cursors", {}).get("after")
        if not nxt or not page.get("paging", {}).get("next"):
            break
        page = graph_safe(token, "{}/media".format(ig_id), after=nxt, **url_params)
    log("Meta: {} медіа, тягну інсайти".format(len(medias)))
    cutoff = now().timestamp() - 365 * 86400
    for m in medias:
        t = parse_ts(m.get("timestamp"))
        if not t or t.timestamp() < cutoff:
            continue
        metrics = REELS_METRICS if m.get("media_product_type") == "REELS" else FEED_METRICS
        r = graph_safe(token, "{}/insights".format(m["id"]), metric=metrics)
        ins = {}
        for row in (r or {}).get("data", []):
            vals = row.get("values") or [{}]
            ins[row["name"]] = vals[0].get("value")
        m["insights"] = ins
    return {"profile": prof, "medias": medias}


def main():
    ap = argparse.ArgumentParser(description="Вигрузка даних для Instagram Audit 360")
    ap.add_argument("--reels", type=int, default=12, help="скільки своїх рілсів перевірити на перегляди")
    ap.add_argument("--rival-reels", type=int, default=4, help="скільки рілсів у кожного конкурента")
    ap.add_argument("--pages", type=int, default=3,
                    help="сторінок стрічки (≈12 постів кожна, 1 кредит за сторінку)")
    ap.add_argument("--skip-rivals", action="store_true")
    args = ap.parse_args()

    conf = load_config()
    key = conf.get("scrapecreators_key")
    if not key:
        die("немає ключа ScrapeCreators. Запусти /ig-audit-setup")
    me = conf["username"]

    log("Мій акаунт @{}".format(me.lstrip("@")))
    data = {"fetched_at": now().isoformat(),
            "me": collect_sc_account(key, me, args.reels, args.pages)}
    log("  {} постів, {} підписників".format(len(data["me"]["posts"]), data["me"]["followers"]))

    data["rivals"] = []
    if not args.skip_rivals:
        for u in (conf.get("competitors") or []):
            try:
                r = collect_sc_account(key, u, args.rival_reels, 1)
                data["rivals"].append(r)
                log("  @{}: {} підписників".format(r["username"], r["followers"]))
            except Exception as e:
                log("  @{}: не вийшло — {}".format(u, e))

    data["meta"] = collect_meta(conf)
    if data["meta"]:
        log("Meta: інсайти зібрано (рівень 2)")
    else:
        log("Meta не підключена — рівень 1. Збережень, утримання і воронки підписки не буде.")

    os.makedirs(HOME, exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    log("Готово → {} · кредитів витрачено {}, лишилось {}".format(
        DATA_PATH, CREDITS["spent"], CREDITS["left"] if CREDITS["left"] is not None else "?"))


if __name__ == "__main__":
    main()
