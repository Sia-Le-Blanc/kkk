"""
YOLO 모델을 직접 테스트하는 스크립트
모델이 실제로 올바른 클래스를 출력하는지 확인
"""

import cv2
import numpy as np
import os
from ultralytics import YOLO

def test_yolo_model():
    """YOLO 모델 직접 테스트"""
    print("🤖 YOLO 모델 직접 테스트")
    print("="*50)
    
    # 모델 경로
    model_path = 'resources/best.onnx'
    
    if not os.path.exists(model_path):
        print(f"❌ 모델 파일이 없습니다: {model_path}")
        return
    
    try:
        # 모델 로드
        print(f"🔄 모델 로딩: {model_path}")
        model = YOLO(model_path)
        print("✅ 모델 로드 성공")
        
        # 모델 정보 확인
        print(f"🔍 모델 이름: {model.model_name if hasattr(model, 'model_name') else 'N/A'}")
        
        # 더미 이미지 생성 및 테스트
        print("🔄 더미 이미지로 추론 테스트...")
        dummy_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        # 추론 실행
        results = model(dummy_img, verbose=True)
        
        # 결과 분석
        result = results[0]
        print(f"📊 감지된 객체 수: {len(result.boxes)}")
        
        if len(result.boxes) > 0:
            print("📋 감지된 객체들:")
            for i, box in enumerate(result.boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_id = int(box.cls[0])
                conf = float(box.conf[0])
                print(f"  #{i+1}: 클래스 ID={class_id}, 신뢰도={conf:.3f}, 좌표=[{x1},{y1},{x2},{y2}]")
        
        # 모델의 클래스 이름 확인 (가능한 경우)
        try:
            if hasattr(model, 'names'):
                print(f"🏷️ 모델의 클래스 이름: {model.names}")
            elif hasattr(model.model, 'names'):
                print(f"🏷️ 모델의 클래스 이름: {model.model.names}")
            else:
                print("⚠️ 모델에서 클래스 이름을 가져올 수 없습니다")
        except Exception as e:
            print(f"⚠️ 클래스 이름 가져오기 실패: {e}")
        
        # 화면 캡처로 실제 테스트
        print("\n🔄 화면 캡처로 실제 테스트...")
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # 첫 번째 모니터
                screenshot = sct.grab(monitor)
                img_array = np.array(screenshot)
                
                # BGR로 변환
                if img_array.shape[2] == 4:  # BGRA
                    img_array = img_array[:, :, :3]  # BGR만 추출
                
                # RGB로 변환 (YOLO용)
                rgb_img = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
                
                print(f"📸 캡처된 이미지 크기: {rgb_img.shape}")
                
                # 실제 화면으로 추론
                real_results = model(rgb_img, verbose=True)
                real_result = real_results[0]
                
                print(f"📊 실제 화면에서 감지된 객체 수: {len(real_result.boxes)}")
                
                if len(real_result.boxes) > 0:
                    print("📋 실제 화면에서 감지된 객체들:")
                    for i, box in enumerate(real_result.boxes):
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        class_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        print(f"  #{i+1}: 클래스 ID={class_id}, 신뢰도={conf:.3f}, 좌표=[{x1},{y1},{x2},{y2}]")
                        
                        # 시각화를 위해 이미지에 박스 그리기
                        cv2.rectangle(img_array, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(img_array, f"ID:{class_id} ({conf:.2f})", 
                                  (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    # 결과 이미지 저장
                    cv2.imwrite("yolo_test_result.jpg", img_array)
                    print("💾 결과 이미지 저장: yolo_test_result.jpg")
                else:
                    print("ℹ️ 실제 화면에서는 객체가 감지되지 않았습니다")
                    # 원본 이미지 저장
                    cv2.imwrite("yolo_test_screenshot.jpg", img_array)
                    print("💾 스크린샷 저장: yolo_test_screenshot.jpg")
                
        except Exception as e:
            print(f"⚠️ 화면 캡처 테스트 실패: {e}")
        
        print("✅ YOLO 모델 테스트 완료")
        
    except Exception as e:
        print(f"❌ YOLO 모델 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def inspect_model_metadata():
    """모델 메타데이터 상세 검사"""
    print("\n🔍 모델 메타데이터 상세 검사")
    print("="*50)
    
    model_path = 'resources/best.onnx'
    
    if not os.path.exists(model_path):
        print(f"❌ 모델 파일이 없습니다: {model_path}")
        return
    
    try:
        # ONNX 모델 직접 검사
        try:
            import onnx
            print("🔄 ONNX 모델 메타데이터 로딩...")
            onnx_model = onnx.load(model_path)
            
            print(f"📋 ONNX 모델 정보:")
            print(f"  - IR 버전: {onnx_model.ir_version}")
            print(f"  - Producer: {onnx_model.producer_name}")
            print(f"  - 메타데이터 개수: {len(onnx_model.metadata_props)}")
            
            # 메타데이터 출력
            for prop in onnx_model.metadata_props:
                print(f"  - {prop.key}: {prop.value}")
            
            # 입력/출력 정보
            graph = onnx_model.graph
            print(f"📋 그래프 정보:")
            print(f"  - 입력 수: {len(graph.input)}")
            print(f"  - 출력 수: {len(graph.output)}")
            
            for i, inp in enumerate(graph.input):
                print(f"  - 입력 #{i}: {inp.name}")
                if inp.type.tensor_type.shape.dim:
                    dims = [d.dim_value for d in inp.type.tensor_type.shape.dim]
                    print(f"    크기: {dims}")
            
            for i, out in enumerate(graph.output):
                print(f"  - 출력 #{i}: {out.name}")
                if out.type.tensor_type.shape.dim:
                    dims = [d.dim_value for d in out.type.tensor_type.shape.dim]
                    print(f"    크기: {dims}")
            
        except ImportError:
            print("⚠️ onnx 패키지가 설치되지 않았습니다")
        except Exception as e:
            print(f"⚠️ ONNX 메타데이터 검사 실패: {e}")
        
        # Ultralytics로 모델 정보 확인
        print("\n🔄 Ultralytics로 모델 정보 확인...")
        model = YOLO(model_path)
        
        # 모델 속성들 확인
        attrs = ['names', 'model', 'predictor', 'trainer']
        for attr in attrs:
            if hasattr(model, attr):
                value = getattr(model, attr)
                print(f"📋 model.{attr}: {type(value)} = {value}")
        
        # 모델의 내부 구조 확인
        if hasattr(model, 'model'):
            print(f"📋 model.model: {type(model.model)}")
            if hasattr(model.model, 'names'):
                print(f"📋 model.model.names: {model.model.names}")
            if hasattr(model.model, 'yaml'):
                print(f"📋 model.model.yaml: {model.model.yaml}")
        
    except Exception as e:
        print(f"❌ 모델 메타데이터 검사 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    print("🧪 YOLO 모델 직접 테스트 시작")
    print(f"📁 현재 작업 디렉토리: {os.getcwd()}")
    
    test_yolo_model()
    inspect_model_metadata()
    
    print("\n🎉 YOLO 모델 테스트 완료!")

if __name__ == "__main__":
    main()