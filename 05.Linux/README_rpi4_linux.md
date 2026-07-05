# 🐧 Linux 배포판(Distribution) 분류 및 특징 정리

> Linux는 단일 운영체제가 아니라, **커널(Kernel)** 을 공유하는 수백 가지 배포판(Distribution, Distro)으로 구성된 생태계입니다.  
> 각 배포판은 **패키지 관리 방식**, **릴리즈 모델**, **대상 사용자**, **철학** 에 따라 크게 분류됩니다.

---

## 📋 목차

- [배포판 분류 기준](#배포판-분류-기준)
- [주요 계열별 분류](#주요-계열별-분류)
  - [Debian 계열](#1-debian-계열)
  - [Red Hat 계열](#2-red-hat-계열)
  - [Arch 계열](#3-arch-계열)
  - [SUSE 계열](#4-suse-계열)
  - [Gentoo 계열](#5-gentoo-계열)
  - [독립 계열](#6-독립-계열)
- [릴리즈 모델 비교](#릴리즈-모델-비교)
- [패키지 관리자 비교](#패키지-관리자-비교)
- [사용 목적별 추천](#사용-목적별-추천)
- [배포판 계통도 요약](#배포판-계통도-요약)

---

## 배포판 분류 기준

| 분류 기준 | 설명 |
|-----------|------|
| **패키지 관리자** | `.deb` (dpkg/apt), `.rpm` (rpm/yum/dnf), `.pkg.tar.zst` (pacman) 등 |
| **릴리즈 모델** | Fixed Release (고정 버전) vs Rolling Release (지속 업데이트) |
| **대상 사용자** | 서버/기업용, 데스크톱용, 임베디드용, 보안/해킹용 등 |
| **지원 모델** | 커뮤니티 지원 vs 상용 기술지원(유료) |
| **Init 시스템** | systemd, SysVinit, OpenRC, runit 등 |

---

## 주요 계열별 분류

### 1. Debian 계열

> **모체**: Debian GNU/Linux (1993년, Ian Murdock 창설)  
> **패키지 형식**: `.deb`  
> **패키지 관리자**: `dpkg`, `apt`, `apt-get`

```
Debian
├── Ubuntu
│   ├── Linux Mint
│   ├── Pop!_OS
│   ├── Elementary OS
│   ├── Zorin OS
│   └── Ubuntu Server / Ubuntu Core
├── Kali Linux
├── Raspberry Pi OS (구 Raspbian)
├── MX Linux
└── antiX
```

#### 주요 배포판 특징

| 배포판 | 특징 | 주요 대상 |
|--------|------|-----------|
| **Debian** | 안정성 최우선, 보수적 릴리즈, 3개 브랜치(stable/testing/unstable) | 서버, 고급 사용자 |
| **Ubuntu** | Debian 기반, 6개월 주기 릴리즈, LTS 5년 지원, 광범위한 하드웨어 지원 | 데스크톱, 서버 |
| **Linux Mint** | Ubuntu 기반, Windows 유사 UI(Cinnamon), 초보자 친화적 | 데스크톱 입문자 |
| **Kali Linux** | 보안/침투테스트 도구 600+ 내장, 롤링 릴리즈 | 보안 전문가, 침투 테스트 |
| **Pop!_OS** | System76 제작, NVIDIA GPU 최적화, 개발자 친화적 | 개발자, 게이머 |
| **Raspberry Pi OS** | ARM 아키텍처 최적화, GPIO/임베디드 지원 | 임베디드, IoT, 교육 |
| **MX Linux** | Debian stable 기반, 경량, MX Tools 내장 | 구형 PC, 일반 사용자 |

#### Debian 브랜치 구조

```
Debian stable   → 안정 버전 (예: Bookworm 12)  ← 서버 운영 권장
Debian testing  → 차기 stable 준비 브랜치
Debian unstable → sid (항상 최신, 불안정 가능)
Debian experimental → 실험적 패키지
```

#### Ubuntu LTS 지원 주기

```
Ubuntu 24.04 LTS (Noble Numbat)   → 2029년까지 지원
Ubuntu 22.04 LTS (Jammy Jellyfish) → 2027년까지 지원
Ubuntu 20.04 LTS (Focal Fossa)    → 2025년까지 지원
```

---

### 2. Red Hat 계열

> **모체**: Red Hat Linux → RHEL (Red Hat Enterprise Linux)  
> **패키지 형식**: `.rpm` (Red Hat Package Manager)  
> **패키지 관리자**: `rpm`, `yum`, `dnf`

```
RHEL (Red Hat Enterprise Linux)
├── Fedora  ← RHEL의 업스트림 테스트베드
├── CentOS Stream  ← RHEL 업스트림 롤링
├── AlmaLinux  ← RHEL 1:1 바이너리 호환 (CentOS 대체)
├── Rocky Linux  ← RHEL 1:1 바이너리 호환 (CentOS 대체)
└── Oracle Linux

Amazon Linux 2 / Amazon Linux 2023  ← RPM 기반, AWS 최적화
```

#### 주요 배포판 특징

| 배포판 | 특징 | 주요 대상 |
|--------|------|-----------|
| **RHEL** | 기업용 최고 안정성, 유료 구독 지원, 10년 지원 주기 | 엔터프라이즈 서버 |
| **Fedora** | RHEL 업스트림, 최신 기술 선도, 6개월 릴리즈, Wayland 선도 | 개발자, 최신 기술 테스트 |
| **CentOS Stream** | RHEL의 롤링 업스트림 (CentOS Linux 종료 후 전환) | CI/CD 테스트 환경 |
| **AlmaLinux** | RHEL 바이너리 호환, 무료, CloudLinux 스폰서 | 구 CentOS 대체 서버 |
| **Rocky Linux** | RHEL 바이너리 호환, 무료, Greg Kurtzer 창설 | 구 CentOS 대체 서버 |
| **Amazon Linux 2023** | AWS EC2 최적화, RHEL 계열, dnf 사용 | AWS 클라우드 서버 |

#### Red Hat 생태계 관계도

```
Fedora (최신 기능 테스트)
    ↓ 안정화된 기능 반영
RHEL (엔터프라이즈 제품)
    ↓ 소스코드 공개 (GPL)
AlmaLinux / Rocky Linux (무료 RHEL 호환 재빌드)

CentOS Stream (RHEL의 업스트림 롤링 브랜치)
```

> ⚠️ **CentOS Linux 종료**: CentOS Linux 8은 2021년 12월 종료. CentOS 7은 2024년 6월 종료.  
> 대체 배포판으로 **AlmaLinux** 또는 **Rocky Linux** 권장.

---

### 3. Arch 계열

> **모체**: Arch Linux (2002년, Judd Vinet 창설)  
> **패키지 형식**: `.pkg.tar.zst`  
> **패키지 관리자**: `pacman`, `yay` (AUR helper)  
> **릴리즈 모델**: Rolling Release (지속 업데이트)

```
Arch Linux
├── Manjaro  ← Arch 기반, 초보자 친화적, 안정화 레이어 추가
├── EndeavourOS  ← Arch 기반, 설치 간소화
├── Garuda Linux  ← Arch 기반, 게이밍/성능 최적화
├── BlackArch  ← Arch 기반, 보안/해킹 도구 특화
└── SteamOS 3 (Valve)  ← Arch 기반, Steam Deck OS
```

#### 주요 특징

| 항목 | 내용 |
|------|------|
| **철학** | KISS (Keep It Simple, Stupid) — 최소한의 기본 설치, 사용자가 직접 구성 |
| **AUR** | Arch User Repository — 커뮤니티 패키지 저장소 (수만 개 패키지) |
| **Arch Wiki** | 업계 최고 수준의 문서화, 타 배포판 사용자도 참고 |
| **장점** | 항상 최신 패키지, 높은 자유도, 가벼운 설치 |
| **단점** | 설치 및 설정 복잡, 높은 진입 장벽, 업데이트 후 불안정 가능성 |

---

### 4. SUSE 계열

> **모체**: SUSE Linux (1994년, 독일)  
> **패키지 형식**: `.rpm`  
> **패키지 관리자**: `zypper`, `rpm`

```
SUSE Linux Enterprise (SLE)  ← 엔터프라이즈 유료 버전
├── openSUSE Leap    ← SLE 기반, 안정적 고정 릴리즈, 무료
└── openSUSE Tumbleweed  ← 롤링 릴리즈, 최신 패키지, 무료
    └── openSUSE MicroOS  ← 컨테이너/임베디드용 불변(Immutable) OS
```

#### 주요 특징

| 배포판 | 특징 |
|--------|------|
| **SLE (SUSE Linux Enterprise)** | 서버/데스크톱용 기업 지원, SAP 인증, 장기 지원 |
| **openSUSE Leap** | SLE 소스 기반, 안정적, 무료, 서버/데스크톱 겸용 |
| **openSUSE Tumbleweed** | 롤링 릴리즈, 항상 최신 커널/소프트웨어, 개발자 선호 |
| **YaST** | SUSE 고유 통합 설정 도구 (Yet Another Setup Tool) |

---

### 5. Gentoo 계열

> **모체**: Gentoo Linux (2002년, Daniel Robbins 창설)  
> **패키지 형식**: 소스코드 직접 컴파일  
> **패키지 관리자**: `portage` (`emerge` 명령어)  
> **특징**: 소스 기반 배포판, 최고 수준의 커스터마이징

```
Gentoo
├── Calculate Linux  ← Gentoo 기반, 기업/서버용
├── Sabayon (구)   ← Gentoo 기반, 데스크톱용
└── ChromeOS / ChromiumOS  ← Google, Gentoo 파생
```

#### 주요 특징

| 항목 | 내용 |
|------|------|
| **컴파일 빌드** | 모든 패키지를 로컬에서 소스 컴파일 → 하드웨어 최적화 |
| **USE 플래그** | 패키지 기능을 세밀하게 ON/OFF 제어 |
| **진입 장벽** | 매우 높음 (Linux 고급 사용자 대상) |
| **성능** | 이론상 최적화되나 실제 차이는 미미한 경우도 있음 |

---

### 6. 독립 계열

> 특정 주요 계열에서 파생되지 않고 독자적으로 개발된 배포판

| 배포판 | 패키지 관리 | 특징 |
|--------|------------|------|
| **Slackware** | `pkgtool` (수동) | 1993년, 최초의 상업 Linux 배포판 중 하나, 극도로 단순한 구조 |
| **Alpine Linux** | `apk` | 초경량 (5MB), musl libc, 컨테이너/Docker 기반 이미지로 널리 사용 |
| **Void Linux** | `xbps` | 독립 개발, runit init, glibc/musl 선택 가능, 롤링 릴리즈 |
| **NixOS** | `nix` | 선언적 구성, 재현 가능한 빌드, 롤링 릴리즈 |
| **Solus** | `eopkg` | 데스크톱 특화, Budgie DE 개발사 |

---

## 릴리즈 모델 비교

| 모델 | 설명 | 대표 배포판 | 장단점 |
|------|------|------------|--------|
| **Fixed Release** | 특정 시점에 버전 확정, 이후 보안 패치만 적용 | Ubuntu LTS, Debian, RHEL, AlmaLinux | ✅ 안정적, ❌ 최신 소프트웨어 지연 |
| **Rolling Release** | 지속적으로 패키지 업데이트, 버전 구분 없음 | Arch, openSUSE Tumbleweed, Kali | ✅ 항상 최신, ❌ 가끔 불안정 |
| **Semi-Rolling** | 핵심 시스템은 고정, 일부 앱은 최신 유지 | Manjaro, openSUSE Leap | ✅ 중간 타협점 |
| **Immutable (불변 OS)** | 루트 파일시스템 읽기 전용, 업데이트는 이미지 교체 | Fedora Silverblue, MicroOS, SteamOS | ✅ 높은 안정성, ❌ 커스터마이징 제한 |

---

## 패키지 관리자 비교

| 계열 | 패키지 형식 | 저수준 도구 | 고수준 도구 | 예시 명령 |
|------|------------|------------|------------|-----------|
| Debian/Ubuntu | `.deb` | `dpkg` | `apt` | `apt install nginx` |
| RHEL/Fedora | `.rpm` | `rpm` | `dnf` / `yum` | `dnf install nginx` |
| Arch | `.pkg.tar.zst` | `pacman` | `yay` (AUR) | `pacman -S nginx` |
| SUSE | `.rpm` | `rpm` | `zypper` | `zypper install nginx` |
| Gentoo | source | `portage` | `emerge` | `emerge nginx` |
| Alpine | `.apk` | `apk` | `apk` | `apk add nginx` |
| Void | `.xbps` | `xbps` | `xbps-install` | `xbps-install nginx` |

---

## 사용 목적별 추천

### 🖥️ 데스크톱 / 개인 사용

| 추천 배포판 | 이유 |
|------------|------|
| **Ubuntu 24.04 LTS** | 가장 광범위한 지원, 풍부한 문서 |
| **Linux Mint** | Windows에서 이주하는 초보자에게 최적 |
| **Fedora** | 최신 기술, 개발자 친화적 |
| **Manjaro** | Arch의 장점 + 쉬운 설치 |
| **Pop!_OS** | NVIDIA GPU, 개발 환경 최적화 |

### 🖥️ 서버 / 엔터프라이즈

| 추천 배포판 | 이유 |
|------------|------|
| **RHEL** | 최고 수준 기술지원, 10년 수명 |
| **AlmaLinux / Rocky Linux** | RHEL 무료 대체, CentOS 마이그레이션 |
| **Ubuntu Server LTS** | 클라우드 최적화, Canonical 지원 |
| **Debian** | 초안정, 무료, 장기 운영 |
| **SUSE Linux Enterprise** | SAP/ERP 환경, 독일계 기업 선호 |

### 🔧 임베디드 / IoT

| 추천 배포판 | 이유 |
|------------|------|
| **Raspberry Pi OS** | Pi 하드웨어 GPIO 최적화 |
| **Alpine Linux** | 초경량, 컨테이너/도커 기본 이미지 |
| **Yocto Project** | 커스텀 임베디드 Linux 빌드 시스템 |
| **BuildRoot** | 소형 임베디드 시스템 크로스 컴파일 |

### 🔐 보안 / 침투 테스트

| 추천 배포판 | 이유 |
|------------|------|
| **Kali Linux** | 600+ 보안 도구, 업계 표준 |
| **Parrot OS** | Kali 대안, 경량, 개인정보 보호 |
| **BlackArch** | Arch 기반, 2800+ 보안 도구 |

### ☁️ 클라우드 / 컨테이너

| 추천 배포판 | 이유 |
|------------|------|
| **Alpine Linux** | Docker 공식 이미지 최소화 |
| **Amazon Linux 2023** | AWS EC2 최적화 |
| **Fedora CoreOS** | 컨테이너 특화 불변 OS |
| **Ubuntu Server** | 클라우드 init 지원, 광범위 지원 |

---

## 배포판 계통도 요약

```
Linux Kernel
│
├── Debian 계열 (.deb / apt)
│   ├── Debian ──→ Ubuntu ──→ Mint, Pop!_OS, Zorin, Elementary
│   ├── Kali Linux
│   └── Raspberry Pi OS
│
├── Red Hat 계열 (.rpm / dnf)
│   ├── Fedora  ←── RHEL ──→ AlmaLinux, Rocky Linux
│   ├── CentOS Stream
│   └── Amazon Linux 2023
│
├── SUSE 계열 (.rpm / zypper)
│   ├── SUSE Linux Enterprise
│   └── openSUSE (Leap / Tumbleweed)
│
├── Arch 계열 (.zst / pacman)
│   ├── Arch Linux ──→ Manjaro, EndeavourOS, Garuda
│   └── SteamOS 3 (Valve)
│
├── Gentoo 계열 (source / portage)
│   └── Gentoo ──→ ChromeOS (Google)
│
└── 독립 계열
    ├── Slackware
    ├── Alpine Linux (.apk)
    ├── Void Linux (xbps)
    └── NixOS (nix)
```

---

## Raspberry Pi Imager v2.0.3 — 라즈베리파이4 설치 가능 OS 총망라

> Raspberry Pi Imager v2.0.3은 라즈베리파이 재단 공식 SD 카드 라이팅 도구입니다.  
> 아래 목록은 Imager에서 Raspberry Pi 4를 선택했을 때 표시되는 모든 OS를 **카테고리별**로 정리한 것입니다.  
> (✅ = Imager에 기본 등록, 🔗 = 수동 다운로드 필요)

### 1. 🥇 공식 / 범용 OS

| OS 이름 | 아키텍처 | 특징 |
|---------|---------|------|
| **Raspberry Pi OS (64-bit)** | arm64 | Debian Trixie 기반, Raspbian 후신, GPIO/카메라/터치스크린 완벽 지원 |
| **Raspberry Pi OS Full (64-bit)** | arm64 | 데스크톱 + LibreOffice, Minecraft, VSCode 등 추천 앱 포함 |
| **Raspberry Pi OS Lite (64-bit)** | arm64 | 데스크톱 없음, 서버/IoT/헤드리스 용도 |
| **Ubuntu Desktop 24.04 LTS** | arm64 | Canonical 공식, 5년 지원, ROS/서버 애플리케이션에 강점 |
| **Ubuntu Server 24.04 LTS** | arm64 | CLI 전용, 클러스터/클라우드/엣지 컴퓨팅 |
| **Debian 12 (Bookworm)** | arm64 | 순수 Debian, RPi OS보다 가볍고 보수적 |
| **Debian 11 (Bullseye)** | armhf/arm64 | 레거시 안정 버전 |
| **Fedora 40+** | aarch64 | 최신 커널/소프트웨어, KDE/GNOME 선택 가능 |
| **Manjaro ARM** | aarch64 | Arch 기반, GUI 설치, AUR 접근 가능 |
| **Arch Linux ARM** | aarch64 | 롤링 릴리즈, 최소 설치, DIY 지향 |
| **openSUSE Tumbleweed** | aarch64 | 롤링 릴리즈, YaST 설정 도구 |
| **openSUSE Leap** | aarch64 | 고정 릴리즈, 안정성 중심 |
| **Kali Linux** | arm64 | 600+ 보안/해킹 도구 내장, 침투 테스트 표준 |
| **Alpine Linux** | aarch64 | 5MB 초경량, musl libc, Docker 최적화 |
| **Armbian** | arm64 | Debian/Ubuntu 기반, SBC 최적화, 커널 업데이트 용이 |
| **FreeBSD** | aarch64 | Linux 계열 아님 (BSD 계열), ZFS, 네트워크 성능 우수 |
| **RISC OS** | arm | ARM 네이티브, 1987년부터 이어진 고유 OS, 경량 GUI |

### 2. 🎮 게이밍 / 레트로 게임

| OS 이름 | 에뮬레이터 | 특징 |
|---------|-----------|------|
| **RetroPie** | RetroArch + 50+ 코어 | 레트로 게이밍의 표준, ES (EmulationStation) 프론트엔드 |
| **Recalbox** | RetroArch 기반 | 설치 즉시 사용 가능, 아동 친화 UI, 클라우드 세이브 |
| **Batocera** | RetroArch 기반 | USB 부팅 가능, PC/Pi/기타 SBC 지원, 선별된 ROM 세트 |
| **Lakka** | RetroArch 기반 | 최소주의, 게임기 UI (XMB), 저사양 기기 최적화 |
| **Box86/Box64 + Wine** | x86 에뮬레이션 | RPi4에서 PC 게임 실행 (실험적, 성능 제한적) |

### 3. 🏠 스마트 홈 / 홈 오토메이션

| OS 이름 | 특징 |
|---------|------|
| **Home Assistant OS** | 스마트 홈 허브 전용, 2000+ 통합 지원, Zigbee/Z-Wave, Lovelace UI |
| **Homebridge** | Apple HomeKit 호환 브리지, 비-HomeKit 기기를 HomeKit에 연결 |
| **openHAB** | 오픈소스 홈 오토메이션, Eclipse IoT 기반, 400+ 애드온 |
| **evcc** | 전기차 충전 관리, PV(태양광) 연동, Wallbox 제어 |
| **Gladys Assistant** | 프라이버시 중심 스마트 홈, 로컬 AI, 음성 제어 |

### 4. 🎬 미디어 센터

| OS 이름 | 플레이어 | 특징 |
|---------|---------|------|
| **LibreELEC** | Kodi | 미디어 센터 전용, 초경량, 단일 용도 최적화 |
| **OSMC** | Kodi + Vero | Debian 기반, Kodi + 범용 Linux 기능 동시 사용, Pi에서 Vero처럼 동작 |
| **Plex Media Server** | Plex | 미디어 스트리밍 서버, 클라이언트-서버 모델, 메타데이터 관리 |

### 5. 📺 디지털 사이니지

| OS 이름 | 특징 |
|---------|------|
| **Screenly OSE** | 웹 기반 디지털 사이니지, Python + Flask, REST API, CMS 불필요 |
| **piSignage** | 상업용 디지털 사이니지, 원격 관리, 예약/재생목록 지원 |
| **Yodeck** | 클라우드 관리, 무료 플랜 (1대), 터치/QR/센서 연동 |

### 6. 🖨️ 3D 프린팅 / CNC

| OS 이름 | 특징 |
|---------|------|
| **OctoPi** | Raspberry Pi OS + OctoPrint, 3D 프린터 원격 모니터링/제어, 웹캠 스트리밍 |
| **MainsailOS** | Klipper 기반 3D 프린터 펌웨어 + 웹 UI, Fluidd/Mainsail 선택 가능 |

### 7. 📡 네트워크 / 서버

| OS 이름 | 특징 |
|---------|------|
| **Pi-hole** | 네트워크 전체 광고 차단 DNS 서버, 경량, 플러그 앤 플레이 |
| **OpenWrt** | 라우터/AP 펌웨어, NAT/QoS/VPN/방화벽, RPi4를 라우터로 변환 |
| **DietPi** | 초경량 Debian 최적화, 사전 구성 소프트웨어 목록 제공 (Nextcloud, Pi-hole 등) |
| **OMV (OpenMediaVault)** | NAS 전용 OS, Debian 기반, RAID/ZFS/Docker, SMB/NFS/FTP |

### 8. 🧪 교육 / 개발

| OS 이름 | 특징 |
|---------|------|
| **Raspberry Pi Desktop (x86)** | PC/VM용 RPi OS, RPi 환경을 일반 PC에서 테스트 |
| **Scratch Desktop** | MIT Scratch 3, 교육용 블록 코딩 환경 |
| **Python IDE / Thonny** | Python 학습/개발 통합 환경 |
| **Android (LineageOS / KonstaKANG)** | 안드로이드 13/14 기반, RPi4에서 안드로이드 앱 실행, 터치스크린 지원 |

### 9. 🛠️ 유틸리티 / 기타

| OS 이름 | 특징 |
|---------|------|
| **Raspberry Pi Diagnostics** | RPi4 하드웨어 진단 도구 (메모리/CPU/스토리지 테스트) |
| **Raspberry Pi OS + Connect** | RPi OS + Raspberry Pi Connect 사전 통합, 원격 접속 즉시 사용 |
| **TLXOS** | Thin Client 전용, VDI/Citrix/VMware Horizon 연결 |
| **Ultramarine Linux** | Fedora 기반, 사용자 친화, Pantheon/Budgie 데스크톱 |
| **Bass OS** | 개발자 중심, 사전 설정된 개발 도구 모음 |
| **Apertis** | 임베디드/자동차용, OTA 업데이트, Debian 기반 |

---

## Raspberry Pi Imager 사용 팁

```bash
# 설치 방법 (Raspberry Pi OS / Ubuntu / Debian)
sudo apt update
sudo apt install rpi-imager

# 실행
rpi-imager
```

> **Imager v2.0 주요 변경사항**
> - 마법사(Wizard) 기반 단계별 UI (Device → OS → Storage)
> - SSH, Wi-Fi, 호스트명, 로케일을 라이팅 전에 사전 설정 가능
> - Raspberry Pi Connect 통합 (원격 접속)
> - 접근성 향상 (키보드 네비게이션, 스크린 리더)
> - 디바이스별 OS 필터링 지원 (Pi 4 선택 시 호환 OS만 표시)

---

## 참고 자료

- [DistroWatch](https://distrowatch.com/) — 배포판 인기 순위 및 정보
- [Arch Wiki](https://wiki.archlinux.org/) — 최고 품질의 Linux 문서
- [Debian Releases](https://www.debian.org/releases/) — Debian 공식 릴리즈 정보
- [Red Hat Documentation](https://access.redhat.com/documentation/) — RHEL 공식 문서
- [Linux Foundation](https://www.linuxfoundation.org/) — Linux 재단 공식 사이트
- [Raspberry Pi Software](https://www.raspberrypi.com/software/) — Imager 다운로드 및 OS 공식 페이지
- [Raspberry Pi Imager GitHub](https://github.com/raspberrypi/rpi-imager) — 오픈소스 저장소

---

## 라이선스

이 문서는 학습 및 교육 목적으로 작성된 정리 자료입니다.

---

*마지막 업데이트: 2026년 7월*
