#!/usr/bin/env python3
"""Щотижневий запуск. macOS — launchd, Linux — crontab.

  python3 schedule.py install          # щопонеділка о 08:00
  python3 schedule.py install --hour 9
  python3 schedule.py status
  python3 schedule.py uninstall
"""

import argparse
import os
import platform
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABEL = "com.matvieiev.ig-audit"
PLIST = os.path.expanduser("~/Library/LaunchAgents/{}.plist".format(LABEL))
RUNNER = os.path.join(HERE, "run_weekly.sh")
MARK = "# ig-audit-360"


def write_runner():
    with open(RUNNER, "w") as f:
        f.write("#!/bin/sh\nset -e\ncd \"{d}\"\n"
                "\"{py}\" collect.py\n\"{py}\" metrics.py\n\"{py}\" report.py\n\"{py}\" notify.py\n"
                .format(d=HERE, py=sys.executable))
    os.chmod(RUNNER, 0o755)


def install(hour):
    write_runner()
    log_out = os.path.expanduser("~/.ig-audit/weekly.log")
    os.makedirs(os.path.dirname(log_out), exist_ok=True)
    if platform.system() == "Darwin":
        os.makedirs(os.path.dirname(PLIST), exist_ok=True)
        with open(PLIST, "w") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array><string>{runner}</string></array>
  <key>StartCalendarInterval</key><dict>
    <key>Weekday</key><integer>1</integer><key>Hour</key><integer>{hour}</integer>
    <key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict></plist>""".format(label=LABEL, runner=RUNNER, hour=hour, log=log_out))
        subprocess.run(["launchctl", "unload", PLIST], capture_output=True)
        subprocess.run(["launchctl", "load", PLIST], check=True)
        print("Готово: щопонеділка о {}:00. Лог у {}".format(hour, log_out))
    else:
        cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        lines = [l for l in cur.splitlines() if MARK not in l]
        lines.append("0 {} * * 1 {} >> {} 2>&1 {}".format(hour, RUNNER, log_out, MARK))
        subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
        print("Готово: щопонеділка о {}:00 через crontab. Лог у {}".format(hour, log_out))


def status():
    if platform.system() == "Darwin":
        r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        print("Активний" if LABEL in r.stdout else "Не встановлений")
    else:
        cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        print("Активний" if MARK in cur else "Не встановлений")


def uninstall():
    if platform.system() == "Darwin":
        subprocess.run(["launchctl", "unload", PLIST], capture_output=True)
        if os.path.exists(PLIST):
            os.remove(PLIST)
    else:
        cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        lines = [l for l in cur.splitlines() if MARK not in l]
        subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
    print("Знято.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["install", "status", "uninstall"])
    ap.add_argument("--hour", type=int, default=8)
    a = ap.parse_args()
    {"install": lambda: install(a.hour), "status": status, "uninstall": uninstall}[a.action]()


if __name__ == "__main__":
    main()
