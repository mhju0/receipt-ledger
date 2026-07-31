# Receipt Ledger

한국어 영수증 이미지를 OCR로 읽고, LLM으로 구조화한 뒤 MySQL에 적재하는 파이프라인입니다.

## License

Copyright (c) 2026 Michael Ju. All rights reserved.
No license is granted for use, copying, modification, or distribution of this code as of 2026-07-30. This repository is public for portfolio review purposes only.

## Pipeline

- `step1_ocr.py` — 영수증 이미지에서 텍스트 추출
- `step2_llm.py` — OCR 텍스트를 구조화된 JSON으로 변환
- `step3_db.py` — 추출 결과를 MySQL에 적재
- `test_db_connection.py` — DB 연결 확인용 스크립트

## Setup

```sh
pip install -r requirements.txt
```

`OPENAI_API_KEY`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` 을
`.env` 에 설정하세요. `.env` 는 커밋되지 않습니다.
