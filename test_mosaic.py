"""
오버레이가 제대로 작동하는지 테스트하는 스크립트
실제 감지 없이 강제로 모자이크를 적용해봄
"""

import cv2
import numpy as np
import time
import threading
from capture.mss_capture import ScreenCapturer
from overlay.pygame_overlay import PygameOverlayWindow
from config import CONFIG

class TestMosaicApp:
    """테스트 모자이크 애플리케이션"""
    
    def __init__(self):
        print("🧪 테스트 모자이크 앱 초기화...")
        
        # 컴포넌트 생성
        self.capturer = ScreenCapturer(CONFIG.get("capture", {}))
        self.overlay = PygameOverlayWindow(CONFIG.get("overlay", {}))
        
        # 테스트 설정
        self.running = False
        self.process_thread = None
        
        print("✅ 테스트 모자이크 앱 초기화 완료")
    
    def apply_test_mosaic(self, frame, pattern_type="center"):
        """테스트용 모자이크 패턴 적용"""
        h, w = frame.shape[:2]
        
        if pattern_type == "center":
            # 화면 중앙에 큰 모자이크
            size_w = w // 4
            size_h = h // 4
            x1 = w // 2 - size_w // 2
            y1 = h // 2 - size_h // 2
            x2 = x1 + size_w
            y2 = y1 + size_h
            
            # 모자이크 적용
            roi = frame[y1:y2, x1:x2]
            mosaic_size = 20
            small_roi = cv2.resize(roi, (max(size_w // mosaic_size, 1), max(size_h // mosaic_size, 1)))
            mosaic_roi = cv2.resize(small_roi, (size_w, size_h), interpolation=cv2.INTER_NEAREST)
            frame[y1:y2, x1:x2] = mosaic_roi
            
            return [(x1, y1, size_w, size_h, "테스트 중앙 모자이크", None)]
            
        elif pattern_type == "corners":
            # 네 모서리에 작은 모자이크들
            regions = []
            size = min(w, h) // 8
            mosaic_size = 15
            
            corners = [
                (50, 50, "좌상단"),
                (w - size - 50, 50, "우상단"),
                (50, h - size - 50, "좌하단"),
                (w - size - 50, h - size - 50, "우하단")
            ]
            
            for x, y, label in corners:
                x2, y2 = x + size, y + size
                roi = frame[y:y2, x:x2]
                small_roi = cv2.resize(roi, (max(size // mosaic_size, 1), max(size // mosaic_size, 1)))
                mosaic_roi = cv2.resize(small_roi, (size, size), interpolation=cv2.INTER_NEAREST)
                frame[y:y2, x:x2] = mosaic_roi
                
                regions.append((x, y, size, size, f"테스트 {label}", None))
            
            return regions
        
        return []
    
    def test_loop(self):
        """테스트 루프"""
        print("🔄 테스트 루프 시작")
        frame_count = 0
        start_time = time.time()
        pattern_type = "center"
        
        try:
            while self.running:
                # 프레임 캡처
                frame = self.capturer.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                # 패턴 변경 (5초마다)
                if frame_count % 150 == 0:  # 30fps 기준 5초
                    pattern_type = "corners" if pattern_type == "center" else "center"
                    print(f"🔄 패턴 변경: {pattern_type}")
                
                # 테스트 모자이크 적용
                processed_frame = frame.copy()
                test_regions = self.apply_test_mosaic(processed_frame, pattern_type)
                
                # 오버레이 업데이트
                self.overlay.update_regions(processed_frame, test_regions)
                
                frame_count += 1
                
                # 통계 출력 (30프레임마다)
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"⚡ 테스트 FPS: {fps:.1f}, 프레임: {frame_count}, 패턴: {pattern_type}")
                
                time.sleep(0.033)  # ~30 FPS
        
        except Exception as e:
            print(f"❌ 테스트 루프 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print("🛑 테스트 루프 종료")
    
    def start_test(self):
        """테스트 시작"""
        print("🚀 테스트 모자이크 시작!")
        print("  - 화면 중앙과 모서리에 번갈아 모자이크가 나타납니다")
        print("  - Ctrl+C로 중지하세요")
        
        # 오버레이 표시
        self.overlay.show()
        
        # 테스트 스레드 시작
        self.running = True
        self.process_thread = threading.Thread(target=self.test_loop, daemon=True)
        self.process_thread.start()
        
        # 메인 루프 (키보드 입력 대기)
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 사용자가 테스트를 중지했습니다")
        finally:
            self.stop_test()
    
    def stop_test(self):
        """테스트 중지"""
        print("🛑 테스트 모자이크 중지 중...")
        self.running = False
        
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=1.0)
        
        self.overlay.hide()
        self.capturer.stop_capture_thread()
        
        print("✅ 테스트 모자이크 중지 완료")

def main():
    """메인 함수"""
    print("🧪 테스트 모자이크 스크립트")
    print("="*50)
    print("이 스크립트는 실제 객체 감지 없이 강제로 모자이크를 적용하여")
    print("오버레이 시스템이 제대로 작동하는지 확인합니다.")
    print("="*50)
    
    app = TestMosaicApp()
    app.start_test()

if __name__ == "__main__":
    main()