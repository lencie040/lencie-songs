# Lencie 自作曲DB

Lencieの自作曲を一覧・検索・再生できるページです。

**サイト:** https://lencie040.github.io/lencie-songs/

## 曲の追加のしかた

GitHubに入れるだけで、数分後にサイトへ自動で反映されます（GitHub Actions）。

1. **音源を追加** — `017_曲名.mp3` のように、先頭に **CSVのIDと同じ番号** を付けてリポジトリ直下に置く
   - バージョン違いは `011_VSレシェ姫_V1.1.mp3` のように `_V番号` を付ける（新しい方が先に再生されます）
   - 対応形式: mp3 / wav / m4a / ogg / flac / aac
2. **CSVを更新** — スプレッドシートから「曲DB」シートをCSVでダウンロードし、`曲DB.csv` に上書き
   - CSVに行が無い音源も「CSV未登録」として表示されます
3. **ジャケ絵（任意）** — `_ジャケ絵/` に `曲名.png`（番号付きでもOK）を置く。ファイル名の曲名で自動で対応付けされます

### アップロード方法
- **ブラウザから:** GitHubのリポジトリページで「Add file → Upload files」にドラッグ＆ドロップして Commit
- **Macから:** このフォルダで
  ```bash
  git add -A && git commit -m "曲を追加" && git push
  ```

## ローカルで見る

```bash
python3 tools/build.py && python3 -m http.server 8000
```

→ http://localhost:8000

## 構成

| ファイル | 役割 |
|---|---|
| `index.html` | 曲一覧ページ（検索・絞り込み・並べ替え・プレイヤー） |
| `曲DB.csv` | 曲データ |
| `tools/build.py` | CSV＋音源＋ジャケ絵から `songs.json` を生成 |
| `.github/workflows/deploy.yml` | push時に自動でビルドしてGitHub Pagesへ公開 |
