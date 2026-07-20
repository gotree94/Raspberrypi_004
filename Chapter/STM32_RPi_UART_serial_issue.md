# STM32F103 NUCLEO ↔ Raspberry Pi4 UART 통신 문제 해결 가이드

## 1. 개요

| 항목 | 내용 |
|---|---|
| STM32 보드 | NUCLEO-F103RB (STM32F103CBT6) |
| STM32 통신 포트 | USART2 (PA2 = TX, PA3 = RX) |
| Raspberry Pi | Raspberry Pi 4 |
| RPi 통신 포트 | `/dev/ttyAMA0` |
| 증상 | STM32 → RPi 상태 데이터 수신은 정상, RPi → STM32 명령 전송이 반응 없음 |

---

## 2. 문제 현상

- STM32F103이 주기적으로 보내는 **상태 데이터는 라즈베리파이에서 정상적으로 수신**됨
- 라즈베리파이에서 STM32F103으로 **명령을 전송해도 STM32가 반응하지 않음**
- 즉, **STM32 → RPi 방향은 정상, RPi → STM32 방향만 통신 불가**

---

## 3. 원인 분석

### 3.1 회로 구조

NUCLEO 보드는 온보드 ST-LINK MCU를 통해 USB-CDC(가상 COM 포트, VCP) 기능을 제공하며, 이 ST-LINK가 타겟 MCU의 **USART2 (PA2/PA3)** 라인에 TTL 레벨로 직접 연결되어 있습니다. 이 연결은 보드의 **SB13, SB14 솔더 브릿지(Solder Bridge)** 를 통해 이루어지며, 기본 상태(공장 출하 상태)는 **닫힘(short)** 입니다.

```
[ST-LINK MCU] --STLK_TX/STLK_RX--(SB13, SB14)--> [PA2/PA3, Target STM32F103]
```

### 3.2 충돌(Bus Contention) 지점

사용자가 라즈베리파이 GPIO(UART, `/dev/ttyAMA0`)를 STM32의 PA2/PA3에 **직접 배선**하면서, 아래와 같이 한 라인에 두 개의 송신 드라이버가 동시에 물리는 상황이 발생했습니다.

| STM32 핀 | 역할 | 연결된 장치 | 상태 |
|---|---|---|---|
| PA2 (USART2_TX) | STM32 송신 | RPi RXD, ST-LINK RX | 정상 (단방향 구동, 충돌 없음) |
| PA3 (USART2_RX) | STM32 수신 | RPi TXD **+** ST-LINK TX | **충돌 발생 지점** |

- **PA2 라인**: STM32가 유일한 드라이버이고, RPi와 ST-LINK는 둘 다 "듣기만" 하는 입장이므로 문제가 없습니다. → 상태 데이터 수신 정상과 일치
- **PA3 라인**: RPi(TXD)와 ST-LINK(TX)가 **동시에 이 라인을 구동하려는 상태**가 되어 버스 컨텐션이 발생, RPi가 보낸 명령 신호가 깨지거나 무시됨 → 명령 전달 안 되는 증상과 정확히 일치

### 3.3 검증 테스트

라즈베리파이와 STM32를 GPIO 직결 대신, **NUCLEO 보드의 USB 포트를 라즈베리파이 USB에 연결**하여 ST-LINK VCP(가상 COM 포트)로 통신하도록 변경 후 테스트한 결과, **명령 전달이 정상적으로 동작**함을 확인했습니다.

이는 아래와 같은 경로 차이 때문입니다.

**(A) 문제가 있었던 구성 — GPIO 직결**
```
RPi GPIO(TXD) ----+
                   ├──> PA3 (충돌 발생)
ST-LINK(TX) -------+

RPi GPIO(RXD) <---- PA2 <---- STM32 (정상, 단방향)
```

**(B) 정상 동작한 구성 — USB(VCP) 경유**
```
RPi (USB) <--CDC--> ST-LINK MCU <--TTL--> PA2/PA3 (STM32)
```
USB 경로에서는 **ST-LINK MCU가 PA2/PA3의 유일한 드라이버**가 되므로, RPi는 ST-LINK와만 통신하고 실제 TTL 라인을 구동하는 주체가 하나로 정리되어 충돌이 사라집니다.

---

## 4. 해결 방법

### 방법 A. USB(ST-LINK VCP) 경유 방식 사용 (현재 검증된 방법)

- NUCLEO 보드의 USB 포트를 라즈베리파이 USB 포트에 연결
- 라즈베리파이에서는 `/dev/ttyACM0` (또는 유사한 CDC 장치)로 인식하여 시리얼 통신
- **장점**: 배선 불필요, 즉시 해결, 안정적
- **단점**:
  - ST-LINK MCU를 경유하므로 GPIO 직결 대비 **레이턴시가 다소 증가**
  - ST-LINK MCU 자체의 처리 오버헤드 존재
  - 실시간성이 중요한 고속 제어 용도로는 부적합할 수 있음

### 방법 B. GPIO 직결(TTL) 방식 유지 + 솔더 브릿지 오픈

GPIO 직결 방식을 계속 사용하고 싶다면, ST-LINK 경로를 물리적으로 분리해야 합니다.

1. NUCLEO 보드에서 **SB13, SB14 솔더 브릿지를 오픈(제거)**
   - 커터/인두로 브릿지를 절단하거나 패드를 분리
2. 이렇게 하면 ST-LINK와 PA2/PA3 사이의 연결이 끊어지고, RPi GPIO만이 PA2/PA3의 유일한 통신 주체가 됨
3. **주의**: 이 작업 이후에는 ST-LINK를 통한 USB 시리얼 모니터링(가상 COM 포트로 로그 확인 등)은 더 이상 사용할 수 없음 (SWD 디버깅/플래싱 기능 자체는 영향 없음)

---

## 5. 추가 점검 체크리스트 (참고용)

GPIO 직결 방식으로 재전환 시 아래 항목도 함께 점검할 것을 권장합니다.

- [ ] SB13, SB14 솔더 브릿지 오픈 여부
- [ ] TX-RX 교차 연결 확인 (STM32 PA2 → RPi RXD, STM32 PA3 → RPi TXD)
- [ ] 두 보드 간 공통 GND 연결 여부
- [ ] 라즈베리파이 UART 설정
  - `raspi-config` → Interface Options → Serial Port
    - 로그인 셸(login shell) 사용 안 함으로 설정
    - 시리얼 포트 하드웨어 사용함으로 설정
  - `/boot/firmware/config.txt` (또는 `/boot/config.txt`)
    - `enable_uart=1` 설정 확인
    - Raspberry Pi 4는 기본적으로 Bluetooth가 `/dev/ttyAMA0`(PL011)를 점유하는 경우가 많으므로, `dtoverlay=disable-bt` 또는 `dtoverlay=miniuart-bt` 설정으로 UART 매핑 확인 필요
- [ ] Baudrate, Parity, Stop bit, Flow control(RTS/CTS 비활성) 등 양쪽 설정 일치 여부
- [ ] 필요 시 로직 애널라이저/오실로스코프로 PA3 라인 실측 파형 확인

---

## 6. 결론

| 구분 | 원인 | 해결 |
|---|---|---|
| 명령 전달 실패 | PA3(USART2_RX) 라인에 RPi TXD와 ST-LINK TX가 동시에 연결되어 발생한 버스 컨텐션 | USB(VCP) 경유 방식으로 전환하여 ST-LINK를 유일한 드라이버로 사용 → 해결 확인 |

현재는 **USB(VCP) 경유 방식**으로 안정적으로 동작 중이며, 추후 더 낮은 레이턴시가 필요한 경우 **SB13/SB14 오픈 후 GPIO 직결 방식**으로 전환하는 옵션을 고려할 수 있습니다.

---

*작성일: 2026-07-20*
*대상 보드: NUCLEO-F103RB (STM32F103CBT6), Raspberry Pi 4*
