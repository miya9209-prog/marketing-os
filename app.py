import base64
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlparse

import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="MISHARP 광고문구 자동생성기",
    page_icon="💌",
    layout="wide",
)

COPYRIGHT = "copyright MISHARP COMPANY by MIYAWA. 2026. All rights reserved."
SUBTITLE = "온라인 셀러를 위한 SNS 매체별 최적화 광고문구 자동 생성기"

CHANNEL_LABELS = {
    "sms": "SMS 문자",
    "app_push": "앱푸시",
    "video_script": "동영상 원고",
    "instagram": "인스타 릴스 피드",
    "tiktok": "틱톡 피드",
    "youtube": "유튜브 쇼츠 피드",
    "kakaostyle": "카카오스타일",
    "review": "REVIEW",
}

@dataclass
class MediaAsset:
    kind: str
    name: str
    mime: str
    data: bytes


@dataclass
class GenerationInput:
    product_url: str
    product_text: str
    event_text: str
    selected_channels: List[str]
    sms_mode: str
    media_assets: List[MediaAsset]


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2.5rem;
            max-width: 1320px;
        }
        .misharp-hero {
            border: 1px solid rgba(180, 153, 166, 0.35);
            background: linear-gradient(180deg, #fffafb 0%, #fff 100%);
            border-radius: 22px;
            padding: 30px 30px 24px 30px;
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
        .stButton > button, .stDownloadButton > button, a[data-testid="stLinkButton"] {
            border-radius: 12px !important;
            min-height: 2.8rem !important;
            font-weight: 700 !important;
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
        }        </style>
        """,
        unsafe_allow_html=True,
    )


def default_state() -> Dict[str, Any]:
    return {
        "product_url": "",
        "product_text": "",
        "event_text": "",
        "sms_mode": "장문",
        "channel_sms": True,
        "channel_app_push": True,
        "channel_video_script": True,
        "channel_instagram": True,
        "channel_tiktok": False,
        "channel_youtube": False,
        "channel_kakaostyle": False,
        "channel_review": False,
        "generated_output": "",
        "last_payload": None,
        "media_uploader_nonce": 0,
        "workload_uploader_nonce": 0,
    }


def ensure_state() -> None:
    for key, value in default_state().items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_state() -> None:
    media_nonce = int(st.session_state.get("media_uploader_nonce", 0)) + 1
    workload_nonce = int(st.session_state.get("workload_uploader_nonce", 0)) + 1
    for key, value in default_state().items():
        st.session_state[key] = value
    st.session_state["media_uploader_nonce"] = media_nonce
    st.session_state["workload_uploader_nonce"] = workload_nonce


def get_client() -> OpenAI:
    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def file_to_data_url(mime: str, data: bytes) -> str:
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def sanitize_filename(value: str) -> str:
    value = re.sub(r"\s+", "_", value.strip())
    value = re.sub(r"[^0-9A-Za-z가-힣._-]", "", value)
    value = re.sub(r"_+", "_", value)
    return value[:40].strip("._-") or "work"


def guess_product_label() -> str:
    for raw in [st.session_state.product_text, st.session_state.event_text]:
        for line in raw.splitlines():
            cleaned = line.strip()
            if cleaned:
                return sanitize_filename(cleaned[:40])
    url = st.session_state.product_url.strip()
    if url:
        parsed = urlparse(url)
        host = parsed.netloc.replace("www.", "")
        path = parsed.path.strip("/").split("/")[-1] if parsed.path else ""
        candidate = "_".join([x for x in [host, path] if x])
        if candidate:
            return sanitize_filename(candidate)
    return "work"


def make_work_filename() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"misharp_marketing_os_{guess_product_label()}_{stamp}.json"


def extract_video_frames(asset: MediaAsset, max_frames: int = 3) -> List[MediaAsset]:
    """Best-effort video frame extraction.

    Streamlit Cloud environments sometimes fail to install OpenCV depending on the
    Python runtime. To keep the app stable, this function degrades gracefully and
    simply skips frame extraction when OpenCV is unavailable.
    """
    try:
        import cv2  # type: ignore
    except Exception:
        return []

    suffix = os.path.splitext(asset.name)[1] or ".mp4"
    frames: List[MediaAsset] = []
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(asset.data)
        tmp_path = tmp.name
    try:
        cap = cv2.VideoCapture(tmp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            cap.release()
            return []

        if max_frames <= 1:
            positions = [0.5]
        else:
            positions = [0.15 + (0.70 * i / (max_frames - 1)) for i in range(max_frames)]

        for idx, pos in enumerate(positions, start=1):
            frame_no = min(max(int(total_frames * float(pos)), 0), max(total_frames - 1, 0))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            frames.append(
                MediaAsset(
                    kind="image",
                    name=f"{os.path.splitext(asset.name)[0]}_frame{idx}.jpg",
                    mime="image/jpeg",
                    data=buffer.tobytes(),
                )
            )
        cap.release()
        return frames
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def build_analysis_context(data: GenerationInput) -> str:
    selected = ", ".join(CHANNEL_LABELS[ch] for ch in data.selected_channels)
    return f"""
[프로젝트]
미샵 광고문구 자동 생성기

[사용자 입력]
상품 URL: {data.product_url or '(없음)'}

상품내용:
{data.product_text or '(없음)'}

이벤트 주요내용:
{data.event_text or '(없음)'}

선택 채널: {selected or '(없음)'}
SMS 모드: {data.sms_mode}

[분석 지시]
1. 먼저 입력에서 상품명, 이벤트명, 핵심 장점, 착용 상황, 고객 고민 해결 포인트를 추출한다.
2. 입력이 부족하면 과장하지 말고 확인 가능한 범위에서만 작성한다.
3. 모든 결과는 한국어로 작성한다.
4. 미샵 4050 여성 고객 톤을 유지한다.
5. 상품내용과 이벤트 주요내용은 분리해서 해석하되, 실제 출력에서는 자연스럽게 통합한다.
6. 동영상이 업로드된 경우 대표 프레임 이미지를 참고해 분위기, 핏, 소재감, 활용 장면을 보완 추론하되 과장하지 않는다.
""".strip()


def channel_prompt_sms(mode: str) -> str:
    if mode == "단문":
        return """
[SNS 채널: SMS 문자 - 단문]
- 3가지 시안 작성
- 각 문구는 반드시 정확히 55자 이내
- 반드시 첫 문구를 '(광고)미샵♥'로 시작
- '(광고)'의 괄호를 절대 삭제하지 말 것
- '♥' 다음에는 띄어쓰기 없이 바로 본문을 이어서 작성
- 반드시 문구 끝에 '▶' 포함
- 시작문구와 끝기호를 모두 포함해 55자 이내
- 짧아도 좋으니 절대 55자를 넘기지 말 것
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
- 각 광고문구 첫 시작은 반드시 '광고)'로 시작

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

2) 타입2: 주말한정 MD추천 10%할인
- 헤드라인 30자 이내 5가지
- 광고문구 3종

3) 타입3: 이벤트 입력 기반
- 헤드라인 30자 이내 5가지
- 광고문구 3종
- 이벤트가 없으면 상품 특장점 기반으로 자연스럽게 대체

각 타입의 광고문구 형식에는 반드시 수신거부설정: 알림함-설정버튼 포함
""".strip()


def channel_prompt_video_script() -> str:
    return """
[SNS 채널: 동영상 원고]
당신은 최고의 온라인마케터이자 박웅현, 정철, 최인아와 같은 최고의 카피라이터입니다.
다음 프로젝트 지침대로 작성해주세요.

[프로젝트 목적]
20~30초 길이, 인스타 릴스, 유튜브 쇼츠용 동영상 원고 카피 작성
대한민국 4050 여성 타겟을 겨냥해
'합리적 소비', '스스로 납득할 수 있는 선택'을 유도하는
이성적 + 논리적 + 생활밀착형 브랜드 소구 전략을 사용한다.
"패션 쇼핑호스트"처럼 친근하고 직접 말 걸듯 제안하는 톤을 유지한다.
말투 : 친근한 쇼핑호스트 및 노련한 옷가게 사장언니의 ~해요 체로.

[프롬프트]
1. A/B 2타입으로 작성
2. 각 타입은 짧은 10줄로 구성, 1줄은 20자 내외
3. 임팩트 있는 광고 카피라이팅
4. 첫줄은 후킹성 헤드라인(stick 요소 강하게)이고, 별도로 헤드라인 후보 5개 제안
5. TPO, pain point에 기반해 "~ 분들을 위한 **" 형태를 적극 활용
6. 상단에서는 실생활 공감 pain point를 제시하고, 진행될수록 상품 USP와 연결하여 상품을 어필
7. 여성들이 많이 쓰는 대중적인 의성어·의태어를 자연스럽게 활용
8. 마지막줄은 공감유도 CTA 문구
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


def channel_prompt_kakaostyle() -> str:
    return """
[SNS 채널: 카카오스타일]
프롬프트
카카오스타일 미샵계정 피드 원고 작성
- 최상단: 해당 상품 홍보를 위한 후킹성 헤드라인
- 본내용: 상품명 적고, 한줄 내려서 상품 상세설명 150자 이내 뉴스형식으로 요약
- 본 내용 하단 "상품 바로가기 ▼" 넣기
- 한 줄 띄우고 "일상도 스타일도 미샵처럼, 심플하게! MISHARP" 넣기
- 그 아래 해당 상품 관련 해시태그 30개 삽입
- 해시태그에는 반드시 #미샵 #여성의류쇼핑몰 #중년여성패션 #ootd #데일리룩 #출근룩 포함
- 계절/시기 키워드 2~3개를 상황에 맞게 포함
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
        elif channel == "video_script":
            prompts.append(channel_prompt_video_script())
        elif channel == "instagram":
            prompts.append(channel_prompt_instagram())
        elif channel == "tiktok":
            prompts.append(channel_prompt_tiktok())
        elif channel == "youtube":
            prompts.append(channel_prompt_youtube())
        elif channel == "kakaostyle":
            prompts.append(channel_prompt_kakaostyle())
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


def enforce_sms_short_constraints(text: str) -> str:
    pattern = re.compile(r"(\[SMS 단문 \d\]\n)(.*?)(?=\n\[SMS 단문 \d\]|\n=+|\Z)", re.DOTALL)

    def normalize_line(line: str) -> str:
        line = " ".join(line.strip().split())
        prefix = "(광고)미샵♥"
        if line.startswith("(광고)미샵") and not line.startswith(prefix):
            body = line.replace("(광고)미샵", "", 1).lstrip(" ♥")
            line = prefix + body
        elif not line.startswith(prefix):
            line = prefix + re.sub(r"^\(?광고\)?\s*미샵\s*♥?\s*", "", line)
        line = line.replace(prefix + " ", prefix)
        if not line.endswith("▶"):
            line = line.rstrip("▶ ") + "▶"
        if len(line) > 55:
            core = line[:-1]
            core = core[:54]
            line = core.rstrip() + "▶"
        if len(line) > 55:
            line = line[:55]
            if not line.endswith("▶"):
                line = line[:-1] + "▶"
        return line

    def repl(match: re.Match) -> str:
        header = match.group(1)
        body = match.group(2).strip().splitlines()[0] if match.group(2).strip() else ""
        return header + normalize_line(body) + "\n"

    return pattern.sub(repl, text)



def enforce_app_push_prefix(text: str) -> str:
    if "==============================\n[앱푸시]\n==============================" not in text:
        return text
    pattern = re.compile(r"(\[앱푸시\].*?\n)(.*?)(?=\n==============================|\Z)", re.DOTALL)

    def repl(match: re.Match) -> str:
        header = match.group(1)
        body = match.group(2).strip()
        lines = body.splitlines()
        fixed = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                fixed.append(line)
                continue
            if stripped.startswith(("헤드라인", "타입", "-", "[", "수신거부설정")):
                fixed.append(line)
                continue
            if not stripped.startswith("광고)"):
                stripped = "광고)" + stripped.lstrip(" )")
            fixed.append(stripped)
        return header + "\n".join(fixed) + "\n"

    return pattern.sub(repl, text)


def inject_kakaostyle_url(text: str, url: str) -> str:
    if not url.strip():
        return text
    if "[카카오스타일]" not in text:
        return text
    pattern = re.compile(r"(\[카카오스타일\].*?)(?=\n==============================|\Z)", re.DOTALL)

    def repl(match: re.Match) -> str:
        block = match.group(1)
        if "상품 바로가기 ▼" in block and url in block:
            return block
        if "상품 바로가기 ▼" in block:
            return block.replace("상품 바로가기 ▼", f"상품 바로가기 ▼\n{url}", 1)
        return block.rstrip() + f"\n상품 바로가기 ▼\n{url}\n"
    return pattern.sub(repl, text)

def generate_marketing_copy(data: GenerationInput) -> str:
    client = get_client()
    content: List[Dict[str, Any]] = [{"type": "input_text", "text": compose_master_prompt(data)}]

    for asset in data.media_assets:
        if asset.kind == "image":
            content.append({
                "type": "input_image",
                "image_url": file_to_data_url(asset.mime, asset.data),
                "detail": "auto",
            })
        elif asset.kind == "video":
            for frame in extract_video_frames(asset):
                content.append({
                    "type": "input_image",
                    "image_url": file_to_data_url(frame.mime, frame.data),
                    "detail": "auto",
                })

    fast_model = st.secrets.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    response = client.responses.create(
        model=fast_model,
        input=[{"role": "user", "content": content}],
        max_output_tokens=5000,
    )
    output = response.output_text.strip()
    if data.sms_mode == "단문" and "sms" in data.selected_channels:
        output = enforce_sms_short_constraints(output)
    if "app_push" in data.selected_channels:
        output = enforce_app_push_prefix(output)
    if "kakaostyle" in data.selected_channels:
        output = inject_kakaostyle_url(output, data.product_url)
    return output


def selected_channels_from_state() -> List[str]:
    selected: List[str] = []
    ordered_keys = [
        ("channel_sms", "sms"),
        ("channel_app_push", "app_push"),
        ("channel_video_script", "video_script"),
        ("channel_instagram", "instagram"),
        ("channel_tiktok", "tiktok"),
        ("channel_youtube", "youtube"),
        ("channel_kakaostyle", "kakaostyle"),
        ("channel_review", "review"),
    ]
    for state_key, channel_key in ordered_keys:
        if st.session_state.get(state_key):
            selected.append(channel_key)
    return selected


def make_payload(media_assets: List[MediaAsset]) -> Dict[str, Any]:
    return {
        "product_url": st.session_state.product_url,
        "product_text": st.session_state.product_text,
        "event_text": st.session_state.event_text,
        "sms_mode": st.session_state.sms_mode,
        "channels": selected_channels_from_state(),
        "media_names": [asset.name for asset in media_assets],
    }


def restore_payload(payload: Dict[str, Any]) -> None:
    st.session_state.product_url = payload.get("product_url", "")
    st.session_state.product_text = payload.get("product_text", "")
    st.session_state.event_text = payload.get("event_text", "")
    st.session_state.sms_mode = payload.get("sms_mode", "장문")

    channels = set(payload.get("channels", []))
    st.session_state.channel_sms = "sms" in channels
    st.session_state.channel_app_push = "app_push" in channels
    st.session_state.channel_video_script = "video_script" in channels
    st.session_state.channel_instagram = "instagram" in channels
    st.session_state.channel_tiktok = "tiktok" in channels
    st.session_state.channel_youtube = "youtube" in channels
    st.session_state.channel_kakaostyle = "kakaostyle" in channels
    st.session_state.channel_review = "review" in channels


def render_header() -> None:
    st.markdown(
        f"""
        <div class="misharp-hero">
            <div class="misharp-title">MISHARP 광고문구 자동생성기</div>
            <p class="misharp-subtitle">{SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_controls() -> None:
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        if st.button("초기화", use_container_width=True):
            reset_state()
            st.success("입력값과 생성 결과를 초기화했습니다.")

    with c2:
        saved_data = json.dumps(st.session_state.last_payload or make_payload([]), ensure_ascii=False, indent=2)
        st.download_button(
            "작업 저장",
            data=saved_data.encode("utf-8"),
            file_name=make_work_filename(),
            mime="application/json",
            use_container_width=True,
        )

    with c3:
        with st.popover("작업 불러오기", use_container_width=True):
            uploaded_json = st.file_uploader(
                "작업 불러오기",
                type=["json"],
                key=f"workload_json_{st.session_state.workload_uploader_nonce}",
                help="작업 저장으로 내려받은 JSON 파일을 선택하세요.",
            )
            if uploaded_json is not None and st.button("불러오기 실행", use_container_width=True):
                try:
                    payload = json.load(uploaded_json)
                    restore_payload(payload)
                    st.session_state.last_payload = payload
                    st.success("이전 작업을 불러왔습니다.")
                except Exception as exc:
                    st.error(f"불러오기에 실패했습니다: {exc}")

    with c4:
        st.link_button("이미지추출", "https://misharp-image-crop-v1.streamlit.app/", use_container_width=True)

    with c5:
        st.link_button("URL 단축", "https://shor.kr/", use_container_width=True)



def uploaded_files_to_assets(uploaded_files: List[Any]) -> List[MediaAsset]:
    assets: List[MediaAsset] = []
    for file in uploaded_files:
        mime = file.type or "application/octet-stream"
        kind = "video" if mime.startswith("video/") else "image"
        assets.append(MediaAsset(kind=kind, name=file.name, mime=mime, data=file.getvalue()))
    return assets


def render_inputs() -> List[MediaAsset]:
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown('<div class="misharp-card">', unsafe_allow_html=True)
        st.subheader("입력 정보")
        st.text_input("상품 URL", key="product_url", placeholder="상품 URL 또는 이벤트 링크를 입력하세요")
        st.text_area(
            "상품내용",
            key="product_text",
            height=210,
            placeholder="상세페이지 상품설명, 상품스펙, 소재, 핏, 컬러, 사이즈, USP 등을 입력하세요",
        )
        st.text_area(
            "이벤트 주요내용",
            key="event_text",
            height=140,
            placeholder="세일, 쿠폰, 기간, 증정, 이벤트 메시지 등 별도 이벤트가 있을 때 입력하세요",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="misharp-card">', unsafe_allow_html=True)
        st.subheader("이미지 / 동영상 등록")
        uploads = st.file_uploader(
            "상품 이미지 또는 동영상",
            type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "m4v", "webm", "avi"],
            accept_multiple_files=True,
            key=f"media_uploads_{st.session_state.media_uploader_nonce}",
            help="텍스트 없이 이미지나 동영상만으로도 생성 가능합니다. 동영상은 대표 프레임을 추출해 참고합니다.",
        )
        assets = uploaded_files_to_assets(uploads or [])
        if assets:
            st.caption(f"업로드됨: {len(assets)}개")
            for asset in assets[:4]:
                if asset.kind == "image":
                    st.image(asset.data, use_container_width=True)
                else:
                    st.video(asset.data)
                    st.caption(f"동영상 참고: {asset.name}")
        st.markdown('<p class="misharp-mini">입력값은 URL, 텍스트, 이미지, 동영상 중 1개 이상만 있어도 생성 가능합니다.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    return assets


def render_channel_selector() -> None:
    st.markdown('<div class="misharp-card">', unsafe_allow_html=True)
    st.subheader("출력 채널 선택")
    st.markdown(
        "<span class='pill'>하나만 선택 가능</span><span class='pill'>여러 개 동시 선택 가능</span><span class='pill'>선택한 채널 순서대로 한 파일로 출력</span>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.checkbox("SMS문자(단문,장문)", key="channel_sms")
        st.checkbox("앱푸시", key="channel_app_push")
    with c2:
        st.checkbox("동영상 원고", key="channel_video_script")
        st.checkbox("인스타 릴스 피드", key="channel_instagram")
    with c3:
        st.checkbox("틱톡 피드", key="channel_tiktok")
        st.checkbox("유튜브 쇼츠 피드", key="channel_youtube")
    with c4:
        st.checkbox("카카오스타일", key="channel_kakaostyle")
        st.checkbox("REVIEW", key="channel_review")

    sms_left, _ = st.columns([0.28, 0.72])
    with sms_left:
        st.radio("SMS 유형", ["장문", "단문"], key="sms_mode", horizontal=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_output() -> None:
    st.markdown('<div class="misharp-card">', unsafe_allow_html=True)
    st.subheader("출력 결과")

    output = st.session_state.generated_output.strip()
    if output:
        st.download_button(
            "텍스트 파일 다운로드",
            data=output.encode("utf-8"),
            file_name=f"misharp_marketing_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
        )
        st.code(output, language=None)
    else:
        st.markdown(
            '<div class="misharp-output">아직 생성된 결과가 없습니다. 입력 후 생성 버튼을 눌러주세요.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


def validate_inputs(media_assets: List[MediaAsset]) -> GenerationInput:
    selected_channels = selected_channels_from_state()
    if not selected_channels:
        raise ValueError("최소 1개 이상의 출력 채널을 선택해주세요.")

    has_any_input = bool(
        st.session_state.product_url.strip()
        or st.session_state.product_text.strip()
        or st.session_state.event_text.strip()
        or media_assets
    )
    if not has_any_input:
        raise ValueError("상품 URL, 상품내용, 이벤트 주요내용, 이미지/동영상 중 최소 1개 이상 입력해주세요.")

    return GenerationInput(
        product_url=st.session_state.product_url.strip(),
        product_text=st.session_state.product_text.strip(),
        event_text=st.session_state.event_text.strip(),
        selected_channels=selected_channels,
        sms_mode=st.session_state.sms_mode,
        media_assets=media_assets,
    )


def main() -> None:
    ensure_state()
    inject_css()
    render_header()
    render_controls()
    media_assets = render_inputs()
    render_channel_selector()

    if st.button("광고문구 생성하기", type="primary", use_container_width=True):
        try:
            data = validate_inputs(media_assets)
            st.session_state.last_payload = make_payload(media_assets)
            with st.spinner("광고문구 생성 중입니다..."):
                st.session_state.generated_output = generate_marketing_copy(data)
            st.success("생성이 완료되었습니다.")
        except Exception as exc:
            st.error(str(exc))

    render_output()
    st.markdown(
        f"""
        <div class="misharp-footer">
            <div>{COPYRIGHT}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    p1, p2, _ = st.columns([1, 1, 3])
    with p1:
        st.page_link("pages/1_개인정보_처리방침.py", label="개인정보 처리방침", use_container_width=False)
    with p2:
        st.page_link("pages/2_서비스_약관.py", label="서비스 약관", use_container_width=False)


if __name__ == "__main__":
    main()
