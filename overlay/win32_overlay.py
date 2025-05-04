"""
Win32 API를 사용하는 모자이크 오버레이 윈도우
"""

import cv2
import numpy as np
import time
import os
import threading
import ctypes
from ctypes import windll, wintypes, byref, c_int
from overlay.base import BaseOverlay

# Windows 상수 정의
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x8
WS_EX_TOOLWINDOW = 0x80
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
HWND_TOPMOST = -1
SWP_NOSIZE = 0x1
SWP_NOMOVE = 0x2
SWP_NOACTIVATE = 0x10
ULW_ALPHA = 0x2
AC_SRC_OVER = 0x0
AC_SRC_ALPHA = 0x1

class Win32OverlayWindow(BaseOverlay):
    """Win32 API를 사용하는 모자이크 오버레이 윈도우"""
    
    def __init__(self, config=None):
        # 화면 정보 초기화
        self.width = windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
        self.height = windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
        
        # 윈도우 핸들
        self.hwnd = None
        self.classname = b"MosaicOverlayClass"
        self.title = b"Mosaic Overlay"
        
        # 기본 클래스 초기화
        super().__init__(config)
        
        # 윈도우 클래스 등록 및 생성
        self._register_window_class()
        self._create_window()
        
        print(f"✅ Win32 API 기반 오버레이 창 초기화 완료 (해상도: {self.width}x{self.height})")
    
    def _register_window_class(self):
        """윈도우 클래스 등록"""
        # WNDPROC 타입 정의 (윈도우 프로시저 함수 포인터 타입)
        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_long, 
            ctypes.c_void_p, 
            ctypes.c_uint, 
            ctypes.c_void_p, 
            ctypes.c_void_p
        )
        
        # 윈도우 프로시저 콜백 저장 (참조를 유지하기 위해)
        self._wndproc_callback = WNDPROC(self._window_proc)
        
        # WNDCLASSEX 구조체 정의 및 설정
        class WNDCLASSEX(ctypes.Structure):
            _fields_ = [
                ('cbSize', ctypes.c_uint),
                ('style', ctypes.c_uint),
                ('lpfnWndProc', WNDPROC),
                ('cbClsExtra', c_int),
                ('cbWndExtra', c_int),
                ('hInstance', ctypes.c_void_p),
                ('hIcon', ctypes.c_void_p),
                ('hCursor', ctypes.c_void_p),
                ('hbrBackground', ctypes.c_void_p),
                ('lpszMenuName', ctypes.c_char_p),
                ('lpszClassName', ctypes.c_char_p),
                ('hIconSm', ctypes.c_void_p)
            ]
        
        wc = WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(WNDCLASSEX)
        wc.style = 0
        wc.lpfnWndProc = self._wndproc_callback
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = windll.kernel32.GetModuleHandleA(None)
        wc.hIcon = 0
        wc.hCursor = windll.user32.LoadCursorA(0, 32512)  # IDC_ARROW
        wc.hbrBackground = 0
        wc.lpszMenuName = None
        wc.lpszClassName = self.classname
        wc.hIconSm = 0
        
        # 클래스 등록
        try:
            if not windll.user32.RegisterClassExA(byref(wc)):
                error = ctypes.GetLastError()
                print(f"❌ 윈도우 클래스 등록 실패. 오류 코드: {error}")
        except Exception as e:
            print(f"❌ 윈도우 클래스 등록 오류: {e}")
            
        self.wc = wc
    
    def _window_proc(self, hwnd, msg, wparam, lparam):
        """윈도우 프로시저"""
        try:
            if msg == 0x10:  # WM_CLOSE
                windll.user32.DestroyWindow(hwnd)
                return 0
            elif msg == 0x2:  # WM_DESTROY
                windll.user32.PostQuitMessage(0)
                return 0
            
            # DefWindowProc 호출
            return windll.user32.DefWindowProcA(
                ctypes.c_void_p(hwnd), 
                ctypes.c_uint(msg), 
                ctypes.c_void_p(wparam), 
                ctypes.c_void_p(lparam)
            )
        except Exception as e:
            print(f"❌ 윈도우 프로시저 오류: {e}")
            return 0
    
    def _create_window(self):
        """투명 오버레이 윈도우 생성"""
        try:
            # 윈도우 생성
            self.hwnd = windll.user32.CreateWindowExA(
                WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
                self.classname,
                self.title,
                WS_POPUP,  # WS_VISIBLE 제거하고 나중에 ShowWindow로 표시
                0, 0, self.width, self.height,
                None, None, self.wc.hInstance, None
            )
            
            if not self.hwnd:
                error = ctypes.GetLastError()
                print(f"❌ 윈도우 생성 실패. 오류 코드: {error}")
                return
            
            # 투명도 설정 - 완전 투명으로 시작
            windll.user32.SetLayeredWindowAttributes(self.hwnd, 0, 0, ULW_ALPHA)
            
            # 항상 최상위로 설정
            windll.user32.SetWindowPos(
                self.hwnd, HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            )
            
            print(f"✅ 오버레이 윈도우 생성 완료: 핸들={self.hwnd}")
        except Exception as e:
            print(f"❌ 윈도우 생성 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def _render_thread_func(self):
        """렌더링 스레드 함수"""
        last_render_time = time.time()
        frame_count = 0
        
        try:
            while not self.stop_event.is_set():
                try:
                    if self.shown:
                        start_time = time.time()
                        
                        # 렌더링 수행
                        if self.mosaic_regions:
                            self._render_overlay()
                        else:
                            # 모자이크 영역이 없으면 완전 투명하게
                            self._clear_overlay()
                        
                        # FPS 계산 및 출력
                        frame_count += 1
                        elapsed = time.time() - start_time
                        if frame_count % 30 == 0:  # 30프레임마다 FPS 출력
                            fps = 30 / (time.time() - last_render_time)
                            print(f"⚡️ 오버레이 렌더링 FPS: {fps:.1f}, 시간: {elapsed*1000:.1f}ms")
                            last_render_time = time.time()
                            frame_count = 0
                        
                        # 프레임 타이밍 조절
                        sleep_time = max(0.001, self.render_interval - elapsed)
                        time.sleep(sleep_time)
                    else:
                        time.sleep(0.1)  # 비활성화 상태에서는 CPU 사용 줄이기
                except Exception as e:
                    print(f"❌ 렌더링 루프 오류: {e}")
                    time.sleep(0.1)
        except Exception as e:
            print(f"❌ 렌더링 스레드 오류: {e}")
        finally:
            print("🛑 렌더링 스레드 종료됨")
    
    def _render_overlay(self):
        """모자이크 오버레이 렌더링"""
        try:
            # BLENDFUNCTION 구조체 정의
            class BLENDFUNCTION(ctypes.Structure):
                _fields_ = [
                    ('BlendOp', ctypes.c_byte),
                    ('BlendFlags', ctypes.c_byte),
                    ('SourceConstantAlpha', ctypes.c_byte),
                    ('AlphaFormat', ctypes.c_byte)
                ]
            
            # POINT 구조체 정의 
            class POINT(ctypes.Structure):
                _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]
            
            # SIZE 구조체 정의
            class SIZE(ctypes.Structure):
                _fields_ = [('cx', ctypes.c_long), ('cy', ctypes.c_long)]
            
            # BITMAPINFOHEADER 구조체 정의
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', ctypes.c_uint32),
                    ('biWidth', ctypes.c_int32),
                    ('biHeight', ctypes.c_int32),
                    ('biPlanes', ctypes.c_uint16),
                    ('biBitCount', ctypes.c_uint16),
                    ('biCompression', ctypes.c_uint32),
                    ('biSizeImage', ctypes.c_uint32),
                    ('biXPelsPerMeter', ctypes.c_int32),
                    ('biYPelsPerMeter', ctypes.c_int32),
                    ('biClrUsed', ctypes.c_uint32),
                    ('biClrImportant', ctypes.c_uint32)
                ]
            
            # 디바이스 컨텍스트 가져오기
            hdc = windll.user32.GetDC(self.hwnd)
            if not hdc:
                print("❌ 디바이스 컨텍스트 가져오기 실패")
                return
            
            # 메모리 DC 생성
            mem_dc = windll.gdi32.CreateCompatibleDC(hdc)
            if not mem_dc:
                windll.user32.ReleaseDC(self.hwnd, hdc)
                print("❌ 메모리 DC 생성 실패")
                return
            
            # 비트맵 생성
            bitmap = windll.gdi32.CreateCompatibleBitmap(hdc, self.width, self.height)
            if not bitmap:
                windll.gdi32.DeleteDC(mem_dc)
                windll.user32.ReleaseDC(self.hwnd, hdc)
                print("❌ 비트맵 생성 실패")
                return
            
            old_bitmap = windll.gdi32.SelectObject(mem_dc, bitmap)
            
            # 투명한 배경으로 초기화
            windll.gdi32.PatBlt(mem_dc, 0, 0, self.width, self.height, 0x00000042)  # BLACKNESS
            
            # 모자이크 영역 그리기
            for x, y, w, h, label, mosaic_img in self.mosaic_regions:
                if mosaic_img is None:
                    continue
                    
                try:
                    # OpenCV 이미지를 Windows 비트맵으로 변환
                    height, width = mosaic_img.shape[:2]
                    
                    # BGR to BGRA 변환
                    bgra = cv2.cvtColor(mosaic_img, cv2.COLOR_BGR2BGRA)
                    bgra[:, :, 3] = 255  # 알파 채널 설정 (완전 불투명)
                    
                    # BITMAPINFO 생성
                    bmi = BITMAPINFOHEADER()
                    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                    bmi.biWidth = width
                    bmi.biHeight = -height  # 상하 반전
                    bmi.biPlanes = 1
                    bmi.biBitCount = 32
                    bmi.biCompression = 0  # BI_RGB
                    
                    # 이미지 그리기를 위한 데이터 포인터 설정
                    data_ptr = bgra.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
                    
                    # 이미지 그리기
                    windll.gdi32.SetDIBitsToDevice(
                        mem_dc, x, y, width, height,
                        0, 0, 0, height,
                        data_ptr,
                        byref(bmi),
                        0  # DIB_RGB_COLORS
                    )
                except Exception as e:
                    print(f"❌ 모자이크 그리기 오류: {e}")
            
            # 블렌드 함수 설정
            blend_function = BLENDFUNCTION()
            blend_function.BlendOp = AC_SRC_OVER
            blend_function.BlendFlags = 0
            blend_function.SourceConstantAlpha = 255  # 완전 불투명 (값이 낮을수록 더 투명)
            blend_function.AlphaFormat = AC_SRC_ALPHA  # 소스 이미지의 알파 채널 사용
            
            # 투명 윈도우 업데이트
            point_zero = POINT(0, 0)
            size = SIZE(self.width, self.height)
            
            # UpdateLayeredWindow 호출
            result = windll.user32.UpdateLayeredWindow(
                self.hwnd,
                hdc,
                None,  # 위치 유지 (NULL)
                byref(size),
                mem_dc,
                byref(point_zero),
                0,  # RGB 색상 (0)
                byref(blend_function),
                ULW_ALPHA
            )
            
            if not result:
                error = ctypes.GetLastError()
                print(f"❌ UpdateLayeredWindow 실패. 오류 코드: {error}")
            
            # 리소스 정리
            windll.gdi32.SelectObject(mem_dc, old_bitmap)
            windll.gdi32.DeleteObject(bitmap)
            windll.gdi32.DeleteDC(mem_dc)
            windll.user32.ReleaseDC(self.hwnd, hdc)
            
        except Exception as e:
            print(f"❌ 렌더링 오류: {e}")
            import traceback
            traceback.print_exc()