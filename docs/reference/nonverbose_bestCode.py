import pygame
import os
import minimalmodbus
import serial
import time
import math
import atexit
import signal
import sys

#Statische WERTE
Winkel = int(450) #DEG
WinkelZurück = int(-450)
JogWinkel = int(25) #DEG
JogWinkelZurück = int(-25)
Drehzahl = int(1000) #RPM
DrehzahlJog = int(750) #RPM
AccelerationTime = int(1) #ms
DecelerationTime = int(1) #ms
JogAccelerationTime = int(5) #ms
JogDecelerationTime = int(5) #ms
WaitingTimeBetweenMovements = int(5) #0,5s

#Getriebe
Nenner = int(16384)
Zähler = int(9)

#Register
#Servo Status
REGISTER_SERVO_STATUS = 0x410A
#Belegbare Schalter
REGISTER_DI6 = 0x0414 #DI6
REGISTER_DI6_NONC = 0x0415 #Normaly Open
REGISTER_DI6_FILTER_TIME = 0x416
REGISTER_DI7 = 0x0418 #DI7
REGISTER_DI7_NONC = 0x0419 #Normaly Open
REGISTER_DI7_FILTER_TIME = 0x41A
#Controll
REGISTER_CONTROL_MODE = 0x0000
REGISTER_S_ON_NONC = 0x0411 #Normlay Open di5
REGISTER_FAULT_RESET_NONC = 0x040D #DI4 NONC
#MISC
REGISTER_SPEED_FEEDBACK = 0x4001
REGISTER_TOURQUE_FEEDBACK = 0x4003
REGISTER_BUS_VOLTAGE = 0x4006
REGISTER_PANEL_DISPLAY = 0x0016
REGISTER_MOTOR_TEMPERATURE = 0x4031
REGISTER_ENCODER_TEMPERATURE = 0x4032



#PosGear
REGISTER_POSITION_REFERENCE_SELECTION = 0x0300
REGISTER_NUMERATOR_OF_GROUP_1_ELECTRIC_GEAR_RATIO = 0x0302
REGISTER_DENOMINATOR_OF_GROUP_1_ELECTRIC_GEAR_RATIO = 0x0304
REGISTER_NUMERATOR_OF_GROUP_2_ELECTRIC_GEAR_RATIO = 0x0306
REGISTER_DENOMINATOR_OF_GROUP_2_ELECTRIC_GEAR_RATIO = 0x0308
#Gear
REGISTER_NUMERATOR_OF_ELETRONIC_GEAR_RATIO_IN_ROTATION_MODE = 0x1018
REGISTER_DENOMINATOR_OF_ELETRONIC_GEAR_RATIO_IN_ROTATION_MODE = 0x1019

#PosPlanung für Gruppen
REGISTER_POSITION_PLANING_MODE_SELECTION = 0x1100
REGISTER_POSITION_PLANING_REFERENCE_TYPE = 0x1101
REGISTER_POSITION_PLANING_REFERENCE_UPDATE_MODE = 0x1102
REGISTER_POSITION_PLANING_INITIAL_GROUP_NUMBER = 0x1103
REGISTER_POSITION_PLANING_END_GROUP_NUMBER = 0x1104
REGISTER_PROCESSING_OF_POSITION_PLANING_REMAINING_SEGMENTS = 0x1105
#1 Hin
REGISTER_GROUP_1_DISPLACEMENT = 0x1106 
REGISTER_GROUP_1_SPEED = 0x1108
REGISTER_GROUP_1_ACCELER11ATION_TIME = 0x110A
REGISTER_GROUP_1_DEACCELERATION_TIME = 0x110C
REGISTER_GROUP_1_WAITING_TIME = 0x110E
#2 Zurück
REGISTER_GROUP_2_DISPLACEMENT = 0x1110 
REGISTER_GROUP_2_SPEED = 0x1112
REGISTER_GROUP_2_ACCELERATION_TIME = 0x1114
REGISTER_GROUP_2_DEACCELERATION_TIME = 0x1116
REGISTER_GROUP_2_WAITING_TIME = 0x1118
#3 Jog Vor TBD
REGISTER_GROUP_3_DISPLACEMENT = 0x1120 
REGISTER_GROUP_3_SPEED = 0x1122
REGISTER_GROUP_3_ACCELERATION_TIME = 0x1124
REGISTER_GROUP_3_DEACCELERATION_TIME = 0x1126
REGISTER_GROUP_3_WAITING_TIME = 0x1128
#Jog Zurück TBD
REGISTER_GROUP_4_DISPLACEMENT = 0x1130 
REGISTER_GROUP_4_SPEED = 0x1132
REGISTER_GROUP_4_ACCELERATION_TIME = 0x1134
REGISTER_GROUP_4_DEACCELERATION_TIME = 0x1136
REGISTER_GROUP_4_WAITING_TIME = 0x1138

#Unterfunktionen:
def ClosePort():
    if servo.serial.is_open:
        servo.serial.close() 
#Text
def Hauptmenü():  
    #Motor Status
    print(" Y=Reset X=Quit A=Go B=Stop LB=JogDown RB=JogUp ", end='\r')
#Funktionen der Tasten / Maschine
def movebackwards():
    time.sleep(1)
    servo.write_register(REGISTER_S_ON_NONC, 0, functioncode=6) #Motor aus
    os.system('cls')        
    print("Fahre Zurück")
    time.sleep(0.5)
    servo.write_register(REGISTER_POSITION_PLANING_INITIAL_GROUP_NUMBER, 3, functioncode=6)
    servo.write_register(REGISTER_POSITION_PLANING_END_GROUP_NUMBER, 3 , functioncode=6)    
#group3 
    servo.write_register(REGISTER_GROUP_3_SPEED, DrehzahlJog, functioncode=6, signed=False)
    servo.write_long(REGISTER_GROUP_3_ACCELERATION_TIME, JogAccelerationTime, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_3_DEACCELERATION_TIME, JogDecelerationTime, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_3_WAITING_TIME, WaitingTimeBetweenMovements, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_3_DISPLACEMENT, JogWinkelZurück, signed=True, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    #starten der bewegung
    servo.write_register(REGISTER_DI6_NONC, 0, functioncode=6) #DI6  
    servo.write_register(REGISTER_DI6, 19 , functioncode=6) #DI6 mit Funktion 19 besetzen
    servo.write_register(REGISTER_S_ON_NONC, 1, functioncode=6) #Motor An
    time.sleep(2) #nach motorstart 2 sec Warten
    servo.write_register(REGISTER_DI6_NONC, 1, functioncode=6) #DI6 auf High setzen
    os.system('cls')  
def movevorwarts():
    servo.write_register(REGISTER_S_ON_NONC, 0, functioncode=6) #Motor aus
    os.system('cls')    
    print("Fahre vor")
    time.sleep(0.1)
    servo.write_register(REGISTER_POSITION_PLANING_INITIAL_GROUP_NUMBER, 4, functioncode=6)
    servo.write_register(REGISTER_POSITION_PLANING_END_GROUP_NUMBER, 4 , functioncode=6)    
#group4 
    servo.write_register(REGISTER_GROUP_4_SPEED, DrehzahlJog, functioncode=6, signed=False)
    servo.write_long(REGISTER_GROUP_4_ACCELERATION_TIME, JogAccelerationTime, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_4_DEACCELERATION_TIME, JogDecelerationTime, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_4_WAITING_TIME, WaitingTimeBetweenMovements, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_4_DISPLACEMENT, JogWinkel, signed=True, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    #starten der bewegung
    servo.write_register(REGISTER_DI6_NONC, 0, functioncode=6) #DI6  
    servo.write_register(REGISTER_DI6, 19 , functioncode=6) #DI6 mit Funktion 19 besetzen
    servo.write_register(REGISTER_S_ON_NONC, 1, functioncode=6) #Motor An
    time.sleep(2) #nach motorstart 2 sec Warten
    servo.write_register(REGISTER_DI6_NONC, 1, functioncode=6) #DI6 auf High setzen
    os.system('cls')  
def MaschineHerunterfahren():
    os.system('cls')  
    print("Beenden")
    time.sleep(1)
    pygame.quit()
    servo.write_register(REGISTER_S_ON_NONC, 0, functioncode=6, signed=False) #DI5 auf LOW setzen
    servo.serial.close()
    exit(0)
def ZyklusStarten():
    os.system('cls')    
    print("los")
    #set
    servo.write_register(REGISTER_S_ON_NONC, 0, functioncode=6) #Motor aus
    time.sleep(0.1)
    servo.write_register(REGISTER_POSITION_PLANING_INITIAL_GROUP_NUMBER, 1, functioncode=6)
    servo.write_register(REGISTER_POSITION_PLANING_END_GROUP_NUMBER, 2 , functioncode=6)    
    #group1
    servo.write_register(REGISTER_GROUP_1_SPEED, Drehzahl, functioncode=6, signed=False)
    servo.write_long(REGISTER_GROUP_1_ACCELER11ATION_TIME, AccelerationTime, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_1_DEACCELERATION_TIME, DecelerationTime, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_1_WAITING_TIME, WaitingTimeBetweenMovements, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_1_DISPLACEMENT, Winkel*-1, signed=True, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    #group2
    servo.write_register(REGISTER_GROUP_2_SPEED, Drehzahl, functioncode=6, signed=False)
    servo.write_long(REGISTER_GROUP_2_ACCELERATION_TIME, AccelerationTime, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_2_DEACCELERATION_TIME, DecelerationTime, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_2_DISPLACEMENT, Winkel, signed=True, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    servo.write_long(REGISTER_GROUP_2_WAITING_TIME, WaitingTimeBetweenMovements, number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE)
    #starten der bewegung
    servo.write_register(REGISTER_DI6_NONC, 0, functioncode=6) #DI6  
    servo.write_register(REGISTER_DI6, 19 , functioncode=6) #DI6 mit Funktion 19 besetzen
    servo.write_register(REGISTER_S_ON_NONC, 1, functioncode=6) #Motor An
    time.sleep(2) #nach motorstart 2 sec Warten
    servo.write_register(REGISTER_DI6_NONC, 1, functioncode=6) #DI6 auf High setzen
    os.system('cls')  
def ZyklusUnterbrechen():
    os.system('cls')    
    print("halt")
    servo.write_register(REGISTER_DI7_NONC, 1, functioncode=6) #DI7 auf High setzen
    time.sleep(0.5)
    os.system('cls')  
def MotorReset():
    os.system('cls')
    print("Reset")
    time.sleep(1)
    servo.write_register(REGISTER_S_ON_NONC, 0, functioncode=6, signed=False) #DI5 auf LOW setzen #maschine aus falls an 
    time.sleep(1)
    servo.write_register(REGISTER_FAULT_RESET_NONC, 1, functioncode=6, signed=False)
    servo.write_register(REGISTER_FAULT_RESET_NONC, 0, functioncode=6, signed=False)
    servo.write_register(REGISTER_CONTROL_MODE, 0, functioncode=6)
    os.system('cls')

#Hauptprogramm
#XBOX Controler Check
pygame.init()
pygame.joystick.init()
while pygame.joystick.get_count() == 0: #exception: "Kein Controller Verbunden"
    print("Kein XBox Controller gefunden, Bitte Verbinden", end='\r')
    pygame.quit()
    pygame.joystick.init()
else:
    os.system('cls')
    print("Controller Verbunden")
    time.sleep(0.5)
controller = pygame.joystick.Joystick(0)
controller.init()
running = True 
#ModbusInit

atexit.register(ClosePort) 


try: 

    servo = minimalmodbus.Instrument('COM12', 1) #com port
    servo.serial.baudrate = 9600 
    servo.serial.bytesize = 8
    servo.serial.parity = minimalmodbus.serial.PARITY_NONE
    servo.serial.stopbits = 1
    servo.serial.timeout = 1 #1 sekunde timeout
    servo.mode = minimalmodbus.MODE_RTU

    MotorReset()
    #init
    os.system('cls')
    #Getriebe Setzen (Electronic Gear Ratio)
    servo.write_long(REGISTER_NUMERATOR_OF_GROUP_1_ELECTRIC_GEAR_RATIO, Zähler , number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE) #C03.02
    servo.write_long(REGISTER_DENOMINATOR_OF_GROUP_1_ELECTRIC_GEAR_RATIO, Nenner , number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE ) #C03.04
    servo.write_long(REGISTER_NUMERATOR_OF_GROUP_2_ELECTRIC_GEAR_RATIO, Zähler , number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE) #C03.06
    servo.write_long(REGISTER_DENOMINATOR_OF_GROUP_2_ELECTRIC_GEAR_RATIO, Nenner , number_of_registers=2, byteorder=minimalmodbus.BYTEORDER_LITTLE ) #C03.08
    #modus setzen
    servo.write_register(REGISTER_POSITION_REFERENCE_SELECTION, 1, functioncode=6)

    servo.write_register(REGISTER_POSITION_PLANING_MODE_SELECTION, 0, functioncode=6)
    servo.write_register(REGISTER_POSITION_PLANING_REFERENCE_TYPE, 1, functioncode=6)
    servo.write_register(REGISTER_POSITION_PLANING_REFERENCE_UPDATE_MODE, 0, functioncode=6)
    servo.write_register(REGISTER_DI6_NONC, 0, functioncode=6) #DI6  auf 0 
    servo.write_register(REGISTER_DI7_NONC, 0, functioncode=6) #di7 auf 0
    servo.write_register(REGISTER_DI6, 19 , functioncode=6) #DI6 mit Funktion 19 (Position Planning Trigger) besetzen 
    servo.write_register(REGISTER_DI7, 20 , functioncode=6) #DI7 mit Funktion 20 (Position Planning Pause) besetzen
    while running:#Hauptloop
        Hauptmenü()
        pygame.event.pump()
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 4:
                        movebackwards()
                        Hauptmenü()
                    if event.button == 5:
                        movevorewarts()
                        Hauptmenü()
                    if event.button == 3:
                        MotorReset()
                        Hauptmenü()
                    if event.button == 2:
                        MaschineHerunterfahren()
                    if event.button == 0:
                        ZyklusStarten()
                        Hauptmenü()                    
                    if event.button == 1:
                        ZyklusUnterbrechen()
                        Hauptmenü()   

finally:
        servo.serial.close()