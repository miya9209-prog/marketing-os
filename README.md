
# MISHARP 광고문구 자동생성기

## 실행
```bash
streamlit run app.py
```

## 설정
- `OPENAI_API_KEY`를 환경변수 또는 Streamlit Secrets에 설정하세요.
- 선택사항: `OPENAI_MODEL` (기본값 `gpt-4.1-mini`)

## 이번 수정 포인트
- 좌측 사이드바 제거
- 입력 정보 / 이미지 등록 위의 무의미한 박스 제거
- 기존 다크톤 UI 느낌 유지
- 초기화 / 작업 저장 / 작업 불러오기 / 이미지추출 / URL 단축 버튼 정리
