# ICD — Liquid Handler ↔ Task Scheduler (SiLA2 경계)

> **Interface Control Document (Draft)**
> 상위 개요: [`../plan.md`](../plan.md) · 인접: [layer2-orchestrator](layer2-orchestrator.md) · [layer3-device](layer3-device.md)
> 대응 API 스케치: [`../experiment_api_example/liquidhandler.ipynb`](../experiment_api_example/liquidhandler.ipynb) · [`ware.ipynb`](../experiment_api_example/ware.ipynb)
>
> 상태: **DRAFT** · 대상 인터페이스: **② Orchestrator/Scheduler ↔ ③ Liquid Handler Device** · 규약: **SiLA2**

---

## 0. 범위

오케스트레이터의 `DeviceAdapter`(= SiLA2 **클라이언트**)와
리퀴드 핸들러의 SiLA2 **서버**(layer3, C++ `sila_cpp`) 사이를 **gRPC로 건너가는 바이트 계약**을 규정.

> ⚠️ **DSL에 대한 규정은 layer1에서 다룸.**
> layer1의 텐서 API(`exp.Stack`, `exp.exec.Dispense`, `(K,8,12)` 볼륨 텐서)는 **Experiment layer**로써
> SiLA2 통신 규격에 해당되지 않음. (plan.md §2 "SiLA2 ≠ 실험 API").
> **"한 `Dispense` pass가 어떤 SiLA2 명령으로 번역되어 선으로 나가는가"**를 규정.

**아키텍처:**

```
① Experiment DSL        exp.Stack( Dispense(src="buffer", volume=(8,12)), Mix(...), ... )
   (layer1, 범위 밖)         │  operator가 기술
                            ▼
② DeviceAdapter          pass 열 → SiLA2 command 열로 번역 (이 ICD가 규정하는 경계 ↓↓↓)
   (SiLA2 client)            │
════════════════════════════╪═══════════════ SiLA2 / gRPC / HTTP2 (+ TLS) ═══════════════
                            ▼
③ Liquid Handler         SiLAService · LockController · LiquidHandling/v1 Feature
   (SiLA2 server, C++)       │  FDL로 선언한 command/property를 실행, stroke로 내부 분해
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
| **TLS 1.3** (RFC 8446) · **X.509**(RFC 5280) · **SPKI Pinning**(RFC 7469 계열 개념) | §3 mTLS·SPKI Pinning 신뢰 확립 |
| `plan.md` · `layer2-orchestrator.md` · `layer3-device.md` | 상위 아키텍처·스케줄링·DeviceAdapter 계약 |

---

## 2. 인터페이스 식별 (Interface Identity)

| 항목 | 값 |
|---|---|
| **엔드포인트 A (initiator)** | Orchestrator `DeviceAdapter` — SiLA2 **Client** (`unitelabs-sila`) |
| **엔드포인트 B (responder)** | Liquid Handler — SiLA2 **Server** (`sila_cpp`, C++), 장비당 1개 |
| **전송(transport)** | SiLA2 over **gRPC / HTTP2**, **TLS 필수**(SiLA2 Part A: 서버 자기서명 인증서 허용) |
| **디스커버리** | **SiLA2 Server Discovery (mDNS / DNS-DS)** — 서버가 `_sila._tcp` 광고, 레지스트리가 자동 등록(layer2 Device Registry) |
| **명령 방향** | **모든 command는 Orchestrator → Device 단방향 개시.** 서버는 observable property/command로 **telemetry만 push** (역방향 명령 없음) |
| **동시성 불변식** | **single-writer** — 임의 시점 한 장비에 lease 소유자 정확히 1개. `LockController`로 강제(§5.2, layer2 §장비 ownership) |
| **timing_class** | **`soft`** — 오케스트레이션 타임스케일(초~분). host 측 hard-RT 제어 루프 없음(layer3 §실시간성). 결정론적 지연을 **보장하지 않음** |

---

## 3. 연결·신뢰 확립 (Connection & Trust Establishment)

연결 전 **상호 인증** 필요. 인터페이스를 노린 위협은 *늘 존재*.
SiLA2 서버는 **다중 클라이언트 연결을 허용**하기에 (layer2 §장비 ownership),
단순 인증 외 **양방향 인증 + 채널 암호화 + 무결성**이 함께 필요.

| 계층 | 질문 | 메커니즘 | 위치 |
|---|---|---|---|
| **전송·identity (§3)** | "상대가 **등록된 identity**인가" (위장 아님) | **mTLS + TOFU SPKI Pinning** | 이 절 |
| 세션 인가 (§5.2) | "지금 쓸 권한자인가" | `LockController` (lease) | §5.2 |

> 독립적인 두 계층: mTLS가 *등록된 identity의 클라이언트/서버인가*를, Lock이 *인증된 클라이언트 중 지금 쓰는 1명인지*를 확인.

> **CA를 두지 않는다.** 랩 전역 Certificate Authority 개인키는 유출 시 *어떤 장비든 위조해 위험한 프로토콜을 흘려보낼 수 있는* 단일 급소가 된다. 대신 각 개체의 **안정적 identity 공개키(SPKI)를 상대가 pinning**, 폐기는 **pin 삭제**로 처리한다(§3.2). 장비 하나가 뚫려도 피해는 그 장비 하나에 한정.
> **DIY 장비 연결 가능**: 벤더 중립 — Pinning은 *등록된 키와의 동일성*만 검증하지 제조 출처를 묻지 않음. SPKI pin은 **identity continuity** 를 증명.

### 3.1 mTLS — 전송 신뢰의 뼈대 (Stage 1)

SiLA2 Part A가 TLS를 필수로 하고 서버 인증서를 요구하므로, 그 위에 **클라이언트 인증서를 더해 상호 TLS(mTLS)** 로 확장.  
스펙과 충돌 없는 배포 강화.

| 항목 | 규정 |
|---|---|
| **프로토콜** | **TLS 1.3** (하위 폴백 금지). SiLA2 gRPC/HTTP2 전송 위에 적용 |
| **상호 인증** | Orchestrator(client)·Liquid Handler(server) **각자 자신의 X.509(self-signed) 제시 → 상대는 SPKI pin와 대조 검증** |
| **개인키 소유 증명** | X.509(self-signed)는 공개키 운반체로 역할. SPKI pin로부터 신뢰, **핸드셰이크가 그 공개키의 개인키를 지금 실제로 쥔 자임을 증명**(공개키만 훔쳐선 통과 불가) |
| **획득 보장** | 채널 **암호화**(도청 방지) + **무결성**(변조 방지) + **채널 바인딩**(MITM 방지) + **양방향 identity** |
| **클라이언트 검증(서버 측)** | 장비 서버는 클라이언트 공개키가 **Orchestrator SPKI pin와 일치**하는지 검증 → rogue orchestrator/client 차단 |
| **서버 검증(클라이언트 측)** | Adapter는 서버 공개키가 **SPKI pin와 일치** + **SPKI pin ↔ mDNS로 발견한 SiLA Server UUID 바인딩** 확인 → 스푸핑 장비 차단 (§3.2) |
| **실패 처리** | pin 불일치·미등록 pin·인증서 만료·UUID 불일치 → **연결 거부**(command 단계 도달 전). SiLA2 command/property 교환은 mTLS 성립 후에만 |

> §1의 "TLS 필수(서버 자기서명 허용)"는 SiLA2 Baseline.
> 여기에 **mTLS + SPKI Pinning**을 추가 요구(자기서명 단독은 rogue client를 막지 못하므로 프로덕션 부적합). SPKI pin는 identity를 고정.

### 3.2 SPKI Pinning — identity 앵커 (Stage 2)

상대가 등록된 identity인지 **상대가 보관한 SPKI pin**에 기반하여 판단.
각 개체(Orchestrator·각 Liquid Handler)는 **안정적 identity 공개키(SPKI)** 를 갖고, 상대는 그 SPKI를 pin한다.
(등록된 키와의 동일성 검증 — 제조 출처 무관, 벤더 중립적.)

- **TOFU (Trust On First Use)**: 최초 연결 시 상대 SPKI를 지문으로 고정(pin). 이후 매 연결마다 제시된 공개키를 pin과 대조.
- **pin 대상 = SPKI(공개키), cert 지문이 아님**: 안정 키 위에서 cert(유한 유효기간)가 회전해도 pin이 깨지지 않는다.
- **UUID 바인딩**: pin 레코드를 장비의 **SiLA Server UUID**(`SiLAService` feature 노출, §4)에 묶는다. → mDNS로 발견한 UUID와 pin된 키가 일치해야 신뢰(§3.1). UUID만 흉내낸 공격자는 pin된 개인키가 없어 차단.
- **pin 레지스트리 = Orchestrator allowlist**: `UUID ↦ SPKI pin`을 오케스트레이터가 보관(신뢰경계, layer2). **Device Registry epoch에 연동** — pin 추가/삭제/교체가 epoch를 올려 dry_run→run Time-of-check to time-of-use (TOCTOU) 감시(layer2 §장비 ownership)가 드리프트를 포착. 감사·백업 대상.
- **cert 수명**: 유한 유효기간 self-signed.
- **Key Ceremony**: identity 키 교체 시 **구 키가 신 키를 서명**해 제시 → 물리 재방문 없이 pin 연속성 유지. **백업 pin**(보조 키 병행 등록)으로 주 키 분실 대비.
- **폐기 = pin 삭제 (즉시, CRL 없음)**: 유출됐거나 회수한 장비는 오케스트레이터에서 pin만 지우면 → 다음 핸드셰이크부터 거부. star 토폴로지라 **한 곳에서 즉시** 끊긴다. 별도 CRL/OCSP responder가 필요 없다.

```
[상시 연결 — 매 세션, Stage 1+2]
  Adapter ─ mDNS 조회 ─▶ 장비 UUID·주소 발견
  Adapter ◀── TLS 1.3 mTLS 핸드셰이크 ──▶ 장비
     · 장비:   클라이언트 공개키 == pin된 Orchestrator SPKI?      (Rogue Client 차단)
     · Adapter: 서버 공개키 == pin된 SPKI + pin ↔ 발견 UUID 바인딩?  (Spoofing 차단)
  성립 ─▶ 이후 LockController.Lock → command (§5.2~6). 실패 ─▶ 연결 거부.
```

> **⚠ 감수하는 잔여 위험.**
> 1. **평이 TOFU의 최초-접촉 신뢰.** 첫 연결은 *누가 응답했는지 인증 없이* pinning — 공유 LAN에서 mDNS 레이스를 이긴 rogue가 정상으로 pin될 수 있다. (TOE/대역외 지문확인을 과설계로 배제.) 값싼 부분완화: **최초 pin은 운영 중이 아니라 통제된 셋업 창(신뢰 세그먼트)에서** 수행.
> 2. **등록됐지만 유출된 장비 → telemetry 오염.** mTLS+pin은 *등록된 identity* 를 증명할 뿐 그 identity가 보내는 *telemetry의 정직성* 은 보증하지 않는다. 등록된 채 뚫린 장비는 거짓 telemetry로 클로즈드-루프 트리거를 잘못 이끌 수 있다("온도 정상"을 위조해 다음 단계 강행). 피해는 그 장비 하나에 그치지만 ICD 차원에서는 막지 못한다 → 완화는 **layer2 TriggerEvaluator의 타당성 경계(plausibility bounds)** 에 맡긴다(§6.4·§7 참고).

> **경계 명확화.** 이 절이 다루는 것은 **오케스트레이터 ↔ 장비 간 인증**뿐이다.
> **사용자-레벨 인증(token/RBAC, owner/group/scope)** 은 **① ↔ ② 경계**의 몫이며, 거기서는 오케스트레이터가 신뢰경계다(layer2 §권한, §5.2).
> 장비는 mTLS로 인증된 단일 lease 소유자만 신뢰할 뿐, 사용자를 구분하지 않는다.

---

## 4. 서버 Feature Catalogue

리퀴드 핸들러 서버는 아래 Feature들을 FDL로 선언한다.
FQI 형식은 `<Originator>/<Category>/<Feature>/v<Major>` (표준=`org.silastandard`, 벤더=역도메인).

| Feature (FQI) | 종류 | 필수 | 이 인터페이스에서의 역할 |
|---|---|:---:|---|
| `org.silastandard/core/SiLAService/v1` | Core | **필수** | 서버 identity: `ServerName`·`ServerUUID`·`ImplementedFeatures`·FDL 조회. 레지스트리 등록의 진입점 |
| `org.silastandard/core/LockController/v2` | Core | **필수** | **lease = Lock.** `LockIdentifier` 발급, single-writer 강제(§5.2) |
| `org.silastandard/core/CancelController/v1` | Core | **필수** | layer1 `run.cancel()` / 스케줄러 abort의 백엔드 |
| `org.silastandard/core/ErrorRecoveryService/v1` | Core | 권장 | 물리 오류(팁 픽업 실패 등) 후 continue/abort 협상 |
| **`lab.sica/devices/LiquidHandling/v1`** | Domain | **필수** | **분주 능력의 본체** — `Dispense`/`Mix`/`Wash`/tip + 덱·리저버 telemetry (§6) |
| `com.<vendor>/devices/<VendorFeature>/v1` | Vendor | 선택 | 벤더 전용(LLD, air-gap 등). layer1 `ext(...)`로 노출. `augments`로 연관형 표시(layer3 §feature 검색) |

> **capability 매핑:** `LiquidHandling/v1` Feature의 존재 = Device Registry의 `capability="liquid_handling"`.
> 스케줄러는 이 capability로 장비를 매칭한다(liquidhandler.ipynb §0의 `lab.device(attribute="liquid_handling")`).

---

## 5. 공통 상호작용 계약

### 5.1 Observable command 실행 (SiLA2 Part B)

분주는 수 초~수십 초 걸리는 물리 동작 → **모든 실행 command는 Observable**이어야 한다.
(layer3 PoC done 기준: unobservable + **observable command/property 구독 스트리밍**까지 검증 필요.)

```
Client(Adapter)                         Server(Handler)
   │  Dispense(VolumeMap, meta=Lock)        │
   │───────────────────────────────────────▶│  파라미터 검증 → CommandExecutionUUID 반환
   │◀───────────────────────────────────────│  UUID
   │  Subscribe ExecutionInfo(UUID)          │
   │───────────────────────────────────────▶│
   │◀───────── ExecutionInfo 스트림 ─────────│  status: waiting→running, progress 0..1,
   │            (running, 0.4, ~8s) ...       │  estimatedRemainingTime
   │◀───────── ExecutionInfo(finished) ──────│
   │  Result(UUID)                           │
   │───────────────────────────────────────▶│
   │◀───────────────────────────────────────│  DispenseResult (§6.2)
```

- **`ExecutionInfo`**: `commandStatus`(waiting/running/finishedSuccessfully/finishedWithError) + `progressInfo`(0..1) + `estimatedRemainingTime` + `estimatedTotalTime`. → layer2 `dry_run` ETA 보정·`run.stream()` 진행표시에 공급.
- **중간 응답(Intermediate Response) — v1 Baseline = 미사용, 선택 프로파일 유보.** `ExecutionInfo`(progress+ETA)만으로 라이브 소비자(`run.stream()` 진행표시·`dry_run` ETA 보정)는 충족. 액추에이션 command는 **하위-동작(stroke) 상태를 command 종료 후에만 소비**(어느 well이 채워졌나 → 재분주/중단 판단)하므로 진행 중 stroke-level 스트리밍이 무가치 → 기본 미노출(§6.1 anti-chatty 원칙과 정합). TriggerEvaluator는 command 중간응답이 아니라 observable **property**(§6.4)를 구독한다.
  - **취소·오류 시 부분완료 귀속 (잔여 설계):** SiLA2는 `finishedWithError`(취소 포함, §5.3)에서 **Result 회수 불가 — `GetObservableCommandResult`가 응답 대신 오류를 raise**한다(검증됨). 따라서 "완료 마스크를 `DispenseResult`에 실어 취소 후 회수"는 **성립하지 않는다**. 부분완료 상태가 필요하면 오류를 견디는 **Intermediate Response 스냅샷** 또는 **지속 observable property(`CompletedMask`)** 가 carrier여야 한다. 이 요구의 실제 필요 여부·carrier 선택은 `CancelController`/`ErrorRecoveryService` 항목과 함께 확정(§10).

### 5.2 Lock = lease (single-writer 강제)

layer2 불변식 "lease 획득 = Lock 획득"의 구현.

1. 스케줄러가 장비 배정 시 `LockController.Lock(LockIdentifier, timeout)` 호출 → 배타 점유 획득.
2. **획득 후 모든 command 호출은 `LockIdentifier`를 SiLA2 Client Metadata로 동반**해야 한다.
   Metadata 누락/불일치 → 서버가 `InvalidLockIdentifier`(LockController 표준 오류)로 거부.
3. 실행 완료/실패 시 `LockController.Unlock(LockIdentifier)`.
4. **TOCTOU 커밋점**: `plan.run()` 커밋 시 스케줄러가 Lock을 **원자적으로 확보** → 실패 시 다른 가용 장비 재배정/중단(layer2 §dry_run↔run 간극). `dry_run(reserve=True, ttl=...)`는 Lock timeout으로 홀드.

> **디바이스 경계의 접근제어 = Lock.** 사용자 token/RBAC(owner/group/scope)는 **① ↔ ② 경계**의 관심사이고
> 오케스트레이터가 신뢰경계다(layer2 §권한). 디바이스는 **자신의 단일 lease 소유자를 신뢰**한다 —
> SiLA2 `AuthenticationService`를 사용자-레벨 RBAC로 모델링하지 않는다.

### 5.3 취소·오류 회복

- **취소**: `CancelController.Cancel(UUID)` → 진행 중 command 안전 중단. layer2는 물리 자원 특성상 이미 시작된 stroke는 완주 후 중단할 수 있음(장비 재량, `ExecutionInfo`로 관측).
- **오류 회복**: 물리 오류는 SiLA2 **Defined Execution Error**로 반환(§6.4). 회복 가능 오류는 `ErrorRecoveryService`로 continue/abort 협상.

---

## 6. Domain Feature — `LiquidHandling/v1` (FDL)

> 아래는 **초안 FDL**이다. 구조 템플릿은 `sila_cpp`의 `HelloSiLA2/TemperatureController`
> (observable command `ControlTemperature` + observable property `CurrentTemperature`)를 따른다(layer3 §PoC).
> 버전·TLS·정확한 XSD는 확정 시 스펙/예제와 대조 필요.

### 6.1 명령 입도 = **pass 1개 = command 1개** (per-well 아님)

**결정적 계약:** 한 `Dispense` pass는 **전체 볼륨 맵(H×W) 하나를 실은 command 1개**로 나간다.
well을 개별 command로 쪼개지 **않는다**(liquidhandler.ipynb §3 "well이 개별 DAG 노드로 쪼개지지 않음").

- **볼륨 맵 → stroke 분해는 서버 내부 책임**(layer3 "통신·내부 동작을 서버 내부에 흡수").
  96채널 헤드 = 1 stroke, 8채널 = 12 stroke … 클라이언트는 관여 안 함.
- 스케줄러는 헤드 기하를 **property로 읽어 ETA(stroke 수) 추정에만** 쓴다 — chatty per-well 표면을 만들지 않는다.
- `volume == 0`인 well = **건너뜀**(맵 안에서 표현, 별도 well-addressing 없음).

### 6.2 볼륨 맵 데이터 타입

SiLA2에 2-D 배열 native 타입이 없으므로 **행-우선(row-major) `List<List<Real>>`**로 표현.
원소는 **Constrained Real**: `Unit=µL` + 범위 제약. 이 제약은 **스케줄러가 읽어** 매칭·`dry_run` feasibility에 쓴다(layer3 §feature 검색).

```xml
<Parameter>
  <Identifier>VolumeMap</Identifier>
  <DisplayName>Volume Map</DisplayName>
  <Description>행-우선 (H×W) well별 분주량. 0 = 건너뜀. 타깃 ware 기하와 일치해야 함.</Description>
  <DataType>
    <List>
      <DataType>
        <List>
          <DataType>
            <Constrained>
              <DataType><Basic>Real</Basic></DataType>
              <Constraints>
                <Unit>
                  <Label>µL</Label>
                  <Factor>1e-9</Factor>          <!-- µL → m³ -->
                  <Offset>0</Offset>
                  <UnitComponent><SIUnit>Cubic Metre</SIUnit><Exponent>1</Exponent></UnitComponent>
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

> **스케일 폴백:** 96 float은 작아 문제없으나, 대형 맵/고밀도 plate는 SiLA2 **Binary Transfer**로
> `Binary`(numpy `.npy`/packed) 전송 가능(Part B). 초안 기본은 `List<List<Real>>`.

### 6.3 명령 (Commands)

| Command | Observable | Parameter | Response | 대응 pass (layer1) |
|---|:---:|---|---|---|
| **`Dispense`** | Yes | `SourceLabel:String`, `VolumeMap`(§6.2), `TargetWareId:String`, `TipPolicy:String{none,once,always}` | `DispenseResult` | `exp.exec.Dispense` |
| **`Mix`** | Yes | `VolumeMap`(마스크·혼합량), `Repetitions:Integer(≥1)` | `MixResult` | `exp.exec.Mix` |
| **`Wash`** | Yes | `Cycles:Integer(≥1)`, `NewTip:Boolean` | `WashResult` | `exp.exec.Wash` |
| **`PickTips` / `EjectTips`** | Yes | `TipRackWareId:String`, `Mask:List<List<Boolean>>` | `TipResult` | tip pass |

- **`SourceLabel`은 논리 내용물 이름 문자열**(예: `"buffer"`). **서버는 이것을 물리 슬롯으로 해소하지 않는다** — §7 참조.
- `TargetWareId`/`SourceLabel`은 스케줄러가 채워 넣는다(Registry 해소 결과). 서버는 "지금 이 덱 슬롯에 있는 용기"로만 인지.

`DispenseResult` (예):

```xml
<Response>
  <Identifier>DispensedVolume</Identifier>
  <DisplayName>Dispensed Volume Map</DisplayName>
  <Description>실제 분주 확인 볼륨 (센서 있으면 실측). 타깃 기하 (H×W), 단위 µL.</Description>
  <DataType><!-- §6.2와 동일한 List<List<Constrained Real µL>> --></DataType>
</Response>
```

> layer1 `run()`이 반환하는 **분주 상태 `(8,12)` ndarray**(측정 아님)의 원천. DeviceAdapter가 이 응답을 ndarray로 흡수(layer1 §I/O 규약).

### 6.4 Observable / Unobservable Properties (telemetry)

TriggerEvaluator·클로즈드 루프·레지스트리 상태 추적에 공급.

| Property | Observable | 타입 | 용도 |
|---|:---:|---|---|
| `DeviceStatus` | **Yes** | `String{idle,busy,error}` | 레지스트리 상태(idle/busy/error), lease 스케줄링 |
| `ReservoirLevels` | **Yes** | `List<Structure{Channel:String, Volume:Real µL}>` | 리저버 잔량 → `dry_run` 잔량 feasibility, closed-loop |
| `DeckOccupancy` | **Yes** | `List<Structure{Slot, WarePresent:Boolean}>` | 물리 점유 **감지**(§7) |
| `DeckLayout` | No | `List<Structure{Slot:String, Accepts:List<String>, Capacity:Real}>` | **정적 덱 descriptor**(슬롯 제약) |
| `HeadGeometry` | No | `Structure{Channels:Integer, Layout:String}` | ETA stroke 추정 입력(§6.1) |

> **PoC done 기준(layer3):** 위 observable property를 **구독해 스트리밍 수신**까지가 인터페이스 검증의 필수 절반.
> observable command + observable property 둘 다 없으면 TriggerEvaluator·클로즈드 루프의 위험한 절반이 미검증.

> **⚠ 인증 ≠ telemetry 무결성.** mTLS+pin(§3)은 이 property를 보내는 개체가 *등록된 identity* 임을 증명하지, 값이 *정직* 함을 보증하지 않는다. 등록된 채 뚫린 장비는 거짓 telemetry로 클로즈드-루프 트리거를 잘못 이끌 수 있다(§3.2 잔여위험 2). 이 값을 트리거·자동 진행의 근거로 쓰는 소비자(layer2 TriggerEvaluator)는 **타당성 경계(plausibility bounds)** 를 걸어야 한다 — property 값을 그대로 믿어선 안 된다.

### 6.5 Defined Execution Errors (FDL 선언)

ad-hoc 문자열이 아니라 **FDL의 Defined Execution Error**로 선언 → 클라이언트가 타입으로 분기.

| Error Identifier | 발생 조건 | 스케줄러 대응 |
|---|---|---|
| `VolumeOutOfRange` | 맵 원소가 헤드 범위(1–300µL) 밖 | pre-flight `dry_run`에서 차단(도달 전 거부) |
| `GeometryMismatch` | `VolumeMap` shape ≠ 타깃 ware 기하 | `dry_run` hard 위반 (liquidhandler.ipynb §6) |
| `SourceEmpty` / `InsufficientVolume` | 리저버 잔량 부족 | `ReservoirLevels`로 사전 감지, 실행 중이면 abort/pause |
| `WareNotPresent` | `TargetWareId`가 덱에 없음 | 전제조건 위반 — 운송/수동 적재(deferred) |
| `SlotConstraintViolated` | 용기가 허용 슬롯 밖(예: wellplate를 tiprack 슬롯) | `dry_run` 슬롯 제약 검사 |
| `TipPickupFailed` | 물리 팁 픽업 실패 | `ErrorRecoveryService`로 재시도/중단 |

(LockController 표준 오류 `InvalidLockIdentifier`는 §5.2에서 별도.)

---

## 7. 상태 소유권 분리 (State Ownership Split) — ICD의 핵심

**같은 "src=buffer"라도 두 주체가 다른 절반을 소유한다.** 이 분리를 어기면(ware 내용물을 서버에 밀어넣으면)
장비-독립 재사용성(liquidhandler.ipynb §4 "어느 랩/핸들러든 재사용")이 깨진다.

| 상태 | 소유자 | 표면 | 근거 |
|---|---|---|---|
| **물리 덱 구성** (슬롯·accepts·capacity) | **Device** | `DeckLayout` property (§6.4) | 장비의 fact |
| **물리 점유·잔량 감지** | **Device** | `DeckOccupancy`·`ReservoirLevels` (센서) | 장비의 fact |
| **ware 정체성·내용물** (`plate-1`, `A1=buffer`) | **Orchestrator Registry** | `lab.ware` (ware.ipynb, 랩-레벨, device-독립) | 벡터는 device 사이를 흐름 |
| **논리 `src` → 물리 슬롯 바인딩** | **Orchestrator** (실행 시 해소) | Adapter가 `SourceLabel`+`TargetWareId`로 주입 | recipe는 논리 이름만 |
| **ware 위치**(`location`) | **Orchestrator Registry** (read-view) | ware.ipynb §3 | 운송/적재는 deferred |

**해소 흐름 (Adapter가 하는 번역):**

```
1. recipe:  Dispense(src="buffer", volume=(8,12))         ← 논리 이름
2. 스케줄러: lab.ware에서 "buffer" 내용물이 이 핸들러 덱(deck-2 리저버 A1)에 있는지 확인
             + 타깃 plate-1 이 덱(deck-3)에 present 확인    ← Registry 정체성을 물리 슬롯에 오버레이
3. Adapter: Dispense(SourceLabel="buffer", VolumeMap=[[...]], TargetWareId="plate-1", ...)  meta=Lock
             ↑ 서버는 "지금 덱에 놓인 용기"로만 인지, 랩 전역 ware 카탈로그는 모름
```

> 서버는 **contents 카탈로그를 갖지 않는다.** "이 슬롯에 무엇이 놓였나"의 의미(내용물 라벨)는 오케스트레이터가 부여.
> 그래서 같은 recipe가 내용물만 맞으면 다른 랩/핸들러에서 재사용된다.

**좌표 프레임:** ware의 well/hole 좌표는 **로컬 프레임**(용기 왼위·안착면 = `(0,0,0)`, mm, device-독립; ware.ipynb §1.1).
**로컬 → 기계 좌표 변환은 Device의 몫** — `DeckLayout` 슬롯이 carrier 원점을 얹는 위치를 규정. ICD 경계에서 좌표는 ware 로컬 프레임으로 전달.

---

## 8. Capability / 메타데이터 → Registry 매핑

서버 FDL·property가 어떻게 스케줄러의 매칭·feasibility 입력으로 승격되는가.

| 서버가 노출 | 레지스트리 필드 | 스케줄러 사용처 |
|---|---|---|
| `LiquidHandling/v1` Feature 존재 | `capability="liquid_handling"` | capability 매칭(장비 후보 선정) |
| Vendor Feature `augments` 메타 | feature 연관형/독립형 구분 | layer1 `ext(...)` 연관/독립 판정(layer3) |
| `VolumeMap` Constraint(1–300µL) | 파라미터 범위·단위 | `dry_run` 볼륨 feasibility·매칭 |
| `HeadGeometry` property | (등록 시 캐시) | ETA stroke 수 추정(§6.1, layer2 §C) |
| `timing_class` (배포 메타) | `soft` | 노드 배치(soft는 일반 노드로 충분, layer3) |
| `DeviceStatus` observable | idle/busy/error | lease 큐·가용성 |

---

## 9. 시퀀스 — dry_run feasibility → run 커밋

```
─ dry_run (장비에 명령 없음, read-only 스냅샷) ─
  Adapter → SiLAService.ImplementedFeatures / FDL      (capability·constraint)
  Adapter → get DeckLayout / DeckOccupancy / ReservoirLevels / HeadGeometry   (property read)
  스케줄러: 기하 호환 · ware 존재·위치 · 슬롯 제약 · 볼륨범위·잔량 · ETA 계산 → Plan 반환
            (liquidhandler.ipynb §6 dry_run 출력)

─ run 커밋 (single-writer) ─
  스케줄러: epoch 드리프트 감지 → 재검증
  Adapter → LockController.Lock(LockId, ttl)            (원자적 lease 확보; 실패 시 재배정/중단)
  loop over pass:
     Adapter → Dispense/Mix/Wash(..., meta=LockId)      (observable command)
     Adapter ← Subscribe ExecutionInfo(UUID)             (running/progress/ETA → run.stream())
     Adapter ← Result(UUID) → DispensedVolume            (→ ndarray 흡수)
  Adapter → LockController.Unlock(LockId)
  (오류: Defined Execution Error → §6.5 대응 / CancelController.Cancel on abort)
```

---

## 10. 비목표 · 미해결 (Non-goals / Open)

**비목표(이 ICD 경계 밖):**
- **device 간 ware 운송(transport) capability** — 별도 오케스트레이션 과제(ware.ipynb §3, deferred).
- **수동 적재 흐름** (`location` 쓰기) — orchestrator 관심사, 이 경계 아님.
- **사용자-레벨 RBAC** — ①↔② 경계. 디바이스는 Lock 소유자만 신뢰(§5.2).
- **전역 RT 레이어** — timing_class=soft, host hard-RT 없음(plan.md §6).

**미해결 (확정 시 결정):** — `[x]` 확정 · `[~]` 방향 확정(세부 잔여) · `[ ]` 미결
- [~] **최초 pin 등록(enrollment) 운영 절차 (§3.2)** — CA/CSR 없음(Pinning 확정). **기준선 = 수동 trust-list(인증 admin 게이트) + 통제된 셋업 창**, **bootstrap 토큰은 선택 강화**. TOFU 최초-접촉 위험(§3.2 잔여위험 1) 완화 지점. 상세:
  - **참고 모델**: 공장 신원(제조사 PKI)에 앵커하는 계열(**IEEE 802.1AR IDevID/BRSKI RFC 8995**, **Matter DAC 어테스테이션**, TPM/secure element)은 *정품 증명*까지 주지만 **벤더 종속** → DIY 1급 지원(§3) 제약상 *강제* 불가. 대신 **로컬 신뢰 확립** 계열(**OPC UA 수동 trust-list** ⭐ 동일 산업 장비 표준·동형, SSH known_hosts TOFU, 페어링 모드)을 채택. 상용 장비가 IDevID를 갖고 오면 admin 게이트를 *자동 통과*시키는 추가 경로로 수용 가능(있으면 쓰고 없으면 수동).
  - **인증 admin 게이트 (기본, 충분)**: 신규 장비 SPKI의 pin 등록은 **오케스트레이터에 인증된 admin principal**(API Key/token, layer2 §권한)만 수행. blind TOFU("응답한 키 자동 pin") → **admin이 명시적으로 승인한 pin**으로 격상. pin 레지스트리에 **등록 principal·시각 기록**(감사·귀속). 안전성은 **"승인하는 그 키가 진짜 그 장비 키냐"**에 달려 있음 → **최초 등록을 통제된 셋업 창(격리 세그먼트, 장비 최초 반입 시)에서** 하면 이것만으로 충분(OPC UA 프로덕션 관행). 운영 중 공유 LAN blind TOFU는 rogue mDNS 레이스 위험 → 부족.
  - **bootstrap 토큰 (선택 강화, 운영 중 원격 등록이 실제로 필요해질 때)**: 인증 admin 세션이 토큰 발급 → 장비에 대역외(OOB) 적재 → 장비가 첫 TLS에서 토큰 증명 → **토큰까지 증명한 키만 pin**. rogue는 토큰이 없어 최초-접촉에서도 차단. (예전 "난수+시간" 직관의 정식 형태.)
    - **토큰 불변 조건(채널 무관)**: short-TTL · **1회성** · **첫 TLS 안에서 증명(채널 바인딩)** → 도청·재전송 불가. TLS가 감싸므로 저엔트로피여도 됨 — 관건은 "OOB로 들어갔다"는 사실.
    - **전달 채널 = 장비 클래스별 프로파일(USB로 못박지 않음)**: ICD는 **"토큰은 device-profile OOB 입력"** 추상만 규정. 구체 채널은 장비가 가진 물리 인터페이스에 좌우 — **프로비저닝 설정파일**(SBC 기반 DIY 대다수; *네트워크 닿기 전* 심어 제일 쌈) / **USB(스토리지·시리얼)**(그 config 파일의 배달 형태 중 하나) / **UART 콘솔** / **로컬 키패드·터치** / **장비 표시 지문 ↔ admin 대조**(=TOE 변형, 디스플레이 필요). SBC 위 C++ SiLA2 서버 기본형은 **프로비저닝 시점 config 심기**가 자연스럽고 USB는 그 배달 수단 중 하나.
  - **빠져나갈 수 없는 전제**: 새 장비 신뢰는 신뢰 못 하는 네트워크만으로 부트스트랩 불가 — **OOB 단계 1회 필수**. 선택지는 "OOB 하냐 마냐"가 아니라 *어느 OOB가 싸냐* — **① 셋업 창 격리(환경 통제)** / **② OOB 지문확인(TOE, 장비 표시수단 필요)** / **③ bootstrap 토큰(장비 토큰 입력 필요)**. API Key는 이 OOB를 없애주지 않고 토큰 방식에서 **발급 권위**로 기여.
  - **확정 필요(잔여)**: 토큰 방식 채택 시 — 증명 방식(TLS 내 metadata vs 별도 handshake)·TTL 수치·저위험 배포에서 admin 게이트만으로 갈지 여부. (기본 채널·기준선은 위에서 확정.)
- [x] **CA vs Pinning / 회전·폐기 정책 — 확정**: **TOFU + SPKI Pinning**(CA 없음, 피해 범위 제한) · 유한 유효기간 self-signed cert(폐기 수단 아님) · 키 교체=회전 세리머니(구 키가 신 키 서명)+백업 pin · **폐기=pin 삭제(즉시, CRL/OCSP 없음)**. 상세 §3.2
- [ ] `LiquidHandling/v1` FDL을 `sila_cpp` `TemperatureController` 예제와 대조해 XSD·버전 확정
- [ ] `LockController` 버전(v1/v2)과 `LockIdentifier` Client Metadata 정확한 전달 메커니즘 스펙 대조
- [ ] `VolumeMap` 최종 표현: `List<List<Real>>` vs Binary Transfer 임계 크기 결정
- [ ] Defined Execution Error 목록 확정 + `ErrorRecoveryService` continue/abort 프로토콜 상세
- [ ] `Mix`/`Wash` 비볼륨 pass의 partial-well 마스크 표현 확정
- [~] **observable command 진행/중간응답 계약 (§5.1)** — 기준선 = `ExecutionInfo`(progress+ETA)만, **Intermediate Response 미사용(선택 프로파일 유보)**: 액추에이션은 하위-동작 상태를 command 종료 후 소비 → 라이브 stroke 스트리밍 무가치. 잔여: 취소/오류 시 부분완료 귀속 필요 여부 — SiLA2가 `finishedWithError`에서 **Result 회수 불가(오류만 raise) 검증됨** → 완료 마스크는 Result 폴백 불가, **IR 스냅샷 또는 지속 property가 carrier**. `CancelController`/`ErrorRecoveryService` 항목과 함께 확정.
- [ ] 헤드 기하 → stroke ETA 모델(layer2 §C 추정기)과 property 계약 정합
