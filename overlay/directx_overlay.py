"""
DirectX 기반 모자이크 오버레이 윈도우 (구현 진행 중)
"""

import cv2
import numpy as np
import threading
import time
import os
from overlay.base import BaseOverlay

class DirectXOverlayWindow(BaseOverlay):
    """DirectX 기반 모자이크 오버레이 윈도우"""
    
    def __init__(self, config=None):
        # 기본 클래스 초기화
        super().__init__(config)
        
        print("✅ DirectX 기반 오버레이 초기화")
        print("⚠️ 경고: DirectX 구현은 현재 진행 중입니다")
        
        # 초기화 플래그 추가
        self.initialized = False
    
    def show(self):
        """오버레이 창 표시"""
        print("✅ DirectX 오버레이 표시")
        self.shown = True
    
    def hide(self):
        """오버레이 창 숨기기"""
        print("🛑 DirectX 오버레이 숨기기")
        self.shown = False
    
    def update_regions(self, original_image, mosaic_regions):
        """모자이크 영역 업데이트"""
        self.original_image = original_image
        self.mosaic_regions = mosaic_regions
        self.frame_count += 1
        
        save_interval = self.config.get('debug_save_interval', 100)
        if len(mosaic_regions) > 0 and self.frame_count % save_interval == 0:
            print(f"✅ DirectX: 모자이크 영역 {len(mosaic_regions)}개 처리 중 (프레임 #{self.frame_count})")
            self._save_debug_image()
    
    def get_window_handle(self):
        """윈도우 핸들 반환"""
        return 0  # 임시