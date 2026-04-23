import os
import hashlib
from pathlib import Path
import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    '''
    .env 값으로 MySQL 연결 객체를 생성해서 반환
    이 함수를 호출하는 쪽에서 close() 메서드로 닫아야 함
    '''
    return pymysql.connect(
        host=os.environ["DB_HOST"], # 호스트 이름
        port=int(os.environ["DB_PORT"]), # 포트 번호는 정수로 변환
        user=os.environ["DB_USER"], # 사용자 이름
        password=os.environ["DB_PASSWORD"], # 비밀번호
        database=os.environ["DB_NAME"], # 데이터베이스 이름
        charset="utf8mb4", # 문자 인코딩
    )

def compute_image_hash(image_path: Path) -> str:
    """
    이미지 바이너리를 SHA-256 해시값으로 변환
    같은 영수증 이미지를 두 번 이상 올리지 않도록 함
    """
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ── 핵심 저장 함수 ────────────────────────────────────────────────────────────

def save_receipt(data: dict, image_hash: str | None = None) -> int:
    """
    LLM이 추출한 JSON dict를 2개 테이블에 트랜잭션으로 저장.

    Args:
        data: step2_llm.py의 extract_receipt_data() 반환값
        image_hash: 중복 체크용 (선택)

    Returns:
        생성된 receipt_id (auto_increment PK)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:

            # ── 1. receipts 테이블 INSERT ────────────────────────────────
            receipt_sql = """
                INSERT INTO receipts (
                    store_name, business_number, receipt_number,
                    date, time,
                    subtotal, tax_amount, total, currency,
                    payment_method, category, image_hash
                ) VALUES (
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
            """
            receipt_values = (
                data.get("store_name"),
                data.get("business_number"),
                data.get("receipt_number"),
                data.get("date"),
                data.get("time"),
                data.get("subtotal"),
                data.get("tax_amount"),
                data["total"],                      # NOT NULL — 없으면 KeyError
                data.get("currency", "KRW"),
                data.get("payment_method"),
                data.get("category"),
                image_hash,
            )
            cursor.execute(receipt_sql, receipt_values)
            receipt_id = cursor.lastrowid           # 방금 만든 PK 가져오기
            
            # ── 2. receipt_items 테이블 INSERT (여러 건) ─────────────────
            items = data.get("items", [])
            if items:
                item_sql = """
                    INSERT INTO receipt_items (receipt_id, name, quantity, price)
                    VALUES (%s, %s, %s, %s)
                """
                # executemany: 여러 INSERT를 한 번에 → 네트워크 왕복 최소화
                item_values = [
                    (receipt_id, item["name"], item["quantity"], item["price"])
                    for item in items
                ]
                cursor.executemany(item_sql, item_values)
        conn.commit()
        return receipt_id
    
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"DB 저장 실패: {e}") from e

    finally:
        conn.close()
