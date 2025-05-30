import cv2
import numpy as np
import time
import os
import threading
from overlay.base import BaseOverlay

class CV2OverlayWindow(BaseOverlay):
    """OpenCV 창을 사용하는 단순한 오버레이 윈도우"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.window_name = "Mosaic Overlay"
        
        try:
            import win32api
            self.width = win32api.GetSystemMetrics(0)  # SM_CXSCREEN
            self.height = win32api.GetSystemMetrics(1)  # SM_CYSCREEN
        except:
            self.width = 1366  # 기본값
            self.height = 768  # 기본값
        
        print(f"✅ OpenCV 기반 오버레이 창 초기화 완료 (해상도: {self.width}x{self.height})")
    
    def _render_thread_func(self):
        """렌더링 스레드 함수"""
        last_render_time = time.time()
        frame_count = 0
        
        try:
            # 투명 이미지 생성
            overlay = np.zeros((self.height, self.width, 4), dtype=np.uint8)
            
            while not self.stop_event.is_set():
                try:
                    if self.shown:
                        start_time = time.time()
                        
                        # 화면 현재 크기에 맞는 빈 투명 이미지 생성
                        overlay.fill(0)  # 모두 투명으로 초기화
                        
                        # 모자이크 영역 그리기 (빨간색 반투명)
                        if self.mosaic_regions:
                            for x, y, w, h, label, _ in self.mosaic_regions:
                                # 좌표 경계 검사
                                x1, y1 = max(0, x), max(0, y)
                                x2, y2 = min(self.width, x+w), min(self.height, y+h)
                                
                                # 영역이 유효하면 사각형 그리기
                                if x2 > x1 and y2 > y1:
                                    # 빨간색 반투명 사각형
                                    overlay[y1:y2, x1:x2, 0] = 0    # B
                                    overlay[y1:y2, x1:x2, 1] = 0    # G
                                    overlay[y1:y2, x1:x2, 2] = 255  # R
                                    overlay[y1:y2, x1:x2, 3] = 180  # Alpha (반투명)
                                    
                                    # 테두리 (흰색)
                                    cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255, 255), 2)
                                    
                                    # 텍스트 (흰색)
                                    cv2.putText(overlay, label, (x1+5, y1+20), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255, 255), 2)
                        
                        # 윈도우가 아직 존재하는지 확인
                        try:
                            visible = cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE)
                            if visible < 1:
                                print("⚠️ 윈도우가 보이지 않음, 다시 생성")
                                cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)
                        except:
                            # 윈도우가 존재하지 않으면 다시 생성
                            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)
                        
                        # 오버레이 창 표시 (투명 배경 지원)
                        cv2.imshow(self.window_name, overlay)
                        cv2.waitKey(1)  # 화면 갱신을 위한 키 이벤트 처리
                        
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
            # 리소스 정리
            try:
                cv2.destroyWindow(self.window_name)
            except:
                pass
            
            print("🛑 렌더링 스레드 종료됨")
    
    def show(self):
        """오버레이 창 표시"""
        print("✅ CV2 오버레이 창 표시")
        
        # namedWindow 설정
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)  # 항상 위에 표시
        
        self.shown = True
        
        # 렌더링 스레드 시작
        if self.render_thread is None or not self.render_thread.is_alive():
            self.stop_event.clear()
            self.render_thread = threading.Thread(target=self._render_thread_func, daemon=True)
            self.render_thread.start()
            print("✅ 렌더링 스레드 시작됨")
    
    def hide(self):
        """오버레이 창 숨기기"""
        print("🛑 CV2 오버레이 창 숨기기")
        
        # 창 닫기
        cv2.destroyWindow(self.window_name)
        self.shown = False
        
        # 렌더링 스레드 중지
        if self.render_thread and self.render_thread.is_alive():
            self.stop_event.set()
            self.render_thread.join(timeout=1.0)
            self.render_thread = None
            print("🛑 렌더링 스레드 중지됨")
    
    def update_regions(self, original_image, mosaic_regions):
        """모자이크 영역 업데이트"""
        try:
            if original_image is None:
                return
            
            self.frame_count += 1
            
            # 모자이크 정보 저장
            self.original_image = original_image
            self.mosaic_regions = mosaic_regions
            
            # 모자이크 영역 조회 및 로그 출력
            save_interval = self.config.get('debug_save_interval', 30)
            if len(mosaic_regions) > 0:
                if self.frame_count % save_interval == 0:  # 30프레임마다 로그 출력
                    print(f"✅ 모자이크 영역 {len(mosaic_regions)}개 처리 중 (프레임 #{self.frame_count})")
                    self._save_debug_image()
            elif self.frame_count % (save_interval * 3) == 0:  # 더 긴 간격으로 로그 출력
                print(f"📢 모자이크 영역 없음 (프레임 #{self.frame_count})")
        
        except Exception as e:
            print(f"❌ 오버레이 업데이트 실패: {e}")
    
    def get_window_handle(self):
        """윈도우 핸들 반환 (OpenCV에서는 실제 핸들이 없음)"""
        return 0