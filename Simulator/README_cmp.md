# [ICD] 반도체 CMP 장비 통합 인터페이스 통제 문서

**문서 버전:** 1.0
**작성일:** 2026-07-08
**대상 시스템:** MCU-FPGA 기반 반도체 CMP 장비 제어 시스템

---

## 1. 시스템 인터페이스 아키텍처 및 통신 프로토콜

CMP 장비 내/외부의 주요 장치들은 각각의 요구 응답성과 신뢰성 기준에 따라 다음과 같은 프로토콜로 연결됩니다.

| 연결 구간 | 장치 명칭 | 물리 계층 (Physical Layer) | 통신 프로토콜 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **PC $\leftrightarrow$ MCU** | 상위 UI 및 Host | 100/1000Base-T Ethernet | TCP/IP, UDP | 레시피 제어(TCP), <br>고속 센서 파형 전송(UDP) |
| **MCU $\leftrightarrow$ FPGA** | 제어기 내부 브리지 | 16-bit Asynchronous SRAM | Memory-Mapped I/O | 내부 버스 <br>(AHB/APB 브리지 연동) |
| **MCU $\leftrightarrow$ Motor** | Carrier, Platen 모터 | RS-485 (Isolated) 또는 CAN | Modbus RTU / CANopen | 속도(RPM) 및 <br>위치 정밀 제어 (10ms 주기) |
| **MCU $\leftrightarrow$ MFC** | Slurry 유량 및 압력 밸브 | RS-485 | Modbus RTU | 설정 유량 및 <br>현재 유량 피드백 |
| **FPGA $\leftrightarrow$ Sensor** | 광학 / Eddy 센서 | 고속 아날로그 신호 선 | High-speed ADC (SPI/Parallel) | Raw 신호 취득 후 <br>FPGA 내부 <br>DSP(FIR/IIR) 처리 |
| **FPGA $\leftrightarrow$ Safety** | Interlock / EMO | 24V Digital I/O | 하드웨어 릴레이 접점 | 비상 정지 시 즉각적인 <br>하드웨어 출력 차단 |

---

## 2. 전기적 사양 (Electrical Specifications)

각 인터페이스 노드의 안정적인 신호 전달을 위한 전기적 레벨 및 타이밍 제약 조건입니다.

### 2.1. MCU-FPGA 메모리 버스 (SRAM Interface)
*   **I/O 전압 레벨:** 3.3V LVCMOS (또는 고속 구동 시 1.8V LVCMOS)
*   **최대 구동 주파수:** 50 MHz 이하 (비동기식 기준)
*   **Setup/Hold 타임:** 
    *   Data Setup Time ($T_{setup}$): 최소 5ns
    *   Data Hold Time ($T_{hold}$): 최소 3ns
*   **임피던스 매칭:** 신호 무결성을 위해 어드레스 및 데이터 라인에 직렬 종단 저항(22~33옴) 적용 권장.

### 2.2. 모터 및 밸브 통신 (RS-485 / CAN)
*   **트랜시버 전압:** 5V (내부 로직은 3.3V, 절연형 트랜시버 사용 필수)
*   **절연(Isolation):** 포토커플러 또는 디지털 아이솔레이터를 통한 2.5kV 이상 갈바닉 절연 (모터 노이즈 유입 방지).
*   **종단 저항:** RS-485 및 CAN 버스 양 끝단에 120옴 저항 실장.

### 2.3. 센서 및 I/O (Analog / Digital)
*   **ADC 입력 허용 전압:** 0 ~ 3.3V (Op-Amp 버퍼를 통한 임피던스 매칭 및 Anti-aliasing 필터 적용)
*   **디지털 I/O 전압:** 공장 자동화 표준인 24V 로직 사용 (포토커플러를 통해 3.3V 로직으로 변환).

---

## 3. MCU-FPGA 물리적 핀 맵 (Pin-out Description)

MCU의 외부 메모리 컨트롤러(FMC/FSMC)와 FPGA 간의 하드웨어 핀 연결 정의입니다.

| 신호명 | 방향 (MCU 관점) | 핀 폭 | 전기적 특성 | 설명 |
| :--- | :---: | :---: | :--- | :--- |
| `ADDR[15:0]` | Output | 16 | 3.3V LVCMOS | 16-bit 주소 버스 (최대 64KB 공간) |
| `DATA[15:0]` | In/Out | 16 | 3.3V LVCMOS | 16-bit 양방향 데이터 버스 |
| `nCS` | Output | 1 | 3.3V LVCMOS | Chip Select (Active Low) |
| `nWE` | Output | 1 | 3.3V LVCMOS | Write Enable (Active Low) |
| `nOE` | Output | 1 | 3.3V LVCMOS | Read Enable / Output Enable (Active Low) |
| `IRQ_EPD` | Input | 1 | 3.3V LVCMOS | End-Point Detection 하드웨어 인터럽트 (FPGA $\rightarrow$ MCU) |

---

## 4. 내부 버스 브리지 및 메모리 맵핑 (Memory Map)

FPGA 내부에 구현된 SRAM to AHB/APB 브리지를 통해 할당된 레지스터 주소입니다. (Base Address: 시스템 설계에 따라 MCU 측에서 지정, 예: `0x6000_0000`)

### 4.1. APB 버스 영역 (저속 구동 및 설정 레지스터)

| 어드레스 (Offset) | 레지스터 명칭 | R/W | Data 크기 | 설명 |
| :--- | :--- | :---: | :---: | :--- |
| **[Carrier 제어]** |
| `0x0000` | `CARRIER_CTRL` | R/W | 16-bit | Bit[0]: 모터 On/Off, Bit[1]: 방향 (0:CW, 1:CCW) |
| `0x0002` | `CARRIER_RPM` | R/W | 16-bit | 목표 회전 속도 (0 ~ 150 RPM) |
| `0x0004` | `CARRIER_PRS` | R/W | 16-bit | 헤드 누름 압력 지령값 (단위: 0.1 PSI) |
| **[Platen 제어]** |
| `0x0010` | `PLATEN_CTRL` | R/W | 16-bit | Platen 구동 제어 상태 |
| `0x0012` | `PLATEN_RPM` | R/W | 16-bit | Platen 목표 회전 속도 (0 ~ 300 RPM) |
| **[센서 설정]** |
| `0x0100` | `FIR_COEF_UP` | R/W | 16-bit | 하드웨어 FIR 필터 계수 업데이트 포트 |
| `0x0110` | `EDDY_CALIB` | R/W | 16-bit | Eddy 센서 영점 오프셋(Calibration) |

### 4.2. AHB 버스 영역 (고속 센서 데이터 버퍼)

| 어드레스 (Offset) | 레지스터 명칭 | R/W | Data 크기 | 설명 |
| :--- | :--- | :---: | :---: | :--- |
| `0x1000` | `FIFO_STATUS` | R | 16-bit | 센서 FIFO 상태 (Bit[0]: Empty, Bit[15:8]: 읽기 가능한 데이터 수) |
| `0x1004` | `OPTICAL_DATA` | R | 16-bit | 광학 센서 두께 데이터 (읽을 시 FIFO 팝 수행) |
| `0x1008` | `EDDY_DATA` | R | 16-bit | Eddy 센서 두께 데이터 (읽을 시 FIFO 팝 수행) |
| `0x100C` | `EPD_TARGET` | R/W | 16-bit | End-Point Detection 목표 임계값 설정 |

---

## 5. 데이터 처리 및 제어 시퀀스

1.  **제어 지령 전송 (MCU $\rightarrow$ Motor/Valve):** MCU는 APB 레지스터 구역(`0x0000` ~ `0x0020`)에 RPM 및 압력 값을 Write합니다. MCU 내부의 Modbus/CAN 드라이버가 이 값을 폴링하여 실제 모터/MFC로 물리 계층(RS-485/CAN)을 통해 패킷을 전송합니다.
2.  **센서 데이터 수집 (FPGA $\rightarrow$ MCU):** FPGA는 ADC를 통해 수집된 센서 데이터를 하드웨어 필터링 후 내부 FIFO에 적재합니다. FIFO에 데이터가 일정 수준 채워지면 `FIFO_STATUS` 레지스터가 업데이트되며, MCU는 DMA 또는 폴링 방식으로 `OPTICAL_DATA`(`0x1004`)를 연속적으로 Read하여 UI PC로 UDP 스트리밍을 수행합니다.
3.  **End-Point Detection:** FPGA 내부 로직이 필터링된 두께 데이터와 `EPD_TARGET`(`0x100C`) 값을 실시간 비교합니다. 타겟 도달 시 즉각 `IRQ_EPD` 핀을 Active하여 MCU에 공정 종료를 알립니다.
