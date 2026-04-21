# import statements
import time
from pathlib import Path
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

import os 
from dotenv import load_dotenv

# .env 파일 읽고 환경변수로 로드
load_dotenv()

# 환경변수에서 값 가져오기
key = os.environ["COMPUTER_VISION_KEY"]
endpoint = os.environ["COMPUTER_VISION_ENDPOINT"]

# Computer Vision 클라이언트 생성
cvc = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))

image_path = Path("receipts") / "sample.jpg"

if not image_path.exists():
    raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

with open(image_path, "rb") as f:
    res = cvc.read_in_stream(f, raw=True)

operation_url = res.headers.get("Operation-Location")
if not operation_url:
    raise RuntimeError("Azure 응답에 Operation-Location 헤더가 없습니다")

operation_id = operation_url.split("/")[-1] 

MAX_WAIT_SECONDS = 60
start = time.time()

print("OCR 처리 중...", end="", flush=True)

while True:
    if time.time() - start > MAX_WAIT_SECONDS:
        raise TimeoutError(f"OCR이 {MAX_WAIT_SECONDS}초 내에 완료되지 않았습니다")
    
    result = cvc.get_read_result(operation_id)

    if result.status not in ["notStarted", "running"]:
        break

    print(".", end="", flush=True)
    time.sleep(1)

print(" 완료!")

if result.status == OperationStatusCodes.succeeded:
    ocr_texts = []
    for page in result.analyze_result.read_results:
        for line in page.lines:
            ocr_texts.append(line.text)
    full_text = "\n".join(ocr_texts)

elif result.status == OperationStatusCodes.failed:
    raise RuntimeError(f"OCR 실패: operation_id={operation_id}")

else:
    raise RuntimeError(f"예상치 못한 OCR 상태: {result.status}")

print("=" * 50)
print("OCR 결과")
print("=" * 50)
print(full_text)
print("=" * 50)
print(f"총 {len(ocr_texts)}줄 추출됨")