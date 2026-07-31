import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

# .env에서 값 가져오기
conn = pymysql.connect(
    host=os.environ["DB_HOST"],
    port=int(os.environ["DB_PORT"]),      # 문자열 → 정수 변환 필수
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"],
    charset="utf8mb4",                    # 한글 + 이모지 지원
)

print("✅ MySQL 연결 성공!")

# 테이블 목록 확인
with conn.cursor() as cursor:
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"테이블 목록: {tables}")

    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"MySQL 버전: {version[0]}")

conn.close()
