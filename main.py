"""
실시간 화면 모자이크 처리 프로그램 메인 모듈
"""

import os
import sys
import time
import argparse
import threading
from capture.mss_capture import ScreenCapturer
from detection.mosaic_processor import MosaicProcessor
from gui.gui_korean import GUIController
from config import CONFIG

# ✅ pygame 오버레이 사용
from overlay.pygame_overlay import PygameOverlayWindow as Overlay

class MosaicApp:
    """모자이크 애플리케이션 메인 클래스"""
    
    def __init__(self, args):
        """초기화"""
        self.args = args
        
        # 디버그 모드 설정
        if args.debug:
            CONFIG['capture']['debug_mode'] = True
            print("🔍 디버그 모드 활성화")
        
        # ✅ UI 컨트롤러 생성
        self.gui = GUIController(CONFIG.get("mosaic", {}))
        
        # ✅ 화면 캡처 객체 생성
        self.capturer = ScreenCapturer(CONFIG.get("capture", {}))
        
        # ✅ 모자이크 처리기 생성
        self.processor = MosaicProcessor(
            CONFIG.get("models", {}).get("onnx_path", None), 
            CONFIG.get("mosaic", {})
        )
        
        # ✅ pygame 기반 오버레이 초기화
        self.overlay = Overlay(CONFIG.get("overlay", {}))
        
        # 처리 스레드
        self.process_thread = None
        self.stop_event = threading.Event()
        
        # 콜백 연결
        self.gui.start_censoring_signal.connect(self.start_censoring)
        self.gui.stop_censoring_signal.connect(self.stop_censoring)
        
        print("✅ 모자이크 앱 초기화 완료")
    
    def start(self):
        """애플리케이션 시작"""
        # 오버레이 표시
        self.overlay.show()
        
        # GUI 메인 루프 실행
        self.gui.run()
        
        # 종료 시 정리
        self.cleanup()
        
    def start_censoring(self):
        """검열 시작"""
        # 이미 실행 중인 경우
        if self.process_thread and self.process_thread.is_alive():
            print("⚠️ 이미 실행 중입니다")
            return
        
        # 파라미터 업데이트
        self.processor.set_targets(self.gui.get_selected_targets())
        self.processor.set_strength(self.gui.get_strength())
        print(f"✅ 검열 시작: 대상={self.processor.targets}, 강도={self.processor.mosaic_strength}")
        
        # 스레드 시작
        self.stop_event.clear()
        self.process_thread = threading.Thread(
            target=self._process_loop, 
            daemon=True,
            name="Mosaic-Process-Thread"
        )
        self.process_thread.start()
        print("✅ 모자이크 처리 스레드 시작됨")
    
    def _process_loop(self):
        """검열 처리 메인 루프"""
        try:
            print("🔍 모자이크 처리 루프 시작")
            frame_count = 0
            start_time = time.time()
            last_fps_time = start_time
            
            while not self.stop_event.is_set() and self.gui.running:
                # 프레임 캡처
                frame = self.capturer.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                # 디버깅 로그 (100프레임마다)
                if frame_count % 100 == 0:
                    print(f"📊 프레임 #{frame_count}: 크기={frame.shape}")
                
                # 객체 감지 및 모자이크 처리
                result = self.processor.detect_objects(frame)
                
                # 오버레이 업데이트
                self.overlay.update_regions(frame, result)
                
                # 통계 업데이트
                frame_count += 1
                now = time.time()
                if now - last_fps_time >= 1.0:
                    fps = frame_count / (now - last_fps_time)
                    print(f"⚡️ 처리 FPS: {fps:.1f}, 프레임 수: {frame_count}")
                    last_fps_time = now
                    frame_count = 0
                
                # CPU 과부하 방지
                time.sleep(0.01)
            
            print("✅ 처리 루프 정상 종료")
        
        except Exception as e:
            print(f"❌ 처리 루프 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print("🛑 처리 스레드 종료")
        
    def cleanup(self):
        """자원 정리"""
        # 검열 중지
        self.stop_censoring()
        
        # 오버레이 숨기기
        self.overlay.hide()
        
        # 캡처 스레드 중지
        self.capturer.stop_capture_thread()
        
        print("✅ 자원 정리 완료")

    def stop_censoring(self):
        """검열 중지"""
        print("🛑 검열 중지 요청...")
        
        # 스레드 중지
        if self.process_thread and self.process_thread.is_alive():
            self.stop_event.set()
            self.process_thread.join(timeout=1.0)
        
        # 오버레이 클리어
        self.overlay.clear()
        
        print("🛑 검열 중지됨")

def main():
    """메인 함수"""
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description="실시간 화면 모자이크 처리 프로그램")
    parser.add_argument("--debug", action="store_true", help="디버깅 모드")
    args = parser.parse_args()
    
    # 앱 생성 및 실행
    app = MosaicApp(args)
    app.start()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 프로그램 실행 오류: {e}")
        import traceback
        traceback.print_exc()