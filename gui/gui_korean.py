"""
Tkinter 기반 한국어 GUI 컨트롤러 모듈
"""

import tkinter as tk
from tkinter import ttk
import threading
from config import CONFIG

class Signal:
    """신호 클래스 (콜백 관리)"""
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for callback in self.callbacks:
            callback()

class MainWindow:
    """메인 윈도우 클래스"""
    
    def __init__(self, config=None):
        if config is None:
            config = CONFIG.get('mosaic', {})
        
        # 설정 및 상태 변수
        self.strength = config.get('default_strength', 25)
        self.targets = config.get('default_targets', ["얼굴", "가슴", "보지", "팬티"])
        self.checkboxes = {}
        self.running = False
        self.render_mode_info = "기본 모드"

        # 콜백 함수
        self.start_callback = None
        self.stop_callback = None
        
        # Tkinter 루트 윈도우 생성
        self.root = tk.Tk()
        self.root.title("실시간 화면 검열 시스템")
        self.root.geometry("400x600")
        self.root.resizable(False, False)
        
        # UI 구성
        self._create_widgets()
        
    def _create_widgets(self):
        """UI 위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 모자이크 강도 라벨 및 슬라이더
        strength_label = ttk.Label(main_frame, text=f"모자이크 강도: {self.strength}")
        strength_label.pack(anchor=tk.W, pady=(0, 5))
        
        strength_slider = ttk.Scale(
            main_frame, 
            from_=5, 
            to=50, 
            orient=tk.HORIZONTAL, 
            value=self.strength,
            length=350
        )
        strength_slider.pack(fill=tk.X, pady=(0, 20))
        
        # 슬라이더 값 변경 시 콜백
        def on_strength_change(value):
            self.strength = int(float(value))
            strength_label.config(text=f"모자이크 강도: {self.strength}")
        
        strength_slider.config(command=on_strength_change)
        
        # 렌더 모드 라벨
        render_mode_label = ttk.Label(main_frame, text=self.render_mode_info)
        render_mode_label.pack(anchor=tk.W, pady=(0, 20))
        self.render_mode_label = render_mode_label
        
        # 검열 대상 프레임
        targets_frame = ttk.LabelFrame(main_frame, text="검열 대상", padding="10")
        targets_frame.pack(fill=tk.BOTH, expand=True)
        
        # 대상 옵션 체크박스
        options = [
            "얼굴", "눈", "손", "가슴", "보지", "팬티",
            "겨드랑이", "자지", "몸 전체", "교미", "신발",
            "가슴_옷", "보지_옷", "여성"
        ]
        
        # 그리드 형태로 체크박스 배열
        for i, option in enumerate(options):
            row, col = divmod(i, 2)
            
            # 체크박스 변수
            var = tk.BooleanVar(value=option in self.targets)
            self.checkboxes[option] = var
            
            # 체크박스 생성
            checkbox = ttk.Checkbutton(targets_frame, text=option, variable=var)
            checkbox.grid(row=row, column=col, sticky=tk.W, padx=10, pady=5)
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, pady=20)
        
        # 검열 시작/중지 버튼
        start_button = ttk.Button(button_frame, text="검열 시작", command=self._on_start_clicked)
        start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        stop_button = ttk.Button(button_frame, text="검열 중지", command=self._on_stop_clicked)
        stop_button.pack(side=tk.RIGHT)
    
    def _on_start_clicked(self):
        """검열 시작 버튼 클릭 핸들러"""
        print("🖱️ 검열 시작 버튼 클릭됨")
        self.running = True
        self.targets = self.get_selected_targets()
        print(f"🎯 선택된 타겟: {self.targets}")
        
        if self.start_callback:
            print("✅ 검열 시작 콜백 실행")
            self.start_callback()
        else:
            print("⚠️ 검열 시작 콜백이 설정되지 않았습니다")
    
    def _on_stop_clicked(self):
        """검열 중지 버튼 클릭 핸들러"""
        print("🖱️ 검열 중지 버튼 클릭됨")
        self.running = False
        
        if self.stop_callback:
            print("✅ 검열 중지 콜백 실행")
            self.stop_callback()
        else:
            print("⚠️ 검열 중지 콜백이 설정되지 않았습니다")
    
    def get_selected_targets(self):
        """선택된 타겟 목록 반환"""
        selected = []
        for label, var in self.checkboxes.items():
            if var.get():
                selected.append(label)
        
        # 아무것도 선택되지 않았으면 기본값 하나 선택
        if not selected and self.checkboxes:
            first_key = next(iter(self.checkboxes))
            self.checkboxes[first_key].set(True)
            selected.append(first_key)
        
        return selected
    
    def get_strength(self):
        """모자이크 강도 반환"""
        return self.strength
    
    def set_start_callback(self, callback):
        """시작 콜백 설정"""
        self.start_callback = callback
    
    def set_stop_callback(self, callback):
        """중지 콜백 설정"""
        self.stop_callback = callback
    
    def set_render_mode_info(self, info_text):
        """렌더 모드 정보 설정"""
        self.render_mode_info = info_text
        if hasattr(self, 'render_mode_label'):
            self.render_mode_label.config(text=info_text)
    
    def show(self):
        """윈도우 표시"""
        # 윈도우가 이미 표시됨
        pass
    
    def run(self):
        """메인 루프 실행"""
        try:
            # Tkinter 메인 루프
            self.root.mainloop()
        except Exception as e:
            print(f"❌ Tkinter 메인 루프 오류: {e}")
            import traceback
            traceback.print_exc()

class GUIController(MainWindow):
    """GUI 컨트롤러 클래스"""
    
    def __init__(self, config=None):
        # MainWindow 초기화
        super().__init__(config)
        
        # 시그널 생성 및 콜백 연결
        self.start_censoring_signal = Signal()
        self.stop_censoring_signal = Signal()
        self.set_start_callback(self.start_censoring_signal.emit)
        self.set_stop_callback(self.stop_censoring_signal.emit)
        
        # 스레드 제어용 이벤트
        self.stop_event = threading.Event()
        
        # 항상 최상위 설정 (다른 창 위에 표시)
        self.root.attributes('-topmost', True)
        
        print("✅ Tkinter GUI 컨트롤러 초기화 완료")