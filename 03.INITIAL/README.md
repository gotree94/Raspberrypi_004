#🍓 Raspberry Pi 4 초기화 하기

## 1. Raspberry Pi Imager 다운로드 및 sdcard 만들기
홈페이지 링크 : https://www.raspberrypi.com/software/
다운로드 링크 : https://downloads.raspberrypi.com/imager/imager_latest.exe

### 1.1 다운로드 및 프로그램 설치

<img width="358" height="172" alt="imager_001" src="https://github.com/user-attachments/assets/2adfc1e2-dec0-4332-9d48-475cacfeca62" />
<br>
<img width="598" height="464" alt="imager_002" src="https://github.com/user-attachments/assets/afb9d0c0-bec5-4ef3-82b8-ac7b361eb436" />
<br>
<img width="598" height="464" alt="imager_003" src="https://github.com/user-attachments/assets/32620cbb-875c-46b6-b5dc-bc038834fb7f" />
<br>
<img width="598" height="464" alt="imager_004" src="https://github.com/user-attachments/assets/0255b0db-543c-4ee3-bdd5-91b4afbb7132" />
<br>
<img width="598" height="464" alt="imager_005" src="https://github.com/user-attachments/assets/b4057243-5cd4-4dfb-99c9-babd505601b8" />
<br>
<img width="598" height="464" alt="imager_006" src="https://github.com/user-attachments/assets/20d458a2-b9da-4d0b-ac67-1c323838f036" />
<br>
<img width="682" height="482" alt="imager_007" src="https://github.com/user-attachments/assets/a7245811-e5d8-46b0-9b21-ed1a5f53be1f" />
<br>

### 1.2 Raspberry Pi Imager 실행 및 sdcard 만들기

<img width="682" height="482" alt="rp4_init_001" src="https://github.com/user-attachments/assets/bb604296-81e9-4f27-a992-b0bf9a25050a" />
<br>
<img width="682" height="482" alt="rp4_init_002" src="https://github.com/user-attachments/assets/ac9fe5ae-c552-4940-bf00-1b83045c0f77" />
<br>
<img width="682" height="482" alt="rp4_init_003" src="https://github.com/user-attachments/assets/f083a21f-0af8-4190-9f15-ad77085532f2" />
<br>
<img width="682" height="482" alt="rp4_init_004" src="https://github.com/user-attachments/assets/894e4ded-a1dc-4b47-9c7b-7fe93102e8f6" />
<br>
<img width="682" height="482" alt="rp4_init_005" src="https://github.com/user-attachments/assets/3c165a98-c62a-4edf-b344-ee820ea9e24f" />
<br>
<img width="682" height="482" alt="rp4_init_006" src="https://github.com/user-attachments/assets/52d09fda-e6bf-4822-a2ea-e7668f28c4c0" />
<br>
<img width="682" height="482" alt="rp4_init_007" src="https://github.com/user-attachments/assets/97fdb4b0-0c29-4c0f-9daf-2da994d38c4b" />
<br>
<img width="682" height="482" alt="rp4_init_008" src="https://github.com/user-attachments/assets/e890e7d1-88d7-42af-81a4-206fae5e46b5" />
<br>
<img width="682" height="482" alt="rp4_init_009" src="https://github.com/user-attachments/assets/98b930de-7b7b-4567-9989-e8e8ed851bd6" />
<br>
<img width="682" height="482" alt="rp4_init_010" src="https://github.com/user-attachments/assets/7c95488d-5ecd-4aa9-9721-2a1e7f4107e9" />
<br>
<img width="682" height="482" alt="rp4_init_011" src="https://github.com/user-attachments/assets/847f276a-5e39-4e20-b3d4-bf96dbd37f4c" />
<br>


### 1.3 Raspberry Pi IP 확인

* IPV4

```cmd
ping -4 rp4-nwkim.local
```

```
Ping rp4-nwk.local [192.168.0.17] 32바이트 데이터 사용:
192.168.0.17의 응답: 바이트=32 시간=4ms TTL=64
192.168.0.17의 응답: 바이트=32 시간=4ms TTL=64
192.168.0.17의 응답: 바이트=32 시간=6ms TTL=64
192.168.0.17의 응답: 바이트=32 시간=5ms TTL=64

192.168.0.17에 대한 Ping 통계:
    패킷: 보냄 = 4, 받음 = 4, 손실 = 0 (0% 손실),
왕복 시간(밀리초):
    최소 = 4ms, 최대 = 6ms, 평균 = 4ms
```

* IPV6
```
ping rp4-nwk.local
```

```
Ping rp4-nwk.local [fe80::e65f:1ff:feca:2425%14] 32바이트 데이터 사용:
fe80::e65f:1ff:feca:2425%14의 응답: 시간=13ms
fe80::e65f:1ff:feca:2425%14의 응답: 시간=5ms
fe80::e65f:1ff:feca:2425%14의 응답: 시간=8ms
fe80::e65f:1ff:feca:2425%14의 응답: 시간=6ms

fe80::e65f:1ff:feca:2425%14에 대한 Ping 통계:
    패킷: 보냄 = 4, 받음 = 4, 손실 = 0 (0% 손실),
왕복 시간(밀리초):
    최소 = 5ms, 최대 = 13ms, 평균 = 8ms
```

### 1.4 MobaXterm

* 홈페이지 링크 : https://mobaxterm.mobatek.net/
* 다운로드 링크 : https://download.mobatek.net/2612026022582601/MobaXterm_Portable_v26.1.zip

* 압축을 해제하고 MobaXterm_Personal_25.3.exe 실행

<img width="1264" height="1034" alt="terminal_001" src="https://github.com/user-attachments/assets/6b0ba916-58f1-4a84-9d24-1b6df98ecb5c" />
<br>
<img width="898" height="604" alt="terminal_002" src="https://github.com/user-attachments/assets/97664a31-7be5-40bc-8700-7f70f6f2af8c" />
<br>
<img width="898" height="604" alt="terminal_003" src="https://github.com/user-attachments/assets/85305736-eb5e-48b7-894b-18b10914987d" />
<br>
<img width="898" height="604" alt="terminal_004" src="https://github.com/user-attachments/assets/c138e930-d8eb-4bd7-82ad-946ff410dd4b" />
<br>
<img width="562" height="251" alt="terminal_005" src="https://github.com/user-attachments/assets/b3f462c4-a3ab-47ca-92bf-fff60666bfa5" />
<br>
<img width="1264" height="1034" alt="terminal_006" src="https://github.com/user-attachments/assets/a02a04ed-f997-4892-9c2d-deed76301a10" />
<br>
<img width="484" height="193" alt="terminal_007" src="https://github.com/user-attachments/assets/b3615b93-7bf3-49ed-9cc1-7cd23bf25348" />
<br>
<img width="659" height="516" alt="terminal_008" src="https://github.com/user-attachments/assets/37b95c52-8286-4c9b-9f75-652e4d4a55ad" />
<br>
<img width="1018" height="859" alt="terminal_009" src="https://github.com/user-attachments/assets/4a229876-e169-4155-ae0d-91cae1fb6e4b" />
<br>

### 1.5 VNC

* raspi-config 이용 (가장 간단)

```bash
sudo raspi-config nonint do_vnc 0
```
  * 0 = 활성화, 1 = 비활성화

* systemctl로 직접 제어
```bash
# RealVNC 서비스 시작 및 자동시작 등록
sudo systemctl enable vncserver-x11-serviced
sudo systemctl start vncserver-x11-serviced

# 상태 확인
sudo systemctl status vncserver-x11-serviced
```

* 확인
```bash
# VNC 포트(5900) 리스닝 확인
sudo ss -tlnp | grep 5900
```

<img width="898" height="604" alt="vnc_001" src="https://github.com/user-attachments/assets/621b85c7-4b9a-445c-b248-e63eb67138e1" />
<br>
<img width="898" height="604" alt="vnc_002" src="https://github.com/user-attachments/assets/d23fb48f-7eb7-49a3-be86-beb4181aef4e" />
<br>
<img width="541" height="346" alt="vnc_003" src="https://github.com/user-attachments/assets/4027a647-094f-45cb-b71c-593b4b0f0030" />
<br>
<img width="356" height="192" alt="vnc_004" src="https://github.com/user-attachments/assets/2ae31d43-b908-419b-9e37-3407e1ac4aa4" />
<br>
<img width="356" height="192" alt="vnc_005" src="https://github.com/user-attachments/assets/58da4375-a70f-4e4b-a96b-52262694ca11" />
<br>

## 문제1 : 호스트 이름이 보이지 않음

### 원인 분석
- 문제는 3가지 레이어에서 발생합니다.

#### 원인 1: DNS 캐시에 IPv4가 아닌 IPv6로만 저장됨 (가장 흔한 원인)
* ping rp4-nwkim.local이 fe80::...로 응답했다는 것은 캐시에도 IPv6만 저장된 상태입니다.
```powershell
# 현재 캐시 상태 확인
Get-DnsClientCache | Where-Object { $_.Entry -like "*.local" }
```
* Data 컬럼이 fe80::...라면 코드의 $_.Data -match '^[0-9]' 조건에서 걸러져서 맵에 추가되지 않습니다.

#### 원인 2: IPv4와 IPv6 중 어느 것으로 캐시되는지 타이밍 문제
* Windows mDNS는 IPv4(A 레코드)와 IPv6(AAAA 레코드) 중 먼저 응답 온 것으로 캐시합니다. 같은 서브넷에서 IPv6 링크로컬이 더 빠르게 응답하면 IPv6만 저장됩니다.

#### 원인 3: socket.gethostbyaddr()는 mDNS .local 미지원
* Windows의 socket.gethostbyaddr()는 표준 DNS만 조회하며, mDNS(.local)는 별도 스택(mDNS/Bonjour)이라 파이썬 기본 소켓에서 투명하게 연결되지 않습니다.

#### 해결 방법
* 근본 해결: ping -4 rp4-nwkim.local 로 IPv4 강제 캐시 등록 후 스캔
```cmd
ping -4 rp4-nwkim.local
```

```
python ip_scanner3.py
```

```
# DNS/mDNS 캐시 삭제
ipconfig /flushdns

# ARP 캐시 전체 삭제
arp -d *

# 또는 netsh로 삭제
netsh interface ip delete arpcache
```

```
# SD 카드 교체 후 캐시 문제 해결
python ip_scanner5.py --flush

# 가장 빠른 방법 (nmap 설치 시)
python ip_scanner5.py --flush --arp-scan
```


<img width="993" height="851" alt="086" src="https://github.com/user-attachments/assets/ee8c50be-2384-43ee-b16c-48bf48f731ae" />


## 문제2 : 터미널에서 wifi 설정

### WIFI ON
   * 아래 코드를 이용하여 wifi를 켤 수 있음

```
sudo nmcli radio wifi on
```

### WIFI 리스트 검색
   * 아래 코드를 이용하여 wifi 리스트를 볼 수 있음
   * 이 중에서 가장 강도가 높은 와이파이를 검색하면 됨

```
sudo nmcli device wifi list
```
 
```
admin@rp4-nwk2:~$ sudo nmcli device wifi list
IN-USE  BSSID              SSID                             MODE   CHAN  RATE        SIGNAL  BARS  SECURITY
        B0:38:6C:46:6A:32  unreal                           Infra  6     130 Mbit/s  100     ▂▄▆█  WPA2
        B0:38:6C:46:6A:30  unreal5G                         Infra  149   270 Mbit/s  100     ▂▄▆█  WPA2
        58:86:94:84:4A:7C  임베디드실-5G                    Infra  149   270 Mbit/s  92      ▂▄▆█  WPA2
        0A:09:B4:82:84:63  KT_Free_WiFi                     Infra  1     260 Mbit/s  74      ▂▄▆_  --
        00:09:B4:82:84:63  KT WiFi                          Infra  1     260 Mbit/s  72      ▂▄▆_  WPA2 802.1X
        0E:09:B4:82:84:63  Public WiFi Secure               Infra  1     260 Mbit/s  72      ▂▄▆_  WPA2 802.1X
        12:09:B4:82:84:63  Public WiFi Free                 Infra  1     260 Mbit/s  72      ▂▄▆_  --
        06:09:B4:82:84:63  KT WiFi                          Infra  1     260 Mbit/s  70      ▂▄▆_  --
        72:5D:CC:C3:4C:CC  그룹토의실-2.4G                  Infra  3     270 Mbit/s  69      ▂▄▆_  WPA2
        0E:09:B4:82:84:64  KT GiGA WiFi                     Infra  60    260 Mbit/s  50      ▂▄__  --
        12:09:B4:82:84:64  KT_Free_WiFi                     Infra  60    260 Mbit/s  50      ▂▄__  --
        1A:09:B4:82:84:64  Public WiFi Free                 Infra  60    260 Mbit/s  50      ▂▄__  --
        00:09:B4:82:84:64  KT WiFi                          Infra  60    260 Mbit/s  50      ▂▄__  WPA2 802.1X
        0A:09:B4:82:84:64  KT GiGA WiFi                     Infra  60    260 Mbit/s  50      ▂▄__  WPA2 802.1X
        06:09:B4:82:84:64  KT WiFi                          Infra  60    260 Mbit/s  49      ▂▄__  --
        16:09:B4:82:84:64  Public WiFi Secure               Infra  60    260 Mbit/s  47      ▂▄__  WPA2 802.1X
        70:5D:CC:83:4C:CE  그룹토의실-5G-2                  Infra  36    270 Mbit/s  45      ▂▄__  WPA2
        64:E5:99:D1:08:3E  office                           Infra  11    270 Mbit/s  44      ▂▄__  --
        4A:9E:BD:55:52:D0  DIRECT-D0-HP OfficeJet Pro 7740  Infra  6     65 Mbit/s   42      ▂▄__  WPA2
        16:09:B4:82:84:54  Public WiFi Secure               Infra  116   260 Mbit/s  20      ▂___  WPA2 802.1X
admin@rp4-nwk2:~$ sudo nmcli device wifi connect "unreal5G" password "iotiotiot"
Device 'wlan0' successfully activated with '14f96b41-98c8-448d-9bb8-bc476b1f4f3e'.
```

### WIFI 접속

   * 아래 코드를 이용하여 wifi에 접속할 수있음
```
sudo nmcli device wifi connect [와이파이 이름] password [와이파이 비밀번호]
```




