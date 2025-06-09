"""
캡처 방지 기능 테스트 스크립트
pygame 오버레이가 정말로 캡처에서 제외되는지 확인
"""

import time
import cv2
import numpy as np
from capture.mss_capture import ScreenCapturer
from overlay.pygame_overlay import PygameOverlayWindow

def test_capture_protection():
    """캡처 방지 기능 테스트"""
    print("🛡️ 캡처 방지 기능 테스트 시작")
    print("="*50)
    
    # 화면 캡처러 초기화
    capturer = ScreenCapturer()
    
    # 캡처 방지 오버레이 초기화
    overlay = PygameOverlayWindow()
    
    print("1️⃣ 오버레이 없이 화면 캡처 테스트...")
    
    # 오버레이 없이 캡처
    frame_without_overlay = capturer.get_frame()
    if frame_without_overlay is not None:
        cv2.imwrite("test_without_overlay.jpg", frame_without_overlay)
        print("✅ 오버레이 없는 캡처 저장: test_without_overlay.jpg")
    else:
        print("❌ 오버레이 없는 캡처 실패")
        return False
    
    print("\n2️⃣ 캡처 방지 오버레이 표시...")
    
    # 캡처 방지 오버레이 표시
    if not overlay.show():
        print("❌ 오버레이 표시 실패")
        return False
    
    # 오버레이 초기화 대기
    print("⏳ 오버레이 초기화 대기 중... (3초)")
    time.sleep(3)
    
    # 테스트용 모자이크 영역 추가
    print("3️⃣ 테스트용 모자이크 영역 추가...")
    
    # 화면 중앙에 빨간 박스 모자이크 영역 생성
    screen_height, screen_width = frame_without_overlay.shape[:2]
    test_x = screen_width // 2 - 100
    test_y = screen_height // 2 - 100
    test_w = 200
    test_h = 200
    
    # 빨간색 테스트 모자이크 생성
    test_mosaic = np.full((test_h, test_w, 3), [0, 0, 255], dtype=np.uint8)  # 빨간색
    
    # 오버레이에 테스트 영역 추가
    test_regions = [(test_x, test_y, test_w, test_h, test_mosaic, "TEST")]
    overlay.update_mosaic_regions(test_regions)
    
    print(f"✅ 테스트 모자이크 추가: ({test_x}, {test_y}, {test_w}, {test_h})")
    print("🔴 화면 중앙에 빨간 박스가 보여야 합니다")
    
    print("\n4️⃣ 오버레이 있는 상태에서 화면 캡처 테스트...")
    
    # 잠시 대기 후 캡처
    time.sleep(2)
    
    frame_with_overlay = capturer.get_frame()
    if frame_with_overlay is not None:
        cv2.imwrite("test_with_overlay.jpg", frame_with_overlay)
        print("✅ 오버레이 있는 캡처 저장: test_with_overlay.jpg")
    else:
        print("❌ 오버레이 있는 캡처 실패")
        overlay.hide()
        return False
    
    print("\n5️⃣ 캡처 결과 분석...")
    
    # 두 이미지 비교
    try:
        # 이미지 차이 계산
        diff = cv2.absdiff(frame_without_overlay, frame_with_overlay)
        diff_sum = np.sum(diff)
        
        # 테스트 영역에서 빨간색 픽셀 확인
        test_region_with = frame_with_overlay[test_y:test_y+test_h, test_x:test_x+test_w]
        red_pixels = np.sum((test_region_with[:, :, 2] > 200) & 
                           (test_region_with[:, :, 1] < 50) & 
                           (test_region_with[:, :, 0] < 50))
        
        print(f"📊 이미지 차이: {diff_sum}")
        print(f"🔴 캡처된 빨간 픽셀 수: {red_pixels}")
        
        if diff_sum < 1000000 and red_pixels < 100:  # 임계값
            print("🎉 캡처 방지 테스트 성공!")
            print("✅ pygame 오버레이가 MSS 캡처에서 제외됨")
            success = True
        else:
            print("⚠️ 캡처 방지 테스트 실패")
            print("❌ pygame 오버레이가 캡처에 포함됨")
            success = False
        
    except Exception as e:
        print(f"❌ 결과 분석 오류: {e}")
        success = False
    
    print("\n6️⃣ 정리...")
    
    # 오버레이 숨기기
    overlay.hide()
    
    print("🧹 테스트 완료")
    
    if success:
        print("\n🎉 최종 결과: 캡처 방지 성공!")
        print("🛡️ pygame 창이 MSS 캡처에서 완전히 제외됩니다.")
        print("✅ 피드백 루프 문제가 100% 해결되었습니다!")
    else:
        print("\n⚠️ 최종 결과: 캡처 방지 실패")
        print("💡 Windows 10+ 에서만 지원되는 기능입니다.")
        print("💡 또는 관리자 권한으로 실행해보세요.")
    
    return success

def main():
    """메인 함수"""
    print("🛡️ pygame 캡처 방지 기능 테스트")
    print("이 스크립트는 pygame 오버레이가 MSS 캡처에서 제외되는지 확인합니다.")
    print()
    
    try:
        success = test_capture_protection()
        
        print("\n📁 생성된 파일:")
        print("- test_without_overlay.jpg: 오버레이 없는 캡처")
        print("- test_with_overlay.jpg: 오버레이 있는 캡처")
        print("\n이 두 파일을 비교해보세요!")
        
        if success:
            print("✅ 두 이미지가 동일하면 캡처 방지 성공!")
        else:
            print("⚠️ 두 이미지가 다르면 캡처 방지 실패")
            
    except KeyboardInterrupt:
        print("\n🛑 테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()