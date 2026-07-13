# 설계 사양서 — 장비 2-보드(ESP32-S3 + STM32F446) + 내부 링크

> **Device Firmware/Hardware Design Specification — DRAFT**
> 대상: Liquid Handler 장비(④ + on-device ③ 링크)의 **2-보드 실현**.
> 상위 경계: [`icd-liquid-handler-3-4.md`](icd-liquid-handler-3-4.md) (SiLA 서버↔driver) · 상위 wire 계약: [`icd-liquid-handler-2-3.md`](icd-liquid-handler-2-3.md)
> 하드웨어: ESP32-S3-DevKitC(comms) + STM32 Nucleo-F446RE(motion) + FRAM. 기구: 1+8채널, 독립 Z 6축.
>
> 상태: **DRAFT** — 역할 분리·펌웨어 태스크 구조·신뢰성 티어·복구 상태머신·§2 wire 필드 폭/enum 코드값은 확정, **정확한 핀/타이머/DMA 스트림 번호는 bring-up 단계 확정**.

---

## 0. 시스템 컨텍스트 · 역할 분리

보드 2개, ESP32-S3에 임베디드 gRPC 서버 탑재. 외부의 스케줄러 ②가 SiLA 클라이언트 표준 프로토콜을 통해 장비에 원격 접속

```
호스트 ②: 오케스트레이터 · SiLA2 클라이언트 — 스케줄러 · Device Registry · mDNS 발견 · SPKI 핀 검증 · deck slot·기기 배정
        ╎ WiFi — SiLA2 / gRPC / HTTP2 / TLS≥1.2 (icd-2-3 계약: 2-3 경계가 이 무선 링크로 옮겨옴)
   ESP32-S3   ← §3: SiLA2 서버 ③ — 임베디드 gRPC/HTTP2 종단 · mDNS(_sila._tcp) 광고
        |           · SiLA/구조 검증 · deck id·section id 광고(②용) · 좌표 검증·합성·driver 변환
        |           · lease/UUID/Lock/Cancel/ErrorRecovery 종단 · observable command 스트림
        |           · 명령 버퍼(WiFi 끊김 흡수) · telemetry(=observable property) 캐시
        │  UART (§2) — SiLA-서버↔driver (icd-3-4 경계가 이 내부 링크로 옮겨옴, **§2 불변**)
   STM32F446  ← §4: driver/firmware ④ — stroke 분해 · step 생성 · ADC/LLD · 플런저 · FRAM 체크포인트
        │  step/dir + 드라이버(Z/P=TMC2209 UART, X/Y=TMC2208 standalone) — §4.3.1
   물리 6축 (X,Y,Z1,Z2,P1,P2) + 팁 이젝터
```

물리 링크 기반의 레이어 매핑: ICD 구조가 물리적 연결 링크와 직결됨
레벨 2-3 경계 (SiLA2/gRPC): ESP32 ↔ 호스트 ② 간 Wi-Fi 링크 활용
레벨 3-4 경계 (SiLA 서버 ↔ 드라이버): ESP32 ↔ STM32 간 내부 UART 링크 활용 (본 문서 §2)
ESP32의 역할: 두 레이어의 경계에서 SiLA 서버로 기능하며, §2의 드라이버 프로토콜을 통해 레벨 3-4의 통신 규격을 준수함

**대표 실행 시퀀스 (② ↔ ESP32 ↔ STM32):**

```
Task Scheduler ②              ESP32-S3 / SiLA 서버 ③                 STM32F446 / driver ④
   │                                      │                                      │
   │  mDNS discovery + TLS/mTLS           │                                      │
   │────────────────────────────────────▶│                                       │
   │◀────────────────────────────────────│  Server UUID/SPKI, FDL                │
   │                                      │                                      │
   │  Get capability/property             │                                      │
   │  DeckIdentity/Sections,              │                                      │
   │  CalibrationStatus, TransferLimits,  │                                      │
   │  ResultQcModes, HeadGeometry         │                                      │
   │────────────────────────────────────▶│  HELLO/RESYNC                         │
   │                                      │─────────────────────────────────────▶│
   │                                      │◀─────────────────────────────────────│  capabilities, calibration mirror,
   │◀────────────────────────────────────│                                       │  result ring free, recovery state
   │                                      │                                      │
   │  LockServer(LockId)                  │                                      │
   │────────────────────────────────────▶│  lease owner/SPKI 기록                │
   │◀────────────────────────────────────│                                       │
   │                                      │                                      │
   │  Dispense(...well_coords,            │                                      │
   │  VolumeMap, LiquidProfile,           │                                      │
   │  meta=LockId)                        │                                      │
   │────────────────────────────────────▶│  SiLA 구조 검증·shape/head 검증         │
   │                                      │  deck+well 좌표 합성                   │
   │                                      │  result ring precheck                │
   │                                      │  SERVER_ADMISSION_PREPARE            │
   │                                      │─────────────────────────────────────▶│
   │                                      │◀─────────────────────────────────────│  SERVER_ADMISSION_ACCEPTED
   │◀────────────────────────────────────│  CommandExecutionUUID 반환             │  FRAM-B: server_admitted_not_dispatched
   │                                      │                                      │
   │  Subscribe ExecutionInfo(UUID)       │                                      │
   │────────────────────────────────────▶│                                       │
   │                                      │  CMD_DISPENSE(driver-ready binary)   │
   │                                      │─────────────────────────────────────▶│  safety gate → FRAM-B driver_accepted
   │                                      │◀─────────────────────────────────────│  CMD_ACCEPTED
   │◀────────────────────────────────────│  ExecutionInfo waiting/running        │
   │                                      │                                      │
   │◀────────────────────────────────────│◀─────────────────────────────────────│  ActiveTarget / DispensePhase /
   │                                      │                                      │  SENSOR best-effort stream
   │                                      │                                      │
   │                                      │◀─────────────────────────────────────│  CMD_RESULT{DispensedVolume, pressure_qc}
   │◀────────────────────────────────────│  ExecutionInfo finished               │  FRAM-B terminal result echo
   │                                      │                                      │
   │  Result(UUID)                        │                                      │
   │────────────────────────────────────▶│                                       │
   │◀────────────────────────────────────│  DispenseResult replay/return         │
   │                                      │                                      │
   │  UnlockServer(LockId)                │                                      │
   │────────────────────────────────────▶│                                       │
   │◀────────────────────────────────────│                                       │
   │                                      │  terminal lifetime 만료 후 RESULT_GC  │
   │                                      │─────────────────────────────────────▶│  FRAM-B GC
```

경계 원칙:
- ②↔③: SiLA2/gRPC 공개 wire. well label·FDL Structure·`List<List<Real>>` 등 명시 표현 유지.
- ③↔④: §2 내부 driver wire. ESP32가 `well_coords[]`와 deck calibration mirror를 합성해 `machine_coords[]`·고정 폭 enum·COBS binary로 변환.
- UUID 반환 전 STM32 FRAM-B journal 기록 필수. ESP32 리셋 시 STM32 `HELLO/RESYNC`로 UUID·owner·terminal record 복구.
- `PIPETTOR_POSE` 같은 machine-space pose는 service/admin `MotionDiagnostics` 전용. 운용 API에는 승격 금지.

**시스템 설계 4대 핵심 원칙:**
1. SiLA 공개 wire와 내부 driver wire 분리
- 개념: Wi-Fi 구간은 SiLA2/gRPC 공개 wire, UART 구간은 §2 내부 driver wire로 분리.
- ESP32의 역할: SiLA 명령을 종단한 뒤 deck calibration mirror와 ware-local well 좌표를 합성해 driver-ready command로 명시 변환. UART 너머로 SiLA 구조·ware catalog 의미를 터널링하지 않음.
- 확장성: 내부 driver command가 전송 계층과 SiLA 표현에 종속되지 않으므로, 향후 CAN 기반 툴헤드 MCU가 추가되더라도 driver wire adapter만 추가해 대응 가능.
2. ESP32 기반의 SiLA 구조 종단 및 레이어 독립성 유지
- SiLA 제어권 집중: Lease, CommandExecutionUUID, LockController, CancelController, ErrorRecovery 등 주요 제어 로직은 모두 ESP32 서버에서 직접 처리(종단).
- 식별자 매핑: 외부 공개 식별자는 SiLA `CommandExecutionUUID`, 내부 실행 식별자는 `cmd_key={cmd_epoch,cmd_id}`. ESP32가 UUID↔`cmd_key` 매핑을 관리하고, STM32는 `cmd_key`로 중복 실행을 막음.
STM32의 독립성: STM32는 SiLA 프로토콜을 인지하지 않고 §2 드라이버 프로토콜의 부분집합만 처리. 즉, SiLA 구조를 UART 너머로 터널링하지 않음으로써 ICD 3-4 경계를 명확히 유지.
3. STM32 중심의 Stroke 분해를 통한 무선 지터 차단
- 명령 최적화: 호스트 ②는 개별 행정 단위가 아닌 패스 단위 명령(예: VolumeMap 등)만 하향 전달하므로, 무선 네트워크 지터(Jitter)로 인한 제어 지연 영향이 없음. (ICD 2-3 §6.1 준수)
- 연산 분담: 호스트 ②는 ETA(예상 소요 시간)를 산정하기 위해 HeadGeometry를 기반으로 총 Stroke 개수를 독립적으로 산출하지만, 실제 구동을 위한 Stroke 분해 연산 및 실행 제어는 모두 STM32가 전담.
4. FRAM 기반의 데이터 복구 권위와 Best-Effort 링크 텔레메트리
- 복구의 신뢰성: 시스템 복구를 위한 데이터의 최종 권위(Source of Truth)는 비휘발성 메모리인 FRAM에 있음.
- 링크 상태: 네트워크 통신을 통한 텔레메트리 데이터 전송은 Best-Effort 서비스로 처리하여 링크 불안정성이 시스템 복구에 미치는 영향을 최소화. (§2.2 신뢰성 티어 및 §5 복구 가이드라인 준수)

**보드별 책임 요약:**

| 관심사 | ESP32-S3 (§3) | STM32F446 (§4) |
|---|---|---|
| 무선·보안 | WiFi, **SiLA2 gRPC/HTTP2/TLS(≥1.2) 서버**, mDNS 광고, 서버 cert·SPKI, 키(NVS) | — |
| 명령 흐름 | **SiLA 서버 ③**: SiLA/구조 검증·lease/UUID/Lock/Cancel/ErrorRecovery 종단, deck id·section 광고, deck+well 좌표 합성, driver command 정규화, 버퍼링, resync | driver-ready pass 명령 수신·실행(machine-space safety gate) |
| 실시간 모션 | — | step/dir 생성, stroke 분해, 플런저 |
| 센싱 | — | 압력(pLLD/TADM), TMC2209 StallGuard/진단 |
| 상태 복구 소스 | telemetry 캐시(휘발, best-effort) | **FRAM 복구 포인트 (최종 기준점)** |
| 시간 특성 | soft(네트워크 지터 허용) | **hard-RT** |

---

## 1. 서버 간 통신 API · 실행 흐름 (② ↔ ESP32-S3/③)

> task scheduler ② 기준의 장비 발견·인증·등록·명령·구독·복구 경계. ESP32 구현 세부는 §3, 내부 driver wire는 §2.

### 1.1 연결 · 발견 · 신뢰 수립

1. 장비 발견: mDNS `_sila._tcp`, SiLA Server UUID, SPKI hint 확인.
2. 전송 계층: SiLA2/gRPC/HTTP2/TLS 1.2 이상, TLS 1.3 가능 시 우선 협상.
3. 서버 신뢰: 장비 자체 서명 서버 인증서/키 제시, ② 최초 접속 시 서버 SPKI TOFU 핀 고정.
4. 클라이언트 인증: ② 클라이언트 인증서 제시, ESP32 mTLS 개인키 보유 확인.
5. 클라이언트 인가: client SPKI hash allowlist + role(`operator|admin|service`) 기준 수락.
6. 소유자 바인딩: server admission 시 client SPKI hash를 `owner_spki_hash`로 기록. 결과 회수·cancel·continuation 권한 판정 기준.

### 1.2 공개 Feature · API 경계

운용 API(task scheduler/user 경로):
- `SiLAService`: FDL 조회, Server UUID 확인
- `LiquidHandling`: `Dispense`, `DispenseAndMix`, `Mix`, `Wash`, `PickTips`, `EjectTips` 등 observable command
- `LockController`: 작업 제출 전 exclusive Lock 획득·유지·해제
- `CancelController`: owner 또는 권한 role 기준 cancel
- `ErrorRecoveryService`: recoverable error continuation 선택
- Observable Property: `DeviceStatus`, `ReservoirLevels`, `DeckOccupancy`, `HeadGeometry`, `DeckIdentity`, `DeckSections`, `CalibrationStatus`, `TransferLimits`, `ResultQcModes`

Service/admin API(기기 엔지니어 경로):
- raw deck layout, deck transform, calibration table, sensor diagnostics, motion diagnostics
- `PipettorPose` 같은 machine-space pose는 service/admin `MotionDiagnostics` 전용. 운용 `LiquidHandling` property 승격 금지
- `admin|service` role, service mode 또는 exclusive Lock, 감사 로그 필수

### 1.3 최초 등록 · capability handoff

최초 장비 등록 시 ESP32 제시 값. ②의 Device Registry 및 Deck/Ware Catalog 바인딩 입력.

| 분류 | 값 | 비고 |
|---|---|---|
| 신원 | SiLA Server UUID, Server Cert/SPKI | SPKI TOFU 핀 대상 |
| Feature | FDL, `LiquidHandling`, Lock/Cancel/ErrorRecovery | SiLA2 공개 계약 |
| Deck 식별 | `DeckIdentity`, `DeckSections`, `CalibrationStatus` | `DeckId`, `SectionId`, calibration version/hash. raw transform 제외 |
| 전송 한계 | `TransferLimits` | `DriverMaxPayloadBytes`, `InlineMaxWells`, payload mode |
| 결과 QC | `ResultQcModes` | `pressure_qc={not_applicable,passed,failed}`, source=`pLLD|TADM|seal_self_test` |
| 헤드/축 | `HeadGeometry`, axis/head capability | ETA·작업 가능성 판단용 |

raw machine 좌표, deck transform, fiducial, calibration table은 운용 API 제공 금지. hardware 조율·캘리브레이션 경로의 service/admin API 전용.

### 1.4 명령 제출 · admission · 실행 흐름

1. Lock 획득: ②의 exclusive Lock 확보 후 SiLA observable command 호출.
2. 공개 wire 입력: well label, FDL Structure, `List<List<Real>>`, liquid profile 등 명시 표현 유지.
3. ESP32 검증: SiLA 구조, Lock, shape/head mode, volume/profile 수치 범위, Deck/Section/Calibration 식별자.
4. ESP32 변환: STM32 deck calibration mirror + ② ware-local `well_coords[]` → `float32` machine 좌표 합성, driver command 정규화.
5. Server admission precheck: UUID 반환 전 result ring 여유 확인.
6. Server admission journal: STM32 FRAM-B에 `server_admitted_not_dispatched` reliable 기록.
7. UUID 반환: journal 성공 후 `CommandExecutionUUID` 반환. 외부 server admission 성립, driver 실행 수락 전 상태.
8. Driver command 하향: ESP32가 §2 내부 `CMD_*` 전송.
9. Driver admission: STM32 safety gate 통과 + FRAM `driver_accepted` 전이 후 `CMD_ACCEPTED` 반환. driver admission/durability 성립.
10. 진행 보고: STM32 best-effort progress/phase/sensor telemetry 상향, ESP32 `ExecutionInfo` 변환.
11. 결과 보고: terminal 시 STM32 reliable `CMD_RESULT` 상향. `outcome=ok`만 ESP32 `Result(UUID)=DispenseResult`로 변환, `outcome=err`는 `ExecutionInfo.finishedWithError` + Defined Execution Error로 변환.
12. 결과 GC: terminal lifetime 만료 후 ESP32 내부 `RESULT_GC` 발행. 외부 consume ACK API 없음.

### 1.5 데이터 I/O 경계

- ②↔③: SiLA2/gRPC/protobuf 공개 wire. 문자열 well label과 명시 구조 표현 허용.
- ③↔④: §2 COBS binary 내부 wire. 문자열 없음, fixed little-endian, `well_index:u16`, `machine_coords[]`, `float32`, 고정 enum.
- Geometry Catalog, Ware Catalog, container-slot 호환성: ② 책임.
- ESP32: 명령 단위 입력 검증·좌표 합성. catalog 장기 보관 없음.
- Deck calibration 지속 권위: STM32 FRAM. ESP32는 HELLO/resync read-only mirror로 좌표 합성.
- STM32: catalog-stateless. 단 machine-space safety gate 최종 수행(calibration version/hash, finite 좌표, soft limit, volume/profile 범위, 속도/가속 상한).

### 1.6 서버 간 복구 계약

- `lifetimeOfExecution`: UUID/Info 및 성공 Result 회수 보장. 실패 terminal은 `ExecutionInfo.finishedWithError`와 Defined Execution Error로 replay.
- 실행 중 수명 갱신: `updatedLifetimeOfExecution` push.
- terminal tail: 기본 300초, PROVISION 파라미터로 조정 가능.
- ESP32 리셋 복구 소스: STM32 FRAM-B `{cmd_key, uuid, owner_spki_hash, payload_hash, state, terminal_record?}`.
- `server_admitted_not_dispatched`: UUID 발급 완료, driver 미전송·미실행 확정. lifetime 내 Info 조회 = `finishedWithError(NotDispatched)` replay. `Result(UUID)`는 DispenseResult 없이 표준 오류.
- Lock lease·observable subscription: ESP32 RAM 상태. 리셋 후 재Lock·재구독 필요.
- UUID/result durability와 Lock durability 분리.

## 2. 보드 간 통신 API · 내부 driver wire (ESP32 ↔ STM32)

> ESP32↔STM32 UART 링크 wire 계약. §3·§4 구현의 공통 통신 경계.

### 2.1 물리 계층

| 항목 | 결정 | 근거 |
|---|---|---|
| 버스 | **UART (USART), full-duplex** | 양방향 비동기 — 명령 하향·telemetry 상향이 대칭. SPI는 async telemetry에 DATA_READY 라인 강제 → pass granularity엔 불필요한 복잡성 |
| 속도 | **1–2 Mbps** (bring-up시 확정), 8N1 | pass-level 명령 + telemetry엔 충분. 양측 DMA(ESP32 UART DMA, STM32 USART+DMA) |
| 흐름 제어 | 앱-레이어 **credit 기반**(§2.4) + **ATN GPIO(v1 채택)**(STM32→ESP32, 긴급 이벤트 알림 → poll 회피) | HW RTS/CTS 대신 이식성 높은 credit |
| 접지/레벨 | 공통 GND, 3.3V 로직 (양측 3.3V — 레벨시프터 불요) | |

### 2.2 링크 계층 — 신뢰성 프레이밍

**COBS** 프레이밍(0x00 구분자) + 고정 헤더 + CRC:

```
[COBS 인코딩 { seq:u8 | flags:u8 | type:u8 | len:u16 | payload[len] | crc16:u16 } ] 0x00
```

- `seq`: 방향별 순증 시퀀스(래핑). ACK 대상.
- `flags`: `ACK_REQ`(신뢰 전송 요구) · `ACK`(이 프레임이 ack) · `PRIO`(우선 경로, §2.5) · `RESYNC`.
- `type`: 메시지 타입(§2.5) 및 코드값(§2.6).
- `crc16`: CRC-16/CCITT, 헤더+payload.

**신뢰성 티어 (핵심 — FRAM 원칙의 귀결).** 전송 등급 2개로 분리, backpressure 최소화.

| 티어 | 메시지 | 전송 | 손실 시 |
|---|---|---|---|
| **Reliable** (`ACK_REQ`) | server admission journal, 명령(하향), **CMD_RESULT**, **RECOVERABLE_ERROR**, CANCEL/CONTINUATION, HELLO/CHECKPOINT | seq+ACK+**재전송**(timeout·N회), 순서 보장 | 재전송; 초과 시 링크 fault→resync |
| **Best-effort** (droppable) | **DispensePhase · ActiveTarget · ExecutionInfo(progress) · 센서 스트림** | ACK 없음, **last-value-wins** | 무시 — ESP32가 마지막값 캐시(§3.1). **복구 경계는 FRAM에서 재구성**(§5), 프레임 전부 수신에 의존 안 함 |

> 이 티어링이 FRAM 존재 이유다: 진행 telemetry를 놓쳐도 STM32의 FRAM 논리 진행이 진실. 링크는 "실시간 보기"이고 FRAM은 "복구 원장".

**중복 실행 방지 원칙.**
- 링크 reliable 전송은 **at-least-once**. `ACK`는 프레임 CRC 정상 수신 확인일 뿐, 명령 수락·실행 의미 아님.
- 실행 exactly-once는 앱 계층 계약: `cmd_key` 중복 판정(§2.5.1), server admission journal(§2.5.3), driver admission(§2.5.4), terminal replay/GC(§2.5.5–§2.5.6) 조합으로 보장.
- ESP32는 `ACK`만으로 driver 상태나 result 상태를 전진시키지 않음.

### 2.3 세션 · 핸드셰이크

- 링크 up/부팅 시 **HELLO** 교환(reliable): `proto_ver`, `fw_ver`, capabilities(축 수, 헤드 리스트=`HeadGeometry`, FRAM 체크포인트 유무, `result_qc_modes={not_applicable,passed,failed}`, `pressure_qc_source={pLLD,TADM,seal_self_test}`), **deck id·section id·캘리브레이션 버전/hash·deck calibration mirror**, `driver_max_payload_bytes`, `inline_max_wells`, `result_ring_capacity/free`, `terminal_tail_sec_supported`(ESP32가 ②에 SiLA capability/registry metadata로 광고; slot 수용 제약은 ② catalog 소관이라 제외).
- `deck calibration mirror`: ESP32 좌표 합성용 read-only transform set. STM32 FRAM 보유값이 지속 권위. 외부 ②에는 version/hash만 광고하고 raw transform은 노출하지 않음.
- `proto_ver` 호환 규칙: `major` 불일치 = 링크 거부. `minor`는 additive-only, 양측 `min(local_minor, peer_minor)` 기능 집합으로 운용. 미지 optional 필드는 무시, 미지 required 필드는 `ProtocolFault/UnsupportedRequiredField`.
- **heartbeat**: 앱 레이어 주기 PING/PONG(장비 링크 liveness). SiLA `KeepLeaseAlive`(lease refresh)와 **별개** — 후자는 호스트 ② 관심사.

### 2.4 흐름 제어 (credit)

STM32는 물리 특성상 **동시 1개 실행**(§4.2 single-writer). 얕은 명령 FIFO(depth 2–4)만 유지, HELLO/상태로 **free slot(credit)** 광고. ESP32는 credit 내에서만 명령 하향, 나머지는 자기 버퍼에 보관(§3.1: WiFi 끊김 흡수 지점).

### 2.5 내부 API 기능 · 흐름

> `cmd_*` 이름은 내부 실행 식별자와 driver 명령군에만 사용. 외부 ②↔③ 표면은 SiLA `CommandExecutionUUID`만 사용. ESP32가 UUID↔`cmd_key` 매핑을 보유하고, STM32는 `cmd_key`와 FRAM 상태만으로 중복 실행을 차단.

#### 2.5.1 공통 식별자 · 중복 실행 방지

`cmd_key={cmd_epoch:u16, cmd_id:u16}` = ESP32 발급 내부 실행 핸들. 모든 실행 command/event/result/cancel/recovery가 이를 참조. `cmd_id`는 `cmd_key`의 하위 필드일 뿐 단독 식별자로 쓰지 않음.

- `cmd_id`: 짧은 순번.
- `cmd_epoch`: 순번 세대. ESP32 NVS 보존. ESP32 부팅 시 또는 `cmd_id` wrap 직전 1 증가 후 저장.
- `cmd_key`: STM32 중복 판정 키. FRAM-B record key.
- `CommandExecutionUUID`: 외부 SiLA observable command 식별자. ②에는 UUID만 노출. STM32는 UUID를 opaque 16B로 저장·반향.
- `payload_hash`: 같은 `cmd_key` 재수신 시 같은 payload 재전송인지, 다른 payload 충돌인지 구분하는 보조값. 실행 키 아님.
- `cmd_epoch`까지 wrap되려면 STM32 FRAM-B 미회수 record가 없어야 함. 남아 있으면 새 command admission을 `ResourceExhausted/ProtocolFault`로 정지.
- 같은 `cmd_key` 재수신 시 `payload_hash` 비교. 같으면 FIFO에 다시 넣지 않고 현재 상태에 맞춰 응답 replay. 다르면 `ProtocolFault/DuplicateCommandConflict`.

> **`cmd_id:u16` 단독 키 금지.** 장기 운용·ESP32 리셋·FRAM 미회수 결과 보유 중 `cmd_id` wrap이 발생하면 과거 command와 alias 가능. 내부 실행 키는 반드시 `cmd_key` 전체.

#### 2.5.2 Session · Capability API

링크 초기화·복구·liveness 흐름. 실행 command와 분리.

| 방향 | type | 티어 | 필드 | 흐름 |
|---|---|---|---|---|
| 양방향 | `HELLO` | reliable | `proto_ver`, `fw_ver`, capabilities, deck id/section id/calibration version/hash, deck calibration mirror, `driver_max_payload_bytes`, `inline_max_wells`, `result_ring_capacity/free`, `terminal_tail_sec_supported` | 부팅·링크 up·resync 시작 |
| 하향 | `PING` | best-effort | — | link liveness probe |
| 상향 | `PONG` | best-effort | — | heartbeat 응답 |

- `HELLO` source = STM32 FRAM 지속값 + firmware capability.
- ESP32는 HELLO 결과를 ②의 `TransferLimits`, `ResultQcModes`, `DeckIdentity`, `DeckSections`, `CalibrationStatus` 광고로 변환.
- SiLA `KeepLeaseAlive`와 내부 `PING/PONG` 분리. 전자는 ②↔③ lease, 후자는 ③↔④ link liveness.

#### 2.5.3 Server Admission · Resync Journal API

UUID 반환 전 durability 확보 흐름. 외부 server admission과 내부 driver admission 분리.

| 방향 | type | 티어 | 필드 | 흐름 |
|---|---|---|---|---|
| 하향 | `SERVER_ADMISSION_PREPARE` | reliable | `cmd_key`, `uuid`, `owner_spki_hash`, `payload_hash`, `lifetime_deadline_ms` | UUID 반환 전 FRAM-B journal prepare |
| 상향 | `SERVER_ADMISSION_ACCEPTED` | reliable | `cmd_key`, `result_ring_free` | FRAM-B `server_admitted_not_dispatched` persist 완료 |

흐름:
1. ESP32 result ring precheck.
2. ESP32 → STM32 `SERVER_ADMISSION_PREPARE`.
3. STM32 FRAM-B 원자 기록: `{cmd_key, uuid, owner_spki_hash, payload_hash, state=server_admitted_not_dispatched}`.
4. STM32 → ESP32 `SERVER_ADMISSION_ACCEPTED`.
5. ESP32 → ② `CommandExecutionUUID` 반환.

리셋 의미:
- journal 전 ESP32 크래시: UUID 미발급, 실행 없음, 클라 재시도.
- journal 후 driver command 전 ESP32 크래시: `server_admitted_not_dispatched`, 실행 안 됨 확정. lifetime 내 Info = `finishedWithError(NotDispatched)`.
- driver accept 후: `driver_accepted|running|terminal` 기준 resync.

#### 2.5.4 실행 Command API

ESP32가 SiLA 명령을 driver-ready machine-space payload로 정규화한 뒤 STM32에 하향. STM32는 catalog-stateless safety gate 통과 후 실행 FIFO에 삽입.

| 방향 | type | 티어 | 필드(요약) | SiLA 대응 |
|---|---|---|---|---|
| 하향 | `CMD_DISPENSE` | reliable | `cmd_key`, `head`, `tip_policy`, `calibration_version/hash`, `src{deck_slot, src_well_index:u16, machine_coords[]}`, `target{deck_slot, machine_coords[], VolumeMap[][]}`, `liquid_profile{...}` | `Dispense` |
| 하향 | `CMD_DISPENSE_AND_MIX` | reliable | `CMD_DISPENSE` + `mix_cycles`, `mix_volume_ul` | `DispenseAndMix` |
| 하향 | `CMD_MIX` | reliable | `cmd_key`, `head`, `calibration_version/hash`, `target{deck_slot, machine_coords[]}`, `mix_volume_ul`, `mask[][]`, `reps` | `Mix` |
| 하향 | `CMD_WASH` | reliable | `cmd_key`, `head`, `wash_station`, `cycles`, `new_tip:bool` | `Wash` |
| 하향 | `CMD_PICK_TIPS` / `CMD_EJECT_TIPS` | reliable | `cmd_key`, `head`, `calibration_version/hash`, `tiprack{deck_slot, machine_coords[]}`, `mask[][]` | `PickTips` / `EjectTips` |
| 상향 | `CMD_ACCEPTED` | reliable | `cmd_key`, `credit_free` | driver admission/durability 성립 |

실행 흐름:
1. ESP32: SiLA 구조·Lock·shape/head·volume/profile 범위 검증.
2. ESP32: `well_coords[]` + deck calibration mirror → `machine_coords[]` 합성. `float32` 고정.
3. ESP32: `CMD_*` 하향. credit 필요.
4. STM32: payload hash·`cmd_key` 중복 판정.
5. STM32: safety gate 통과 전 모션 금지.
6. STM32: FRAM-B record `driver_accepted` 전이, FIFO 삽입.
7. STM32: `CMD_ACCEPTED` 상향.

좌표·shape 경계:
- ②→③ SiLA 명령의 `well_coords[]` = ②가 geometry catalog로 해소한 ware-local 좌표.
- ③→④ UART payload = driver-ready `machine_coords[]`, 문자열 well label 없음.
- `VolumeMap`/`mask` = 타깃 ware shape. ganged 8채널 열-균일 위반은 ② dry-run 차단. STM32 도달분은 상위 의미상 실행 가능 전제이나, safety gate 통과 전 모션 금지.

STM32 safety gate:
- 캘리브레이션 버전/hash 일치.
- 모든 `float32` machine 좌표 finite, NaN/Inf/subnormal reject.
- 축별 soft limit·금지영역·travel envelope 확인.
- VolumeMap·mix_volume·aspirate/dispense 속도·가속·압력 파라미터 finite.
- 플런저 stroke·최소/최대 volume·속도/가속 상한 확인.
- `machine_coords[]`·`VolumeMap`·`mask` shape와 head mode 일치. 길이 불일치·well_index 범위 초과·빈 mask reject.
- 실패 처리: 내부 `CMD_RESULT{err, InvalidPayload|SafetyLimitViolation|CalibrationVersionMismatch}` 기록. ESP32는 외부 `ExecutionInfo.finishedWithError` + Defined Execution Error로 표면화.

#### 2.5.5 진행 Telemetry · Terminal Result API

진행 telemetry는 best-effort, terminal record는 reliable. 복구 권위는 FRAM-B terminal record.

| 방향 | type | 티어 | 필드 | 외부 변환 |
|---|---|---|---|---|
| 상향 | `EXECUTION_INFO` | best-effort | `cmd_key`, `status`, `progress:0..1`, `eta_hint?` | SiLA `ExecutionInfo` |
| 상향 | `ACTIVE_TARGET` | best-effort | `cmd_key`, `deck_slot`, `well_index` | Lane A `ActiveTarget` |
| 상향 | `DISPENSE_PHASE` | best-effort | `cmd_key`, `phase:enum{MovingToWell,Dispensing,Mixing,ChangingTip,MovingAway}` | Intermediate response |
| 상향 | `SENSOR` | best-effort | `ReservoirLevels[]` / `DeckOccupancy[]` / `DeviceStatus` | Observable property |
| 상향 | `PIPETTOR_POSE` | best-effort | `cmd_key`, pose(벤더) | service/admin `MotionDiagnostics` 전용 |
| 상향 | `CMD_RESULT` | reliable | `cmd_key`, `outcome:enum{ok,err}`, `error?`, `DispensedVolume[][]`, `pressure_qc` | `ok`만 `Result(UUID)=DispenseResult`; `err`는 `finishedWithError` |

결과 의미(v1):
- `DispensedVolume[][]` = driver가 실행한 정규화 명령량 echo.
- 압력 센서는 직접 체적 측정값 아님. pLLD/TADM QC 근거.
- `commanded|estimated|measured` 3분기 `result_basis` 없음.
- 성공 liquid transfer + 압력 파형·씰 self-test 정상 = `pressure_qc=passed`.
- 압력 검증 비대상 = `pressure_qc=not_applicable`.
- 클롯·기포·숏샘플·누설 의심 = `pressure_qc=failed` + terminal/recoverable error.

오류 enum:
- icd-2-3 §6.5 집합 + 장비 safety gate 집합.
- `GeometryMismatch` · `VolumeOutOfRange` · `HeadMapIncompatible` · `SourceEmpty`/`InsufficientVolume` · `WareNotPresent` · `TipPolicyUnsupported` · `TipPickupFailed` · `InvalidPayload` · `SafetyLimitViolation` · `CalibrationVersionMismatch` · `Unauthorized` · `ProvisionRejected` · `ResourceExhausted` · `ProtocolFault` · `DuplicateCommandConflict` · `UnsupportedRequiredField` · `OperationNotSupported` · `Cancelled` · `UncertainStroke` · `NotDispatched` · `StaleContinuation`.

장비 스펙 노출:
- `pressure_qc` enum 집합과 QC source는 최초 장비 등록 시 `ResultQcModes` capability로 ②에 제시.
- task scheduler는 QC 필수 작업에서 `pressure_qc=passed` 요구 여부, `not_applicable` 허용 여부, 실패 시 재시도/격리 정책 결정.
- enum 의미 변경 = `proto_ver` minor additive 또는 major bump 대상.

#### 2.5.6 제어 · 오류 회복 · GC API

버퍼 뒤에 줄 서면 안 되는 제어 흐름. `PRIO` 프레임 사용.

| 방향 | type | 티어 | 필드 | 흐름 |
|---|---|---|---|---|
| 하향 | `CANCEL` | reliable + PRIO | `cmd_key` 또는 `ALL`, `op_seq` | command cancel |
| 상향 | `RECOVERABLE_ERROR` | reliable | `cmd_key`, `recovery_seq`, `error`, `options[]` | recoverable error 대기 |
| 하향 | `CONTINUATION` | reliable + PRIO | `cmd_key`, `recovery_seq`, `op_seq`, `option`, `input?` | 오류 회복 선택 |
| 하향 | `RESULT_GC` | reliable | `cmd_key`, `op_seq` | terminal lifetime 만료 후 FRAM-B record GC |

중복·stale 방지:
- `CANCEL`·`RESULT_GC`: `{cmd_key, op_seq}` 기준 1회 적용. 같은 op 재수신 = 마지막 응답 replay.
- `CONTINUATION`: `{cmd_key, recovery_seq, op_seq}` 기준 1회 적용.
- `recovery_seq` 불일치 = `ProtocolFault/StaleContinuation`.

권한:
- state-changing 명령 = allowlist 등록 클라이언트 + 유효 Lock 필요.
- `CANCEL`: 해당 command `owner_spki_hash`와 현재 mTLS client SPKI 일치 시 허용. `CANCEL ALL`은 Lock owner 또는 `admin/service` role만 허용.
- `CONTINUATION`: recoverable command owner 또는 `admin/service` role만 허용.
- `RESULT_GC`: 외부 클라이언트 호출 없음. ESP32 내부 lifetime 정책만 발행.

취소·회복 표면화:
- 취소 결과 = 내부 `CMD_RESULT{err, Cancelled}` 기록, 외부 `ExecutionInfo.finishedWithError(Cancelled)`.
- `Result(UUID)`는 DispenseResult 없이 표준 오류.
- 재분주 경계 = FRAM 논리 상태 + ESP32 캐시(마지막 `ActiveTarget`/`DispensePhase`).

#### 2.5.7 조회 · Service/Admin · Provision API

운용 property read와 기기 엔지니어용 조율 경로 분리.

| 방향 | type | 티어 | 필드 | 권한 |
|---|---|---|---|---|
| 하향 | `QUERY` | reliable | `what:enum{ReservoirLevels,DeckOccupancy,DeviceStatus,HeadGeometry,DeckIdentity,DeckSections,CalibrationStatus,TransferLimits,ResultQcModes}` | `operator|admin|service`, allowlist 필요. Lock 없이 허용 가능 |
| 하향 | `SERVICE_QUERY` | reliable | `what:enum{RawDeckLayout,DeckTransform,CalibrationTable,SensorDiagnostics,MotionDiagnostics}` | `admin|service`, service mode 또는 exclusive Lock, 감사 로그 |
| 하향 | `PROVISION` | reliable | deck 캘리브레이션 등 config-path 값, `config_version`, `signature` | `admin|service`, active command 없음, exclusive Lock 또는 service mode |

운용 `QUERY` 반환 경계:
- raw deck transform·기준점 좌표·machine 좌표·calibration table 미포함.
- `DeckIdentity` = `DeckId/SectionId/CalibrationVersion/Hash`.
- `DeckSections` = section 식별자와 사용 가능 여부.
- `CalibrationStatus` = version/hash/current|stale|pending.

`SERVICE_QUERY` 반환 경계:
- raw deck layout, deck transform, calibration table, sensor diagnostics, motion diagnostics 허용.
- `PipettorPose` 같은 machine-space pose stream = `MotionDiagnostics`.
- 외부 task scheduler 운용 경로 호출·구독 금지.

`PROVISION` 적용:
- payload 서명 검증 + `config_version` 단조 증가 확인.
- rollback·서명 불일치·role 부족 reject.
- 캘리브레이션 변경 후 STM32는 새 calibration version/hash와 deck calibration mirror를 FRAM에 반영.
- HELLO/resync에 새 version/hash·mirror 노출.
- slot 배열·section 구성·기준점·transform 변경 시 `DeckId` 또는 `CalibrationVersion/Hash` 반드시 갱신.
- ESP32는 기존 좌표 합성 mirror 폐기 후 새 mirror 사용.
- ②는 기존 Deck/Ware Catalog 바인딩 stale 처리, 장비 재등록 또는 catalog 재바인딩 전까지 새 작업 할당 금지.

Provisioning bootstrap:
- 제조 시 device root public key 또는 provisioning root SPKI hash를 Secure Boot 보호 read-only 영역에 주입.
- 최초 admin allowlist 등록 = 물리 presence(service jumper/button) + root-signed provisioning bundle.
- admin 분실 복구 = service mode + root signature.
- 일반 `PROVISION`으로 root key 교체 금지. root 교체 = 제조/서비스 RMA 절차 전용.

### 2.6 링크 파라미터 확정 (필드 폭·코드·물리)

§2.2–§2.5의 wire 상수 고정(링크 open 항목 해소). 필드 폭·enum은 아래로 확정, 실측 대상(속도·ring·credit)은 초기값+튜닝.

**SiLA2 정합성 판단:** §2 UART wire는 ESP32↔STM32 내부 driver wire이며 SiLA2 공개 wire가 아님. ②↔③ 경계는 계속 SiLA2 gRPC/HTTP2/TLS + FDL/protobuf 타입(`List<List<Real>>`, `Structure`, Observable Command/Property)을 사용. ESP32 `sila_task`가 SiLA2 타입을 검증·변환한 뒤 내부 `float32`/고정 폭 enum/COBS 프레임으로 하향. 외부 SiLA2 command의 `"A1"` 같은 well label·명시적 구조 표현은 ESP32에서 `well_index:u16`·`machine_coords[]`로 변환하며, UART payload에는 문자열을 넣지 않음. 따라서 아래 binary layout은 SiLA2 Part B의 gRPC/protobuf wire와 섞지 않음. 외부 SiLA2 command에 COBS frame이나 CRC 필드를 노출하지 않음.

**프레임 필드 폭:** `seq:u8`(방향별 순증, 래핑) · `flags:u8`(bit0 `ACK_REQ`, bit1 `ACK`, bit2 `PRIO`, bit3 `RESYNC`, 4–7 예약) · `type:u8`(아래) · `len:u16`(payload 바이트, 상한은 장비가 광고하는 `DriverMaxPayloadBytes`; `DriverMaxPayloadBytes <= 65535`, v1 초기값 `4096`) · `crc16:u16`.

**CRC:** **CRC-16/CCITT-FALSE**(poly `0x1021`, init `0xFFFF`, no-reflect, xorout `0x0000`), 대상 = `{seq,flags,type,len,payload}`(COBS 인코딩 전 원본).

**`type` 코드값** (high-bit = 방향 관례):

| 방향 | 코드 | 메시지 |
|---|---|---|
| 세션 | `0x00` HELLO · `0x01` PING · `0x02` PONG | 양방향/heartbeat |
| 하향 | `0x08` RESULT_GC · `0x09` SERVER_ADMISSION_PREPARE · `0x10` CMD_DISPENSE · `0x11` …_AND_MIX · `0x12` CMD_MIX · `0x13` CMD_WASH · `0x14` CMD_PICK_TIPS · `0x15` CMD_EJECT_TIPS · `0x16` QUERY · `0x17` PROVISION · `0x18` SERVICE_QUERY · `0x1E` CANCEL(PRIO) · `0x1F` CONTINUATION(PRIO) | §2.5 하향 |
| 상향 | `0x80` CMD_ACCEPTED · `0x81` EXECUTION_INFO · `0x82` ACTIVE_TARGET · `0x83` DISPENSE_PHASE · `0x84` PIPETTOR_POSE · `0x85` SENSOR · `0x89` SERVER_ADMISSION_ACCEPTED · `0x88` CHECKPOINT_STATE · `0x8E` RECOVERABLE_ERROR · `0x8F` CMD_RESULT | §2.5 상향 |

**payload 내부 폭/표현:** little-endian 고정. `cmd_epoch:u16` · `cmd_id:u16`(단독 식별자 아님, 항상 `cmd_epoch`와 쌍으로 사용) · `op_seq:u8`(PRIO/GC 계열 중복 적용 방지) · `recovery_seq:u8`(recoverable error 세대, stale continuation 방지) · `deck_slot:u8`(STM32 상주 캘리브레이션 인덱스, §4.1 — 라벨→인덱스와 machine 좌표 합성은 ESP32 수행) · `well_index:u16`(1536-well 인덱스 수용) · machine 좌표/VolumeMap = IEEE-754 `float32` · `uuid:16B`(RFC 4122 binary) · `owner_spki_hash:32B`(SHA-256) · `calibration_hash:32B`(SHA-256) · `payload_hash:u32`(명령 본문에서 `payload_hash` 필드를 제외한 CRC32C, 중복 수신 비교용) · 나머지 enum = `u8`.

**단위·배열 순서:** 좌표 = mm(machine-space), VolumeMap/mix volume = µL, 플런저/모션 속도 = mm/s 또는 µL/s(필드별 고정), 압력 = kPa gauge, 시간 = ms. SiLA `well_coords[]`와 driver `machine_coords[]`, `VolumeMap`, `mask`는 row-major. NaN/Inf/subnormal은 reject, -0.0은 +0.0으로 정규화 가능. SiLA2 `Real`→내부 `float32` 변환과 deck+well 좌표 합성은 ESP32에서 수행하며, STM32 safety gate에서 범위·finite 재검증.

**payload 크기 계약:** `DriverMaxPayloadBytes`는 하드웨어·펌웨어 프로파일에 따라 달라질 수 있는 장비 capability이나, `len:u16` wire 폭 때문에 단일 프레임 payload 절대 상한은 65535 bytes. v1 초기값은 `4096` bytes. 최초 장비 등록 시 ESP32가 `TransferLimits`로 `DriverMaxPayloadBytes`, `InlineMaxWells=96`, `PayloadModes={inline_v1}`, `ChunkedPayload=false`, `IdProvisioning=false` 제시. 결과 QC capability는 `ResultQcModes={pressure_qc:[not_applicable,passed,failed], source:[pLLD,TADM,seal_self_test]}`로 함께 제시. 384/1536-well 전체 좌표 inline은 v1 초기 capability 범위 밖이며, 후속 v2에서 chunked payload 또는 id-provisioning 도입 시 capability 값을 바꿔 등록.

**물리·흐름 (초기값 · bring-up 튜닝):**
- **UART = 2 Mbps, 8N1**(1 Mbps 폴백). pass-granularity + telemetry에 충분·헤드룸. 양측 DMA.
- **DMA ring:** STM32 RX/TX DMA 풀은 광고한 `DriverMaxPayloadBytes`에 header/crc, COBS overhead, 0x00 delimiter 여유를 더해 산정. `DriverMaxPayloadBytes`는 payload cap이고, COBS/DMA 버퍼 산정값은 이보다 커야 함. v1 초기값 `DriverMaxPayloadBytes=4096` 기준 TX 선형 DMA 풀은 **4608B 이상**. ESP32 UART DMA 동급.
- **credit FIFO depth = 4**(§2.4 기본). telemetry는 credit 무관(best-effort). 실측으로 2–4 튜닝.
- **`proto_ver` = `major:u8.minor:u8`**(HELLO). **major 불일치 = 링크 거부**, minor는 additive-only(양측 `min(local_minor, peer_minor)` 기능 집합으로 운용). 미지 optional 필드는 무시, 미지 required 필드는 `ProtocolFault/UnsupportedRequiredField`. ⇒ reject-on-major/negotiate-on-minor.
- **ATN GPIO 채택**(STM32→ESP32, open-drain active-low): v1 보드 필수 신호. **reliable 상향**(RECOVERABLE_ERROR/CMD_RESULT/CHECKPOINT_STATE) 대기 중 assert → ESP32가 polling 없이 즉시 read. best-effort telemetry는 **ATN 미assert**(스트림/poll).

---

## 3. ESP32-S3 구현 세부 (comms 코프로세서)

### 3.1 책임

**SiLA2 서버 ③ (임베디드 gRPC)**
-  아키텍처 구조: 장비 내 네이티브 SiLA2 서버로 동작. 스케줄러 ②는 SiLA 클라이언트로서 WiFi를 경유해 gRPC/HTTP2에 직접 접속(icd-2-3 계약 준수).
-  구현 스택: 보드 독립 SiLA protocol core(`nanopb`, upstream `nghttp2`, TLS port) + board port(`port/posix`, `port/esp32`) 구조. 호스트용 `sila_cpp` 및 Qt5는 포팅 대상에서 제외.
-  TLS 협상: TLS 1.2+ 하위 호환을 보장하며, TLS 1.3 가용 시 이를 우선적으로 협상 및 선택(§3.5).
-  노출 기능 (Feature): `SiLAService`(FDL 조회 및 서버 UUID), `LiquidHandling`, `LockController`, `CancelController`, `ErrorRecoveryService`를 외부 노출.
-  통신 모델: Observable Command(`CommandExecutionUUID` 및 `ExecutionInfo` 서버 스트림) 및 Observable Property 서비스 지원.

**디스커버리 및 보안 종단**
-  네트워크 디스커버리: `mdns_port`를 통해 `_sila._tcp` 서비스를 네트워크에 노출. SiLA Server UUID와 바인딩 처리(icd-2-3 §3). lwIP mDNS responder를 1차 기준으로 두고, ESP-IDF 네이티브 mDNS는 `port/esp32` 선택지로만 허용.
-  인증 및 보안: **mTLS + 서버 SPKI TOFU Pinning**. 장비는 자체 서명 서버 인증서/키를 제시(TLS 1.2 이상, SiLA2 표준 허용). 클라이언트(호스트 ②)는 최초 접속 시 **서버 SPKI**를 TOFU(Trust On First Use)로 핀 고정.
-  클라이언트 인증: 호스트 ②도 클라이언트 인증서를 제시. ESP32는 mTLS로 클라이언트가 해당 개인키를 보유함을 검증.
-  클라이언트 인가: ESP32는 허용된 **클라이언트 SPKI hash allowlist**만 수락. allowlist 엔트리 = `{spki_hash, role:operator|admin|service, enabled}`. 등록·교체·폐기는 `PROVISION` 경로 또는 제조/현장 provisioning 절차로 수행(정확한 운영 절차는 보안 provisioning 사양에서 확정). allowlist 미등록 클라이언트는 TLS 핸드셰이크 또는 SiLA 요청 단계에서 거부.
-  소유자 바인딩: server admission 시 현재 mTLS 클라이언트의 **client SPKI hash**를 `owner_spki_hash`로 기록. 결과 회수·continuation·cancel 권한 판정의 기준 토큰.
-  하드웨어 가속: protocol core는 TLS 라이브러리 API까지만 의존. ESP32 하드웨어 암호화 가속은 `tls_port/esp32`의 mbedTLS ALT 구현에서만 사용.

**명령 검증 및 변환 (SiLA → driver)**
-  Geometry Catalog / Liquid Profile 관리: ②가 데이터 단독 소유, ware-로컬 좌표 및 `liquid_profile`을 최종 해석 후 각 명령에 인라인(Inline) 형태로 하향 전송함(§2.5). ESP32는 catalog를 보관하지 않고 명령 단위 입력으로만 사용.
-  ESP32 검증·변환 범위: SiLA 프로토콜 및 구조적 검증(Lease, Lock, UUID ↔ `cmd_key` 매핑), 배열 shape/head mode 확인, liquid profile 수치 범위 1차 확인, deck calibration mirror와 ware-local well 좌표의 machine-space 합성, driver command 정규화. 좌표 합성은 ESP32-S3 단정도 FPU 기준 `float32`로 수행하며 `double` 경로는 두지 않음. Geometry catalog 의미 검증은 ②가 Dry-run 단계에서 최종 종단 처리함(§2.5).
-  STM32 안전 검증 범위: Catalog 의미 해석은 하지 않되, 물리 안전 게이트는 STM32가 최종 수행. soft limit, 캘리브레이션 버전/hash, machine 좌표 범위, volume 범위, 속도/가속 상한, NaN/Inf reject 통과 전 모션 금지(§2.5).
-  Deck Slot / 기기 배정 권한: ②가 배정 권한을 소유하며, 사용자가 기기 및 슬롯을 명시적 지정 가능.
-  하드웨어 정보 및 좌표 소유권: Deck 구역의 Section ID 및 좌표(캘리브레이션용) 데이터만 하드웨어 소유. 캘리브레이션 지속 권위는 STM32 FRAM이며, ESP32는 HELLO/resync로 read-only mirror를 받아 좌표 합성에 사용. ESP32는 Catalog 바인딩을 위해 Deck ID 및 Section ID를 ②에 광고(Broadcast). raw machine 좌표는 외부 ②에 제공하지 않음.
-  Slot / Container 검증: Slot 수용 제약 및 Container 호환성은 ware의 속성이므로 ②의 Catalog 소관. 따라서 Container 등록 및 container-slot 호환성 검증은 ②가 자체 Catalog를 기준으로 수행. Section ID는 장비가 광고하는 deck 식별·캘리브레이션 경계로만 사용.
-  STM32 역할: Catalog 정보에 대해 상태 비저장(Stateless) 동작. Deck calibration의 지속 권위와 machine-space safety gate만 담당. ESP32가 합성한 driver-ready 좌표를 재검증 후 실행(§4.1 / §2.5).

- **최초 접속 핸드오프 (Handoff → ②)**
-   초기 연결 제공 정보: 스케줄러 최초 연결 시 ③가 아래의 데이터 세트 제시.
    -   신원 정보: SiLA Server UUID, Server Cert / SPKI (TOFU 핀 고정 대상).
    -   기능 정의: `GetFeatureDefinition` 결과물 및 FDL (외부 노출 Feature).
    -   장비 역량 (Capability): 구동축 수, `HeadGeometry`, FRAM 탑재 여부, `TransferLimits`(`DriverMaxPayloadBytes`, `InlineMaxWells`, payload mode), `ResultQcModes`(`pressure_qc={not_applicable,passed,failed}`, source=`pLLD|TADM|seal_self_test`).
    -   하드웨어 프로파일: Deck ID, Section ID, 캘리브레이션 버전/hash (②가 자체 Deck/Ware Catalog를 바인딩하기 위한 식별자 정보, §2.3 HELLO 메시지 소스).
-   상태 정보 특이사항: ②에는 Deck ID / Section ID / 캘리브레이션 버전/hash만 제공. raw machine 좌표와 deck transform은 외부 API로 제공하지 않음. Container 등록 검증은 ②의 Catalog가 전담.
-   운용/조율 경계: 일반 운용 handoff는 `DeckId`, `SectionId`, `CalibrationVersion/Hash`, `TransferLimits`, `ResultQcModes`만 제공. raw deck transform·기준점 좌표는 hardware 조율·캘리브레이션용 service/admin path에서만 제공 가능. 해당 경로는 `admin|service` role, service mode 또는 exclusive Lock, 감사 로그, 서명된 `PROVISION` payload를 요구.
-   API surface 분리: 운용 API(task scheduler/user 경로)는 작업 배정·catalog binding에 필요한 식별자와 capability만 제공. service/admin API(기기 엔지니어 경로)는 설치·조율·캘리브레이션·진단용 raw deck layout/transform/table을 제공하며 별도 권한·service mode·감사 로그 적용.
-   예외 처리 및 규격: STM32가 리셋 복구 상태인 경우 해당 명령을 `RecoverableErrors`로 정의하여 외부 표면화(§5). 2-3 Wire 구간 통신은 icd-2-3 규격을 준수.

**비휘발성 설정 저장 (NVS)**
-   저장 항목: Server Cert / Key(자체 신원 인증용), WiFi 접속 자격 증명(Credential), 장비 고유 식별자(SiLA Server UUID), 허용 클라이언트 SPKI hash allowlist(role 포함), `cmd_epoch`.

**명령 버퍼링 (Buffering)**
-   WiFi 일시 단절 대응: 로밍 및 AP 재기동으로 인한 일시적인 통신 단절 현상을 명령 버퍼링으로 흡수.
-   하향 전송 제어: STM32의 수신 잔여 용량(Credit, §2.4 참조) 범위 내에서만 데이터 하향 전송.
-   유실 방지: 크레딧을 초과하는 데이터는 WiFi 모듈 내부의 RAM 큐에 임시 보관하여 데이터 유실 차단.

**재접속 및 동기화 (Resync)**
-   세션 재동기화: WiFi/TLS 연결 재수립 후 클라이언트 세션을 재동기화. 현재 진행 중인 `cmd_key` 및 마지막 텔레메트리(Telemetry)를 재보고.
-   물리 상태 보존: 세션 재연결 시 STM32의 물리적 구동 상태는 변경하지 않음(§5.1: ESP32 리셋은 기구부의 실제 위치에 영향을 주지 않음).
-   데이터 복구 메커니즘: SiLA 세션 상태(Lease, 구독 정보)는 ESP32 RAM에 저장되어 리셋 시 소멸. 단, server admission journal, `cmd_key` ↔ UUID 매핑, 소유자 정보, terminal record(`ok`면 `DispensedVolume` echo + `pressure_qc`, `err`면 error code)는 STM32 FRAM에 지속 저장되므로 리셋 후에도 안전하게 복구 가능. Lease 상태는 재잠금(Lock) 처리(전체 프로토콜 §5.5).

**텔레메트리 캐시 (Observable Property 저장소)**
-   상태 값 보관: Best-effort 방식으로 수신되는 운용 실시간 데이터(DispensePhase, ActiveTarget, 센서 데이터 등)의 최종값(Last-value)보관. `PipettorPose` 같은 machine-space pose는 service/admin `MotionDiagnostics` 캐시에만 보관하고 운용 observable property로 노출하지 않음.
-  SiLA 서비스 연동: SiLA Observable Command의 중간 응답(Intermediate Response) 및 Observable Property 구독 요청에 직접 데이터를 서비스(icd-3-4 §254 "서버의 최종 Phase 값 보관" 규격의 실현 지점).
-   연결 유지: 데이터 스트림은 gRPC Keepalive 메커니즘을 통해 지속 유지.


명시적 비책임:  
- stroke 타이밍·모션·센싱은 STM32 몫, §4.  
- SiLA 서버·gRPC·mDNS는 ESP32 담당.  
- 무거운 장기 저장 시스템(SQLite류) 도입하지 않음.  

### 3.2 펌웨어 태스크 구조 (ESP32 port / FreeRTOS)

| 태스크 | 우선순위 | 역할 |
|---|---|---|
| `net_task` | 중 | WiFi 이벤트, TLS 세션(≥1.2), TCP/소켓, mDNS 광고, resync 상태머신 |
| `sila_task` | 중 | **SiLA2 gRPC 서버**: HTTP/2 프레이밍·스트림, protobuf(nanopb) 인/디코드, observable command 실행·`ExecutionInfo` 스트림, Lock/Cancel/ErrorRecovery, UUID↔`cmd_key` 매핑, 구조 검증, deck+well 좌표 합성, driver command 정규화 |
| `link_task` | 높음 | UART(§2) DMA I/O, COBS/CRC, seq/ACK/재전송, credit 회계 |
| `buffer_mgr` | 중 | 명령 큐(WiFi↔UART 속도차·끊김 흡수), telemetry last-value(=observable property) 캐시 |
| `sys_task` | 낮음 | NVS, 워치독, 헬스, PING/PONG heartbeat |

- SiLA 태스크 처리 및 경계 변환 (sila_task)
**데이터 흐름 및 변환:** `sila_task`가 외부의 SiLA gRPC 요청을 내부의 §2 driver 메시지로 변환하여 `buffer_mgr` 및 `link_task`를 거쳐 하향 전송함. 반대로 하부에서 상향되는 텔레메트리(Telemetry) 및 처리 결과는 SiLA Observable 스트림 데이터로 복원(환원).
**태스크 간 통신:** `sila_task`와 `link_task` 간의 양방향 통신에는 데이터 병목 최소화를 위해 락 없는 링 큐(Lock-free Ring Queue) 메커니즘 적용.
**프로토콜 경계의 일원화:** SiLA 프로토콜과 내부 driver 메시지 간 상호 변환은 오직 `sila_task`에서만 집중 수행. 이에 따라 UART 레이어 너머로는 사전에 정의된 driver 부분집합 데이터만 엄격히 격리되어 전송(설계 원칙 2 준수).

### 3.3 메모리 구조 및 관리
-   **NVS 파티션 구성:** `certs`(서버 자체 신원 인증용 인증서 및 개인키), `wifi`(WiFi 접속 정보), `ident`(SiLA Server UUID), `clients`(클라이언트 SPKI hash allowlist + role), `cmd_epoch`를 저장함. Production 이미지는 Flash Encryption + Secure Boot v2 필수. 미활성 구성은 bring-up/dev-only로 제한하며 field 배포 금지. 기존 `pins` 필드는 아키텍처 방향 역전으로 인해 폐기됨(§3.1).
-   **Flash 메모리 관리 (FDL 저장):** `SiLAService.GetFeatureDefinition` 대응용 FDL XML 데이터 포함. 단, Geometry Catalog 및 Liquid Profile은 ESP32 내부에 보관 안함(② 소유 및 명령 인라인 전송 원칙, §2.5). Deck 캘리브레이션의 지속 권위는 STM32에 있으며(§4.1), ESP32는 좌표 합성을 위한 read-only mirror와 ② 광고용 Deck ID / Section ID / calibration version만 보유함.
-   **PSRAM 확장 및 활용:** gRPC/HTTP2 버퍼 관리, 다중 스트림 상태 유지, TLS 레코드 처리를 위해 내장 SRAM과 외부 PSRAM을 병행하여 필수적으로 확장 및 사용함.
-   **명령 큐 RAM 산정:** 개별 명령의 최악 조건 페이로드(Payload)를 약 수 KB로 산정함(예: 96-well × 좌표 3 float + VolumeMap 1 float). 최종 큐 깊이(Depth)는 'WiFi 최대 순단 시간 × 명령 유입률' 공식으로 산정하며, 브링업(Bring-up) 단계에서 실측을 통해 확정함(초기 설계값은 8–16개 명령분 예약).
-   **텔레메트리 캐시:** 운용 경로는 명령(Command)별 Phase, Target, 센서 데이터를 저장하기 위한 정적 크기의 최종값(Last-value) 슬롯으로 구성 및 관리. machine-space Pose는 service/admin `MotionDiagnostics` 캐시로 분리.

### 3.4 부팅 시퀀스 (Boot Sequence)
1.  **초기화 및 네트워크 수립:** NVS에서 서버 인증서, 개인키, 환경 설정을 로드한 후 WiFi 접속. 이후 TLS 서버 소켓 바인딩(TLS 1.2 이상 준수, §3.5).
2.  **하드웨어 역량 파악:** UART 통신의 **HELLO** 메시지(§2.3)를 통해 STM32 하드웨어의 역량 데이터(구동축, 헤드, FRAM 유무, 펌웨어/캘리브레이션 버전/hash, deck calibration mirror)를 취득함. 이를 기반으로 SiLA `LiquidHandling` 및 `HeadGeometry`에 노출할 최종 피처 값과 ESP32 좌표 합성 테이블 확정.
3.  **서비스 광고 및 핸드오프:** FDL 로드 상태를 확인한 후, `mdns_port`를 통해 `_sila._tcp` 서비스(SiLA Server UUID 바인딩)를 네트워크에 광고함. 스케줄러(gRPC 클라이언트) 접속 수락을 개시하며, 접속 시 최초 핸드오프 세트(신원, FDL, 역량 정보, Deck ID, Section ID)를 ②에 제시함(§3.1).
4.  **예외 처리 및 크레딧 활성화:** STM32가 리셋 복구 상태(§5)로 확인될 경우, 서버는 해당 명령을 **`RecoverableErrors` 상태로 표면화**하여 클라이언트(스케줄러)가 지속 여부를 결정하도록 유도함(자동 재개는 §5 정책 적용). 정적 상위 상태가 정상인 경우 STM32 크레딧(Credit)을 개방하여 명령 수신 및 실행.

### 3.5 SiLA2 서버 스택 및 브링업 트랙 (E 프로파일)
-   **설계 원칙 및 리스크 격리:** 호스트 PoC(layer3-device §PoC, sila_cpp)의 Embedded profile 규격으로 경량화 및 이식(신규 구현). gRPC 서버를 마이크로컨트롤러(MCU) 환경에 신규 임베디드 형태로 구현하기에, 구현 리스크를 철저히 격리하고 단계별 순차 검증 기법 채택(호스트 PoC 단계에서 클라이언트 및 C++ 리스크를 상호 분리한 설계 원칙과 동일 적용).

**스택 결정 (substrate):**

| 층 | 선택 | 성숙도·리스크 |
|---|---|---|
| HTTP/2 | **upstream `nghttp2` core** | ESP-IDF 컴포넌트 wrapper에 의존하지 않음. 서버 모드·HPACK·trailer 처리는 POSIX Spike에서 먼저 검증 |
| protobuf | **nanopb** | plain C core. board port 불필요 |
| TLS | **mbedTLS upstream primary**, wolfSSL secondary profile | **TLS ≥1.2 협상, 1.3 opportunistic** + **mTLS + 서버 SPKI TOFU Pinning + 클라이언트 SPKI allowlist**. core는 TLS port만 호출. ESP32 HW crypto ALT는 `port/esp32` 전용 |
| TCP/IP | **BSD socket compatible `net_port`** | POSIX = native socket, ESP32 = lwIP socket. core는 WiFi/ESP-IDF event API 직접 호출 금지 |
| discovery | **`mdns_port`** | lwIP mDNS responder 1차. ESP-IDF native mDNS는 ESP32 port 선택지. POSIX 검증은 mDNSResponder/Avahi 계열 adapter 허용 |
| gRPC 프레이밍 | **자체 구현**(upstream `nghttp2` 위) | **임베디드 gRPC 선례 부족 = 핵심 리스크** |
| SiLA2 시맨틱 | observable command/property·metadata·framework error | gRPC 매핑, 컨포먼스는 실 클라이언트로 게이트(공식 `sila2`, 아래) |

**보드 독립 포팅 경계:**
- `core/`: SiLA2 FDL dispatch, gRPC message prefix, HTTP/2 stream state, protobuf encode/decode, UUID·Lock·ErrorRecovery, admission control. ESP-IDF/FreeRTOS header include 금지.
- `net_port`: listen/connect/read/write, ALPN socket binding, peer address. POSIX socket과 lwIP socket 모두 수용.
- `tls_port`: certificate/key load, mTLS verify callback, SPKI hash extract, RNG hook, TLS record I/O. mbedTLS와 wolfSSL 프로파일 교체 가능.
- `mdns_port`: `_sila._tcp` advertise, TXT record(Server UUID/SPKI hint), start/stop/update.
- `os_port`: task/thread, mutex, queue, monotonic clock, watchdog yield. FreeRTOS와 POSIX pthread 모두 수용.
- `storage_port`: NVS/flash/파일 기반 KV. certs·clients·cmd_epoch namespace 동일.
- `uart_port`: ESP32↔STM32 링크용 DMA/UART I/O. COBS/CRC/seq/ACK state machine은 portable C core에 유지.
- 포팅 완료 기준: `core`가 POSIX CI에서 `nghttp2`+TLS stub+nanopb로 unary/observable 계약 테스트 통과 후 `port/esp32` 결합.

**준거 규격·레퍼런스 구현:** SiLA 2 준거, 컨포먼스·interop 레퍼런스 클라이언트 = 공식 `sila2`(Tecan/wega 유지, gitlab.com/SiLA2, MIT). 오케스트레이터 ②가 이 구현 기반이라 장비 서버는 공식 `sila2` 컨포먼스에 정렬(2-3 interop 대상 = ②). 버전 pin 권장(예: 0.14.x) — 공식 `sila2`는 유지보수 전용(frozen)이나 컨포먼스 오라클로는 **안정 표적이라 오히려 이점**. UniteLabs `unitelabs-sila`(활발·SiLA 2.1.1)는 **미채택** — ② interop 대상이 아님(둘 다 MIT라 라이선스 무관).

**gRPC 최소 계약 (자체 구현 시 클라이언트에 거부될 수 있는 지점 = 스파이크 통과 기준):**
- DATA 프레임 내 **5바이트 메시지 프리픽스**(1B 압축 플래그 + 4B big-endian 길이).
- **`content-type: application/grpc`**.
- **`grpc-status`는 HTTP/2 트레일러**(초기 헤더가 아니라 DATA 뒤 HEADERS+END_STREAM) → `nghttp2_submit_trailer` 왕복 검증. 트레일러가 전형적 실패 부분.

**bring-up 래더 (리스크 순):**
- **Spike -1 — POSIX protocol core.** `core`를 Linux/POSIX에서 먼저 빌드. `nghttp2` + TLS stub + nanopb로 unary echo, trailer, observable stream state machine 검증. ESP32 port 결합 전 board dependency 유입 차단.
- **Spike 0 — TLS/전송 실측.** `tls_port`의 mbedTLS mTLS 핸드셰이크로 **실제 협상된 TLS 버전**·ALPN `h2`·상호인증·클라이언트의 서버 SPKI Pin 확인·ESP32의 클라이언트 SPKI allowlist 거부/수락 확인(정책은 1.2 베이스라인 확정, 스택표 §3.5 — 여기선 협상 결과 확인·1.3 취득 여부만 정보성).
- **Spike 1 — gRPC unary echo (h2c 평문 먼저).** upstream `nghttp2` 위에 자체 gRPC framing + nanopb, `grpcurl`/공식 `sila2` 클라이언트 호출. **TLS와 분리(h2c)** → 실패 원인이 gRPC framing인지 TLS인지 구별 가능. 통과 = 위 5B 프리픽스·content-type·트레일러 왕복.
- **Stage 1 — SiLAService(unary) + 실 클라이언트 conformance 게이트.** mDNS 광고 후 공식 `sila2` 클라이언트가 발견·`GetFeatureDefinition`(FDL)·서버 UUID·unary 호출. 호스트 PoC "unary gate" 대응 — **실 클라이언트로 SiLA2 비표준 조기 포착.**
- **Stage 2 — Observable Command & Property 구현 (리스크 집중 단계)**
   - 구현 범위: `LiquidHandling` 내 Observable Command(`CommandExecutionUUID` 및 `ExecutionInfo` 스트림)와 개별 Observable Property에 대한 구독 기능 1개를 구현.
   - 자원 및 제어 구조: Long-lived HTTP/2 스트림과 실시간 텔레메트리 캐시(§3.1) 메커니즘을 연동하여 운용.
   - 검증 목표: 호스트 PoC 단계에서 완료된 'Observable 스트리밍 기능'을 임베디드 환경으로 이식하여, 장시간 스트림 유지에 따른 메모리 누수 및 통신 안정성 리스크를 최종 검증.
- **Stage 3 — 다중 클라이언트 + 동시성 캡(icd-2-3 §72).** N개 클라이언트/스트림, 캡·백프레셔, 스트림당 PSRAM/힙 실측 → 캡 숫자 확정.
- **Stage 4 — 풀 피처·라이프사이클.** LockController·CancelController·ErrorRecoveryService, ESP32 리셋 후 세션 resync = §5.5에서 설계 확정(lifetimeOfExecution durability window, cmd_key↔UUID·owner·terminal record FRAM 지속, lease 재Lock).

- **교차 리스크 관리 및 자원 배치**
     - 프로토콜 처리 리스크: 신규 구현하는 gRPC 프레이밍(Framing) 및 트레일러(Trailer) 처리 과정의 오버헤드 검증.
     - 메모리 자원 제약: 개별 스트림당 소요되는 메모리를 분석하여 최대 수용량(Cap) 한계치 산정.
     - 태스크 스케줄링 최적화: 고부하 gRPC/TLS 연산 작업이 최우선순위인 `link_task`(§3.2)의 CPU 자원을 선점(Starvation)하지 않도록, 전용 CPU 코어 할당 및 정밀한 태스크 우선순위 배치 적용.
     - 보드 종속성 차단: `core` 하위에서 ESP-IDF, FreeRTOS, HAL, WiFi driver, NVS header 직접 include 금지. 예외는 `port/esp32`와 board bring-up 테스트에만 허용.

### 3.6 SiLA 서버 운영 파라미터 확정
-  **실행 수명(lifetimeOfExecution) 관리:** 명령 실행 중에는 수명을 지속적으로 갱신하며, 종료(Terminal) 상태 이후 자원 회수 유예 시간(Tail)은 300초(초기 제안값, PROVISION 파라미터로 조정 가능)로 설정. 96-well 분주 등 장시간 작업 시 수명 만료로 인한 오류(`InvalidCommandExecutionUUID`)를 방지하기 위해, 실행 중 서버가 `updatedLifetimeOfExecution` 데이터를 주기적으로 Push. 종료 이후의 300초는 연결이 끊긴 클라이언트가 결과물(UUID/Result)을 회수할 수 있도록 보장하는 유효 창 역할을 하며, 이 불변 수명은 32KB FRAM 영역-B 링 버퍼(16개 이상 결과물 수용, §4.8)의 저장 범위를 초과할 수 없음. 시스템 재부팅 시간(~10초)은 이 유예 시간에서 자동 차감(§5.5).
-  **결과 링 server admission precheck:** ESP32는 `CommandExecutionUUID` 반환 전 STM32가 보고한 FRAM 영역-B `result_ring_free`와 자체 예약 슬롯을 대조. `free - reserved < 1`이면 새 observable command를 server admission 단계에서 `ResourceExhausted`/busy로 즉시 거부(UUID 미발급). 이 단계는 외부 UUID 반환 전 자원 예약 검증이며, driver durability 성립이 아님. 이미 광고한 terminal tail은 임의 단축 금지. 회수 조건은 terminal lifetime 만료뿐.
-  **server admission journal:** precheck 통과 후 ESP32는 UUID를 클라이언트에 반환하기 전에 STM32 FRAM 영역-B에 `{cmd_key, uuid, owner_spki_hash, payload_hash, state=server_admitted_not_dispatched}`를 reliable로 먼저 기록시킴(§2.5/§5.5). 기록 성공 전에는 UUID 반환 금지. 이 상태는 driver FIFO 삽입 전이므로 ESP32 리셋 후 발견 시 **미실행 확정**이며, lifetime 내 Info 조회는 `finishedWithError(NotDispatched)`로 replay. `Result(UUID)`는 DispenseResult 없이 표준 오류. 실제 CMD 수신·검증 후 STM32가 같은 레코드를 `driver_accepted`로 전이하고, 그때부터 driver admission/durability 성립. STM32 driver admission/persist 시점에 링 불일치가 발견되면 실행 전 terminal err(`ResourceExhausted`)로 표면화하고 모션 금지.
-  **결과 GC 메커니즘:** 외부 2-3 경계에 consume ACK API를 두지 않음. `Result(UUID)` 회수, gRPC delivery ACK, 클라이언트 영속 저장 완료 여부는 FRAM 영역-B 회수 조건이 아님. terminal lifetime이 만료되면 ESP32가 내부 하향 reliable `RESULT_GC{cmd_key,op_seq}` 프레임(§2.5/§2.6)으로 STM32에 통지하고 해당 terminal record를 GC. tail 만료 전에는 성공 Result 또는 실패 terminal 상태 replay 가능.
-  **Observable 스트림 유지 및 데이터 동기화:** 유휴 상태의 Observable 스트림은 HTTP/2 PING 메커니즘을 통해 약 20초 주기로 유지(gRPC keepalive). 클라이언트가 구독을 개시하면 텔레메트리 캐시의 최종값(Last-value)을 즉시 서비스, 첫 신선 데이터가 수신되기 전까지는 기존 데이터를 오래된 상태(Stale)로 표기. 이를 통해 gRPC 스트림 수명 주기와 UART 프레임 수신 주기(§2.2 best-effort)를 상호 분리(Decouple)함. 스트림은 내부 캐시를 참조하고, 캐시는 §2.2 상향 통신을 통해 실시간 갱신.
-  **FDL 데이터 서빙:** FDL XML 데이터는 Flash 파티션에 보관(§3.3), `SiLAService.GetFeatureDefinition` 요청 발생 시 Flash에서 Chunk-unit Streaming 방식으로 분할 전송하여 PSRAM 전량 적재에 따른 메모리 낭비를 방지.
-  **다중 클라이언트 수용량 제안 (Stage 3):** 초기 운영 기준은 최대 클라이언트 4개, 동시 스트림 8개로 제한함. Stage 3에서 스트림당 소요되는 PSRAM 및 힙(Heap) 메모리를 실측한 후 최종 확정함(§3.5). 이 제한은 HTTP/2 `SETTINGS_MAX_CONCURRENT_STREAMS` 설정 및 최대 연결 수 제한 기능을 통해 강제하며, 초과 요청은 백프레셔(Backpressure) 메커니즘으로 거부 처리함.
-  **큐 및 캐시 크기 사양:** 명령 큐 깊이(Depth)는 초기 8~16개 레코드로 예약하며(§3.3), 브링업 단계에서 WiFi 일시적 연결 단절 통계를 기반으로 최적화. 텔레메트리 캐시는 명령(Cmd)별 정적 고정 슬롯으로 관리하여 동적 메모리 할당으로 인한 비대화 방지(§3.3).
-  **데이터 보안 (At-Rest 암호화):** `certs`(서버 인증서/개인키), `wifi`(접속 정보), `ident`(Server UUID), `clients`(클라이언트 SPKI hash allowlist + role), `cmd_epoch` 파티션을 대상으로 Flash Encryption 및 Secure Boot v2를 전면 적용하여 기기 내부의 데이터를 보호함. 특히 `certs`와 `clients` 파티션은 필수 암호화 대상으로 지정.
-  **브링업 실측 및 튜닝 항목:** gRPC/HTTP2 버퍼 및 다중 스트림 상태 관리를 위한 PSRAM 실제 사용량(§3.3), TLS 핸드셰이크 지연 시간, ESP32 하드웨어 암호화 가속 엔진의 실제 효율을 측정. 이를 바탕으로 mbedTLS 빌드 프로파일(지원 암호군, 레코드 버퍼 크기)을 브링업 단계에서 최종 확정.

## 4. STM32F446 구현 세부 (motion / hard-RT)

### 4.1 책임

- **pass 명령 실행.** `CMD_DISPENSE`류(§2.5) 수신 → **stroke 분해**(원칙 3) → 6축 모션·플런저 시퀀스.
- **다축 step/dir 생성.** X,Y,Z1,Z2,P1,P2 펄스를 타이머+DMA로 생성. **드라이버 혼용(§4.3.1):** Z/P축 = **TMC2209**(UART, 마이크로스텝·전류·StallGuard 센서리스 홈잉·접촉감지), X/Y축 = **TMC2208**(보유분, standalone, 엔드스톱 홈잉).
- **센싱 — 압력 기반(pLLD + TADM).** 유로의 **압력 트랜스듀서**로 (a) 액면 검출(pLLD, Z-vs-액면), (b) 흡입/분주 압력 모니터링(TADM — 클롯·숏샘플·기포·분주 QC), (c) 잔량 판정. 압력 변화가 작아 **디지털 출력(SPI/I²C) 고분해능 센서 권장**(12-bit ADC 노이즈 우회; 부품 후보 §4.3.3). 접촉/충돌·바닥 기준은 TMC2209 **StallGuard**(센서리스) 겸용. 팁터치(벽)는 geometry 좌표 기반 open-loop이라 센서 불요.
- **채널 배치.** ganged 8채널은 **단일 플런저·공유 유로**라 압력 라인 **1개(매니폴드 평균)**, 1채널 별도 **1개** = 2 라인. 공유 라인은 8팁 개별 액면 판별 불가지만 **열 균일 강제**(§2.5)로 동시 접촉 전제라 무방.
- **FRAM 체크포인트.** 물리 논리 상태를 주요 전환마다 기록 — **복구 원장의 권위**(§5).
- **telemetry 발행.** DispensePhase·ActiveTarget·progress·pose·센서를 best-effort 상향(§2.2).

명시적 비책임: 네트워크·보안·geometry catalog·liquid profile·SiLA 의미론은 **모름**. Deck calibration은 지속 저장하되 좌표 합성은 ESP32가 read-only mirror로 수행. STM32는 UART로 받은 `machine_coords[]`를 물리 한계 기준으로 재검증 후 실행. slot 수용 제약·container 스펙은 ware 속성이라 미보유(② catalog).

### 4.2 펌웨어 아키텍처

```
[USART DMA ↔ ESP32] → 명령 파서 → 얕은 명령 FIFO(depth 2–4)
                                      │ (single-writer)
                                      ▼
                            모션 시퀀서 (stroke 분해)
                        ┌───────────┼────────────┐
                     step 엔진     플런저      팁 핸들링
                   (TIM+DMA/축)   (P1/P2)    (pick/eject)
                        │           │
                        ▼           ▼
                   TMC2209 UART   압력센서(pLLD+TADM, SPI/I²C)
                        │
                   FRAM writer(전환마다) ─── CHECKPOINT_STATE
                        │
                   telemetry emitter(best-effort) → USART
```

- **모션 시퀀서**가 유일한 single-writer(§2.4 credit이 이를 반영). PRIO(CANCEL/CONTINUATION)만 FIFO 선점(§2.4/§5).
- step 엔진: 축별 타이머 채널 + DMA로 CPU 개입 없이 펄스열 생성(가감속 프로파일 테이블). 가속/저크는 stroke 분해 단계에서 산출.
- **pLLD 검색 모션 모드**: 액면 탐색 시 Z를 **느리고 일정한 속도로 하강**시키며 압력 **기울기(derivative)** 로 액면 돌파를 검출 → 그 Z를 wet/submerged 분주 기준. 일반 step 프로파일과 별개 모드(홈잉 StallGuard와도 별개). **공압 밀폐(노즐-팁 seal)가 신호 품질 좌우** — 팁 장착력 설계와 직결.

**모션 프로파일 파라미터 (방법 확정 · 수치 bring-up 실측):**
- **가감속 프로파일:** XY 겐트리 = **사다리꼴(trapezoidal)**, **플런저(P1/P2) = S-curve(저크 제한)** — 급가속의 압력 트랜지언트가 TADM/계량을 오염시키므로 jerk-limited 필수. Z = 사다리꼴(홈잉·pLLD 강하는 별개 모드). 파라미터(축별 a_max·j_max)는 stroke 분해 단계에서 산출, **초기값 보수적**(P1은 §4.3.2 토크-속도 droop 캡에 따라 가용토크 ≥ 3× 부하가 되는 속도로 제한) → bring-up 실측 재교정(홈잉 StallGuard 임계 §4.6 포함).
- **pLLD 강하 초기값(실측 게이트):** 하강 속도 **2 mm/s**(느린 준정적, 소구경 웰 헤드룸 확보), 압력 샘플 **~1 kHz**(§4.3.3 로컬 read), 액면 검출 임계 = **dP/dt > 3× RMS 노이즈 플로어**(§4.3.3 게이트의 미분 헤드룸 소비, 10 ms 창). 소구경(384/1536) 한계·최종 속도/임계는 실측(bring-up 잔여) — 방법·초기값만 확정.

### 4.3 주변장치 자원 예산 (핀 확정 전 — fit 검증)

F446이 요구 자원을 담을 수 있는지 **개수 기준**으로 확인(정확한 핀/스트림 배정은 bring-up):

| 기능 | 요구 | F446 가용 | 상태 |
|---|---|---|---|
| step/dir 6축 | 6× 타이머 채널(스텝 펄스) + 6 DIR GPIO | TIM1/2/3/4/5/8 등 다수 채널 | 여유 |
| step DMA | 축당 1 DMA 스트림(펄스열) | DMA1/DMA2 = 16 스트림 | 여유(타이머-스트림 매핑은 RM 대조 필요) |
| TMC2209 제어 (Z1,Z2,P1,P2) | 1× UART(주소지정, 4개/버스) | USART/UART 다수 | OK — 4개가 정확히 1버스(§4.3.1) |
| TMC2208 (X,Y, 보유분) | UART 미사용 **standalone**(VREF·핀 스트랩) | — | 링크·TMC2209 UART 무부담 |
| 엔드스톱 | X,Y(+옵션 Z) 리밋 스위치 → GPIO 입력 | GPIO 다수 | 여유(§4.3.1) |
| ESP32 링크 | 1× USART full-duplex(§2) | 별도 USART 1개 전용 | OK |
| FRAM | 1× SPI **FM25V02A-G**(1차)/**MB85RS256B**(2차) 32KB | SPI 3개·I²C 3개 | 여유. 원 FM25V02 EOL→후속 드롭인, §4.8 |
| 압력 센싱(pLLD+TADM) | **디지털 압력 센서 2× (gang 1 + single 1)** — MS5525DSO/ABP2급 24-bit gauge, §4.3.3 (P1은 1개) | SPI 3개·I²C 3개(FRAM과 버스 공유 가능) | 여유. 아날로그 센서면 ADC×3로 폴백 |
| 아날로그 out(옵션) | DAC | DAC×2 | 여유, **§4.4 배선 주의** |
| FPU/DSP | 가감속·필터 실수 연산 | Cortex-M4F FPU | OK |

결론: **단일 F446으로 6축 + 링크 + FRAM + 센싱 수용 가능.** TMC2209가 마이크로스텝을 오프로드하므로 step 레이트도 감당.

### 4.3.1 드라이버·모터 배정 (실 부품 · 단계적 빌드)

**설계 타깃은 6축, 주 드라이버는 TMC2209**(StallGuard4로 센서리스 홈잉·접촉/클롯 감지). TMC2208은 StallGuard가 없어(센서리스 홈잉·stall 감지 불가) **접촉 감지가 필요 없는 자유공간 축에만** 쓰고 홈잉은 엔드스톱으로 규정. TMC2208은 UART 주소지정도 없어 개별 어드레싱 불가 → **standalone**(핀 스트랩·VREF 전류)로 운용.

| 축 | 드라이버 | 홈잉 | StallGuard 용도 |
|---|---|---|---|
| X, Y (겐트리) | **TMC2208** (보유) standalone | **엔드스톱 스위치** | — (자유공간, 접촉 감지 불요) |
| Z1, Z2 | **TMC2209** | StallGuard 센서리스 | 바닥/덱 크래시·홈 |
| P1, P2 (플런저) | **TMC2209** | StallGuard 센서리스(하드스톱) | stall=클롯/막힘(압력 TADM 보완)·플런저 제로 |

- **UART 버스:** TMC2209 4개(Z1,Z2,P1,P2) = **1개 주소지정 UART 버스**(MS1/MS2로 addr 0–3, 정확히 4개 → 딱 맞음). TMC2208(X,Y)은 UART 미사용 standalone이라 이 버스·링크 UART에 부담 없음.
- **엔드스톱(방식 확정):** TMC2208은 StallGuard 부재로 접촉 감지가 원천 불가 → X/Y는 **기계식 microswitch**를 축 끝단에 두고, 부팅 시 그쪽으로 밀어 접점을 눌러 **절대 원점(홈)**을 확립. GPIO 입력(디바운스). 접점 반복정밀도(수십 µm급)가 원점 정밀도를 좌우하므로 정밀 요구 시 광학 슬롯 센서로 동일 인터페이스 교체 가능. **NC(normally-closed) 배선**으로 단선·커넥터 탈락을 상시 트리거로 처리(fail-safe). 반대편 오버런은 소프트 리미트로 대체(홈 스위치 1개/축 기준). StallGuard 축(Z/P)은 엔드스톱 불요이나, 안전 대비 Z에 물리 리밋을 옵션으로 둘 수 있음. **기계식 엔드스톱 원점 검출은 CNC·산업 로봇 수십 년 공지 기술이라 특허 제약 없음.**
- **bring-up 잔여(실측/확정):** 엔드스톱 디바운스 시간·GPIO 핀(§4.7), TMC2208(X/Y) standalone **VREF 전류·마이크로스텝 스트랩 값** 확정.

**빌드 단계 (Z2/P2/multi8 placeholder는 구조·코드로 유지):**

| 단계 | 활성 축 | 드라이버 | 부품 출처 | 비고 |
|---|---|---|---|---|
| **P1. 단일채널 프로토타입** | X, Y, Z1, P1 (4축) | **TMC2208 ×4 (전량 보유)** + 엔드스톱 | 보유 부품만 | StallGuard 없음 → 홈잉·접촉 전부 엔드스톱/오픈루프. Z2·P2·multi8·pLLD-StallGuard 겸용은 placeholder |
| **P2. 6축 풀빌드** | + Z2, P2 (single→multi8) | Z1,Z2,P1,P2 → **TMC2209 ×4 (구매)**, X,Y → TMC2208 유지 | TMC2209 4개 구매 | 센서리스 홈잉·접촉/클롯 감지 활성. §2.5 multi8 활성화 |

**모터 배정(보유분):** **17HS4401**(1.7A, ~40 N·cm, 강) → **부하 최대 축**(겐트리 중 무거운 쪽). **17HS4023**(23mm 숏바디, ~0.7A, ~9–14 N·cm, 약) ×3 → 나머지(P1, Z1, 겐트리 경축). 토크 마진은 §4.3.2에서 정량 확인 — **P1 프로토타입은 여유(4.6×)**, 유일 임계는 **P2 ganged**(풀빌드 시 강 모터 필요).

### 4.3.2 토크 예산 (모터 → 플런저/Z 직선력)

리드스크류 변환 $F = 2\pi \cdot T \cdot \eta / L$ (T=가용 동토크, η=스크류 효율, L=lead). 가용 동토크 = 홀딩의 ~50%(속도 droop·전류 헤드룸 보수 반영): 17HS4023 ≈ **0.05 N·m**, 17HS4401 ≈ **0.20 N·m**.

**리드스크류 가용력** (Tr8):

| 스크류 | lead각 | η | 백드라이브 | 17HS4023(0.05) | 17HS4401(0.20) |
|---|---|---|---|---|---|
| Tr8×8 | 20° | 0.60 | **가능**(정전 낙하) | 24 N | 94 N |
| **Tr8×2** | 5.2° | 0.35 | **자기잠금**(λ<φ) | **55 N** | 220 N |
| lead 1mm | 2.6° | 0.30 | 자기잠금 | 94 N | — |

**요구력 vs 마진** (Tr8×2 = 17HS4023 55 N 기준):

| 축 | 구성 | 요구력(worst) | 마진 | 판정 |
|---|---|---|---|---|
| P1 플런저(1ch) | 압력분 대기압상한 ~1.7 N + 실링마찰 ~10 N | ~12 N | **4.6×** | ✅ 여유 |
| Z1 승강(단일헤드) | 헤드 0.8kg 중력 7.9 + 가속 1.6 + 마찰 2 | ~12 N | **4.6×** | ✅ 여유·자기잠금 |
| **P2 ganged 8ch** | 8×(압력 1.7 + 마찰 10) | **~93 N** | **0.6×** | ❌ **부족** |

**결론:**
- **P1 단일채널 = 정적 힘 무문제.** 공기치환 흡입은 대기압(~101 kPa)에 물리 상한이라 압력분 <2 N, **마찰이 지배**하고 그마저 4.6× 여유. 17HS4023으로 충분.
- **진짜 제약은 정적 힘이 아니라 토크-속도 droop.** 숏바디 저인덕턴스 모터는 스텝율↑ 시 back-EMF로 토크가 일찍 꺾임. **P1은 StallGuard 없음(TMC2208) → 탈조 무음** → 플런저/Z **속도를 보수 캡**(가용토크 ≥ 3× 부하 구간). 약한 모터는 **능력이 아니라 처리량(속도) 제한**.
- **P2 ganged 8채널 = 힘-임계 축(0.6×).** 8실린지 마찰 누적. 풀빌드 추가구매 모터 중 **강 모터(17HS4401급/기어드)를 P2에 배정**하거나 lead≤1mm+저속. 약 모터 배치 금지. (**두 번째 P2 힘-임계 = Z2 8팁 동시 픽업력 80–240 N**, §4.3.4 — 순차/캠/고력으로 별도 해결.)
- **리드 선택 부수효과:** Tr8×2 이하는 자기잠금 → **정전 시 Z 낙하 없음**(브레이크 불요). Tr8×8은 백드라이브 → Z 부적합.
- 가정치(실린지 ID 4.6mm/1mL급, 실링마찰 ~10 N, 헤드 0.8kg, η)는 실기구 확정 시 재교정 대상(bring-up 잔여).

**P2 ganged 모터 후보** (목표 3× 마진=설계력 ~280 N). 제약 두 개가 후보를 좁힘: **① TMC2209 전류 한계 ~2A peak**(초과 시 TMC5160 필요 → "TMC2209 4개=1버스" 균일 설계 §4.3.1 붕괴), **② 기어박스 백래시=계량 오차**(흡입↔분주 반전 시 볼륨 오차 → 계량축 부적합).

| 방식 | 대표 부품 | 전류 | 가용력(Tr8) | 마진 | 판정 |
|---|---|---|---|---|---|
| **① Tr8×1 리드 감속 + 보유급** | 17HS4401 재구매 | **1.7A** | ~377 N | **4.0×** | ⭐ **1순위** — 신모델 불요·TMC2209 이내·버스 균일·기어 무. 대가=플런저 최고속 반감(ganged 벌크라 수용) |
| **② 대형 NEMA17 직결(Tr8×2)** | 17HS8401(48mm) | 1.8A | ~290 N | 3.1× | ⭐ 2순위 — 속도 유지, 전류 한계선(방열) |
| NEMA23 직결 | 23HS22-2804S | 2.8A | ~700 N | 7.5× | ❌ TMC2209 초과→TMC5160·무거움 |
| 기어드(PG5) | 17HS+5.18:1 | — | 매우 큼 | 8×+ | ❌ 백래시 ≤1.5°→계량 오차 |

- **권장: 1순위(Tr8×1 리드 감속) — 보유 17HS4401을 하나 더 구매**하고 P2 스크류만 lead 1mm로. §4.3.1 균일 버스·전류·기어무 설계 무손상.
- 어느 안이든 **플런저 스크류엔 안티백래시 너트 필수**(방향 반전 볼륨 정확도).

**lead 확정:** **P2 플런저 = Tr8 lead 1 mm**(1순위 리드 감속, ~377 N·4.0×). **P1 플런저 = Tr8×2**(55 N·4.6× 여유, §4.3.2 토크 예산). **Z1·Z2 = Tr8×2**(λ<φ 자기잠금 → 정전 시 Z 낙하 없음·브레이크 불요, §4.3.2 결론). **17HS4401(강) 배정 축 = 부하 큰 겐트리 축 — 기구 질량 분포 확인 후 확정**(현 단계 미결, 실기구 종속). 안티백래시 너트 = P1·P2 스크류 소싱 항목(bring-up 잔여).

### 4.3.3 압력 센서 선정 (pLLD + TADM)

라인당 **24-bit 디지털 gauge/compound 압력 센서 1개** — 디지털 출력으로 §4.1의 "12-bit ADC 노이즈 우회" 의도 실현. 후보:

| 후보 | 부품 | 인터페이스 | 분해능 근거 | 판정 |
|---|---|---|---|---|
| **①** | **TE MS5525DSO** | SPI+I²C(PS핀), 1 ms 변환 | 24-bit ΔΣ, gauge/compound/diff, 1–30 psi. I²C 주소 2개(CSB) → 2라인 딱 | ⭐ 1순위 — gauge 변형 재고(예 `5525DSO-SB001GS`) |
| **②** | **Honeywell ABP2** | I²C/SPI, ~200 Hz | 피에조 실리콘 sealed-diaphragm, 24-bit, ±0.25%FSS BFSL, 1 psi gauge 재고 다수 | 비교·폴백 후보 |

**기준형 = gauge/compound(양방향), absolute 아님.** 대기 기준 포트 개방. 흡입은 대기 이하(부분진공)라 **양방향(compound) 필수** — 0→FS 단방향 vented-gauge는 흡입 TADM을 못 잡음. absolute 배제 이유(정확히): 분해능을 0→대기 오프셋에 낭비 + 기압 보정 필요(부호 문제가 아님).

**⚠️ 범위↔분해능 = 이 선정의 핵심 트레이드, 그리고 단일 센서 pLLD 적정성은 bring-up 검증 사항(미확정).**
- pLLD 메니스커스 이벤트는 ~수 mbar(수백 Pa). **±1–2 psi(±7–14 kPa) 양방향**이면 pLLD + 정상 흡입 TADM을 고분해능으로 잡고, 하드 클롯은 레일(포화=클롯 플래그, 무방). **±5 psi(±34 kPa)**는 클롯 프로파일 전체를 담으나 소신호 분해능↓ → **저범위부터** 권장.
- **24-bit raw ≠ 사용가능 24-bit.** 선택 범위·OSR에서 **noise-free 분해능이 ~100 Pa보다 충분히 낮고 미분(derivative)용 헤드룸**이 있어야 단일 센서로 pLLD가 성립. 데이터시트 RMS 노이즈로 **실측 게이트**(아래 RMS 노이즈 게이트 절차, bring-up 잔여) — 센서가 메니스커스를 "분해한다"고 여기서 단정하지 않음.

**배치:** ganged 8ch = 공유 매니폴드 1라인(§4.1 열균일 강제) + 1ch 1라인 = 2 센서. **P1 빌드 = P1 라인 1개만, P2 풀빌드에서 +1.**

**버스:** SPI(결정적·주소충돌 무) 2 CS, 또는 I²C 2주소(MS5525 CSB=0x76/0x77 → 2라인 딱). FRAM과 버스 공유 가능하나 SPI면 CS 분리(§4.4 SPI1/DAC 충돌 주의). **샘플링은 STM32 hard-RT 로컬 read**(1 ms 변환 → ~500 Hz–1 kHz, 느린 pLLD 강하 미분에 충분); 상향 telemetry는 best-effort(§2.2) → 무선 지터 무관.

**미디어 보호(중요):** 두 후보 다 **건조 공기 전용**. 액/에어로졸/응결 유입 금지 → **소수성 벤트/필터 + 데드에어 컬럼 + 센서를 매니폴드 위쪽 배치.** 노즐-팁 seal 사양(§4.3.4 공압 밀폐 사양)과 직결 — seal이 pLLD SNR과 센서 보호를 동시에 좌우.

**폴백(단일 센서 pLLD SNR 부족 판명 시):** 라인당 **저범위 sealed-diaphragm gauge 추가**(Honeywell ABP2/HSC ±1 psi급 또는 저범위 MS5525 변형) — 봉인 다이어프램·유로 누설 없음·드라이버 코드 재사용. **Sensirion SDP810류 thermal flow-through는 배제**: 대기 포트가 밀폐 공기컬럼의 **누설 경로** → 흡입 홀드·pLLD seal 파괴, 준정적(무유동) 강하엔 유동식 부적합.

**RMS 노이즈 게이트 절차(확정):** 선택 범위·OSR에서 (1) 센서 밀폐·무유동 정적 상태로 **N≥1000 샘플** 취득 → RMS(Pa) 산출 = noise-free 분해능. (2) **PASS 조건 = RMS ≪ ~100 Pa(메니스커스 수백 Pa 대비 여유) AND 미분 SNR ≥ 3×**(가장 느린 예상 메니스커스 dP/dt 기준, §4.2 강하 초기값). (3) FAIL → OSR↑(변환 느려짐 수용) 또는 폴백 저범위 센서 추가. 이 절차 통과가 "단일 센서 pLLD 성립" 판정.

**발주 플래그(recall 아님, 발주 시 확인):** MS5525DSO는 **양방향 compound/±1 psi급 변형** 우선(gauge-vented는 흡입 TADM 못 잡음, §4.3.3 기준형) — 정확한 range suffix·재고는 **발주 시 데이터시트/유통 확인**(recall로 단정 금지). ABP2도 동일. **미디어 보호 기구(확정):** 매니폴드↔센서 사이 **소수성 PTFE 멤브레인 벤트 필터** 인라인 + **데드에어 컬럼**(길이는 §4.3.4 컴플라이언스 최소화와 균형) + **센서를 매니폴드 상부 배치**(중력 배액) + 매니폴드 최저점 드레인. 액/에어로졸/응결이 다이어프램 도달 차단.

### 4.3.4 공압 밀폐 사양 (노즐-팁 seal)

pLLD/TADM 신호 품질과 계량 정확도가 노즐-팁 기밀에 종속(§4.1·§4.3.3·§4.2 pLLD 모드). 아래는 기구팀 합의용 사양.

**씰 방식 = 원뿔 간섭끼움(conical taper), O-ring 없음(기본).**
- 대상 팁 표준 = **universal/Eppendorf식 원뿔 팁**(내부 테이퍼 성형) → 노즐도 원뿔 맨드릴로 절삭. PP 팁의 탄성 변형이 씰 → "일반 비전도성 PP 팁 호환" 목표에 부합.
- ⚠️ **Rainin LTS는 원통형 LiteTouch 씰**(다른 맨드릴 기하) → universal-taper 노즐과 호환 안 됨. 노즐 기준 팁 표준을 명시할 것.
- **O-ring(FKM/EPDM)은 폴백**(누설·보유 사양 미달 시): 단 컴플라이언스↑→**pLLD 미분 둔화** + 데드볼륨↑ + 팁 내경 공차 종속(호환성↓)이라 기본 아님.

**힘 사양 두 가지 (혼동 금지):**
- **(a) 장착/픽업력(seating).** 팁 랙에 노즐을 눌러 탄성 시트. 단일 팁 **~10–30 N(잠정)**, Z 프레스온으로 공급.
- **(b) 보유력(급성 이탈 저항).** 흡입(부분진공)은 팁을 콘에 *더* 밀착시키나, **강제 분주/blowout 양압은 팁을 콘에서 밀어냄** → **보유 한계 = 최대 blowout 압력에서 팁 이탈 없음.** 누설-decay와 **별개 실패모드**(양압이 지배).

**누설·보유 정량 (pLLD SNR 기준):**
- **완속 누설:** worst-case 운전압에서 hold 후 **decay < ~50–100 Pa/s(잠정)** — 누설 유발 dP/dt ≪ 강하 시 메니스커스 dP/dt여야 미분 검출 성립. §4.3.3 저범위 센서·bring-up 실측 게이트와 함께 튜닝.
- **급성 보유:** 보유력 > (최대 blowout 양압 × 팁 콘 단면).
- **데드볼륨/컴플라이언스 최소화:** 플런저↔팁 오리피스 공기컬럼을 짧게 → 압력 응답 sharp(pLLD 미분·계량 정확도 개선). taper가 O-ring보다 유리한 핵심 이유.
- **동심도·리드인:** 노즐 챔퍼로 XY 위치 공차에도 신뢰 인게이지. 재질=SS316/PEEK(내화학·마모). 이젝션=**기계식 이젝터 슬리브**(스텝퍼 불요·§0), 이젝력 ≈ 장착력.

**단계별 (P1 vs P2):**
- **P1 (단일 노즐·단일 압력라인):** 원뿔 간섭끼움 1개. 합산·"8중 누가 샜나" 모호성 없음. Z1 픽업력 ~10–30 N ≪ Z1 가용 55 N(§4.3.2) → 여유. **지금 조립 가능한 범위는 여기까지.**
- **P2 (8 노즐·공유 매니폴드):**
  - **동시 픽업력이 Z2 힘-임계.** SBS 팁 높이 공차는 **노즐별 컴플라이언스(스프링)**로 흡수해 8개 전부 접촉 보장 — 단 **컴플라이언스는 접촉만 보장, 합산력은 못 줄임.** 완전 시트 시 **8 × (10–30 N) = 80–240 N > Z2 가용 ~55 N**(§4.3.2) → **Z2-픽업 = P2 플런저와 나란한 두 번째 P2 힘-임계 축.** 해법: 순차/그룹 픽업 · 캠/웨지 · Z2 고력화(17HS4401+lead 감속). **컴플라이언스로는 해결 안 됨.**
  - **공유 매니폴드 함정:** 팁 1개 누설 → 매니폴드 평균압 오염 → **8채널 pLLD/TADM 전부 무효.** → **픽업 후 씰 self-test**: 매니폴드를 worst-case 운전압 근처로 가압·hold하여 decay 측정. *어느* 팁인지 격리 못 하나 **8중 임의 누설 검출**(→ 재픽업/에러). `pressure_qc=passed` 신뢰의 전제.

**실측 절차·해법 확정(수치 bring-up):**
- **측정 방법:** (a) 장착력 = Z 프레스온 중 인라인 로드셀/포스게이지로 피크 N 기록. (b) 급성 보유력 = 팁 장착 후 매니폴드를 blowout 양압까지 램프, **팝오프 발생 압력** 측정 → 보유 한계. (c) 누설 decay = worst-case 운전압 가압·hold, **dP/dt 로깅**(§4.3.3 센서). (d) 컴플라이언스 스프링레이트 = 변위-force 곡선. 임계값(장착 10–30 N·decay <50–100 Pa/s)은 §4.3.4/§4.3.3 잠정치, 실측으로 확정.
- **Z2 8팁 동시 픽업력 해법 = 미해결 진짜 포크(P2 시점 확정).** ⚠️ **순차-바이-모션은 불가:** 강체 등높이 gang은 Z2 하강 시 랙 웰이 있는 모든 노즐이 **동시 시트** → 느린 프레스온도 완전 시트에서 8×force 합산(컴플라이언스는 접촉 보장이지 순차화 아님, §4.3.4 P2 설명). 실현 가능한 후보 3:
  - **(i) 그룹 부분-랙 픽업** — N개만 랙에 제시·픽업 후 재배치·다음 N. Z2 모션 재사용이나 **대가**: (a) 이미 장착된 노즐 아래 랙 위치가 **비어야**(재충돌 방지) = 랙 레이아웃/워크플로 제약, (b) ⌈8/N⌉× 픽업 이동, (c) **N은 미실측 팁당 힘에 종속** — worst 30 N/팁이면 55÷30 → 그룹=1 = **8회 개별 픽업**.
  - **(ii) 캠/웨지 시간 스태거** — 기계식으로 노즐 시트 시점을 어긋냄(등높이 아님). 신규 기구.
  - **(iii) Z2 고력화** — 17HS4401+lead 감속(§4.3.2 P2 플런저와 동일 해법).
  - → **P2 빌드에서 팁당 힘 실측 후 확정**(P1 무관, 단일 노즐). 순차가 "공짜"라는 이전 서술은 물리적으로 틀림.
- **O-ring 폴백 트리거(확정):** bring-up에서 **원뿔 taper 씰이 (b) 보유 < blowout 요구 OR (c) decay > 임계를 N 픽업 사이클 내 반복 위반**하면 O-ring(FKM/EPDM) 폴백 전환 — 단 미분 둔화·데드볼륨·호환성 대가(§4.3.4 씰 방식) 감수 판정은 사용자.

### 4.4 배선 주의

- Nucleo-F446RE의 **DAC_OUT2(PA5)는 온보드 LD2 LED·SPI1_SCK와 공유** → DAC 사용 시 **PA4(DAC_OUT1) 우선**. PA5를 SPI1 SCK로 쓰면 DAC_OUT2/LD2와 충돌하니 FRAM SPI는 SPI1 회피 또는 SCK 리맵.
- 그 외 정확한 타이머↔핀, DMA 스트림↔타이머 매핑은 **STM32F446 레퍼런스 매뉴얼 / Nucleo 데이터시트 대조 후 확정**(bring-up 잔여).

### 4.5 SRAM · FRAM 레코드 레이아웃

- **SRAM(128KB):** 모션 프로파일 테이블, 명령 FIFO, DMA 버퍼(step ring, USART ring), TMC 상태 미러. pass 1개는 순차 처리라 상주 명령 payload는 소수.
- **FRAM 레코드(§5.2):** 논리 진행 원장. 원자적 쓰기(더블버퍼/시퀀스 넘버로 부분쓰기 검출). FRAM은 사실상 무제한 내구라 마모는 비이슈지만 **레코드 원자성**은 보장 필요(§4.8 확정).

### 4.6 부팅 · 필수 홈잉 시퀀스

1. 클록·주변장치 init → TMC2209(Z/P) UART 설정(전류·마이크로스텝·StallGuard), TMC2208(X/Y)은 standalone 핀 스트랩(외부).
2. **FRAM 읽음** → 리셋 복구인지 콜드 부팅인지 판별(§5.1).
3. `homed=false`이면(전원/워치독 리셋) → **자동 동작 전 재홈잉 필수**(오픈루프). **홈잉 방식은 축별(§4.3.1):** Z/P축 = TMC2209 StallGuard 센서리스, X/Y축 = 엔드스톱 스위치(P1 프로토타입은 전 축 엔드스톱). 단 **젖은/장착 팁이면 자동 재홈잉 금지 → operator 개입 대기**(§5.2).
4. HELLO 응답으로 capabilities·복구 상태 ESP32에 보고. credit 광고 → 명령 수신.

- **P1 프로토타입 플런저 홈잉 = 저전류 하드스톱 램(확정).** TMC2208은 StallGuard 없음(§4.3.1) → 플런저를 **전류 제한(부드러운) 상태로 기계식 하드스톱까지 램**해 제로 확립. 엔드스톱 스위치 대비 부품·핀 절감·플런저 구조 단순. P2(TMC2209)는 StallGuard 센서리스로 대체(§4.3.1).

### 4.7 핀·타이머·DMA 배정 (제안 — RM0390/Nucleo 대조 전)

> ⚠️ **이 표는 제안이다 — RM0390 DMA-request 매핑 표와 Nucleo-F446RE 핀맵 대조 후 bring-up에서 확정**(§4.3 "RM 대조 필요", bring-up 잔여). F4는 DMAMUX가 없어 타이머↔DMA 스트림이 **고정 request 표**에 종속되고 6축 동시엔 스트림 경합이 실재 → 아래 스트림 열은 특히 검증 대상. 개수 fit은 §4.3에서 확인됨(여유), 여기선 **배정 초안**.

**step/dir (축당 타이머 CC 1채널 = step 펄스, DIR=GPIO, 속도 프로파일=UPDATE-DMA로 ARR/CCR 리로드):**

| 축 | 타이머·채널 | 종류 | DIR/EN | UPDATE-DMA(제안, ⚠️미검증) |
|---|---|---|---|---|
| X | TIM3_CH1 | 16-bit GP | GPIO | DMA1 |
| Y | TIM4_CH1 | 16-bit GP | GPIO | DMA1 |
| Z1 | TIM2_CH1 | 32-bit GP | GPIO | DMA1 |
| Z2 | TIM5_CH1 | 32-bit GP | GPIO | DMA1 |
| P1 | TIM1_CH1 | adv | GPIO | **DMA2**(TIM1은 DMA2 전속) |
| P2 | TIM8_CH1 | adv | GPIO | **DMA2**(TIM8은 DMA2 전속) |

- **경합 주의:** TIM1_UP·TIM8_UP은 **DMA2만** 서비스 → 두 adv 타이머가 DMA2 내 별도 스트림을 잡아야 함(스트림 번호 = RM0390 표 확정). 32-bit TIM2/5를 Z(긴 stroke·정밀)에 배정해 카운터 오버플로 여유.

**통신·주변:**

| 기능 | 배정(제안) | 근거 |
|---|---|---|
| ESP32 링크 UART | **USART1**(PA9/PA10) | Nucleo VCP=USART2(PA2/3) **회피**. full-duplex+DMA(§2.1) |
| TMC2209 UART(Z1,Z2,P1,P2) | **UART4 single-wire**(PDN_UART, addr 0–3) | 1버스 4드라이버(§4.3.1). VCP·링크 UART와 분리 |
| FRAM + 압력센서 | **SPI2**(PB13 SCK/PB14 MISO/PB15 MOSI) + CS 분리 | **SPI1 회피**(PA5 SCK↔DAC_OUT2/LD2 충돌 §4.4). FRAM·센서 2–3 CS |
| 엔드스톱(X,Y) | GPIO in + 디바운스 | **기계식 microswitch**(§4.3.1 확정) |

### 4.8 FRAM 레코드 레이아웃 · 쓰기 · 원자성

256Kb/32KB SPI FRAM 전제. **부품(2026-07-13 갱신): `FM25V02A-G`(Infineon, 1차) / `MB85RS256B`(Fujitsu, 2차 소스, 핀 호환 SOIC-8)** — 원 `FM25V02`는 EOL/NRND, 후속 `FM25V02A`는 핀·패키지·기능 동일 드롭인(차이는 read-only Device ID뿐, 펌웨어가 ID로 분기 안 하므로 무영향). 2차 소스 지정 근거 = 2026 FRAM 리드타임 30주+ 지연 헤지. 조달난 시 같은 SPI/SOIC 패밀리 **512Kb(MB85RS512T)/1Mb(MB85RS1MT)로 용량 상향 가능**(드라이버·풋프린트 동일 = 무료 헤드룸). **두 리셋 도메인이 한 칩을 공유하되 영역 분리**(§5.1):

| 영역 | 용도 | 구조 | 도메인 |
|---|---|---|---|
| **A. 물리 복구 레코드** | 축 진행·재홈잉 판단(§5.2 물리 필드) | **최신-우선 더블버퍼 2슬롯** | STM32 리셋 |
| **B. SiLA resync 링** | `{cmd_key, uuid, owner_spki_hash, payload_hash, state, terminal_record?}`(§5.5) | **bounded ring**(엔트리 ~512B, ≥16개=8KB) | ESP32 리셋 |

- **원자성:** 각 레코드 = `{seq:u32(++), payload, crc16}`. 쓰기는 **대체 슬롯에** 기록, 리더는 **crc 유효 + 최대 seq** 선택 → torn-write는 crc 실패로 검출·직전 슬롯 폴백(FRAM 부분쓰기 방어). 더블버퍼(A)/링(B) 공통.
- **쓰기 주기:** 영역 A = stroke two-phase checkpoint(`stroke_state=pre|in_progress|post|uncertain`) 및 phase 전환마다, 최소 per-well. 영역 B = UUID 반환 전 server admission journal `{cmd_key,uuid,owner_spki_hash,payload_hash,state=server_admitted_not_dispatched}` 1회 + 실제 CMD 수신·검증 후 `state=driver_accepted` 전이 + 실행 중 `running` 갱신 + terminal 도달 시 compact terminal record append(`outcome=ok`이면 `DispensedVolume`·`pressure_qc`, `outcome=err`이면 error code), **terminal lifetime 만료 후 `RESULT_GC`(§2.5) 수신 시 GC**(§5.5).
- **영역 B 상태:** `server_admitted_not_dispatched`(UUID 발급 가능, driver 미전송·미실행) → `driver_accepted`(FRAM persist 완료, FIFO 삽입 가능) → `running` → `terminal` → `gc_done`. STM32는 UUID·owner 의미를 해석하지 않고 opaque correlation token으로 저장·반향만 수행.
- **Admission control:** 영역 B는 terminal record 보유 tail을 보장하는 자원. STM32는 HELLO/CHECKPOINT에 `result_ring_capacity`, `result_ring_free`, `terminal_tail_sec_supported`를 보고. ESP32는 미회수 terminal + 예약 슬롯이 capacity를 채우기 전에 새 command를 거부하며, tail을 줄여 공간을 만들지 않음.
- **용량:** 영역 A ~수백 B×2 + 영역 B 8KB ≪ 32KB. **FDL은 FRAM 아님**(ESP32 flash, §3.3), geometry·liquid profile은 애초에 기기 밖(② 소유·인라인) → 여유 충분. 8KB FM24CL64로는 영역 B 링이 빠듯 → **32KB(FM25V02A/MB85RS256B) 권장 근거**(§5.5).

---

## 5. 복구 · 리셋 도메인 (오픈루프의 함정)

> 크로스-보드 관심사: ESP32와 STM32의 리셋은 **다른 결과 도출**. 이 절이 §3.1(ESP32 resync)·§4.6(STM32 홈잉)을 묶음.

**오픈루프 스텝퍼라 "resume"은 위험.** 리셋 후 물리 위치는 **미상** → 동작 전 **재홈잉 필수**(축별: Z/P=TMC2209 StallGuard, X/Y=엔드스톱, §4.3.1). **FRAM은 논리 진행이지 재개 위치가 아님.**

### 5.1 두 리셋 도메인 구분

| 도메인 | 위치 정보 | 처리 |
|---|---|---|
| **STM32 리셋**(전원·워치독) | **위치 상실** | FRAM 논리 상태 읽음 → **재홈잉 필요** → `CHECKPOINT_STATE` 보고 → 호스트 ②가 재개 전략 결정 |
| **ESP32 리셋·링크 드롭** | STM32 위치 **유지**(계속 실행/정지 상태) | 링크 resync만(§3.1) — replay/재구독, 물리 재홈잉 불필요 |

### 5.2 `CHECKPOINT_STATE` payload (FRAM 원장)

STM32가 주요 전환(per-well/per-stroke)마다 FRAM에 기록, 리셋 후·resync 시 보고:

```
{ cmd_key, head, logical_well_index, phase, stroke_state,
  tip_attached:bool, tip_has_liquid:bool,
  homed:bool,               // 위치 좌표는 신뢰 안 함(오픈루프)
  uuid, owner_spki_hash,    // SiLA resync용 불투명 상관 토큰(client SPKI hash, §5.5) — STM32 미해석
  terminal_record? }        // ok: DispensedVolume + pressure_qc, err: error code 보유(§5.5)
```

> `uuid`·`owner_spki_hash`·`terminal_record`는 **ESP32 리셋 도메인** 전용(§5.5 SiLA resync). STM32 리셋 도메인(재홈잉·재개 결정)은 위 물리 필드만 사용 — 두 도메인이 같은 FRAM 원장을 공유하되 관심 필드가 다름.

- **젖은/장착 팁 재홈잉 금지.** `tip_attached && tip_has_liquid`인 상태의 자동 재홈잉은 crash/spill 위험 → **operator 개입 경로**(`RecoverableErrors`→`Continue`)로만. 마른/미장착이면 호스트 ② 판단으로 자동 재홈잉 허용.
- 재분주 경계는 이 FRAM 논리 상태 + ESP32 캐시(마지막 `ActiveTarget`/`DispensePhase`)를 조합(icd-2-3 §5.1). **`CompletedMask` 없음** 원칙 유지.
- **stroke two-phase checkpoint:** stroke 시작 전 `pre`, 액체 이동/플런저 stroke 진입 직전 `in_progress`, 완료 검증 후 `post` 기록. STM32 리셋 후 `in_progress`로 발견되면 실제 흡입/분주 완료 여부 불확실 → `stroke_state=uncertain`, `RECOVERABLE_ERROR{UncertainStroke}`로 표면화. 자동 재실행 금지, operator 또는 상위 복구 정책이 Retry/Skip/Abort 결정.
- **`tip_has_liquid` 판정 근거(확정):** **명령 실행 논리 상태가 1차 권위** — 흡입 성공 후 완전 분주(+blowout) 전이면 true. **플런저 위치가 보강**(제로 미복귀 = 잔량). **pLLD 압력은 선택적 교차확인**(액면/막힘). 즉 `tip_has_liquid = f(aspirated∧¬fully_dispensed)`를 FRAM에 논리 플래그로 지속(§5.2 payload) — 센서 단독 판정 아님(젖은 팁 재홈잉 금지 트리거, §5.2).

### 5.3 Cancel / Continuation — 우선 경로 (out-of-band)

`CANCEL`·`CONTINUATION`은 버퍼된 pass 명령들 **뒤에 줄 서면 선점 불가**. 따라서:

- **PRIO 플래그** 프레임 → ESP32·STM32 모두 **명령 FIFO를 건너뛰어 즉시 처리**.
- **stroke 원자성 존중**: 진행 중 stroke는 **완주 후** 정지(icd-2-3 §5.3). 안전 취소 불가 구간이면 `OperationNotSupported` 성격의 거부.
- 취소 결과 = command → 내부 `CMD_RESULT{err, Cancelled}` 기록, 외부 `ExecutionInfo.finishedWithError(Cancelled)` 표면화. `Result(UUID)`는 DispenseResult 없이 표준 오류. 재분주 경계는 §5.2(FRAM + 캐시).

### 5.4 구체 프레임 예시 (설명용)

`CMD_DISPENSE`(multi8, 96-well 타깃) 하향:

```
COBS{ seq=0x11 | flags=ACK_REQ | type=CMD_DISPENSE | len=… |
      cmd_key={cmd_epoch=0x0002, cmd_id=0x0007}
      payload_hash=…
      head=multi8  tip_policy=once
      src.deck_slot=2  src_well_index=0  src.machine_coords=[(x,y,z)]
      target.deck_slot=3
      target.machine_coords=[96×(x,y,z) floats]
      VolumeMap=[8×12 µL floats]
      liquid_profile={aspirate:…, dispense:…} }
  CRC16 } 0x00
```

STM32 응답 흐름:
```
CMD_ACCEPTED{cmd_key=2:7, credit_free=2}           (reliable)
EXECUTION_INFO{2:7, running, 0.0}                  (best-effort)
ACTIVE_TARGET{2:7, deck-3, col=1} … col=12         (best-effort, per stroke)
DISPENSE_PHASE{2:7, MovingToWell→Dispensing→MovingAway} × 12  (best-effort)
CMD_RESULT{2:7, ok, DispensedVolume[8×12], pressure_qc=passed}   (reliable)
```

### 5.5 SiLA 세션 resync (ESP32 리셋 — Stage 4 · §3.5)

§5.1 우측 도메인: **ESP32 리셋/링크 드롭은 STM32 물리 위치를 유지**하나 SiLA lease·구독 같은 세션 상태는 ESP32 RAM에 있어 상실. 반면 UUID·owner·terminal record는 STM32 FRAM 영역-B journal로 복구. 재접속 클라이언트가 진행 중 command를 어떻게 되찾는가. **핵심 계약 = `lifetimeOfExecution`**(icd-2-3 §4.1 line 186 "Adapter의 UUID/result 회수 수명") — 서버가 이 수명 동안 UUID/Info, 성공 Result, 실패 terminal 상태 회수를 보장하는 durability window.

**무엇이 ESP32 리셋을 견디나 (durability 결정):**

| 상태 | 리셋 견딤? | 메커니즘 |
|---|---|---|
| **cmd_key↔UUID 맵** | **예(필수)** | STM32 **FRAM 원장 지속**. ESP32가 UUID 반환 전 `SERVER_ADMISSION_PREPARE`로 `{cmd_key, uuid, owner_spki_hash, payload_hash, state=server_admitted_not_dispatched}`를 기록시킴. 실제 CMD 수신 후 STM32가 `driver_accepted`로 전이. 리부트 시 ESP32가 CHECKPOINT_STATE(RESYNC)로 재구성 |
| **진행 ExecutionInfo**(phase/progress) | 재생 | best-effort telemetry 캐시가 STM32의 지속 스트림으로 재충전 → 재구독 시 last-value 서비스(첫 신선 샘플 전까지 stale 표기) |
| **terminal record**(`ok`/`err`) | **예(필수)** | terminal lifetime 만료까지 compact terminal record를 STM32 FRAM에 보유. `ok`는 ESP32 리셋 후에도 `Result(UUID)` replay 보장. `err`는 `ExecutionInfo.finishedWithError` + Defined Execution Error replay. `DispensedVolume`은 정규화 명령량 echo, `pressure_qc`는 pLLD/TADM 검증 상태 |
| **lease(LockIdentifier)** | **아니오(필수)** | 크래시 서버가 lock을 인질 삼지 않음 → 클라가 재Lock. 서버 재기동 ≈ lease 만료 |
| **observable property 구독** | 아니오 | 재구독(캐시가 현재값 즉시 서비스) |

**UUID 순서 제약 (crux — double-dispatch 방지):** ESP32는 **UUID 반환 전** STM32 FRAM 영역-B에 server admission journal을 먼저 남김. 기록 성공 후 UUID를 클라에 반환하고, 그 뒤 실제 CMD를 하향. 리셋 케이스: ⓐ journal 전 크래시 → call 실패, UUID 없음, 하향 없음, 클라 재시도; ⓑ journal 성공·UUID 반환 후·CMD 하향 전 크래시 → FRAM에 `server_admitted_not_dispatched` 보유, **실행 안 됨 확정**, lifetime 내 Info 조회는 `finishedWithError(NotDispatched)`로 replay, `Result(UUID)`는 DispenseResult 없이 표준 오류; ⓒ CMD 수신·검증 후 STM32 `driver_accepted` persist → 투명 resync. STM32 실행 시작 후 UUID가 클라에 도달 못 하는 double-dispatch는 journal-before-return + driver-accepted 전이 순서로 차단.

**resync 프로토콜 (ESP32 리부트):**
1. 부팅 → NVS(cert/key, 클라이언트 SPKI allowlist) → WiFi/TLS → **UART HELLO(RESYNC)** → STM32가 capabilities + **미종료/미회수 command 셋**(`{cmd_key, uuid, owner_spki_hash, payload_hash, state, phase, tip flags, terminal_record-if-done}`) 보고.
2. ESP32가 RAM 재구성: cmd_key↔uuid 맵·telemetry 캐시(stale)·보유 terminal record.
3. mDNS 재광고 — **SiLA Server UUID는 NVS 상수라 불변** → 클라의 **서버 SPKI 핀 ↔ UUID 바인딩** 유효(§2.1).
4. 클라 재접속(새 TLS/gRPC, 서버 SPKI 핀 재검증 + 클라이언트 인증서 제시 — 핀은 클라 측 지속, 클라이언트 allowlist는 ESP32 측 지속).
5. **클라 재Lock** — 구 `LockIdentifier`는 `InvalidLockIdentifier`. 재Lock 트리거 = **KeepLeaseAlive deadline-miss(icd-2-3 §5.2, Timeout/2)** *또는* **예기치 못한 `InvalidLockIdentifier`**(후자가 Timeout/2 미만 빠른 리부트를 커버).
6. **진행 command 재구독** `<Cmd>_Info(uuid)`/`_Result(uuid)`:
   - 수명 내 + UUID 앎 + **owner 신원 일치** → honor. `server_admitted_not_dispatched`는 `finishedWithError(NotDispatched)`로 즉시 replay. `driver_accepted|running`은 Info를 캐시에서 재개, `ok` Result는 STM32 CMD_RESULT 도달 시(또는 FRAM 보유분 즉시) 전달. `err` terminal은 Result payload 없이 Defined Execution Error로 전달.
   - **retrieval 인가 = 신원 바인딩**: `owner_spki_hash` = server admission 당시의 **클라이언트 SPKI hash**(FRAM 지속). 재접속 mTLS 클라이언트 SPKI와 일치해야 회수 허용(icd-2-3 §5.2 line 210 준수, 새 lease 소유자에게 타 클라의 pressure QC 유출 방지).
   - UUID 미상·수명 만료·신원 불일치 → `InvalidCommandExecutionUUID` → 클라가 QUERY(DeviceStatus) + layer2 이력(ETA/stroke)으로 재도출.
7. **STM32 물리 실행 무중단**(§5.1). lock 공백이 in-flight stroke를 멈추지 않음(§5.3 원자성 — lock은 *제출* 보호이지 원자 stroke 아님). ESP32 다운 중엔 하향이 없어 새 작업 미유입(단일 writer·shallow FIFO §2.4) → 재Lock 전까지 신규 command 없음.

**수명 계약 (durability window 정합):** 실행 중엔 서버가 `updatedLifetimeOfExecution`를 **연속 push**(장수명 command가 만료로 UUID 무효화되지 않게 — §3.6). terminal 후 **회수 tail(기본 300s)** 동안 FRAM이 terminal record를 보유, **리부트 시간이 이 tail을 소모**. 장비는 **FRAM이 리부트를 넘어 지킬 수 있는 것보다 긴 tail을 광고하면 안 됨**. terminal record GC는 tail 만료 후 ESP32가 내부 `RESULT_GC`(§2.5)를 보낼 때만 수행, bounded ring(무한 성장 방지).

**경계 주의:** UUID·`owner_spki_hash`·server admission state를 FRAM에 두는 것은 §0 원칙 2("STM32 catalog-stateless")를 깨지 않음 — STM32는 이를 **해석하지 않는 불투명 상관 토큰(opaque correlation token)**으로 저장·반향만 함(의미는 ESP32 종단). STM32가 판단하는 것은 `server_admitted_not_dispatched`는 FIFO 미삽입 상태라 모션 미실행이라는 물리 사실뿐. 단 레코드 폭이 늘어 **FRAM 부품 선정(§4.8)은 32KB SPI(`FM25V02A-G` 1차 / `MB85RS256B` 2차)가 8KB `FM24CL64`보다 유리**.
