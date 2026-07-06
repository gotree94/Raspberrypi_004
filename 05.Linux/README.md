# 🐧 리눅스 필수 명령어 100선

> 임베디드 개발자 및 리눅스 사용자를 위한 핵심 명령어 레퍼런스

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Linux](https://img.shields.io/badge/OS-Linux-blue?logo=linux)
![Shell](https://img.shields.io/badge/Shell-Bash-green?logo=gnu-bash)

---

## 📋 목차

| 분류 | 명령어 수 |
|------|-----------|
| [📁 파일 및 디렉토리 관리](#-파일-및-디렉토리-관리) | 20개 |
| [📄 파일 내용 보기 및 편집](#-파일-내용-보기-및-편집) | 10개 |
| [🔍 검색 및 필터링](#-검색-및-필터링) | 10개 |
| [⚙️ 프로세스 관리](#️-프로세스-관리) | 10개 |
| [🌐 네트워크](#-네트워크) | 10개 |
| [💾 디스크 및 시스템 정보](#-디스크-및-시스템-정보) | 10개 |
| [👤 사용자 및 권한 관리](#-사용자-및-권한-관리) | 10개 |
| [📦 패키지 및 압축](#-패키지-및-압축) | 10개 |
| [🔧 시스템 관리 및 기타](#-시스템-관리-및-기타) | 10개 |

---

## 📁 파일 및 디렉토리 관리

### 1. `ls` — 디렉토리 목록 출력

디렉토리의 파일과 폴더 목록을 표시합니다.

```bash
ls                    # 현재 디렉토리 목록
ls -l                 # 상세 정보 (권한, 크기, 날짜)
ls -la                # 숨김 파일 포함 상세 목록
ls -lh                # 파일 크기를 사람이 읽기 쉽게 표시
ls -lt                # 수정 시간 기준 정렬
ls /home/user/        # 특정 디렉토리 목록
```

---

### 2. `cd` — 디렉토리 이동

현재 작업 디렉토리를 변경합니다.

```bash
cd /home/user/        # 절대 경로 이동
cd ..                 # 상위 디렉토리로 이동
cd ~                  # 홈 디렉토리로 이동
cd -                  # 이전 디렉토리로 이동
cd ../../etc          # 두 단계 위로 올라가서 etc로 이동
```

---

### 3. `pwd` — 현재 디렉토리 경로 출력

현재 작업 중인 디렉토리의 절대 경로를 출력합니다.

```bash
pwd
# 출력 예시: /home/namu/projects
```

---

### 4. `mkdir` — 디렉토리 생성

새로운 디렉토리를 만듭니다.

```bash
mkdir mydir               # 단일 디렉토리 생성
mkdir -p a/b/c            # 중간 경로 포함 재귀적 생성
mkdir -m 755 mydir        # 권한 지정 후 생성
mkdir dir1 dir2 dir3      # 여러 디렉토리 동시 생성
```

---

### 5. `rm` — 파일/디렉토리 삭제

파일 또는 디렉토리를 삭제합니다.

```bash
rm file.txt               # 파일 삭제
rm -r mydir/              # 디렉토리 재귀 삭제
rm -rf mydir/             # 강제 재귀 삭제 (확인 없음, 주의!)
rm -i file.txt            # 삭제 전 확인 요청
rm *.log                  # 패턴 매칭으로 여러 파일 삭제
```

> ⚠️ `rm -rf /` 는 절대 실행하지 마세요!

---

### 6. `cp` — 파일/디렉토리 복사

파일이나 디렉토리를 복사합니다.

```bash
cp file.txt backup.txt        # 파일 복사
cp -r srcdir/ dstdir/         # 디렉토리 재귀 복사
cp -p file.txt backup.txt     # 권한/타임스탬프 유지 복사
cp -u file.txt backup.txt     # 원본이 더 새로울 때만 복사
cp *.c /backup/               # 여러 파일 복사
```

---

### 7. `mv` — 파일/디렉토리 이동 및 이름 변경

파일을 이동하거나 이름을 바꿉니다.

```bash
mv old.txt new.txt            # 파일 이름 변경
mv file.txt /tmp/             # 파일 이동
mv dir1/ /home/user/          # 디렉토리 이동
mv -i file.txt backup.txt     # 덮어쓰기 전 확인
mv -u file.txt /backup/       # 더 새로운 파일만 이동
```

---

### 8. `touch` — 파일 생성 및 타임스탬프 갱신

빈 파일을 생성하거나 기존 파일의 접근/수정 시간을 갱신합니다.

```bash
touch newfile.txt             # 빈 파일 생성
touch file1.txt file2.txt     # 여러 파일 동시 생성
touch -t 202401011200 f.txt   # 특정 시간으로 타임스탬프 설정
touch -a file.txt             # 접근 시간만 갱신
touch -m file.txt             # 수정 시간만 갱신
```

---

### 9. `ln` — 링크 생성

하드 링크 또는 심볼릭 링크를 생성합니다.

```bash
ln file.txt hardlink.txt      # 하드 링크 생성
ln -s /usr/bin/python python  # 심볼릭 링크 생성
ln -sf new.txt link.txt       # 기존 심볼릭 링크 강제 갱신
ls -l link.txt                # 링크 확인
readlink link.txt             # 링크 대상 경로 출력
```

---

### 10. `find` — 파일 검색

조건에 맞는 파일을 디렉토리 트리에서 검색합니다.

```bash
find . -name "*.c"                        # 현재 위치에서 .c 파일 검색
find /home -name "*.txt" -type f          # 일반 파일만 검색
find . -mtime -7                          # 7일 이내 수정된 파일
find . -size +10M                         # 10MB 이상 파일
find . -perm 644                          # 특정 권한의 파일
find . -name "*.log" -exec rm {} \;      # 검색 후 삭제 실행
```

---

### 11. `stat` — 파일 상세 정보

파일의 상세 메타데이터(권한, inode, 시간 등)를 표시합니다.

```bash
stat file.txt
# 출력 예시:
#   File: file.txt
#   Size: 1024      Blocks: 8    IO Block: 4096  regular file
#   Inode: 12345    Links: 1
#   Access: 2024-01-01 12:00:00
```

---

### 12. `file` — 파일 타입 확인

파일의 실제 형식(타입)을 판별합니다.

```bash
file image.jpg          # JPEG 이미지 파일 확인
file script.sh          # 쉘 스크립트 확인
file binary             # ELF 실행 파일 확인
file *                  # 현재 디렉토리 모든 파일 타입 출력
```

---

### 13. `chmod` — 파일 권한 변경

파일 또는 디렉토리의 접근 권한을 변경합니다.
* 순서 : 소유자(user) / 그룹(group) / 기타(others)

```bash
chmod 755 script.sh         # rwxr-xr-x 권한 설정
chmod +x script.sh          # 실행 권한 추가
chmod -w file.txt           # 쓰기 권한 제거
chmod -R 644 /data/         # 재귀적으로 권한 변경
chmod u+x,g-w file.txt      # 소유자 실행 추가, 그룹 쓰기 제거
```

| 숫자 | 권한 | 의미 |
|------|------|------|
| 7 | rwx | 읽기+쓰기+실행 |
| 6 | rw- | 읽기+쓰기 |
| 5 | r-x | 읽기+실행 |
| 4 | r-- | 읽기 전용 |

---

### 14. `chown` — 파일 소유자 변경

파일의 소유자 및 그룹을 변경합니다.

```bash
chown user file.txt             # 소유자 변경
chown user:group file.txt       # 소유자와 그룹 동시 변경
chown -R user:group /data/      # 재귀적으로 변경
chown :group file.txt           # 그룹만 변경
```

---

### 15. `chgrp` — 파일 그룹 변경

파일의 소유 그룹을 변경합니다.

```bash
chgrp developers file.txt       # 그룹 변경
chgrp -R developers /project/   # 디렉토리 재귀 변경
```

---

### 16. `du` — 디스크 사용량 확인

디렉토리 또는 파일의 디스크 사용량을 확인합니다.

```bash
du -h file.txt              # 사람이 읽기 쉬운 형태로 출력
du -sh /home/user/          # 디렉토리 전체 용량 합산
du -ah /var/log/            # 모든 파일 개별 크기 출력
du -h --max-depth=1 /       # 1단계 깊이까지만 표시
du -sh * | sort -h          # 크기 기준 정렬
```

---

### 17. `df` — 파일시스템 디스크 용량

마운트된 파일시스템의 용량 정보를 표시합니다.

```bash
df -h                       # 모든 파일시스템 용량 (읽기 쉬운 단위)
df -h /home                 # 특정 경로의 파일시스템 확인
df -T                       # 파일시스템 타입 포함 출력
df -i                       # inode 사용량 확인
```

---

### 18. `mount` — 파일시스템 마운트

디바이스를 파일시스템에 마운트합니다.

```bash
mount /dev/sdb1 /mnt/usb        # USB 드라이브 마운트
mount -t ext4 /dev/sdb1 /mnt/   # 파일시스템 타입 지정
mount -o ro /dev/sdb1 /mnt/     # 읽기 전용 마운트
mount                            # 현재 마운트 목록 출력
umount /mnt/usb                  # 마운트 해제
```

---

### 19. `umount` — 파일시스템 마운트 해제

마운트된 파일시스템을 분리합니다.

```bash
umount /mnt/usb             # 마운트 포인트로 해제
umount /dev/sdb1            # 디바이스명으로 해제
umount -l /mnt/usb          # 지연 마운트 해제 (사용 중일 때)
umount -f /mnt/nfs          # 강제 해제 (NFS 등)
```

---

### 20. `dd` — 디스크 복사/변환

블록 단위로 데이터를 복사하거나 변환합니다.

```bash
# SD 카드에 이미지 굽기 (임베디드 필수!)
dd if=raspios.img of=/dev/sdb bs=4M status=progress

# 디스크 백업
dd if=/dev/sda of=backup.img bs=64K status=progress

# 빈 파일 생성 (100MB)
dd if=/dev/zero of=test.bin bs=1M count=100

# 디스크 완전 초기화
dd if=/dev/urandom of=/dev/sdb bs=1M
```

---

## 📄 파일 내용 보기 및 편집

### 21. `cat` — 파일 내용 출력

파일의 내용을 표준 출력으로 출력합니다.

```bash
cat file.txt                # 파일 내용 출력
cat file1.txt file2.txt     # 여러 파일 연결 출력
cat -n file.txt             # 행 번호 포함 출력
cat -A file.txt             # 특수 문자 표시 (탭, 줄바꿈 등)
cat > newfile.txt           # 키보드 입력으로 파일 생성 (Ctrl+D 종료)
cat file1.txt >> file2.txt  # 파일 내용 추가
```

---

### 22. `less` — 파일 페이지 단위 보기

파일 내용을 페이지 단위로 스크롤하며 볼 수 있습니다.

```bash
less file.txt               # 파일 열기
less +G file.txt            # 파일 끝부터 열기
less +F file.txt            # 실시간 추가 내용 모니터링 (tail -f와 유사)

# less 내부 단축키
# Space / b     : 다음/이전 페이지
# /pattern      : 앞으로 검색
# ?pattern      : 뒤로 검색
# n / N         : 다음/이전 검색 결과
# q             : 종료
```

---

### 23. `more` — 파일 순방향 페이징

파일을 위에서 아래로 한 페이지씩 표시합니다.

```bash
more file.txt               # 파일 열기
more -n 20 file.txt         # 한 번에 20줄씩 표시
command | more              # 명령 출력을 페이지 단위로 보기
```

---

### 24. `head` — 파일 앞부분 출력

파일의 처음 N줄을 출력합니다.

```bash
head file.txt               # 기본 앞 10줄 출력
head -n 20 file.txt         # 앞 20줄 출력
head -c 100 file.txt        # 앞 100바이트 출력
head -n -5 file.txt         # 마지막 5줄을 제외한 전체 출력
```

---

### 25. `tail` — 파일 뒷부분 출력

파일의 마지막 N줄을 출력합니다.

```bash
tail file.txt               # 기본 마지막 10줄 출력
tail -n 50 file.txt         # 마지막 50줄 출력
tail -f /var/log/syslog     # 실시간 로그 모니터링 (임베디드 디버깅 필수!)
tail -f -n 100 app.log      # 마지막 100줄부터 실시간 모니터링
tail -c 200 file.txt        # 마지막 200바이트 출력
```

---

### 26. `wc` — 줄/단어/바이트 수 계산

파일의 줄 수, 단어 수, 바이트 수를 계산합니다.

```bash
# 예제 파일 준비
cat > file.txt << 'EOF'
Hello Linux World
This is a test file
Linux is awesome
EOF

# 실행 및 결과
wc file.txt                 # 3  12  58 file.txt (줄 단어 바이트)
wc -l file.txt              # 3 file.txt
wc -w file.txt              # 12 file.txt
wc -c file.txt              # 58 file.txt
wc -l *.c                   # 여러 소스 파일 줄 수 합산
```

---

### 27. `diff` — 파일 비교

두 파일 간의 차이점을 표시합니다.

```bash
# 예제 파일 준비
cat > file1.txt << 'EOF'
apple
banana
cherry
EOF

cat > file2.txt << 'EOF'
apple
blueberry
cherry
date
EOF

# 실행 및 결과
diff file1.txt file2.txt
# 출력:
# 2c2
# < banana
# ---
# > blueberry
# 4a5
# > date

diff -u file1.txt file2.txt     # unified 형식 출력 (패치 파일 생성에 유용)
diff -r dir1/ dir2/             # 디렉토리 재귀 비교
diff -i file1.txt file2.txt     # 대소문자 무시
diff --color file1.txt file2.txt # 색상으로 차이 표시
```

---

### 28. `sort` — 파일 정렬

텍스트 파일의 내용을 정렬합니다.

```bash
# 예제 파일 준비
cat > file.txt << 'EOF'
banana
apple
cherry
banana
date
apple
EOF

cat > numbers.txt << 'EOF'
10
2
33
5
111
EOF

# 실행 및 결과
sort file.txt               # 알파벳 순 정렬: apple apple banana banana cherry date
sort -r file.txt            # 역순 정렬: date cherry banana banana apple apple
sort -n numbers.txt         # 숫자 기준 정렬: 2 5 10 33 111
sort -u file.txt            # 중복 제거 후 정렬: apple banana cherry date
```

---

### 29. `uniq` — 중복 행 처리

정렬된 파일에서 중복 행을 제거하거나 카운트합니다.

```bash
# 예제 파일 준비 (정렬 전)
cat > file.txt << 'EOF'
apple
banana
banana
cherry
cherry
cherry
date
EOF

# 실행 및 결과 (sort와 파이프로 연결하여 사용)
sort file.txt | uniq            # apple banana cherry date (중복 제거)
sort file.txt | uniq -c         # 1 apple, 2 banana, 3 cherry, 1 date (중복 횟수)
sort file.txt | uniq -d         # banana cherry (중복된 행만)
sort file.txt | uniq -u         # apple date (고유한 행만, 한 번만 등장)
```

---

### 30. `cut` — 텍스트 필드 추출

각 행에서 특정 필드나 문자를 추출합니다.

```bash
# 예제 파일 준비
cat > data.csv << 'EOF'
name,age,city
Alice,30,Seoul
Bob,25,Busan
Charlie,35,Incheon
EOF

# 실행 및 결과
cut -d, -f1 data.csv            # name  Alice  Bob  Charlie (1번째 열)
cut -d, -f2 data.csv            # age  30  25  35 (2번째 열)
cut -d, -f1,3 data.csv          # name,city  Alice,Seoul  Bob,Busan  Charlie,Incheon
cut -c1-4 data.csv              # name  Alic  Bob,  Char (앞 4글자)

# /etc/passwd 예제 (시스템)
cut -d: -f1 /etc/passwd         # ':' 구분자로 1번째 필드 추출 (사용자명)
cut -d: -f1,3 /etc/passwd       # 1번째, 3번째 필드 추출
```

---

## 🔍 검색 및 필터링

### 31. `grep` — 패턴 검색

파일에서 정규표현식 패턴에 일치하는 행을 검색합니다.

```bash
grep "error" /var/log/syslog        # 특정 문자열 검색
grep -i "error" file.txt            # 대소문자 무시
grep -r "TODO" ./src/               # 디렉토리 재귀 검색
grep -n "main" main.c               # 행 번호 포함 출력
grep -v "comment" file.txt          # 패턴 제외 행 출력
grep -c "error" log.txt             # 일치 행 수 출력
grep -l "pattern" *.txt             # 일치하는 파일명만 출력
grep -E "err|warn" log.txt          # 확장 정규표현식
grep -A 3 -B 3 "error" log.txt      # 앞뒤 3줄 함께 출력
```

---

### 32. `awk` — 텍스트 처리 언어

강력한 패턴 매칭 및 텍스트 처리 도구입니다.

```bash
# 예제 파일 준비
cat > score.txt << 'EOF'
Alice 90 85 88
Bob 75 92 80
Charlie 88 70 95
Diana 95 90 92
EOF

# 실행 및 결과
awk '{print $1}' score.txt              # Alice Bob Charlie Diana (1번째 필드)
awk '{print $1, $2}' score.txt          # Alice 90  Bob 75  Charlie 88  Diana 95
awk '{sum += $2} END {print sum}' score.txt  # 348 (2열 합계)
awk '{sum += $2; count++} END {print sum/count}' score.txt  # 87 (2열 평균)
awk 'NR==3' score.txt                   # Charlie 88 70 95 (3번째 행만)
awk '{if ($3 > 80) print $1, $3}' score.txt  # Alice 85  Bob 92  Diana 90

# 구분자 지정 예제
awk -F: '{print $1, $3}' /etc/passwd    # ':' 구분자로 1,3번째 필드 출력
awk '{print NR, $0}' score.txt          # 행 번호 추가 출력
```

---

### 33. `sed` — 스트림 에디터

파이프라인에서 텍스트를 치환, 삭제, 삽입합니다.

```bash
sed 's/old/new/' file.txt               # 각 행의 첫 번째 일치만 치환
sed 's/old/new/g' file.txt              # 모든 일치 치환 (global)
sed -i 's/old/new/g' file.txt          # 파일 직접 수정
sed -n '5,10p' file.txt                # 5~10행 출력
sed '/pattern/d' file.txt              # 패턴 포함 행 삭제
sed '3a\추가할 내용' file.txt           # 3행 뒤에 행 추가
sed -i 's/#.*//; /^$/d' config.txt     # 주석 및 빈 줄 제거
```

---

### 34. `locate` — 파일 빠른 검색

데이터베이스 기반으로 파일을 빠르게 검색합니다.

```bash
locate filename.txt             # 파일명으로 검색
locate -i filename.txt          # 대소문자 무시 검색
locate "*.conf"                 # 패턴으로 검색
updatedb                        # 데이터베이스 갱신 (root 필요)
locate -c "*.py"                # 검색 결과 수만 출력
```

---

### 35. `which` — 명령어 경로 확인

명령어의 실행 파일 경로를 찾습니다.

```bash
which python3               # python3 실행 파일 경로
which gcc                   # GCC 컴파일러 경로
which -a python             # 모든 python 경로 출력
```

---

### 36. `whereis` — 명령어 관련 파일 검색

명령어의 바이너리, 소스, 매뉴얼 경로를 찾습니다.

```bash
whereis gcc                 # GCC 관련 파일 모두 검색
whereis -b gcc              # 바이너리만 검색
whereis -m python3          # 매뉴얼 페이지만 검색
```

---

### 37. `xargs` — 인자 전달 및 실행

표준 입력을 읽어 명령의 인수로 전달합니다.

```bash
find . -name "*.log" | xargs rm             # 찾은 파일 모두 삭제
find . -name "*.c" | xargs grep "main"      # 여러 파일에서 검색
cat files.txt | xargs -I {} cp {} /backup/  # 파일 목록으로 복사
echo "a b c" | xargs -n1 echo              # 한 번에 하나씩 처리
ls *.txt | xargs wc -l                     # 여러 파일 줄 수 합산
```

---

### 38. `tr` — 문자 변환 및 삭제

문자를 변환하거나 삭제합니다.

```bash
echo "hello" | tr 'a-z' 'A-Z'      # 소문자 → 대문자 변환
echo "hello world" | tr -d ' '      # 공백 삭제
echo "aabbcc" | tr -s 'a-z'         # 연속 중복 문자 압축
cat file.txt | tr '\n' ' '          # 줄바꿈을 공백으로 변환
echo "abc123" | tr -d '0-9'         # 숫자 삭제
```

---

### 39. `tee` — 출력 분기

표준 입력을 파일과 표준 출력으로 동시에 보냅니다.

```bash
ls -l | tee output.txt              # 화면 출력과 동시에 파일 저장
ls -l | tee -a output.txt           # 파일에 추가 (append)
command | tee log.txt | grep error  # 파이프 중간에서 로그 저장
```

---

### 40. `strings` — 바이너리 내 문자열 추출

바이너리 파일에서 출력 가능한 문자열을 추출합니다.

```bash
strings /usr/bin/ls             # 실행 파일에서 문자열 추출
strings firmware.bin | grep "version"  # 펌웨어 버전 정보 확인
strings -n 8 binary.elf        # 8자 이상의 문자열만 추출
```

---

## ⚙️ 프로세스 관리

### 41. `ps` — 프로세스 목록

현재 실행 중인 프로세스를 표시합니다.

```bash
ps                          # 현재 쉘의 프로세스만
ps aux                      # 모든 사용자의 모든 프로세스
ps -ef                      # 전체 형식으로 모든 프로세스
ps aux | grep nginx         # 특정 프로세스 검색
ps -p 1234                  # 특정 PID 정보
ps --sort=-%mem | head      # 메모리 사용량 기준 정렬
```

---

### 42. `top` — 실시간 프로세스 모니터링

시스템 자원 사용 현황을 실시간으로 모니터링합니다.

```bash
top                         # 실시간 모니터링 시작
top -p 1234                 # 특정 PID만 모니터링
top -u username             # 특정 사용자 프로세스만

# top 내부 단축키
# k    : 프로세스 종료 (kill)
# r    : nice 값 변경 (renice)
# M    : 메모리 사용량 기준 정렬
# P    : CPU 사용량 기준 정렬
# q    : 종료
```

---

### 43. `htop` — 인터랙티브 프로세스 뷰어

top의 개선 버전으로 더 직관적인 인터페이스를 제공합니다.

```bash
htop                        # htop 실행
htop -u namu                # 특정 사용자 프로세스만
htop -p 1234,5678           # 특정 PID들만 모니터링
# F5: 트리 뷰, F6: 정렬, F9: kill, F10: 종료
```

---

### 44. `kill` — 프로세스 종료

PID를 지정하여 프로세스에 시그널을 전송합니다.

```bash
kill 1234                   # SIGTERM (정상 종료 요청)
kill -9 1234                # SIGKILL (강제 종료)
kill -15 1234               # SIGTERM (명시적)
kill -l                     # 사용 가능한 시그널 목록
killall nginx               # 이름으로 프로세스 종료
pkill -f "python script"    # 패턴으로 프로세스 종료
```

| 시그널 | 번호 | 의미 |
|--------|------|------|
| SIGTERM | 15 | 정상 종료 요청 |
| SIGKILL | 9 | 강제 종료 |
| SIGHUP | 1 | 재시작 |
| SIGSTOP | 19 | 일시 정지 |

---

### 45. `jobs` — 백그라운드 작업 목록

현재 쉘의 백그라운드/포그라운드 작업을 나열합니다.

```bash
jobs                        # 작업 목록
jobs -l                     # PID 포함 작업 목록
fg %1                       # 1번 작업을 포그라운드로
bg %2                       # 2번 작업을 백그라운드로
command &                   # 명령을 백그라운드로 실행
Ctrl+Z                      # 실행 중인 작업을 일시 정지
```

---

### 46. `nohup` — 로그아웃 후에도 실행 유지

터미널 종료 후에도 프로세스가 계속 실행되도록 합니다.

```bash
nohup python3 server.py &           # 백그라운드 실행, nohup.out에 로그
nohup ./script.sh > output.log 2>&1 &  # 로그 파일 지정
nohup command &                     # HUP 시그널 무시 후 백그라운드 실행
```

---

### 47. `nice` / `renice` — 프로세스 우선순위

프로세스의 CPU 스케줄링 우선순위를 조정합니다.

```bash
nice -n 10 ./heavy_process         # nice 값 10으로 실행 (낮은 우선순위)
nice -n -5 ./realtime_process      # 높은 우선순위 (root 필요)
renice 15 -p 1234                  # 실행 중인 프로세스 우선순위 변경
renice -n 5 -u username            # 사용자의 모든 프로세스 변경
# nice 범위: -20(최고) ~ 19(최저), 기본값 0
```

---

### 48. `strace` — 시스템 콜 추적

프로세스의 시스템 콜 및 시그널을 추적합니다.

```bash
strace ls                           # ls 명령의 시스템 콜 추적
strace -p 1234                      # 실행 중인 프로세스 추적
strace -e trace=open,read ls        # 특정 시스템 콜만 추적
strace -o output.txt ./program      # 결과 파일로 저장
strace -c ./program                 # 시스템 콜 통계 요약
```

---

### 49. `lsof` — 열린 파일 목록

현재 열려있는 파일과 프로세스 정보를 표시합니다.

```bash
lsof                            # 모든 열린 파일
lsof -p 1234                    # 특정 PID의 열린 파일
lsof /var/log/syslog            # 특정 파일을 사용하는 프로세스
lsof -i :8080                   # 특정 포트를 사용하는 프로세스
lsof -u username                # 특정 사용자의 열린 파일
lsof -i TCP                     # 모든 TCP 연결
```

---

### 50. `cron` / `crontab` — 작업 스케줄러

주기적으로 명령을 자동 실행하도록 예약합니다.

```bash
crontab -e                      # crontab 편집
crontab -l                      # 현재 crontab 목록
crontab -r                      # crontab 삭제

# 크론 문법: 분 시 일 월 요일 명령
# ┌───── 분 (0-59)
# │ ┌───── 시 (0-23)
# │ │ ┌───── 일 (1-31)
# │ │ │ ┌───── 월 (1-12)
# │ │ │ │ ┌───── 요일 (0-7, 0과7이 일요일)
# │ │ │ │ │
# * * * * * /path/to/command

# 예시
0 2 * * *  /home/namu/backup.sh          # 매일 새벽 2시에 실행
*/5 * * * * /usr/bin/python3 monitor.py  # 5분마다 실행
0 9 * * 1   /usr/local/bin/weekly.sh    # 매주 월요일 9시
```

---

## 🌐 네트워크

### 51. `ping` — 네트워크 연결 확인

ICMP 패킷으로 호스트의 연결 가능 여부를 테스트합니다.

```bash
ping google.com                 # 연속 ping
ping -c 5 192.168.1.1           # 5회만 ping
ping -i 0.5 host                # 0.5초 간격으로 ping
ping -s 1400 host               # 패킷 크기 지정
ping6 ::1                       # IPv6 ping
```

---

### 52. `ifconfig` — 네트워크 인터페이스 설정

네트워크 인터페이스의 설정을 확인하거나 변경합니다.

```bash
ifconfig                        # 모든 인터페이스 정보
ifconfig eth0                   # eth0 인터페이스 정보
ifconfig eth0 192.168.1.100     # IP 주소 설정
ifconfig eth0 up                # 인터페이스 활성화
ifconfig eth0 down              # 인터페이스 비활성화
ifconfig eth0 mtu 1500          # MTU 설정
```

---

### 53. `ip` — 네트워크 설정 (ifconfig 대체)

최신 리눅스의 표준 네트워크 설정 명령입니다.

```bash
ip addr show                    # 모든 인터페이스 주소 정보
ip addr show eth0               # eth0 정보
ip addr add 192.168.1.10/24 dev eth0  # IP 주소 추가
ip link set eth0 up             # 인터페이스 활성화
ip route show                   # 라우팅 테이블 확인
ip route add 0.0.0.0/0 via 192.168.1.1  # 기본 게이트웨이 설정
ip neigh show                   # ARP 테이블 확인
```

---

### 54. `netstat` — 네트워크 상태

네트워크 연결, 라우팅 테이블, 인터페이스 통계를 표시합니다.

```bash
netstat -tuln                   # 리스닝 중인 TCP/UDP 포트
netstat -an                     # 모든 연결 상태
netstat -p                      # PID/프로세스명 포함
netstat -r                      # 라우팅 테이블
netstat -s                      # 프로토콜별 통계
netstat -i                      # 네트워크 인터페이스 통계
```

---

### 55. `ss` — 소켓 상태 (netstat 대체)

netstat보다 빠르고 자세한 소켓 정보를 표시합니다.

```bash
ss -tuln                        # 리스닝 중인 TCP/UDP 소켓
ss -t state established         # 연결된 TCP 소켓
ss -p                           # 프로세스 정보 포함
ss -s                           # 소켓 통계 요약
ss -tnp | grep :8080            # 특정 포트 확인
```

---

### 56. `ssh` — 보안 원격 접속

암호화된 원격 쉘 접속 프로토콜입니다.

```bash
ssh user@192.168.1.100          # 기본 SSH 접속
ssh -p 2222 user@host           # 포트 지정
ssh -i ~/.ssh/id_rsa user@host  # 키 파일 지정
ssh -L 8080:localhost:80 user@host  # 로컬 포트 포워딩
ssh -X user@host                # X11 포워딩 (GUI 앱)
ssh-keygen -t rsa -b 4096       # RSA 키 쌍 생성
ssh-copy-id user@host           # 공개키 복사 (패스워드 없는 로그인)
```

---

### 57. `scp` — 보안 파일 복사

SSH를 통해 원격 호스트와 파일을 복사합니다.

```bash
scp file.txt user@host:/remote/path/        # 로컬 → 원격
scp user@host:/remote/file.txt ./           # 원격 → 로컬
scp -r localdir/ user@host:/remote/dir/     # 디렉토리 복사
scp -P 2222 file.txt user@host:/path/       # 포트 지정
```

---

### 58. `wget` — 파일 다운로드

HTTP/HTTPS/FTP로 파일을 다운로드합니다.

```bash
wget https://example.com/file.tar.gz            # 파일 다운로드
wget -O output.txt https://example.com/file     # 저장 파일명 지정
wget -c https://example.com/large.file          # 이어받기
wget -r -np https://example.com/docs/           # 재귀 다운로드
wget -q --show-progress https://example.com/f   # 진행률 표시
wget --limit-rate=1m URL                        # 다운로드 속도 제한
```

---

### 59. `curl` — URL 데이터 전송

HTTP, FTP 등 다양한 프로토콜로 데이터를 전송/수신합니다.

```bash
curl https://api.example.com                    # GET 요청
curl -o file.txt https://example.com/file       # 파일 저장
curl -X POST -d '{"key":"val"}' -H "Content-Type: application/json" URL  # POST 요청
curl -I https://example.com                     # HTTP 헤더만 확인
curl -u user:password https://example.com       # 인증
curl -v URL                                     # 자세한 출력 (디버깅)
curl --retry 3 URL                              # 실패 시 재시도
```

---

### 60. `nmap` — 네트워크 스캔

네트워크 호스트와 포트를 스캔합니다.

```bash
nmap 192.168.1.1                    # 단일 호스트 스캔
nmap 192.168.1.0/24                 # 서브넷 전체 스캔
nmap -p 22,80,443 192.168.1.1       # 특정 포트 스캔
nmap -sV 192.168.1.1                # 서비스 버전 감지
nmap -O 192.168.1.1                 # OS 감지
nmap -sn 192.168.1.0/24             # ping 스캔 (포트 스캔 없이 호스트 확인)
```

---

## 💾 디스크 및 시스템 정보

### 61. `uname` — 시스템 정보

시스템의 커널 및 하드웨어 정보를 출력합니다.

```bash
uname -a                    # 모든 시스템 정보
uname -r                    # 커널 버전
uname -m                    # 아키텍처 (x86_64, aarch64 등)
uname -n                    # 호스트명
uname -s                    # 커널 이름
```

---

### 62. `hostname` — 호스트명 확인/설정

시스템의 호스트명을 확인하거나 변경합니다.

```bash
hostname                    # 현재 호스트명 출력
hostname newname            # 임시 호스트명 변경
hostname -I                 # IP 주소 목록 출력
hostnamectl set-hostname newname  # 영구 호스트명 변경 (systemd)
```

---

### 63. `uptime` — 시스템 가동 시간

시스템의 가동 시간과 부하 평균을 표시합니다.

```bash
uptime
# 출력 예시:
# 14:23:11 up 5 days, 3:15, 2 users, load average: 0.12, 0.08, 0.05
#          ↑가동시간          ↑로그인수    ↑1분  ↑5분  ↑15분 평균 부하
```

---

### 64. `free` — 메모리 사용량

시스템의 메모리 사용 현황을 표시합니다.

```bash
free                        # 기본 출력 (kB 단위)
free -h                     # 사람이 읽기 쉬운 단위
free -m                     # MB 단위
free -s 5                   # 5초마다 갱신
watch -n 1 free -h          # 1초마다 갱신 (watch와 함께)
```

---

### 65. `vmstat` — 가상 메모리 통계

CPU, 메모리, 디스크 I/O, 시스템 활동 통계를 표시합니다.

```bash
vmstat                      # 현재 통계 출력
vmstat 2 10                 # 2초 간격으로 10회 출력
vmstat -s                   # 메모리 통계 요약
vmstat -d                   # 디스크 통계
```

---

### 66. `iostat` — I/O 통계

CPU 및 디스크 I/O 통계를 표시합니다.

```bash
iostat                      # CPU 및 디스크 I/O 통계
iostat -x                   # 확장 통계 (섹터, 큐 깊이 등)
iostat 2 5                  # 2초 간격 5회 출력
iostat -d /dev/sda          # 특정 디바이스만
```

---

### 67. `dmesg` — 커널 메시지

커널 링 버퍼의 메시지를 출력합니다 (부팅 메시지, 드라이버 오류 등).

```bash
dmesg                           # 전체 커널 메시지
dmesg | tail -20                # 최근 20줄
dmesg | grep -i "error"         # 에러 메시지만
dmesg -T                        # 타임스탬프를 사람이 읽는 형식으로
dmesg -w                        # 실시간 커널 메시지 모니터링
dmesg -c                        # 출력 후 링 버퍼 초기화 (root 필요)
```

---

### 68. `lsblk` — 블록 디바이스 목록

블록 디바이스(디스크, 파티션)의 트리 구조를 표시합니다.

```bash
lsblk                       # 블록 디바이스 목록
lsblk -f                    # 파일시스템 정보 포함
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT  # 특정 필드 출력
```

---

### 69. `lspci` — PCI 디바이스 목록

PCI 버스에 연결된 디바이스 목록을 표시합니다.

```bash
lspci                       # PCI 디바이스 목록
lspci -v                    # 상세 정보
lspci -k                    # 사용 중인 커널 드라이버 정보
lspci | grep -i "ethernet"  # 이더넷 카드 확인
lspci | grep -i "vga"       # 그래픽 카드 확인
```

---

### 70. `lsusb` — USB 디바이스 목록

연결된 USB 디바이스 목록을 표시합니다.

```bash
lsusb                       # USB 디바이스 목록
lsusb -v                    # 상세 정보
lsusb -t                    # 트리 구조로 표시
lsusb -d 0403:6001          # Vendor:Product ID로 검색
```

---

## 👤 사용자 및 권한 관리

### 71. `whoami` — 현재 사용자 확인

현재 로그인된 사용자명을 출력합니다.

```bash
whoami
# 출력: namu
```

---

### 72. `who` — 로그인 사용자 목록

현재 시스템에 로그인한 사용자 목록을 표시합니다.

```bash
who                         # 로그인 사용자 목록
who -H                      # 헤더 포함
who -b                      # 마지막 부팅 시간
w                           # 로그인 사용자 및 활동 정보 (확장판)
```

---

### 73. `id` — 사용자 ID 정보

사용자의 UID, GID, 소속 그룹 정보를 출력합니다.

```bash
id                          # 현재 사용자 정보
id username                 # 특정 사용자 정보
id -u                       # UID만 출력
id -g                       # 기본 GID만 출력
id -G                       # 모든 그룹 GID 출력
```

---

### 74. `useradd` — 사용자 추가

새로운 사용자 계정을 생성합니다.

```bash
useradd username                        # 사용자 생성
useradd -m username                     # 홈 디렉토리 생성 포함
useradd -m -s /bin/bash username        # 쉘 지정
useradd -m -G sudo username             # 그룹 지정
useradd -m -u 1001 username             # UID 지정
passwd username                         # 비밀번호 설정
```

---

### 75. `usermod` — 사용자 정보 변경

기존 사용자 계정 설정을 변경합니다.

```bash
usermod -aG sudo username           # sudo 그룹에 추가
usermod -aG docker username         # docker 그룹에 추가
usermod -s /bin/zsh username        # 쉘 변경
usermod -l newname oldname          # 사용자명 변경
usermod -L username                 # 계정 잠금
usermod -U username                 # 계정 잠금 해제
```

---

### 76. `userdel` — 사용자 삭제

사용자 계정을 삭제합니다.

```bash
userdel username                    # 사용자 삭제 (홈 디렉토리 유지)
userdel -r username                 # 사용자 + 홈 디렉토리 삭제
```

---

### 77. `groupadd` / `groupdel` — 그룹 관리

그룹을 생성하거나 삭제합니다.

```bash
groupadd developers                 # 그룹 생성
groupadd -g 1010 developers         # GID 지정 후 생성
groupdel developers                 # 그룹 삭제
cat /etc/group | grep developers    # 그룹 정보 확인
```

---

### 78. `sudo` — 관리자 권한 실행

다른 사용자(기본: root)의 권한으로 명령을 실행합니다.

```bash
sudo apt update                     # root 권한으로 실행
sudo -i                             # root 쉘로 전환
sudo -u otheruser command           # 다른 사용자로 실행
sudo !!                             # 이전 명령을 sudo로 재실행
visudo                              # sudoers 파일 편집
sudo -l                             # 현재 사용자의 sudo 권한 확인
```

---

### 79. `passwd` — 비밀번호 변경

사용자 비밀번호를 변경합니다.

```bash
passwd                      # 현재 사용자 비밀번호 변경
passwd username             # 특정 사용자 비밀번호 변경 (root)
passwd -l username          # 계정 잠금
passwd -u username          # 계정 잠금 해제
passwd -e username          # 다음 로그인 시 비밀번호 변경 강제
```

---

### 80. `su` — 사용자 전환

다른 사용자 계정으로 전환합니다.

```bash
su username                 # 사용자 전환 (환경 변수 유지)
su - username               # 사용자 전환 (완전한 로그인 쉘)
su -                        # root로 전환
su -c "command" username    # 특정 사용자로 명령 실행 후 복귀
```

---

## 📦 패키지 및 압축

### 81. `apt` — Debian/Ubuntu 패키지 관리

Debian 계열 리눅스의 패키지 관리자입니다.

```bash
sudo apt update                     # 패키지 목록 갱신
sudo apt upgrade                    # 패키지 업그레이드
sudo apt install package            # 패키지 설치
sudo apt remove package             # 패키지 제거
sudo apt purge package              # 패키지 + 설정 파일 제거
sudo apt autoremove                 # 불필요한 패키지 자동 제거
apt search keyword                  # 패키지 검색
apt show package                    # 패키지 정보 확인
apt list --installed                # 설치된 패키지 목록
```

---

### 82. `dpkg` — Debian 패키지 직접 관리

.deb 패키지 파일을 직접 설치/제거합니다.

```bash
dpkg -i package.deb                 # .deb 패키지 설치
dpkg -r package                     # 패키지 제거
dpkg -l                             # 설치된 패키지 목록
dpkg -l | grep python               # 특정 패키지 검색
dpkg -s package                     # 패키지 상태 확인
dpkg -L package                     # 패키지가 설치한 파일 목록
```

---

### 83. `tar` — 아카이브 관리

파일을 묶거나 풀어주는 아카이브 명령입니다.

```bash
# 압축 생성
tar -czvf archive.tar.gz directory/    # gzip 압축 (c=생성, z=gzip, v=verbose, f=파일)
tar -cjvf archive.tar.bz2 directory/   # bzip2 압축
tar -cJvf archive.tar.xz directory/    # xz 압축

# 압축 해제
tar -xzvf archive.tar.gz               # gzip 해제
tar -xjvf archive.tar.bz2              # bzip2 해제
tar -xJvf archive.tar.xz               # xz 해제
tar -xzvf archive.tar.gz -C /dest/     # 특정 디렉토리에 해제

# 확인
tar -tzvf archive.tar.gz               # 내용 목록 확인
```

---

### 84. `zip` / `unzip` — ZIP 압축

ZIP 형식으로 압축하거나 해제합니다.

```bash
zip archive.zip file1.txt file2.txt    # 파일 압축
zip -r archive.zip directory/          # 디렉토리 압축
zip -e archive.zip file.txt            # 암호화 압축
unzip archive.zip                      # 현재 디렉토리에 해제
unzip archive.zip -d /dest/            # 특정 디렉토리에 해제
unzip -l archive.zip                   # 내용 목록만 확인
```

---

### 85. `gzip` / `gunzip` — gzip 압축

단일 파일을 gzip으로 압축/해제합니다.

```bash
gzip file.txt                   # 압축 (원본 파일 삭제됨)
gzip -k file.txt                # 원본 파일 유지하며 압축
gzip -d file.txt.gz             # 압축 해제
gunzip file.txt.gz              # 압축 해제 (gzip -d와 동일)
gzip -9 file.txt                # 최고 압축률
gzip -l file.txt.gz             # 압축 정보 확인
```

---

### 86. `rsync` — 파일 동기화

효율적인 파일/디렉토리 동기화 도구입니다.

```bash
rsync -av src/ dst/                         # 로컬 동기화
rsync -av src/ user@host:/remote/dst/       # 원격으로 동기화
rsync -avz src/ user@host:/dst/             # 전송 시 압축
rsync -av --delete src/ dst/               # 소스에 없는 파일 삭제
rsync -av --dry-run src/ dst/              # 실제 실행 없이 미리보기
rsync -av --exclude='*.log' src/ dst/      # 특정 패턴 제외
rsync -av --progress src/ dst/             # 진행률 표시
```

---

### 87. `pip` — Python 패키지 관리

Python 패키지를 설치, 관리합니다.

```bash
pip install package                 # 패키지 설치
pip install package==1.2.3          # 특정 버전 설치
pip install -r requirements.txt     # requirements 파일로 설치
pip uninstall package               # 패키지 제거
pip list                            # 설치된 패키지 목록
pip show package                    # 패키지 정보
pip freeze > requirements.txt       # 설치 목록 저장
pip install --upgrade package       # 패키지 업그레이드
```

---

### 88. `make` — 빌드 자동화

Makefile을 기반으로 소프트웨어를 빌드합니다.

```bash
make                            # 기본 타겟 빌드
make all                        # 'all' 타겟 빌드
make clean                      # 빌드 파일 정리
make install                    # 설치
make -j4                        # 4개 병렬 빌드 (빠른 컴파일)
make -f MyMakefile              # 특정 Makefile 사용
make VARIABLE=value             # 변수 지정
```

---

### 89. `gcc` / `g++` — C/C++ 컴파일러

GNU C/C++ 컴파일러입니다.

```bash
gcc hello.c -o hello                    # C 소스 컴파일
g++ hello.cpp -o hello                  # C++ 소스 컴파일
gcc -Wall -Wextra main.c -o main        # 경고 활성화
gcc -O2 -o optimized main.c             # 최적화 빌드
gcc -g main.c -o debug                  # 디버그 정보 포함
gcc -I/usr/include -L/usr/lib -lm       # 헤더/라이브러리 경로 지정
arm-linux-gnueabihf-gcc main.c -o main  # ARM 크로스 컴파일
```

---

### 90. `git` — 버전 관리

소스 코드 버전 관리 시스템입니다.

```bash
git init                            # 저장소 초기화
git clone https://github.com/...    # 저장소 복제
git status                          # 상태 확인
git add file.txt                    # 스테이징
git add .                           # 모든 변경사항 스테이징
git commit -m "커밋 메시지"          # 커밋
git push origin main                # 원격 저장소에 push
git pull                            # 원격 저장소에서 pull
git branch feature                  # 브랜치 생성
git checkout feature                # 브랜치 전환
git merge feature                   # 브랜치 병합
git log --oneline --graph           # 커밋 로그 시각화
```

---

## 🔧 시스템 관리 및 기타

### 91. `systemctl` — 시스템 서비스 관리

systemd 기반 서비스를 관리합니다.

```bash
systemctl start nginx               # 서비스 시작
systemctl stop nginx                # 서비스 중지
systemctl restart nginx             # 서비스 재시작
systemctl reload nginx              # 설정 재로드
systemctl enable nginx              # 부팅 시 자동 시작 등록
systemctl disable nginx             # 자동 시작 해제
systemctl status nginx              # 서비스 상태 확인
systemctl list-units --type=service # 모든 서비스 목록
journalctl -u nginx -f              # 서비스 로그 실시간 확인
```

---

### 92. `journalctl` — 시스템 로그

systemd 저널 로그를 조회합니다.

```bash
journalctl                          # 전체 로그
journalctl -f                       # 실시간 로그 모니터링
journalctl -u nginx                 # 특정 서비스 로그
journalctl --since "1 hour ago"     # 1시간 이내 로그
journalctl --since "2024-01-01" --until "2024-01-02"  # 날짜 범위
journalctl -p err                   # 에러 레벨 이상만
journalctl -b                       # 현재 부팅 이후 로그
journalctl -b -1                    # 이전 부팅 로그
```

---

### 93. `env` / `export` — 환경 변수

환경 변수를 확인하거나 설정합니다.

```bash
env                                 # 모든 환경 변수 출력
echo $PATH                          # 특정 환경 변수 값 확인
export MY_VAR="value"               # 환경 변수 설정 (현재 세션)
export PATH=$PATH:/new/path         # PATH에 경로 추가
unset MY_VAR                        # 환경 변수 삭제
env -i command                      # 환경 변수 없이 명령 실행

# 영구 설정 (~/.bashrc 또는 ~/.profile에 추가)
echo 'export MY_VAR="value"' >> ~/.bashrc
source ~/.bashrc
```

---

### 94. `echo` — 문자열 출력

문자열이나 변수 값을 출력합니다.

```bash
echo "Hello, World!"            # 문자열 출력
echo $HOME                      # 환경 변수 출력
echo -n "No newline"            # 줄바꿈 없이 출력
echo -e "Line1\nLine2"          # 이스케이프 시퀀스 해석
echo "text" > file.txt          # 파일에 쓰기 (덮어쓰기)
echo "text" >> file.txt         # 파일에 추가
echo {1..5}                     # 범위 확장: 1 2 3 4 5
```

---

### 95. `alias` — 명령어 별칭

자주 사용하는 명령에 별칭을 지정합니다.

```bash
alias ll='ls -alF'                  # 별칭 생성
alias la='ls -A'
alias grep='grep --color=auto'
alias ..='cd ..'
alias ...='cd ../..'
alias df='df -h'
alias free='free -h'
alias unalias ll                    # 별칭 제거
alias                               # 모든 별칭 목록

# ~/.bashrc에 추가하여 영구 적용
echo "alias ll='ls -alF'" >> ~/.bashrc
```

---

### 96. `history` — 명령 히스토리

이전에 실행한 명령 목록을 표시합니다.

```bash
history                         # 전체 히스토리
history 20                      # 최근 20개
history | grep git              # 히스토리에서 검색
!123                            # 123번 명령 재실행
!!                              # 직전 명령 재실행
!git                            # 'git'으로 시작하는 최근 명령 재실행
Ctrl+R                          # 히스토리 역방향 검색 (인터랙티브)
history -c                      # 히스토리 삭제
```

---

### 97. `cmp` — 파일 바이트 비교

두 파일을 바이트 단위로 비교합니다.

```bash
cmp file1.bin file2.bin             # 바이너리 파일 비교
cmp -l file1.bin file2.bin          # 모든 차이점 출력
cmp -s file1.bin file2.bin && echo "동일" || echo "다름"  # 조건 분기
```

---

### 98. `xxd` — 16진수 덤프

파일 내용을 16진수로 덤프하거나 변환합니다.

```bash
xxd file.bin                        # 16진수 덤프
xxd -l 64 file.bin                  # 처음 64바이트만
xxd -s 0x10 file.bin                # 오프셋 0x10부터
xxd -b file.bin                     # 이진수로 덤프
xxd file.bin | xxd -r > copy.bin    # 덤프 후 역변환
echo "48656c6c6f" | xxd -r -p       # 16진수를 ASCII로 변환
```

---

### 99. `screen` / `tmux` — 터미널 멀티플렉서

하나의 터미널에서 여러 세션을 관리합니다.

```bash
# tmux (권장)
tmux                            # 새 세션 시작
tmux new -s mysession           # 이름 있는 세션 시작
tmux ls                         # 세션 목록
tmux attach -t mysession        # 세션 재접속
tmux kill-session -t mysession  # 세션 종료

# tmux 내부 단축키 (Ctrl+B 접두사)
# Ctrl+B, c  : 새 창 생성
# Ctrl+B, %  : 수직 분할
# Ctrl+B, "  : 수평 분할
# Ctrl+B, d  : 세션 분리 (detach)
# Ctrl+B, [  : 스크롤 모드

# screen
screen                          # 새 세션 시작
screen -S name                  # 이름 있는 세션
screen -r                       # 재접속
# Ctrl+A, d  : detach
```

---

### 100. `man` — 매뉴얼 페이지

명령어의 공식 매뉴얼(도움말)을 표시합니다.

```bash
man ls                          # ls 명령 매뉴얼
man 5 crontab                   # 섹션 5의 crontab 매뉴얼
man -k keyword                  # 키워드로 관련 매뉴얼 검색
man -f command                  # 명령 관련 섹션 번호 확인

# man 내부 단축키
# Space   : 다음 페이지
# b       : 이전 페이지
# /text   : 검색
# n / N   : 다음/이전 검색 결과
# q       : 종료

# 도움말 대안
command --help                  # 간단한 도움말
info command                    # GNU info 페이지
```

| 섹션 | 내용 |
|------|------|
| 1 | 일반 명령 |
| 2 | 시스템 콜 |
| 3 | C 라이브러리 함수 |
| 5 | 설정 파일 형식 |
| 8 | 관리자 명령 |

---

## 📌 자주 쓰는 조합 예제

### 로그 분석

```bash
# 에러 로그 실시간 모니터링 + 필터링
tail -f /var/log/syslog | grep -i "error\|warn"

# 로그에서 IP 주소 추출 및 접속 횟수 집계
grep -oE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" access.log | sort | uniq -c | sort -rn | head
```

### 디스크 용량 정리

```bash
# 큰 파일 찾기 (상위 10개)
du -ah / 2>/dev/null | sort -rh | head -10

# 30일 이상 된 로그 파일 삭제
find /var/log -name "*.log" -mtime +30 -exec rm {} \;
```

### 프로세스 디버깅

```bash
# 특정 포트 사용 프로세스 찾기
lsof -i :8080 | awk 'NR>1 {print $2}' | xargs kill -9

# CPU 많이 쓰는 프로세스 top 5
ps aux --sort=-%cpu | head -6
```

### 원격 파일 작업

```bash
# 원격 서버 로그 실시간 모니터링
ssh user@host "tail -f /var/log/app.log"

# 여러 서버에 파일 동시 배포
for host in server1 server2 server3; do
    scp deploy.sh user@$host:/tmp/ && ssh user@$host "bash /tmp/deploy.sh"
done
```

---

## 🔗 참고 자료

- [GNU Coreutils 공식 문서](https://www.gnu.org/software/coreutils/manual/)
- [The Linux Command Line (무료 전자책)](https://linuxcommand.org/tlcl.php)
- [Linux man-pages 프로젝트](https://www.kernel.org/doc/man-pages/)
- [Bash Reference Manual](https://www.gnu.org/software/bash/manual/)
- [Explain Shell](https://explainshell.com/) — 복잡한 명령어 분석 도구

---

<div align="center">

**⭐ 이 레포지토리가 도움이 되었다면 Star를 눌러주세요!**

Made with ❤️ for Linux Developers

</div>
