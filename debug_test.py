"""
모자이크 시스템 컴포넌트 개별 테스트 스크립트
각 모듈이 제대로 작동하는지 단계별로 확인
"""

import cv2
import numpy as np
import time
import os
import sys

def test_imports():
    """필수 모듈 임포트 테스트"""
    print("="*50)
    print("📦 모듈 임포트 테스트")
    print("="*50)
    
    try:
        import pygame
        print("✅ pygame 임포트 성공")
    except ImportError as e:
        print(f"❌ pygame 임포트 실패: {e}")
    
    try:
        import cv2
        print(f"✅ opencv 임포트 성공 (버전: {cv2.__version__})")
    except ImportError as e:
        print(f"❌ opencv 임포트 실패: {e}")
    
    try:
        import mss
        print("✅ mss 임포트 성공")
    except ImportError as e:
        print(f"❌ mss 임포트 실패: {e}")
    
    try:
        from ultralytics import YOLO
        print("✅ ultralytics 임포트 성공")
    except ImportError as e:
        print(f"❌ ultralytics 임포트 실패: {e}")
    
    try:
        import win32api
        print("✅ win32api 임포트 성공")
    except ImportError as e:
        print(f"❌ win32api 임포트 실패: {e}")

def test_config():
    """설정 파일 테스트"""
    print("\n" + "="*50)
    print("⚙️ 설정 파일 테스트")
    print("="*50)
    
    try:
        from config import CONFIG
        print("✅ config 모듈 임포트 성공")
        print(f"🔍 CONFIG 키들: {list(CONFIG.keys())}")
        
        # 모델 경로 확인
        model_path = CONFIG.get('models', {}).get('onnx_path', 'resources/best.onnx')
        print(f"🔍 모델 경로: {model_path}")
        print(f"🔍 모델 파일 존재: {os.path.exists(model_path)}")
        
        # resources 디렉토리 확인
        if os.path.exists('resources'):
            files = os.listdir('resources')
            print(f"🔍 resources 디렉토리 파일들: {files}")
        else:
            print("⚠️ resources 디렉토리가 존재하지 않습니다")
            
    except Exception as e:
        print(f"❌ config 테스트 실패: {e}")

def test_screen_capture():
    """화면 캡처 테스트"""
    print("\n" + "="*50)
    print("📸 화면 캡처 테스트")
    print("="*50)
    
    try:
        from capture.mss_capture import ScreenCapturer
        from config import CONFIG
        
        capturer = ScreenCapturer(CONFIG.get("capture", {}))
        print(f"✅ ScreenCapturer 생성 성공")
        print(f"🔍 화면 해상도: {capturer.screen_width}x{capturer.screen_height}")
        print(f"🔍 캡처 해상도: {capturer.capture_width}x{capturer.capture_height}")
        
        # 프레임 캡처 테스트
        print("🔄 프레임 캡처 테스트 중...")
        start_time = time.time()
        
        for i in range(5):
            frame = capturer.get_frame()
            if frame is not None:
                print(f"✅ 프레임 #{i+1}: {frame.shape}, 타입: {frame.dtype}")
                
                # 첫 번째 프레임 저장
                if i == 0:
                    cv2.imwrite("test_capture.jpg", frame)
                    print("💾 테스트 캡처 이미지 저장: test_capture.jpg")
            else:
                print(f"❌ 프레임 #{i+1} 캡처 실패")
            
            time.sleep(0.1)
        
        elapsed = time.time() - start_time
        fps = 5 / elapsed
        print(f"⚡ 캡처 성능: {fps:.1f} FPS")
        
        capturer.stop_capture_thread()
        print("✅ 화면 캡처 테스트 완료")
        
    except Exception as e:
        print(f"❌ 화면 캡처 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_model_loading():
    """모델 로딩 테스트"""
    print("\n" + "="*50)
    print("🤖 모델 로딩 테스트")
    print("="*50)
    
    try:
        from detection.mosaic_processor import MosaicProcessor
        from config import CONFIG
        
        processor = MosaicProcessor(None, CONFIG.get("mosaic", {}))
        print(f"✅ MosaicProcessor 생성 완료")
        print(f"🔍 모델 준비 상태: {processor.model_ready}")
        print(f"🔍 클래스 이름들: {processor.class_names}")
        print(f"🔍 타겟 클래스들: {processor.targets}")
        
        if processor.model_ready:
            # 더미 이미지로 추론 테스트
            print("🔄 더미 이미지로 추론 테스트...")
            dummy_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            start_time = time.time()
            result = processor.detect_objects(dummy_image)
            inference_time = time.time() - start_time
            
            print(f"✅ 추론 완료: {inference_time:.3f}초")
            print(f"🔍 결과 타입: {type(result)}, 크기: {result.shape if hasattr(result, 'shape') else 'N/A'}")
            
            # 테스트 모자이크 적용
            print("🔄 테스트 모자이크 적용...")
            test_result = processor.apply_test_pattern(dummy_image.copy())
            cv2.imwrite("test_mosaic.jpg", test_result)
            print("💾 테스트 모자이크 이미지 저장: test_mosaic.jpg")
        else:
            print("⚠️ 모델이 준비되지 않아 추론 테스트를 건너뜁니다")
            
    except Exception as e:
        print(f"❌ 모델 로딩 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_overlay():
    """오버레이 테스트"""
    print("\n" + "="*50)
    print("🖼️ 오버레이 테스트")
    print("="*50)
    
    try:
        from overlay.pygame_overlay import PygameOverlayWindow
        from config import CONFIG
        
        overlay = PygameOverlayWindow(CONFIG.get("overlay", {}))
        print(f"✅ PygameOverlayWindow 생성 완료")
        print(f"🔍 오버레이 크기: {overlay.width}x{overlay.height}")
        
        # 오버레이 표시 테스트
        print("🔄 오버레이 표시 테스트...")
        overlay.show()
        
        # 테스트 영역 생성
        test_regions = [
            (100, 100, 200, 150, "테스트 영역 1", None),
            (400, 300, 180, 120, "테스트 영역 2", None),
        ]
        
        print("🔄 테스트 영역 업데이트...")
        dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
        overlay.update_regions(dummy_image, test_regions)
        
        print("⏱️ 5초 동안 오버레이 표시 테스트...")
        time.sleep(5)
        
        overlay.hide()
        print("✅ 오버레이 테스트 완료")
        
    except Exception as e:
        print(f"❌ 오버레이 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_gui():
    """GUI 테스트"""
    print("\n" + "="*50)
    print("🎮 GUI 테스트")
    print("="*50)
    
    try:
        from gui.gui_korean import GUIController
        from config import CONFIG
        
        # GUI 생성만 테스트 (실제 실행은 하지 않음)
        gui = GUIController(CONFIG.get("mosaic", {}))
        print(f"✅ GUIController 생성 완료")
        print(f"🔍 GUI 타겟들: {gui.get_selected_targets()}")
        print(f"🔍 GUI 강도: {gui.get_strength()}")
        
        # GUI는 메인 루프를 실행하면 블로킹되므로 여기서는 생성만 확인
        print("ℹ️ GUI 메인 루프는 수동으로 테스트하세요")
        
    except Exception as e:
        print(f"❌ GUI 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_integration():
    """통합 테스트 (짧은 시간)"""
    print("\n" + "="*50)
    print("🔄 통합 테스트 (10초간)")
    print("="*50)
    
    try:
        from capture.mss_capture import ScreenCapturer
        from detection.mosaic_processor import MosaicProcessor
        from overlay.pygame_overlay import PygameOverlayWindow
        from config import CONFIG
        
        # 컴포넌트들 생성
        capturer = ScreenCapturer(CONFIG.get("capture", {}))
        processor = MosaicProcessor(None, CONFIG.get("mosaic", {}))
        overlay = PygameOverlayWindow(CONFIG.get("overlay", {}))
        
        if not processor.model_ready:
            print("⚠️ 모델이 준비되지 않아 통합 테스트를 건너뜁니다")
            return
        
        print("✅ 모든 컴포넌트 생성 완료")
        
        # 오버레이 표시
        overlay.show()
        
        # 10초간 처리 루프
        print("🔄 10초간 실제 처리 테스트...")
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 10:
            # 프레임 캡처
            frame = capturer.get_frame()
            if frame is None:
                continue
            
            # 객체 감지 및 모자이크
            result = processor.detect_objects(frame)
            
            # 더미 모자이크 영역 (실제 감지 결과 대신)
            has_change = not np.array_equal(frame, result)
            regions = []
            if has_change:
                h, w = frame.shape[:2]
                regions = [(w//4, h//4, w//2, h//2, f"프레임 {frame_count}", result)]
            
            # 오버레이 업데이트
            overlay.update_regions(result, regions)
            
            frame_count += 1
            time.sleep(0.033)  # ~30 FPS
        
        total_time = time.time() - start_time
        fps = frame_count / total_time
        
        print(f"✅ 통합 테스트 완료")
        print(f"⚡ 처리된 프레임: {frame_count}")
        print(f"⚡ 평균 FPS: {fps:.1f}")
        
        # 정리
        overlay.hide()
        capturer.stop_capture_thread()
        
    except Exception as e:
        print(f"❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 테스트 함수"""
    print("🧪 모자이크 시스템 컴포넌트 테스트 시작")
    print("현재 작업 디렉토리:", os.getcwd())
    
    # 각 테스트 실행
    test_imports()
    test_config()
    test_screen_capture()
    test_model_loading()
    test_overlay()
    test_gui()
    test_integration()
    
    print("\n" + "="*50)
    print("🎉 모든 테스트 완료!")
    print("="*50)
    print("💡 문제가 있는 부분을 확인하고 main.py를 실행하세요.")

if __name__ == "__main__":
    main()