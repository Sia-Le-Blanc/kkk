"""
ONNX 모델을 사용한 객체 감지 및 모자이크 처리 모듈
"""

import cv2
import numpy as np
import os
import time
import onnxruntime as ort
from config import CONFIG

class MosaicProcessor:
    """객체 감지 및 모자이크 처리 클래스"""
    
    def __init__(self, model_path=None, config=None):
        # 설정 가져오기
        if config is None:
            config = CONFIG.get('mosaic', {})
        self.config = config
        
        # 모델 관련 설정
        if model_path is None:
            model_path = CONFIG.get('models', {}).get('onnx_path', 'resources/best.onnx')
            
        self.model_path = model_path
        self.input_size = CONFIG.get('models', {}).get('input_size', (640, 640))
        self.conf_threshold = config.get('conf_threshold', 0.5)
        self.class_names = CONFIG.get('models', {}).get('class_names', [])
        
        # 모자이크 설정
        self.mosaic_strength = config.get('default_strength', 15)
        self.targets = config.get('default_targets', ["얼굴", "가슴", "보지", "팬티"])
        
        # 테스트용 영역 (디버그 모드에서 사용)
        self.test_regions = []
        
        # 성능 측정 변수
        self.avg_processing_time = 0.0
        
        # ONNX 런타임 세션 초기화
        self._init_onnx_session()
    
    def _init_onnx_session(self):
        """ONNX 런타임 세션 초기화"""
        try:
            # 가능한 모든 실행 공급자 확인
            providers = []
            
            # CUDA/GPU 공급자 시도
            if 'CUDAExecutionProvider' in ort.get_available_providers():
                providers.append('CUDAExecutionProvider')
                print("✅ CUDA 실행 공급자 사용 가능")
                
            # DirectML 공급자 시도 (Windows)
            if 'DmlExecutionProvider' in ort.get_available_providers():
                providers.append('DmlExecutionProvider')
                print("✅ DirectML 실행 공급자 사용 가능")
                
            # 항상 CPU 공급자는 마지막에 추가
            providers.append('CPUExecutionProvider')
            
            # 세션 생성 시도
            if os.path.isfile(self.model_path):
                self.session = ort.InferenceSession(self.model_path, providers=providers)
                self.input_name = self.session.get_inputs()[0].name
                self.output_names = [output.name for output in self.session.get_outputs()]
                print(f"✅ ONNX 모델 로드 성공: {self.model_path}")
                print(f"   입력명: {self.input_name}")
                print(f"   출력명: {self.output_names}")
                self.model_ready = True
            else:
                print(f"❌ 모델 파일이 존재하지 않음: {self.model_path}")
                self.session = None
                self.model_ready = False
                
        except Exception as e:
            print(f"❌ ONNX 모델 로드 실패: {e}")
            # 백업 옵션: 테스트 모드로 전환
            self.session = None
            self.model_ready = False
    
    def preprocess(self, frame):
        """이미지 전처리"""
        # 모델 입력 크기로 리사이즈
        img = cv2.resize(frame, self.input_size)
        
        # BGR에서 RGB로 변환 및 정규화
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_rgb = img_rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
        
        # 배치 차원 추가
        return np.expand_dims(img_rgb, axis=0), img.shape[1], img.shape[0]
    
    def postprocess(self, outputs, original_w, original_h):
        """모델 출력 후처리"""
        # 모델 출력에 따라 postprocess 방식 결정
        
        # YOLOv8 출력 형식 (nx8400x84 또는 nx8400x5+nc) - 일반적인 형태
        if len(outputs) == 1 and len(outputs[0].shape) == 3:
            return self._postprocess_yolov8(outputs, original_w, original_h)
            
        # YOLOv5 출력 형식 (1x25200x85) - 구형 모델
        elif len(outputs) == 1 and len(outputs[0].shape) == 3:
            return self._postprocess_yolov5(outputs, original_w, original_h)
            
        # 다중 출력 형식 - 일부 모델
        elif len(outputs) > 1:
            print("⚠️ 다중 출력 형식 감지됨, 첫 번째 출력 처리")
            return self._postprocess_yolov8([outputs[0]], original_w, original_h)
            
        # 알 수 없는 형식
        else:
            print(f"⚠️ 알 수 없는 출력 형식: {[o.shape for o in outputs]}")
            # 빈 결과 반환
            return []
    
    def _postprocess_yolov8(self, outputs, original_w, original_h):
        """YOLOv8 출력 후처리"""
        preds = outputs[0]  # (1, num_boxes, 4+1+num_classes)
        boxes = []
        
        # 각 박스 확인
        for pred in preds[0]:
            # 신뢰도 확인
            conf = float(pred[4])
            if conf < self.conf_threshold:
                continue
                
            # 클래스 확인
            class_scores = pred[5:]
            class_id = int(np.argmax(class_scores))
            
            # 타겟 클래스만 처리
            if self.class_names and class_id < len(self.class_names):
                class_name = self.class_names[class_id]
                if self.targets and class_name not in self.targets:
                    continue
            else:
                # 클래스 이름 없으면 숫자로 표시
                class_name = f"Class-{class_id}"
                
            # 좌표 변환 (중심점, 크기 -> 좌상단, 우하단)
            cx, cy, w, h = pred[0:4]
            x1 = int((cx - w / 2) * original_w / self.input_size[0])
            y1 = int((cy - h / 2) * original_h / self.input_size[1])
            x2 = int((cx + w / 2) * original_w / self.input_size[0])
            y2 = int((cy + h / 2) * original_h / self.input_size[1])
            
            # 유효한 좌표만 추가
            if x1 < x2 and y1 < y2:
                boxes.append((x1, y1, x2, y2, conf, class_id, class_name))
                
        return boxes
    
    def _postprocess_yolov5(self, outputs, original_w, original_h):
        """YOLOv5 출력 후처리"""
        boxes = []
        preds = outputs[0]  # (1, 25200, 85)
        
        # 각 박스 확인
        for i in range(preds.shape[1]):
            pred = preds[0, i]
            
            # 신뢰도 확인
            conf = float(pred[4])
            if conf < self.conf_threshold:
                continue
                
            # 클래스 확인
            class_scores = pred[5:]
            class_id = int(np.argmax(class_scores))
            
            # 타겟 클래스만 처리
            if self.class_names and class_id < len(self.class_names):
                class_name = self.class_names[class_id]
                if self.targets and class_name not in self.targets:
                    continue
            else:
                # 클래스 이름 없으면 숫자로 표시
                class_name = f"Class-{class_id}"
                
            # 좌표 변환 (xywh -> x1y1x2y2)
            x, y, w, h = pred[0:4]
            x1 = int(x * original_w / self.input_size[0])
            y1 = int(y * original_h / self.input_size[1])
            x2 = int((x + w) * original_w / self.input_size[0])
            y2 = int((y + h) * original_h / self.input_size[1])
            
            # 유효한 좌표만 추가
            if x1 < x2 and y1 < y2:
                boxes.append((x1, y1, x2, y2, conf, class_id, class_name))
                
        return boxes
    
    def apply_mosaic(self, frame, boxes):
        """검출된 객체에 모자이크 효과 적용"""
        results = []
        
        # 모자이크 강도 적용
        strength = self.mosaic_strength
        
        # 각 객체에 대해 모자이크 처리
        for box in boxes:
            x1, y1, x2, y2, conf, class_id, class_name = box
            
            # 좌표 경계 검사
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
            
            # 너비, 높이 계산
            w, h = x2 - x1, y2 - y1
            
            # 영역이 유효한지 확인
            if w <= 0 or h <= 0:
                continue
                
            # 영역 추출
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue
                
            # 성능 최적화: 작은 영역은 더 빠른 알고리즘 사용
            fast_mosaic_threshold = 50 * 50  # 50x50 픽셀 이하는 빠른 처리
            
            if w * h <= fast_mosaic_threshold:
                # 작은 영역: 단순 평균값으로 처리 (더 빠름)
                color = np.mean(roi, axis=(0, 1)).astype(np.uint8)
                mosaic = np.ones((h, w, 3), dtype=np.uint8) * color.reshape(1, 1, 3)
            else:
                # 큰 영역: 모자이크 효과 적용
                small = cv2.resize(roi, (strength, strength), interpolation=cv2.INTER_LINEAR)
                mosaic = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
            
            # 결과에 추가
            results.append((x1, y1, w, h, class_name, mosaic))
        
        return results
    
    def detect_objects(self, frame):
        """프레임에서 객체 감지 후 모자이크 처리"""
        # 시작 시간 기록
        start_time = time.time()
        
        # 모델이 준비되지 않은 경우 테스트 영역 반환
        if not self.model_ready or self.session is None:
            if not self.test_regions:
                # 기본 테스트 영역 설정
                self.test_regions = [
                    (100, 100, 200, 200, self.targets[0] if self.targets else "테스트1", None),
                    (400, 300, 150, 150, self.targets[1] if len(self.targets) > 1 else "테스트2", None)
                ]
                
                # 테스트 영역에 모자이크 적용
                for i, (x, y, w, h, label, _) in enumerate(self.test_regions):
                    # 좌표 경계 검사
                    if x < 0 or y < 0 or x + w > frame.shape[1] or y + h > frame.shape[0]:
                        continue
                        
                    # 영역 추출 및 모자이크 적용
                    roi = frame[y:y+h, x:x+w]
                    small = cv2.resize(roi, (self.mosaic_strength, self.mosaic_strength), interpolation=cv2.INTER_LINEAR)
                    mosaic = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
                    
                    # 테스트 영역 업데이트
                    self.test_regions[i] = (x, y, w, h, label, mosaic)
            
            # 테스트 영역 반환
            return self.test_regions
        
        # 실제 객체 감지 및 모자이크 처리
        try:
            # 이미지 전처리
            input_tensor, input_width, input_height = self.preprocess(frame)
            
            # 모델 추론
            outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
            
            # 결과 후처리
            boxes = self.postprocess(outputs, frame.shape[1], frame.shape[0])
            
            # 모자이크 적용
            result = self.apply_mosaic(frame, boxes)
            
            # 처리 시간 측정 및 업데이트
            process_time = (time.time() - start_time) * 1000  # ms 단위
            
            # 이동 평균 업데이트
            if not hasattr(self, 'avg_processing_time') or self.avg_processing_time == 0:
                self.avg_processing_time = process_time
            else:
                self.avg_processing_time = 0.9 * self.avg_processing_time + 0.1 * process_time
            
            return result
            
        except Exception as e:
            print(f"❌ 객체 감지 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def set_targets(self, targets):
        """타겟 클래스 설정"""
        self.targets = targets
        print(f"✅ 모자이크 타겟 설정: {self.targets}")
    
    def set_strength(self, strength):
        """모자이크 강도 설정"""
        self.mosaic_strength = max(5, min(50, strength))  # 5-50 범위로 제한
        print(f"✅ 모자이크 강도 설정: {self.mosaic_strength}")