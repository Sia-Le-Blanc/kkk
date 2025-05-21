"""
모자이크 시스템의 설정 값들을 관리하는 모듈
"""

CONFIG = {
    'capture': {
        'downscale': 1.0,       # 캡처 화면 크기 조절 (1.0 = 원본 크기)
        'max_fps': 60,          # 최대 캡처 FPS
        'debug_mode': False,    # 디버그 모드 활성화 여부
        'debug_save_interval': 300  # 디버그 이미지 저장 간격 (프레임 수)
    },
    'overlay': {
        'default_type': 'pygame',   # 기본 오버레이 타입 (pygame, cv2, win32, opengl, directx)
        'fps': 30,               # 오버레이 렌더링 FPS
        'debug_save_interval': 100  # 디버그 이미지 저장 간격 (프레임 수)
    },
    'pipeline': {
        'queue_size': 3,         # 프레임 큐 크기
        'log_interval': 30,      # 로그 출력 간격 (프레임 수)
        'stats_interval': 100    # 통계 출력 간격 (프레임 수)
    },
    'mosaic': {
        'default_strength': 15,  # 기본 모자이크 강도
        'default_targets': ["얼굴", "가슴", "보지", "팬티"],  # 기본 타겟
        'conf_threshold': 0.5    # 객체 감지 신뢰도 임계값
    },
    'models': {
        'onnx_path': 'resources/best.onnx',  # ONNX 모델 경로
        'input_size': (640, 640),  # 모델 입력 크기
        'class_names': [  # 클래스 이름 목록
            "얼굴", "눈", "손", "가슴", "보지", "팬티",
            "겨드랑이", "자지", "몸 전체", "교미", "신발",
            "가슴_옷", "보지_옷", "여성", "남성"
        ]
    },
    'paths': {
        'debug_dir': 'debug',  # 디버그 이미지 저장 디렉토리
        'resources_dir': 'resources'  # 리소스 디렉토리
    }
}