# AESA Radar Test System ICD

---

# AESA Radar Test System
# Interface Control Document (ICD)

* Version 1.0

## 1. Document Information

* Item	Description
* Project	AESA Radar Test System
* Version	1.0
* Author	
* Date	
* HW Version	
* FPGA Version	
* FW Version	
* SW Version	

## 2. System Architecture
```
                Windows GUI
                      │
                TCP/IP Ethernet
                      │
        ┌──────────────────────────┐
        │ Embedded Controller      │
        │ (Linux / RTOS)           │
        └──────────────────────────┘
              │
     ┌────────┼────────┐
     │        │        │
 FPGA Board  Power    Motion
     │        │
     │
 Beamforming FPGA
     │
300 TR Modules
```

## 3. Communication Interface

* Physical Interface
* Interface	Protocol
* Ethernet	Gigabit Ethernet
* USB	USB3.0
* UART	Debug
* CAN	Optional
* SPI	FPGA Interface
* I2C	Sensor
* GPIO	Trigger

## 4. Communication Protocol

* 추천
* GUI ↔ Controller
* TCP/IP
* Message
* JSON
* 또는
* Google Protocol Buffer

* 예)
```
GUI
    |
TCP
    |
Embedded Linux
    |
Shared Memory
    |
FPGA Driver
```

Controller ↔ FPGA

권장 : DMA / PCIe / 또는 / AXI Bus

* Packet Example
```
Header

Message ID

Length

Payload

CRC
```

* Power Board

* 권장 CANOpen 또는 Modbus TCP
* 예)
```
24V

12V

5V

3.3V

Current

Temperature

Power Status
```

* TR Module

* SPI 또는 LVDS

* Packet
```
Module ID

Gain

Phase

Temperature

Power

Fault

ADC

RSSI
```

## 5. Software Protocol

* Command
```
CMD_SET_GAIN

CMD_SET_PHASE

CMD_SET_POWER

CMD_READ_STATUS

CMD_START_SCAN

CMD_STOP_SCAN

CMD_CALIBRATION

CMD_RESET
```

* Response
```
ACK

NACK

ERROR

BUSY

COMPLETE
```

* 6. Data Packet

* Example

```
Header      2 byte

Version     1 byte

Message ID  2 byte

Length      2 byte

Payload

CRC16
```

* Payload
```
Beam Angle

Azimuth

Elevation

Frequency

Power

Phase

Gain
```

## 7. Alarm Definition

* Code	Description
* 1001	24V Low
* 1002	12V Low
* 1003	Temperature High
* 1004	TR Failure
* 1005	PLL Unlock
* 1006	ADC Error
* 1007	Beamforming Error

## 8. Status Message

* Example
```
{
  "Power":{

      "24V":"OK",

      "12V":"OK",

      "5V":"OK",

      "3.3V":"OK"

  },

 "TRModule":{

      "ID":124,

      "Temperature":42,

      "Gain":31,

      "Phase":120,

      "Status":"OK"

 }

}
```

## 9. Beamforming Command

```
CMD_BEAM

Azimuth

Elevation

Frequency

Power

Pattern

Tracking

Apply
```

10. ICD Timing

GUI

100ms

↓

Controller

↓

FPGA

↓

TR Module

↓

Response

100ms 이하

11. Logging

모든 Command

모든 Alarm

Power History

Temperature History

Beamforming History

CSV

SQLite

12. Recommended Standards

이 부분이 가장 중요합니다.

항목	권장 표준
ICD 작성	IEEE 1016 Software Design Description(SDD)
Requirement	ISO/IEC/IEEE 29148
Software Architecture	ISO/IEC/IEEE 42010
Interface	IEEE 610
Ethernet	IEEE 802.3
Time Sync	IEEE 1588 (PTP)
CAN	CAN 2.0B / CANopen
Modbus	Modbus TCP
OPC	OPC UA (장비 연동 시)
API	REST + JSON 또는 gRPC + Protocol Buffers
Binary Protocol	TLV(Type-Length-Value)
Logging	Syslog + SQLite
CRC	CRC16 또는 CRC32
실제 방산 장비에서는 이렇게 구성하는 것이 일반적입니다.
                GUI
           Qt / C# / WPF
                  │
            gRPC 또는 TCP/IP
                  │
        Embedded Linux Controller
                  │
       ┌──────────┴──────────┐
       │                     │
    FPGA Driver          Power Board
       │                     │
    PCIe/AXI             CANopen
       │
 Beamforming FPGA
       │
   SPI/LVDS Daisy Chain
       │
  300 TR Modules


이 폴더는 ICD 문서 모음입니다.

1. 프로젝트 개요
2. 시스템 아키텍처
3. 하드웨어 구성도
4. Software Architecture
5. UI Architecture
6. FPGA Interface
7. Power Board Interface
8. T/R Module Interface
9. Beamforming Interface
10. Calibration Interface
11. Built-In Test(BIT)
12. Self Test Procedure
13. Fault Management
14. Alarm Code 정의
15. Packet Protocol
16. Binary Packet Format
17. JSON Debug Protocol
18. gRPC API
19. CANopen Object Dictionary
20. Modbus Register Map
21. FPGA Register Map
22. Timing Diagram
23. Sequence Diagram
24. State Machine
25. Database Schema(SQLite)
26. Logging Format
27. Configuration File
28. Recipe Format
29. User Permission
30. Cyber Security
31. Software Update
32. Network Configuration
33. Performance Requirements
34. Error Recovery
35. Maintenance Procedure
36. Test Case
37. Acceptance Test Procedure
38. Appendix

* 또한 각 장에는 다음과 같은 UML/SysML 다이어그램을 포함할 수 있습니다.

1. System Context Diagram
2. Block Definition Diagram(BDD)
3. Internal Block Diagram(IBD)
4. Sequence Diagram
5. Activity Diagram
6. State Machine Diagram
7. Deployment Diagram
8. Data Flow Diagram
9. Network Topology
10. Timing Diagram
11. Register Map
12. Packet Structure
