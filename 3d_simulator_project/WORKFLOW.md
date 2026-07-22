# 실내 시뮬레이터 구축 워크플로우

## 전체 흐름

```
[1일차] 촬영 → [2일차] 3D 복원 → [3일차] 메시 편집 → [4일차] UE5 적용
```

## 1단계: 촬영 (내일)
1. 스마트폰으로 실내 촬영 (20~30장)
2. `C:\simulator_project\photos\` 에 저장

## 2단계: 사진 전처리
```bash
cd C:\simulator_project\scripts
python photo_preprocess.py
```

## 3단계: 3D 모델 생성 (방법 선택)

### 방법A: Polycam (쉬움)
1. Polycam 앱에서 "Capture" → 사진 업로드
2. 처리 후 .OBJ/.GLB 다운로드
3. `C:\simulator_project\3d_models\` 에 저장

### 방법B: Meshroom (정확함)
1. Meshroom 실행
2. CameraInit → FeatureExtraction → ... → Texturing 순서로 처리
3. .OBJ 출력

## 4단계: Blender 최적화
1. .OBJ 파일 Blender에서 열기
2. 메시 정리 (불필요한 면 제거)
3. UV unwrapping
4. .FBX 로 내보내기

## 5단계: Unreal Engine 적용
1. UE5 프로젝트 생성
2. .FBX 임포트
3. 머티리얼/텍스처 적용
4. 조명 설정 (Lumen)

## 파일 구조
```
C:\simulator_project\
├── photos/           # 원본 사진
│   └── processed/    # 전처리된 사진
├── 3d_models/        # 생성된 3D 모델
├── scripts/          # 유틸리티 스크립트
└── unreal_project/   # UE5 프로젝트
```
