// shut.h
#pragma once

#include <Arduino.h>

// シャッター系の初期化（Arduinoのsetup()から呼ぶ）
void shutterSetup();

// メインループ（Arduinoのloop()から呼ぶ）
void shutterLoop();
