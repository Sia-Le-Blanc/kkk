"""
모자이크 시스템의 결과를 스크린샷으로 저장하는 테스트 스크립트
"""

import cv2
import numpy as np
import time
import os
from datetime import datetime
from capture.mss_capture import ScreenCapturer
from detection.mosaic_processor import MosaicProcessor
from overlay.pygame_overlay import PygameOverlayWindow
from config import CONFIG

class ScreenshotTester:
    """스크린샷 테스트 클래스"""
    
    def __init__(self):
        print("📸 스크린샷 테스터 초기화...")
        
        self.capturer = ScreenCapturer(CONFIG.get("capture", {}))
        self.processor = MosaicProcessor(None, CONFIG.get("mosaic", {}))
        self.overlay = PygameOverlayWindow(CONFIG.get("overlay", {}))
        
        # 결과 저장 디렉토리
        self.results_dir = "screenshot_results"
        os.makedirs(self.results_dir, exist_ok=True)
        
        print("✅ 스크린샷 테스터 초기화 완료")
    
    def capture_and_process(self, duration=10):
        """지정된 시간 동안 캡처하고 처리한 결과 저장"""
        print(f"🔄 {duration}초 동안 캡처 및 처리 시작...")
        
        # 타겟 설정
        self.processor.set_targets(["여성", "얼굴", "가슴", "보지", "팬티"])
        self.processor.set_strength(20)  # 강한 모자이크
        
        # 오버레이 표시
        self.overlay.show()
        
        start_time = time.time()
        frame_count = 0
        processed_count = 0
        
        try:
            while time.time() - start_time < duration:
                # 프레임 캡처
                frame = self.capturer.get_frame()
                if frame is None:
                    continue
                
                frame_count += 1
                
                # 객체 감지 및 모자이크 처리
                original_frame = frame.copy()
                processed_frame = self.processor.detect_objects(frame)
                
                # 모자이크 적용 여부 확인
                diff = cv2.absdiff(original_frame, processed_frame)
                has_mosaic = np.sum(diff) > 1000000
                
                if has_mosaic:
                    processed_count += 1
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    
                    # 원본 저장
                    original_path = os.path.join(self.results_dir, f"original_{timestamp}.jpg")
                    cv2.imwrite(original_path, original_frame)
                    
                    # 처리된 프레임 저장
                    processed_path = os.path.join(self.results_dir, f"processed_{timestamp}.jpg")
                    cv2.imwrite(processed_path, processed_frame)
                    
                    # 차이 이미지 저장
                    diff_path = os.path.join(self.results_dir, f"diff_{timestamp}.jpg")
                    cv2.imwrite(diff_path, diff)
                    
                    print(f"💾 모자이크 적용된 프레임 #{frame_count} 저장:")
                    print(f"   원본: {original_path}")
                    print(f"   처리됨: {processed_path}")
                    print(f"   차이: {diff_path}")
                    
                    # 더미 오버레이 영역 생성
                    h, w = processed_frame.shape[:2]
                    test_regions = [(w//4, h//4, w//2, h//2, f"프레임 {frame_count}", None)]
                    self.overlay.update_regions(processed_frame, test_regions)
                
                # 3초마다 강제 스크린샷
                if frame_count % 90 == 0:  # 30fps 기준 3초
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = os.path.join(self.results_dir, f"screenshot_{timestamp}.jpg")
                    
                    # 전체 화면 캡처
                    full_screen = self.capturer.get_frame()
                    if full_screen is not None:
                        cv2.imwrite(screenshot_path, full_screen)
                        print(f"📸 전체 화면 캡처: {screenshot_path}")
                
                time.sleep(0.033)  # ~30 FPS
        
        except KeyboardInterrupt:
            print("\n🛑 사용자가 테스트를 중지했습니다")
        
        finally:
            self.overlay.hide()
            
            # 최종 통계
            print(f"\n📊 테스트 완료:")
            print(f"   총 프레임: {frame_count}")
            print(f"   모자이크 적용: {processed_count}")
            print(f"   결과 디렉토리: {self.results_dir}")
            
            if processed_count > 0:
                print(f"   적용률: {(processed_count/frame_count)*100:.1f}%")
            
            # 디렉토리 내용 확인
            files = os.listdir(self.results_dir)
            print(f"   저장된 파일 수: {len(files)}")
    
    def single_capture_test(self):
        """단일 캡처 테스트"""
        print("📸 단일 캡처 테스트...")
        
        # 타겟 설정
        self.processor.set_targets(["여성", "얼굴", "가슴"])
        
        # 프레임 캡처
        frame = self.capturer.get_frame()
        if frame is None:
            print("❌ 프레임 캡처 실패")
            return
        
        print(f"✅ 프레임 캡처 성공: {frame.shape}")
        
        # 처리
        original_frame = frame.copy()
        processed_frame = self.processor.detect_objects(frame)
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        original_path = os.path.join(self.results_dir, f"single_original_{timestamp}.jpg")
        processed_path = os.path.join(self.results_dir, f"single_processed_{timestamp}.jpg")
        
        cv2.imwrite(original_path, original_frame)
        cv2.imwrite(processed_path, processed_frame)
        
        # 차이 확인
        diff = cv2.absdiff(original_frame, processed_frame)
        diff_sum = np.sum(diff)
        
        print(f"💾 단일 테스트 결과 저장:")
        print(f"   원본: {original_path}")
        print(f"   처리됨: {processed_path}")
        print(f"   차이값: {diff_sum}")
        
        if diff_sum > 1000000:
            print("✅ 모자이크가 적용되었습니다!")
            diff_path = os.path.join(self.results_dir, f"single_diff_{timestamp}.jpg")
            cv2.imwrite(diff_path, diff)
            print(f"   차이 이미지: {diff_path}")
        else:
            print("ℹ️ 모자이크가 적용되지 않았습니다")

def main():
    """메인 함수"""
    print("📸 모자이크 시스템 스크린샷 테스트")
    print("="*50)
    
    tester = ScreenshotTester()
    
    print("\n선택하세요:")
    print("1. 단일 캡처 테스트")
    print("2. 10초간 연속 캡처 테스트")
    
    choice = input("선택 (1/2): ").strip()
    
    if choice == "1":
        tester.single_capture_test()
    elif choice == "2":
        tester.capture_and_process(10)
    else:
        print("잘못된 선택입니다")
    
    print(f"\n✅ 테스트 완료! 결과는 {tester.results_dir} 폴더를 확인하세요")

if __name__ == "__main__":
    main()