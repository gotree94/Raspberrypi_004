"""
AI Drug Discovery Automation Platform
=====================================

실제 AI/ML 기술을 활용한 신약 개발 전 과정 자동화 플랫폼

Modules:
    alphafold   : AlphaFold2/3 단백질 구조 예측 통합
    molecular   : RDKit 기반 분자 처리, 지문, 기술자 계산
    screening   : 가상 스크리닝 (유사도 검색, Pharmacophore, 라이브러리 관리)
    admet       : ML 기반 ADMET (흡수·분포·대사·배설·독성) 예측
    generation  : VAE/GA/RL 기반 신규 분자 생성 및 최적화
    docking     : AutoDock Vina 분자 도킹 자동화
    pipeline    : DAG 워크플로우 오케스트레이션 및 상태 관리
    api         : FastAPI REST API 및 WebSocket
    visualization: 분자 구조, 차트, 대시보드 시각화
"""

__version__ = "1.0.0"
__author__ = "AI Drug Discovery Lab"
