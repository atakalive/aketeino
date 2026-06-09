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
  int ch;
  String arg;
  if (cmd.length() >= 2 && (cmd[1] == '2' || cmd[1] == '3')
      && (cmd.length() == 2 || !(cmd[2] >= '0' && cmd[2] <= '9'))) {
    ch = cmd[1] - '1';
    arg = cmd.substring(2);
  } else {
    ch = 0;
    arg = cmd.substring(1);
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
    int angle = parseAngle(arg);
    setServoAngle(ch, angle);
    Serial.println(currentAngle[ch]);
  } else if (c0 == 'q' || c0 == 'Q') {
    Serial.println(currentAngle[ch]);
  } else {
    Serial.print("UNKNOWN CMD: ");
    Serial.println(cmd);
  }
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < NUM_CHANNELS; ++i) {
    servos[i].attach(SERVO_PINS[i]);
  }
  delay(500);
  for (int i = 0; i < NUM_CHANNELS; ++i) {
    setServoAngle(i, angleClosed[i]);
  }
  Serial.println("READY (3ch servo shutter)");
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
