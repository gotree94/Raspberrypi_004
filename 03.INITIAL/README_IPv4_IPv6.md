# 🌐 IPv4 vs IPv6 완벽 비교 가이드

> 인터넷 프로토콜 버전 4(IPv4)와 버전 6(IPv6)의 구조, 특징, 차이점을 정리한 기술 레퍼런스

---

## 📋 목차

- [개요](#개요)
- [주소 체계 비교](#주소-체계-비교)
- [헤더 구조](#헤더-구조)
- [핵심 기능 비교](#핵심-기능-비교)
- [IPv4 주소 고갈 문제](#ipv4-주소-고갈-문제)
- [IPv6 전환 기술](#ipv6-전환-기술)
- [IPv6 주소 유형](#ipv6-주소-유형)
- [자동 주소 설정 (SLAAC)](#자동-주소-설정-slaac)
- [실습 명령어](#실습-명령어)
- [임베디드 / IoT 관점](#임베디드--iot-관점)

---

## 개요

| 항목 | IPv4 | IPv6 |
|------|------|------|
| 표준 제정 | RFC 791 (1981) | RFC 8200 (2017) |
| 주소 길이 | **32비트** | **128비트** |
| 주소 개수 | 약 **43억** (2³²) | 약 **3.4 × 10³⁸** (2¹²⁸) |
| 표기 방식 | 10진수 점 구분 (`192.168.1.1`) | 16진수 콜론 구분 (`2001:db8::1`) |
| 헤더 크기 | 20 ~ 60 bytes (가변) | **40 bytes 고정** |
| NAT 필요 여부 | ✅ 필요 | ❌ 불필요 |
| 브로드캐스트 | ✅ 지원 | ❌ 없음 (멀티캐스트로 대체) |
| IPsec | 선택적 | **기본 내장** |
| 자동 주소 설정 | DHCP | **SLAAC** (서버 불필요) |
| 단편화 주체 | 라우터 + 송신자 | **송신자만** |
| 헤더 체크섬 | 있음 | **없음** (L4에서 처리) |
| QoS | ToS 필드 | **Flow Label** 필드 |
| 현재 보급률 | ~65% (주류) | ~40% (빠르게 확산) |

---

## 주소 체계 비교

### IPv4 주소 표기

```
점-10진수 표기 (Dotted Decimal Notation)

  192   .  168   .   1    .   1
8비트   8비트   8비트   8비트
└───────────── 총 32비트 ─────────────┘

예시:
  공인 IP:    203.0.113.1
  사설 IP:    192.168.0.1 / 10.0.0.1 / 172.16.0.1
  루프백:     127.0.0.1
  브로드캐스트: 255.255.255.255
```

### IPv6 주소 표기

```
콜론-16진수 표기 (Colon Hexadecimal Notation)

2001:0db8:85a3:0000:0000:8a2e:0370:7334
16비트 × 8 그룹 = 총 128비트

압축 규칙:
  1. 각 그룹 앞의 0 생략 가능
     0db8 → db8,  0000 → 0

  2. 연속된 0 그룹은 :: 로 단 한 번 생략 가능
     2001:0db8:0000:0000:0000:0000:0000:0001
     → 2001:db8::1

예시:
  전체 표기:  2001:0db8:85a3:0000:0000:8a2e:0370:7334
  압축 표기:  2001:db8:85a3::8a2e:370:7334
  루프백:     ::1  (IPv4의 127.0.0.1)
  링크-로컬:  fe80::1%eth0
```

### IPv4 주소 클래스

| 클래스 | 범위 | 용도 |
|--------|------|------|
| A | `1.0.0.0` ~ `126.255.255.255` | 대규모 네트워크 |
| B | `128.0.0.0` ~ `191.255.255.255` | 중규모 네트워크 |
| C | `192.0.0.0` ~ `223.255.255.255` | 소규모 네트워크 |
| D | `224.0.0.0` ~ `239.255.255.255` | 멀티캐스트 |
| E | `240.0.0.0` ~ `255.255.255.255` | 예약 (실험적) |

### 사설 IP 주소 범위 (RFC 1918)

| 범위 | CIDR | 사용 가능 호스트 수 |
|------|------|---------------------|
| `10.0.0.0` ~ `10.255.255.255` | `10.0.0.0/8` | 16,777,214 |
| `172.16.0.0` ~ `172.31.255.255` | `172.16.0.0/12` | 1,048,574 |
| `192.168.0.0` ~ `192.168.255.255` | `192.168.0.0/16` | 65,534 |

---

## 헤더 구조

### IPv4 헤더 (20 ~ 60 bytes)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version|  IHL  |Type of Service|          Total Length         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Identification        |Flags|      Fragment Offset    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Time to Live |    Protocol   |         Header Checksum       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Source Address                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Destination Address                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options                    |    Padding    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

주요 필드:
  IHL           헤더 길이 (4바이트 단위, 최솟값 5 = 20bytes)
  TOS           서비스 유형 (DSCP/ECN)
  TTL           홉 제한 (0이 되면 패킷 폐기)
  Protocol      상위 프로토콜 (TCP=6, UDP=17, ICMP=1)
  Header Checksum  헤더 오류 검출
```

### IPv6 헤더 (40 bytes 고정)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version| Traffic Class |           Flow Label                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Payload Length        |  Next Header  |   Hop Limit   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                                                               +
|                                                               |
+                         Source Address                        +
|                                                               |
+                                                               +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                                                               +
|                                                               |
+                      Destination Address                      +
|                                                               |
+                                                               +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

주요 필드:
  Traffic Class  DSCP + ECN (IPv4 TOS 대응)
  Flow Label     QoS 흐름 식별 (20비트, IPv4에 없음)
  Next Header    다음 헤더 유형 (확장 헤더 또는 상위 프로토콜)
  Hop Limit      IPv4 TTL 대응 (체크섬 없음 → 처리 속도 향상)
```

### 헤더 비교 요약

| 필드 | IPv4 | IPv6 | 비고 |
|------|------|------|------|
| 버전 | ✅ | ✅ | IPv4=4, IPv6=6 |
| 헤더 길이 | ✅ IHL | ❌ | IPv6는 고정 40bytes |
| TOS / Traffic Class | ✅ | ✅ | DSCP, ECN |
| 전체 길이 | ✅ Total Length | ✅ Payload Length | |
| 단편화 | ✅ ID/Flags/Offset | ❌ | IPv6는 확장헤더로 분리 |
| TTL / Hop Limit | ✅ TTL | ✅ Hop Limit | 동일 역할 |
| 프로토콜 / Next Header | ✅ Protocol | ✅ Next Header | |
| 헤더 체크섬 | ✅ | ❌ | IPv6는 L4에 위임 |
| 소스 주소 | ✅ 32bit | ✅ 128bit | |
| 목적지 주소 | ✅ 32bit | ✅ 128bit | |
| 옵션 | ✅ (가변) | ❌ | 확장 헤더로 대체 |
| Flow Label | ❌ | ✅ 20bit | QoS 향상 |

---

## 핵심 기능 비교

### NAT (Network Address Translation)

```
[IPv4 - NAT 필요]

사설망                         공인 IP 1개
─────────────────────────────────────────
192.168.0.10 ──┐
192.168.0.11 ──┤──► NAT 라우터 ──► 203.0.113.1 ──► 인터넷
192.168.0.12 ──┘    (포트 매핑)

[IPv6 - NAT 불필요]

각 장치에 고유한 전역 주소 부여
─────────────────────────────────────────
2001:db8::10 ──┐
2001:db8::11 ──┤──────────────────────────► 인터넷
2001:db8::12 ──┘
```

### 단편화 (Fragmentation)

| 구분 | IPv4 | IPv6 |
|------|------|------|
| 단편화 주체 | 라우터 + 송신자 | **송신자만** |
| MTU 탐색 | 선택적 | **필수** (Path MTU Discovery) |
| 라우터 부담 | 높음 | **없음** |
| 최소 MTU | 576 bytes | **1280 bytes** |

### 멀티캐스트 vs 브로드캐스트

```
IPv4 브로드캐스트 (255.255.255.255):
  모든 장치에게 패킷 전송 → 네트워크 부하 증가

IPv6 멀티캐스트 (ff00::/8):
  특정 그룹에만 전송 → 효율적

주요 IPv6 멀티캐스트 주소:
  ff02::1   모든 노드 (링크-로컬)
  ff02::2   모든 라우터 (링크-로컬)
  ff02::1:ff00:0/104  Solicited-Node (NDP 사용)
```

---

## IPv4 주소 고갈 문제

```
1981  IPv4 표준 제정 (RFC 791)
      약 43억 개 주소 → "충분하다"고 판단

1990s 인터넷 폭발적 성장

2011  IANA IPv4 주소 풀 고갈 (2월 3일)
      APNIC(아시아-태평양) 마지막 블록 배정

2012  RIPE NCC(유럽) 고갈
2015  ARIN(북미) 고갈
2017  LACNIC(중남미) 고갈

현재  중고 IP 거래 시장 형성
      NAT으로 임시 대응 중
      IPv6 전환 가속화
```

**NAT의 부작용:**
- P2P 통신 복잡 (포트 포워딩 필요)
- VoIP, 게임 등 실시간 서비스 지연
- 종단간(End-to-End) 투명성 손실
- 보안 감사 어려움

---

## IPv6 전환 기술

### 1. Dual Stack (이중 스택)

```
가장 일반적인 방식 — IPv4와 IPv6 동시 운용

[호스트]
  ├── IPv4 스택: 192.168.1.10
  └── IPv6 스택: 2001:db8::10

  → 상대방이 지원하는 프로토콜로 통신
  → 모든 장비/소프트웨어가 두 스택 지원 필요
```

### 2. Tunneling (터널링)

```
IPv4 네트워크 위에 IPv6 패킷을 캡슐화하여 전송

[IPv6 호스트] → [IPv6-in-IPv4 캡슐화] → [IPv4 망] → [역캡슐화] → [IPv6 호스트]

주요 방식:
  6to4     : 2002::/16 주소 블록 사용, 자동 터널링
  6in4     : 수동 설정 터널 (RFC 4213)
  Teredo   : NAT 환경에서도 동작 (UDP 포트 3544)
  ISATAP   : 기업 내부망용 자동 터널링
```

### 3. Translation (변환)

```
IPv4 ↔ IPv6 주소 및 패킷 변환

NAT64  : IPv6 → IPv4 변환 (RFC 6146)
DNS64  : AAAA 레코드 없는 도메인에 합성 AAAA 생성
         IPv6-only 클라이언트가 IPv4 서버에 접속 가능

[IPv6 클라이언트] ──► [NAT64 게이트웨이] ──► [IPv4 서버]
  2001:db8::1              64:ff9b::      203.0.113.1
```

---

## IPv6 주소 유형

| 유형 | 접두사 | 설명 |
|------|--------|------|
| 전역 유니캐스트 | `2000::/3` | 인터넷에서 라우팅 가능 (공인 IP) |
| 링크-로컬 | `fe80::/10` | 동일 링크 내부 통신 전용 |
| 사이트-로컬 (deprecated) | `fec0::/10` | 조직 내부 (RFC 3879로 폐기) |
| 고유 로컬 | `fc00::/7` | IPv4 사설 IP 대응 (RFC 4193) |
| 멀티캐스트 | `ff00::/8` | 그룹 통신 |
| 루프백 | `::1/128` | IPv4의 127.0.0.1 |
| 미지정 | `::/128` | 주소 없음 (IPv4의 0.0.0.0) |
| IPv4 매핑 | `::ffff:0:0/96` | IPv4 주소를 IPv6로 표현 |

---

## 자동 주소 설정 (SLAAC)

IPv6의 핵심 기능 — DHCP 서버 없이 자동으로 주소 생성

```
SLAAC 동작 과정 (Stateless Address Autoconfiguration, RFC 4862)

1. 링크-로컬 주소 생성
   fe80:: + EUI-64 (MAC 주소 기반)
   예: MAC=AA:BB:CC:DD:EE:FF → fe80::a8bb:ccff:fedd:eeff

2. 중복 주소 감지 (DAD - Duplicate Address Detection)
   Neighbor Solicitation 전송
   응답 없으면 → 주소 사용 가능

3. 라우터 탐색 (Router Discovery)
   RS(Router Solicitation) 전송 → ff02::2 (모든 라우터)
   RA(Router Advertisement) 수신 ← 라우터

4. 전역 주소 생성
   RA의 접두사 + EUI-64 또는 임의 인터페이스 ID
   예: 2001:db8::/64 + 인터페이스ID → 2001:db8::a8bb:ccff:fedd:eeff

장점:
  ✅ DHCP 서버 불필요
  ✅ 플러그-앤-플레이 네트워킹
  ✅ 임베디드/IoT 기기에 이상적
```

### NDP (Neighbor Discovery Protocol)

IPv6에서 ARP를 대체하는 프로토콜 (ICMPv6 기반)

| NDP 메시지 | 역할 | IPv4 대응 |
|------------|------|-----------|
| NS (Neighbor Solicitation) | MAC 주소 요청 | ARP Request |
| NA (Neighbor Advertisement) | MAC 주소 응답 | ARP Reply |
| RS (Router Solicitation) | 라우터 탐색 | - |
| RA (Router Advertisement) | 접두사/게이트웨이 공지 | DHCP |
| Redirect | 더 나은 경로 알림 | ICMP Redirect |

---

## 실습 명령어

### Linux / Raspberry Pi

```bash
# IP 주소 확인
ip addr show
ip -6 addr show

# 라우팅 테이블
ip route show
ip -6 route show

# IPv6 연결 테스트
ping6 ::1                          # 루프백
ping6 ff02::1%eth0                 # 링크-로컬 모든 노드
ping6 2001:4860:4860::8888        # Google DNS IPv6

# IPv6 DNS 조회
dig AAAA google.com
nslookup -type=AAAA google.com

# 인터페이스 IPv6 상태
cat /proc/net/if_inet6

# 링크-로컬 주소 확인
ip -6 addr show dev eth0 scope link

# IPv6 라우터 광고 수신 확인
rdisc6 eth0

# 중복 주소 감지 (DAD) 상태
ip -6 addr show | grep -E "tentative|dadfailed"

# IPv6 이웃 테이블 (ARP 대신 NDP)
ip -6 neigh show

# 연결 상태 확인
ss -6 -tlnp   # TCP
ss -6 -ulnp   # UDP

# 방화벽 (ip6tables)
sudo ip6tables -L -n -v
```

### Python 소켓 예제

```python
import socket

# IPv4 서버
sock4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock4.bind(('0.0.0.0', 8080))

# IPv6 서버 (IPv4도 처리 가능 - 듀얼 스택)
sock6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
sock6.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # 듀얼 스택
sock6.bind(('::', 8080))

# IPv6 주소 파싱
addr = '2001:db8::1'
info = socket.getaddrinfo(addr, 80, socket.AF_INET6)
print(info)

# 프로토콜 감지
def get_ip_version(ip_str):
    try:
        socket.inet_pton(socket.AF_INET, ip_str)
        return 4
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, ip_str)
            return 6
        except socket.error:
            return None
```

### C 소켓 예제 (임베디드)

```c
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

/* IPv6 소켓 생성 */
int sock = socket(AF_INET6, SOCK_STREAM, 0);

struct sockaddr_in6 addr6;
memset(&addr6, 0, sizeof(addr6));
addr6.sin6_family = AF_INET6;
addr6.sin6_port   = htons(8080);
inet_pton(AF_INET6, "::1", &addr6.sin6_addr);   /* 루프백 */

bind(sock, (struct sockaddr*)&addr6, sizeof(addr6));

/* 듀얼 스택 설정 (IPv6 소켓으로 IPv4도 처리) */
int off = 0;
setsockopt(sock, IPPROTO_IPV6, IPV6_V6ONLY, &off, sizeof(off));
```

---

## 임베디드 / IoT 관점

### Raspberry Pi IPv6 설정

```bash
# /boot/firmware/cmdline.txt 또는 /etc/sysctl.conf
# IPv6 활성화 확인
sysctl net.ipv6.conf.all.disable_ipv6   # 0이면 활성화

# IPv6 활성화
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0

# 영구 설정 (/etc/sysctl.conf)
net.ipv6.conf.all.disable_ipv6 = 0
net.ipv6.conf.default.disable_ipv6 = 0

# SLAAC 주소 자동 수신 확인
ip -6 addr show | grep "scope global"
```

### lwIP (경량 TCP/IP 스택) IPv6 설정

STM32, ESP32 등 MCU에서 주로 사용하는 TCP/IP 스택

```c
/* lwipopts.h */
#define LWIP_IPV6                   1    /* IPv6 활성화 */
#define LWIP_IPV6_NUM_ADDRESSES     3    /* 인터페이스당 최대 주소 수 */
#define LWIP_IPV6_FORWARD           0    /* 라우터 기능 비활성화 */
#define LWIP_IPV6_ND                1    /* NDP (이웃 탐색) 활성화 */
#define LWIP_IPV6_AUTOCONFIG        1    /* SLAAC 활성화 */
#define LWIP_IPV6_DUP_DETECT_ATTEMPTS 1 /* DAD 시도 횟수 */
#define LWIP_ICMP6                  1    /* ICMPv6 활성화 */
```

### 주요 판단 기준

| 상황 | 권장 프로토콜 | 이유 |
|------|---------------|------|
| 기존 인프라 연동 | IPv4 또는 Dual Stack | 호환성 |
| 신규 IoT 서비스 | IPv6 | 주소 부족 없음, SLAAC |
| 클라우드 연결 | Dual Stack | 대부분 지원 |
| 로컬 네트워크만 | IPv4 | 단순성 |
| 대규모 센서 네트워크 | **IPv6** | 주소 고갈 없음 |
| 이동통신 (5G/LTE) | **IPv6** | 통신사 IPv6 전환 완료 |

---

## 참고 자료

- [RFC 791 - IPv4 표준](https://www.rfc-editor.org/rfc/rfc791)
- [RFC 8200 - IPv6 표준](https://www.rfc-editor.org/rfc/rfc8200)
- [RFC 4291 - IPv6 주소 아키텍처](https://www.rfc-editor.org/rfc/rfc4291)
- [RFC 4862 - IPv6 SLAAC](https://www.rfc-editor.org/rfc/rfc4862)
- [RFC 6146 - NAT64](https://www.rfc-editor.org/rfc/rfc6146)
- [IANA IPv6 특수 주소 레지스트리](https://www.iana.org/assignments/ipv6-address-space)
- [Google IPv6 통계](https://www.google.com/intl/en/ipv6/statistics.html)

---

*최종 업데이트: 2025년*
