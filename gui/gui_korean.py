"""
Tkinter 기반 한국어 GUI 컨트롤러 모듈 (간단한 스크롤)
"""

import tkinter as tk
from tkinter import ttk
import threading
from config import CONFIG

class ScrollableFrame(tk.Frame):
    """스크롤 가능한 프레임 클래스"""
    
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Canvas와 Scrollbar 생성
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        # 스크롤 영역 설정
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Canvas에 프레임 추가
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Canvas 크기 조정
        def configure_canvas(event):
            self.canvas.itemconfig(self.canvas_frame, width=event.width)
        
        self.canvas.bind('<Configure>', configure_canvas)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 레이아웃
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 마우스 휠 바인딩 (간단한 방법)
        self.bind_mousewheel()
    
    def bind_mousewheel(self):
        """마우스 휠 바인딩"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _on_mousewheel_linux(event):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
        
        # 바인딩 함수
        def bind_to_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)  # Windows
            widget.bind("<Button-4>", _on_mousewheel_linux)  # Linux
            widget.bind("<Button-5>", _on_mousewheel_linux)  # Linux
            
            # 모든 자식 위젯에도 바인딩
            for child in widget.winfo_children():
                bind_to_mousewheel(child)
        
        # Canvas와 스크롤 가능한 프레임에 바인딩
        bind_to_mousewheel(self.canvas)
        bind_to_mousewheel(self.scrollable_frame)
        
        # 상위 윈도우에도 바인딩
        def bind_to_parent():
            parent = self.winfo_toplevel()
            if parent:
                bind_to_mousewheel(parent)
        
        # 약간의 지연 후 바인딩
        self.after(100, bind_to_parent)

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
    """메인 윈도우 클래스 (간단한 스크롤)"""
    
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
        self.root.resizable(True, True)
        self.root.minsize(350, 400)
        
        # UI 구성
        self._create_widgets()
        
    def _create_widgets(self):
        """UI 위젯 생성"""
        
        # 드래그 가능한 제목 바
        title_frame = tk.Frame(self.root, bg="lightblue", relief="raised", bd=2, cursor="hand2")
        title_frame.pack(fill=tk.X, padx=2, pady=2)
        
        title_label = tk.Label(
            title_frame, 
            text="🛡️ 화면 검열 시스템 (제목바 드래그로 이동)", 
            font=("Arial", 10, "bold"), 
            bg="lightblue",
            pady=8
        )
        title_label.pack()
        
        # 드래그 기능
        def start_drag(event):
            title_frame.start_x = event.x_root
            title_frame.start_y = event.y_root
        
        def do_drag(event):
            x = event.x_root - title_frame.start_x + self.root.winfo_x()
            y = event.y_root - title_frame.start_y + self.root.winfo_y()
            self.root.geometry(f"+{x}+{y}")
        
        title_frame.bind("<Button-1>", start_drag)
        title_frame.bind("<B1-Motion>", do_drag)
        title_label.bind("<Button-1>", start_drag)
        title_label.bind("<B1-Motion>", do_drag)
        
        # 스크롤 안내
        info_label = tk.Label(
            self.root,
            text="📜 마우스 휠로 스크롤 또는 우측 스크롤바 드래그",
            font=("Arial", 9),
            bg="lightyellow",
            fg="blue",
            pady=3
        )
        info_label.pack(fill=tk.X, padx=2)
        
        # 스크롤 가능한 메인 영역
        self.scrollable_container = ScrollableFrame(self.root)
        self.scrollable_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 실제 내용을 스크롤 가능한 프레임에 추가
        self.create_content(self.scrollable_container.scrollable_frame)
        
    def create_content(self, parent):
        """실제 내용 생성 (기존 구조 유지)"""
        
        # 메인 프레임
        main_frame = ttk.Frame(parent, padding="20")
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
        
        # 추가 설정 프레임
        settings_frame = ttk.LabelFrame(main_frame, text="추가 설정", padding="10")
        settings_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 신뢰도 설정
        confidence_label = ttk.Label(settings_frame, text="감지 신뢰도: 0.1")
        confidence_label.pack(anchor=tk.W, pady=(0, 5))
        
        confidence_slider = ttk.Scale(
            settings_frame,
            from_=0.1,
            to=0.9,
            orient=tk.HORIZONTAL,
            value=0.1,
            length=350
        )
        confidence_slider.pack(fill=tk.X, pady=(0, 10))
        
        def on_confidence_change(value):
            confidence_label.config(text=f"감지 신뢰도: {float(value):.2f}")
        
        confidence_slider.config(command=on_confidence_change)
        
        # 버튼 프레임 (중요!)
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, pady=20)
        
        # 버튼 강조
        button_bg = tk.Frame(button_frame, bg="lightgray", relief="raised", bd=3)
        button_bg.pack(fill=tk.X, pady=10)
        
        inner_button_frame = tk.Frame(button_bg, bg="lightgray")
        inner_button_frame.pack(pady=15)
        
        # 검열 시작/중지 버튼
        start_button = tk.Button(
            inner_button_frame, 
            text="🚀 검열 시작", 
            command=self._on_start_clicked,
            bg="green",
            fg="white",
            font=("Arial", 14, "bold"),
            width=12,
            height=2
        )
        start_button.pack(side=tk.LEFT, padx=10)
        
        stop_button = tk.Button(
            inner_button_frame, 
            text="🛑 검열 중지", 
            command=self._on_stop_clicked,
            bg="red",
            fg="white", 
            font=("Arial", 14, "bold"),
            width=12,
            height=2
        )
        stop_button.pack(side=tk.RIGHT, padx=10)
        
        # 상태 표시 프레임
        status_frame = ttk.LabelFrame(main_frame, text="상태", padding="15")
        status_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.status_label = ttk.Label(status_frame, text="⭕ 대기 중", font=("Arial", 12))
        self.status_label.pack()
        
        # 스크롤 테스트용 추가 공간
        test_frame = ttk.LabelFrame(main_frame, text="스크롤 테스트", padding="15")
        test_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 스크롤 확인용 텍스트들
        test_texts = [
            "✅ 여기까지 스크롤이 되었다면 성공!",
            "✅ 위로 스크롤해서 버튼들을 사용하세요",
            "✅ 마우스 휠로 쉽게 스크롤 가능",
            "✅ 우측 스크롤바도 드래그 가능",
            "✅ 제목바 드래그로 창 이동 가능"
        ]
        
        for text in test_texts:
            test_label = ttk.Label(test_frame, text=text)
            test_label.pack(anchor=tk.W, pady=3)
        
        # 마지막 여백
        spacer = tk.Frame(main_frame, height=50)
        spacer.pack()
        
    def _on_start_clicked(self):
        """검열 시작 버튼 클릭 핸들러"""
        print("🖱️ 검열 시작 버튼 클릭됨")
        self.running = True
        self.targets = self.get_selected_targets()
        print(f"🎯 선택된 타겟: {self.targets}")
        
        if hasattr(self, 'status_label'):
            self.status_label.config(text="✅ 검열 중", foreground="green")
        
        if self.start_callback:
            print("✅ 검열 시작 콜백 실행")
            self.start_callback()
        else:
            print("⚠️ 검열 시작 콜백이 설정되지 않았습니다")
    
    def _on_stop_clicked(self):
        """검열 중지 버튼 클릭 핸들러"""
        print("🖱️ 검열 중지 버튼 클릭됨")
        self.running = False
        
        if hasattr(self, 'status_label'):
            self.status_label.config(text="⭕ 대기 중", foreground="red")
        
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
        pass
    
    def run(self):
        """메인 루프 실행"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"❌ Tkinter 메인 루프 오류: {e}")
            import traceback
            traceback.print_exc()

class GUIController(MainWindow):
    """GUI 컨트롤러 클래스"""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        self.start_censoring_signal = Signal()
        self.stop_censoring_signal = Signal()
        self.set_start_callback(self.start_censoring_signal.emit)
        self.set_stop_callback(self.stop_censoring_signal.emit)
        
        self.stop_event = threading.Event()
        
        self.root.attributes('-topmost', True)
        
        print("✅ Tkinter GUI 컨트롤러 초기화 완료 (간단한 스크롤)")