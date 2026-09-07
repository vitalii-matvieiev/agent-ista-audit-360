#!/usr/bin/env python3
"""Дашборд: HTML з вбудованими кадрами постів. Один самодостатній файл.

  python3 report.py                       # → ~/.ig-audit/dashboard.html
  python3 report.py --out ./audit.html
"""

import argparse
import base64
import io
import json
import os
import urllib.request
from html import escape

from core import HOME, die, log

UA = {"User-Agent": "Mozilla/5.0"}
LINKS = ("https://www.instagram.com/matvieiev.vitaliy",
         "https://www.youtube.com/channel/UCkb3G7yVFVWGPQWMrzvamGA",
         "https://t.me/matvieiev_vitalii", "https://matvieiev.com")


def thumb(url, width=320):
    """Стискаємо в data URI. Без PIL — вбудовуємо як є."""
    if not url:
        return ""
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read()
    except Exception:
        return ""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im = im.resize((width, int(im.height * width / im.width)))
        b = io.BytesIO()
        im.save(b, "JPEG", quality=72, optimize=True)
        raw = b.getvalue()
    except ImportError:
        pass
    except Exception:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


CSS = """
:root{--gold:#BEAA91;--terracotta:#7F4D43;--black:#0E0D0F;--dark:#15151A;--gray:#989799;--light:#F5F0EA}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--black);color:var(--light);font:15px/1.7 'Helvetica Neue',Helvetica,Arial,sans-serif}
.page{max-width:980px;margin:0 auto;padding:56px 40px 90px}
.head{display:flex;justify-content:space-between;align-items:flex-end;padding-bottom:30px;
border-bottom:1px solid rgba(190,170,145,.2);margin-bottom:52px}
.wm{font-family:'Barlow Condensed',sans-serif;font-size:24px;letter-spacing:.22em;color:var(--gold);text-transform:uppercase}
.meta{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--gray);text-align:right}
h1{font-family:'Barlow Condensed',sans-serif;font-size:60px;color:var(--gold);font-weight:400;line-height:1.04;margin-bottom:16px}
h2{font-family:'Barlow Condensed',sans-serif;font-size:32px;color:var(--gold);font-weight:400;letter-spacing:.03em;margin-bottom:6px}
.num{font-family:'Barlow Condensed',sans-serif;font-size:12px;letter-spacing:.2em;color:var(--terracotta);text-transform:uppercase}
section{margin-top:64px}
p{margin-bottom:15px;color:rgba(245,240,234,.85)}
.lede{font-size:18px;max-width:70ch}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(172px,1fr));gap:1px;
background:rgba(190,170,145,.16);border:1px solid rgba(190,170,145,.16);margin:24px 0}
.tile{background:var(--dark);padding:20px}
.tile .v{font-family:'Barlow Condensed',sans-serif;font-size:40px;line-height:1;color:var(--gold)}
.tile .v small{font-size:16px;color:var(--gray)}
.tile .l{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--gray);margin-top:8px}
.tile .d{font-size:12px;color:rgba(245,240,234,.55);margin-top:4px}
.read{border-left:2px solid var(--gold);padding-left:22px;margin:26px 0}
.read h3{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--gray);margin-bottom:9px}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:13px;margin:24px 0}
.shot{background:var(--dark);border:1px solid rgba(190,170,145,.16)}
.shot .im{position:relative;aspect-ratio:9/14;overflow:hidden;background:#000}
.shot .im img{width:100%;height:100%;object-fit:cover;display:block}
.badge{position:absolute;top:0;left:0;font-family:'Barlow Condensed',sans-serif;font-size:12px;
letter-spacing:.13em;text-transform:uppercase;padding:4px 9px}
.win .badge{background:var(--gold);color:var(--black)}
.lose .badge{background:var(--terracotta);color:var(--light)}
.shot .body{padding:11px 12px 13px}
.shot .big{font-family:'Barlow Condensed',sans-serif;font-size:28px;line-height:1;color:var(--gold)}
.lose .big{color:#C98C7A}
.shot .k{font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--gray);margin-top:5px}
.shot .cap{font-size:12px;color:rgba(245,240,234,.62);margin-top:8px;line-height:1.45}
.shot .dt{font-size:10px;letter-spacing:.08em;color:var(--gray);margin-top:6px}
.grid9{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;max-width:330px;
background:rgba(190,170,145,.14);border:1px solid rgba(190,170,145,.14)}
.grid9 div{position:relative;aspect-ratio:1/1;overflow:hidden;background:#000}
.grid9 img{width:100%;height:100%;object-fit:cover;display:block}
.grid9 span{position:absolute;right:3px;bottom:2px;font-family:'Barlow Condensed',sans-serif;
font-size:15px;color:#fff;text-shadow:0 1px 4px #000}
.pair{display:grid;grid-template-columns:1fr 44px 1fr;align-items:center;gap:14px;margin:24px 0}
.pair .ar{font-family:'Barlow Condensed',sans-serif;font-size:28px;color:var(--terracotta);text-align:center}
table{width:100%;border-collapse:collapse;margin:22px 0;font-size:14px}
th{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--gray);text-align:left;
padding:9px 12px 9px 0;border-bottom:1px solid rgba(190,170,145,.28)}
td{padding:11px 12px 11px 0;border-bottom:1px solid rgba(190,170,145,.09);vertical-align:top}
td.n{font-family:'Barlow Condensed',sans-serif;font-size:20px;color:var(--gold);white-space:nowrap}
tr.me td{background:rgba(190,170,145,.07)}tr.me td:first-child{color:var(--gold);font-weight:600}
.refrow{display:grid;grid-template-columns:170px 1fr;gap:20px;align-items:center;padding:18px 0;
border-bottom:1px solid rgba(190,170,145,.1)}
.refstrip{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
.refstrip img{width:100%;aspect-ratio:9/14;object-fit:cover;display:block}
.rec{background:var(--dark);border-top:1px solid var(--terracotta);padding:20px 22px;margin-top:24px}
.rec h3{font-family:'Barlow Condensed',sans-serif;font-size:19px;letter-spacing:.05em;
color:var(--gold);text-transform:uppercase;margin-bottom:9px}
.rec p{font-size:14px;margin-bottom:7px}.rec b{color:var(--light)}
.figcap{font-size:11px;letter-spacing:.06em;color:var(--gray);margin-top:9px;text-transform:uppercase}
.miss li{margin-bottom:11px;color:rgba(245,240,234,.78);font-size:14px}.miss{padding-left:19px}
.foot{margin-top:80px;padding-top:26px;border-top:1px solid rgba(190,170,145,.15);font-size:13px;color:var(--gray)}
.foot a{color:var(--gold);text-decoration:none;border-bottom:1px solid rgba(190,170,145,.3)}
.foot .sig{font-size:11px;letter-spacing:.1em;text-transform:uppercase;margin-top:14px}
@media(max-width:640px){.page{padding:34px 18px}h1{font-size:40px}.pair{grid-template-columns:1fr}
.refrow{grid-template-columns:1fr}}
"""


def card(c, kind, badge, cache):
    im = cache.get(c.get("thumb", ""), "")
    return ('<div class="shot {k}"><div class="im">{img}<span class="badge">{b}</span></div>'
            '<div class="body"><div class="big">{e}</div><div class="k">взаємодій · {l} лайків, {cm} коментарів</div>'
            '<div class="cap">{cap}</div><div class="dt">{ts} · {t}</div></div></div>').format(
        k=kind, b=escape(badge), e=c["eng"], l=c["likes"], cm=c["comments"],
        img='<img src="{}" alt="">'.format(im) if im else "",
        cap=escape(c.get("caption") or "—"), ts=c["ts"], t="REELS" if c["is_reel"] else "FEED")


def build(o, cache):
    S = []
    A = S.append
    lvl = o["level"]
    A('<div class="head"><div class="wm">Instagram Audit 360</div>'
      '<div class="meta">@{} · {} підписників<br>{}</div></div>'.format(
          escape(o["username"]), o["followers"], o.get("date", "")))

    head = "Рівень {}. {} постів під мікроскопом.".format(lvl, o["posts_analysed"])
    A("<h1>{}</h1>".format(escape(head)))
    lede = ("Це автоматичний зріз акаунта. Кожна цифра має джерело, а кожен блок — "
            "рекомендацію. Там, де метрики немає, так і написано: немає. "
            "Відсутня метрика — не нуль.")
    if lvl == 1:
        lede += (" Зараз працює рівень 1 — публічні дані. Збережень, охоплення, утримання "
                 "й воронки підписки в них не існує; щоб їх побачити, підключи Meta.")
    A('<p class="lede">{}</p>'.format(lede))

    # 01 пульс
    A('<section><div class="num">Секція 01</div><h2>Пульс</h2><div class="tiles">')
    A(tile(o.get("per_week"), "постів на тиждень", "найдовша пауза {} дн".format(o.get("longest_gap_days", "?"))))
    A(tile(o["engagement_median"], "медіана взаємодій", "ER {}%".format(o.get("er_median_pct"))))
    if o.get("reels_views_median"):
        A(tile("{:,}".format(o["reels_views_median"]).replace(",", " "), "медіана переглядів рілса",
               "{}% від бази".format(o.get("reels_pct_of_base"))))
    if o.get("reach_median"):
        A(tile(o["reach_median"], "медіана охоплення", "{}% бази · нижче бази {} із {}".format(
            o["reach_pct_of_base"], o["below_base"], o["meta_posts"])))
    A("</div>")
    if o.get("grid"):
        cells = "".join('<div>{}<span>{}</span></div>'.format(
            '<img src="{}" alt="">'.format(cache.get(g.get("thumb", ""), "")) if cache.get(g.get("thumb", "")) else "",
            g["eng"]) for g in o["grid"])
        A('<div class="grid9">{}</div><p class="figcap">Сітка профілю очима нового відвідувача · '
          'цифра = взаємодії</p>'.format(cells))
    A("</section>")

    # 02 залетіло / не залетіло
    if o.get("top"):
        A('<section><div class="num">Секція 02</div><h2>Що залетіло, що ні</h2>')
        A('<div class="shots">{}</div>'.format(
            "".join(card(c, "win", "залетіло", cache) for c in o["top"])))
        A('<div class="shots">{}</div>'.format(
            "".join(card(c, "lose", "не залетіло", cache) for c in o["bottom"])))
        A('<div class="read"><h3>Як це читати</h3><p>Порівнюй не якість картинки — вона в обох рядах '
          'однакова. Порівнюй, <b>чи є в пості подія</b>, яку можна переказати. Верхній ряд зазвичай '
          'містить конфлікт, помилку або чужу історію; нижній — анонс власної послуги.</p></div>')
        A(rec("Взяти конструкцію верхнього ряду і повторити її двічі цього тижня",
              "різниця між рядами — {}× за взаємодіями".format(
                  round(max(c["eng"] for c in o["top"]) / max(min(c["eng"] for c in o["bottom"]), 1))),
              "у @nick_saraev числовий список — опорний формат, а не разова ідея"))
        A("</section>")

    # 03 канібалізація
    if o.get("cannibal"):
        c = o["cannibal"]
        A('<section><div class="num">Секція 03</div><h2>Ритм</h2><div class="tiles">')
        A(tile(c["tight"], "пости впритул, <24 год", "{} штук".format(c["tight_n"])))
        A(tile(c["loose"], "пости з паузою 2+ дні", "{}штук".format(c["loose_n"])))
        A(tile("{}×".format(c["ratio"]), "різниця", "на тій самій базі"))
        A("</div>")
        if o.get("cannibal_pair"):
            p = o["cannibal_pair"]
            A('<div class="pair">{}<div class="ar">→</div>{}</div>'
              '<p class="figcap">Реальна пара з твоєї стрічки: другий пост вийшов через {} год</p>'.format(
                  card(p["first"], "win", "перший", cache),
                  card(p["second"], "lose", "+{} год".format(p["hours"]), cache), p["hours"]))
        A('<div class="read"><h3>Як це читати</h3><p>Instagram не показує два твої пости одній людині '
          'поспіль. Другий забирає авдиторію в першого, а не додає нову.</p></div>')
        A(rec("Тримати мінімум 48 годин між постами",
              "{} проти {} — різниця {}× без жодної зміни контенту".format(
                  c["tight"], c["loose"], c["ratio"]),
              "у @nateherkai 605 постів рівним кроком через день, жодних здвоєних"))
        A("</section>")

    # 04 рівень 2
    if lvl == 2:
        A('<section><div class="num">Секція 04</div><h2>Що обмежує охоплення</h2>')
        if o.get("corr"):
            A("<table><tr><th>Метрика</th><th>r з охопленням</th></tr>" + "".join(
                '<tr><td>{}</td><td class="n">{:+.2f}</td></tr>'.format(escape(k), v)
                for k, v in o["corr"].items()) + "</table>")
            A('<p class="figcap">Кореляція не є причинністю — напрям двосторонній. '
              'Значення біля нуля означають, що на цей важіль не варто витрачати увагу</p>')
        if o.get("formats"):
            A("<table><tr><th>Формат</th><th>Шт</th><th>Охоплення</th><th>Збереження</th><th>Підписок</th></tr>")
            for k, v in o["formats"].items():
                A('<tr><td>{}</td><td class="n">{}</td><td class="n">{}</td><td class="n">{}</td>'
                  '<td>{}</td></tr>'.format(k, v["n"], v["reach"], v["saved"],
                                            "Meta не віддає" if k == "REELS" else v["follows"]))
            A("</table>")
            A('<p class="figcap">Підписки з рілсів — відсутня метрика, а не нуль: '
              'Meta не віддає follows для рілсів у принципі</p>')
        if o.get("hook_r") is not None:
            weak = abs(o["hook_r"]) < 0.4
            A('<div class="read"><h3>Хук</h3><p>Утримання {} с, зв\'язок з охопленням r = {:+.2f}. '
              '<b>{}</b></p></div>'.format(
                  o.get("watch_median_s"), o["hook_r"],
                  "Хук не є вузьким місцем — переписувати його зараз означає витратити тиждень "
                  "на важіль, який майже нічого не рухає." if weak else
                  "Хук важить: над першими секундами варто попрацювати."))
        A("</section>")
        if o.get("funnel"):
            f = o["funnel"]
            A('<section><div class="num">Секція 05</div><h2>Ціна підписника</h2><div class="tiles">')
            A(tile("{:,}".format(f["reach"]).replace(",", " "), "охоплення FEED", "за рік"))
            A(tile(f["visits"], "переходів у профіль", "{}% від охоплення".format(f["visit_pct"])))
            A(tile(f["follows"], "підписки", "{}% з переходів".format(f["follow_pct"])))
            A(tile(f["cost"], "охоплення на 1 підписку", "ціна підписника"))
            A("</div>")
            if o.get("hero"):
                h = o["hero"]
                im = cache.get(h.get("thumb", ""), "")
                A('<div class="pair" style="grid-template-columns:230px 1fr">'
                  '<div>{}</div><div style="grid-column:span 2">'
                  '<p><b>{}% усіх підписок за рік дав один пост</b> від {}: {} охоплення, '
                  '{} переходів у профіль, {} підписок, {} збережень.</p>'
                  '<p style="font-size:13px;color:var(--gray)">{}</p></div></div>'.format(
                      '<img src="{}" style="width:100%">'.format(im) if im else "",
                      h["share_of_all"], h["ts"], h["reach"], h["visits"], h["follows"],
                      h["saved"], escape(h["caption"])))
            step = "перший" if f["visit_pct"] < 3 else "другий"
            A(rec("Закріпити найкращий пост і переписати перший рядок шапки з переліку посад на адресу: кому і що",
                  "вужче місце — {} крок: у профіль заходять {}%, а підписується кожен {}".format(
                      step, f["visit_pct"], round(100 / max(f["follow_pct"], 1))),
                  "у @nick_saraev у шапці одна лінія користі й одне посилання"))
            A("</section>")

    # бенчмарки
    if o.get("rivals"):
        A('<section><div class="num">Секція 06</div><h2>Де ми відносно ніші</h2>')
        rows = [(r["username"], r["followers"], r["views_median"], r["pct"], False) for r in o["rivals"]]
        if o.get("reels_pct_of_base"):
            rows.append(("ти", o["followers"], o["reels_views_median"], o["reels_pct_of_base"], True))
        rows.sort(key=lambda x: -(x[3] or 0))
        A("<table><tr><th>Акаунт</th><th>База</th><th>Медіана переглядів рілса</th><th>% бази</th></tr>")
        for u, f, v, p, me in rows:
            A('<tr class="{}"><td>{}</td><td class="n">{}</td><td class="n">{}</td>'
              '<td class="n">{}%</td></tr>'.format(
                  "me" if me else "", "Ти" if me else "@" + escape(u), f or "?", v or "?", p or "?"))
        A("</table>")
        A('<div class="read"><h3>Як це читати</h3><p>Що менша база, то вищий відсоток — це механіка '
          'алгоритму, а не якість контенту. Порівнюй себе з акаунтами свого розміру, '
          'а не з найбільшими в таблиці.</p></div>')
        for r in o["rivals"]:
            strip = "".join('<img src="{}" alt="">'.format(cache.get(t, ""))
                            for t in r.get("thumbs", []) if cache.get(t))
            if strip:
                A('<div class="refrow"><div class="refstrip">{}</div><div>'
                  '<h2 style="font-size:22px;margin:0">@{}</h2>'
                  '<p style="font-size:12px;color:var(--gray);text-transform:uppercase;letter-spacing:.1em">'
                  '{} бази · {} переглядів · {}%</p></div></div>'.format(
                      strip, escape(r["username"]), r["followers"], r["views_median"] or "?", r["pct"] or "?"))
        A("</section>")

    # чого немає
    A('<section><div class="num">Секція 07</div><h2>Чого немає</h2><ul class="miss">')
    if lvl == 1:
        A("<li><b>Охоплення, збереження, шери, утримання, воронка підписки.</b> Публічні дані їх "
          "не містять — це відсутні метрики, а не нулі. Підключи Meta командою "
          "<code>/ig-audit-setup meta</code>, і ці розділи з'являться.</li>")
    else:
        A("<li><b>Підписки й переходи в профіль з рілсів.</b> Meta не віддає їх для рілсів "
          "у принципі — не читай прочерк як нуль.</li>")
        A("<li><b>Тапи вперед і виходи в сторіс.</b> Метрика живе 24 години, "
          "заднім числом не відновлюється.</li>")
    A("<li><b>Перегляди рілсів рахувались на вибірці</b>, а не на всіх — щоб не палити кредити. "
      "Розмір вибірки в підсумку збору.</li>")
    A("</ul></section>")

    A('<div class="foot"><p>Цей звіт зібрав агент <b>Instagram Audit 360</b> — один із агентів '
      'Віталія Матвєєва. Він віддає їх безкоштовно, бо вважає, що агент має робити роботу, '
      'а не пояснювати її.</p>'
      '<p>Далі буде більше: <a href="{}">Instagram</a> · <a href="{}">YouTube</a> · '
      '<a href="{}">Telegram</a> · <a href="{}">matvieiev.com</a></p>'
      '<p class="sig">Matvieiev · {}</p></div>'.format(*LINKS, o.get("date", "")))
    return "".join(S)


def tile(v, label, sub=""):
    return ('<div class="tile"><div class="v">{}</div><div class="l">{}</div>'
            '<div class="d">{}</div></div>').format(v, escape(str(label)), escape(str(sub)))


def rec(what, why, who):
    return ('<div class="rec"><h3>Рекомендація</h3><p><b>Що робити:</b> {}</p>'
            '<p><b>Чому:</b> {}</p><p><b>У кого підглянути:</b> {}</p></div>').format(
        escape(what), escape(why), escape(who))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HOME, "dashboard.html"))
    args = ap.parse_args()
    mp = os.path.join(HOME, "metrics.json")
    if not os.path.exists(mp):
        die("немає metrics.json. Спершу python3 metrics.py")
    with open(mp) as f:
        o = json.load(f)
    from datetime import datetime
    o["date"] = datetime.now().strftime("%d.%m.%Y")

    urls = set()
    for grp in ("top", "bottom", "grid"):
        urls |= {c.get("thumb") for c in o.get(grp, []) if c.get("thumb")}
    if o.get("cannibal_pair"):
        urls |= {o["cannibal_pair"][k].get("thumb") for k in ("first", "second")}
    if o.get("hero", {}).get("thumb"):
        urls.add(o["hero"]["thumb"])
    for r in o.get("rivals", []):
        urls |= set(t for t in r.get("thumbs", []) if t)
    urls.discard(None)
    log("тягну {} зображень".format(len(urls)))
    cache = {}
    for u in urls:
        cache[u] = thumb(u)
    ok = sum(1 for v in cache.values() if v)
    log("завантажено {} із {}".format(ok, len(urls)))

    html = ("<!DOCTYPE html><html lang=\"uk\"><head><meta charset=\"UTF-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Instagram Audit 360 · @{}</title>"
            "<link href=\"https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;400;500"
            "&display=swap\" rel=\"stylesheet\"><style>{}</style></head><body>"
            "<div class=\"page\">{}</div></body></html>").format(
        o["username"], CSS, build(o, cache))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(html)
    log("Дашборд → {} ({} КБ)".format(args.out, len(html) // 1024))


if __name__ == "__main__":
    main()
