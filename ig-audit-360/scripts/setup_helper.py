#!/usr/bin/env python3
"""Перевірка й збереження доступів. Кожна команда сама пише в конфіг.

  python3 setup_helper.py save --username X --competitors a,b --refs c,d --goal "..."
  python3 setup_helper.py check-sc   <ключ>
  python3 setup_helper.py check-tg   <токен>
  python3 setup_helper.py check-meta <токен>
  python3 setup_helper.py show
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

from core import CONFIG_PATH, graph, load_config, sc_profile, save_config


def conf():
    try:
        return load_config()
    except SystemExit:
        return {}


def put(**kw):
    c = conf()
    c.update({k: v for k, v in kw.items() if v is not None})
    save_config(c)
    return c


def mask(s):
    return (s[:6] + "…" + s[-4:]) if s and len(s) > 12 else ("вказано" if s else "—")


def cmd_save(a):
    split = lambda s: [x.strip().lstrip("@") for x in (s or "").split(",") if x.strip()]
    c = put(username=(a.username or "").strip().lstrip("@").rstrip("/").split("/")[-1] or None,
            competitors=split(a.competitors) or None,
            refs=split(a.refs) or None,
            goal=a.goal or None)
    print("ok · @{} · конкурентів {} · референсів {}".format(
        c.get("username"), len(c.get("competitors") or []), len(c.get("refs") or [])))


def cmd_check_sc(a):
    c = conf()
    user = c.get("username")
    if not user:
        sys.exit("спершу save --username")
    try:
        raw = sc_profile(a.key, user)
    except Exception as e:
        sys.exit("ключ не працює: {}".format(e))
    from core import CREDITS, profile_followers
    n = profile_followers(raw)
    put(scrapecreators_key=a.key)
    print("ok · @{} · підписників {} · кредитів лишилось {}".format(
        user, n, CREDITS["left"] if CREDITS["left"] is not None else "?"))


def _tg(token, method, **params):
    url = "https://api.telegram.org/bot{}/{}".format(token, method)
    data = urllib.parse.urlencode(params).encode() if params else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=25) as r:
        return json.loads(r.read().decode())


def cmd_check_tg(a):
    try:
        me = _tg(a.token, "getMe")
    except Exception as e:
        sys.exit("токен не приймається: {}".format(e))
    if not me.get("ok"):
        sys.exit("токен не приймається: {}".format(me))
    name = me["result"].get("username")
    upd = _tg(a.token, "getUpdates")
    chats = []
    for u in upd.get("result", []):
        m = u.get("message") or u.get("channel_post") or {}
        cid = (m.get("chat") or {}).get("id")
        if cid and cid not in chats:
            chats.append(cid)
    if not chats:
        sys.exit("бот @{} живий, але йому ще ніхто не написав. "
                 "Напиши йому будь-що в Telegram і запусти цю команду ще раз.".format(name))
    chat = chats[0]
    _tg(a.token, "sendMessage", chat_id=chat,
        text="Instagram Audit 360 підключений. Сюди приходитиме щотижневий звіт.")
    put(telegram_token=a.token, telegram_chat_id=str(chat))
    print("ok · бот @{} · chat_id {} · тестове повідомлення надіслано".format(name, chat))


def cmd_check_meta(a):
    try:
        pages = graph(a.token, "me/accounts",
                      fields="id,name,instagram_business_account{id,username}")
    except Exception as e:
        sys.exit("токен не працює: {}".format(e))
    found = []
    for p in pages.get("data", []):
        iba = p.get("instagram_business_account")
        if iba:
            found.append((p.get("name"), iba["id"], iba.get("username")))
    if not found:
        sys.exit("токен живий, але жодного Instagram-акаунта до нього не привʼязано.\n"
                 "Найчастіші причини: Instagram не переведений у професійний акаунт, "
                 "не привʼязаний до Facebook-сторінки, або системному користувачу "
                 "не видали доступ до активів у Business Settings → Assign Assets.")
    want = (conf().get("username") or "").lower()
    pick = next((f for f in found if (f[2] or "").lower() == want), found[0])
    put(meta_token=a.token, meta_ig_user_id=pick[1])
    print("ok · сторінка «{}» · @{} · ig_user_id {}".format(pick[0], pick[2], pick[1]))
    if len(found) > 1:
        print("   (знайдено ще: {})".format(", ".join("@" + f[2] for f in found if f is not pick)))


def cmd_show(a):
    c = conf()
    lvl = 2 if c.get("meta_token") else 1
    print("конфіг: {}".format(CONFIG_PATH))
    print("  акаунт            @{}".format(c.get("username") or "—"))
    print("  конкуренти        {}".format(", ".join("@" + x for x in c.get("competitors") or []) or "—"))
    print("  референси         {}".format(", ".join("@" + x for x in c.get("refs") or []) or "—"))
    print("  ціль              {}".format(c.get("goal") or "—"))
    print("  ScrapeCreators    {}".format(mask(c.get("scrapecreators_key"))))
    print("  Telegram          {} · chat {}".format(mask(c.get("telegram_token")),
                                                    c.get("telegram_chat_id") or "—"))
    print("  Meta              {} · ig {}".format(mask(c.get("meta_token")),
                                                  c.get("meta_ig_user_id") or "—"))
    print("  РІВЕНЬ {}".format(lvl))
    if lvl == 1:
        print("  (без Meta немає збережень, охоплення, утримання й воронки підписки)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save")
    s.add_argument("--username")
    s.add_argument("--competitors", help="через кому")
    s.add_argument("--refs", help="через кому")
    s.add_argument("--goal")
    s.set_defaults(fn=cmd_save)
    for name, fn in [("check-sc", cmd_check_sc), ("check-tg", cmd_check_tg),
                     ("check-meta", cmd_check_meta)]:
        p = sub.add_parser(name)
        p.add_argument("key" if name == "check-sc" else "token")
        p.set_defaults(fn=fn)
    sub.add_parser("show").set_defaults(fn=cmd_show)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
