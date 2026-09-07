#!/usr/bin/env python3
"""Розрахунок. Друкує підсумок і кладе metrics.json поруч із даними.

  python3 metrics.py            # у консоль
  python3 metrics.py --json     # тільки JSON
"""

import argparse
import json
import os
import re
from collections import Counter, defaultdict

from core import DATA_PATH, HOME, die, median, now, parse_ts, pearson


def load():
    if not os.path.exists(DATA_PATH):
        die("немає {}. Спершу python3 collect.py".format(DATA_PATH))
    with open(DATA_PATH) as f:
        return json.load(f)


def ins(m, k):
    v = (m.get("insights") or {}).get(k)
    return v if isinstance(v, (int, float)) else None


def _posts_from_meta(meta):
    """Meta знає всю історію, ScrapeCreators — лише кілька сторінок.
    Коли рівень 2, рахуємо ритм і топи на повних даних, а вагою беремо охоплення."""
    cut = now().timestamp() - 365 * 86400
    out = []
    for m in meta.get("medias", []):
        t = parse_ts(m.get("timestamp"))
        if not t or t.timestamp() < cut or not ins(m, "reach"):
            continue
        out.append({
            "code": (m.get("permalink") or "").rstrip("/").split("/")[-1],
            "ts": t.isoformat(), "is_reel": m.get("media_product_type") == "REELS",
            "likes": ins(m, "likes") or m.get("like_count") or 0,
            "comments": ins(m, "comments") or m.get("comments_count") or 0,
            "caption": (m.get("caption") or "")[:600],
            "thumb": m.get("thumbnail_url") or m.get("media_url") or "",
            "views": ins(m, "views"), "reach": ins(m, "reach"),
        })
    return out


def compute(d):
    me = d["me"]
    base = me["followers"] or 0
    level = 2 if d.get("meta") else 1
    posts = _posts_from_meta(d["meta"]) if level == 2 else list(me["posts"])
    posts = [p for p in posts if parse_ts(p["ts"])]
    posts.sort(key=lambda p: parse_ts(p["ts"]))
    # вага поста: на рівні 2 — охоплення, на рівні 1 — взаємодії
    weight = (lambda p: p.get("reach") or 0) if level == 2 else (lambda p: p["likes"] + p["comments"])
    wname = "охоплення" if level == 2 else "взаємодій"
    out = {"username": me["username"], "followers": base, "level": level,
           "posts_analysed": len(posts), "weight_name": wname}

    # --- пульс на публічних даних ---
    if len(posts) >= 2:
        span = (parse_ts(posts[-1]["ts"]) - parse_ts(posts[0]["ts"])).days or 1
        out["per_week"] = round(len(posts) / span * 7, 1)
        gaps = [(parse_ts(b["ts"]) - parse_ts(a["ts"])).days for a, b in zip(posts, posts[1:])]
        out["longest_gap_days"] = max(gaps) if gaps else 0
    out["engagement_median"] = int(median([weight(p) for p in posts]))
    inter = [p["likes"] + p["comments"] for p in posts]
    out["interactions_median"] = int(median(inter))
    # ER на рівні 2 рахуємо від охоплення (так його рахує сам Instagram),
    # на рівні 1 охоплення немає — лишається від бази підписників
    if level == 2:
        er = [(p["likes"] + p["comments"]) / p["reach"] for p in posts if p.get("reach")]
        out["er_median_pct"] = round(median(er) * 100, 2) if er else None
        out["er_base"] = "від охоплення"
    else:
        out["er_median_pct"] = round(median(inter) / base * 100, 2) if base else None
        out["er_base"] = "від бази"

    reels = [p for p in posts if p["is_reel"] and p.get("views")]
    if level == 1 and not reels:
        reels = [p for p in me["posts"] if p["is_reel"] and p.get("views")]
    if reels:
        v = [p["views"] for p in reels]
        out["reels_views_median"] = int(median(v))
        out["reels_pct_of_base"] = round(median(v) / base * 100) if base else None
        out["reels_sampled"] = len(reels)

    # --- канібалізація: працює й без Meta ---
    tight, loose = [], []
    for a, b in zip(posts, posts[1:]):
        h = (parse_ts(b["ts"]) - parse_ts(a["ts"])).total_seconds() / 3600
        (tight if h < 24 else loose).append(weight(b))
    if len(tight) >= 4 and len(loose) >= 4:
        out["cannibal"] = {"tight_n": len(tight), "tight": int(median(tight)),
                           "loose_n": len(loose), "loose": int(median(loose)),
                           "ratio": round(median(loose) / max(median(tight), 1), 1)}

    # --- ефект гостя ---
    with_at = [weight(p) for p in posts if "@" in (p.get("caption") or "")]
    without = [weight(p) for p in posts if "@" not in (p.get("caption") or "")]
    if len(with_at) >= 3 and len(without) >= 3:
        out["guest_effect"] = {"with_n": len(with_at), "with": int(median(with_at)),
                               "without": int(median(without)),
                               "ratio": round(median(with_at) / max(median(without), 1), 1)}

    mentions = Counter()
    for p in posts:
        for u in set(re.findall(r"@([a-zA-Z0-9_.]{3,30})", p.get("caption") or "")):
            u = u.lower().strip(".")
            if u != me["username"].lower():
                mentions[u] += 1
    out["mentions"] = mentions.most_common(12)

    # --- топ і дно ---
    ranked = sorted(posts, key=lambda p: -weight(p))
    out["top"] = [_card(p, weight) for p in ranked[:4]]
    out["bottom"] = [_card(p, weight) for p in ranked[-4:][::-1]]
    out["grid"] = [_card(p, weight) for p in posts[::-1][:9]]
    pair = _cannibal_pair(posts, weight)
    if pair:
        out["cannibal_pair"] = pair

    # --- конкуренти ---
    rivals = []
    for r in d.get("rivals", []):
        rv = [p["views"] for p in r["posts"] if p.get("views")]
        row = {"username": r["username"], "followers": r["followers"],
               "views_median": int(median(rv)) if rv else None,
               "pct": round(median(rv) / r["followers"] * 100) if rv and r["followers"] else None,
               "thumbs": [p["thumb"] for p in r["posts"] if p["is_reel"] and p["thumb"]][:3]}
        rivals.append(row)
    rivals.sort(key=lambda x: -(x["pct"] or 0))
    out["rivals"] = rivals

    if d.get("meta"):
        out.update(_meta_metrics(d["meta"], base))
    return out


def _card(p, weight):
    return {"code": p.get("code"), "ts": p["ts"][:10], "is_reel": p["is_reel"],
            "likes": p["likes"], "comments": p["comments"],
            "eng": weight(p), "thumb": p.get("thumb", ""),
            "caption": (p.get("caption") or "")[:110]}


def _cannibal_pair(posts, weight):
    """Найяскравіша пара «вийшли поспіль» для картинки у звіті."""
    best = None
    for a, b in zip(posts, posts[1:]):
        h = (parse_ts(b["ts"]) - parse_ts(a["ts"])).total_seconds() / 3600
        ea, eb = weight(a), weight(b)
        if h < 24 and ea > 0 and eb < ea:
            drop = ea - eb
            if not best or drop > best[0]:
                best = (drop, {"first": _card(a, weight), "second": _card(b, weight),
                               "hours": round(h)})
    return best[1] if best else None


def _meta_metrics(meta, base):
    """Рівень 2: те, чого публічні дані не дають у принципі."""
    cut = now().timestamp() - 365 * 86400
    M = [m for m in meta.get("medias", [])
         if parse_ts(m.get("timestamp")) and parse_ts(m["timestamp"]).timestamp() >= cut
         and ins(m, "reach")]
    if not M:
        return {}
    o = {"meta_posts": len(M)}
    o["reach_median"] = int(median([ins(m, "reach") for m in M]))
    o["reach_pct_of_base"] = round(o["reach_median"] / base * 100) if base else None
    o["below_base"] = sum(1 for m in M if ins(m, "reach") < base)

    # кореляційна карта
    R = [ins(m, "reach") for m in M]
    corr = {}
    for label, key in [("шери", "shares"), ("збереження", "saved"), ("лайки", "likes"),
                       ("коментарі", "comments")]:
        c = pearson(R, [ins(m, key) or 0 for m in M])
        if c is not None:
            corr[label] = round(c, 2)
    corr_extra = pearson(R, [len(m.get("caption") or "") for m in M])
    if corr_extra is not None:
        corr["довжина підпису"] = round(corr_extra, 2)
    corr_h = pearson(R, [len(re.findall(r"#\w+", m.get("caption") or "")) for m in M])
    if corr_h is not None:
        corr["хештеги"] = round(corr_h, 2)
    o["corr"] = dict(sorted(corr.items(), key=lambda kv: -abs(kv[1])))

    # формати
    fmt = defaultdict(list)
    for m in M:
        fmt[m.get("media_product_type") or "FEED"].append(m)
    o["formats"] = {k: {"n": len(v), "reach": int(median([ins(x, "reach") for x in v])),
                        "saved": int(median([ins(x, "saved") or 0 for x in v])),
                        "follows": sum(ins(x, "follows") or 0 for x in v)}
                    for k, v in fmt.items()}

    # воронка підписки — тільки FEED, Meta не дає follows для рілсів
    feed = [m for m in M if m.get("media_product_type") != "REELS"]
    reach = sum(ins(m, "reach") or 0 for m in feed)
    visits = sum(ins(m, "profile_visits") or 0 for m in feed)
    follows = sum(ins(m, "follows") or 0 for m in feed)
    if reach and follows:
        o["funnel"] = {"reach": reach, "visits": visits, "follows": follows,
                       "visit_pct": round(visits / reach * 100, 1),
                       "follow_pct": round(follows / visits * 100, 1) if visits else None,
                       "cost": round(reach / follows)}
        best = max(feed, key=lambda m: ins(m, "follows") or 0)
        if ins(best, "follows"):
            o["hero"] = {"follows": ins(best, "follows"), "reach": ins(best, "reach"),
                         "visits": ins(best, "profile_visits") or 0,
                         "saved": ins(best, "saved") or 0, "ts": best["timestamp"][:10],
                         "caption": (best.get("caption") or "")[:110],
                         "thumb": best.get("thumbnail_url") or best.get("media_url") or "",
                         "share_of_all": round(ins(best, "follows") / follows * 100)}
    # утримання
    watch = [ins(m, "ig_reels_avg_watch_time") for m in M
             if ins(m, "ig_reels_avg_watch_time")]
    if watch:
        o["watch_median_s"] = round(median(watch) / 1000, 1)
        rl = [m for m in M if ins(m, "ig_reels_avg_watch_time")]
        c = pearson([ins(m, "ig_reels_avg_watch_time") for m in rl],
                    [ins(m, "reach") for m in rl])
        if c is not None:
            o["hook_r"] = round(c, 2)
    # квартали
    q = defaultdict(list)
    for m in M:
        t = parse_ts(m["timestamp"])
        q["{}-Q{}".format(t.year, (t.month - 1) // 3 + 1)].append(m)
    o["quarters"] = {k: {"n": len(v), "reach": int(median([ins(x, "reach") for x in v])),
                         "shares": sum(ins(x, "shares") or 0 for x in v)}
                     for k, v in sorted(q.items())}
    return o


def render(o):
    L = []
    A = L.append
    A("INSTAGRAM AUDIT 360 · @{} · {} підписників · рівень {}".format(
        o["username"], o["followers"], o["level"]))
    A("постів у вибірці: {}".format(o["posts_analysed"]))
    A("")
    A("ПУЛЬС")
    A("  темп {} постів/тиждень · найдовша пауза {} днів".format(
        o.get("per_week", "?"), o.get("longest_gap_days", "?")))
    line = "  медіана {} {}".format(o.get("weight_name", "взаємодій"), o["engagement_median"])
    if o.get("weight_name") != "взаємодій":
        line += " · взаємодій {}".format(o.get("interactions_median"))
    A(line + " · ER {}% ({})".format(o.get("er_median_pct"), o.get("er_base", "")))
    if o.get("reels_views_median"):
        A("  рілси: медіана {} переглядів = {}% бази ({} у вибірці)".format(
            o["reels_views_median"], o["reels_pct_of_base"], o["reels_sampled"]))
    if o.get("reach_median"):
        A("  охоплення: медіана {} = {}% бази · нижче бази {} із {}".format(
            o["reach_median"], o["reach_pct_of_base"], o["below_base"], o["meta_posts"]))
    if o.get("cannibal"):
        c = o["cannibal"]
        A("")
        A("КАНІБАЛІЗАЦІЯ")
        A("  впритул (<24 год): {} ({} постів)".format(c["tight"], c["tight_n"]))
        A("  з паузою (2+ дні): {} ({} постів)".format(c["loose"], c["loose_n"]))
        A("  різниця {}×".format(c["ratio"]))
    if o.get("guest_effect"):
        g = o["guest_effect"]
        A("")
        A("ЕФЕКТ ГОСТЯ: зі згадкою @ {} ({} шт) проти {} без · {}×".format(
            g["with"], g["with_n"], g["without"], g["ratio"]))
    if o.get("corr"):
        A("")
        A("ЩО ЙДЕ РАЗОМ З ОХОПЛЕННЯМ (r)")
        for k, v in o["corr"].items():
            A("  {:<18} {:+.2f}".format(k, v))
        A("  ! кореляція не є причинністю — напрям двосторонній")
    if o.get("formats"):
        A("")
        A("ФОРМАТИ")
        for k, v in o["formats"].items():
            A("  {:<8} {:>3} шт · охоплення {:>5} · збереження {:>2} · підписок {}".format(
                k, v["n"], v["reach"], v["saved"],
                v["follows"] if k != "REELS" else "Meta не віддає"))
    if o.get("funnel"):
        f = o["funnel"]
        A("")
        A("ВОРОНКА ПІДПИСКИ (лише FEED)")
        A("  {} охоплення → {} переходів ({}%) → {} підписок ({}%)".format(
            f["reach"], f["visits"], f["visit_pct"], f["follows"], f["follow_pct"]))
        A("  ціна підписника: {} охоплення на 1 підписку".format(f["cost"]))
    if o.get("hook_r") is not None:
        A("")
        A("ХУК: утримання {} с · зв'язок з охопленням r = {:+.2f} — {}".format(
            o.get("watch_median_s"), o["hook_r"],
            "хук важить" if abs(o["hook_r"]) >= 0.4 else "охоплення впирається НЕ в хук"))
    if o.get("quarters"):
        A("")
        A("КВАРТАЛИ")
        for k, v in o["quarters"].items():
            A("  {}: {:>3} постів · медіана {:>5} · шери {:>4}".format(
                k, v["n"], v["reach"], v["shares"]))
    if o.get("rivals"):
        A("")
        A("КОНКУРЕНТИ (перегляди рілса до бази)")
        for r in o["rivals"]:
            A("  @{:<22} {:>7} бази · медіана {:>7} · {}%".format(
                r["username"], r["followers"], r["views_median"] or 0, r["pct"] or "?"))
        if o.get("reels_pct_of_base"):
            A("  {:<23} {:>7} бази · медіана {:>7} · {}%  ← ти".format(
                "ТИ", o["followers"], o["reels_views_median"], o["reels_pct_of_base"]))
    if o["level"] == 1:
        A("")
        A("РІВЕНЬ 1. Немає: збережень, шерів, охоплення, утримання, воронки підписки.")
        A("Це не нулі — цих метрик не існує в публічних даних. Підключи Meta: /ig-audit-setup meta")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    o = compute(load())
    with open(os.path.join(HOME, "metrics.json"), "w") as f:
        json.dump(o, f, ensure_ascii=False)
    print(json.dumps(o, ensure_ascii=False, indent=2) if args.json else render(o))


if __name__ == "__main__":
    main()
