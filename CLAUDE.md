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
```

## Architecture

- `src/main.cpp` — メインファームウェア（3ch サーボシャッター）

## Git Rules

- **main 直 commit。ブランチを切るな。** 1 issue = 1 commit on main.
- コミットメッセージ: `feat(Closes #N): ...` / `fix(#N): ...`
