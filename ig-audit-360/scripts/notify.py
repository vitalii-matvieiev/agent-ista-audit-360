#!/usr/bin/env python3
"""Дайджест у Telegram. Без токена нічого не падає — текст іде в консоль.

  python3 notify.py            # зібрати дайджест з metrics.json і надіслати
  python3 notify.py --dry      # тільки показати
"""

import argparse
import json
import os
import urllib.parse
import urllib.request

from core import HOME, load_config, log

LINKS = ("Instagram https://www.instagram.com/matvieiev.vitaliy\n"
         "YouTube https://www.youtube.com/channel/UCkb3G7yVFVWGPQWMrzvamGA\n"
         "Telegram https://t.me/matvieiev_vitalii")


def digest(o):
    L = ["Instagram Audit 360 · @{}".format(o["username"]),
         "{} підписників · рівень {}".format(o["followers"], o["level"]), ""]
    if o.get("reels_views_median"):
        L.append("Рілси: медіана {} переглядів = {}% бази".format(
            o["reels_views_median"], o["reels_pct_of_base"]))
    if o.get("reach_median"):
        L.append("Охоплення: медіана {} = {}% бази".format(
            o["reach_median"], o["reach_pct_of_base"]))
    L.append("ER {}% · темп {} постів на тиждень".format(
        o.get("er_median_pct"), o.get("per_week")))

    actions = []
    if o.get("cannibal") and o["cannibal"]["ratio"] >= 1.5:
        c = o["cannibal"]
        L += ["", "Головне: {} постів вийшли впритул і дали {} проти {} у решти — різниця {}×.".format(
            c["tight_n"], c["tight"], c["loose"], c["ratio"])]
        actions.append("Тримати 48 годин між постами")
    if o.get("funnel") and o["funnel"]["visit_pct"] < 3:
        actions.append("Закріпити найкращий пост: у профіль заходять лише {}% від охоплення".format(
            o["funnel"]["visit_pct"]))
    if o.get("hook_r") is not None and abs(o["hook_r"]) < 0.4:
        actions.append("Хуки не чіпати — r = {:+.2f}, охоплення впирається не в них".format(o["hook_r"]))
    if o.get("guest_effect") and o["guest_effect"]["ratio"] >= 1.3:
        actions.append("Більше колаборацій: пости зі згадкою @ дають у {}× більше".format(
            o["guest_effect"]["ratio"]))
    if o.get("rivals"):
        top = max((r for r in o["rivals"] if r.get("pct")), key=lambda r: r["pct"], default=None)
        if top and o.get("reels_pct_of_base"):
            L += ["", "У ніші: @{} робить {}% бази, ти {}%.".format(
                top["username"], top["pct"], o["reels_pct_of_base"])]
    if not actions and o.get("rivals"):
        top = max((r for r in o["rivals"] if r.get("pct")), key=lambda r: r["pct"], default=None)
        if top and o.get("reels_pct_of_base") and top["pct"] > o["reels_pct_of_base"]:
            actions.append("Ціль на квартал: {}% бази переглядами замість {}% — "
                           "орієнтир @{}".format(
                               min(top["pct"], o["reels_pct_of_base"] * 2),
                               o["reels_pct_of_base"], top["username"]))
    if not actions:
        actions.append("Відкрий дашборд — там топ і дно постів із кадрами, "
                       "різниця між рядами зазвичай видно очима")
    L += [""] + ["{}. {}".format(i, a) for i, a in enumerate(actions[:3], 1)]

    L += ["", "Дашборд: ~/.ig-audit/dashboard.html", "",
          "Звіт зібрав агент Віталія Матвєєва. Він викладає своїх агентів безкоштовно —",
          "далі буде більше:", LINKS]
    return "\n".join(L)


def send(text, token, chat):
    """parse_mode навмисно не ставимо: Markdown падає на підкресленнях у назвах файлів."""
    data = urllib.parse.urlencode({
        "chat_id": str(chat), "text": text[:4000], "disable_web_page_preview": "true"
    }).encode()
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=25) as r:
        return r.status == 200


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    with open(os.path.join(HOME, "metrics.json")) as f:
        o = json.load(f)
    text = digest(o)
    print(text)
    if args.dry:
        return
    conf = load_config()
    token, chat = conf.get("telegram_token"), conf.get("telegram_chat_id")
    if not (token and chat):
        log("Telegram не налаштований — дайджест лишається в консолі.")
        return
    try:
        send(text, token, chat)
        log("Надіслано в Telegram ({} символів)".format(len(text)))
    except Exception as e:
        log("Telegram не прийняв: {}".format(e))


if __name__ == "__main__":
    main()
