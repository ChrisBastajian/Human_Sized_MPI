//xy motor variables:
#define ALM1 0
#define PEND1 1
#define ENA1 2
#define DIR1 3
#define PU1 4 //xy

//z motor variables
#define ALM2 A0
#define ENA2 A1
#define DIR2 A2
#define PU2 A3 //z

long steps_per_revolution = 40000; //for both motors so far.

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
    total_angle = -total_angle;
  }
  else{
    digitalWrite(direction_pin, HIGH);
  }
  
  // For determining the period of the PWM
  float steps_per_sec = single_motor_calc(total_angle, total_time, subdivsion);
  //Serial.println(steps_per_sec);
  long total_steps = (long)(steps_per_sec * total_time);     //Recalculating for the loop limits
  float step_delay = 1000000.0 / steps_per_sec / 2.0;
  float count = 0;
  //For generating the PWM
  //Since the delay needs to be an int, if the step_delay is a decimal, ms should be converted to ms.
  //However, delayMicroseconds is only accurate up to 16838 us. Delay(ms) is still required for higher subdivisions.
  if (step_delay < 16383){
    unsigned long step_delay_us = 1000000.0 / steps_per_sec / 2.0; //converting to us
    //Serial.println(step_delay_us);
    for (long i = 0; i < total_steps ; i++){ 
      digitalWrite(pulse_pin, HIGH);
      delayMicroseconds(step_delay_us);
      digitalWrite(pulse_pin, LOW);
      delayMicroseconds(step_delay_us);
      // For debug purposes:
      count = count + (step_delay_us * 2);
      //Serial.println("timer " + String(count));
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
    xy_angle = 2*xy_angle; //dk why but this is what works
    z_angle = 2*z_angle;
    total_time = total_time * 2;
  if (xy_angle < 0){
    xy_angle = -xy_angle;
    digitalWrite(DIR1, LOW);
  }
  else{
    digitalWrite(DIR1, HIGH);
  }
  if (z_angle < 0){
    z_angle = -z_angle;
    digitalWrite(DIR2, LOW);
  }
  else{
    digitalWrite(DIR2, HIGH);
  }
  float xy_steps_per_sec = single_motor_calc(xy_angle, total_time, xy_subdivsion);
  float z_steps_per_sec = single_motor_calc(z_angle, total_time, y_subdivsion);
  
  long xy_total_steps = (long)(xy_steps_per_sec * total_time);
  long z_total_steps = (long)(z_steps_per_sec * total_time);

  unsigned long xy_step_delay = (unsigned long) (1000000.0 / xy_steps_per_sec / 2.0);
  unsigned long z_step_delay = (unsigned long) (1000000.0 / z_steps_per_sec / 2.0);

  unsigned long start_time = micros();
  unsigned long end_time   = start_time + (unsigned long)(total_time * 1000000.0);

  unsigned long next_xy = start_time + xy_step_delay;
  unsigned long next_z  = start_time + z_step_delay;

  long xy_count = 0;
  long z_count  = 0;

  bool xy_state = false;
  bool z_state  = false;

  while (micros() < end_time) {
      unsigned long now = micros();

      if (xy_count < xy_total_steps && now >= next_xy) {
          xy_state = !xy_state;
          digitalWrite(PU1, xy_state);
          next_xy += xy_step_delay; // adds the next half period
          xy_count++;
      }
      
      if (z_count < z_total_steps && now >= next_z) {
          z_state = !z_state;
          digitalWrite(PU2, z_state);
          next_z += z_step_delay;//adds the next half period
          z_count++;
      }
  }
}


String receivedMessage = "";

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
  checkForData();
}

void checkForData() {
  while (Serial.available()) {
    char incomingChar = Serial.read();

    if (incomingChar == '\n') {
      processMessage(receivedMessage);
      receivedMessage = "";
    } 
    else if (incomingChar != '\r') {
      receivedMessage += incomingChar;
    }
  }
}

void processMessage(String msg) {

  // Split by commas (there's always 3 commas regardless of function needed:
  int index1 = msg.indexOf(',');
  int index2 = msg.indexOf(',', index1 + 1);
  int index3 = msg.indexOf(',', index2 + 1);

  if (index1 < 0 || index2 < 0 || index3 < 0) {
    Serial.println("ERR: Bad format");
    return;
  }

  // Extract parts
  String part1 = msg.substring(0, index1);
  String part2 = msg.substring(index1 + 1, index2);
  String part3 = msg.substring(index2 + 1, index3);
  String func  = msg.substring(index3 + 1);

  // Convert numbers
  float value1   = part1.toFloat();
  float value2   = part2.toFloat();
  float rot_time = part3.toFloat();

  // Debug print
  Serial.print("Parsed: ");
  Serial.print(value1); Serial.print(" | ");
  Serial.print(value2); Serial.print(" | ");
  Serial.print(rot_time); Serial.print(" | ");
  Serial.println(func);

  // Call functions depending on f0 / f1
  if (func == "f0") {
    if ((int)value1 == 0){// if it's the xy motor that has to turn
      test_motor(value2, rot_time, steps_per_revolution, DIR1, PU1); //float total_angle, float total_time, float subdivsion, int direction_pin, int pulse_pin
    }
    else{//the z motor has to turn
      test_motor(value2, rot_time, steps_per_revolution, DIR2, PU2);
    }
  }
  else if (func == "f1") {
    both_motors(value1, value2, rot_time, steps_per_revolution, steps_per_revolution); //both_motors(float xy_angle, float z_angle, float total_time, float xy_subdivsion, float z_subdivsion)
  }
  else {
    Serial.println("ERR: Unknown function");
  }
}
