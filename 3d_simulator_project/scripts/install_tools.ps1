# 필수 도구 설치 스크립트
# 실행: powershell -ExecutionPolicy Bypass -File install_tools.ps1

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  실내 시뮬레이터 도구 설치" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Python 패키지 설치
Write-Host "[1/2] Python 패키지 설치 중..." -ForegroundColor Yellow
pip install Pillow open3d trimesh numpy 2>$null
if ($?) {
    Write-Host "  OK: Python 패키지 설치 완료" -ForegroundColor Green
} else {
    Write-Host "  python: 일부 패키지 설치 실패 (Pillow는 필수)" -ForegroundColor Red
}

Write-Host ""
Write-Host "[2/2] 수동 설치가 필요한 프로그램:" -ForegroundColor Yellow
Write-Host "  1. Blender: https://www.blender.org/download/" -ForegroundColor White
Write-Host "  2. Unreal Engine: https://www.unrealengine.com/download" -ForegroundColor White
Write-Host "  3. Meshroom: https://meshroom.org/index.php/download/" -ForegroundColor White
Write-Host "  4. Polycam: 앱스토어에서 설치" -ForegroundColor White
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  설치 완료!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
pause
