import base64
import io
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any

import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="MISHARP MARKETING OS",
    page_icon="💌",
    layout="wide",
)

COPYRIGHT = "copyright MISHARP COMPANY by MIYAWA. 2026. All rights reservde."
SUBTITLE = "온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기"

CHANNEL_LABELS = {
    "sms": "SMS 문자",
    "app_push": "앱푸시",
    "instagram": "인스타 릴스 피드",
    "tiktok": "틱톡 피드",
    "youtube": "유튜브 숏츠 피드",
    "review": "REVIEW",
}


@dataclass
class GenerationInput:
    product_url: str
    source_text: str
    selected_channels: List[str]
    sms_mode: str
    uploaded_images: List[Any]


# -----------------------------
# Styling
# -----------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
            max-width: 1320px;
        }
        .misharp-hero {
            border: 1px solid rgba(180, 153, 166, 0.35);
            background: linear-gradient(180deg, #fffafb 0%, #fff 100%);
            border-radius: 22px;
            padding: 26px 28px 20px 28px;
            box-shadow: 0 14px 40px rgba(93, 63, 76, 0.08);
            margin-bottom: 18px;
        }
        .misharp-title {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: 0.02em;
            color: #2c1f25;
            margin-bottom: 0.35rem;
        }
        .misharp-subtitle {
            font-size: 1rem;
            color: #745862;
            margin-bottom: 0;
        }
        .misharp-card {
            border: 1px solid rgba(180, 153, 166, 0.25);
            border-radius: 20px;
            padding: 18px;
            background: #ffffff;
            box-shadow: 0 12px 30px rgba(51, 33, 40, 0.05);
        }
        .misharp-mini {
            color: #866873;
            font-size: 0.92rem;
        }
        .misharp-output {
            white-space: pre-wrap;
            font-size: 0.96rem;
            line-height: 1.72;
            background: #fffdfd;
            border: 1px solid rgba(180, 153, 166, 0.25);
            border-radius: 18px;
            padding: 18px;
        }
        .misharp-footer {
            margin-top: 24px;
            padding: 16px 4px 8px 4px;
            color: #7d6670;
            font-size: 0.88rem;
            border-top: 1px solid rgba(180, 153, 166, 0.22);
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 12px !important;
            height: 2.8rem;
            font-weight: 700;
        }
        .pill {
            display:inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background:#fbf1f5;
            border:1px solid rgba(180, 153, 166, 0.25);
            color:#7a5664;
            font-size:0.85rem;
            margin-right:8px;
            margin-bottom:8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Session helpers
# -----------------------------
def default_state() -> Dict[str, Any]:
    return {
        "product_url": "",
        "source_text": "",
        "sms_mode": "장문",
        "channel_sms": True,
        "channel_app_push": True,
        "channel_instagram": True,
        "channel_tiktok": False,
        "channel_youtube": False,
        "channel_review": False,
        "generated_output": "",
        "last_payload": None,
    }


def ensure_state() -> None:
    for key, value in default_state().items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_state() -> None:
    for key, value in default_state().items():
        st.session_state[key] = value


# -----------------------------
# OpenAI helpers
# -----------------------------
def get_client() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def file_to_data_url(uploaded_file: Any) -> str:
    mime = uploaded_file.type or "image/png"
    encoded = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def build_analysis_context(data: GenerationInput) -> str:
    selected = ", ".join(CHANNEL_LABELS[ch] for ch in data.selected_channels)
    return f"""
[프로젝트]
미샵 광고문구 자동 생성기

[사용자 입력]
상품 URL: {data.product_url or '(없음)'}
상품/이벤트 주요 내용:
{data.source_text or '(없음)'}

선택 채널: {selected or '(없음)'}
SMS 모드: {data.sms_mode}

[분석 지시]
1. 먼저 입력에서 상품명, 이벤트명, 핵심 장점, 착용 상황, 고객 고민 해결 포인트를 추출한다.
2. 입력이 부족하면 과장하지 말고 확인 가능한 범위에서만 작성한다.
3. 모든 결과는 한국어로 작성한다.
4. 미샵 4050 여성 고객 톤을 유지한다.
""".strip()


def channel_prompt_sms(mode: str) -> str:
    if mode == "단문":
        return """
[SNS 채널: SMS 문자 - 단문]
- 3가지 시안 작성
- 한글 56자 이내
- 반드시 '(광고)미샵♥'로 시작
- 반드시 문구 끝에 '▶' 포함
- 시작문구와 끝기호 포함 총 56자 이내
- 후킹성, 신선함, 긴박감은 넣되 과장 금지
- 링크를 넣는 경우에도 56자 이내를 지킬 것
- 결과 형식:
[SMS 단문 1]
...
[SMS 단문 2]
...
[SMS 단문 3]
...
""".strip()
    return """
[SNS 채널: SMS 문자 - 장문]
- 3가지 시안 작성
- 제목 형식: (광고)미샵 "이벤트명"
- 본문은 후킹성과 구매전환율이 높게 작성하되 광고티가 과하지 않게 작성
- 아래 고정 문구를 반드시 하단에 그대로 넣을 것

※혹시 피싱문자 우려되신다면 네이버 검색창에 "미샵" 검색 후 클릭하셔서 주말이벤트 확인해주세요:)

♡일상을 위한 데일리룩, 출근룩 쇼핑에 꼭 활용해보세요.

일상도 스타일도 미샵처럼, 심플하게! MISHARP

♡지금 미샵 바로가기
http://misharp.co.kr

♡요즘 핫한 미샵 인스타그램, 지금 만나보세요:)(@misharp2006)

♡유튜브 미샵TV, 틱톡, 카카오스토리에서 미샵의 다양한 컨텐츠를 만나보세요:)

M  I  S  H  A  R  P

- 결과 형식:
[SMS 장문 1]
제목: ...
본문:
...

[SMS 장문 2]
...

[SMS 장문 3]
...
""".strip()


def channel_prompt_app_push() -> str:
    return """
[SNS 채널: 앱푸시]
아래 규칙을 엄격히 지켜 작성한다.

[공통 작성 원칙]
❌ 하지 말 것
- 할인율(%, 전상품)을 문구 첫 문장에 바로 노출하지 말 것
- 과도한 느낌표, 자극적인 홈쇼핑 말투 금지
- 정보 나열형 문구 금지
- 광고내용에 상품명은 [ ]로 구분. 광고문구에 상품명 1번만 사용

✅ 반드시 지킬 것
- 문구 구조: 상황 공감 → 이유 제시 → 행동 유도
- 4050 여성이 실제로 쓰는 말투
- MD 추천의 신뢰감
- 아래 키워드 중 최소 1개 이상 자연스럽게 반영
  (붙지 않음 / 체형커버 / 오래 입음 / 코디 쉬움 / 자주 손이 감)
- 문장은 부드럽고 담담하게, 그러나 선택은 분명하게

[출력]
1) 타입1: 24시간 MD추천 10%할인
- 헤드라인 30자 이내 5가지
- 광고문구 3종
- 형식:
[앱푸시 타입1]
헤드라인 후보:
1. ...
2. ...
3. ...
4. ...
5. ...

광고문구 1:
광고)24시간 MD추천 10%할인 [상품명]
(푸시 문구 – 한글 50자 이내)
수신거부설정: 알림함-설정버튼

광고문구 2:
...
광고문구 3:
...

2) 타입2: 주말한정 MD추천 10%할인
- 헤드라인 30자 이내 5가지
- 광고문구 3종
- 형식:
[앱푸시 타입2]
헤드라인 후보:
1. ...
2. ...
3. ...
4. ...
5. ...

광고문구 1:
광고)주말한정 MD추천 10%할인 [상품명]
(푸시 문구 – 한글 50자 이내)
수신거부설정: 알림함-설정버튼

광고문구 2:
...
광고문구 3:
...

3) 타입3: 이벤트 입력 기반
- 헤드라인 30자 이내 5가지
- 광고문구 3종
- 형식:
[앱푸시 타입3]
헤드라인 후보:
1. ...
2. ...
3. ...
4. ...
5. ...

광고문구 1:
광고) [이벤트명] + 광고문구 + 수신거부설정: 알림함-설정버튼
- 총 100자 이내

광고문구 2:
...
광고문구 3:
...
""".strip()


def channel_prompt_instagram() -> str:
    return """
[SNS 채널: 인스타 릴스 피드]
- 상품 원고를 바탕으로 15줄 작성
- 첫째줄: 헤드라인
- 둘째줄: 미샵 상품명
- 4050 여성 공감 포인트 반영
- 진짜 사람이 말하는 듯한 친근한 여성 어투
- 마지막 줄은 CTA 문구
- 그 다음 한 줄 띄우고 해시태그 5개
  (#미샵 을 제일 앞에, 나머지 4개 해시태그)
- 그 다음 한 줄 띄우고 아래 2줄 고정
  자세한 상품정보는 상단 프로필 링크 참조
  일상도 스타일도 미샵처럼, 심플하게! MISHARP
- 이모지 금지
""".strip()


def channel_prompt_tiktok() -> str:
    return """
[SNS 채널: 틱톡 피드]
- 상품 원고를 바탕으로 15줄 작성
- 첫째줄: 헤드라인
- 둘째줄: 미샵 상품명
- 4050 여성 공감 포인트 반영
- 진짜 사람이 말하는 듯한 친근한 여성 어투
- 마지막 줄은 CTA 문구
- 그 다음 한 줄 띄우고 해시태그 5개
  (#미샵 을 제일 앞에, 나머지 4개 해시태그)
- 그 다음 한 줄 띄우고 아래 2줄 고정
  자세한 상품정보는 하단 상품링크 또는 상단 프로필 링크 참조
  일상도 스타일도 미샵처럼, 심플하게! MISHARP
- 이모지 금지
""".strip()


def channel_prompt_youtube() -> str:
    return """
[SNS 채널: 유튜브 숏츠 피드]
- 타이틀 100자 이내
- 후킹성 강한 타이틀 다음에 해시태그 8~10개 포함
- 반드시 #미샵 #shorts #ootd 포함
- 설명 피드 작성: 상품내용 공감형, TPO 담아 설명글 작성
- 마지막에 CTA 문구
- 최하단에 아래 문구 고정
  상세한 상품정보는 영상 하단 상품배너 클릭
- 그 아래 상품 해시태그 10개 작성
""".strip()


def channel_prompt_review() -> str:
    return """
[SNS 채널: REVIEW]
- 총 10개 작성
- 긴글 5개, 짧은 글 5개
- 50자 ~ 300자 내외
- 4050대 일반인 여성이 쓴 듯한 일상적 문체
- 배송받아 처음 입어본 소감 톤
- 패션 전문용어 금지
- 각 후기 시작은 반드시 (키/몸무게) 형식
- 키는 155cm~163cm, 몸무게는 52kg~63kg 범위
- 작성자 10명 성격과 말투가 전부 다르게
- 체형 대비 만족감, 품질, 구매경험, 활용성, 가성비 반영
- ㅎㅎ, ~~, ^^, :) 등을 적절히 사용
- 배송이 빨랐다 / 미샵에서 사길 잘했다는 맥락 적절히 혼합
- 후기글에 제목 금지
- 후기글에 상품명 금지
""".strip()


def compose_master_prompt(data: GenerationInput) -> str:
    prompts = [build_analysis_context(data)]
    for channel in data.selected_channels:
        if channel == "sms":
            prompts.append(channel_prompt_sms(data.sms_mode))
        elif channel == "app_push":
            prompts.append(channel_prompt_app_push())
        elif channel == "instagram":
            prompts.append(channel_prompt_instagram())
        elif channel == "tiktok":
            prompts.append(channel_prompt_tiktok())
        elif channel == "youtube":
            prompts.append(channel_prompt_youtube())
        elif channel == "review":
            prompts.append(channel_prompt_review())

    prompts.append(
        """
[최종 출력 규칙]
- 선택된 채널만 순서대로 출력
- 각 채널 시작 시 반드시 아래 형식으로 구분선 표기
==============================
[채널명]
==============================
- 불필요한 해설, 메모, 자기평가 금지
- 결과만 바로 출력
""".strip()
    )
    return "\n\n".join(prompts)


def generate_marketing_copy(data: GenerationInput) -> str:
    client = get_client()

    content: List[Dict[str, Any]] = [
        {
            "type": "input_text",
            "text": compose_master_prompt(data),
        }
    ]

    for image in data.uploaded_images:
        content.append(
            {
                "type": "input_image",
                "image_url": file_to_data_url(image),
                "detail": "auto",
            }
        )

    response = client.responses.create(
        model="gpt-5",
        input=[
            {
                "role": "user",
                "content": content,
            }
        ],
    )
    return response.output_text.strip()


# -----------------------------
# UI helpers
# -----------------------------
def selected_channels_from_state() -> List[str]:
    selected: List[str] = []
    if st.session_state.channel_sms:
        selected.append("sms")
    if st.session_state.channel_app_push:
        selected.append("app_push")
    if st.session_state.channel_instagram:
        selected.append("instagram")
    if st.session_state.channel_tiktok:
        selected.append("tiktok")
    if st.session_state.channel_youtube:
        selected.append("youtube")
    if st.session_state.channel_review:
        selected.append("review")
    return selected


def make_payload(uploaded_images: List[Any]) -> Dict[str, Any]:
    return {
        "product_url": st.session_state.product_url,
        "source_text": st.session_state.source_text,
        "sms_mode": st.session_state.sms_mode,
        "channels": selected_channels_from_state(),
        "image_names": [img.name for img in uploaded_images],
    }


def restore_payload(payload: Dict[str, Any]) -> None:
    st.session_state.product_url = payload.get("product_url", "")
    st.session_state.source_text = payload.get("source_text", "")
    st.session_state.sms_mode = payload.get("sms_mode", "장문")

    channels = set(payload.get("channels", []))
    st.session_state.channel_sms = "sms" in channels
    st.session_state.channel_app_push = "app_push" in channels
    st.session_state.channel_instagram = "instagram" in channels
    st.session_state.channel_tiktok = "tiktok" in channels
    st.session_state.channel_youtube = "youtube" in channels
    st.session_state.channel_review = "review" in channels


def render_header() -> None:
    st.markdown(
        f"""
        <div class="misharp-hero">
            <div class="misharp-title">MISHARP MARKETING OS</div>
            <p class="misharp-subtitle">{SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_controls() -> None:
    c1, c2, c3, c4 = st.columns([1.15, 1.1, 0.8, 0.95])

    with c1:
        saved_data = json.dumps(st.session_state.last_payload or default_state(), ensure_ascii=False, indent=2)
        st.download_button(
            "현재 작업 저장",
            data=saved_data.encode("utf-8"),
            file_name="misharp_marketing_os_work.json",
            mime="application/json",
            use_container_width=True,
        )

    with c2:
        uploaded_json = st.file_uploader(
            "기존 작업 불러오기",
            type=["json"],
            label_visibility="collapsed",
            key="workload_json",
        )
        if uploaded_json is not None:
            if st.button("불러오기", use_container_width=True):
                try:
                    payload = json.load(uploaded_json)
                    restore_payload(payload)
                    st.session_state.last_payload = payload
                    st.success("이전 작업을 불러왔습니다.")
                except Exception as exc:
                    st.error(f"불러오기에 실패했습니다: {exc}")

    with c3:
        if st.button("초기화", use_container_width=True):
            reset_state()
            st.success("입력값과 생성 결과를 초기화했습니다.")

    with c4:
        st.link_button("URL 단축 바로가기", "https://shor.kr/", use_container_width=True)


def render_inputs() -> List[Any]:
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown('<div class="misharp-card">', unsafe_allow_html=True)
        st.subheader("입력 정보")
        st.text_input("상품 URL", key="product_url", placeholder="상품 URL 또는 이벤트 링크를 입력하세요")
        st.text_area(
            "상품, 이벤트 주요 내용",
            key="source_text",
            height=300,
            placeholder="상품명, 특징, 세일 정보, 타겟 고객, 강조 포인트 등을 자유롭게 입력하세요",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="misharp-card">', unsafe_allow_html=True)
        st.subheader("이미지 등록")
        images = st.file_uploader(
            "상품 이미지 또는 이벤트 배너",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="image_uploads",
            help="텍스트 없이 이미지 만으로도 분석 가능하도록 설계했습니다.",
        )
        if images:
            st.caption(f"업로드됨: {len(images)}장")
            preview_cols = st.columns(min(3, len(images)))
            for i, img in enumerate(images[:3]):
                with preview_cols[i % len(preview_cols)]:
                    st.image(img, use_container_width=True)
        st.markdown('<p class="misharp-mini">입력값은 URL, 텍스트, 이미지 중 1개 이상만 있어도 생성 가능합니다.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    return images or []


def render_channel_selector() -> None:
    st.markdown('<div class="misharp-card">', unsafe_allow_html=True)
    st.subheader("출력 채널 선택")
    st.markdown(
        "<span class='pill'>하나만 선택 가능</span><span class='pill'>여러 개 동시 선택 가능</span><span class='pill'>선택한 채널 순서대로 한 파일로 출력</span>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.checkbox("SMS 문자", key="channel_sms")
    with c2:
        st.checkbox("앱푸시", key="channel_app_push")
    with c3:
        st.checkbox("인스타 릴스 피드", key="channel_instagram")
    with c4:
        st.checkbox("틱톡 피드", key="channel_tiktok")
    with c5:
        st.checkbox("유튜브 숏츠 피드", key="channel_youtube")
    with c6:
        st.checkbox("REVIEW", key="channel_review")

    sms_left, sms_right = st.columns([0.3, 0.7])
    with sms_left:
        st.radio("SMS 유형", ["장문", "단문"], key="sms_mode", horizontal=True)
    with sms_right:
        st.caption("SMS 채널 선택 시에만 적용됩니다. 단문은 56자 제한 규칙을 적용합니다.")

    st.markdown('</div>', unsafe_allow_html=True)


def render_output() -> None:
    st.markdown('<div class="misharp-card">', unsafe_allow_html=True)
    st.subheader("출력 결과")

    output = st.session_state.generated_output.strip()
    if output:
        st.download_button(
            "텍스트 파일 다운로드",
            data=output.encode("utf-8"),
            file_name="misharp_marketing_output.txt",
            mime="text/plain",
        )
        st.code(output, language=None)
    else:
        st.markdown(
            '<div class="misharp-output">아직 생성된 결과가 없습니다. 입력 후 생성 버튼을 눌러주세요.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


def validate_inputs(images: List[Any]) -> GenerationInput:
    selected_channels = selected_channels_from_state()
    if not selected_channels:
        raise ValueError("최소 1개 이상의 출력 채널을 선택해주세요.")

    has_any_input = bool(st.session_state.product_url.strip() or st.session_state.source_text.strip() or images)
    if not has_any_input:
        raise ValueError("상품 URL, 주요 내용, 이미지 중 최소 1개 이상 입력해주세요.")

    return GenerationInput(
        product_url=st.session_state.product_url.strip(),
        source_text=st.session_state.source_text.strip(),
        selected_channels=selected_channels,
        sms_mode=st.session_state.sms_mode,
        uploaded_images=images,
    )


def main() -> None:
    ensure_state()
    inject_css()
    render_header()
    render_controls()
    uploaded_images = render_inputs()
    render_channel_selector()

    if st.button("광고문구 생성하기", type="primary", use_container_width=True):
        try:
            data = validate_inputs(uploaded_images)
            st.session_state.last_payload = make_payload(uploaded_images)
            with st.spinner("미샵 톤으로 광고문구를 생성하고 있습니다..."):
                st.session_state.generated_output = generate_marketing_copy(data)
            st.success("생성이 완료되었습니다.")
        except Exception as exc:
            st.error(str(exc))

    render_output()

    st.markdown(
        f"""
        <div class="misharp-footer">
            <div>{COPYRIGHT}</div>
            <div style="margin-top:6px;">개인정보 처리방침 · 서비스 약관</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
