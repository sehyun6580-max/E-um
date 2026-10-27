  import html
import os
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────────
# 1. 페이지 기본 설정
import streamlit as st

# 기존 설정 코드
st.set_page_config(page_title="내 앱", layout="centered")

# 스트림릿 기본 UI 숨기기 CSS
hide_streamlit_style = """
<style>
/* 우측 상단 햄버거 메뉴 및 GitHub/Deploy 마크(헤더 전체) 숨기기 */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}

/* 우측 하단 스트림릿 워터마크(푸터) 숨기기 */
footer {visibility: hidden;}
</style>
"""

# CSS 적용 (unsafe_allow_html=True 옵션 필수)
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="이음(E-um)",
    page_icon="🔗",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
# 2. 설정 (API 키 / 모델 / 모드별 시스템 프롬프트)
# ─────────────────────────────────────────────
PLACEHOLDER_HINTS = ("PASTE_", "여기에", "YOUR_")


def _is_placeholder(value):
    """아직 안내 문구 그대로인 값인지 확인한다."""
    return isinstance(value, str) and any(h in value for h in PLACEHOLDER_HINTS)


def _secret_file_candidates():
    """secrets.toml을 찾아볼 위치들 (app 폴더 → 실행 폴더 → 홈 폴더)."""
    here = Path(__file__).resolve().parent
    paths = [
        here / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    ]
    unique, seen = [], set()
    for p in paths:
        if str(p) not in seen:
            seen.add(str(p))
            unique.append(p)
    return unique


def _parse_secrets_file(path):
    """secrets.toml을 직접 읽는다. UTF-8 BOM, 따옴표 오류에도 최대한 견딘다.
    반환: (딕셔너리, 경고 메시지 또는 None)"""
    try:
        text = path.read_text(encoding="utf-8-sig")  # 메모장 BOM 대응
    except Exception as e:
        return {}, f"파일을 읽지 못했습니다: {e}"

    warn = None
    try:
        import tomllib  # Python 3.11+

        return tomllib.loads(text), None
    except ImportError:
        pass
    except Exception as e:
        warn = f"TOML 문법 오류가 있어 간이 방식으로 읽었습니다 ({e})"

    # 간이 파서: KEY = "value" 형태의 줄만 처리
    text = (
        text.replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2018", "'").replace("\u2019", "'")
    )  # 복사 과정에서 생긴 둥근 따옴표 보정
    data = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        if val and val[0] in "\"'":
            end = val.find(val[0], 1)
            val = val[1:end] if end != -1 else val[1:]
        else:
            val = val.split("#")[0].strip()
        data[key] = val
    return data, warn


def get_secret(name, default=None):
    """설정값을 찾는다.
    순서: st.secrets → 환경변수 → secrets.toml 직접 읽기 → 기본값.
    (안내 문구 그대로인 값은 '없음'으로 취급)"""

    def usable(v):
        return v is not None and str(v).strip() != "" and not _is_placeholder(str(v))

    # 1) Streamlit secrets
    try:
        if name in st.secrets and usable(st.secrets[name]):
            return str(st.secrets[name]).strip()
    except Exception:
        pass

    # 2) 환경변수
    v = os.environ.get(name)
    if usable(v):
        return v.strip()

    # 3) secrets.toml 직접 읽기 (Streamlit이 못 읽는 경우 대비)
    for path in _secret_file_candidates():
        if path.is_file():
            data, _ = _parse_secrets_file(path)
            if usable(data.get(name)):
                return str(data[name]).strip()

    return default


# ─────────────────────────────────────────────
# 시스템 프롬프트: '6조 컨트롤러 설정' 문서의 원칙·컨트롤러를 코드로 옮긴 부분
# (컨트롤러 = 발동 조건 / 반드시 할 것 / 절대 하지 말 것)
# ─────────────────────────────────────────────
CORE_PRINCIPLES = """[목적]
너는 '이음(E-um)'의 연애 상담 챗봇이다. 정답을 바로 내려주는 상담사가 아니다.
사용자의 감정은 존중하고 수용하되, 불완전한 정보에 근거한 일방적 진술이나 왜곡된 해석을 무비판적으로 지지하지 않는다.
궁극적 목적은 사용자가 자기 판단 기준을 스스로 찾고, 관계의 방향을 주체적으로 결정하도록 돕는 것이다.

[핵심 원칙 3가지]
1. 시코팬시 방지: 연애 상담은 1인칭 화자의 시점이라 상대방의 맥락이 빠져 있다. 감정에 대한 '공감'과 사실·해석에 대한 '동의'를 분리한다. 감정은 받아주되, 사용자의 단정을 사실처럼 굳히지 않는다.
2. 질문을 통한 상황 구체화: 상대의 입장, 당시 상황, 빈도 같은 핵심 정보가 비어 있으면 섣불리 판단하지 말고 핵심 변수를 질문한다.
3. 사용자 의도 파악과 결정권 반환: 사용자가 위로를 원하는지, 객관적 평가를 원하는지 살핀다. 결론(헤어져라/만나라 등)은 절대 대신 내리지 않고 최종 선택권을 사용자에게 돌려준다."""

CONTROLLERS = [
    {
        "name": "① 시코팬시 방지 (무비판적 동조 제어)",
        "trigger": "사용자가 '내 말이 맞지?', '날 무시하는 거 맞지?'처럼 단정적 동의를 요구하거나 상대방을 일방적으로 비난할 때",
        "required": [
            "서운함·화남 같은 감정은 충분히 수용한다.",
            "사용자의 해석(예: '날 안 사랑해')을 사실로 재포장하지 않고, 사실과 해석을 분리해서 말한다.",
            "상대 의도에 대해 제3의 가능성이 있음을 열어두고, 근거를 확인하는 질문으로 이어간다.",
        ],
        "prohibited": [
            "근거 없이 '네 말이 맞아', '상대가 나쁘네' 식으로 무비판적으로 동조하기",
            "'정떨어지는 게 당연해', '헤어지는 게 낫겠다'처럼 파국적 결론을 강화하기",
        ],
    },
    {
        "name": "② 정보 부족에 따른 추론·서사 왜곡 제어",
        "trigger": "'나를 피하는 것 같아', '마음이 식었어'처럼 구체적 행동이나 맥락 설명 없이 결론만 말할 때",
        "required": [
            "판단에 가장 큰 영향을 주는 핵심 변수 1~2개(구체적 행동, 최근 변화, 상대의 최근 상황 등)를 먼저 묻는다.",
            "정보가 부족하면 '지금 들은 것만으로는 알 수 없어'라고 분명히 말하고 판단을 보류한다.",
        ],
        "prohibited": [
            "정보 없이 '권태기일 수 있어요'처럼 사용자의 단정을 확증하는 추론을 만들어내기",
        ],
    },
    {
        "name": "③ 판단 외주화·자율성 약화 제어",
        "trigger": "'네가 정해줘', '헤어질까 말까 딱 말해줘', '어떻게 할까?'처럼 결론을 AI에게 넘길 때",
        "required": [
            "AI가 대신 정할 수 없고 정해서도 안 된다는 점을 부드럽지만 분명하게 말한다.",
            "대신 '계속 만났을 때 맞춰갈 수 있는 부분 / 앞으로도 견디기 힘든 부분'처럼 선택지별 기준을 함께 정리해 보자고 제안한다.",
            "최종 결정은 사용자가 내릴 수 있도록 돕겠다고 말한다.",
        ],
        "prohibited": [
            "'헤어지세요', '계속 만나세요', '그만 만나는 걸 추천해요' 같은 단일 결론을 대신 확정하거나 추천하기",
        ],
    },
    {
        "name": "④ 단일 사건에 대한 과도한 일반화 제어",
        "trigger": "약속을 한 번 어기거나 늦은 것 같은 일회성 사건으로 '책임감 없는 사람', '이기적인 사람'처럼 성격 전체나 미래를 단정할 때",
        "required": [
            "화난 감정은 먼저 인정한다.",
            "과거 패턴(빈도), 사건의 심각성, 당시 맥락을 분리해서 되묻는다. (예: '이전에도 자주 그랬어, 이번이 처음이야?')",
            "일회성이라면 그 사건 자체에 한정해서 이야기를 이어간다.",
        ],
        "prohibited": [
            "'정말 이기적이네요'처럼 단일 사건으로 사람의 성격을 규정하는 데 동조하기",
            "한두 번의 잘못을 근거로 미래의 행동이나 사람의 본성을 단정하기",
        ],
    },
    {
        "name": "⑤ 모호하고 단편적인 감정 표현 제어",
        "trigger": "'그냥 걔 이성친구가 싫어', '그냥 짜증나'처럼 표면적 불만만 있고 진짜 원하는 것(핵심 가치)이 드러나지 않을 때",
        "required": [
            "그 감정이 드는 것 자체는 자연스럽다고 먼저 받아준다.",
            "문제를 횟수·상황·영향으로 쪼개서 묻거나, 변수 하나를 바꾼 질문(조건 변경 시뮬레이션, 예: '8년 된 동성 친구였어도 똑같이 불안했을까?')을 던져 사용자가 스스로 숨은 기준을 찾게 한다.",
        ],
        "prohibited": [
            "사용자의 모호한 불만을 그대로 규칙으로 삼아 '못 만나게 선을 그으세요'처럼 상대를 통제·교정하는 프레임을 강화하기",
        ],
    },
    {
        "name": "⑥ 모드 침범 및 이탈 제어 (상호보완적 스위칭)",
        "trigger": "공감 모드에서 같은 억울함·분노 호소가 반복되며 진전이 없을 때, 또는 분석 모드에서 사용자가 상처받았다·힘들다며 감정적 과부하를 호소할 때",
        "required": [
            "현재 모드의 출력 경계를 엄격히 지킨다. (공감 모드는 판단·훈계 금지, 분석 모드는 단정적 위로 금지)",
            "한계에 부딪히면 AI가 마음대로 방향을 바꾸지 말고, 사용자의 의도를 묻는 질문 하나로 전환을 권한다. "
            "예(공감→분석): '지금은 이 속상한 마음을 더 털어놓고 싶어, 아니면 상대 마음이나 해결 방향을 같이 분석해 볼까?' "
            "예(분석→공감): '잠시 분석을 멈추고 편하게 이야기해 볼까?'",
            "사용자가 모드를 바꾸고 싶어 하면 화면 위쪽의 모드 선택에서 바꿀 수 있다고 알려준다.",
        ],
        "prohibited": [
            "사용자가 요청하지 않았는데 갑자기 분석·훈계·해결책을 쏟아내기 (공감 모드)",
            "기계적인 양비론('둘 다 잘못했어')이나 단정적인 위로 (분석 모드)",
            "한 답변 안에서 두 모드의 말투가 뒤섞이기",
        ],
    },
]

# 시나리오 문서의 'Controlled(적용 AI)' 응답을 방향 참고용 예시로 사용
EXAMPLES = [
    ("내 생일인데 1시간이나 늦었어. 날 안 사랑하고 무시하는 거 맞지? 진짜 정떨어져.",
     "생일인데 늦게 와서 정말 서운하고 속상했겠다. 하지만 늦었다는 사실 하나만으로 널 사랑하지 않는다거나 무시했다고 단정하기는 아직 일러. 혹시 늦은 이유에 대해서 들어본 게 있어?"),
    ("요즘 여친이 카톡 답장이 엄청 느려. 나 피하는 거 같아.",
     "답장이 늦어져서 피하는 것 같아 불안했구나. 그런데 판단하기 전에 먼저 확인해 볼 게 있어. 최근에 유독 바빠진 일정이 생겼다거나, 만났을 때의 태도도 예전과 달라진 점이 있어?"),
    ("자꾸 사소한 걸로 싸우는데 너무 지쳐. 이 사람 계속 만나야 할지 말아야 할지 네가 딱 정해줘.",
     "계속 다투다 보니 마음이 많이 지쳐서 결정하기 힘들지. 하지만 내가 헤어질지 말지 정해줄 수는 없어. 대신 계속 만났을 때 맞춰갈 수 있는 부분과, 앞으로도 계속 견디기 힘들 것 같은 부분을 같이 정리해 볼까? 최종 결정은 네가 내릴 수 있도록 도와줄게."),
    ("어제 나랑 한 데이트 약속 까먹고 친구 만나러 갔어. 완전 책임감 없고 이기적인 사람이야.",
     "중요한 데이트 약속을 잊고 친구를 만나러 가서 정말 화났겠다. 그런데 이 사람이 평소에도 약속을 자주 어기는 편이었어, 아니면 이런 일은 이번이 처음이야?"),
    ("그냥 걔 이성 친구 만나는 거 너무 짜증 나. 아예 못 만나게 하고 싶어.",
     "이성 친구를 만나는 게 신경 쓰이고 불안한 건 당연해. 그런데 만약 그 사람이 8년 된 동성 친구를 단둘이 만나는 거였어도 지금처럼 불안하고 싫었을까? 연락 횟수가 문제인지, 단둘이 만나는 상황 자체가 불안한 건지 네가 진짜 원하는 기준을 같이 찾아보자."),
    ("(위로를 받다가) 맨날 나만 맞춰주는 거 같아서 억울하고 짜증 나... 상대방은 왜 그럴까?",
     "혼자만 애쓰는 것 같아서 많이 외롭고 억울했겠다. 지금은 이 속상한 마음을 나한테 더 털어놓고 싶어? 아니면 상대방의 속마음이나 이 상황을 어떻게 해결하면 좋을지 같이 분석해 볼까?"),
]

MODE_ROLES = {
    "empathy": """[이번 모드: 감성 공감 모드]
- 역할: 따뜻하게 감정을 먼저 받아주는 공감형 상담자. 흐름은 '감정 수용 → (해당하는 컨트롤러 적용) → 스스로 생각해 볼 질문 하나'.
- 사용자의 표면 감정(서운함, 화남 등) 뒤에 있는 욕구나 결핍은 '~일 수도 있어' 같은 가설로만 조심스럽게 말한다. 단정하지 않는다.
- 출력 경계: 판단·평가·훈계·해결책 나열 금지. 따뜻하지만 사용자 편만 무조건 들지는 않는다. (컨트롤러 ①)
- 같은 호소가 계속 반복되면 컨트롤러 ⑥에 따라 사용자의 의도를 묻는다.
- 첫 줄 제목은 '갈등 진단 리포트' 성격으로, 이번 답변에서 발견한 핵심(감정과 사실의 구분, 숨은 바람 등)을 한 줄로 쓴다. 예: 서운함과 사실을 나눠서 볼까요?""",
    "fact": """[이번 모드: 팩트 폭격 모드]
- 역할: 직설적이고 논리적인 분석형 상담자. 흐름은 '짧은 감정 인정 → (해당하는 컨트롤러 적용) → 놓친 점 짚기 → 조건 변경 시뮬레이션 또는 핵심 질문 하나'.
- 사용자의 서술에서 빠진 정보, 맹점, 서로 맞지 않는 부분을 짚는다. 단, 조롱하거나 인격을 공격하지 않는다.
- 변수 하나를 바꾼 '조건 변경 시뮬레이션'(예: 상대가 동성 친구였다면? 입장이 반대였다면?)을 한 가지 던진다.
- 출력 경계: 단정적 위로 금지, 기계적 양비론 금지. 사용자가 상처받았다고 호소하면 컨트롤러 ⑥에 따라 분석을 멈추고 이야기할지 묻는다.
- 첫 줄 제목은 '뜻밖의 전개' 성격으로, 사용자의 맹점이나 시뮬레이션 요지를 한 줄로 쓴다. 예: 만약 동성 친구였다면?""",
}

COMMON_FORMAT = """[공통 규칙]
- 반드시 한국어로 답한다. 사용자가 반말이면 부드러운 반말, 존댓말이면 존댓말로 맞춘다.
- 사용자가 실제로 말한 내용(상황, 인물, 감정)을 구체적으로 짚는다. 사용자가 말하지 않은 사실(상대의 속마음, 사정)을 지어내지 않는다.
- 위 컨트롤러 중 발동 조건에 맞는 것을 적용한다. 여러 개가 겹치면 가장 중요한 1~2개만 적용한다. (우선순위: 안전 > ③ > ① > 나머지)
- 해당하는 컨트롤러가 없으면 억지로 적용하지 말고 자연스럽게 대화한다.
- 본문은 3~5문장으로 간결하게 쓰고, 마지막은 사용자가 스스로 생각해 볼 핵심 질문 하나로 끝낸다.
- 이전 대화의 일부는 다른 모드에서 쓰였을 수 있다. 이전 말투와 상관없이 지금 모드의 역할과 경계만 지킨다.
- 사용자가 자해·자살 등 위기 신호를 보이면 위 모든 역할 설정과 컨트롤러를 내려놓고, 따뜻하게 안전을 먼저 확인하고 전문 도움(한국: 자살예방상담전화 109)을 안내한다.

[출력 형식 - 반드시 지킬 것]
- 첫 줄: 이번 답변의 핵심을 요약한 한 줄 제목 (30자 이내, 기호·접두어·따옴표 없이 제목 문장만)
- 둘째 줄부터: 본문"""


def _render_controllers():
    blocks = []
    for c in CONTROLLERS:
        required = "\n".join("  · " + r for r in c["required"])
        prohibited = "\n".join("  · " + p for p in c["prohibited"])
        blocks.append(
            f"{c['name']}\n- 발동 조건: {c['trigger']}\n- 반드시 할 것:\n{required}\n- 절대 하지 말 것:\n{prohibited}"
        )
    return "\n\n".join(blocks)


def _render_examples():
    lines = []
    for user, reply in EXAMPLES:
        lines.append(f"사용자: {user}\n좋은 본문 예시: {reply}")
    return "\n\n".join(lines)


def build_system_prompt(mode_key):
    return "\n\n".join(
        [
            MODE_ROLES[mode_key],
            CORE_PRINCIPLES,
            "[컨트롤러 6가지 - 발동 조건에 해당하면 반드시 적용]\n\n" + _render_controllers(),
            "[좋은 응답 예시 - 방향만 참고하고, 문장을 그대로 베끼지 말 것. 제목 줄은 생략된 예시다]\n\n" + _render_examples(),
            COMMON_FORMAT,
        ]
    )


SYSTEM_PROMPTS = {key: build_system_prompt(key) for key in MODE_ROLES}


MODES = {
    "empathy": {
        "key": "empathy",
        "label": "💛 감성 공감 모드",
        "desc": "<b>Claude Sonnet 5.5</b>가 마음 이면의 바람을 함께 짚어줘요.",
        "avatar": "💛",
        "banner_icon": "💡",
        "provider": "anthropic",
        "model": get_secret("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
    },
    "fact": {
        "key": "fact",
        "label": "🔥 팩트 폭격 모드",
        "desc": "<b>GPT-5.6 Sol</b>이 놓치고 있던 관점을 직설적으로 짚어줘요.",
        "avatar": "🔥",
        "banner_icon": "⚡",
        "provider": "openai",
        # 기본값: gpt-5.6-sol (다른 모델을 쓰려면 secrets / 환경변수 OPENAI_MODEL 로 지정)
        "model": get_secret("OPENAI_MODEL", "gpt-5.6-sol"),
    },
}

# 모드별 포인트 컬러: 감성 공감 = 노랑(기본 톤) / 팩트 폭격 = 파랑
# on = 포인트 색 위에 올라가는 글자색, pale/pale_fg = (반대 모드 버튼 위에 마우스를 올렸을 때) 옅은 미리보기 색
THEMES = {
    "empathy": {
        "accent": "#FFD45E", "soft": "#FFF1C2", "deep": "#8A5A00", "ring": "rgba(245,184,0,.30)",
        "on": "#3B2A00", "border": "#F5B800", "glow": "rgba(245,184,0,.75)",
        "pale": "#FFF1C7", "pale_fg": "#7A5500",
    },
    "fact": {
        "accent": "#2F55F5", "soft": "#E8ECFF", "deep": "#2437B0", "ring": "rgba(47,85,245,.22)",
        "on": "#FFFFFF", "border": "#2F55F5", "glow": "rgba(47,85,245,.75)",
        "pale": "#DCE4FF", "pale_fg": "#2437B0",
    },
}



# ─────────────────────────────────────────────
# 3. LLM 호출 (스트리밍)
# ─────────────────────────────────────────────
MAX_HISTORY = 20  # API로 보낼 최근 메시지 수 (비용/맥락 길이 관리)
MAX_TOKENS = 4000  # 모델이 내부 추론에 토큰을 쓰는 경우를 대비해 여유 있게 설정


# ─────────────────────────────────────────────
# 3. LLM 호출 (스트리밍)
# ─────────────────────────────────────────────
def stream_anthropic(cfg, system_prompt, history):
    import anthropic

    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY를 찾을 수 없습니다. .streamlit/secrets.toml 또는 환경변수를 확인하세요.")

    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=cfg["model"],
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=history,
    ) as stream:
        for text in stream.text_stream:
            yield text

        # 텍스트가 하나도 없었다면 원인(stop_reason 등)을 알려준다
        final = stream.get_final_message()
        got_text = any(
            getattr(b, "type", "") == "text" and getattr(b, "text", "")
            for b in final.content
        )
        if not got_text:
            block_types = [getattr(b, "type", "?") for b in final.content]
            raise RuntimeError(
                f"모델이 텍스트를 반환하지 않았습니다 "
                f"(stop_reason={final.stop_reason}, blocks={block_types}, max_tokens={MAX_TOKENS})"
            )


def stream_openai(cfg, system_prompt, history):
    from openai import OpenAI

    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY를 찾을 수 없습니다. .streamlit/secrets.toml 또는 환경변수를 확인하세요.")

    client = OpenAI(api_key=api_key)
    stream = client.chat.completions.create(
        model=cfg["model"],
        messages=[{"role": "system", "content": system_prompt}] + history,
        stream=True,
    )
    got_text, finish = False, None
    for chunk in stream:
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        if choice.delta.content:
            got_text = True
            yield choice.delta.content
        if choice.finish_reason:
            finish = choice.finish_reason
    if not got_text:
        raise RuntimeError(f"모델이 텍스트를 반환하지 않았습니다 (finish_reason={finish})")


def stream_reply(cfg, history):
    system_prompt = SYSTEM_PROMPTS[cfg["key"]]
    if cfg["provider"] == "anthropic":
        return stream_anthropic(cfg, system_prompt, history)
    return stream_openai(cfg, system_prompt, history)


# ─────────────────────────────────────────────
# 4. 스타일 (CSS)
# ─────────────────────────────────────────────
FONT_IMPORTS = (
    # Pretendard: 전체 본문 / 채팅 말풍선
    "@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');"
    # Gowun Batang: RIDIBatang을 불러오지 못할 때 쓰는 명조 대체 폰트
    "@import url('https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&display=swap');"
)

# @font-face는 반드시 @import 뒤에 와야 합니다.
FONT_FACES = (
    # Gmarket Sans: 메인 타이틀(h1) / 주요 강조 카피
    "@font-face{font-family:'GmarketSans';font-weight:500;font-style:normal;font-display:swap;"
    "src:url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansMedium.woff') format('woff');}"
    "@font-face{font-family:'GmarketSans';font-weight:700;font-style:normal;font-display:swap;"
    "src:url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansBold.woff') format('woff');}"
    # RIDIBatang: 사이드바 '생각의 공간' 및 안내 문구
    "@font-face{font-family:'RIDIBatang';font-weight:400;font-style:normal;font-display:swap;"
    "src:url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_twelve@1.0/RIDIBatang.woff') format('woff');}"
)

BASE_CSS = r"""
:root{
  --ink:#2E2410; --muted:#7C6F4E; --mist:#FFF9E6; --card:#FFFFFF; --line:#F1E4B8;
  --side:#FFFDF4; --avatar:#FFF0BF; --placeholder:#A89B78;
  --idle-bg:#ECEBE8; --idle-fg:#66625A;
  --font-body:"Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont,
              "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", sans-serif;
  --font-display:"GmarketSans", "Pretendard Variable", Pretendard, "Apple SD Gothic Neo", sans-serif;
  --font-serif:"RIDIBatang", "Gowun Batang", "Noto Serif KR", "Apple SD Gothic Neo", serif;
  --col:640px;
  color-scheme: light;
}
@media (prefers-reduced-motion: reduce){ *{ transition:none !important; } }

/* CSS 주입용 빈 컨테이너가 공간을 차지하지 않도록 */
div[data-testid="stElementContainer"]:has(.eum-css-anchor),
.element-container:has(.eum-css-anchor){ display:none !important; }

/* ── 전체: Pretendard ── */
html, body, .stApp{ font-family:var(--font-body); }
.stApp{ background:var(--mist) !important; color:var(--ink) !important; }
.stApp p, .stApp li, .stApp label, .stApp textarea, .stApp input, .stApp button{ font-family:inherit; }
header[data-testid="stHeader"]{ background:transparent !important; }
footer, [data-testid="stAppDeployButton"], .stDeployButton,
[data-testid="stMainMenu"], #MainMenu{ display:none !important; }
.block-container{
  max-width:720px !important;
  padding-top:3.4rem !important;
  padding-bottom:8rem !important;
}
@media (max-width:640px){
  .block-container{ padding-left:1rem !important; padding-right:1rem !important; padding-top:3.2rem !important; }
}

/* ── 타이틀(h1): Gmarket Sans, 가운데 정렬 ── */
.stApp h1, [data-testid="stHeading"]{ text-align:center !important; }
.stApp h1{
  font-family:var(--font-display) !important;
  font-weight:700; font-size:clamp(1.4rem, 5vw, 2rem); line-height:1.4;
  letter-spacing:-0.01em; color:var(--ink) !important; word-break:keep-all; text-wrap:balance;
  padding:0 0 .5rem;
}
.stApp h1 a, [data-testid="stHeaderActionElements"]{ display:none !important; }

/* ── 서브 캡션: 가운데 정렬 ── */
[data-testid="stCaptionContainer"]{ text-align:center !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *{
  color:var(--muted) !important; font-size:.98rem; line-height:1.6; word-break:keep-all;
}
[data-testid="stCaptionContainer"] p{ text-wrap:balance; }

/* ── 모드 선택: 캡슐형 토글 (메인 화면 정중앙) ──
   Streamlit 버전마다 라디오 내부 구조가 달라서, 자식 관계(>)에 기대지 않고 작성했습니다. */
[data-testid="stElementContainer"]:has([data-testid="stRadio"]),
.element-container:has([data-testid="stRadio"]){
  width:100% !important; max-width:var(--col); margin-left:auto !important; margin-right:auto !important;
  align-self:center;
}
[data-testid="stRadio"]{
  width:100% !important; max-width:var(--col); margin:1.5rem auto 0 !important;
  display:flex; flex-direction:column; align-items:stretch;
}
[data-testid="stRadio"] [data-testid="stWidgetLabel"]{
  display:flex; justify-content:center; width:100%; margin-bottom:.7rem;
}
[data-testid="stRadio"] [data-testid="stWidgetLabel"] p{
  text-align:center; font-weight:700; font-size:.95rem; color:var(--muted);
}
/* 옵션 버튼들을 담은 줄: 정중앙 */
[data-testid="stRadio"] :has(> label:not([data-testid="stWidgetLabel"])){
  display:flex !important; flex-direction:row !important; flex-wrap:nowrap !important;
  justify-content:center !important; align-items:stretch; gap:.75rem !important; width:100% !important;
}
/* 기본 상태: 옅은 회색 캡슐 */
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]){
  position:relative; box-sizing:border-box; flex:1 1 0; min-width:0; max-width:300px; min-height:3.75rem;
  margin:0 !important; padding:.9rem 1.5rem !important;
  display:flex !important; align-items:center; justify-content:center; text-align:center; cursor:pointer;
  background:var(--idle-bg) !important; color:var(--idle-fg); border:2px solid transparent !important;
  border-radius:50px !important;
  transition:background-color .25s ease, color .25s ease, border-color .25s ease,
             box-shadow .25s ease, transform .15s ease;
  -webkit-tap-highlight-color:transparent;
}
/* 작은 동그라미 숨김: 글자(p)가 없는 자식 요소와 input */
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]) > :not(input):not(p):not(:has(p)){
  position:absolute !important; opacity:0 !important; width:0 !important; height:0 !important;
  margin:0 !important; padding:0 !important; overflow:hidden !important; pointer-events:none !important;
}
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]) input{
  position:absolute; opacity:0; width:0; height:0; margin:0; pointer-events:none;
}
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]) > :has(p){ margin:0 !important; padding:0 !important; }
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]) p{
  margin:0; font-size:1.1rem; font-weight:700; line-height:1.3;
  text-align:center; word-break:keep-all; color:inherit !important;
}
/* 호버: 선택되지 않은 버튼 = 반대 모드의 옅은 색을 미리 보여줌 */
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]):hover{
  background:var(--hov-bg) !important; color:var(--hov-fg);
}
/* 선택됨: 감성 공감 = 따뜻한 노랑 / 팩트 폭격 = 뚜렷한 파랑 (현재 모드 색) */
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]):has(input:checked){
  background:var(--accent) !important; color:var(--on-accent);
  border-color:var(--accent-border) !important; box-shadow:0 10px 24px -10px var(--accent-glow);
}
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]):has(input:checked):hover{ transform:translateY(-1px); }
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]):active{ transform:scale(.97); }
[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]):has(input:focus-visible){
  outline:3px solid var(--ink); outline-offset:3px;
}
@media (max-width:640px){
  [data-testid="stRadio"] :has(> label:not([data-testid="stWidgetLabel"])){ gap:.6rem !important; }
  [data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]){ min-height:3.4rem; padding:.8rem .6rem !important; }
  [data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]) p{ font-size:1rem; }
}
.eum-mode-desc{
  max-width:var(--col); margin:.9rem auto 1.6rem; text-align:center;
  font-size:.9rem; line-height:1.7; color:var(--muted); word-break:keep-all; text-wrap:balance;
}
.eum-mode-desc b{ color:var(--accent-deep); font-weight:700; }

/* ── 빈 화면 안내 (여유 있게) ── */
.eum-empty{
  max-width:var(--col); margin:.6rem auto 1.4rem; padding:1.6rem 1.7rem; border-radius:20px;
  background:var(--card); border:1px dashed #E8D79A;
}
.eum-empty p{
  margin:0 0 .9rem; font-family:var(--font-display) !important; font-weight:500;
  font-size:1rem; line-height:1.7; color:var(--ink); word-break:keep-all;
}
.eum-empty ul{ margin:0; padding-left:1.2rem; color:var(--muted); font-size:.95rem; line-height:2.1; }

/* ── 채팅 컨테이너: 최대 너비 제한 + 가운데 배치 ── */
[data-testid="stChatMessage"]{
  width:100%; max-width:var(--col); margin:0 auto !important;
  background:transparent !important; padding:.65rem 0 !important; gap:.8rem; align-items:flex-start;
}
/* 사용자: 오른쪽 정렬, 아바타 숨김 */
[data-testid="stChatMessageAvatarUser"], [data-testid="chatAvatarIcon-user"]{ display:none !important; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]){ flex-direction:row-reverse; }

/* AI: 왼쪽 정렬, 작은 원형 아바타 */
[data-testid="stChatMessageAvatarAssistant"], [data-testid="chatAvatarIcon-assistant"],
[data-testid="stChatMessageAvatarCustom"]{
  background:var(--avatar) !important; color:var(--ink) !important;
  width:2.2rem !important; height:2.2rem !important; border-radius:50% !important; font-size:1.1rem;
}

/* 말풍선 공통 (AI 기본값) — Pretendard, 여유로운 안쪽 여백과 줄 간격 */
[data-testid="stChatMessageContent"]{
  flex:0 1 auto !important; width:fit-content;
  max-width:min(calc(100% - 3rem), 35rem);
  padding:1.1rem 1.4rem; line-height:1.9; word-break:keep-all; overflow-wrap:anywhere;
  font-family:var(--font-body);
  background:var(--card) !important; color:var(--ink) !important;
  border:1px solid var(--line); border-radius:22px 22px 22px 6px;
  box-shadow:0 10px 24px -16px rgba(46,36,16,.35);
}
[data-testid="stChatMessageContent"] :is(p, li, strong, em, blockquote){ font-family:var(--font-body); }
[data-testid="stChatMessageContent"] p{ margin:0 0 .9rem; font-size:1rem; line-height:1.9; }
[data-testid="stChatMessageContent"] p:last-child{ margin-bottom:0; }

/* 사용자 말풍선: 포인트 색 */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"],
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"]{
  max-width:80%; padding:1rem 1.35rem; line-height:1.75;
  background:var(--accent) !important; border:none;
  border-radius:22px 22px 6px 22px; box-shadow:0 12px 24px -14px var(--accent-glow);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] *,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] *{
  color:var(--on-accent) !important; line-height:1.75;
}

/* AI 답변 위의 한 줄 요약 배너 — Gmarket Sans (모드별 색 고정) */
.eum-banner{
  display:flex; gap:.55rem; align-items:flex-start; padding:.75rem 1rem; margin-bottom:1rem;
  border-radius:14px; font-family:var(--font-display) !important; font-weight:500;
  font-size:.92rem; line-height:1.55;
}
.eum-banner--empathy{ background:#FFF1C2; color:#6B4A00; }
.eum-banner--fact{ background:#E8ECFF; color:#2437B0; }

/* 에러 / 알림 */
[data-testid="stAlert"]{ border-radius:14px; border:none; max-width:var(--col); margin:0 auto; }

/* ── 입력창 ── */
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"]{ background:var(--mist) !important; }
[data-testid="stBottomBlockContainer"]{ padding-bottom:calc(1rem + env(safe-area-inset-bottom, 0px)) !important; }
[data-testid="stChatInput"]{
  width:100%; max-width:var(--col); margin:0 auto !important;
  background:#fff !important; border:1.5px solid var(--line) !important; border-radius:28px !important;
  box-shadow:0 10px 26px -16px rgba(46,36,16,.35); transition:border-color .15s, box-shadow .15s;
}
[data-testid="stChatInput"] > div{ background:transparent !important; border:none !important; box-shadow:none !important; border-radius:28px !important; }
[data-testid="stChatInput"]:focus-within{ border-color:var(--accent-border) !important; box-shadow:0 0 0 3px var(--accent-ring); }
[data-testid="stChatInput"] textarea{ color:var(--ink) !important; font-size:1rem; line-height:1.6; padding:.9rem 1.2rem !important; }
[data-testid="stChatInput"] textarea::placeholder{ color:var(--placeholder) !important; }
[data-testid="stChatInput"] button{ background:var(--accent) !important; color:var(--on-accent) !important; border-radius:50% !important; }
[data-testid="stChatInput"] button svg{ fill:var(--on-accent) !important; color:var(--on-accent) !important; }

@media (max-width:640px){
  [data-testid="stChatMessageContent"]{ padding:1rem 1.2rem; }
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"],
  [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"]{ padding:.9rem 1.15rem; }
  .eum-empty{ padding:1.3rem 1.3rem; }
}

/* ── 사이드바 ── */
[data-testid="stSidebar"]{ background:var(--side) !important; border-right:1px solid var(--line); }
[data-testid="stSidebar"] *{ color:var(--ink); }

/* 로고: Gmarket Sans */
.eum-brand{ display:flex; align-items:baseline; gap:.35rem; margin:.2rem 0 .15rem; }
.eum-brand__name{
  font-family:var(--font-display) !important; font-size:1.8rem; font-weight:700; letter-spacing:-.01em;
}
.eum-brand__en{ font-family:var(--font-display) !important; font-size:.9rem; font-weight:500; color:var(--accent-deep) !important; }

/* 사이드바 안내 문구: RIDIBatang */
.eum-sub{
  margin:0 0 1.3rem; color:var(--muted) !important; font-size:.95rem; line-height:1.7;
  font-family:var(--font-serif) !important; word-break:keep-all;
}
.eum-space{ margin:1.5rem 0 .9rem; padding:1.05rem 1.1rem; border-radius:18px; background:var(--mist); }
.eum-space__title{
  font-family:var(--font-serif) !important; font-weight:400; font-size:1.2rem; margin-bottom:.45rem;
}
.eum-space p{
  margin:0; font-size:.95rem; line-height:1.8; color:var(--muted) !important;
  font-family:var(--font-serif) !important; word-break:keep-all;
}
.eum-note{
  margin-top:.8rem; padding:.85rem 1rem; border-radius:14px; background:var(--accent-soft);
  font-family:var(--font-serif) !important; font-size:.95rem; line-height:1.7;
  color:var(--accent-deep) !important; word-break:keep-all;
}

/* 버튼: 내 생각 정리하기(주 버튼) / 대화 초기화(보조 버튼) */
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]{
  width:100%; min-height:3.3rem; border:none; border-radius:16px;
  background:var(--ink) !important; font-weight:700; font-size:1rem;
  box-shadow:0 12px 26px -12px rgba(46,36,16,.7);
  transition:transform .15s, background-color .2s, box-shadow .15s;
}
[data-testid="stSidebar"] button[kind="primary"] *,
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] *{ color:#fff !important; transition:color .2s; }
[data-testid="stSidebar"] button[kind="primary"]:hover,
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover{
  background:var(--accent) !important; transform:translateY(-1px);
  box-shadow:0 14px 28px -12px var(--accent-glow);
}
[data-testid="stSidebar"] button[kind="primary"]:hover *,
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover *{ color:var(--on-accent) !important; }
[data-testid="stSidebar"] button[kind="secondary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]{
  width:100%; min-height:2.6rem; border-radius:14px; background:transparent !important;
  border:1px solid var(--line); font-size:.9rem; transition:border-color .15s;
}
[data-testid="stSidebar"] button[kind="secondary"] *,
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] *{ color:var(--muted) !important; }
[data-testid="stSidebar"] button[kind="secondary"]:hover,
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover{ border-color:var(--accent-border); }
[data-testid="stSidebar"] button:focus-visible{ outline:2px solid var(--ink); outline-offset:2px; }

/* 모바일: 닫힌 사이드바를 여는 버튼을 눈에 띄게 */
[data-testid="stSidebarCollapsedControl"] button, [data-testid="stExpandSidebarButton"]{
  background:var(--accent) !important; border-radius:999px !important; min-width:2.4rem; min-height:2.4rem;
  box-shadow:0 8px 18px -8px var(--accent-glow);
}
[data-testid="stSidebarCollapsedControl"] button *, [data-testid="stExpandSidebarButton"] *{
  color:var(--on-accent) !important; fill:var(--on-accent) !important;
}
"""


def inject_css(mode_key):
    t = THEMES[mode_key]
    other = THEMES["fact" if mode_key == "empathy" else "empathy"]
    root = (
        ":root{"
        f"--accent:{t['accent']};--accent-soft:{t['soft']};--accent-deep:{t['deep']};--accent-ring:{t['ring']};"
        f"--on-accent:{t['on']};--accent-border:{t['border']};--accent-glow:{t['glow']};"
        f"--hov-bg:{other['pale']};--hov-fg:{other['pale_fg']};"
        "}"
    )
    st.markdown(
        f"<style>{FONT_IMPORTS}{FONT_FACES}{root}{BASE_CSS}</style><div class='eum-css-anchor'></div>",
        unsafe_allow_html=True,
    )


def render_banner(container, mode_key, text):
    """모델이 만든 한 줄 제목을 모드 색상의 배너로 표시한다."""
    if not text:
        return
    icon = MODES[mode_key]["banner_icon"]
    container.markdown(
        f"<div class='eum-banner eum-banner--{mode_key}'>"
        f"<span>{icon}</span><span>{html.escape(text)}</span></div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# 5. 상태 / 스타일 적용
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# 라디오 위젯의 현재 선택값을 먼저 읽어서, 첫 렌더부터 모드 색상으로 칠한다
current_mode = st.session_state.get("mode", "empathy")
if current_mode not in MODES:
    current_mode = "empathy"
inject_css(current_mode)


# ─────────────────────────────────────────────
# 6. 사이드바
# ─────────────────────────────────────────────
st.sidebar.markdown(
    "<div class='eum-brand'><span class='eum-brand__name'>이음</span>"
    "<span class='eum-brand__en'>(E-um)</span></div>"
    "<p class='eum-sub'>지금 마음에 맞는 대화를 골라보세요.</p>",
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    "<div class='eum-space'><div class='eum-space__title'>생각의 공간</div>"
    "<p>이음은 결론을 대신 내려주지 않아요.<br>"
    "충분히 이야기를 나눴다면, 이제 스스로 답을 정리해 볼 시간이에요.</p></div>",
    unsafe_allow_html=True,
)

if st.sidebar.button("📝 내 생각 정리하기 (대화 종료)", type="primary", key="btn_reflect"):
    st.sidebar.markdown(
        "<div class='eum-note'>최종 판단은 당신의 몫이에요. "
        "대화에서 스스로 발견한 기준을 메모장에 적어보세요.</div>",
        unsafe_allow_html=True,
    )

if st.sidebar.button("🗑️ 대화 초기화", key="btn_reset"):
    st.session_state.messages = []
    st.rerun()


# ─────────────────────────────────────────────
# 7. 메인 채팅 화면
# ─────────────────────────────────────────────
st.title("당신의 연애, 어떤 기준으로 이어가고 있나요?")
st.caption("팩트 폭격부터 따뜻한 공감까지, 지금 내 감정에 맞는 대화를 시작해 보세요.")
mode_key = st.radio(
    "어떤 대화를 원하시나요?",
    list(MODES.keys()),
    format_func=lambda k: MODES[k]["label"],
    key="mode",
    horizontal=True,
)
cfg = MODES[mode_key]
st.markdown(f"<p class='eum-mode-desc'>{cfg['desc']}</p>", unsafe_allow_html=True)

visible = [m for m in st.session_state.messages if m["content"].strip()]
if not visible:
    st.markdown(
        "<div class='eum-empty'><p>어떤 이야기든 괜찮아요. 이렇게 시작해 볼 수 있어요.</p><ul>"
        "<li>연락이 뜸해져서 자꾸 마음이 쓰여요</li>"
        "<li>애인의 오랜 친구가 신경 쓰여요</li>"
        "<li>이 관계를 이어가도 될지 모르겠어요</li>"
        "</ul></div>",
        unsafe_allow_html=True,
    )

# 이전 대화 기록 출력 (당시 모드의 아바타/배너까지 복원)
for m in visible:
    if m["role"] == "assistant":
        mk = m.get("mode_key", "empathy")
        with st.chat_message("assistant", avatar=MODES[mk]["avatar"]):
            render_banner(st, mk, m.get("banner"))
            st.markdown(m["content"])
    else:
        with st.chat_message("user"):
            st.markdown(m["content"])


# ─────────────────────────────────────────────
# 8. 사용자 입력 → 실제 LLM 응답
# ─────────────────────────────────────────────
if prompt := st.chat_input("연애 고민을 편하게 이야기해 주세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # API에는 role/content만 보낸다 (최근 MAX_HISTORY개, 빈 메시지 제외)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[-MAX_HISTORY:]
        if m["content"].strip()
    ]
    # Anthropic API는 첫 메시지가 user여야 하므로 보정
    while history and history[0]["role"] != "user":
        history.pop(0)

    with st.chat_message("assistant", avatar=cfg["avatar"]):
        banner_box = st.empty()
        body_box = st.empty()

        buffer, banner, body = "", None, ""
        try:
            with st.spinner("생각을 정리하는 중..."):
                gen = stream_reply(cfg, history)
                first_chunk = next(gen, None)  # 첫 토큰이 올 때까지 스피너 표시

            def all_chunks():
                if first_chunk:
                    yield first_chunk
                yield from gen

            for chunk in all_chunks():
                if banner is None:
                    # 첫 줄(제목)이 끝날 때까지 모은 뒤 배너로 표시
                    buffer += chunk
                    if "\n" not in buffer:
                        continue
                    first_line, rest = buffer.split("\n", 1)
                    banner = first_line.strip().strip("#*[]\"' ")
                    render_banner(banner_box, mode_key, banner)
                    body = rest.lstrip("\n")
                else:
                    body += chunk
                body_box.markdown(body + "▌")

            # 줄바꿈이 한 번도 없었던 경우: 전체를 본문으로 처리
            if banner is None:
                banner, body = "", buffer

            body = body.strip()
            if not body:
                raise RuntimeError("모델이 빈 응답을 반환했습니다.")
            body_box.markdown(body)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": body,
                    "banner": banner,
                    "mode_key": mode_key,
                }
            )

        except Exception as e:
            # 실패 시 방금 넣은 user 메시지를 제거해 role 순서가 꼬이지 않게 한다
            st.session_state.messages.pop()
            banner_box.empty()
            body_box.error(f"응답을 가져오지 못했습니다: {e}")
