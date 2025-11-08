#define ALM1 0
#define PEND1 1
#define ENA1 2
#define DIR1 3
#define PU1 4
#define ALM2 A0
#define ENA2 A1
#define DIR2 A2
#define PU2 A3

// Relevant info:
// The inherent angle of each step is approximately 1.8 +/- 5%
// This has an error of +/- 0.09 degrees per step
// Meaning, the number of steps within 180 degrees is approximately:
// 180/1.8 = 100 steps
// The stepper motor can take half-steps, therefore
// 180/0.9 = 200 half steps
// Per complete revolution, there are 400 half-steps.
// For simplicity, the subdivision is 400 steps per revolution

// Ideally, 2.5 revolutions per minute:
// 2.5 rev/min * 1 min/60sec  = 0.04167 revs/sec
// 0.04167 rev/sec * 400 steps/rev = 16.67 steps/sec
// 16.67 steps/sec * 1.8 degrees/step = 30 degrees/sec
// With the subdivisions, each rotation will be longer but more accurate
// RPM = (steps/sec) * 60 (sec/minute) / 400 (steps/revolution)

//Global Variables
float deg_per_step = 1.8; //Degrees per step

//Function for single motor calculations - used to calculate values needed for PWM signal
  //The amount of seconds per step is the period of the signal. 
float single_motor_calc(float total_angle, float total_time){
  float total_steps = total_angle / deg_per_step;      // (steps) = (angle) * (steps/angle)
  float steps_per_sec = total_steps / total_time;      // (steps/sec) = (steps) / (sec)
  float angle_per_sec = steps_per_sec * deg_per_step;  // (angle/sec) = (steps/sec) * (angle/steps)
  float sec_per_step = 1/steps_per_sec;                // (sec/step) = (steps/sec)^-1
  return sec_per_step;

}

//Function for testing single motor
void test_motor(float total_angle, float total_time, int PIN){
  float sec_per_step = single_motor_calc(total_angle, total_time);

//for debug purposes
  float count = 0;

for (float i = 0; i <= total_time ; i ++){ 
  digitalWrite(PIN, HIGH);
  delay(sec_per_step/2);
  digitalWrite(PIN, LOW);
  delay(sec_per_step/2);
  count = count + sec_per_step;
  Serial.println("Seconds Per Step " + String(count));
}
}

//Movement of the Motor: 
//both x-y axis and z-axis motors have the same degrees per step, therefore same function required. 
//angle in degrees, total_time in seconds
void both_motors(float xy_angle, float z_angle, float total_time){
  float xy_sec_per_step = single_motor_calc(xy_angle, total_time);
  float z_sec_per_step = single_motor_calc(z_angle, total_time);

for (float i = 0; i <= total_time ; i ++){ 
  
  digitalWrite(PU1, HIGH);
  digitalWrite(PU2, HIGH);
  delay(z_sec_per_step/2);   
  digitalWrite(PU2, LOW);
  delay((xy_sec_per_step/2) - (z_sec_per_step/2));
  digitalWrite(PU1, LOW);
  //THIS IS WRONG RN, WILL FIX
  delay(z_sec_per_step/2);
  delay(xy_sec_per_step/2);

}
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  pinMode(ALM1, INPUT);    //Alarm, x-y stepper motor
  pinMode(PEND1, OUTPUT); 
  pinMode(ENA1, OUTPUT);  
  pinMode(DIR1, OUTPUT);  
  pinMode(PU1, OUTPUT);    //PWM Signal

  digitalWrite(ENA1, LOW); //According to Spec sheet, enable at logic high will disable motor
  digitalWrite(ENA2, LOW); 
  
}
void loop() {
  // put your main code here, to run repeatedly:

  if ((digitalRead(ALM1) == LOW) && (digitalRead(ALM2) == LOW)){
  test_motor(180, 30);  //Example, change to desired function/values

  }else{

  }

}