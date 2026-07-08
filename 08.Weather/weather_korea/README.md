# 한국 지도를 그리고

* 서울특별시 및 인천, 대전, 광주, 부산, 대구, 부산 위치의
* 온도, 습도, 체감온도 표시하는  flask 프로젝트


## 1.   프로젝트 구조

```
weather_korea/
├── app.py               ← Flask 백엔드
├── requirements.txt
└── templates/
    └── index.html       ← 한국 지도 + 날씨 UI
```
  
2. 실행 방법 (라즈베리파이)

```
# 패키지 설치
pip3 install flask requests

# 실행
cd weather_korea
python3 app.py

```
3. 실행

* 브라우저에서 http://localhost:5000 또는 http://라즈베리파이IP:5000 접속