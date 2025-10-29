#define PUL_PIN 13
#define DIR_PIN 12
#define ENA_PIN 11

const int steps_per_revolution = 1600; //there are 1600 steps per revolution with current config.

//Functions:
void rotate_degrees(float degrees, float total_time){
  int steps = (int)(steps_per_revolution * (degrees/360.0));
  if (steps<0){
    digitalWrite(DIR_PIN, LOW); //
    steps = -steps; //reversing direction
    degrees = -degrees;
  }
  else{
    digitalWrite(DIR_PIN, HIGH);
  }
  //Calculating rpm desired:
  float rpm = (degrees/360.0)/(total_time/60.0);//total_time will be in seconds
  
  //Calculating delay between steps for desired rpm:
  float steps_per_sec = (rpm* steps_per_revolution)/60.0;

  unsigned long step_delay = 1000000.0/steps_per_sec/2; //us (half period)

  for (int i=0; i<steps; i++){
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

  rotate_degrees(180, 5.0); //CW
  delay(1000);
  rotate_degrees(-180, 5.0); //CCW
  delay(1000);
}
