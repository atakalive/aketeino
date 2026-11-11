# aketeino

[English](README.md) | 日本語

Arduino Nano R4 (RA4M1) 用の **3ch サーボシャッター**ファームウェアです。
シリアルコマンドで最大3個のサーボを独立に制御し、開/閉のシャッター動作を行います。
プロジェクトは [PlatformIO](https://platformio.org/) で管理しています。

## 特徴

- サーボ **3チャンネル**を独立制御
- 開角度・閉角度を**ランタイムでシリアルから設定**可能
- シンプルな1文字ベースのシリアルコマンド(115200 baud)
- 依存ライブラリなし・単一HTMLの**動作確認用GUI**(Web Serial)付き
- ターミナル・スクリプト・LLM エージェント(Claude Code など)から操作できる **CLI** 付き

## 必要なもの

- Arduino Nano R4(RA4M1 / `nano_r4`)
- サーボモータ × 最大3個
- PlatformIO(`pio` CLI、または PlatformIO IDE / VS Code 拡張)
- GUI を使う場合: Chrome または Edge(Web Serial API 対応ブラウザ)
- CLI を使う場合: Python 3.9 以上と pyserial(または uv)

## 部品表 (BOM)

| # | 品名 | 数量 | 備考 |
| - | ---- | ---- | ---- |
| 1 | Arduino Nano R4(RA4M1 / `nano_r4`) | 1 | メインボード |
| 2 | サーボモータ(3線式・PWM 制御) | 1〜3 | 制御するシャッターのch数ぶん。開発では SG90 を使用 |
| 3 | ジャンパワイヤ / 配線 | 適量 | 信号・電源・GND の接続用 |
| 4 | サーボ用外部 5V 電源(任意) | 0〜1 | 2 台以上、特に 3 台を動かすときに推奨。1 台でも USB 給電で電流が足りないときは使う。GND はボードとつなぐ |
| 5 | 電解コンデンサ(任意) | 0〜1 | サーボの電源と GND の間(サーボの近く)に並列接続し、静止保持中のサーボの微動(ジッタ)を抑える。470〜1000µF 程度、耐圧 10 V 以上 |

## 配線

サーボの信号線を以下のピンへ接続します(いずれも PWM 対応ピン)。

| チャネル | 信号ピン |
| -------- | -------- |
| CH1      | D3       |
| CH2      | D5       |
| CH3      | D6       |

サーボの 3 本の線は次のようにつなぎます。

| サーボの線 | つなぐ先 |
| ---------- | -------- |
| 信号(橙・黄・白など) | 上の表のピン(D3 / D5 / D6) |
| 電源(赤) | 1 台: ボードの +5V ピン(USB 給電でよい。下の注意を参照) / 2 台以上(特に 3 台): 外部 5V 電源の +(推奨) |
| GND(茶・黒など) | ボードの GND。外部電源を使うときは、外部電源の − もボードの GND につなぐ |

- USB 給電で取れる電流は、ボード自身の分も含めて 500 mA までです。これは USB 2.0 の上限で、PC のポートやハブによってはもっと少ないことがあります。
- サーボは、動き出す瞬間や、負荷が重いとき、動きを止められたとき(ロック)に大きな電流を流します。
  1 台でも、ボードがリセットする・サーボの動きが乱れるなど電流が足りない様子があれば、外部 5V 電源を使ってください。
- 外部 5V 電源は、つなぐサーボ全部のロック時の電流(各データシートの stall current)の合計以上を流せるものを選んでください。
  値が分からないサーボは、多めに見積もってください。
- **外部 5V 電源の + を、ボードの +5V ピンにはつながないでください**(つなぐのはサーボの赤い線だけ)。
- **サーボの微動(ジッタ)対策**: 指令を出していない静止保持中でも、電源ラインのノイズや
  電圧変動でサーボが微動することがあります。サーボの電源と GND の間(ボードの +5V ピンか外部 5V 電源の +。サーボの近く)に、
  電解コンデンサ(470〜1000µF 程度、耐圧 10 V 以上)を並列に入れて電源を安定させると、
  この微動を抑えられます。コンデンサの極性(+/−)に注意してください。
- ピン配置の全体は [simple-pinout.png](simple-pinout.png) を参照してください。この図は Arduino による Nano R4 のピン配置図です(出典: [Arduino Docs](https://github.com/arduino/docs-content/blob/dab66ecbd6ad52cd742da6c19c5b6330a7f2caae/content/hardware/nano/boards/nano-r4/tutorials/01.user-manual/assets/simple-pinout.png)、ライセンス: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/))。

## ビルド・書き込み・モニタ

```bash
# ビルド
pio run

# アップロード(実機接続時)
pio run --target upload

# シリアルモニタ
pio device monitor -b 115200
```

## シリアルコマンド

115200 baud。1行 = 1コマンドで、改行(`\n` / `\r`)で確定します。

### 文法

```text
<cmd>[ch1-3][ <angle>]
```

- `cmd` … コマンド文字(下表)
- `ch` … チャネル `1`〜`3`。**省略時は CH1**。
- `angle` … 角度 `0`〜`180`。**コマンド/チャネルとの間にスペースが必須**。

### コマンド一覧

| cmd | 意味 |
| --- | ---- |
| `o` | 開く(設定済みの**開角度**へ移動) |
| `c` | 閉じる(設定済みの**閉角度**へ移動) |
| `O [angle]` | **開角度を設定**して移動(角度を省略すると現在の開角度へ移動するだけ) |
| `C [angle]` | **閉角度を設定**して移動(角度を省略すると現在の閉角度へ移動するだけ) |
| `a` / `A` `<angle>` | 任意角度へ移動(角度は必須。無いと `ERR: angle required`) |
| `q` / `Q` | 現在角度を照会 |
| `s` / `S` | 状態を照会(現在角度・開角度・閉角度) |

- 既定値: **開 = 90° / 閉 = 0°**
- 角度範囲は 0〜180(範囲外はクランプ、非数値は 0 として扱う)
- 起動時は各chとも**閉(0°)**

### 例

| 入力 | 動作 |
| ---- | ---- |
| `o2` | CH2 を開く |
| `O1 120` | CH1 の開角度を 120° に設定して移動 |
| `A2 90` | CH2 を 90° へ移動 |
| `C3 10` | CH3 の閉角度を 10° に設定して移動 |
| `q2` | CH2 の現在角度を照会 |
| `s2` | CH2 の状態を照会(例 `90 90 0`) |

### 応答

- 成功時: **裸の数値**(現在角度、または設定した角度)
- `s` / `S` の成功時: **半角スペース 1 つ区切りの数値 3 つ** — `<現在角度> <開角度> <閉角度>`(例 `90 90 0`)
- エラー時: `ERR: ...`
- 未知のコマンド: `UNKNOWN CMD: ...`

## ⚠️ 大文字・小文字の罠

開/閉コマンドは**大文字と小文字で動作が異なります**。混同に注意してください。

- `o` / `c`(小文字)… **移動のみ**(設定済みの開/閉角度へ動かす)
- `O` / `C`(大文字)… **角度を設定してから移動**
- 一方 `a` / `A`、`q` / `Q`、`s` / `S` は**大文字・小文字どちらでも同じ**

## 起動時の挙動

電源投入時・リセット時、`setup()` で各サーボを `attach()` した直後に
**閉位置(0°)を書き込みます**(`attach()` のデフォルト 1500us=90° へのジャンプを抑えるため)。
そのため起動の瞬間に全チャネルが閉方向へ動きます。

起動後、シリアルに以下のバナーを出力します。

```text
READY (3ch servo shutter)
cmd: <o|c|O|C|a|q|s>[ch1-3][ angle]  e.g. o2 / O1 / A2 90 / C3 10 / q2 / s2
```

## 制限・注意点

- 1行は**最大16文字**まで(超過分は切り捨て)。
- チャネルは**1桁のみ**。`o12` のようにコマンド/チャネル直後が空白でも行末でもない場合は `ERR` になります。
- `o` / `c` / `q` / `s` にうっかり付けた引数は**無視**されます。
- 応答には**チャネル識別子が含まれません**。後述のGUIは、送信したチャネルを
  FIFO(送信順)で応答行へ対応付けています。
- 開角度・閉角度は **RAM にだけ保持**します。リセットや電源の入れ直しで既定値(開 90° / 閉 0°)に戻ります。
- `q` / `Q` と `s` / `S` が返す現在角度は**最後に指令した角度**で、サーボの実際の位置を測った値ではありません。

## 動作確認用GUI

[gui/index.html](gui/index.html) を **Chrome / Edge** で開くと、ボタン操作で各chを
動かして動作確認できます(Web Serial API を使用)。

1. まず `file://` で HTML を直接開いて試します。
2. 動かない場合はプロジェクトルートで簡易サーバを起動し、`http://localhost:8000/gui/` で開きます。
   ```bash
   python -m http.server
   ```
3. 他のシリアルモニタ(`pio device monitor` など)を**閉じてから** Connect してください
   (COM ポートは1プロセスが占有するため)。
4. Connect 時にボードがリセットされ、READY バナーが表示されることがあります。

## CLI

[cli/aketeino.py](cli/aketeino.py) で、ターミナルからボードを操作できます。1 回呼ぶとポートを開き、
コマンドを送って応答を待ち、結果を出して終わります。スクリプトや Claude Code などの LLM エージェントも、
普通のシェルのコマンドとしてシャッターを操作し、状態を読めます。

Python 3.9 以上と [pyserial](https://pypi.org/project/pyserial/)(`python -m pip install pyserial`)が要ります。
[uv](https://docs.astral.sh/uv/) があれば、`uv run cli/aketeino.py ...` で pyserial を自動で入れて動きます。

```bash
python cli/aketeino.py ports            # シリアルポートの一覧(Nano R4 に [Nano R4] の印)
python cli/aketeino.py status           # 全chの現在角度・開角度・閉角度・状態
python cli/aketeino.py open 2           # CH2 を開く
python cli/aketeino.py close all        # CH1〜CH3 を閉じる
python cli/aketeino.py move 1 45        # CH1 を 45° へ
python cli/aketeino.py set-open 1 120   # CH1 の開角度を 120° に設定して移動
python cli/aketeino.py set-close 3 10   # CH3 の閉角度を 10° に設定して移動
python cli/aketeino.py raw q1 "A2 90"   # ファームのコマンド行をそのまま送る
python cli/aketeino.py --help           # 使い方・終了コード・注意の全体
```

| CLI | 送るファームのコマンド |
| --- | ---------------------- |
| `open <ch>...` | `o` |
| `close <ch>...` | `c` |
| `move <ch> <angle>` | `A <angle>` |
| `set-open <ch> <angle>` | `O <angle>` |
| `set-close <ch> <angle>` | `C <angle>` |
| `status [<ch>...]` | `s`(`ch` を省くと全ch) |
| `raw <line>...` | 行をそのまま(印字可能な ASCII 1〜16 文字) |

- チャネルは `1`・`2`・`3`・`all`、角度は 0〜180 の整数。それ以外は何も送らずに弾きます
  (ファームは黙ってクランプするか 0 として扱うため)。
- 出力は 1 結果 1 行(例 `CH2: 90`)。`status` は次のように出します。
  ```text
  port: COM5
  CH1: 90 (open) open=90 close=0
  CH2: 0 (closed) open=90 close=0
  CH3: 45 (other) open=120 close=10
  ```
  状態は、現在角度が開角度と同じなら `open`、閉角度と同じなら `closed`、どちらでもなければ `other` です。
  角度は最後に指令した値で、サーボの実際の位置を測った値ではありません。
- `--json` を付けると `{"port": "COM5", "results": [...]}` を出します。失敗したときは、それまでの結果に
  `"error": {"code": ..., "message": ...}` を添えて出します。
- 複数の送信は順に行い、最初の失敗で止めます。エラーは標準エラーに、次にすることの案内と一緒に出します。
- ポート: `--port COM5`、無ければ環境変数 `AKETEINO_PORT`、それも無ければ接続中の Nano R4
  (USB VID 2341 / PID 0074)が 1 台だけのときそれを使います。0 台・2 台以上なら `--port` を指定します。
- **GUI と `pio device monitor` を閉じてから使ってください**(COM ポートは1プロセスが占有するため)。
  ほかのプログラムが開いているポートは CLI から開けません。
- `status` には `s` コマンドのあるファームが要ります。古いファームでは書き込み(`pio run --target upload`)を案内します。

| 終了コード | 意味 |
| ---------- | ---- |
| 0 | 成功 |
| 1 | ボードが `ERR` / `UNKNOWN CMD`、または想定外の形の応答を返した |
| 2 | 引数の誤り(何も送っていない) |
| 3 | ポートが見つからない・開けない・途中で消えた(ボードのリセットなど) |
| 4 | 応答がタイムアウトした(`--timeout`、既定 2 秒) |

テストは実機なしで動きます: `python -m unittest discover -s cli -v`

## プロジェクト構成

```text
aketeino/
├── src/main.cpp       … メインファームウェア(3ch サーボシャッター)
├── gui/index.html     … ホスト側 動作確認GUI(Web Serial、単一HTML・依存なし)
├── cli/               … ホスト側 CLI(aketeino.py、pyserial)とそのテスト
├── platformio.ini     … PlatformIO 設定(env: nano_r4)
├── simple-pinout.png  … Nano R4 ピン配置図(Arduino、CC BY-SA 4.0)
├── CLAUDE.md          … Claude Code 用の開発ルール
└── LICENSE            … MIT License
```

## ライセンス

[MIT License](LICENSE)

ただし `simple-pinout.png` は Arduino の著作物で、[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) で提供されています。MIT License の対象外です。
