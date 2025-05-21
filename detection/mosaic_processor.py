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
        self.class_names = [
            "얼굴", "가슴", "겨드랑이", "보지", "발", "몸 전체", "자지",
            "팬티", "눈", "손", "교미", "신발", "가슴_옷", "보지_옷", "여성"
        ]

        # 모델 로드
        if model_path is None:
            model_path = CONFIG.get('models', {}).get('onnx_path', 'resources/best.onnx')

        self.model_path = model_path
        try:
            self.model = YOLO(self.model_path)
            self.model_ready = True
            print(f"✅ Ultralytics YOLO 모델 로드 성공: {self.model_path}")
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
            return frame

        try:
            results = self.model(frame)[0]  # 첫 번째 결과만 사용
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_id = int(box.cls[0])
                class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"Class-{class_id}"

                if class_name in self.targets:
                    frame = self.apply_mosaic(frame, x1, y1, x2, y2)

            return frame

        except Exception as e:
            print(f"❌ 감지 실패: {e}")
            return frame
