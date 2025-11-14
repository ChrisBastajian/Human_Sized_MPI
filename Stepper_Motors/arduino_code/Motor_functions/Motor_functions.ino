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

//Function for single motor calculations - used to calculate values needed for PWM signal 
//Requires: desired angle movement, desired time to run, and subdivision the motor is operating at
float single_motor_calc(float total_angle, float total_time, float subdivision){
  float deg_per_step = 360.0/subdivision;              // (Deg/step) = (deg/rev) * (rev/steps)
  float total_steps = total_angle / deg_per_step;      // (steps) = (angle) * (steps/angle)
  float steps_per_sec = total_steps / total_time;      // (steps/sec) = (steps) / (sec)
  float sec_per_step = 1/steps_per_sec;                // (sec/step) = (steps/sec)^-1
  return steps_per_sec;
}


//Function for testing single motor
void test_motor(float total_angle, float total_time, float subdivsion, int direction_pin, int pulse_pin){
  
  // For determining whether the motor moves clockwise or counterclockwise:
  if (total_angle < 0){
    digitalWrite(direction_pin, LOW);
  }
  else{
    digitalWrite(direction_pin, HIGH);
  }
  
  // For determining the period of the PWM
  float steps_per_sec = single_motor_calc(total_angle, total_time, subdivsion);
  Serial.println(steps_per_sec);
  long total_steps = (long)(steps_per_sec * total_time);     //Recalculating for the loop limits
  Serial.println(total_steps);
  float step_delay = 1000000.0 / steps_per_sec / 2.0;
  Serial.println(step_delay);
  float count = 0;
  //For generating the PWM
  //Since the delay needs to be an int, if the step_delay is a decimal, ms should be converted to ms.
  //However, delayMicroseconds is only accurate up to 16838 us. Delay(ms) is still required for higher subdivisions.
  if (step_delay < 16383){
    unsigned long step_delay_us = 1000000.0 / steps_per_sec / 2.0; //converting to us
    Serial.println(step_delay_us);
    for (long i = 0; i < total_steps ; i++){ 
      digitalWrite(pulse_pin, HIGH);
      delayMicroseconds(step_delay_us);
      digitalWrite(pulse_pin, LOW);
      delayMicroseconds(step_delay_us);
      // For debug purposes:
      count = count + (step_delay_us * 2);
      Serial.println("timer " + String(count));
    }
  }else{
    unsigned long step_delay_ms = 1000.0 / steps_per_sec / 2.0;
    for (long i = 0; i < total_steps ; i++){ 
      digitalWrite(pulse_pin, HIGH);
      delay(step_delay_ms);
      digitalWrite(pulse_pin, LOW);
      delay(step_delay_ms);
      // For debug purposes:
      count = count + (step_delay * 2);
      //Serial.println("timer " + String(count));
    }
  }
}
//Movement of the Motor: 
//both x-y axis and z-axis motors have the same degrees per step, therefore same function required. 
//angle in degrees, total_time in seconds
void both_motors(float xy_angle, float z_angle, float total_time, float xy_subdivsion, float y_subdivsion){
    // For determining whether the motor moves clockwise or counterclockwise:
  if (xy_angle < 0){
    digitalWrite(DIR1, LOW);
  }
  else{
    digitalWrite(DIR1, HIGH);
  }
  if (z_angle < 0){
    digitalWrite(DIR2, LOW);
  }
  else{
    digitalWrite(DIR2, HIGH);
  }
  float xy_steps_per_sec = single_motor_calc(xy_angle, total_time, xy_subdivsion);
  float z_steps_per_sec = single_motor_calc(z_angle, total_time, y_subdivsion);
  
  long xy_total_steps = (long)(xy_steps_per_sec * total_time);
  long z_total_steps = (long)(z_steps_per_sec * total_time);
  Serial.println(xy_total_steps);
  Serial.println(z_total_steps);
  float xy_step_delay = 1000000.0 / xy_steps_per_sec / 2.0;
  float z_step_delay = 1000000.0 / z_steps_per_sec / 2.0;
  Serial.println(xy_step_delay);
  Serial.println(z_step_delay);

  //For generating the PWM
  //Since the delay needs to be an int, if the step_delay is a decimal, ms should be converted to ms.
  //However, delayMicroseconds is only accurate up to 16838 us. Delay(ms) is still required for higher subdivisions.
  //Need to create if statements to determine what type of delay is used for each variable
  
  bool state_xy = true; //For determining xy state
  bool state_z = true;  //For determining z state

  if (xy_step_delay < 16383 && z_step_delay >= 16383){
    unsigned long xy_step_delay_us = 1000000.0 / xy_steps_per_sec / 2.0; //converting to us
    unsigned long z_step_delay_ms = 1000.0 / z_steps_per_sec / 2.0;      //converting to ms
    long delay_xy = xy_step_delay_us;
    long delay_z = z_step_delay_ms;
    for (long i = 0; i < xy_total_steps ; i++){                          //To send two PWM signals with varying frequencies at once, the statements will determine how 
      if(delay_z < delay_xy){                                            //long the delay needs to be to achieve the desired steps/sec. Since the signals have varying frequencies,
        delay(delay_z);                                                  //the delays will not usually be in phase with each other, and they can be checked to determine when each 
        delay_xy = delay_xy - (delay_z * 1000);                          //signal needs to change HIGH vs. LOW.
        state_z = !state_z;
        digitalWrite(PU2, state_z);
        delay_z = z_step_delay_ms;
      }if(delay_xy < delay_z){
        delayMicroseconds(delay_xy);
        delay_z = delay_z - (delay_xy / 1000);
        state_xy = !state_xy;
        digitalWrite(PU1, state_xy);
        delay_xy = xy_step_delay_us;
      }else{
        state_xy = !state_xy;
        state_z = !state_z;
        digitalWrite(PU1, state_xy);
        digitalWrite(PU2, state_z);
        delay_xy = xy_step_delay_us;
        delay_z = z_step_delay_ms;
      }
    }
  }if (xy_step_delay >= 16383 && z_step_delay < 16838){
    unsigned long xy_step_delay_ms = 1000.0 / xy_steps_per_sec / 2.0;    //converting to us
    unsigned long z_step_delay_us = 1000000.0 / z_steps_per_sec / 2.0;   //converting to ms
    long delay_xy = xy_step_delay_ms;
    long delay_z = z_step_delay_us;
    for (long i = 0; i < xy_total_steps ; i++){ 
      if(delay_z < (delay_xy * 1000)){
        delayMicroseconds(delay_z);
        delay_xy = delay_xy - (delay_z / 1000);
        state_z = !state_z;
        digitalWrite(PU2, state_z);
        delay_z = z_step_delay_us;
      }if(delay_xy < (delay_z/1000)){
        delay(delay_xy);
        delay_z = delay_z - (delay_xy * 1000);
        state_xy = !state_xy;
        digitalWrite(PU1, state_xy);
        delay_xy = xy_step_delay_ms;
      }else{
        state_xy = !state_xy;
        state_z = !state_z;
        digitalWrite(PU1, state_xy);
        digitalWrite(PU2, state_z);
        delay_xy = xy_step_delay_ms;
        delay_z = z_step_delay_us;
      }
    }
  }if (xy_step_delay < 16383 && z_step_delay < 16363){
    unsigned long xy_step_delay_us = 1000000.0 / xy_steps_per_sec / 2.0; //converting to us
    unsigned long z_step_delay_us = 1000000.0 / z_steps_per_sec / 2.0;   //converting to ms
    long delay_xy = xy_step_delay_us;
    long delay_z = z_step_delay_us;

    long countxy = 0;
    long countz  = 0;

    for (long i = 0; i <= xy_total_steps ; i++){ 
      if(delay_z < delay_xy){
        delayMicroseconds(delay_z);
        delay_xy = delay_xy - delay_z;
        state_z = !state_z;
        digitalWrite(PU2, state_z);
        delay_z = z_step_delay_us;
      }if(delay_xy < delay_z){
        delayMicroseconds(delay_xy);
        delay_z = delay_z - delay_xy;
        state_xy = !state_xy;
        digitalWrite(PU1, state_xy);
        delay_xy = xy_step_delay_us;
      }else{
        state_xy = !state_xy;
        state_z = !state_z;
        digitalWrite(PU1, state_xy);
        digitalWrite(PU2, state_z);
        delay_xy = xy_step_delay_us;
        delay_z = z_step_delay_us;
      }
      countxy = countxy + delay_xy;
      //Serial.println(countxy);
      //Serial.println(countxy);
    }
  }else{  //both signals are in ms
    unsigned long xy_step_delay_ms = 1000.0 / xy_steps_per_sec / 2.0; //converting to us
    unsigned long z_step_delay_ms = 1000.0 / z_steps_per_sec / 2.0;   //converting to ms
    long delay_xy = xy_step_delay_ms;
    long delay_z = z_step_delay_ms;
    for (long i = 0; i < xy_total_steps ; i++){ 
      if(delay_z < delay_xy){
        delay(delay_z);
        delay_xy = delay_xy - delay_z;
        state_z = !state_z;
        digitalWrite(PU2, state_z);
        delay_z = z_step_delay_ms;
      }if(delay_xy < delay_z){
        delay(delay_xy);
        delay_z = delay_z - delay_xy;
        state_xy = !state_xy;
        digitalWrite(PU1, state_xy);
        delay_xy = xy_step_delay_ms;
      }else{
        state_xy = !state_xy;
        state_z = !state_z;
        digitalWrite(PU1, state_xy);
        digitalWrite(PU2, state_z);
        delay_xy = xy_step_delay_ms;
        delay_z = z_step_delay_ms;
        
      }
    }
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
  
  //test_motor(180, 5, 400, DIR1, PU1);
  both_motors(180, 100, 60, 40000, 40000);

  Serial.println("All Done!");
  // put your main code here, to run repeatedly:
  // if ((digitalRead(ALM1) == LOW) && (digitalRead(ALM2) == LOW)){

  // }else{
  // }

}
