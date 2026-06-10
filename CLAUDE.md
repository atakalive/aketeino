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
- `src/shut.cpp` + `include/shut.h` — LCD＋モードスイッチ版の別ファームウェア（スコープ外）
- PlatformIO が `src/` 配下の全 `.cpp` を同時コンパイル。`shut.cpp` のシンボルは全て `static` / `const`

## Git Rules

- **main 直 commit。ブランチを切るな。** 1 issue = 1 commit on main.
- コミットメッセージ: `feat(Closes #N): ...` / `fix(#N): ...`
