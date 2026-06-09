// shut.cpp
#include "shut.h"
#include <Servo.h>
#include <LiquidCrystal.h>

// ===== ピン設定 =====
const int SERVO1_PIN = 3;
const int SERVO2_PIN = 5;
const int SERVO3_PIN = 6;

// トグルスイッチ
const int MODE_SWITCH_PIN   = 7;  // REMOTE / DIRECT
const int DIRECT_SWITCH_PIN = 2;  // DIRECT時の ON / OFF

// LCD (例)
const int LCD_RS = 12;
const int LCD_EN = 11;
const int LCD_D4 = 10;
const int LCD_D5 = 9;
const int LCD_D6 = 8;
const int LCD_D7 = 4;

// ===== サーボ・LCD オブジェクト =====
Servo servo1;
Servo servo2;
Servo servo3;

LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);

// ===== モード定義 =====
enum ControlMode {
  MODE_REMOTE = 0,
  MODE_DIRECT = 1
};

enum DirectState {
  DIRECT_CLOSED = 0,
  DIRECT_OPEN   = 1
};

static ControlMode currentMode   = MODE_REMOTE;
static DirectState currentDirect = DIRECT_CLOSED;

// ===== サーボ状態: true = OPEN, false = CLOSE =====
static bool servoState[3] = {false, false, false};

// サーボ角度（必要に応じて調整）
const int SERVO_ANGLE_CLOSED = 0;   // シャッター閉
const int SERVO_ANGLE_OPEN   = 90;  // シャッター開

// シリアル入力行バッファ
static String serialLine;

// LCD 更新タイミング
static unsigned long lastLcdUpdate = 0;
const unsigned long LCD_UPDATE_INTERVAL_MS = 250;

// ===== サーボ制御関数 =====
static void applyServoState(int index) {
  int angle = servoState[index] ? SERVO_ANGLE_OPEN : SERVO_ANGLE_CLOSED;
  switch (index) {
    case 0: servo1.write(angle); break;
    case 1: servo2.write(angle); break;
    case 2: servo3.write(angle); break;
  }
}

static void setServoState(int index, bool open) {
  if (index < 0 || index > 2) return;
  if (servoState[index] == open) return;
  servoState[index] = open;
  applyServoState(index);
}

static void setAllServos(bool open) {
  for (int i = 0; i < 3; ++i) {
    servoState[i] = open;
    applyServoState(i);
  }
}

// ===== シリアルコマンド処理 =====
// REMOTEモード時のみ使用
static void processCommand(const String &cmd) {
  if (cmd.length() < 2) return;

  char ch = cmd[0];
  char st = cmd[1];

  bool open = (st == '1' || st == 'O' || st == 'o');

  if (ch == '1') {
    setServoState(0, open);
  } else if (ch == '2') {
    setServoState(1, open);
  } else if (ch == '3') {
    setServoState(2, open);
  } else if (ch == 'A' || ch == 'a') {
    setAllServos(open);
  } else {
    // 未知コマンドは無視
    return;
  }

  Serial.print(F("CMD: "));
  Serial.println(cmd);
}

static void handleSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialLine.length() > 0) {
        processCommand(serialLine);
        serialLine = "";
      }
    } else {
      if (serialLine.length() < 16) {
        serialLine += c;
      }
    }
  }
}

// ===== LCD 表示 =====
static void updateLcd() {
  lcd.clear();

  lcd.setCursor(0, 0);
  if (currentMode == MODE_REMOTE) {
    lcd.print(F("Mode: REMOTE   "));
  } else {
    if (currentDirect == DIRECT_OPEN) {
      lcd.print(F("Mode:DIRECT O  "));
    } else {
      lcd.print(F("Mode:DIRECT C  "));
    }
  }

  lcd.setCursor(0, 1);
  lcd.print(F("S1:"));
  lcd.print(servoState[0] ? 'O' : 'C');
  lcd.print(F(" S2:"));
  lcd.print(servoState[1] ? 'O' : 'C');
  lcd.print(F(" S3:"));
  lcd.print(servoState[2] ? 'O' : 'C');
}

// ===== 外部公開関数 =====

void shutterSetup() {
  Serial.begin(115200);

  // サーボ
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo3.attach(SERVO3_PIN);

  // スイッチ入力
  pinMode(MODE_SWITCH_PIN,   INPUT_PULLUP);  // 中央端子 -> ピン, 片側 -> GND
  pinMode(DIRECT_SWITCH_PIN, INPUT_PULLUP);

  // LCD
  lcd.begin(16, 2);

  // 初期は全閉 & REMOTEモード
  setAllServos(false);
  currentMode   = MODE_REMOTE;
  currentDirect = DIRECT_CLOSED;

  updateLcd();

  Serial.println(F("Ready."));
  Serial.println(F("REMOTE: A0/A1, 10/11,20/21,30/31 etc."));
}

void shutterLoop() {
  // スイッチ読み取り
  bool modeDirect = (digitalRead(MODE_SWITCH_PIN) == LOW);   // レバーがGND側なら DIRECT
  bool dirOpen    = (digitalRead(DIRECT_SWITCH_PIN) == LOW); // レバーがGND側なら OPEN

  ControlMode newMode = modeDirect ? MODE_DIRECT : MODE_REMOTE;
  DirectState newDirectState = dirOpen ? DIRECT_OPEN : DIRECT_CLOSED;

  // 状態が変わったら反映
  if (newMode != currentMode || newDirectState != currentDirect) {
    currentMode   = newMode;
    currentDirect = newDirectState;

    if (currentMode == MODE_DIRECT) {
      // DIRECTモードではスイッチ状態に応じてサーボ一括制御
      if (currentDirect == DIRECT_OPEN) {
        setAllServos(true);
      } else {
        setAllServos(false);
      }
    }

    updateLcd();
  }

  // REMOTEモードのときだけシリアル制御を受け付ける
  if (currentMode == MODE_REMOTE) {
    handleSerial();
  }

  // 定期的にLCD更新（実質状態変化時だけでもいいが）
  unsigned long now = millis();
  if (now - lastLcdUpdate > LCD_UPDATE_INTERVAL_MS) {
    lastLcdUpdate = now;
    updateLcd();
  }
}
