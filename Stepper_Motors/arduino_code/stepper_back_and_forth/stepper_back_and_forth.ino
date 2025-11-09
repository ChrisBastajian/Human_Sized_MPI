#define PUL_PIN A3
#define DIR_PIN A2
#define ENA_PIN A1
const long steps_per_revolution = 51200; //there are 51200 steps per revolution with current config.
const float rpm = 10;


//Functions:
void rotate_degrees(float degrees, float rpm){
  long steps = (long)(steps_per_revolution * (degrees/360.0));
  Serial.println(steps);
  if (steps<0){
    digitalWrite(DIR_PIN, LOW); //
    steps = -steps; //reversing direction
  }
  else{
    digitalWrite(DIR_PIN, HIGH);
  }
  //Calculating delay between steps for desired rpm:
  float steps_per_sec = (rpm* steps_per_revolution)/60.0;

  unsigned long step_delay = 1000000.0/steps_per_sec/2; //us (half period)

  for (long i=0; i<steps; i++){
    digitalWrite(PUL_PIN, HIGH);
    delayMicroseconds(step_delay);
    digitalWrite(PUL_PIN, LOW);
    delayMicroseconds(step_delay);
  }
}

void setup() {
  // put your setup code here, to run once:
  pinMode(PUL_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENA_PIN, OUTPUT);

  digitalWrite(ENA_PIN, LOW); //enable
  Serial.begin(9600);
}

void loop() {
  // put your main code here, to run repeatedly:

  rotate_degrees(180, rpm); //CW
  delay(1000);
  rotate_degrees(-180, rpm); //CCW
  delay(1000);
}
