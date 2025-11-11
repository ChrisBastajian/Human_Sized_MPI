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
// The stepper motor takes half-steps, therefore
// 180/0.9 = 200 half steps
// Per complete revolution, there are 400 half-steps.
// For simplicity, the subdivision is 400 steps per revolution

// Example: 2.5 revolutions per minute:
// 2.5 rev/min * 1 min/60sec  = 0.04167 revs/sec
// 0.04167 rev/sec * 400 steps/rev = 16.67 steps/sec
// 16.67 steps/sec * 0.9 degrees/step = 15 degrees/sec
// With the subdivisions, each rotation will be longer but more accurate
// RPM = (steps/sec) * 60 (sec/minute) / 400 (steps/revolution)

// Global Variables
long subdivision = 400; // Total Steps in a Revolution 

//Function for single motor calculations - used to calculate values needed for PWM signal 
float single_motor_calc(float total_angle, float total_time){
  float deg_per_step = 360.0/subdivision;              // (Deg/step) = (deg/rev) * (rev/steps)
  float total_steps = total_angle / deg_per_step;      // (steps) = (angle) * (steps/angle)
  float steps_per_sec = total_steps / total_time;      // (steps/sec) = (steps) / (sec)
  float sec_per_step = 1/steps_per_sec;                // (sec/step) = (steps/sec)^-1
  return steps_per_sec;

}

//Function for testing single motor
void test_motor(float total_angle, float total_time, int direction_pin, int pulse_pin){
  
  // For determining whether the motor moves clockwise or counterclockwise:
  if (total_angle < 0){
    digitalWrite(direction_pin, LOW);
  }
  else{
    digitalWrite(direction_pin, HIGH);
  }
  
  // For determining the period of the PWM
  float steps_per_sec = single_motor_calc(total_angle, total_time);
  long total_steps = (long)(steps_per_sec * total_time);     //Recalculating for the loop limits
  //Serial.println(total_steps);
  unsigned long step_delay = 1000.0 / steps_per_sec / 2.0;

  float count = 0;

// Creating PWM signal
  for (long i = 0; i < total_steps ; i++){ 
    digitalWrite(pulse_pin, HIGH);
    delay(step_delay);
    digitalWrite(pulse_pin, LOW);
    delay(step_delay);
    // For debug purposes:
    count = count + (step_delay * 2);
    Serial.println("timer " + String(count));
  }
}

//Movement of the Motor: 
//both x-y axis and z-axis motors have the same degrees per step, therefore same function required. 
//angle in degrees, total_time in seconds
void both_motors(float xy_angle, float z_angle, float total_time, int xy_dir_pin, int z_dir_pin, int xy_pu_pin, int z_pu_pin){

    // For determining whether the motor moves clockwise or counterclockwise:
  if (xy_angle < 0){
    digitalWrite(xy_dir_pin, LOW);
  }
  else{
    digitalWrite(xy_dir_pin, HIGH);
  }

  if (z_angle < 0){
    digitalWrite(z_dir_pin, LOW);
  }
  else{
    digitalWrite(z_dir_pin, HIGH);
  }
  float xy_steps_per_sec = single_motor_calc(xy_angle, total_time);
  float z_steps_per_sec = single_motor_calc(z_angle, total_time);
  
  long xy_total_steps = (long)(xy_steps_per_sec * total_time);
  long z_total_steps = (long)(z_steps_per_sec * total_time);

  unsigned long xy_step_delay = 1000.0 / xy_steps_per_sec / 2.0;
  unsigned long z_step_delay = 1000.0 / z_steps_per_sec / 2.0;

  for (float i = 0; i <= total_time ; i ++){ 
    
    digitalWrite(xy_pu_pin, HIGH);
    digitalWrite(z_pu_pin, HIGH);
    delay(z_step_delay);   
    digitalWrite(z_pu_pin, LOW);
    delay((xy_step_delay) - (z_step_delay));
    digitalWrite(xy_pu_pin, LOW);
    //THIS IS WRONG RN, WILL FIX
    delay(z_step_delay);
    delay(xy_step_delay);

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
  pinMode(ALM2, INPUT);
  pinMode(ENA2, OUTPUT);
  pinMode(DIR2, OUTPUT);
  pinMode(PU2, OUTPUT);

  digitalWrite(ENA1, LOW); //According to Spec sheet, enable at logic high will disable motor
  digitalWrite(ENA2, LOW); 
  
}
void loop() {
  // put your main code here, to run repeatedly:

  test_motor(180, 2, DIR2, PU2);
  delay(5000);
  
  // if ((digitalRead(ALM1) == LOW) && (digitalRead(ALM2) == LOW)){


  // }else{

  // }

}
