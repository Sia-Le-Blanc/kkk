import cv2
import numpy as np
import time
from ultralytics import YOLO
from config import CONFIG

class MosaicProcessor:
    """Ultralytics YOLO 기반 객체 감지 및 모자이크 처리"""

    def __init__(self, model_path=None, config=None):
        # 설정 초기화
        if config is None:
            config = CONFIG.get('mosaic', {})
        self.config = config

        self.mosaic_strength = config.get('default_strength', 15)
        self.targets = config.get('default_targets', ["얼굴", "가슴", "보지", "팬티"])

        # 클래스 이름 수동 정의 (data.yaml 기준)
        self.class_names = CONFIG.get('models', {}).get('class_names', [
            "얼굴", "가슴", "겨드랑이", "보지", "발", "몸 전체", "자지",
            "팬티", "눈", "손", "교미", "신발", "가슴_옷", "보지_옷", "여성"
        ])

        # 모델 로드
        if model_path is None:
            model_path = CONFIG.get('models', {}).get('onnx_path', 'resources/best.onnx')

        self.model_path = model_path
        try:
            self.model = YOLO(self.model_path)
            self.model_ready = True
            print(f"✅ Ultralytics YOLO 모델 로드 성공: {self.model_path}")
        
            # 테스트 이미지로 모델 테스트
            import os
            test_img_path = os.path.join('resources', 'test.png')
            if os.path.exists(test_img_path):
                print(f"🧪 테스트 이미지로 모델 테스트: {test_img_path}")
                test_results = self.model(test_img_path)
                print(f"🧪 테스트 결과: {len(test_results[0].boxes)} 객체 감지됨")
                
                # 감지된 객체 정보 출력
                for i, box in enumerate(test_results[0].boxes):
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    class_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"Class-{class_id}"
                    print(f"🧪 테스트 감지 #{i+1}: {class_name} ({conf:.2f}) @ [{x1},{y1},{x2},{y2}]")
            else:
                print("🧪 테스트 이미지를 찾을 수 없습니다. resources/test.jpg를 추가하세요.")
        
        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            self.model_ready = False

    def set_targets(self, targets):
        self.targets = targets
        print(f"✅ 모자이크 타겟 설정: {self.targets}")

    def set_strength(self, strength):
        self.mosaic_strength = max(5, min(50, strength))
        print(f"✅ 모자이크 강도 설정: {self.mosaic_strength}")

    def apply_mosaic(self, img, x1, y1, x2, y2):
        """좌표 영역에 모자이크 적용"""
        roi = img[y1:y2, x1:x2]
        h, w = roi.shape[:2]

        if h < 5 or w < 5:
            return img

        roi = cv2.resize(roi, (max(w // self.mosaic_strength, 1), max(h // self.mosaic_strength, 1)), interpolation=cv2.INTER_LINEAR)
        roi = cv2.resize(roi, (w, h), interpolation=cv2.INTER_NEAREST)
        img[y1:y2, x1:x2] = roi
        return img
    
    def detect_objects(self, frame):
        """객체 감지 후 모자이크 적용"""
        if not self.model_ready:
            print("⚠️ 모델이 준비되지 않았습니다.")
            return frame

        try:
            # 디버깅용 정보 출력
            h, w, c = frame.shape
            print(f"🔍 프레임 분석: 크기={w}x{h}, 채널={c}, 타입={frame.dtype}")
            
            # 프레임 복사 및 전처리
            processed_frame = frame.copy()
            
            # BGR -> RGB 변환 (YOLO는 RGB 입력 예상)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 모델 실행
            results = self.model(rgb_frame, verbose=True)
            
            # 결과 처리
            num_detections = len(results[0].boxes)
            print(f"✅ 감지 결과: {num_detections} 객체 감지됨")
            
            # 감지된 객체가 있으면 처리
            if num_detections > 0:
                for i, box in enumerate(results[0].boxes):
                    # 좌표 및 정보 추출
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    class_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    # 신뢰도 임계값 확인
                    threshold = self.config.get('conf_threshold', 0.5)
                    if conf < threshold:
                        print(f"ℹ️ 객체 #{i+1} 신뢰도 부족: {conf:.2f} < {threshold}")
                        continue
                    
                    # 클래스 이름 가져오기
                    if class_id < len(self.class_names):
                        class_name = self.class_names[class_id]
                    else:
                        class_name = f"Class-{class_id}"
                    
                    # 디버깅 정보 출력
                    print(f"📌 감지 #{i+1}: {class_name} ({conf:.2f}) @ [{x1},{y1},{x2},{y2}]")
                    
                    # 타겟 클래스인 경우 모자이크 적용
                    if class_name in self.targets:
                        print(f"🎯 모자이크 적용: {class_name}")
                        processed_frame = self.apply_mosaic(processed_frame, x1, y1, x2, y2)
                    else:
                        print(f"ℹ️ 타겟이 아님: {class_name} ∉ {self.targets}")
            
            # 디버깅: 매 100 프레임마다 이미지 저장
            if not hasattr(self, 'frame_count'):
                self.frame_count = 0
            self.frame_count += 1
            
            if self.frame_count % 100 == 1:
                try:
                    import os
                    debug_dir = "debug_detection"
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_path = os.path.join(debug_dir, f"frame_{self.frame_count:04d}.jpg")
                    cv2.imwrite(debug_path, frame)
                    print(f"🧪 디버깅용 프레임 저장: {debug_path}")
                except Exception as e:
                    print(f"⚠️ 디버깅 이미지 저장 실패: {e}")
            
            
            return processed_frame

        except Exception as e:
            print(f"❌ 객체 감지 실패: {e}")
            import traceback
            traceback.print_exc()
            return frame
        

    def apply_test_pattern(self, frame):
        """테스트용 패턴 적용 (화면 중앙에 모자이크)"""
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        size = min(w, h) // 4
        
        x1 = center_x - size
        y1 = center_y - size
        x2 = center_x + size
        y2 = center_y + size
        
        print(f"🧪 테스트 모자이크: 중앙 영역 [{x1},{y1},{x2},{y2}]")
        return self.apply_mosaic(frame, x1, y1, x2, y2)