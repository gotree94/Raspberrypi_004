# 실내 스캔 촬영 가이드

## 촬영 준비물
- 스마트폰 (카메라 기능)
- 충전기 (배터리 많이 소모됨)
- 삼각대 (있으면 좋음, 없어도 OK)

## 촬영 방법

### 1. 전체 둘러보기 촬영 (10~15장)
- 방의 4방향에서 벽면 사진 촬영
- 바닥과 천장도 포함

### 2. 상세 촬영 (20~30장)
- 벽면, 가구, 기기 등 세부 사진
- 겹치는 부분을 반드시 포함 (30% 이상 오버랩)

### 3. 촬영 팁
- [ ] 조명이 균일한 시간에 촬영 (형광등 ON)
- [ ] 그림자가 적은 각도에서 촬영
- [ ] 플래시 사용 금지 (반사 방지)
- [ ] 수직/수평 유지
- [ ] 같은 높이에서 촬영 ( eye level )
- [ ] 이동할 때마다 30cm 간격

## 사진 naming 규칙
```
scan_001.jpg, scan_002.jpg, ...
```

## 후처리 순서
1. 사진 준비 → `C:\Users\Administrator\Desktop\3d_simulator_project\photos\`
2. 전처리 실행 → `python scripts/photo_preprocess.py`
3. Meshroom 2025.1로 3D 모델 생성 (Template: Photogrammetry)
4. Blender에서 메시 최적화
5. Unreal Engine으로 임포트
