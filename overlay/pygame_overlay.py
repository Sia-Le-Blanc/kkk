"""
Pygame을 사용한 전체 화면 오버레이 모듈
"""

import pygame
import cv2
import numpy as np
import time
import os
import threading
import sys
from overlay.base import BaseOverlay

class PygameOverlayWindow(BaseOverlay):
    """Pygame을 사용한 전체 화면 오버레이 윈도우"""
    
    def __init__(self, config=None):
        # 화면 크기
        try:
            import win32api
            self.width = win32api.GetSystemMetrics(0)  # SM_CXSCREEN
            self.height = win32api.GetSystemMetrics(1)  # SM_CYSCREEN
        except:
            self.width = 1366  # 기본값
            self.height = 768  # 기본값
        
        # 기본 클래스 초기화
        super().__init__(config)
        
        # Pygame 관련 변수
        self.pygame_initialized = False
        self.screen = None
        self.font = None
        
        # 렌더링 스레드
        self.render_thread = None
        
        print(f"✅ Pygame 기반 오버레이 창 초기화 완료 (해상도: {self.width}x{self.height})")
    
    def _init_pygame(self):
        """Pygame 초기화"""
        try:
            pygame.init()
            
            # 화면 설정
            self.screen = pygame.display.set_mode(
                (self.width, self.height), 
                pygame.NOFRAME
            )
            pygame.display.set_caption("Mosaic Overlay")
            
            # 폰트 설정
            self.font = pygame.font.SysFont('Arial', 18)
            
            # 투명 설정 (Windows 환경)
            if sys.platform == "win32":
                try:
                    import win32gui
                    import win32con
                    import win32api
                    
                    # 윈도우 핸들 가져오기
                    hwnd = pygame.display.get_wm_info()['window']
                    
                    # 투명 윈도우 설정
                    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    win32gui.SetWindowLong(
                        hwnd, 
                        win32con.GWL_EXSTYLE, 
                        ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
                    )
                    
                    # 컬러키 설정 (검은색을 투명으로)
                    win32gui.SetLayeredWindowAttributes(
                        hwnd, 
                        win32api.RGB(0, 0, 0), 
                        0, 
                        win32con.LWA_COLORKEY
                    )
                    
                    # 항상 위에 표시
                    win32gui.SetWindowPos(
                        hwnd, 
                        win32con.HWND_TOPMOST, 
                        0, 0, 0, 0, 
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                    )
                    
                except Exception as e:
                    print(f"⚠️ 윈도우 투명 설정 실패: {e}")
            
            self.pygame_initialized = True
            return True
        except Exception as e:
            print(f"❌ Pygame 초기화 실패: {e}")
            return False
    
    def _render_thread_func(self):
        """렌더링 스레드 함수"""
        # Pygame 초기화 확인
        if not self.pygame_initialized and not self._init_pygame():
            print("❌ Pygame 초기화 실패로 렌더링 중단")
            return
        
        # 주요 변수 초기화
        last_render_time = time.time()
        frame_count = 0
        clock = pygame.time.Clock()
        
        # 메인 렌더링 루프
        while not self.stop_event.is_set():
            # 이벤트 처리
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop_event.set()
            
            # 화면이 표시되지 않는 경우 건너뛰기
            if not self.shown:
                time.sleep(0.1)
                continue
            
            # 렌더링 시작
            start_time = time.time()
            
            # 화면 초기화 (검은색 - 투명으로 처리됨)
            self.screen.fill((0, 0, 0))
            
            # 모자이크 영역 그리기
            if self.mosaic_regions:
                for x, y, w, h, label, mosaic in self.mosaic_regions:
                    # 오버레이 사각형 (빨간색 반투명)
                    overlay_surface = pygame.Surface((w, h), pygame.SRCALPHA)
                    overlay_surface.fill((255, 0, 0, 180))  # RGBA: 빨간색 반투명
                    
                    # 테두리 (흰색)
                    pygame.draw.rect(
                        overlay_surface, 
                        (255, 255, 255, 255), 
                        pygame.Rect(0, 0, w, h), 
                        2
                    )
                    
                    # 텍스트 렌더링 (흰색)
                    text_surface = self.font.render(label, True, (255, 255, 255))
                    overlay_surface.blit(text_surface, (5, 5))
                    
                    # 화면에 그리기
                    self.screen.blit(overlay_surface, (x, y))
            
            # 화면 갱신
            pygame.display.flip()
            
            # FPS 계산 및 출력
            frame_count += 1
            elapsed = time.time() - start_time
            if frame_count >= 30:  # 30프레임마다 FPS 출력
                fps = frame_count / (time.time() - last_render_time)
                print(f"⚡️ Pygame 오버레이 FPS: {fps:.1f}, 시간: {elapsed*1000:.1f}ms")
                last_render_time = time.time()
                frame_count = 0
            
            # 프레임 레이트 제한
            clock.tick(self.fps)
    
    def show(self):
        """오버레이 창 표시"""
        print("✅ Pygame 오버레이 창 표시")
        self.shown = True
        
        # 렌더링 스레드 시작
        if self.render_thread is None or not self.render_thread.is_alive():
            self.stop_event.clear()
            self.render_thread = threading.Thread(target=self._render_thread_func, daemon=True)
            self.render_thread.start()
            print("✅ Pygame 렌더링 스레드 시작됨")
    
    def hide(self):
        """오버레이 창 숨기기"""
        print("🛑 Pygame 오버레이 창 숨기기")
        self.shown = False
        
        # 렌더링 스레드 중지
        if self.render_thread and self.render_thread.is_alive():
            self.stop_event.set()
            self.render_thread.join(timeout=1.0)
            self.render_thread = None
            print("🛑 Pygame 렌더링 스레드 중지됨")
    
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
            save_interval = self.config.get('debug_save_interval', 30)
            if len(mosaic_regions) > 0:
                if self.frame_count % save_interval == 0:  # 30프레임마다 로그 출력
                    print(f"✅ 모자이크 영역 {len(mosaic_regions)}개 처리 중 (프레임 #{self.frame_count})")
                    self._save_debug_image()
            elif self.frame_count % (save_interval * 3) == 0:  # 더 긴 간격으로 로그 출력
                print(f"📢 모자이크 영역 없음 (프레임 #{self.frame_count})")
        
        except Exception as e:
            print(f"❌ 오버레이 업데이트 실패: {e}")
    
    def update_frame(self, regions):
        """main.py와 호환성을 위한 update_regions 래퍼 메서드"""
        if not regions:
            return
        
        # 테스트 환경에서는 regions가 이미 프레임일 수 있음
        if isinstance(regions, np.ndarray) and len(regions.shape) == 3:
            # regions가 프레임인 경우 - 전체 이미지를 저장
            self.original_image = regions
        else:
            # regions가 검출 결과인 경우 - 모자이크 영역 업데이트
            self.update_regions(self.original_image, regions)
    
    def clear(self):
        """모자이크 영역 초기화"""
        self.mosaic_regions = []
    
    def get_window_handle(self):
        """윈도우 핸들 반환"""
        try:
            if self.pygame_initialized and pygame.display.get_init():
                return pygame.display.get_wm_info()['window']
        except:
            pass
        return 0
    
    def __del__(self):
        """소멸자"""
        self.hide()
        if self.pygame_initialized:
            try:
                pygame.quit()
            except:
                pass