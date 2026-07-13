# ICD — Liquid Handler ↔ Task Scheduler (SiLA2 경계)

> **Interface Control Document (Design Final)**
> 상위 개요: [`../plan.md`](../plan.md) · 인접: [layer2-orchestrator](layer2-orchestrator.md) · [layer3-device](layer3-device.md)
> 대응 API 스케치: [`../experiment_api_example/liquidhandler.ipynb`](../experiment_api_example/liquidhandler.ipynb) · [`ware.ipynb`](../experiment_api_example/ware.ipynb)
>
> 상태: **DESIGN FINAL** · 대상 인터페이스: **② Orchestrator/Scheduler ↔ ③ Liquid Handler Device** · 규약: **SiLA2**
>
> **개정 이력**
> · 2026-07-11 — **멀티 헤드 반영**: 하드웨어 구성이 **1채널 + 8채널 헤드(플런저 2개, 독립 Z)**로 확정됨에 따라 `HeadSelector` 파라미터, per-head `HeadGeometry`, ganged 8채널 feasibility 규칙, `HeadMapIncompatible` 오류 추가(§6). ([lower-layer notes](icd-liquid-handler-lower-layer-notes.md), [`icd-liquid-handler-3-4.md`](icd-liquid-handler-3-4.md) 하드웨어 경계)

---

## 0. 범위

오케스트레이터의 `DeviceAdapter`(= SiLA2 **클라이언트**)와
리퀴드 핸들러의 SiLA2 **서버**(layer3 §구현 프로파일 — host C++/Python 또는 장비 MCU 임베디드) 사이에서 **gRPC로 오가는 바이트 계약**을 규정. 이 바이트 계약은 서버 구현 프로파일과 무관하게 동일하다.

> ⚠️ **DSL에 대한 규정은 layer1에서 다룸.**
> layer1의 텐서 API(`exp.Stack`, `exp.exec.Dispense`, `(K,8,12)` 볼륨 텐서)는 **Experiment layer**에 속하며
> SiLA2 통신 규격의 대상이 아님. (plan.md §2 "SiLA2 ≠ 실험 API")
> 한 `Dispense` pass의 SiLA2 명령 번역·송출 규격을 규정.

**아키텍처:**

```
① Experiment DSL        exp.Stack( Dispense(src="buffer", volume=(8,12)), Mix(...), ... )
   (layer1, 범위 밖)         │  operator가 기술
                            ▼
② DeviceAdapter          pass 열 → SiLA2 command 열로 번역 (이 ICD가 규정하는 경계 ↓↓↓)
   (SiLA2 client)           │
════════════════════════════╪═══════════════ SiLA2 / gRPC / HTTP2 (+ TLS) ═══════════════
                            ▼
③ Liquid Handler         SiLAService · LockController · LiquidHandling/v1 Feature
   (SiLA2 server; §0 프로파일) │  FDL로 선언한 command/property를 실행, stroke로 내부 분해
                            ▼
④ 물리 핸들러             8/96채널 헤드, 덱, 리저버
```

---

## 1. 참조 표준 (Referenced Standards)

| 문서 | 용도 |
|---|---|
| **SiLA 2 Part A** (Overarching Concepts) | 전송·보안(TLS)·디스커버리·Feature/Command/Property/Error 모델 |
| **SiLA 2 Part B** (Mapping to gRPC) | proto 매핑, observable command 실행(`CommandExecutionUUID`, `ExecutionInfo` 스트림), Binary Transfer |
| **SiLA 2 Feature Definition Language (FDL)** XSD | 이 문서 §6의 Feature 정의 스키마 |
| **SiLA2 Core Features** | `SiLAService`, `LockController`, `CancelController`, `ErrorRecoveryService` |
| **TLS ≥1.2** (RFC 8446 TLS 1.3 · RFC 5246 TLS 1.2; 1.0/1.1 금지 RFC 8996) · **X.509**(RFC 5280) · **SPKI Pinning**(RFC 7469 계열 개념) | §3 mTLS·SPKI Pinning 신뢰 확립 |
| `plan.md` · `layer2-orchestrator.md` · `layer3-device.md` | 상위 아키텍처·스케줄링·DeviceAdapter 계약 |

---

## 2. 인터페이스 식별 (Interface Identity)

| 항목 | 값 |
|---|---|
| **엔드포인트 A (initiator)** | Orchestrator `DeviceAdapter` — SiLA2 **Client** (`unitelabs-sila`) |
| **엔드포인트 B (responder)** | Liquid Handler — SiLA2 **Server** (구현 프로파일: host C++/Python 또는 장비 MCU 임베디드, layer3 §구현 프로파일), 장비당 1개 |
| **전송(transport)** | SiLA2 over **gRPC / HTTP2**, **TLS 필수**(SiLA2 Part A: 서버 자기서명 인증서 허용) |
| **디스커버리** | **SiLA2 Server Discovery (mDNS / DNS-SD)** — 서버가 `_sila._tcp` 광고, 레지스트리가 자동 등록(layer2 Device Registry) |
| **명령 방향** | **모든 command는 Orchestrator → Device 단방향 개시.** 서버는 observable property/command로 **telemetry만 push** (역방향 명령 없음) |
| **동시성 불변식** | **single-writer** — 임의 시점 한 장비에 lease 소유자 정확히 1개. `LockController`로 강제(§5.2, layer2 §장비 ownership) |
| **timing_class** | **`soft`** — 오케스트레이션 타임스케일(초~분). host 측 hard-RT 제어 루프 없음(layer3 §실시간성). 결정론적 지연을 **보장하지 않음** |

---

## 3. 연결·신뢰 확립 (Connection & Trust Establishment)

연결 전 **상호 인증** 필요.
SiLA2 서버는 **다중 클라이언트 연결을 허용**하므로(layer2 §장비 ownership),
단순 인증만으로는 부족하고 **양방향 인증 + 채널 암호화 + 무결성**이 함께 필요.

| 계층 | 질문 | 메커니즘 | 위치 |
|---|---|---|---|
| **전송·identity (§3)** | "상대가 **등록된 identity**인가" (위장 아님) | **mTLS + TOFU SPKI Pinning** | 이 절 |
| 세션 인가 (§5.2) | "지금 쓸 권한자인가" | `LockController` (lease) | §5.2 |

> 두 계층은 서로 독립적: mTLS는 *등록된 identity(클라이언트/서버)*를 확인 후, Lock은 *인증된 클라이언트 중 지금 사용 중인 1명인지*를 확인.

> CA 채택 시 랩 전역 Certificate Authority 개인키는 유출되면 *어떤 장비든 위조해 위험한 프로토콜을 흘려보낼 수 있어* 위험도가 큼. 대신 각 개체의 **안정적 identity 공개키(SPKI)를 상대가 pinning**하고, 폐기는 **pin 삭제**로 처리(§3.2). 장비 하나가 뚫려도 피해는 그 장비 하나로 한정.
> **DIY 장비 연결 가능**: 벤더 중립적 — Pinning은 *등록된 키와의 동일성*만 검증할 뿐 제조 출처는 묻지 않음. SPKI pin은 **identity continuity**를 증명.

### 3.1 mTLS — 전송 신뢰의 뼈대 (Stage 1)

SiLA2 Part A가 TLS를 필수로 하고 서버 인증서를 요구하므로, 여기에 **클라이언트 인증서를 더해 상호 TLS(mTLS)로 확장**.  
스펙과 충돌하지 않는 배포 강화.

| 항목 | 규정 |
|---|---|
| **프로토콜** | **TLS ≥1.2** (floor=1.2, **TLS 1.0/1.1 금지**=다운그레이드 차단; 1.3은 양단 지원 시 협상 우선). SiLA2 gRPC/HTTP2 전송 위에 적용. SiLA2 표준은 TLS만 MUST·버전 미지정이라 1.3은 요건 아님 — 임베디드 서버(ESP32) 베이스라인=mbedTLS 1.2(spc §1.5) |
| **상호 인증** | Orchestrator(client)·Liquid Handler(server) **각자 자신의 X.509(self-signed) 제시 → 상대는 SPKI pin과 대조 검증** |
| **개인키 소유 증명** | X.509(self-signed)는 공개키 운반체로 역할. SPKI pin로부터 신뢰, **핸드셰이크가 그 공개키의 개인키를 현재 실 소유자임을 증명**(공개키만 훔쳐선 통과 불가) |
| **획득 보장** | 채널 **암호화**(도청 방지) + **무결성**(변조 방지) + **채널 바인딩**(MITM 방지) + **양방향 identity** |
| **클라이언트 검증(서버 측)** | 장비 서버는 클라이언트 공개키가 **Orchestrator SPKI pin과 일치**하는지 검증 → rogue orchestrator/client 차단 |
| **서버 검증(클라이언트 측)** | Adapter는 서버 공개키가 **SPKI pin과 일치** + **SPKI pin ↔ mDNS로 발견한 SiLA Server UUID 바인딩** 확인 → 스푸핑 장비 차단 (§3.2) |
| **실패 처리** | pin 불일치·미등록 pin·인증서 만료·UUID 불일치 → **연결 거부**(command 단계 도달 전). SiLA2 command/property 교환은 mTLS 성립 후에만 |

장비 서버는 허용된 client SPKI별 role(`operator|admin|service`)을 보유. 일반 scheduler/DeviceAdapter 경로는 `operator`, raw deck layout·calibration table·진단 raw data를 다루는 service-admin 표면은 `admin|service`만 허용. role 부여·교체·폐기는 provisioning 절차와 감사 로그 대상이며, 사용자 레벨 RBAC는 여전히 ①↔② 경계 책임(§3.2, §5.2).

> §1의 "TLS 필수(서버 자기서명 허용)"는 SiLA2 Baseline.
> 이 ICD는 여기에 **mTLS + SPKI Pinning**을 추가 요구.

### 3.2 SPKI Pinning — identity 앵커 (Stage 2)

상대가 등록된 identity인지는 **상대가 보관한 SPKI pin**을 기준으로 판단.
각 개체(Orchestrator·각 Liquid Handler)는 **안정적 identity 공개키(SPKI)**를 갖고, 상대는 그 SPKI를 pin.

- **TOFU (Trust On First Use)**: 최초 연결 시 상대 SPKI를 지문으로 고정(pin). 이후 매 연결마다 제시된 공개키를 pin과 대조.
- **pin 대상 = SPKI(공개키), cert 지문이 아님**: 안정 키 위에서 cert(유한 유효기간)가 회전해도 pin이 깨지지 않음.
- **UUID 바인딩**: pin 레코드를 장비의 **SiLA Server UUID**(`SiLAService` feature 노출, §4)에 바인딩. mDNS로 발견한 UUID와 pin된 키가 일치해야 신뢰(§3.1). UUID만 흉내낸 공격자는 pin된 개인키가 없어 차단.
- **pin 레지스트리 = Orchestrator allowlist**: `UUID ↦ SPKI pin`을 오케스트레이터가 보관(신뢰경계, layer2). **Device Registry epoch에 연동** — pin 추가/삭제/교체가 epoch를 올리면 dry_run→run Time-of-check to time-of-use(TOCTOU) 감시(layer2 §장비 ownership)가 드리프트를 포착. 감사·백업 대상.
- **cert 수명**: 유한한 유효기간을 가진 self-signed 인증서.
- **Key Ceremony**: identity 키 교체 시 **구 키가 신 키를 서명**해 제시함으로써 물리 재방문 없이 pin 연속성 유지. **백업 pin**(보조 키 병행 등록)으로 주 키 분실에 대비.
  - **정상 rotation과 compromise recovery 분리**: 구 키 서명은 *정상 교체*에만 유효. 구 개인키 유출·장비 회수·의심 징후가 있으면 구 키 서명은 신뢰하지 않고, 해당 pin 삭제 후 물리/OOB 재등록 절차로만 복구 가능. 백업 pin은 장비별 최소 개수로 제한하고 등록·사용·삭제 모두 감사 로그 대상.
- **폐기 = pin 삭제 (즉시, CRL 없음)**: 유출됐거나 회수한 장비는 오케스트레이터에서 pin만 지우면 다음 핸드셰이크부터 거부. star 토폴로지이므로 별도 CRL/OCSP responder가 필요없이 **한 곳에서 즉시** 단절.

> **Provisioning 초안(하위 레이어 확정 전).**
> TOFU는 운영 중 자동 등록 메커니즘이 아니라 **초기 provisioning 후보 수집 방식**으로만 사용.
> 미등록 장비는 quarantine 상태로 등록하고 command 송신 대상이 될 수 없음.
> pin 승격은 관리자 승인 + out-of-band fingerprint 확인(QR/물리 라벨/장비 버튼 등) 뒤에만 허용.
> 정확한 pairing ceremony와 물리 확인 수단은 lower-layer 설계 확정 시 이 절에 고정.

```
[상시 연결 — 매 세션, Stage 1+2]
  Adapter ─ mDNS 조회 ─▶ 장비 UUID·주소 발견
  Adapter ◀── TLS(≥1.2) mTLS 핸드셰이크 ──▶ 장비
     · 장비:   클라이언트 공개키 == pin된 Orchestrator SPKI?      (Rogue Client 차단)
     · Adapter: 서버 공개키 == pin된 SPKI + pin ↔ 발견 UUID 바인딩?  (Spoofing 차단)
  성립 ─▶ 이후 LockController.LockServer → command (§5.2~6). 실패 ─▶ 연결 거부.
```

> **잔여 위험과 완화.**
> 최초 pin은 통제된 셋업 창에서 수행.
> telemetry 소비자는 layer2 TriggerEvaluator에서 타당성 경계(plausibility bounds)를 적용(§6.4·§7).

> **경계 명확화. 오케스트레이터 ↔ 장비 간 인증**만 다룸.
> **사용자-레벨 인증(token/RBAC, owner/group/scope)** 은 **① ↔ ② 경계**의 몫이며, 이 때 오케스트레이터가 신뢰경계(layer2 §권한, §5.2).
> 장비는 mTLS로 인증된 단일 lease 소유자만 신뢰할 뿐, 사용자 구분없음.

---

## 4. 서버 Feature Catalogue

리퀴드 핸들러 서버는 아래 Feature들을 FDL로 선언.
FQI 형식은 `<Originator>/<Category>/<Feature>/v<Major>` (표준=`org.silastandard`, 벤더=역도메인).

| Feature (FQI) | 종류 | 필수 | 이 인터페이스에서의 역할 |
|---|---|:---:|---|
| `org.silastandard/core/SiLAService/v1` | Core | **필수** | 서버 identity: `ServerName`·`ServerUUID`·`ImplementedFeatures`·FDL 조회. 레지스트리 등록의 진입점 |
| `org.silastandard/core/LockController/v1` | Core | **필수** | **lease = Lock.** `LockServer`/`UnlockServer`(`LockIdentifier` Client Metadata로 발급), single-writer 강제(§5.2). `sila_base` FDL로 codegen·구현 |
| `org.silastandard/**core.commands**/CancelController/v1` | Core | **필수** | layer1 `run.cancel()` / 스케줄러 abort의 백엔드. 명령 = `CancelCommand(CommandExecutionUUID)`·`CancelAll`(§5.3). `sila_base` FDL로 codegen·구현 |
| `org.silastandard/core/ErrorRecoveryService/v1` | Core | 권장 | 물리 오류(팁 픽업 실패 등) 회복 협상 — observable `RecoverableErrors` property + continuation option + timeout(§5.3). `sila_base` FDL로 codegen·구현 |
| **`lab.sica/devices/LiquidHandling/v1`** | Domain | **필수** | **분주 능력의 본체** — `Dispense`/`Mix`/`Wash`/tip + 덱·리저버 telemetry (§6) |
| `com.<vendor>/devices/<VendorFeature>/v1` | Vendor | 선택 | 벤더 전용(LLD, air-gap 등). layer1 `ext(...)`로 노출. 연관형/독립형 구분은 SiLA FDL 확장이 아니라 Registry overlay의 `augments` 메타데이터로 표시(§8, [lower-layer notes](icd-liquid-handler-lower-layer-notes.md)) |

> **capability 매핑:** `LiquidHandling/v1` Feature의 존재 = Device Registry의 `capability="liquid_handling"`.
> 스케줄러는 이 capability로 장비를 매칭(liquidhandler.ipynb §0의 `lab.device(attribute="liquid_handling")`).

---

## 5. 공통 상호작용 계약

### 5.1 Observable command 실행 (SiLA2 Part B)

분주는 수 초~수십 초가 걸리는 물리 동작이므로 **모든 실행 command는 Observable**.

```
Client(Adapter)                         Server(Handler)
   │  Dispense(VolumeMap, meta=Lock)        │
   │───────────────────────────────────────▶│  구조 검증·admission precheck → CommandExecutionUUID 반환
   │◀───────────────────────────────────────│  UUID
   │                                        │  driver 하향·persist는 비동기
   │  Subscribe ExecutionInfo(UUID)         │
   │───────────────────────────────────────▶│
   │◀───────── ExecutionInfo 스트림 ─────────│  status: waiting→running, progress 0..1,
   │            (running, 0.4, ~8s) ...     │  estimatedRemainingTime
   │◀───────── ExecutionInfo(finished) ─────│
   │  Result(UUID)                          │
   │───────────────────────────────────────▶│
   │◀───────────────────────────────────────│  DispenseResult (§6.2)
```

**UUID-first 실행 모델.** 서버는 SiLA 요청의 구조 검증, Lock/권한 확인, 결과 링 admission precheck를 통과한 뒤, UUID 반환 전 내부 driver resync journal에 `{cmd_key, uuid, owner_spki_hash, payload_hash, state=server_admitted_not_dispatched}`를 비휘발 기록. 이 기록 성공 후 `CommandExecutionUUID`를 반환. 실제 driver 실행 durability는 그 뒤 STM32 `CMD_ACCEPTED`/FRAM persist(`driver_accepted`) 시점에 성립. UUID 반환 후 driver accept 전에 서버가 리셋되면 해당 UUID는 orphan이 아니라 `server_admitted_not_dispatched`로 복구되며, 실행 안 됨이 확정되므로 lifetime 내 조회는 `NotDispatched` terminal error로 표면화. driver accept 이후에는 `cmd_key↔UUID`가 FRAM에 남아 resync 대상.

**결과 회수와 보관 해제.** `Result(UUID)`는 결과 조회일 뿐 consume ACK가 아님. 이 2-3 경계에는 `ConfirmResultConsumed`류 외부 API를 두지 않음. 서버는 terminal `lifetimeOfExecution` tail 동안 결과를 replay 가능하게 보관하고, tail 만료 후 내부 driver GC 정책으로만 보관을 해제.

**진행/중간응답 — 운용 채널과 진단 채널 분리.** 실행 상태·진행률·남은 시간은 `ExecutionInfo` 담당, 총 예상시간은 layer2 스케줄러 추정값(§6.1·§8)을 기준으로 함. 운용 경로는 `ActiveTarget`과 `DispensePhase`만 소비하며, 물리 pose류 진단은 service/admin 표면으로 분리.

| 채널 | 갱신 시점 | 싣는 값 | 소비처 |
|---|---|---|---|
| `ExecutionInfo`(모든 observable command 공통) | 서버가 `waiting→running→finished*` 전이마다 push | `commandStatus`(waiting/running/finishedSuccessfully/finishedWithError) + `progressInfo`(0..1) + `estimatedRemainingTime` + `updatedLifetimeOfExecution` | `run.stream()` 상태·진행률·남은 시간 표시, Adapter의 UUID/result 회수 수명 관리, 실행 이력 보정 참고 |
| Lane A — `ActiveTarget`(§6.4) | 서버가 well 단위로 갱신 | 현재/직전 완료 **덱·well**(well-index, 벤더 중립) | `run.stream()`의 현재 위치 표시(실험자용) |
| `DispensePhase` Intermediate Response(`Dispense`/`DispenseAndMix` 전용, §6.3) | 서버가 well 내부 단계 전환마다 push | `String{MovingToWell,Dispensing,Mixing,ChangingTip,MovingAway}` | 에러 시 well 재사용/폐기 판단(아래) |

- **Lane A**: 읽기전용 telemetry라 §6.1 anti-chatty(=per-well *command* 금지)와 무모순, 취소를 견딤.
- **Pose/diagnostics**: `PipettorPose` 같은 물리 좌표·기계 진단 값은 task scheduler 운용 API에 노출하지 않음. service/admin role, service mode 또는 exclusive Lock, 감사 로그가 있는 진단 표면에서만 조회·구독 가능.
- **`DispensePhase`**: Lane A `ActiveTarget`(well 단위)보다 세밀한 well 내부 단계 telemetry. Lane A를 대체하지 않고 보강. 소비 규칙 — `MovingToWell` 중 에러면 해당 well은 미접촉(재사용 안전), `Dispensing` 중이면 부분 분주(폐기/재검증 필요), `Mixing` 중이면 분주는 끝났지만 혼합은 불완전(재분주 금지, 재혼합/검증 판단), `ChangingTip`/`MovingAway` 중이면 분주 자체는 완료(팁·포지셔닝 문제만 별도 확인).
  - **소비 방식**: `Dispense`/`DispenseAndMix` 실행 내내 클라이언트가 `DispensePhase` 스트림을 열어두고 마지막 수신값을 자체 보관. 에러 뒤 재구독으로 값을 회수하는 방식은 사용하지 않음.
  - **스트림 유지 요구**: 클라이언트·서버 gRPC keepalive 설정, 구독 RPC deadline 미설정 또는 충분한 여유값 적용, 마지막 `DispensePhase`/`ActiveTarget` 값의 상태 저장소 보관.
  - **끊김 시 대체 처리**: 스트림이 끊기면 재사용/폐기 판단은 Lane A `ActiveTarget`(well 단위)까지만 사용.

**에러·취소 시 귀속 흐름:** `finishedWithError`(취소 포함, §5.3) 전이 시 Result 회수 불가. 완료 상태를 `DispenseResult`에 실어 취소 후 회수하는 방식은 사용하지 않음. 대신 **Lane A `ActiveTarget`의 마지막 관측값 + `DispensePhase`의 마지막 클라이언트 보관값**을 조합해 재분주 경계를 재구성.

> **`CompletedMask` 없음.** 취소·오류 후 재분주 경계는 `ActiveTarget`과 `DispensePhase` 캐시만 사용.

### 5.2 Lock = lease (single-writer 강제)

layer2 불변식 "lease 획득 = Lock 획득"의 구현.

1. 스케줄러가 장비 배정 시 `LockController.LockServer(LockIdentifier, Timeout)` 호출 → 배타 점유 획득. (`Timeout`=초. SiLA2 baseline에서 0은 무기한이나, 이 ICD 운영 profile은 §5.2.7에 따라 0을 사용하지 않음.)
2. **획득 후 모든 lock-protected request는 `LockIdentifier`를 SiLA2 Client Metadata로 동반**해야함.
   Metadata 누락/불일치 → 서버가 `InvalidLockIdentifier`(LockController 표준 오류)로 거부.
3. 실행 완료/실패 시 `LockController.UnlockServer(LockIdentifier)`.
4. **보호 범위 — 확정**: mutating `LiquidHandling` command(`Dispense`/`DispenseAndMix`/`Mix`/`Wash`/tip/`KeepLeaseAlive`)는 lock-protected. `SiLAService`, `LockController.IsLocked`, read-only property 조회·구독은 lock 없이 허용. command lifecycle 조회(`ExecutionInfo`/Result)와 cancel/recovery는 해당 command를 소유한 Adapter가 동일 `LockIdentifier`를 동반.
   - **LockIdentifier 생성·보관**: `LockIdentifier`는 예측 불가능한 값이어야 한다(CSPRNG, 128-bit entropy 이상). 재사용 금지, 로그·trace·UI에는 원문을 남기지 않고 redaction/hash만 기록. command/result/cancel/recovery 조회 권한은 `LockIdentifier` 값뿐 아니라 **mTLS client SPKI와 command owner binding**이 함께 일치해야 인정.
   - **읽기 표면 접근제어**: read-only property는 lock 없이 허용하되, 인증된 모든 클라이언트에게 무제한 공개하지 않음. `ActiveTarget`/command lifecycle/Result/`RecoverableErrors`처럼 run 내용을 드러내는 조회·구독은 해당 command owner 또는 오케스트레이터 내부 감사 주체로 제한. `DeckIdentity`/`DeckSections`/`CalibrationStatus`/`HeadGeometry`/`TransferLimits`/`ResultQcModes` 같은 운용 descriptor는 registry bootstrap에 필요한 범위에서 허용. raw deck layout·transform·calibration table·machine 좌표는 service/admin API 전용.
   - **구독·조회 남용 방지**: 서버는 client identity별 동시 subscription 수, property 갱신률, lifecycle 조회 빈도에 상한을 둠. 초과 시 표준 오류로 거부 후 감사 로그에 기록.
5. **TOCTOU 커밋점**: `reserve=False`면 `plan.run()` 커밋 시 스케줄러가 Lock을 **원자적으로 확보** → 실패 시 다른 가용 장비 재배정/중단(layer2 §dry_run↔run 간극). `dry_run(reserve=True, ttl=...)`는 dry-run 단계에서 Lock을 먼저 잡고 같은 `LockIdentifier`를 Plan에 귀속.
6. **예약 refresh — 확정**: `reserve=True`로 잡은 Lock은 `Timeout/2` 이하 주기로 `LiquidHandling.KeepLeaseAlive`(§6.3, 물리 동작 없는 lock-protected no-op)를 호출해 timeout을 갱신. refresh 실패 또는 deadline miss 1회면 Plan은 invalidated 상태가 되고, `run`은 재검증·재Lock 없이는 진행 안함.
7. **TTL 상한 — 확정**: SiLA2 baseline의 `Timeout=0`(무기한)과 달리 모든 Lock은 배포별 `max_lock_ttl` 이하의 유한 timeout을 가져야 하며, heartbeat miss 또는 timeout 만료 시 서버가 lock을 해제함. 복구 대기(`RecoverableErrors`)도 별도 `max_recovery_wait` 상한을 갖고, 초과 시 command를 `finishedWithError`로 강등.
8. **관리자 break-glass**: 장비 점유 DoS·오케스트레이터 장애·안전 정지를 위해 운영자 권한의 강제 unlock/preemption 절차 도입. 강제 해제는 감사 로그에 원인, 주체, 기존 owner SPKI hash, command UUID를 기록, 진행 중 command는 안전한 중단 가능 지점에서만 정지.

> **디바이스 경계의 접근제어 = Lock.** 사용자 token/RBAC(owner/group/scope)는 **① ↔ ② 경계**의 관심사로써
> 오케스트레이터가 신뢰경계다(layer2 §권한). 디바이스는 **자신의 단일 lease 소유자를 신뢰** —
> SiLA2 `AuthenticationService`를 사용자-레벨 RBAC로 모델링하지 않음.

### 5.3 취소·오류 회복

- **취소** (`CancelController`, `core.commands`): `CancelCommand(CommandExecutionUUID)`(또는 `CancelAll`)로 진행 중 observable command 중단. **스펙 계약**: 취소 시 서버는 command status를 **`finishedWithError`로 전이**(취소 사유 메시지 동반)하고 **회귀/재개 불가**.
  - **범위 제한**: `CancelCommand`/`CancelAll`은 동일 `LockIdentifier`와 동일 mTLS client SPKI에 귀속된 command에만 적용. `CancelAll`은 장비 전체 kill-switch가 아니라 **현재 lease owner의 미종료 command 집합**에 대한 축약 명령. 운영자 break-glass 취소는 §5.2의 강제 unlock/preemption 절차를 사용.
  - **물리 안전 재량**: 물리 자원 특성상 이미 시작된 stroke는 **완주 후** 중단; 안전하게 취소 불가한 구간이면 서버가 **`OperationNotSupported`** 로 거부 (스펙 허용). 진행/중단 지점은 `ExecutionInfo`로 관측.
  - **취소 후 재분주 경계**: 취소는 `finishedWithError` → **`DispenseResult` 회수 불가**(§5.1 검증). 따라서 "분주 진행 정도"는 **Lane A `ActiveTarget` 마지막 관측값 + `DispensePhase` Intermediate Response 마지막 클라이언트 보관값**으로 재구성(§5.1·§6.3·§6.4).
- **오류 회복** (`ErrorRecoveryService/v1`): 물리 오류는 SiLA2 **Defined Execution Error**로 반환(§6.5). **회복 가능** 오류는 즉시 종료 대신, 서버의 observable property **`RecoverableErrors`**(오류 메시지·Command Identifier·Command Execution UUID·**서버가 광고하는 continuation option** 목록)에 얹혀 command가 **정지 대기**.
  - 클라이언트(스케줄러) 선택: **`ExecuteContinuationOption(UUID, option, InputData)`**(서버 광고 옵션 중 택1, option이 추가 입력을 요구할 때 `InputData` 사용) / **`AbortErrorHandling(UUID)`**(표준 오류로 강등 = 취소와 동일 종료) / **`SetErrorHandlingTimeout`**(무응답 시 자동 강등 시한).
  - 이진 continue/abort가 아니라 **서버가 정의한 named option 집합** 기반 — option 문자열의 기준은 서버(§6.5 권장 어휘).
  - **Lock 상호작용**: 회복 대기 중 command는 아직 미종료 → **lease(Lock) 유지**. 무한 점유 방지는 `SetErrorHandlingTimeout`과 §5.2 `max_recovery_wait`가 가드(→ layer2 lease/preemption 정책과 연동).

---

## 6. Domain Feature — `LiquidHandling/v1` (FDL)

> **FDL 계약은 설계 확정, XML 산출물은 구현 단계에서 작성.** 구조 템플릿은 `sila_cpp`의 `HelloSiLA2/TemperatureController`
> (observable command `ControlTemperature` + observable property `CurrentTemperature`)를 따름(layer3 §PoC).
> 정확한 XML 파일은 구현 단계에서 FDL 작성 → codegen → XSD 검증으로 확인.

### 6.1 명령 단위 = **pass 1개 = command 1개** (per-well 아님)

하나의 `Dispense` 명령은 **한 분주 용액에 대한 볼륨 맵(1xH×W) 하나를 실은 command 1개**로 구성.
well을 개별 command로 나누지 **않음**(liquidhandler.ipynb §3 "well이 개별 DAG 노드로 쪼개지지 않음").

- **볼륨 맵 → stroke 분해는 서버 내부 책임**(layer3 "통신·내부 동작을 서버 내부에 흡수").
  96채널 헤드 = 1 stroke, 8채널 = 12 stroke, 1채널 = 96 stroke … 클라이언트는 관여하지 않음.
- **멀티 헤드 — 확정.** 장비가 헤드 2개(1채널 + 8채널) 이상을 가지면 command의 `HeadSelector`(§6.3)가 어느 헤드로 실행할지 지정. **`VolumeMap` shape는 헤드와 무관하게 항상 타깃 ware geometry(H×W)** — 헤드는 stroke 분해 방식만 바꿈(1채널=well당 stroke, 8채널=열당 stroke). 스케줄러는 `HeadGeometry[HeadSelector]` footprint로 stroke 수 = f(맵 점유 well, **선택 헤드** footprint) 산출.
- **ganged 8채널 feasibility — 확정.** 8채널 헤드가 시린지 8개를 단일 플런저(P2)로 **ganged** 구동하면(=`HeadGeometry.PerChannelIndependent=false`), 한 stroke의 8 well은 **동일 볼륨**만 가능하고 **열 내부 개별 well skip 불가**(전 tip 동시 흡입/토출). 따라서 `HeadSelector=multi8`은 대상 각 열의 8행 볼륨이 **균일**(또는 전부 0)이어야 함. 비균일·부분 열은 1채널 헤드로 라우팅. 위반 시 §6.5 `HeadMapIncompatible`. 1채널 헤드는 tip 1개라 이 제약 없음.
- 스케줄러는 헤드 geometry(`HeadGeometry` footprint Rows×Cols, §6.4)를 **property로 읽어 stroke 수 산출 → ETA 추정에만** 사용. stroke→시간 변환은 **디바이스가 아니라 스케줄러**가 담당. 디바이스는 기하 fact만 노출.
- `volume == 0`인 well = **건너뜀**(맵 안에서 표현, 별도 well-addressing 없음). 단 ganged 8채널의 열 내부 skip은 위 제약 적용.

### 6.2 볼륨 맵 데이터 타입

SiLA2에 2-D 배열 native 타입이 없으므로 **행-우선(row-major) `List<List<Real>>`**로 표현.
원소는 **Constrained Real**: `Unit=µL` + 범위 제약. 이 제약은 **스케줄러가 읽어** 매칭· `dry_run` feasibility에 사용(layer3 §feature 검색).

```xml
<Parameter>
  <Identifier>VolumeMap</Identifier>
  <DisplayName>Volume Map</DisplayName>
  <Description>행-우선 (H×W) well별 분주량. 0 = 건너뜀. 타깃 ware geometry와 일치해야 함.</Description>
  <DataType>
    <List>
      <DataType>
        <List>
          <DataType>
            <Constrained>
              <!-- 분주량은 소수 µL(예 12.5) 표현을 위해 Real 사용. -->
              <DataType><Basic>Real</Basic></DataType>
              <Constraints>
                <Unit>
                  <Label>µL</Label>
                  <Factor>0.000000001</Factor>   <!-- µL → m³; xs:decimal이라 과학 표기법(1e-9) 금지 -->
                  <Offset>0</Offset>
                  <UnitComponent><SIUnit>Meter</SIUnit><Exponent>3</Exponent></UnitComponent>
                </Unit>
                <MinimalInclusive>0</MinimalInclusive>
                <MaximalInclusive>300</MaximalInclusive>   <!-- 예: 1–300µL 헤드 범위 -->
              </Constraints>
            </Constrained>
          </DataType>
        </List>
      </DataType>
    </List>
  </DataType>
</Parameter>
```

> **`List<List<Real>>` 요청·검증·응답 프로세스.**
>
> | 구분 | 내용 | 결과 |
> |---|---|---|
> | **모양** | dense H×W 행렬, 행-우선 `List<List<Constrained Real>>`, 원소 = µL 볼륨(0 = 건너뜀) | layer1 `(8,12)` ndarray ↔ 요청 `VolumeMap` ↔ 응답 `DispensedVolume`(§6.3) 모두 2D → DeviceAdapter가 reshape 없이 그대로 주고받음 |
> | **보낼 때 크기** | 항상 인라인, 메시지 하나 | Binary Transfer 사용 안 함 |
> | **서버 검증** | inner-list 길이가 같은 지는 타입이 못 잡음(ragged 허용) → 서버가 **인라인 well 좌표 배열·헤드 모드와 대조** | 불일치 시 `GeometryMismatch`(§6.5). 응답 `DispensedVolume`도 같은 규칙 |
> | **스케줄러 읽기** | `Constrained` 원소의 **Unit(µL)·범위를 타입에서 바로** 읽음 | 매칭·`dry_run` feasibility(layer3 §feature 검색). shape·dtype·unit을 따로(OOB) 맞출 필요 없음 |
>
> **크기 상한과 early reject.** Binary Transfer를 쓰지 않으므로 서버는 gRPC message size, outer/inner list 길이, string 길이에 hard cap을 적용.
> 기본 상한은 배포 profile에서 정하되, `VolumeMap`/`Mask`는 장비가 지원하는 최대 ware footprint를 넘을 수 없고, 모든 `String` parameter는 device-local identifier로 필요한 길이만 허용.
> cap 초과·ragged list·NaN/Inf Real·음수 반복 횟수 등은 물리 동작 시작 전 Defined Execution Error 또는 표준 validation error로 거부.


### 6.3 명령 (Commands)

아래 타입 표기는 **계약 설명용 약식**. 실제 FDL 설계 시 SiLA2 XSD가 허용하는 형태만 사용.

- `String{a,b,c}` → `Constrained Basic String` + `<Set><Value>...</Value></Set>`.
- `Structure{...}` → FDL `Structure`와 `Element` 목록.
- FDL에는 optional parameter 문법이 없으므로 `?`를 사용하지 않음. layer1/DeviceAdapter의 optional API는 SiLA 경계에서 **별도 command 선택** 또는 **sentinel 값**으로 변환.
- 이 ICD의 v1 결정: `MixAfter`는 `Dispense` optional parameter가 아니라 **`DispenseAndMix` 별도 command**로 변환. layer1의 `Dispense(..., mix_after=...)`는 Adapter가 `DispenseAndMix`로 번역.
- 선택 `Mask`는 FDL에서 optional로 만들지 않음. `Mask:List<List<Boolean>>`는 항상 존재하고, **빈 outer list = 전체 well**로 해석. 비어 있지 않으면 타깃 ware geometry와 동일한 직사각형 boolean matrix 필요.

| Command | Observable | Parameter | Response | 대응 pass (layer1) |
|---|:---:|---|---|---|
| **`Dispense`** | Yes | `HeadSelector:String enum(single,multi8)`, `SourceLabel:String`, `SourceWareId:String`, `SourceDeckSlot:String`, `SourceWareGeometryId:String`, `SourcePosition:String`, `SourceWellCoords:List<Structure{X:Real,Y:Real,Z:Real}>`, `VolumeMap`(§6.2), `TargetWareId:String`, `TargetDeckSlot:String`, `TargetWareGeometryId:String`, `TargetWellCoords:List<Structure{X:Real,Y:Real,Z:Real}>`, `LiquidProfile:Structure{...}`, `TipPolicy:String enum(none,once,always)` | `DispenseResult` | `exp.exec.Dispense` |
| **`DispenseAndMix`** | Yes | `HeadSelector:String enum(single,multi8)`, `SourceLabel:String`, `SourceWareId:String`, `SourceDeckSlot:String`, `SourceWareGeometryId:String`, `SourcePosition:String`, `SourceWellCoords:List<Structure{X:Real,Y:Real,Z:Real}>`, `VolumeMap`(§6.2), `TargetWareId:String`, `TargetDeckSlot:String`, `TargetWareGeometryId:String`, `TargetWellCoords:List<Structure{X:Real,Y:Real,Z:Real}>`, `LiquidProfile:Structure{...}`, `TipPolicy:String enum(none,once,always)`, `MixCycles:Integer(≥1)`, `MixVolume:Constrained Real(µL)` | `DispenseResult` | `exp.exec.Dispense(..., mix_after=...)` |
| ⤷ Intermediate Response `DispensePhase` | — | `String{MovingToWell,Dispensing,Mixing,ChangingTip,MovingAway}` (§5.1) — 에러 시 재사용/폐기 판단용, 클라이언트는 실행 내내 구독하고 자체 보관(재구독에 의존하지 않음) | — | — |
| **`Mix`** | Yes | `HeadSelector:String enum(single,multi8)`, `TargetWareId:String`, `TargetDeckSlot:String`, `TargetWareGeometryId:String`, `TargetWellCoords:List<Structure{X:Real,Y:Real,Z:Real}>`, `MixVolume:Constrained Real(µL)`(스칼라·전 well 균일), `Mask:List<List<Boolean>>`(빈 outer list=전 well, §6.5 기하 검증), `LiquidProfile:Structure{...}`, `Repetitions:Integer(≥1)` | `MixResult` | `exp.exec.Mix` |
| **`Wash`** | Yes | `HeadSelector:String enum(single,multi8)`, `WashStationId:String`, `Cycles:Integer(≥1)`, `NewTip:Boolean` | `WashResult` | `exp.exec.Wash` |
| **`PickTips` / `EjectTips`** | Yes | `HeadSelector:String enum(single,multi8)`, `TipRackWareId:String`, `TipRackDeckSlot:String`, `TipRackGeometryId:String`, `TipRackWellCoords:List<Structure{X:Real,Y:Real,Z:Real}>`, `Mask:List<List<Boolean>>` | `TipResult` | tip pass |
| **`KeepLeaseAlive`** | No | 없음. `LockIdentifier` metadata만 사용 | 없음 | `dry_run(reserve=True)` lease refresh |

- **`HeadSelector` — 확정.** 어느 물리 헤드로 command를 실행할지 지정하는 논리 선택(독립 Z라 물리 기구 모드가 아니라 순수 "어느 Z/플런저를 명령할지"). enum 값은 장비 `HeadGeometry` 리스트가 노출한 `HeadId` 집합의 부분(예: `single`=1채널, `multi8`=8채널). enum 밖 값은 FDL constrained string 검증으로 선차단, enum 안이나 미장착 헤드는 §6.5 `HeadMapIncompatible`(또는 capability mismatch)로 거부. 서버는 선택 헤드의 footprint·볼륨범위·ganged 여부(`HeadGeometry[HeadSelector]`, §6.4)로 stroke 분해·feasibility·좌표 오프셋을 결정. 단일 헤드 장비는 enum이 한 값뿐.
- **논리 식별자와 물리 주소 모두 전달 — 확정.** `SourceLabel`은 용액/contents 상관관계용 논리 라벨, `SourceWareId`/`TargetWareId`/`TipRackWareId`는 Plan·로그·결과 상관관계용 ware id. 실제 motion에는 `SourceDeckSlot`/`SourcePosition`/`TargetDeckSlot`/`TipRackDeckSlot`/`WashStationId` 같은 device-local address와 인라인 well 좌표 사용. `SourcePosition`은 source ware 내부 위치(예: reservoir channel/well `A1`)이며 pipette channel이 아님.
- **geometry 기준 — 확정.** ware geometry는 장비 종속 상태가 아니라 장비 사이를 이동하는 Registry tensor. `SourceWareGeometryId`/`TargetWareGeometryId`/`TipRackGeometryId`는 Plan 시점 geometry version 추적용 메타데이터이며, 서버 catalog 조회 키가 아님. Adapter는 Registry에서 ware-local well 좌표를 해소해 `SourceWellCoords`/`TargetWellCoords`/`TipRackWellCoords`로 인라인 전송. 서버는 geometry id 의미를 해석하지 않고, 좌표 배열 길이·row-major 순서·`VolumeMap`/`Mask` shape·헤드 모드 일치만 검증.
- **액체 특성 — 확정.** SiLA command는 별도 `LiquidClassId`를 받지 않음. 기준은 `SourceLabel`/`SourceWareId`가 가리키는 상위 용액 정의. Adapter/Registry는 이 용액 정의를 장비별 numeric `LiquidProfile`로 해석해 command에 인라인 전송. 지원하지 않는 용액 profile은 command 송신 전 layer2 `dry_run`에서 차단하고, 서버/driver는 전달된 profile의 물리 범위·finite 여부만 검증.
- **`DispenseAndMix` phase 순서 — 확정.** 일반 `Dispense`는 well별로 `MovingToWell → Dispensing → MovingAway`(필요 시 `ChangingTip`) 발행. `DispenseAndMix`는 같은 well에서 분주 직후 `MovingToWell → Dispensing → Mixing → MovingAway` 순서로 발행. `Mixing` 중 오류는 이미 투입된 well의 재분주가 아니라 재혼합/검증/폐기 판단으로 처리.
- **`TipPolicy` 미지원 처리 — 확정.** enum 밖의 값은 FDL constrained string 검증 오류로 command 실행 전 거부. enum 안의 값(`none`/`once`/`always`)이지만 장비/드라이버가 지원하지 않는 정책은 정상 경로에서 layer2 `dry_run`이 차단하며, 서버까지 도달하면 §6.5 `TipPolicyUnsupported` Defined Execution Error로 종료.
- `SourceLabel`과 ware id/address/geometry id/좌표/profile은 스케줄러가 Registry 해소 결과로 채움. 서버는 랩 전역 contents·ware geometry catalog를 갖지 않고, 전달받은 device-local address와 자기 deck calibration·head capability·물리 safety gate만 검증.
- **Mix = 2형태 / Wash = 독립**: **"바로 혼합"**(용액 투입 직후)은 layer1에서는 `Dispense`의 `mix_after` option, SiLA 경계에서는 `DispenseAndMix` command. **"나중에 혼합"**은 standalone `Mix` command. Mix 혼합량은 스칼라(전 well 균일), 부분 실행은 boolean `Mask`로 표현. **`Wash`**는 **`HeadSelector`가 가리키는 헤드의** 전체 팁 세척이라 마스크 없음(`Cycles`+`NewTip`).

`DispenseResult` (예):

```xml
<Response>
  <Identifier>DispensedVolume</Identifier>
  <DisplayName>Dispensed Volume Map</DisplayName>
  <Description>실행한 정규화 명령량 echo. 타깃 기하 (H×W), 단위 µL.</Description>
  <DataType><!-- §6.2와 동일한 List<List<Constrained Real µL>> --></DataType>
</Response>
<Response>
  <Identifier>PressureQc</Identifier>
  <DisplayName>Pressure QC</DisplayName>
  <Description>pLLD/TADM/씰 self-test 기반 결과 QC. not_applicable=압력 검증 비대상, passed=정상, failed=클롯·기포·숏샘플·누설 의심.</Description>
  <DataType><!-- Constrained Basic String Set(not_applicable, passed, failed) --></DataType>
</Response>
```

> layer1 `run()`이 반환하는 **분주 상태 `(8,12)` ndarray**의 원천. DeviceAdapter는 `DispensedVolume`을 ndarray로 흡수, `PressureQc`를 결과 metadata로 보존. 압력 센서는 직접 체적 측정값이 아니라 pLLD/TADM QC 근거이므로 `commanded|estimated|measured` 3분기 `ResultBasis`를 두지 않음.

### 6.4 Observable / Unobservable Properties (telemetry)

TriggerEvaluator·클로즈드 루프·레지스트리 상태 추적에 공급.

| Property | Observable | 타입 | 용도 |
|---|:---:|---|---|
| `DeviceStatus` | **Yes** | `String{idle,busy,error}` | 레지스트리 상태(idle/busy/error), lease 스케줄링 |
| `ReservoirLevels` | **Yes** | `List<Structure{Channel:String, Volume:Real µL}>` | 리저버 잔량 → `dry_run` 잔량 feasibility, closed-loop |
| `DeckOccupancy` | **Yes** | `List<Structure{Slot, WarePresent:Boolean}>` | 물리 점유 **감지**(§7) |
| `DeckIdentity` | No | `Structure{DeckId:String, CalibrationVersion:String, CalibrationHash:String}` | **운용 덱 식별자**. 장비가 소유한 deck id·calibration version/hash 광고. raw transform·기계 좌표 미포함 |
| `DeckSections` | No | `List<Structure{SectionId:String, Slots:List<String>, Available:Boolean}>` | scheduler catalog binding용 section/slot 식별자. slot→machine transform은 장비 내부 보유 |
| `CalibrationStatus` | No | `Structure{Version:String, Hash:String, State:String{current,stale,pending}}` | 현재 캘리브레이션 freshness 판단. raw calibration table 미포함 |
| `HeadGeometry` | No | `List<Structure{HeadId:String, Channels:Integer, Rows:Integer, Cols:Integer, Layout:String, PerChannelIndependent:Boolean, MinVolumeUl:Real, MaxVolumeUl:Real}>` | **헤드별 descriptor 리스트**(멀티 헤드). `HeadId`=`HeadSelector` enum 값(예 `single`/`multi8`), footprint(Rows×Cols)→stroke 수 산출(§6.1), `PerChannelIndependent=false`=ganged(열 균일 강제, §6.1), `Min/MaxVolumeUl`=**헤드별 볼륨 범위**(§6.2 `VolumeMap` FDL 제약은 전 헤드 superset, 실범위는 헤드별로 여기서). `Layout:String`=벤더 서술(산출 비입력). 단일 헤드 장비는 원소 1개 |
| `TransferLimits` | No | `Structure{DriverMaxPayloadBytes:Integer, InlineMaxWells:Integer, PayloadModes:List<String>, ChunkedPayload:Boolean, IdProvisioning:Boolean}` | **장비 내부 driver 전송 한계**. Registry 최초 등록 시 캐시. v1 기본값 = `DriverMaxPayloadBytes=4096`, `InlineMaxWells=96`, `PayloadModes=["inline_v1"]`, `ChunkedPayload=false`, `IdProvisioning=false`. 이 값은 SiLA2 gRPC message size가 아니라 ESP32↔STM32 내부 frame 한계 |
| `ResultQcModes` | No | `Structure{PressureQc:List<String>, Source:List<String>}` | 결과 QC capability. v1 `PressureQc=["not_applicable","passed","failed"]`, `Source=["pLLD","TADM","seal_self_test"]`. Registry 최초 등록 시 캐시해 QC 필수 작업의 `passed` 요구·`not_applicable` 허용·실패 정책 결정 |
| `ActiveTarget` | **Yes** | `Structure{TargetWareId:String, DeckSlot:String, Well:String}` | **논리 진행(Lane A, §5.1)** — 현재/직전 완료 덱·well, 실험자 진행표시 + 취소 시 재분주 경계. well-index(벤더 중립) |
> **운용 API / service-admin API 분리.** Task Scheduler가 쓰는 운용 표면은 `DeckIdentity`/`DeckSections`/`CalibrationStatus`처럼 식별자와 freshness만 제공. raw deck layout·deck transform·calibration table·machine 좌표·진단 raw data는 service/admin role, service mode 또는 exclusive Lock, 감사 로그가 필요한 별도 서비스 표면에서만 노출.
> `PipettorPose` 등 pose/diagnostic stream은 `SensorDiagnostics`/`MotionDiagnostics` service-admin 표면에 속하며, 운용 `LiquidHandling/v1` property로 노출하지 않음.

> **telemetry 소비 규칙.** mTLS+pin은 송신 identity만 보증. TriggerEvaluator는 property 값에 타당성 경계(plausibility bounds)를 적용.

### 6.5 Defined Execution Errors (FDL 선언)

ad-hoc 문자열이 아니라 **FDL의 Defined Execution Error**로 선언 → 클라이언트가 타입으로 분기.

| Error Identifier | 발생 조건 | 회복 등급 | 스케줄러 대응 |
|---|---|---|---|
| `VolumeOutOfRange` | 맵 원소가 **선택 헤드**의 범위(`HeadGeometry[HeadSelector].Min/MaxVolumeUl`) 밖 | **terminal** | pre-flight `dry_run`에서 차단(도달 전 거부) |
| `GeometryMismatch` | 인라인 `*WellCoords` 길이·row-major 순서·`VolumeMap`/`Mask` shape가 서로 불일치, ragged matrix, head mode와 좌표 배열 불일치 | **terminal** | `dry_run` hard 위반 (liquidhandler.ipynb §6) |
| `HeadMapIncompatible` | `HeadSelector`가 맵을 실행 불가 — 특히 ganged 8채널(`PerChannelIndependent=false`)에서 열의 8행 볼륨이 비균일이거나 부분 열(개별 tip skip), 또는 미장착 `HeadId` | **terminal** | `dry_run`에서 차단 → 비균일·부분 열은 `single` 헤드로 라우팅(§6.1) |
| `SourceEmpty` / `InsufficientVolume` | 리저버 잔량 부족 | **recoverable** | `ReservoirLevels`로 사전 감지. 실행 중이면 `RecoverableErrors`로 정지 → 재충전 후 `Continue`/`Abort` |
| `WareNotPresent` | `SourceDeckSlot`/`TargetDeckSlot`/`TipRackDeckSlot` 점유 감지 결과가 Plan 전제와 불일치 | **terminal** | 전제조건 위반 — 운송/수동 적재와 container-slot 호환성은 상위 레이어 처리 |
| `TipPolicyUnsupported` | enum 값은 유효하지만 해당 장비/드라이버가 그 tip policy를 지원하지 않음 | **terminal** | `dry_run`에서 차단. 서버 도달 시 장비 capability mismatch로 거부 |
| `TipPickupFailed` | 물리 팁 픽업 실패 | **recoverable** | `RecoverableErrors`로 정지 → `Retry`/`SkipWell`/`Abort` (§5.3) |
| `ResourceExhausted` | 장비 내부 결과 링/명령 큐/driver payload 한계 때문에 광고한 lifetime/result 보관 계약을 지킬 수 없음 | **terminal** | Registry가 `TransferLimits`와 `DeviceStatus`를 반영해 재시도 지연. UUID 미발급 거부가 원칙, 레이스 시 실행 전 terminal err |
| `NotDispatched` | UUID는 server admission journal에 남았으나 driver command가 아직 `driver_accepted` 되기 전 서버 리셋/링크 fault가 발생해 물리 실행 안 됨이 확정 | **terminal** | 같은 pass를 안전하게 재제출 가능. 기존 UUID는 lifetime 동안 이 terminal error로 replay |

- **terminal** = 표준 오류로 즉시 `finishedWithError`. 대부분 pre-flight `dry_run`에서 걸러 도달 전 거부.
- **recoverable** = `ErrorRecoveryService/v1`의 `RecoverableErrors` property에 얹혀 정지 대기 → 스케줄러가 continuation option 선택(§5.3).
- `GeometryMismatch`/`WareNotPresent`/`TipPolicyUnsupported`/`HeadMapIncompatible`/`ResourceExhausted`는 **FDL Defined Execution Error로 선언**. 서버는 command 수신 시에도 인라인 좌표·shape·deck address·head capability 기준으로 검증하되, 정상 경로에서는 layer2 `dry_run`이 먼저 잡아 command 실행 전에 차단. container-slot 호환성은 ware catalog 종속 제약이므로 장비가 판단하지 않음.
- **continuation option 권장 어휘 (기준 = 서버)**: `Retry`(같은 동작 재시도) · `SkipWell`(해당 well/tip 건너뜀) · `Continue`(오퍼레이터 물리 조치 후 진행, 예: 리저버 재충전) · `Abort`(강등 종료). **서버가 광고하는 실제 option이 우선**이고, ICD는 오케스트레이터가 이해해야 할 기준 어휘만 권장(벤더 중립).

(LockController 표준 오류 `InvalidLockIdentifier`는 §5.2에서 별도. 취소/회복강등 시 command → `finishedWithError`이며 lease(Lock)는 별도 `UnlockServer`까지 유지 — §5.2·§5.3.)

---

## 7. 상태 소유권 분리 (State Ownership Split)

**같은 "src=buffer"라도 두 주체가 다른 절반을 소유.**

| 상태 | 소유자 | 표면 | 근거 |
|---|---|---|---|
| **물리 덱 구성** (deck id·section id·calibration version/hash·slot id) | **Device** | `DeckIdentity`·`DeckSections`·`CalibrationStatus` property (§6.4) | 장비의 fact. 기계 좌표·slot transform은 장비 내부 보유, raw deck layout/transform은 service-admin 표면 전용 |
| **물리 점유·잔량 감지** | **Device** | `DeckOccupancy`·`ReservoirLevels` (센서) | 장비의 fact |
| **ware 정체성·내용물·ware-local geometry** (`plate-1`, `A1=buffer`, well 좌표 tensor) | **Orchestrator Registry** | `lab.ware` (ware.ipynb, 랩-레벨, device-독립) | ware는 device 사이를 이동. 장비 종속 catalog 아님 |
| **논리 `src` → 물리 주소·좌표·profile 바인딩** | **Orchestrator** (실행 시 해소) | Adapter가 ware id, deck slot, geometry id, 인라인 well 좌표, numeric liquid profile 주입 | recipe는 논리 이름만 |
| **ware 위치**(`location`) | **Orchestrator Registry** (read-view) | ware.ipynb §3 | 운송/적재는 상위 레이어 처리 |

**해소 흐름 (Adapter가 하는 번역):**

```
1. recipe:  Dispense(src="buffer", volume=(8,12))         ← 논리 이름
2. Scheduler: lab.ware에서 "buffer" 내용물이 이 핸들러 덱(deck-2 리저버 A1)에 있는지 확인
             + 타깃 plate-1 이 덱(deck-3)에 있는 지 확인    ← 레지스트리의 논리 신원(내용물·ware)이 실제 덱 슬롯에 있는지 대조
3. Adapter: Dispense(HeadSelector="multi8",
                     SourceLabel="buffer",
                     SourceWareId="reservoir-1", SourceDeckSlot="deck-2",
                     SourceWareGeometryId="nest_12_reservoir/v1", SourcePosition="A1",
                     SourceWellCoords=[(x,y,z)],
                     VolumeMap=[[...]],
                     TargetWareId="plate-1", TargetDeckSlot="deck-3",
                     TargetWareGeometryId="corning_96_wellplate_360ul_flat/v1",
                     TargetWellCoords=[96×(x,y,z)],
                     LiquidProfile={...}, ...)  meta=Lock
             ↑ 서버는 "지금 덱에 놓인 용기"로만 인지, 랩 전역 ware 카탈로그는 모름
```

> 서버는 **contents 카탈로그를 갖지 않음.** 슬롯 적재물의 의미(내용물 라벨)는 오케스트레이터가 부여.
> 따라서 장비가 검증할 수 없는 contents 의미는 오케스트레이터 신뢰경계 안에서만 사용,
> 서버는 전달된 `SourceLabel`을 motion·분주 안전 판단의 단독 근거로 사용하지 않음.

**좌표 프레임:** ware의 well/hole 좌표는 **로컬 프레임**(용기 왼위·안착면 = `(0,0,0)`, mm, device-독립; ware.ipynb §1.1). Adapter가 Plan 할당 시 이 좌표값을 인라인 전송.
**로컬 → 기계 좌표 변환은 Device의 몫** — 장비는 deck slot·section calibration으로 carrier 원점과 transform을 내부 합성. Task Scheduler는 최초 등록 시 deck id·section id·calibration version을 보유하고 freshness만 대조, raw 기계 좌표를 소유하지 않음.

---

## 8. Capability / 메타데이터 → Registry 매핑

서버 FDL·property와 Registry overlay가 스케줄러의 매칭·feasibility 입력으로 승격되는 경로.

| 서버가 노출 | 레지스트리 필드 | 스케줄러 사용처 |
|---|---|---|
| `LiquidHandling/v1` Feature 존재 | `capability="liquid_handling"` | capability 매칭(장비 후보 선정) |
| Registry overlay `feature_augments` 메타(서버 FDL 밖) | feature 연관형/독립형 구분 | layer1 `ext(...)` 연관/독립 판정(layer3). SiLA2 FDL XSD는 임의 `augments` 필드를 허용하지 않음 |
| `VolumeMap` Constraint(1–300µL) | 파라미터 범위·단위 | `dry_run` 볼륨 feasibility·매칭 |
| Registry-pinned geometry id + 인라인 `*WellCoords` | ware geometry catalog version + row-major 좌표 tensor | source position·shape·container-slot 호환성 검증, well 좌표 해소 후 command에 인라인 전송. 장비는 catalog 미보유 |
| source 용액 정의 → 장비별 numeric `LiquidProfile` | liquid behavior profile | 장비별 aspiration/dispense/mix 파라미터 선택, volume correction/LLD feasibility 후 command에 인라인 전송. 장비는 물리 범위·finite 여부만 검증 |
| `HeadGeometry` property(**per-head 리스트**: footprint·ganged·볼륨범위) | (등록 시 캐시, `HeadId`별) | `HeadSelector`별 stroke 수 산출 → ETA(§6.1), ganged feasibility(§6.1), 헤드별 볼륨 feasibility; stroke→시간 변환은 layer2 §C(스펙 prior+이력) |
| `TransferLimits` property | `driver_max_payload_bytes`, `inline_max_wells`, `payload_modes` | 최초 장비 등록 시 payload 생성 전략 결정. v1 `inline_max_wells=96` 초과 ware는 chunk/id-provisioning capability 없으면 `dry_run`에서 거부 |
| `ResultQcModes` property | `pressure_qc_modes`, `pressure_qc_sources` | 최초 장비 등록 시 QC 정책 결정. QC 필수 작업은 `PressureQc=passed`를 요구하고, 검증 비대상 명령의 `not_applicable` 허용 여부를 스케줄러 정책으로 판단 |
| `DeckIdentity`·`DeckSections`·`CalibrationStatus` property | deck id·section id·calibration version/hash·freshness | ware/deck catalog binding, calibration freshness 검증. raw transform은 레지스트리에 저장하지 않음 |
| `timing_class` (배포 메타) | `soft` | 노드 배치(soft는 일반 노드로 충분, layer3) |
| `DeviceStatus` observable | idle/busy/error | lease 큐·가용성 |

---

## 9. 시퀀스 — dry_run feasibility → run 커밋

```
─ dry_run (장비에 명령 없음, read-only 스냅샷) ─
  Adapter → SiLAService.ImplementedFeatures / FDL      (capability·constraint)
  Adapter → get DeckIdentity / DeckSections / CalibrationStatus / DeckOccupancy / ReservoirLevels / HeadGeometry / TransferLimits / ResultQcModes
  스케줄러: source/target/tiprack 기하 호환 · ware 존재·위치 · 슬롯 제약 · source 용액 profile 지원 · 볼륨범위·잔량 · ETA 계산
            + ware-local well 좌표와 numeric LiquidProfile 해소 → Plan 반환
            (liquidhandler.ipynb §6 dry_run 출력)

─ run 커밋 (single-writer) ─
  스케줄러: epoch 드리프트 감지 → 재검증
  Adapter → LockController.LockServer(LockId, ttl)      (원자적 lease 확보; 실패 시 재배정/중단)
  Adapter → get DeckOccupancy / ReservoirLevels / DeckIdentity / DeckSections / CalibrationStatus / HeadGeometry / TransferLimits / ResultQcModes
             (Lock 획득 직후 freshness 재검증; dry_run snapshot과 다르면 Plan invalidated)
  loop over pass:
     Adapter → Dispense/Mix/Wash(...address+geometry id+well coords+profile..., meta=LockId)      (observable command)
     Adapter ← Subscribe ExecutionInfo(UUID)             (status/progress/remaining time → run.stream(), lifetime → Adapter)
     Adapter ← Result(UUID) → DispensedVolume + PressureQc             (→ ndarray + QC metadata 흡수)
  Adapter → LockController.UnlockServer(LockId)
  (오류: Defined Execution Error → §6.5 대응 / CancelController.Cancel on abort)
```

---
