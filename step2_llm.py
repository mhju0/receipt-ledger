import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# ── 프롬프트 ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
너는 영수증 데이터 추출 전문가야.
OCR로 읽은 영수증 텍스트를 받아서, 아래 JSON 형식으로 정확하게 추출해.

반드시 지켜야 할 규칙:
1. 반드시 유효한 JSON만 반환. 설명, 마크다운 코드블록 절대 금지
2. 값을 찾을 수 없으면 null 사용 (빈 문자열 "" 사용 금지)
3. 숫자 필드는 콤마/원기호/통화기호 제거 후 정수만
4. date 형식: YYYY-MM-DD / time 형식: HH:MM:SS

반환할 JSON 구조:
{
  "store_name":      "가게명 (없으면 null)",
  "business_number": "사업자등록번호 (없으면 null)",
  "receipt_number":  "영수증 번호 (없으면 null)",
  "date":            "YYYY-MM-DD (없으면 null)",
  "time":            "HH:MM:SS (없으면 null)",
  "subtotal":        부가세 전 금액 정수 (없으면 null),
  "tax_amount":      부가세 정수 (없으면 null),
  "total":           최종 합계 정수 (필수 — 못 찾으면 items 합계로 계산),
  "currency":        "KRW",
  "payment_method":  "card | cash | mobile | transfer | other (없으면 null)",
  "category":        "식비 | 카페 | 쇼핑 | 교통 | 의료 | 문화 | 주거 | 기타",
  "items": [
    {"name": "상품명", "quantity": 수량 정수, "price": 단가 정수}
  ]
}

payment_method 판단 기준:
- 신용카드/체크카드/CARD/카드 → "card"
- 현금/CASH → "cash"
- 카카오페이/네이버페이/페이/PAY → "mobile"
- 계좌이체/무통장 → "transfer"
- 나머지 → "other"

category 판단 기준:
- 식당/음식/배달 → "식비"
- 카페/커피/음료 → "카페"
- 마트/편의점/쇼핑몰/의류 → "쇼핑"
- 지하철/버스/택시/주유 → "교통"
- 병원/약국/의원 → "의료"
- 영화/공연/도서/게임 → "문화"
- 관리비/월세/인터넷 → "주거"
- 판단 불가 → "기타"
""".strip()


# ── 핵심 함수 ─────────────────────────────────────────────────────────────────

def extract_receipt_data(ocr_text: str) -> dict:
    """
    OCR 텍스트를 받아 MySQL 스키마에 맞는 dict 반환.
    파싱 실패 시 ValueError 발생.
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"영수증 텍스트:\n{ocr_text}"}
        ],
        temperature=0,           # 정보 추출 → 창의성 불필요
        response_format={"type": "json_object"},  # JSON 모드 강제
    )

    raw = response.choices[0].message.content

    # 방어적 파싱: 혹시 ```json 으로 감싸도 처리
    cleaned = (
        raw.strip()
           .removeprefix("```json")
           .removeprefix("```")
           .removesuffix("```")
           .strip()
    )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패\n원본 응답:\n{raw}") from e


def validate_result(data: dict) -> None:
    """필수 필드 누락 여부 확인."""
    if data.get("total") is None:
        raise ValueError("total 필드가 null입니다. 영수증 이미지를 확인하세요.")

    valid_categories = {"식비","카페","쇼핑","교통","의료","문화","주거","기타"}
    if data.get("category") not in valid_categories:
        raise ValueError(f"유효하지 않은 category: {data.get('category')}")


# ── 실행 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # 나중에 step1_ocr.py 와 합칠 때 full_text 를 인자로 받게 됨
    # 지금은 테스트용 샘플 텍스트 사용
    sample_ocr_text = """
    스타벅스 강남점
    사업자번호: 123-45-67890
    2024-03-15  14:32
    영수증번호: SB-20240315-0042

    아메리카노        1   4,500
    카페라떼          2   5,500
    블루베리머핀      1   4,200

    소계          19,700
    부가세         1,790
    합계          21,490

    카카오페이 결제
    """.strip()

    print("=" * 50)
    print("LLM 분석 중...")
    print("=" * 50)

    data = extract_receipt_data(sample_ocr_text)
    validate_result(data)

    # 결과 출력
    print(f"가게명:      {data.get('store_name')}")
    print(f"날짜:        {data.get('date')}  {data.get('time')}")
    print(f"카테고리:    {data.get('category')}")
    print(f"결제방법:    {data.get('payment_method')}")
    print(f"소계:        {data.get('subtotal'):,}" if data.get('subtotal') else "소계: null")
    print(f"부가세:      {data.get('tax_amount'):,}" if data.get('tax_amount') else "부가세: null")
    print(f"합계:        {data.get('total'):,}")
    print()
    print("품목:")
    for item in data.get("items", []):
        print(f"  - {item['name']:<15} {item['quantity']}개  {item['price']:>7,}원")

    print()
    print("원본 JSON:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
