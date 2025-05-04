"""
화면 내에서 직접 모자이크 처리하는 고성능 프로세서
"""

import cv2
import numpy as np
import threading
import time
import os
import mss
import mss.tools
from overlay.base import BaseOverlay

class InlineScreenProcessor(BaseOverlay):
    """화면 내에서 직접 모자이크 처리하는 고성능 프로세서"""
    
    def __init__(self, config=None):
        # 화면 정보 초기화
        self.sct = mss.mss()
        monitor = self.sct.monitors[0]
        self.width = monitor["width"]
        self.height = monitor["height"]
        
        # 기본 클래스 초기화
        super().__init__(config)
        
        # 처리 스레드
        self.processor_thread = None
        self.fps_times = []
        
        print(f"✅ 인라인 스크린 프로세서 초기화 (해상도: {self.width}x{self.height})")
    
    def show(self):
        """프로세서 활성화 및 스레드 시작"""
        print("✅ 인라인 스크린 프로세서 시작")
        self.shown = True
        
        # 스레드 시작
        if self.processor_thread is None or not self.processor_thread.is_alive():
            self.stop_event.clear()
            self.processor_thread = threading.Thread(target=self._process_loop, daemon=True)
            self.processor_thread.start()
            print("✅ 프로세서 스레드 시작됨")
    
    def hide(self):
        """프로세서 비활성화 및 스레드 중지"""
        print("🛑 인라인 스크린 프로세서 중지")
        self.shown = False
        
        # 스레드 중지
        if self.processor_thread and self.processor_thread.is_alive():
            self.stop_event.set()
            self.processor_thread.join(timeout=1.0)
            self.processor_thread = None
            print("🛑 프로세서 스레드 중지됨")
    
    def update_regions(self, original_image, mosaic_regions):
        """모자이크 영역 업데이트"""
        try:
            if original_image is None:
                return
                
            self.frame_count += 1
            
            # 모자이크 정보 저장
            self.original_image = original_image
            self.mosaic_regions = mosaic_regions
            
            # 모자이크 영역 조회 및 로그 출력
            save_interval = self.config.get('debug_save_interval', 100)
            if len(mosaic_regions) > 0:
                if self.frame_count % save_interval == 0:
                    print(f"✅ 모자이크 영역 {len(mosaic_regions)}개 처리 중 (프레임 #{self.frame_count})")
                    self._save_debug_image()
            elif self.frame_count % (save_interval * 3) == 0:
                print(f"📢 모자이크 영역 없음 (프레임 #{self.frame_count})")
        
        except Exception as e:
            print(f"❌ 오버레이 업데이트 실패: {e}")
    
    def _process_loop(self):
        """모자이크 처리 메인 루프"""
        try:
            while not self.stop_event.is_set() and self.shown:
                start_time = time.time()
                
                if not self.mosaic_regions:
                    time.sleep(0.016)  # 약 60fps
                    continue
                
                # 영역별로 화면 캡처 및 모자이크 적용
                for x, y, w, h, label, mosaic_img in self.mosaic_regions:
                    try:
                        if x < 0 or y < 0 or x + w > self.width or y + h > self.height:
                            continue
                        if w <= 0 or h <= 0 or mosaic_img is None:
                            continue
                        
                        # 해당 영역만 캡처
                        monitor = {"top": y, "left": x, "width": w, "height": h}
                        
                        # 모자이크 직접 적용 (실제 구현 필요)
                        # 실제로는 여기서 Win32 API를 사용하여 해당 위치에
                        # 모자이크 이미지를 직접 그리는 방식으로 구현해야 함
                        # 예: windll.user32.BitBlt 등 사용
                        
                    except Exception as e:
                        print(f"❌ 영역 처리 오류: {e} @ ({x},{y},{w},{h})")
                
                # FPS 계산 및 제한
                elapsed = time.time() - start_time
                self.fps_times.append(elapsed)
                if len(self.fps_times) > 60:
                    self.fps_times.pop(0)
                
                # FPS 출력 (60프레임마다)
                if self.frame_count % 60 == 0:
                    avg_time = sum(self.fps_times) / len(self.fps_times)
                    fps = 1.0 / avg_time if avg_time > 0 else 0
                    print(f"⚡️ 처리 FPS: {fps:.1f}, 평균 처리 시간: {avg_time*1000:.1f}ms")
                
                # 프레임 레이트 제한
                sleep_time = max(0, 0.016 - elapsed)  # 약 60fps
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except Exception as e:
            print(f"❌ 처리 루프 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def get_window_handle(self):
        """윈도우 핸들 반환"""
        return 0  # 실제 창이 없으므로 0 반환
    
    def __del__(self):
        """소멸자: 자원 정리"""
        self.hide()
        if hasattr(self, 'sct'):
            try:
                self.sct.close()
            except:
                pass