import abc
import os
import time
import cv2
import numpy as np
import threading

class BaseOverlay(abc.ABC):
    """모든 오버레이 클래스가 구현해야 하는 기본 인터페이스"""
    
    def __init__(self, config=None):
        """초기화 함수"""
        # 기본 설정값
        self.config = config or {}
        self.width = self.config.get('width', 1920)
        self.height = self.config.get('height', 1080)
        self.fps = self.config.get('fps', 30)
        self.render_interval = 1.0 / self.fps
        
        # 상태 변수
        self.shown = False
        self.mosaic_regions = []
        self.original_image = None
        self.frame_count = 0
        
        # 스레드 관련
        self.render_thread = None
        self.stop_event = threading.Event()
        
        # 디버깅 관련
        self.debug_dir = self.config.get('debug_dir', 'debug_overlay')
        os.makedirs(self.debug_dir, exist_ok=True)
        
        self._init_resources()
        
    def _init_resources(self):
        """초기 리소스 할당 및 설정"""
        # 각 구현체에서 오버라이드
        pass
    
    @abc.abstractmethod
    def show(self):
        """오버레이 창 표시"""
        pass
    
    @abc.abstractmethod
    def hide(self):
        """오버레이 창 숨기기"""
        pass
    
    @abc.abstractmethod
    def update_regions(self, original_image, mosaic_regions):
        """모자이크 영역 업데이트"""
        pass
    
    @abc.abstractmethod
    def get_window_handle(self):
        """윈도우 핸들 반환"""
        pass
    
    def _save_debug_image(self):
        """디버깅용 이미지 저장"""
        try:
            if self.original_image is None or not self.mosaic_regions:
                return
                
            # 표시된 모자이크 영역 시각화
            debug_image = self.original_image.copy()
            for x, y, w, h, label, _ in self.mosaic_regions:
                # 원본 이미지에 박스 표시
                cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 0, 255), 2)  # 빨간색
                cv2.putText(debug_image, label, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # 이미지 저장
            debug_path = f"{self.debug_dir}/overlay_{self.__class__.__name__}_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(debug_path, debug_image)
            print(f"📸 디버깅용 오버레이 이미지 저장: {debug_path}")
        except Exception as e:
            print(f"⚠️ 디버깅 이미지 저장 실패: {e}")
    
    def __del__(self):
        """소멸자: 리소스 정리"""
        self.hide()