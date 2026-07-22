# 실내 스캔 → 언리얼 엔진 시뮬레이터 구축 상세 가이드

## 전체 흐름 요약

```
촬영 → 전처리 → 3D 복원 → 메시 편집 → UE5 임포트 → 시뮬레이터 구성
```

---

## Step 1: 사진 촬영 및 전처리 (완료)

```bash
cd C:\simulator_project\scripts
python check_photos.py          # 사진 상태 확인
python photo_preprocess.py      # 리사이즈 + 메타데이터 추출
```

결과물: `C:\simulator_project\photos\processed\` 폴더에 `scan_001.jpg` ~ `scan_XX.jpg`

---

## Step 2: 3D 모델 생성

### 방법 A: Polycam (추천 - 쉬움)

#### 2-1. Polycam에서 처리
1. Polycam 앱 실행
2. 하단 "+" 버튼 → **"Capture"** 또는 **"Import"** 선택
3. **"Import"** 선택 시:
   - `photos/processed/` 폴더의 사진 전체 선택
   - 업로드 시작 (Wi-Fi 환경 권장)
4. 처리 완료 대기 (5~20분, 사진 수에 따라 다름)
5. **"Export"** → 형식 선택:
   - **GLB** (추천, 텍스처 포함)
   - 또는 **OBJ** (범용)

#### 2-2. 파일 저장
- 다운로드한 파일을 `C:\simulator_project\3d_models\` 에 저장
- 파일명: `room_scan.glb` 또는 `room_scan.obj`

#### 2-3. Polycam 웹에서 확인 (선택)
- https://web.polycam.io 접속
- 방금 업로드한 모델 확인 가능
- 웹에서도 회전/확대 하며 품질 확인

---

### 방법 B: Meshroom (정확한 결과)

#### 2-1. Meshroom 설치
- https://alicevision.org/meshroom/download
- GitHub Releases에서 최신 버전 다운로드
- 압축 해제 후 `Meshroom.exe` 실행

#### 2-2. Meshroom 처리 순서
1. **File → New** 클릭
2. 오른쪽 **"Images"** 패널에서:
   - "+" 버튼 클릭
   - `C:\simulator_project\photos\processed\` 폴더 선택
   - 모든 사진 추가
3. 상단 **"Start"** 버튼 클릭
4. 처리 파이프라인 (자동 순서):

```
CameraInit
    ↓
FeatureExtraction
    ↓
FeatureMatching
    ↓
IncrementalSfM
    ↓
DepthMap
    ↓
DepthMapFilter
    ↓
Meshing
    ↓
MeshFiltering
    ↓
Texturing
```

5. 처리 완료 후 (30분~2시간):
   - 왼쪽 **"Graph Editor"** 에서 **Texturing** 노드 우클릭
   - **"Open Folder"** → 결과 파일 위치 확인
   - `texturedMesh.obj` + 텍스처 파일

#### 2-3. 결과물 저장
- `texturedMesh.obj` + `.mtl` + `.png` (텍스처) 파일을:
  - `C:\simulator_project\3d_models\` 에 복사

---

### 방법 C: COLMAP (고급 사용자)

```bash
# COLMAP 설치 (chocolatey 사용 시)
choco install colmap

# 또는 GitHub에서 직접 다운로드
# https://github.com/colmap/colmap/releases
```

#### 처리 순서
```bash
# 1. 특징 추출
colmap feature_extractor \
  --database_path db.db \
  --image_path C:\simulator_project\photos\processed

# 2. 특징 매칭
colmap exhaustive_matcher \
  --database_path db.db

# 3. 희소 모델 복원
mkdir sparse
colmap mapper \
  --database_path db.db \
  --image_path C:\simulator_project\photos\processed \
  --output_path sparse

# 4. 메시 생성
mkdir dense
colmap image_undistorter \
  --image_path C:\simulator_project\photos\processed \
  --input_path sparse/0 \
  --output_path dense

colmap patch_match_stereo \
  --workspace_path dense

colmap stereo_fusion \
  --workspace_path dense \
  --output_path dense/fused.ply

# 5. 메시 구축
colmap poisson_mesher \
  --input_path dense/fused.ply \
  --output_path dense/meshed.ply

# 6. 텍스처 매핑
colmap delaunay_mesher \
  --input_path dense \
  --output_path dense/meshed-delaunay.ply
```

- 최종 결과: `dense/meshed-delaunay.ply`
- PLY → OBJ 변환 필요 (MeshLab 또는 Blender 사용)

---

## Step 3: Blender에서 메시 최적화

### 3-1. Blender 설치 및 실행
- https://www.blender.org/download/ 에서 다운로드
- 설치 후 실행

### 3-2. 3D 모델 임포트
1. **File → Import** 클릭
2. 형식 선택:
   - GLB 파일 → **glTF 2.0 (.glb/.gltf)**
   - OBJ 파일 → **Wavefront (.obj)**
   - PLY 파일 → **Stanford (.ply)**
3. 파일 선택 후 **Import** 클릭

### 3-3. 모델 확인
1. **Numpad 5** → 와이어프레임/솔리드 전환
2. **Numpad 1/3/7** → 정면/측면/상단 뷰
3. **Scroll** → 확대/축소
4. **Shift + Scroll** → 팬
5. **Numpad 0** → 카메라 뷰

### 3-4. 메시 정리

#### 불필요한 요소 제거
1. 모델 선택 (좌클릭)
2. **Tab** → 편집 모드 진입
3. **A** → 전체 선택
4. **M** → Merge 메뉴:
   - **"By Distance"** → 중복 버텍스 제거 (기본 0.001m)
   - 거리 값 조정: 오른쪽 패널 **"Merge Distance"** 슬라이더

#### 메시 단순화 (필요 시)
1. 모델 선택 (Tab → 오브젝트 모드)
2. ** Modifier 탭** (렌더링 아이콘 옆 청록색 톱니바퀴)
3. **"Add Modifier"** → **"Decimate"**
4. **Ratio** 값을 조정 (0.5 = 50% 단순화)
5. **"Apply"** 클릭

#### 법선 수정
1. Tab → 편집 모드
2. **A** → 전체 선택
3. **Alt + N** → **"Recalculate Outside"**

### 3-5. UV Unwrapping
1. Tab → 편집 모드
2. **A** → 전체 선택
3. **U** → **"Smart UV Project"** 선택
4. 기본 설정으로 **OK** (기본 66도 옵셋)

### 3-6. 스케일 조정 (중요!)
- 언리얼 엔진은 **1 유닛 = 1센티미터**
1. 모델 선택 (오브젝트 모드)
2. **N** 패널 열기 → **Item** 탭
3. **Scale** 값 확인
4. 필요 시 **S** 키로 스케일 조정:
   - 실내 기준: 약 3~10m → Blender에서 3~10으로 설정
   - **S**, 숫자 입력, **Enter**

### 3-7. FBX로 내보내기
1. **File → Export → FBX (.fbx)** 클릭
2. 경로: `C:\simulator_project\3d_models\room_scan.fbx`
3. 설정 (오른쪽 패널):

```
Include:
  ☑ Selected Objects (선택한 것만) 또는 전체
  ☑ Apply Modifiers

Transform:
  Forward: -Z Forward
  Up: Y Up

Geometry:
  ☑ Apply Modifiers
  Smoothing: Face

Armature:
  ☐ Add Leaf Bones (체크 해제)

Animation:
  ☐ Baked Animation (체크 해제)
```

4. **"Export FBX"** 클릭

### 3-8. 텍스처도 함께 내보내기
- FBX에 텍스처가 포함되지 않을 수 있음
- 텍스처 PNG 파일을 `C:\simulator_project\3d_models\textures\` 에 별도 저장
- 또는 Blender에서 **File → External Data → Pack All Into .blend** 사용

---

## Step 4: Unreal Engine 5 설정

### 4-1. Unreal Engine 설치
1. https://www.unrealengine.com/download 접속
2. **"Download Launcher"** 클릭
3. Epic Games Launcher 설치 후 실행
4. **"Unreal Engine"** 탭 → **"Library"**
5. **"+" 버튼** → **"Engine Versions"** → **5.3.x** 또는 **5.4.x** 설치
6. 설치 완료 대기 (약 30~60GB)

### 4-2. 프로젝트 생성
1. Epic Games Launcher 실행
2. **"Unreal Engine"** 탭 → **"Launch"** 클릭
3. **"Games"** → **"Blank"** 선택
4. 설정:
   - **Project Type**: Blueprint (추천) 또는 C++
   - **Target Platform**: Desktop
   - **Quality Preset**: Maximum
   - **Starter Content**: 체크 해제
   - **Raytracing**: 체크 (있으면)
5. **Project Location**: `C:\simulator_project\`
6. **Project Name**: `SimulatorProject`
7. **"Create"** 클릭

### 4-3. 3D 모델 임포트

#### 방법 1: 직접 임포트
1. **Content Browser** (하단 패널) 에서 우클릭
2. **"Import to /Game/..."** → **"Import Asset"**
3. `C:\simulator_project\3d_models\room_scan.fbx` 선택
4. **Import Options** 팝업:

```
Mesh:
  ☑ Import Mesh
  ☑ Import Textures
  ☑ Import Materials

Transform:
  Import Rotation: X=0, Y=0, Z=0
  Import Scale: 1.0 (스케일이 틀리면 여기서 조정)

Material:
  ☑ Import as Mesh (추천)
  Material Import: Create New Materials
```

5. **"Import All"** 클릭

#### 방법 2: 드래그 앤 드롭
- 파일 탐색기에서 FBX 파일을 Content Browser로 드래그

### 4-4. 머티리얼 설정
1. Content Browser에서 임포트된 머티리얼 더블클릭
2. **Material Editor** 에서:
   - **Base Color** 노드에 텍스처 연결
   - **Normal** 노드에 노멀맵 연결 (있으면)
   - **Roughness** 조정 (실내: 0.5~0.8)
3. **"Apply"** → **"Save"**

### 4-5. 레벨에 배치
1. Content Browser에서 임포트된 메시를 **Level Viewport** 로 드래그
2. 위치/회전 조정:
   - **W** → 이동
   - **E** → 회전
   - **R** → 스케일
3. **Ctrl + S** → 저장

---

## Step 5: 언리얼 엔진 시뮬레이터 설정

### 5-1. 조명 설정 (Lumen)
1. **Window → Details** 패널 확인
2. **"World Settings"** 탭:
   - **Dynamic Global Illumination Method**: Lumen
   - **Reflection Method**: Lumen
   - **Shadow Map Method**: Virtual Shadow Maps

3. **스카이박스/환경광** 추가:
   - **Content Browser** 우클릭 → **"Lights"** → **"Directional Light"**
   - **Window → Environmental Light Mixer** 열기
   - **"Create Sky Light"** / **"Create Sky Atmosphere"** 클릭

### 5-2. 카메라 설정
1. **Place Actors** 패널 → **"Cinematic"** → **"Camera"** 드래그
2. ** Details** 패널:
   - **Focal Length**: 35~50mm (실내용)
   - **Aspect Ratio**: 16:9
3. **"Pilot"** 모드로 시점 이동 (카메라 선택 → **"Pilot 'CameraActor'"** 클릭)

### 5-3. 시뮬레이션용 설정 (선택)
- **Player Start** 배치 (시작 지점)
- **Collision** 설정 (벽면에 부딪힘)
- **Third Person 템플릿** 사용 시:
  - `ThirdPersonBP` 폴더에서 캐릭터 임포트

### 5-4. 빌드 및 테스트
1. **"Play"** 버튼 클릭 (또는 **Alt + P**)
2. 모드 선택:
   - **"Selected Viewport"** → 에디터 내에서 재생
   - **"Standalone"** → 별도 윈도우에서 재생
3. WASD로 이동, 마우스로 시점 전환 테스트

---

## Step 6: 최적화 및 품질 향상

### 6-1. LOD (Level of Detail) 설정
1. 메시 선택 → **Details** 패널
2. **"LOD Settings"** → **"Number of LODs"**: 3~4
3. 각 LOD별 **Screen Size** 설정:
   - LOD0: 1.0 (가까움)
   - LOD1: 0.5
   - LOD2: 0.25
   - LOD3: 0.125 (멀리)

### 6-2. UV1 설정 (Lightmap)
1. Blender에서 FBX 내보낼 때:
   - **Second UV** 채널 생성 (Lightmap용)
2. 또는 UE5에서:
   - 메시 우클릭 → **"Build"** → **"Lightmap UV"**

### 6-3. 텍스처 압축
1. 텍스처 파일 선택
2. **Details** 패널:
   - **Compression**: Default (DXT1/5)
   - **Max Texture Size**: 2048

---

## 문제 해결

### 문제 1: 모델이 너무 작거나 큼
- Blender에서 스케일 조정 후 재내보내기
- 또는 UE5 Import Options에서 **Import Scale** 조정

### 문제 2: 텍스처가 안 보임
- FBX와 텍스처 파일이 같은 폴더에 있는지 확인
- 머티리얼 에디터에서 텍스처 수동 연결

### 문제 3: 메시에 구멍이 있음
- Blender에서 **"Fill"** 명령 (F 키)으로 구멍 메우기
- 또는 Meshroom에서 **"DepthMap"** 단계 재처리

### 문제 4: 조명이 이상함
- **Lightmap Resolution** 증가 (메시 선택 → Details → Lightmap Resolution)
- **Force No Precomputed Lighting** 체크 해제

### 문제 5: 프레임 저하
- **Console Commands** 사용:
  ```
  r.ScreenPercentage 75
  sg.ResolutionQuality 75
  ```
- LOD 설정 강화
- 텍스처 해상도 축소 (2048 → 1024)

---

## 유용한 단축키 (UE5)

| 키 | 기능 |
|----|------|
| W | 이동 |
| E | 회전 |
| R | 스케일 |
| Alt + P | 재생 |
| Ctrl + S | 저장 |
| Ctrl + Z | 실행 취소 |
| Ctrl + Shift + S | 다른 이름으로 저장 |
| G | 게임 뷰 전환 |
| F | 선택한 오브젝트에 포커스 |
| Ctrl + Space | Content Browser 포커스 |

---

## 최종 체크리스트

- [ ] 사진 20장 이상 촬영
- [ ] 전처리 완료 (`photo_preprocess.py`)
- [ ] 3D 모델 생성 (Polycam/Meshroom)
- [ ] Blender에서 메시 최적화
- [ ] FBX + 텍스처 내보내기
- [ ] UE5 프로젝트 생성
- [ ] FBX 임포트
- [ ] 머티리얼 적용
- [ ] 조명 설정 (Lumen)
- [ ] 카메라 배치
- [ ] Play 테스트
- [ ] LOD 설정
- [ ] 최종 빌드
