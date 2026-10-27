#!/usr/bin/env python3
"""曲DBのCSVと音源・ジャケ絵フォルダを読み取り、songs.json を生成する。

使い方: python3 tools/build.py   （リポジトリのルートで実行）

- CSV: ルートか data/ にある .csv（「曲DB」を含む名前を優先）
- 音源: リポジトリ内の .mp3/.wav/.m4a/.ogg/.flac/.aac
        ファイル名の先頭 "001_" がCSVのIDと対応。"_V1.1" でバージョン指定
- ジャケ絵: _ジャケ絵/ (または jackets/) の画像。曲名を含むファイル名で対応（なければID）
"""
import csv
import json
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
JACKET_DIRS = ["_ジャケ絵", "jackets"]
SKIP_DIRS = {".git", ".github", "tools", "_site", "node_modules"}


def nfc(s):
    # macOSのファイル名はNFDになりがちなので、比較用に正規化する
    return unicodedata.normalize("NFC", s)


def norm_key(s):
    return re.sub(r"[\s_　]+", "", nfc(s)).lower()


def find_csv():
    cands = [p for d in (ROOT, ROOT / "data") if d.is_dir() for p in d.glob("*.csv")]
    if not cands:
        return None
    cands.sort(key=lambda p: ("曲DB" not in nfc(p.name), nfc(p.name)))
    return cands[0]


def clean_header(h):
    # 「汎異記号(説明…)」のような長い説明付き見出しを短くする
    h = nfc(h).strip()
    m = re.match(r"^([^()（）]+)[(（](.+)[)）]$", h)
    if m and len(m.group(2)) > 8:
        return m.group(1).strip(), m.group(2).strip()
    return h, ""


def walk_files(exts, base=ROOT):
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts):
            continue
        if p.is_file() and p.suffix.lower() in exts:
            yield p


def rel_url(p):
    return nfc(p.relative_to(ROOT).as_posix())


def parse_audio(p):
    stem = nfc(p.stem)
    m = re.match(r"^(\d+)[_\-\s](.*)$", stem)
    sid = int(m.group(1)) if m else None
    rest = m.group(2) if m else stem
    vm = re.search(r"[_\s][Vv](\d+(?:\.\d+)*)$", rest)
    version = vm.group(1) if vm else None
    title = rest[: vm.start()] if vm else rest
    return {
        "id": sid,
        "title": title,
        "version": version,
        "file": rel_url(p),
        "format": p.suffix.lower().lstrip("."),
        "size": p.stat().st_size,
    }


def vkey(v):
    try:
        return tuple(int(x) for x in (v or "0").split("."))
    except ValueError:
        return (0,)


def main():
    csv_path = find_csv()
    columns, notes, rows = [], {}, []
    if csv_path:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            for h in header:
                name, note = clean_header(h)
                columns.append(name)
                if note:
                    notes[name] = note
            for r in reader:
                if not any(c.strip() for c in r):
                    continue
                r = (r + [""] * len(columns))[: len(columns)]
                rows.append({c: nfc(v).strip() for c, v in zip(columns, r)})

    audios = [parse_audio(p) for p in walk_files(AUDIO_EXT)]
    jackets = []
    for d in JACKET_DIRS:
        if (ROOT / d).is_dir():
            jackets += [p for p in walk_files(IMAGE_EXT, ROOT / d)]

    all_titles = {norm_key(r.get("曲名", "")) for r in rows if r.get("曲名")}

    def match_jacket(sid, title):
        # 曲名一致を優先。番号一致は、そのジャケが別の曲名を指していない場合のみ
        tkey = norm_key(title)
        for p in jackets:
            body = norm_key(re.sub(r"^\d+[_\-\s]", "", nfc(p.stem)))
            if tkey and body == tkey:
                return rel_url(p)
        for p in jackets:
            m = re.match(r"^(\d+)[_\-\s]?(.*)$", nfc(p.stem))
            if m and sid is not None and int(m.group(1)) == sid and norm_key(m.group(2)) not in all_titles:
                return rel_url(p)
        return None

    songs, used = [], set()
    for r in rows:
        try:
            sid = int(r.get("ID", ""))
        except ValueError:
            sid = None
        title = r.get("曲名", "")
        mine = [a for a in audios if a["id"] is not None and a["id"] == sid]
        if not mine and title:
            mine = [a for a in audios if norm_key(a["title"]) == norm_key(title)]
        mine.sort(key=lambda a: vkey(a["version"]), reverse=True)
        used.update(a["file"] for a in mine)
        songs.append({"id": sid, "registered": True, "fields": r, "audio": mine,
                      "jacket": match_jacket(sid, title)})

    # CSVにまだ無い音源も「未登録」として表示する
    orphans = {}
    for a in audios:
        if a["file"] in used:
            continue
        key = a["id"] if a["id"] is not None else a["title"]
        orphans.setdefault(key, []).append(a)
    for key, group in orphans.items():
        group.sort(key=lambda a: vkey(a["version"]), reverse=True)
        a = group[0]
        songs.append({"id": a["id"], "registered": False,
                      "fields": {"ID": str(a["id"] or ""), "曲名": a["title"]},
                      "audio": group, "jacket": match_jacket(a["id"], a["title"])})

    songs.sort(key=lambda s: (s["id"] is None, s["id"] or 0))
    out = {
        "generated": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"),
        "csv": nfc(csv_path.name) if csv_path else None,
        "columns": columns,
        "columnNotes": notes,
        "songs": songs,
    }
    (ROOT / "songs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"songs.json: {len(songs)}曲 (CSV {len(rows)}行, 音源 {len(audios)}ファイル, ジャケ {len(jackets)}枚)")


if __name__ == "__main__":
    main()
