/*
  Minimal code to send Somfy frames via the Serial (UART) port of the Arduino
  Uno board and to send pulse on the free GPIO pin of the Arduino Uno board.
*/
#include <Arduino.h>
#define debug(x) Serial.println(x)

const uint16_t SYMBOL = 640;

// Sortie pilotant l'émetteur à 433,42 MHz
// Output pin controlling the 433.42 MHz emitter
const uint8_t TX_PIN = 5;

String raw_command = "";
String processed_command = "";
byte frame[7];

// Liste des commandes des volets
// Blinds commands list
// enum command : uint8_t {
//  /*
//    0x1 | My | Stop or move to favourite position
//    0x2 | Up | Move up
//    0x3 | My + Up | Set upper motor limit in initial programming mode
//    0x4 | Down | Move down
//    0x5 | My + Down | Set lower motor limit in initial programming mode
//    0x6 | Up + Down | Change motor limit and initial programming mode
//    0x8 | Prog | Used for (de-)registering remotes, see below
//    0x9 | Sun + Flag | Enable sun and wind detector (SUN and FLAG symbol on
//    the Telis Soliris RC)
//    0xA | Flag | Disable sun detector (FLAG symbol on
//    the Telis Soliris RC)
//
//    Sources:
//    https://pushstack.wordpress.com/somfy-rts-protocol/
//    http://www.automatedshadeinc.com/files/motors/all-somfy-rts%20motors-programming-quick-guide-02-09.pdf
//  */
//  // My or stop
//  MY = 0x1,
//  // My or stop
//  STOP = 0x1,
//  // Up
//  UP = 0x2,
//  // Up
//  HAUT = 0x2,
//  // My and up (set upper motor limit in initial programming mode)
//  MY_UP = 0x3,
//  // Down
//  DOWN = 0x4,
//  // Down
//  BAS = 0x4,
//  // My and down (set lower motor limit in initial programming mode)
//  MY_DOWN = 0x5,
//  // Up and down (change motor limit and initial programming mode)
//  UP_DOWN = 0x6,
//  // Prog ((de-)registering remotes)
//  PROG = 0x8,
//  // Enable sun and wind detector
//  // (SUN and FLAG symbol on the Telis Soliris RC)
//  SUN_FLAG = 0x9,
//  // Disable sun detector (FLAG symbol on the Telis Soliris RC)
//  SUN_UNFLAG = 0xA
//};

byte char_to_byte(char char_byte);
byte two_char_to_byte(char MSB, char LSB);
void send_command(byte *frame, byte sync, uint8_t port_tx,
                  uint32_t symbol = SYMBOL);
void send_frame(byte *frame, uint8_t tx_pin);

void setup() {
  // Start Serial link|Démarrage de la liaison série
  Serial.begin(115200);
}

void loop() {
  if (Serial.available()) {
    // Read raw command
    raw_command = Serial.readStringUntil('\n');
    processed_command = raw_command;
    processed_command.replace(" ", "");
    processed_command.toUpperCase();
    // Check frame size --> Should be 7 bytes (14 char)

    uint8_t valid_command = 0;
    if (processed_command.startsWith("PULSE(") &&
        processed_command.endsWith(")")) {
      String command =
          processed_command.substring(6, processed_command.length() - 1);
      uint32_t pulse_arguments[2] = {
          (uint32_t)command.substring(0, command.indexOf(',')).toInt(),
          (uint32_t)command.substring(command.indexOf(',') + 1).toInt()};

      if (pulse_arguments[0] >= 2 && pulse_arguments[0] != TX_PIN &&
          pulse_arguments[0] <= 19) {
        Serial.println(raw_command);
        pinMode(pulse_arguments[0], OUTPUT);
        digitalWrite(pulse_arguments[0], LOW);
        digitalWrite(pulse_arguments[0], HIGH);
        delay(pulse_arguments[1]);
        digitalWrite(pulse_arguments[0], LOW);
      }
      valid_command = 2;
    }

    else if (processed_command.length() == 14) {
      for (uint8_t i(0); i < 14; i++) {
        if (char_to_byte(processed_command.charAt(i)) == 0xFF) {
          debug("Error the frame does not only contain HEX characters.");
        }
      }

      for (uint8_t i(0); i < 7; i++) {
        frame[i] = two_char_to_byte(processed_command.charAt(2 * i),
                                    processed_command.charAt(2 * i + 1));
      }
      valid_command = 1;
    }

    else {
      debug("Error the frame should have a length of 14 characters (7 bytes).");
    }

    switch (valid_command) {
    case 0: // Invalid instruction
      //        Serial.println("Wrong number of arguments!");
      Serial.println("Valid command is:");
      Serial.println("1 argument for:  send_raw_rts(hex frame)");
      break;

    // Send a RAW RTS frame
    // Envoyer une trame RTS brute
    case 1: // Send RAW command
      send_frame(frame, TX_PIN);
      debug(raw_command);
      break;

    // Send a pulse on a pin
    // Envoie un impulsion sur une pin
    case 2: // Pulse pin
      break;
    }
  }
}

byte char_to_byte(char char_byte) {
  if (char_byte == '0')
    return 0x0;
  else if (char_byte == '1')
    return 0x1;
  else if (char_byte == '2')
    return 0x2;
  else if (char_byte == '3')
    return 0x3;
  else if (char_byte == '4')
    return 0x4;
  else if (char_byte == '5')
    return 0x5;
  else if (char_byte == '6')
    return 0x6;
  else if (char_byte == '7')
    return 0x7;
  else if (char_byte == '8')
    return 0x8;
  else if (char_byte == '9')
    return 0x9;
  else if (char_byte == 'A')
    return 0xA;
  else if (char_byte == 'B')
    return 0xB;
  else if (char_byte == 'C')
    return 0xC;
  else if (char_byte == 'D')
    return 0xD;
  else if (char_byte == 'E')
    return 0xE;
  else if (char_byte == 'F')
    return 0xF;
  else
    return 0xFF;
}

byte two_char_to_byte(char MSB, char LSB) {
  return (char_to_byte(MSB) << 4) + char_to_byte(LSB);
}

void send_command(byte *frame, byte sync, uint8_t port_tx, uint32_t symbol) {
  // Signal de synchronisation
  // Synchronization signal
  if (sync == 2) {
    // Set port_tx pin to HIGH
    PORTD |= 1 << port_tx;
    delayMicroseconds(9415);
    // Set port_tx pin to LOW
    PORTD &= ~(1 << port_tx);
    delayMicroseconds(24030);
    delayMicroseconds(65535);
  }

  for (byte i = 0; i < sync; i++) {
    // Set port_tx pin to HIGH
    PORTD |= 1 << port_tx;
    delayMicroseconds(4 * symbol);
    // Set port_tx pin to LOW
    PORTD &= ~(1 << port_tx);
    delayMicroseconds(4 * symbol);
  }

  // Set port_tx pin to HIGH
  PORTD |= 1 << port_tx;
  delayMicroseconds(4550);
  // Set port_tx pin to LOW
  PORTD &= ~(1 << port_tx);
  delayMicroseconds(symbol);

  for (byte i = 0; i < 56; i++) {
    if (((frame[i / 8] >> (7 - (i % 8))) & 1) == 1) {
      // Set port_tx pin to LOW
      PORTD &= ~(1 << port_tx);
      delayMicroseconds(symbol);
      // Set port_tx pin to HIGH
      PORTD ^= 1 << port_tx;
      delayMicroseconds(symbol);
    }

    else {
      // Set port_tx pin to HIGH
      PORTD |= (1 << port_tx);
      delayMicroseconds(symbol);
      // Set port_tx pin to LOW
      PORTD ^= 1 << port_tx;
      delayMicroseconds(symbol);
    }
  }

  // Set port_tx pin to LOW
  PORTD &= ~(1 << port_tx);
  delayMicroseconds(30415);
}

void send_frame(byte *frame, uint8_t tx_pin) {
  // Configure the port|Configuration du port
  DDRD = DDRD | (1 << TX_PIN);

  send_command(frame, 2, tx_pin);

  for (uint8_t i = 0; i < 2; i++) {
    send_command(frame, 7, tx_pin);
  }
}
