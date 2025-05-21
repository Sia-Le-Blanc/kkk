"""
OpenGL을 사용한 오버레이 윈도우
"""

import cv2
import numpy as np
import time
import os
import threading
import sys
from overlay.base import BaseOverlay

# OpenGL과 Pygame 모듈을 전역에서 임포트 시도
try:
    import pygame
    from pygame.locals import DOUBLEBUF, OPENGL, NOFRAME
    import OpenGL
    from OpenGL.GL import *
    from OpenGL.GLU import *
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False
    print("⚠️ PyOpenGL 또는 pygame 모듈이 설치되지 않았습니다.")
    print("pip install pygame PyOpenGL PyOpenGL_accelerate 명령으로 설치하세요.")

class OpenGLOverlayWindow(BaseOverlay):
    """OpenGL을 사용한 오버레이 윈도우"""
    
    def __init__(self, config=None):
        # OpenGL 및 PyGame 모듈 가용성 확인
        self.has_opengl = HAS_OPENGL
        
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
            
        # OpenGL 초기화 확인
        self.initialized = self.has_opengl
        self.pygame_initialized = False
        self.window = None
        self.font = None
        
        if self.initialized:
            print(f"✅ OpenGL 기반 오버레이 창 초기화 완료 (해상도: {self.width}x{self.height})")
        else:
            print("❌ OpenGL 또는 Pygame 모듈이 없어 초기화가 불가능합니다.")
    
    def _init_pygame_and_opengl(self):
        """Pygame 및 OpenGL 초기화"""
        if not self.has_opengl:
            return False
            
        try:
            # Pygame 초기화
            pygame.init()
            
            # 디스플레이 모드 설정
            flags = DOUBLEBUF | OPENGL | NOFRAME  # 테두리 없는 창
            self.window = pygame.display.set_mode((self.width, self.height), flags)
            pygame.display.set_caption("Mosaic Overlay")
            
            # 윈도우 설정 (클릭 통과 등)
            try:
                import win32gui
                import win32con
                
                # 윈도우 핸들 가져오기
                HWND = pygame.display.get_wm_info()['window']
                
                # 윈도우 스타일 설정
                ex_style = win32gui.GetWindowLong(HWND, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(HWND, win32con.GWL_EXSTYLE, 
                                    ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
                
                # 윈도우 투명도 설정
                win32gui.SetLayeredWindowAttributes(HWND, 0, 255, win32con.LWA_COLORKEY)
                
                # 항상 최상위 설정
                win32gui.SetWindowPos(HWND, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            except Exception as e:
                print(f"⚠️ 윈도우 설정 실패: {e}")
            
            # OpenGL 설정
            glViewport(0, 0, self.width, self.height)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(0, self.width, self.height, 0, -1, 1)  # 좌상단이 (0,0)
            glMatrixMode(GL_MODELVIEW)
            
            # 알파 블렌딩 활성화
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # 폰트 초기화
            self.font = pygame.font.SysFont('Arial', 18)
            
            # 초기화 성공
            self.pygame_initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Pygame/OpenGL 초기화 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _render_thread_func(self):
        """렌더링 스레드 함수"""
        if not self.has_opengl:
            print("❌ OpenGL 모듈이 없어 렌더링이 불가능합니다.")
            return
            
        # Pygame 및 OpenGL 초기화
        if not self.pygame_initialized:
            if not self._init_pygame_and_opengl():
                print("❌ Pygame/OpenGL 초기화 실패로 렌더링 스레드 종료")
                return
        
        # 렌더링 루프
        last_render_time = time.time()
        frame_count = 0
        
        try:
            while not self.stop_event.is_set():
                # 이벤트 처리
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.stop_event.set()
                
                # 화면 지우기 (투명 배경)
                glClearColor(0.0, 0.0, 0.0, 0.0)
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                
                # 모자이크 영역 그리기
                if self.mosaic_regions:
                    for x, y, w, h, label, _ in self.mosaic_regions:
                        # 화면 경계 확인
                        if x < 0 or y < 0 or x > self.width or y > self.height:
                            continue
                            
                        # 빨간색 반투명 사각형 그리기
                        glColor4f(1.0, 0.0, 0.0, 0.7)  # R, G, B, Alpha
                        glBegin(GL_QUADS)
                        glVertex2f(x, y)           # 좌상단
                        glVertex2f(x + w, y)       # 우상단
                        glVertex2f(x + w, y + h)   # 우하단
                        glVertex2f(x, y + h)       # 좌하단
                        glEnd()
                        
                        # 테두리 그리기 (흰색)
                        glColor4f(1.0, 1.0, 1.0, 1.0)  # 흰색
                        glLineWidth(2.0)
                        glBegin(GL_LINE_LOOP)
                        glVertex2f(x, y)
                        glVertex2f(x + w, y)
                        glVertex2f(x + w, y + h)
                        glVertex2f(x, y + h)
                        glEnd()
                        
                        # 텍스트 렌더링
                        self._render_text(label, x + 5, y + 5)
                
                # 화면 갱신
                pygame.display.flip()
                
                # FPS 계산 및 출력
                frame_count += 1
                elapsed = time.time() - last_render_time
                if frame_count >= 30:  # 30프레임마다 FPS 출력
                    fps = frame_count / elapsed
                    print(f"⚡️ OpenGL 오버레이 FPS: {fps:.1f}")
                    last_render_time = time.time()
                    frame_count = 0
                
                # 프레임 레이트 제한
                time.sleep(self.render_interval)
            
        except Exception as e:
            print(f"❌ OpenGL 렌더링 스레드 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 종료 처리
            try:
                pygame.quit()
                self.pygame_initialized = False
            except:
                pass
            print("🛑 OpenGL 렌더링 스레드 종료됨")
    
    def _render_text(self, text, x, y):
        """텍스트 렌더링 함수"""
        try:
            # 텍스트 렌더링
            text_surface = self.font.render(text, True, (255, 255, 255))
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            text_width, text_height = text_surface.get_size()
            
            # 텍스처 생성 및 바인딩
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            
            # 텍스처 설정
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_width, text_height, 
                        0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            
            # 텍스처 렌더링
            glEnable(GL_TEXTURE_2D)
            glColor4f(1.0, 1.0, 1.0, 1.0)  # 흰색
            
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(x, y)
            glTexCoord2f(1, 0); glVertex2f(x + text_width, y)
            glTexCoord2f(1, 1); glVertex2f(x + text_width, y + text_height)
            glTexCoord2f(0, 1); glVertex2f(x, y + text_height)
            glEnd()
            
            glDisable(GL_TEXTURE_2D)
            
            # 텍스처 삭제
            glDeleteTextures(1, [texture_id])
        except Exception as e:
            print(f"⚠️ 텍스트 렌더링 오류: {e}")
    
    def show(self):
        """오버레이 창 표시"""
        if not self.initialized:
            print("❌ OpenGL이 초기화되지 않아 표시할 수 없습니다.")
            return
            
        print("✅ OpenGL 오버레이 창 표시")
        self.shown = True
        
        # 렌더링 스레드 시작
        if self.render_thread is None or not self.render_thread.is_alive():
            self.stop_event.clear()
            self.render_thread = threading.Thread(target=self._render_thread_func, daemon=True)
            self.render_thread.start()
            print("✅ OpenGL 렌더링 스레드 시작됨")
    
    def hide(self):
        """오버레이 창 숨기기"""
        print("🛑 OpenGL 오버레이 창 숨기기")
        self.shown = False
        
        # 렌더링 스레드 중지
        if self.render_thread and self.render_thread.is_alive():
            self.stop_event.set()
            self.render_thread.join(timeout=1.0)
            self.render_thread = None
            print("🛑 OpenGL 렌더링 스레드 중지됨")
    
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
    
    def get_window_handle(self):
        """윈도우 핸들 반환"""
        try:
            if self.has_opengl and self.shown and self.pygame_initialized:
                return pygame.display.get_wm_info()['window']
        except:
            pass
        return 0
    
    def __del__(self):
        """소멸자"""
        self.hide()
        # Pygame 종료
        if self.pygame_initialized:
            try:
                pygame.quit()
            except:
                pass