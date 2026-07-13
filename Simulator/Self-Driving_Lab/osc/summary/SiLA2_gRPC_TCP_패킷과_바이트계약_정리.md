# SiLA2 / gRPC / TCP 패킷 구조 이해

## 핵심 질문

> ICD에서 말하는 "바이트 계약(Byte Contract)"은 TCP/IP 패킷 안에서
> 어떻게 나타나는가?

결론부터 말하면,

-   **맞다.** 실제로 네트워크를 통해 TCP 패킷으로 전달된다.
-   하지만 **SiLA2는 TCP나 HTTP 같은 전송 프로토콜이 아니라 애플리케이션
    계층의 규약**이다.

------------------------------------------------------------------------

# 전체 계층 구조

``` text
┌──────────────────────────────────────────┐
│ Application                              │
│ (Task Scheduler / Liquid Handler SW)     │
├──────────────────────────────────────────┤
│ LiquidHandling Feature                   │
│ (Dispense, Mix, Wash ...)                │
├──────────────────────────────────────────┤
│ SiLA2                                    │
│ (Feature, Command, Property, Observable) │
├──────────────────────────────────────────┤
│ gRPC                                     │
├──────────────────────────────────────────┤
│ HTTP/2                                   │
├──────────────────────────────────────────┤
│ TLS                                      │
├──────────────────────────────────────────┤
│ TCP/IP                                   │
└──────────────────────────────────────────┘
```

## 각 계층의 역할

  계층                     역할
  ------------------------ -------------------------------------------------
  Application              실험 제어 프로그램
  LiquidHandling Feature   분주 장비 기능 정의(Dispense, Mix 등)
  SiLA2                    장비 API 규약(Command, Property, Observable 등)
  gRPC                     원격 함수 호출(RPC)
  HTTP/2                   gRPC 전송
  TLS                      암호화 및 인증
  TCP/IP                   네트워크 전송

------------------------------------------------------------------------

# Dispense 호출 과정

애플리케이션에서는

``` cpp
client->Dispense(request);
```

만 호출한다.

내부적으로는

``` text
Application
    ↓
LiquidHandling Feature
    ↓
SiLA2 Command
    ↓
gRPC
    ↓
HTTP/2
    ↓
TLS
    ↓
TCP Packet
```

순서로 내려간다.

------------------------------------------------------------------------

# 실제 TCP 패킷 내부

실제 전송 시에는 캡슐화(encapsulation)가 일어난다.

``` text
TCP Packet
└── TLS Record
    └── HTTP/2 Frame
        └── gRPC Message
            └── Protobuf
                └── DispenseRequest
```

따라서 **DispenseRequest는 TCP 헤더 안에 직접 존재하는 것이 아니라**,
여러 계층을 거쳐 Payload로 포함된다.

------------------------------------------------------------------------

# Wireshark에서는 어떻게 보일까?

## TLS를 복호화하지 못하는 경우

일반적으로는

``` text
Ethernet
└── IP
    └── TCP
        └── TLS Application Data
```

까지만 보인다.

gRPC와 protobuf 내용은 암호화되어 있으므로 볼 수 없다.

------------------------------------------------------------------------

## TLS를 복호화할 수 있는 경우

SSLKEYLOGFILE 등의 세션 키를 제공하면

``` text
Ethernet
└── IP
    └── TCP
        └── TLS
            └── HTTP/2
                └── gRPC
                    └── protobuf
                        └── DispenseRequest
```

처럼 더 깊은 계층까지 해석할 수 있다.

------------------------------------------------------------------------

# SiLA2도 Wireshark가 자동으로 해석할까?

부분적으로만 가능하다.

-   HTTP/2는 해석 가능
-   gRPC는 해석 가능
-   protobuf는 .proto 스키마가 있어야 사람이 읽기 쉬운 형태로 해석 가능

예를 들어

``` protobuf
DispenseRequest
{
    HeadSelector = HEAD_8CH
    VolumeMap = [[10,10,...]]
    LiquidProfile = ...
}
```

와 같은 구조를 보려면 protobuf 정의가 필요하다.

------------------------------------------------------------------------

# ICD에서 말하는 "바이트 계약"

ICD는 TCP나 TLS를 정의하는 문서가 아니다.

ICD가 정의하는 것은 다음과 같은 애플리케이션 데이터의 구조이다.

``` protobuf
DispenseRequest
{
    HeadSelector
    VolumeMap
    SourceLabel
    LiquidProfile
}
```

즉,

-   어떤 필드가 존재하는가
-   각 필드의 타입은 무엇인가
-   어떤 순서와 의미로 직렬화되는가

를 정의한다.

이것이 "바이트 계약(Byte Contract)"이다.

------------------------------------------------------------------------

# 비유

``` text
TCP/IP      = 택배 트럭
TLS         = 잠금 박스
HTTP/2      = 운송 규칙
gRPC        = 송장 형식
SiLA2       = 실험장비끼리 사용하는 공통 대화 규칙
LiquidHandling = 분주장비 전용 주문서
Application = 주문서를 작성하는 프로그램
```

Application이 작성한 Dispense 요청은 여러 계층을 거쳐 TCP 패킷으로
전달되고, 반대편에서는 역순으로 해석되어 장비가 실행한다.

------------------------------------------------------------------------

# 한 문장 요약

**ICD의 "바이트 계약"은 TCP/IP 패킷 속에 실려 전송되는 protobuf 메시지의
구조와 의미를 정의하는 것이며, SiLA2는 그 메시지가 어떤 Command와
Property를 가지는지를 규정하는 애플리케이션 계층의 표준이다.**
