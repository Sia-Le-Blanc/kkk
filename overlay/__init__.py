"""
오버레이 및 렌더링 모듈 패키지
"""
from .base import BaseOverlay
from .cv2_overlay import CV2OverlayWindow

# Pygame 오버레이 추가
try:
    from .pygame_overlay import PygameOverlayWindow
    __all__ = ['BaseOverlay', 'CV2OverlayWindow', 'PygameOverlayWindow']
except ImportError:
    print("Pygame 모듈이 설치되어 있지 않습니다. 'pip install pygame' 명령으로 설치하세요.")
    __all__ = ['BaseOverlay', 'CV2OverlayWindow']

try:
    from .win32_overlay import Win32OverlayWindow
    __all__.append('Win32OverlayWindow')
except ImportError:
    pass

try:
    from .opengl_overlay import OpenGLOverlayWindow
    __all__.append('OpenGLOverlayWindow')
except ImportError:
    pass

try:
    from .directx_overlay import DirectXOverlayWindow
    __all__.append('DirectXOverlayWindow')
except ImportError:
    pass

try:
    from .inline_processor import InlineScreenProcessor
    __all__.append('InlineScreenProcessor')
except ImportError:
    pass