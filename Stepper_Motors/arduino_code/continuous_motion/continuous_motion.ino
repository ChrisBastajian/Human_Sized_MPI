#define PUL_PIN 13
#define DIR_PIN 12
#define ENA_PIN 11

const int steps_per_revolution = 1600;  // microstepping setup
float rpm = 5;                         // target speed (adjust freely)

unsigned long lastStepTime = 0;
unsigned long stepDelayMicros = 0;
bool stepState = false;

void setup() {
  pinMode(PUL_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENA_PIN, OUTPUT);

  digitalWrite(ENA_PIN, LOW);   // enable motor driver
  digitalWrite(DIR_PIN, HIGH);  // set initial direction

  // Calculate delay per half-step pulse based on rpm
  float steps_per_sec = (rpm * steps_per_revolution) / 60.0;
  stepDelayMicros = 1000000.0 / (steps_per_sec * 2);
}

void loop() {
  // Toggle the step pin at precise intervals
  if (micros() - lastStepTime >= stepDelayMicros) {
    lastStepTime = micros();
    stepState = !stepState;
    digitalWrite(PUL_PIN, stepState);
  }

    static unsigned long lastDirChange = 0;
  if (millis() - lastDirChange > 5000) {
    lastDirChange = millis();
    digitalWrite(DIR_PIN, !digitalRead(DIR_PIN));
  }
}
