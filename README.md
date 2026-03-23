# MISHARP MARKETING OS

온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기입니다.

## 포함 기능
- 상품 URL / 설명 텍스트 / 이미지 중 1개 이상만으로 생성 가능
- SMS(장문/단문), 앱푸시, 인스타, 틱톡, 유튜브 쇼츠, 리뷰 동시 생성
- 작업 저장(JSON 다운로드) / 작업 불러오기(JSON 업로드)
- 출력 결과 TXT 다운로드
- URL 단축 사이트 바로가기 버튼 포함

## 실행 방법
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets 예시
`.streamlit/secrets.toml`
```toml
OPENAI_API_KEY = "your_api_key_here"
```

## 메모
- Streamlit Cloud는 서버 로컬 저장소가 영구적이지 않아서, "기존 작업 불러오기"는
  JSON 저장/불러오기 방식으로 구현했습니다.
- 추후 Seller OS에 붙일 때는 사용자 계정별 DB 저장 방식으로 확장하면 됩니다.
