"""
한국어 GUI 컨트롤러 모듈
Win32 API를 사용하는 심플한 GUI
"""

import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32api
import numpy as np
from config import CONFIG
import threading

# 트랙바(슬라이더) 스타일 상수 정의
TBS_HORZ = 0x0000
TBS_AUTOTICKS = 0x0001
TBM_SETRANGE = 0x0406
TBM_SETPOS = 0x0405
TBM_GETPOS = 0x0400
BM_SETCHECK = 0x00F1
BM_GETCHECK = 0x00F0
BS_AUTOCHECKBOX = 0x0003
BS_GROUPBOX = 0x0007
BS_PUSHBUTTON = 0x0000

class MainWindow:
    def __init__(self, config=None):
        if config is None:
            config = CONFIG.get('mosaic', {})
        
        self.hwnd = None
        self.strength = config.get('default_strength', 25)
        self.targets = config.get('default_targets', ["얼굴", "가슴", "보지", "팬티"])
        self.checkboxes = {}
        self.running = False
        self.render_mode_info = "기본 모드"

        self.wc = self._register_window_class()
        self._create_window()
        self._create_controls()

        self.start_callback = None
        self.stop_callback = None

    def _register_window_class(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._window_proc
        wc.lpszClassName = "MosaicControlWindow"
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.hbrBackground = win32gui.GetStockObject(win32con.WHITE_BRUSH)
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        win32gui.RegisterClass(wc)
        return wc

    def _create_window(self):
        self.hwnd = win32gui.CreateWindow(
            self.wc.lpszClassName,
            "실시간 화면 검열 시스템",
            win32con.WS_OVERLAPPEDWINDOW,
            win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
            400, 600,
            0, 0, self.wc.hInstance, None
        )

    def _create_controls(self):
        self.strength_label = win32gui.CreateWindow(
            "STATIC", f"모자이크 강도: {self.strength}",
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            20, 20, 150, 20,
            self.hwnd, 0, None, None
        )
        self.strength_slider = win32gui.CreateWindow(
            "msctls_trackbar32", "",
            win32con.WS_CHILD | win32con.WS_VISIBLE | TBS_HORZ | TBS_AUTOTICKS,
            20, 50, 350, 30,
            self.hwnd, 1001, None, None
        )
        win32gui.SendMessage(self.strength_slider, TBM_SETRANGE, 1, (50 << 16) | 5)
        win32gui.SendMessage(self.strength_slider, TBM_SETPOS, 1, self.strength)

        self.render_mode_label = win32gui.CreateWindow(
            "STATIC", self.render_mode_info,
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            20, 85, 350, 20,
            self.hwnd, 0, None, None
        )

        self.group_box = win32gui.CreateWindow(
            "BUTTON", "검열 대상",
            win32con.WS_CHILD | win32con.WS_VISIBLE | BS_GROUPBOX,
            20, 115, 350, 300,
            self.hwnd, 0, None, None
        )

        options = [
            "얼굴", "눈", "손", "가슴", "보지", "팬티",
            "겨드랑이", "자지", "몸 전체", "교미", "신발",
            "가슴_옷", "보지_옷", "여성"
        ]

        for i, option in enumerate(options):
            checkbox = win32gui.CreateWindow(
                "BUTTON", option,
                win32con.WS_CHILD | win32con.WS_VISIBLE | BS_AUTOCHECKBOX,
                40 + (i % 2) * 160, 145 + (i // 2) * 25, 150, 20,
                self.hwnd, 2000 + i, None, None
            )
            if option in self.targets:
                win32gui.SendMessage(checkbox, BM_SETCHECK, 1, 0)
            self.checkboxes[option] = checkbox

        self.start_button = win32gui.CreateWindow(
            "BUTTON", "검열 시작",
            win32con.WS_CHILD | win32con.WS_VISIBLE | BS_PUSHBUTTON,
            70, 480, 100, 30,
            self.hwnd, 3001, None, None
        )

        self.stop_button = win32gui.CreateWindow(
            "BUTTON", "검열 중지",
            win32con.WS_CHILD | win32con.WS_VISIBLE | BS_PUSHBUTTON,
            230, 480, 100, 30,
            self.hwnd, 3002, None, None
        )

    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_COMMAND:
            control_id = win32api.LOWORD(wparam)
            if control_id == 3001:
                self._on_start_clicked()
            elif control_id == 3002:
                self._on_stop_clicked()
            elif 2000 <= control_id < 2100:
                self._on_checkbox_clicked(control_id - 2000)
        elif msg == win32con.WM_HSCROLL:
            if lparam == self.strength_slider:
                self.strength = win32gui.SendMessage(self.strength_slider, TBM_GETPOS, 0, 0)
                win32gui.SetWindowText(self.strength_label, f"모자이크 강도: {self.strength}")
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _on_start_clicked(self):
        print("🖱️ 검열 시작 버튼 클릭됨")
        self.running = True
        self.targets = self.get_selected_targets()
        print(f"🎯 선택된 타겟: {self.targets}")
        if self.start_callback:
            self.start_callback()
            print("✅ 검열 시작 콜백 실행됨")
        else:
            print("⚠️ 검열 시작 콜백이 설정되지 않았습니다")

    def _on_stop_clicked(self):
        self.running = False
        if self.stop_callback:
            self.stop_callback()

    def _on_checkbox_clicked(self, index):
        pass

    def get_selected_targets(self):
        selected = []
        for label, checkbox in self.checkboxes.items():
            if win32gui.SendMessage(checkbox, BM_GETCHECK, 0, 0):
                selected.append(label)
        if not selected and self.checkboxes:
            first_key = next(iter(self.checkboxes))
            selected.append(first_key)
            win32gui.SendMessage(self.checkboxes[first_key], BM_SETCHECK, 1, 0)
        return selected

    def get_strength(self):
        return self.strength

    def set_start_callback(self, callback):
        self.start_callback = callback

    def set_stop_callback(self, callback):
        self.stop_callback = callback

    def set_render_mode_info(self, info_text):
        self.render_mode_info = info_text
        if hasattr(self, 'render_mode_label'):
            win32gui.SetWindowText(self.render_mode_label, info_text)

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)

    def run(self):
        """단순화된 메시지 루프"""
        try:
            import time
            
            # 창 표시
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.UpdateWindow(self.hwnd)
            
            # 메시지 펌프 대신 단순 루프 사용
            print("✅ 간단한 메시지 루프 시작")
            
            # 임시 이벤트로 전환 (GUI가 계속 실행되도록)
            while win32gui.IsWindow(self.hwnd):
                # 단순 딜레이로 CPU 사용 줄이기
                time.sleep(0.1)
                
                # 기본적인 윈도우 메시지 처리
                try:
                    msg = wintypes.MSG()
                    while win32gui.PeekMessage(msg, 0, 0, 0, 1):
                        win32gui.TranslateMessage(msg)
                        win32gui.DispatchMessage(msg)
                except:
                    pass  # 예외 무시하고 계속 진행
                    
        except Exception as e:
            print(f"❌ 메시지 루프 오류: {e}")
        
        print("🛑 메시지 루프 종료")

class Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for callback in self.callbacks:
            callback()

class GUIController(MainWindow):
    def __init__(self, config=None):
        super().__init__(config)
        self.start_censoring_signal = Signal()
        self.stop_censoring_signal = Signal()
        self.set_start_callback(self.start_censoring_signal.emit)
        self.set_stop_callback(self.stop_censoring_signal.emit)
        self.stop_event = threading.Event()