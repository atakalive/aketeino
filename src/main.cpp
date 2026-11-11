#include <Arduino.h>
#include <Servo.h>

const int NUM_CHANNELS = 3;
const int SERVO_PINS[NUM_CHANNELS] = {3, 5, 6};

int angleClosed[NUM_CHANNELS] = {0, 0, 0};
int angleOpen[NUM_CHANNELS]   = {90, 90, 90};

int currentAngle[NUM_CHANNELS] = {0, 0, 0};   // 「今こう書き込んだはず」の角度

Servo servos[NUM_CHANNELS];
String cmdLine;

int parseAngle(const String &s) {
  int val = s.toInt();
  if (val < 0)   val = 0;
  if (val > 180) val = 180;
  return val;
}

void setServoAngle(int ch, int angle) {
  if (ch < 0 || ch >= NUM_CHANNELS) return;
  currentAngle[ch] = angle;
  servos[ch].write(angle);
}

void processCommand(const String &cmd) {
  if (cmd.length() == 0) return;

  char c0 = cmd[0];

  // --- チャネル・引数の分離 ---
  // 文法: <コマンド文字>[チャネル1-3][ <角度>]  角度は必ずスペース区切り
  int ch = 0;
  unsigned int pos = 1;
  if (cmd.length() > pos && cmd[pos] >= '1' && cmd[pos] <= '3') {
    ch = cmd[pos] - '1';
    ++pos;
  }
  String arg;
  if (cmd.length() > pos) {
    if (cmd[pos] != ' ') {
      Serial.print("ERR: use <cmd>[1-3] [angle]: ");
      Serial.println(cmd);
      return;
    }
    arg = cmd.substring(pos + 1);
    arg.trim();
  }

  // --- コマンド分岐 ---
  if (c0 == 'o') {
    setServoAngle(ch, angleOpen[ch]);
    Serial.println(currentAngle[ch]);
  } else if (c0 == 'O') {
    if (arg.length() == 0) {
      setServoAngle(ch, angleOpen[ch]);
      Serial.println(currentAngle[ch]);
    } else {
      int angle = parseAngle(arg);
      angleOpen[ch] = angle;
      setServoAngle(ch, angleOpen[ch]);
      Serial.println(angleOpen[ch]);
    }
  } else if (c0 == 'c') {
    setServoAngle(ch, angleClosed[ch]);
    Serial.println(currentAngle[ch]);
  } else if (c0 == 'C') {
    if (arg.length() == 0) {
      setServoAngle(ch, angleClosed[ch]);
      Serial.println(currentAngle[ch]);
    } else {
      int angle = parseAngle(arg);
      angleClosed[ch] = angle;
      setServoAngle(ch, angleClosed[ch]);
      Serial.println(angleClosed[ch]);
    }
  } else if (c0 == 'a' || c0 == 'A') {
    if (arg.length() == 0) {
      Serial.print("ERR: angle required: ");
      Serial.println(cmd);
      return;
    }
    int angle = parseAngle(arg);
    setServoAngle(ch, angle);
    Serial.println(currentAngle[ch]);
  } else if (c0 == 'q' || c0 == 'Q') {
    Serial.println(currentAngle[ch]);
  } else if (c0 == 's' || c0 == 'S') {
    // 状態照会: "<現在角度> <開角度> <閉角度>" を1行で返す
    Serial.print(currentAngle[ch]);
    Serial.print(' ');
    Serial.print(angleOpen[ch]);
    Serial.print(' ');
    Serial.println(angleClosed[ch]);
  } else {
    Serial.print("UNKNOWN CMD: ");
    Serial.println(cmd);
  }
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < NUM_CHANNELS; ++i) {
    // attach() はデフォルトで1500us(=90°)を出すため、直後に閉位置を書いてジャンプを抑える
    servos[i].attach(SERVO_PINS[i]);
    setServoAngle(i, angleClosed[i]);
  }
  Serial.println("READY (3ch servo shutter)");
  Serial.println("cmd: <o|c|O|C|a|q|s>[ch1-3][ angle]  e.g. o2 / O1 / A2 90 / C3 10 / q2 / s2");
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (cmdLine.length() > 0) {
        processCommand(cmdLine);
        cmdLine = "";
      }
    } else {
      if (cmdLine.length() < 16) {
        cmdLine += c;
      }
    }
  }
}
