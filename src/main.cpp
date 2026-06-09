#include <Arduino.h>
#include <Servo.h>

const int SERVO_PIN = 3;

int SERVO_ANGLE_CLOSED = 0;
int SERVO_ANGLE_OPEN   = 90;

int currentAngle = 0;   // 「今こう書き込んだはず」の角度

Servo servo;
String cmdLine;

int parseAngle(const String &s) {
  int val = s.toInt();
  if (val < 0)   val = 0;
  if (val > 180) val = 180;
  return val;
}

void setServoAngle(int angle) {
  currentAngle = angle;
  servo.write(angle);
}

void processCommand(const String &cmd) {
  if (cmd.length() == 0) return;

  char c0 = cmd[0];

  // 1文字コマンド
  if (cmd.length() == 1) {
    if (c0 == 'o' || c0 == 'O') {
      setServoAngle(SERVO_ANGLE_OPEN);
      //Serial.print("OPEN -> ");
      Serial.println(currentAngle);
      return;
    } else if (c0 == 'c' || c0 == 'C') {
      setServoAngle(SERVO_ANGLE_CLOSED);
      // Serial.print("CLOSE -> ");
      Serial.println(currentAngle);
      return;
    } else if (c0 == 'q' || c0 == 'Q') {
      // 角度問い合わせ（指令値ベース）
      // Serial.print("ANGLE = ");
      Serial.println(currentAngle);
      return;
    }
  }

  // コマンド+数値
  if (cmd.length() >= 2) {
    String arg = cmd.substring(1);
    int angle = parseAngle(arg);

    if (c0 == 'O') {
      SERVO_ANGLE_OPEN = angle;
      setServoAngle(SERVO_ANGLE_OPEN);
      // Serial.print("SET OPEN = ");
      Serial.println(SERVO_ANGLE_OPEN);
      return;
    } else if (c0 == 'C') {
      SERVO_ANGLE_CLOSED = angle;
      setServoAngle(SERVO_ANGLE_CLOSED);
      // Serial.print("SET CLOSE = ");
      Serial.println(SERVO_ANGLE_CLOSED);
      return;
    } else if (c0 == 'A' || c0 == 'a') {
      setServoAngle(angle);
      // Serial.print("MOVE -> ");
      Serial.println(currentAngle);
      return;
    }
  }

  Serial.print("UNKNOWN CMD: ");
  Serial.println(cmd);
}

void setup() {
  Serial.begin(115200);
  servo.attach(SERVO_PIN);

  delay(500);
  setServoAngle(SERVO_ANGLE_CLOSED);

  Serial.println("READY (position servo)");
  Serial.println("Commands:");
  Serial.println("  o / O : move to OPEN angle");
  Serial.println("  c / C : move to CLOSE angle");
  Serial.println("  Oxxx  : set OPEN angle = xxx deg and move");
  Serial.println("  Cxxx  : set CLOSE angle = xxx deg and move");
  Serial.println("  Axxx  : move to angle xxx deg");
  Serial.println("  q / Q : query current angle (commanded)");
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
