"""
실시간 화면 모자이크 처리 프로그램 메인 모듈
"""

import os
import sys
import cv2
import time
import threading
import queue
from threading import Event
import argparse
import numpy as np

# PyQt5 필요 모듈
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QElapsedTimer, QT_VERSION_STR
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
    print("PyQt5 모듈이 설치되어 있지 않습니다. Win32 GUI를 사용합니다.")

# 설정 및 모듈 로드
from config import CONFIG
from gui.gui_korean import GUIController
from capture.mss_capture import ScreenCapturer
from detection.mosaic_processor import MosaicProcessor
from detection.sort import Sort


class ParallelProcessingPipeline:
    """병렬 처리 파이프라인 클래스"""
    
    def __init__(self, capturer, processor, renderer, config=None):
        """
        초기화
        capturer: 화면 캡처 객체
        processor: 모자이크 처리 객체
        renderer: 오버레이 렌더링 객체
        """
        if config is None:
            config = CONFIG.get('pipeline', {})
            
        self.capturer = capturer
        self.processor = processor
        self.renderer = renderer
        
        # 파이프라인 설정
        self.queue_size = config.get('queue_size', 3)
        self.log_interval = config.get('log_interval', 30)
        self.stats_interval = config.get('stats_interval', 100)
        
        # 각 단계 간 큐
        self.capture_to_detect = queue.Queue(maxsize=self.queue_size)
        self.detect_to_render = queue.Queue(maxsize=self.queue_size)
        
        # 스레드
        self.capture_thread = None
        self.detect_thread = None
        self.render_thread = None
        
        # 제어 이벤트
        self.stop_event = threading.Event()
        
        # 성능 측정 변수
        self.frame_count = 0
        self.start_time = None
        self.last_fps_print = 0
        self.processing_times = []
        
        # 큐 동기화 락
        self.queue_lock = threading.Lock()
        
    def start(self):
        """파이프라인 시작"""
        self.stop_event.clear()
        self.frame_count = 0
        self.start_time = time.time()
        self.last_fps_print = self.start_time
        
        # 렌더러에 캡처러 제외 영역 등록
        if hasattr(self.renderer, 'get_window_handle'):
            hwnd = self.renderer.get_window_handle()
            if hwnd:
                self.capturer.set_exclude_hwnd(hwnd)
        
        # 캡처 스레드
        self.capture_thread = threading.Thread(
            target=self._capture_loop, 
            daemon=True,
            name="Capture-Thread"
        )
        
        # 감지 스레드
        self.detect_thread = threading.Thread(
            target=self._detect_loop, 
            daemon=True,
            name="Detect-Thread"
        )
        
        # 렌더링 스레드
        self.render_thread = threading.Thread(
            target=self._render_loop, 
            daemon=True,
            name="Render-Thread"
        )
        
        # 스레드 시작
        print("🚀 병렬 처리 파이프라인 시작")
        self.capture_thread.start()
        self.detect_thread.start()
        self.render_thread.start()
        
    def _capture_loop(self):
        """캡처 루프 - 가장 높은 우선순위"""
        # 스레드 우선순위 높게 설정
        self._set_high_priority()
        print("✅ 캡처 스레드 시작됨")
        
        # 메인 루프
        while not self.stop_event.is_set():
            try:
                # 프레임 캡처
                frame = self.capturer.get_frame()
                
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                # 큐가 가득 차면 이전 프레임 제거하고 새 프레임 넣기
                try:
                    with self.queue_lock:
                        if self.capture_to_detect.full():
                            self.capture_to_detect.get_nowait()
                        self.capture_to_detect.put(frame, block=False)
                except queue.Full:
                    pass  # 무시하고 계속
                
                # 프레임 레이트 제한
                time.sleep(0.01)  # 최대 약 100fps
                
            except Exception as e:
                print(f"❌ 캡처 루프 오류: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
                
    def _detect_loop(self):
        """감지 루프"""
        print("✅ 감지 스레드 시작됨")
        
        # 객체 추적기 초기화
        tracker = Sort(max_age=3, min_hits=1)
        
        while not self.stop_event.is_set():
            try:
                # 캡처 큐에서 프레임 가져오기
                try:
                    frame = self.capture_to_detect.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # 객체 감지 수행
                detect_start = time.time()
                regions = self.processor.detect_objects(frame)
                detect_time = (time.time() - detect_start) * 1000
                
                # 처리 시간 업데이트
                self.processing_times.append(detect_time)
                if len(self.processing_times) > 30:
                    self.processing_times.pop(0)
                
                # 렌더링 큐로 결과 전달
                try:
                    with self.queue_lock:
                        if self.detect_to_render.full():
                            self.detect_to_render.get_nowait()
                        self.detect_to_render.put((frame, regions), block=False)
                except queue.Full:
                    pass
                    
                # 성능 측정 및 로깅
                self.frame_count += 1
                current_time = time.time()
                if current_time - self.last_fps_print >= 1.0:
                    fps = self.frame_count / (current_time - self.start_time)
                    avg_process_time = np.mean(self.processing_times) if self.processing_times else 0
                    print(f"⚡️ FPS: {fps:.1f}, 평균 처리 시간: {avg_process_time:.1f}ms, 프레임: {self.frame_count}")
                    self.last_fps_print = current_time
                    
            except Exception as e:
                print(f"❌ 감지 루프 오류: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
                
    def _render_loop(self):
        """렌더링 루프"""
        print("✅ 렌더링 스레드 시작됨")
        
        while not self.stop_event.is_set():
            try:
                # 감지 큐에서 결과 가져오기
                try:
                    frame, regions = self.detect_to_render.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # 렌더링
                self.renderer.update_regions(frame, regions)
                
                # 모자이크 정보 로깅
                if len(regions) > 0 and self.frame_count % self.stats_interval == 0:
                    print(f"📬 모자이크 영역 {len(regions)}개 처리 중")
                
            except Exception as e:
                print(f"❌ 렌더링 루프 오류: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
                
    def _set_high_priority(self):
        """스레드 우선순위 높이기"""
        try:
            if hasattr(os, 'sched_setaffinity'):
                # Linux
                try:
                    os.sched_setaffinity(0, {0, 1})  # CPU 코어 0, 1에 할당
                except:
                    pass
            else:
                # Windows
                try:
                    import win32api
                    import win32process
                    import win32con
                    win32process.SetThreadPriority(
                        win32api.GetCurrentThread(),
                        win32con.THREAD_PRIORITY_HIGHEST
                    )
                except ImportError:
                    print("⚠️ win32api 모듈을 찾을 수 없습니다. 스레드 우선순위 설정을 건너뜁니다.")
        except Exception as e:
            print(f"⚠️ 스레드 우선순위 설정 실패: {e}")
            
    def stop(self):
        """파이프라인 중지"""
        print("🛑 병렬 처리 파이프라인 중지 중...")
        self.stop_event.set()
        
        # 스레드 종료 대기
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        if self.detect_thread and self.detect_thread.is_alive():
            self.detect_thread.join(timeout=1.0)
        if self.render_thread and self.render_thread.is_alive():
            self.render_thread.join(timeout=1.0)
            
        print("✅ 파이프라인 정상 종료됨")


def check_gpu_availability():
    """GPU 사용 가능 여부와 종류를 확인"""
    gpu_available = False
    gpu_info = "CPU 모드"
    
    # CUDA 가용성 확인
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            gpu_info = f"CUDA GPU: {torch.cuda.get_device_name(0)}"
            print(f"✅ {gpu_info} 감지됨")
            return gpu_available, "cuda", gpu_info
    except:
        pass
    
    # DirectX/GPU 가속 확인 (Windows 환경)
    try:
        import ctypes
        from ctypes import windll
        if hasattr(windll, 'dxgi'):
            gpu_available = True
            gpu_info = "DirectX GPU 가속 가능"
            print(f"✅ {gpu_info} 감지됨")
            return gpu_available, "directx", gpu_info
    except:
        pass
    
    print(f"ℹ️ {gpu_info}로 실행됩니다")
    return gpu_available, "cpu", gpu_info


def create_overlay(overlay_type):
    """지정된 타입의 오버레이 객체 생성"""
    overlay = None
    
    if overlay_type == 'cv2':
        try:
            from overlay.cv2_overlay import CV2OverlayWindow
            overlay = CV2OverlayWindow()
            print("✅ OpenCV 기반 오버레이 사용 중")
        except Exception as e:
            print(f"❌ CV2OverlayWindow 초기화 실패: {e}")
            return None
    
    elif overlay_type == 'win32':
        try:
            from overlay.win32_overlay import Win32OverlayWindow
            overlay = Win32OverlayWindow()
            print("✅ Win32 API 기반 오버레이 사용 중")
        except Exception as e:
            print(f"❌ Win32OverlayWindow 초기화 실패: {e}")
            return None
    
    elif overlay_type == 'opengl':
        try:
            from overlay.opengl_overlay import OpenGLOverlayWindow
            overlay = OpenGLOverlayWindow()
            print("✅ OpenGL 기반 오버레이 사용 중")
        except Exception as e:
            print(f"❌ OpenGLOverlayWindow 초기화 실패: {e}")
            return None
    
    elif overlay_type == 'directx':
        try:
            from overlay.directx_overlay import DirectXOverlayWindow
            overlay = DirectXOverlayWindow()
            print("✅ DirectX 기반 오버레이 사용 중")
        except Exception as e:
            print(f"❌ DirectXOverlayWindow 초기화 실패: {e}")
            return None
    
    elif overlay_type == 'inline':
        try:
            from overlay.inline_processor import InlineScreenProcessor
            overlay = InlineScreenProcessor()
            print("✅ 인라인 스크린 프로세서 사용 중")
        except Exception as e:
            print(f"❌ InlineScreenProcessor 초기화 실패: {e}")
            return None
    
    else:
        print(f"❌ 알 수 없는 오버레이 타입: {overlay_type}")
        return None
    
    return overlay


if __name__ == "__main__":
    try:
        # 명령줄 인자 파싱
        parser = argparse.ArgumentParser(description='실시간 화면 모자이크 처리 프로그램')
        parser.add_argument('--debug', action='store_true', help='디버깅 모드 활성화')
        parser.add_argument('--force-cpu', action='store_true', help='CPU 모드 강제 사용')
        parser.add_argument('--speed', action='store_true', help='속도 우선 모드 (품질 저하)')
        parser.add_argument('--overlay', choices=['cv2', 'win32', 'opengl', 'directx', 'inline'], 
                            default=CONFIG.get('overlay', {}).get('default_type', 'cv2'), 
                            help='오버레이 방식 선택')                      
        args = parser.parse_args()
        
        # 버전 정보 출력
        print(f"🚀 OpenCV 버전: {cv2.__version__}")
        if HAS_PYQT:
            print(f"🚀 Qt 버전: {QT_VERSION_STR}")
        
        # GPU 확인
        try:
            gpu_available, render_mode, gpu_info = check_gpu_availability()
            if args.force_cpu:
                render_mode = "cpu"
                gpu_info = "CPU 모드 (강제 설정)"
                print("ℹ️ CPU 모드로 강제 전환됨")
        except Exception as e:
            print(f"⚠️ GPU 확인 중 오류 발생: {e}")
            print("ℹ️ 기본 CPU 모드로 진행합니다")
            render_mode = "cpu"
            gpu_info = "CPU 모드 (오류 복구)"
        
        # 설정 업데이트
        if args.debug:
            CONFIG['capture']['debug_mode'] = True
        
        if args.speed:
            print("⚡️ 속도 우선 모드 활성화 (품질 저하)")
            CONFIG['capture']['downscale'] = 0.75
        
        # QApplication 생성 (GUI 용도로만 사용)
        if HAS_PYQT:
            app = QApplication(sys.argv)
        
        # GUI 컨트롤러 생성
        window = GUIController(CONFIG.get('mosaic'))
        
        # 오버레이 방식 선택
        overlay = create_overlay(args.overlay)
        if overlay is None:
            # 기본 오버레이로 폴백
            print("⚠️ 기본 OpenCV 오버레이로 대체합니다")
            overlay = create_overlay('cv2')
            if overlay is None:
                print("❌ 오버레이 생성 실패, 프로그램을 종료합니다")
                sys.exit(1)
        
        # UI에 현재 모드 표시
        window.set_render_mode_info(f"{gpu_info} | {args.overlay} 오버레이")
        
        # 컴포넌트 초기화
        capturer = ScreenCapturer(CONFIG.get('capture'))
        processor = MosaicProcessor(config=CONFIG.get('mosaic'))
        
        # 병렬 파이프라인 설정
        pipeline = ParallelProcessingPipeline(capturer, processor, overlay, CONFIG.get('pipeline'))
        
        def start():
            """시작 함수"""
            # 파라미터 업데이트
            processor.set_targets(window.get_selected_targets())
            processor.set_strength(window.get_strength())
            print(f"🔄 모자이크 파라미터 업데이트: 대상={processor.targets}, 강도={processor.mosaic_strength}")
            
            # 오버레이 표시
            overlay.show()
            
            # 파이프라인 시작
            pipeline.start()

        def stop():
            """중지 함수"""
            # 오버레이 숨기기
            overlay.hide()
            
            # 파이프라인 중지
            pipeline.stop()

        # 시그널 연결
        window.start_censoring_signal.connect(start)
        window.stop_censoring_signal.connect(stop)

        # GUI 표시
        window.show()
        
        # 메시지 루프 실행
        if HAS_PYQT:
            sys.exit(app.exec_())
        else:
            window.run()

    except Exception as e:
        print(f"❌ 프로그램 시작 오류: {e}")
        import traceback
        traceback.print_exc()