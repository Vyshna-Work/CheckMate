# CheckMate
Project Innovate - Group Project
--------------------------------------------------------------------------------------------------------------------------------------------------
CheckMate — Smart Attendance Monitoring System
Project Status

🚧 This project is currently in the design and prototyping phase.
Software and hardware architecture have been completed, and implementation will begin in the next phase.

Prototype designs, schematics, and technical design documents are included in the project documentation.

--------------------------------------------------------------------------------------------------------------------------------------------------

Project Overview

CheckMate is a Smart Attendance Monitoring System designed to automate attendance tracking in educational environments. Traditional attendance methods such as roll calls and paper-based systems are time-consuming, inefficient, and prone to manipulation. This project proposes a hybrid system that combines a mobile application (BLE-based detection) with an NFC card backup system to create a reliable, automated attendance solution.

The system automatically detects when a student enters a classroom, records attendance in real time, and provides instant feedback through a display and audio system. The solution integrates embedded hardware, mobile software, and a database system to create a scalable and intelligent attendance platform.

---------------------------------------------------------------------------------------------------------------------------------------------------
Problem Statement

Current attendance systems face several major issues:

Manual attendance takes valuable class time
Human errors in marking attendance
Proxy attendance (students marking for others)
No real-time attendance analytics
Lack of automation in most systems

CheckMate aims to solve these problems through automation, secure identification, and real-time data processing.

--------------------------------------------------------------------------------------------------------------------------------------------------
Project Objectives

Develop a mobile application for automatic attendance detection
Implement real-time attendance recording
Design a hardware-based NFC backup system
Provide instant feedback via LCD and audio
Track student punctuality and time spent in class
Reduce proxy attendance and data manipulation
Create a user-friendly and interactive system

--------------------------------------------------------------------------------------------------------------------------------------------------
System Overview

How the System Works
Student enters the classroom
Mobile app broadcasts BLE identifier
Raspberry Pi detects the BLE signal
System verifies identity in database
Attendance is recorded automatically
LCD displays confirmation
Speaker plays audio feedback
If BLE fails → student taps NFC card
Attendance recorded via NFC backup

--------------------------------------------------------------------------------------------------------------------------------------------------

Key Features

Mobile Application :

Automatic attendance detection
Secure login system
Real-time data synchronization
Attendance history view

Hardware System :

NFC reader (backup check-in)
LCD display
Speaker for voice feedback
LED status indicators
Push-button menu interface

Smart Feedback System :

Voice greetings
Visual confirmation
LED status indicators
Late/on-time notifications

Attendance Tracking : 

Entry time recording
Late arrival tracking
Attendance history
Semester reports
Real-time dashboard

--------------------------------------------------------------------------------------------------------------------------------------------------
User Stories

The system is designed based on the following core user requirements:

ID	User Story	Priority :

US-01	Card-based attendance registration	High
US-02	App-based attendance registration	High
US-03	Late arrival tracking	High
US-05	Real-time dashboard	High
US-08	Fast identification (<3 sec)	High
US-09	Duplicate check-in prevention	High
US-04	Personal attendance history	Medium
US-06	Semester attendance report	Medium
US-10	Offline mode & data sync	Medium
US-07	Manual attendance correction	Low

These user stories define the functional requirements and system behaviour.

--------------------------------------------------------------------------------------------------------------------------------------------------
System Architecture

Software Components :
 
BLE Scanner Module
NFC Reader Module
Attendance Manager
LCD UI Controller
Audio Controller
REST API Server (Flask)
SQLite Database
Mobile Application (Android/iOS)

Hardware Components :

Raspberry Pi 4 Model B (central controller)
PN532 NFC Reader
20×4 LCD Display (I2C)
Speaker + Amplifier
LED Indicators
Push Buttons
Power Supply
Perfboard (final build)
3D Printed Casing

--------------------------------------------------------------------------------------------------------------------------------------------------
Technology Stack

Category	                            Technology

Embedded System	                      Raspberry Pi 4
Programming Language	                Python
Mobile App	                          Android & iOS
Communication	                        Bluetooth Low Energy (BLE), NFC
API	                                  Flask REST API
Database	                            SQLite
Hardware Interface	                  GPIO, I2C
Audio	                                PWM / I2S
Prototyping	                          Breadboard → Perfboard
Enclosure	                            3D Printed PLA Case

--------------------------------------------------------------------------------------------------------------------------------------------------
Testing and Validation

The system will be tested using:

Functional Testing (BLE, NFC, database logging)
Integration Testing (communication between modules)
Performance Testing (multiple students entering at once)
Validation Testing (compare with manual attendance)
Reliability Testing (low battery, Bluetooth off, no internet)
Security Testing (prevent duplicate or fake check-ins)

--------------------------------------------------------------------------------------------------------------------------------------------------
Risk Assessment

Risk	                                 Mitigation

BLE detection failure	                 NFC backup system
App not working in background	         Device compatibility testing
Incorrect attendance	                 Duplicate prevention + validation
Privacy/security issues	               Secure database + unique UUID
Integration issues	                   Test modules individually
Project delays	                       Milestones and phased development
Backup failure	                       Early backup testingRisk Assessment

--------------------------------------------------------------------------------------------------------------------------------------------------
Future Improvements

Face recognition integration
Web dashboard for lecturers
Cloud database
Multi-classroom support
iOS full support
Analytics and attendance prediction

--------------------------------------------------------------------------------------------------------------------------------------------------
Team

Name	                                Role
Slman & Aisha	                        Software
Vyshna & Ondrej                       Hardware
Sana & Sjonly                         Mobile App
Whole Team                            Documentation

--------------------------------------------------------------------------------------------------------------------------------------------------
Conclusion

CheckMate aims to modernize attendance systems by combining BLE-based automatic detection with an NFC backup system to ensure reliability. By integrating embedded hardware, mobile software, and a real-time database, the system provides a fast, secure, and scalable solution for educational institutions.

--------------------------------------------------------------------------------------------------------------------------------------------------
Acknowledgements

This project was developed as part of an academic engineering project. Prototype designs, schematics and all the explained information are included in the technical design.

--------------------------------------------------------------------------------------------------------------------------------------------------




