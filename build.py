#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
京都市営地下鉄 烏丸線＋東西線の公式CSV(source/) から timetable.json を生成する。
（烏丸御池での乗換に対応。アプリ側で 烏丸御池 経由の2レグ接続を計算する）

各路線について high/low の2方向を持つ:
  烏丸線: high=竹田方面(下り) / low=国際会館方面(上り)   order=[国際会館..竹田]
  東西線: high=六地蔵方面(上り) / low=太秦天神川方面(下り) order=[太秦天神川..六地蔵]
  ※ high = order[-1] 方面 / low = order[0] 方面
列車 = {"dest": 行先(終着), "t": {駅名: "HH:MM"}}
"""
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source"
OUT = ROOT / "timetable.json"

ORDER = {
    "烏丸線": ["国際会館", "松ヶ崎", "北山", "北大路", "鞍馬口", "今出川", "丸太町",
              "烏丸御池", "四条", "五条", "京都", "九条", "十条", "くいな橋", "竹田"],
    "東西線": ["太秦天神川", "西大路御池", "二条", "二条城前", "烏丸御池", "京都市役所前",
              "三条京阪", "東山", "蹴上", "御陵", "山科", "東野", "椥辻", "小野",
              "醍醐", "石田", "六地蔵"],
}

COORDS = {
    # 烏丸線
    "国際会館": [35.062921, 135.785117], "松ヶ崎": [35.051652, 135.776071],
    "北山": [35.051243, 135.765209], "北大路": [35.044573, 135.758709],
    "鞍馬口": [35.037182, 135.759303], "今出川": [35.029394, 135.759369],
    "丸太町": [35.016288, 135.759553], "烏丸御池": [35.009974, 135.759619],
    "四条": [35.002518, 135.759588], "五条": [34.99494, 135.759714],
    "京都": [34.986192, 135.759968], "九条": [34.979177, 135.759668],
    "十条": [34.972577, 135.759716], "くいな橋": [34.962281, 135.757046],
    "竹田": [34.956439, 135.756124],
    # 東西線
    "太秦天神川": [35.01078, 135.716202], "西大路御池": [35.010945, 135.730634],
    "二条": [35.011943, 135.741582], "二条城前": [35.01189, 135.750281],
    "京都市役所前": [35.010813, 135.768342], "三条京阪": [35.009291, 135.773985],
    "東山": [35.009434, 135.779778], "蹴上": [35.007597, 135.790557],
    "御陵": [34.99606, 135.801768], "山科": [34.991262, 135.817262],
    "東野": [34.981957, 135.816675], "椥辻": [34.972709, 135.814901],
    "小野": [34.961145, 135.812689], "醍醐": [34.950669, 135.810651],
    "石田": [34.940626, 135.804006], "六地蔵": [34.934001, 135.796469],
}

# day -> line -> (high_csv, low_csv)
FILES = {
    "weekday": {
        "烏丸線": ("烏丸線　平日　下り（竹田／新田辺・近鉄奈良方面）.csv",
                  "烏丸線　平日　上り（国際会館方面）.csv"),
        "東西線": ("東西線　平日　上り（六地蔵／びわ湖浜大津方面）.csv",
                  "東西線　平日　下り（太秦天神川方面）.csv"),
    },
    "holiday": {
        "烏丸線": ("烏丸線　土曜・休日　下り（竹田／新田辺・近鉄奈良方面）.csv",
                  "烏丸線　土曜・休日　上り（国際会館方面）.csv"),
        "東西線": ("東西線　土曜・休日　上り（六地蔵／びわ湖浜大津方面）.csv",
                  "東西線　土曜・休日　下り（太秦天神川方面）.csv"),
    },
}


def load(path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            return list(csv.reader(io.StringIO(raw.decode(enc))))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"decode failed: {path}")


def trains(rows, order):
    header = rows[3]
    idx = {st: header.index(st) for st in order if st in header}
    out = []
    for r in rows[4:]:
        t = {}
        for st, ci in idx.items():
            if ci < len(r) and r[ci].strip():
                t[st] = r[ci].strip()
        if len(t) >= 2:
            out.append({"dest": (r[0] or "").strip(), "t": t})
    return out


def main():
    station_line = {}
    for ln, order in ORDER.items():
        for st in order:
            station_line.setdefault(st, [])
            if ln not in station_line[st]:
                station_line[st].append(ln)

    data = {
        "system": "京都市営地下鉄",
        "revision": "2025-02-22",
        "source": "出典: 京都市オープンデータ「京都市営地下鉄時刻表（令和7年2月22日改正）」CC BY 4.0"
                  "／近鉄直通ダイヤは令和8年3月14日改正",
        "note": "烏丸御池で乗換(一律5分見込み)。high=order末尾方面/low=order先頭方面。0:xxは翌日早朝。",
        "transfer": "烏丸御池",
        "transferMin": 5,
        "order": ORDER,
        "coords": COORDS,
        "stationLine": station_line,
    }
    for day, lines in FILES.items():
        data[day] = {}
        for ln, (hi, lo) in lines.items():
            data[day][ln] = {
                "high": trains(load(SRC / hi), ORDER[ln]),
                "low":  trains(load(SRC / lo), ORDER[ln]),
            }
            print(f"{day} {ln}: high {len(data[day][ln]['high'])}本 / low {len(data[day][ln]['low'])}本")

    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    print(f"-> {OUT}  ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
