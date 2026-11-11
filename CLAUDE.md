# CLAUDE.md

## What This Is

aketeino — Arduino Nano R4 (RA4M1) 用サーボシャッターファームウェア。PlatformIO で管理。

## Commands

```bash
# ビルド
pio run

# アップロード（実機接続時）
pio run --target upload

# シリアルモニタ
pio device monitor -b 115200

# CLI（ボードの操作と状況の確認）
python cli/aketeino.py --help
python cli/aketeino.py status
python cli/aketeino.py open 2

# CLI のテスト（実機なし）
python -m unittest discover -s cli -v
ruff check cli
```

## Architecture

- `src/main.cpp` — メインファームウェア（3ch サーボシャッター）
- `gui/index.html` — ホスト側 動作確認 GUI（Web Serial、単一HTML・依存なし。Chrome/Edge で開く）
- `cli/aketeino.py` — ホスト側 CLI（pyserial。1 回呼ぶと送って応答を読んで終わる。LLM から操作する手段）
- `cli/test_aketeino.py` — CLI のテスト（`src/main.cpp` を真似た偽ボード。実機なし）

## Operating the Board (LLM)

- サーボの操作と状況の把握は `cli/aketeino.py` で行う。使い方は `--help`。**実物のサーボが動く。**
- 状況は `status`（各 ch の現在角度・開角度・閉角度・状態 `open`/`closed`/`other`）。値は最後に指令した角度で、実際の位置ではない。
- 機械が読むなら `--json`。終了コード: 0 成功 / 1 ボードがエラーを返した / 2 引数の誤り（何も送っていない）/ 3 ポートが無い・開けない・消えた / 4 タイムアウト。
- COM ポートは 1 プロセス占有。GUI や `pio device monitor` を開いていると CLI は開けない（終了コード 3）。

## Git Rules

- **main 直 commit。ブランチを切るな。** 1 issue = 1 commit on main.
- コミットメッセージ: `feat(Closes #N): ...` / `fix(#N): ...`
