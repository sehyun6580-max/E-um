import streamlit as st
from datetime import datetime
import json

# API 라이브러리 로드 (설치되어 있지 않아도 UI 시연이 가능하도록 예외 처리)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import anthropic
except ImportError:
    anthropic = None

# ---------------------------------------------------------
# 1. 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="이음(E-um) | 당신의 연애 기준",
    page_icon="💌",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 2. 세션 상태(Session State) 초기화
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = "empathy"  # 'empathy' (감성 공감) 또는 'fact' (팩트 폭격)
if "x_room_notes" not in st.session_state:
    # X룸에 채워질 포스트잇 & 대화 아카이브 리스트
    st.session_state.x_room_notes = []

# ---------------------------------------------------------
# 3. 커스텀 CSS (스트림릿 마크 제거 + 이음 UI + 환승연애 X룸 & 포스트잇 디자인)
# ---------------------------------------------------------
custom_css = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
@import url('https://fastly.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansMedium.woff');
@import url('https://fastly.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/RIDIBatang.woff');

/* 0. 우측 상단 Github/메뉴 마크 및 우측 하단 스트림릿 워터마크 완벽 제거 */
#MainMenu {visibility: hidden !important;}
header {visibility: hidden !important;}
footer {visibility: hidden !important;}
[data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
[data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
[data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}

/* 1. 전체 배경 및 기본 폰트 */
.stApp {
    background-color: #FDF8EC;
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #2B2118;
}

.block-container {
    max-width: 680px !important;
    padding-top: 2rem !important;
    padding-bottom: 6rem !important;
}

/* 2. 메인 타이틀 & 서브 캡션 */
.main-title {
    font-family: 'GmarketSansMedium', 'Pretendard', sans-serif;
    font-size: 1.95rem;
    font-weight: 800;
    text-align: center;
    color: #2B2118;
    margin-bottom: 0.3rem;
    letter-spacing: -0.03em;
}
.sub-caption {
    text-align: center;
    font-size: 0.9rem;
    color: #8C7A6B;
    margin-bottom: 1.5rem;
}

/* 3. 상단 탭 (이음 라운지 vs X-ROOM) 디자인 */
.stTabs [data-baseweb="tab-list"] {
    justify-content: center;
    gap: 12px;
    background-color: #F4EFE3;
    padding: 6px;
    border-radius: 999px;
    max-width: 420px;
    margin: 0 auto 1.8rem auto;
    border: 1px solid #E5DEC9;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 999px !important;
    padding: 8px 22px !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    color: #6E6259 !important;
    border: none !important;
    background-color: transparent !important;
}
.stTabs [aria-selected="true"] {
    background-color: #2B2118 !important;
    color: #FDF8EC !important;
    box-shadow: 0 2px 8px rgba(43,33,24,0.18);
}

/* 4. 초기 가이드 박스 */
.guide-box {
    background-color: #FAF6EE;
    border: 1.5px dashed #DFD5C0;
    border-radius: 18px;
    padding: 18px 22px;
    margin: 1rem 0 1.5rem 0;
}
.guide-title {
    font-weight: 700;
    font-size: 0.92rem;
    margin-bottom: 8px;
    color: #2B2118;
}
.guide-list {
    font-size: 0.84rem;
    color: #6E6259;
    margin: 0;
    padding-left: 1.2rem;
    line-height: 1.7;
}

/* 5. 채팅 말풍선 디자인 */
.user-bubble-empathy {
    background-color: #F7C844;
    color: #2B2118;
    padding: 12px 18px;
    border-radius: 20px 20px 4px 20px;
    max-width: 78%;
    margin-left: auto;
    margin-bottom: 14px;
    font-size: 0.92rem;
    font-weight: 600;
    box-shadow: 0 2px 6px rgba(247, 200, 68, 0.25);
}
.user-bubble-fact {
    background-color: #2554E8;
    color: #FFFFFF;
    padding: 12px 18px;
    border-radius: 20px 20px 4px 20px;
    max-width: 78%;
    margin-left: auto;
    margin-bottom: 14px;
    font-size: 0.92rem;
    font-weight: 600;
    box-shadow: 0 2px 6px rgba(37, 84, 232, 0.25);
}
.ai-card {
    background-color: #FAF6EE;
    border: 1px solid #EDE5D4;
    border-radius: 4px 20px 20px 20px;
    padding: 16px 18px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}
.badge-empathy {
    background-color: #F6E4B2;
    color: #6B4908;
    padding: 7px 13px;
    border-radius: 10px;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 10px;
    display: inline-block;
    width: 100%;
}
.badge-fact {
    background-color: #E2E8FC;
    color: #213B9E;
    padding: 7px 13px;
    border-radius: 10px;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 10px;
    display: inline-block;
    width: 100%;
}
.ai-body {
    font-size: 0.92rem;
    line-height: 1.65;
    color: #2B2118;
}

/* 6. 환승연애 오마주: X-ROOM (어둡고 시네마틱한 기억의 방) */
.xroom-wrapper {
    background: linear-gradient(180deg, #161418 0%, #221D24 100%);
    color: #F3EFEA;
    border-radius: 24px;
    padding: 32px 26px;
    box-shadow: 0 14px 35px rgba(0,0,0,0.28);
    border: 1px solid #3A323D;
    margin-top: 0.5rem;
}
.xroom-header {
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    padding-bottom: 20px;
    margin-bottom: 24px;
}
.xroom-badge {
    display: inline-block;
    background: rgba(229, 107, 111, 0.18);
    color: #FF9EAA;
    border: 1px solid rgba(229, 107, 111, 0.4);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    padding: 4px 12px;
    border-radius: 999px;
    margin-bottom: 10px;
}
.xroom-title {
    font-family: 'RIDIBatang', serif;
    font-size: 1.6rem;
    color: #FFFFFF;
    margin-bottom: 6px;
    letter-spacing: 0.04em;
}
.xroom-desc {
    font-family: 'RIDIBatang', serif;
    font-size: 0.84rem;
    color: #B8AEB8;
    line-height: 1.6;
}

/* 7. X-ROOM 내부 포스트잇 (생각 정리 카드) 디자인 */
.postit-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 18px;
    margin-top: 16px;
}
.postit-card {
    padding: 20px 18px;
    border-radius: 4px 14px 14px 14px;
    box-shadow: 4px 6px 16px rgba(0,0,0,0.35);
    position: relative;
    transition: transform 0.2s ease;
    color: #2B2118;
}
.postit-card:hover {
    transform: translateY(-4px) rotate(0.5deg);
}
.postit-yellow {
    background: #FFF3B0;
    border-top: 10px solid #F3DC7A;
}
.postit-pink {
    background: #FFD6E0;
    border-top: 10px solid #F2B5C4;
}
.postit-blue {
    background: #D8E6FF;
    border-top: 10px solid #B3CCFA;
}
.postit-time {
    font-size: 0.72rem;
    color: #6E6259;
    margin-bottom: 8px;
    font-weight: 600;
}
.postit-to {
    font-family: 'RIDIBatang', serif;
    font-size: 0.85rem;
    font-weight: 700;
    color: #1F1914;
    margin-bottom: 8px;
    border-bottom: 1px dashed rgba(0,0,0,0.15);
    padding-bottom: 6px;
}
.postit-standard {
    font-size: 0.8rem;
    background: rgba(255,255,255,0.65);
    padding: 6px 10px;
    border-radius: 8px;
    margin-bottom: 10px;
    font-weight: 700;
    color: #3D2E22;
}
.postit-body {
    font-family: 'RIDIBatang', serif;
    font-size: 0.88rem;
    line-height: 1.6;
    color: #2B2118;
    white-space: pre-wrap;
}

/* 8. 환승연애 밤 '속마음 문자' 모달 디자인 */
.heart-sms-header {
    background: linear-gradient(135deg, #1E1B24 0%, #2D2638 100%);
    color: #FFFFFF;
    padding: 18px 20px;
    border-radius: 16px;
    margin-bottom: 16px;
    text-align: center;
    border: 1px solid #453A52;
}
.heart-sms-time {
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    color: #F7C844;
    font-weight: 700;
    margin-bottom: 4px;
}
.heart-sms-title {
    font-family: 'RIDIBatang', serif;
    font-size: 1.05rem;
    line-height: 1.5;
    color: #FAF6EE;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. 6대 제어 규칙 시스템 프롬프트 & AI 호출 함수
# ---------------------------------------------------------
BASE_CONTROLLER_RULES = """
당신은 연애 갈등 상황에서 사용자가 스스로 판단 기준을 찾게 돕는 대화형 AI '이음(E-um)'입니다.
반드시 아래 6대 제어 규칙을 준수하여 응답하세요:
1. 시코팬시 방지: 사용자의 일방적 비난이나 단정적 동의 요구에 무비판적으로 맞장구치지 말고 감정과 사실을 분리하세요.
2. 정보 부족 추론 제어: 구체적 맥락 없이 결론만 제시할 때 최소 사실을 먼저 확인하세요.
3. 판단 외주화 제어(소프트 스캐폴딩): "헤어질까 말까 정해줘" 같은 요구에 차갑게 거절하지 말고, 지친 마음을 먼저 보듬은 뒤 선택지별 기준을 함께 정리하자며 부드럽게 결정권을 돌려주세요.
4. 과도한 일반화 제어: 일회성 사건으로 상대의 인격 전체를 단정할 때 과거 빈도와 패턴을 되물으세요.
5. 모호한 감정 구체화: 막연한 불만을 횟수·상황·영향으로 쪼개거나 조건을 바꾼 질문(Unexpected Turn)을 던지세요.
6. 모드 이탈 제어: 현재 모드의 톤앤매너를 유지하되, 마지막엔 반드시 사용자가 스스로 생각해볼 질문 1개로 마무리하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{
  "summary_badge": "말풍선 상단에 들어갈 핵심 요약 한 줄 (25자 이내, 이모지 제외)",
  "message": "사용자에게 건네는 본문 응답 (친근한 반말/해체 사용, 마지막엔 질문 1개로 마무리)"
}
"""

def generate_ai_response(messages, mode):
    """선택된 모드에 따라 API를 호출하거나 시뮬레이션 응답을 반환합니다."""
    openai_key = st.secrets.get("OPENAI_API_KEY", None) if hasattr(st, "secrets") else None
    anthropic_key = st.secrets.get("ANTHROPIC_API_KEY", None) if hasattr(st, "secrets") else None

    # 1) 감성 공감 모드 (Claude Sonnet 연동)
    if mode == "empathy":
        if anthropic and anthropic_key:
            try:
                client = anthropic.Anthropic(api_key=anthropic_key)
                sys_prompt = f"{BASE_CONTROLLER_RULES}\n[현재 모드: 감성 공감 모드]\n섬세하고 다정하게 감정을 수용하되 내면의 결핍과 기준을 구조화(Interpretation)하세요."
                resp = client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=800,
                    system=sys_prompt,
                    messages=[{"role": m["role"], "content": m["content"]} for m in messages]
                )
                return json.loads(resp.content[0].text)
            except Exception:
                pass
        # API 키 미설정 시 기본 응답
        return {
            "summary_badge": "지친 마음과 결정의 기준을 나눠볼까?",
            "message": "혼자 애쓰는 기분이 들면 누구라도 지치고 외로웠을 거야. 다만 상대방의 마음이 어떤지 지금 정보만으로는 단정하기 어려워. 요즘 가장 마음이 쓰였던 순간 하나만 떠올려 본다면, 상대의 어떤 행동이 제일 서운했어?"
        }

    # 2) 팩트 폭격 모드 (OpenAI GPT 연동)
    else:
        if OpenAI and openai_key:
            try:
                client = OpenAI(api_key=openai_key)
                sys_prompt = f"{BASE_CONTROLLER_RULES}\n[현재 모드: 팩트 폭격 모드]\n감정에 휩쓸리지 않고 객관적 사실과 맹점을 직설적으로 짚어주세요(Unexpected Turn)."
                resp = client.chat.completions.create(
                    model="gpt-4o",
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        *[{"role": m["role"], "content": m["content"]} for m in messages]
                    ]
                )
                return json.loads(resp.choices[0].message.content)
            except Exception:
                pass
        # API 키 미설정 시 기본 응답
        return {
            "summary_badge": "답장 속도보다 만났을 때 태도가 변수야",
            "message": "연락이 늦어져서 불안한 건 이해하지만, 연락 빈도 하나만으로 마음이 식었다고 단정하긴 일러. 최근 상대방 일정이 바빴는지, 실제로 만났을 때도 거리감이 느껴졌는지부터 팩트를 체크해 보자. 만났을 때 태도는 예전과 똑같다고 가정해도 여전히 피한다고 느낄까?"
        }

# ---------------------------------------------------------
# 5. 요구사항 2: 환승연애 '속마음 문자' 스타일 생각 정리 모달 (포스트잇 생성)
# ---------------------------------------------------------
@st.dialog("💌 오늘 밤, 당신의 속마음 문자")
def open_heart_sms_modal():
    st.markdown("""
    <div class="heart-sms-header">
        <div class="heart-sms-time">🌙 HEART MESSAGE · 인식적 자율성 노트</div>
        <div class="heart-sms-title">
            AI는 정답을 대신 내려주지 않습니다.<br>
            오늘 대화를 통해 발견한 <b>당신의 기준</b>을 포스트잇에 남겨주세요.
        </div>
    </div>
    """, unsafe_allow_html=True)

    target_topic = st.text_input(
        "🔖 어떤 고민(또는 상대)에 대한 기록인가요?",
        placeholder="예: 연락 텀이 길어진 애인과의 갈등 / 8년 된 이성친구 문제"
    )
    my_standard = st.text_input(
        "⚖️ 오늘 대화로 찾은 '나의 핵심 연애 기준'은?",
        placeholder="예: 연락 횟수 자체보다, 바빠도 미리 일정을 공유해 주는 배려가 중요하다"
    )
    my_message = st.text_area(
        "📝 나를 향해(또는 그 사람에게) 남기는 최종 생각 정리 포스트잇",
        placeholder="환승연애 속마음 문자처럼 오늘 내린 나만의 결론을 솔직하게 적어보세요.\n작성된 포스트잇은 오늘 나눈 대화와 함께 [X-ROOM]에 보관됩니다.",
        height=110
    )
    postit_color = st.radio(
        "🎨 포스트잇 컬러 선택",
        options=["💛 머스타드 옐로우 (공감)", "🩷 로즈 핑크 (설렘/미련)", "💙 미드나잇 블루 (이성/결단)"],
        horizontal=True
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("취소", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("📩 X-ROOM에 포스트잇 붙이기", type="primary", use_container_width=True):
            if not my_standard.strip() and not my_message.strip():
                st.warning("나의 기준이나 속마음 메모를 한 줄 이상 적어주세요!")
            else:
                color_class = "postit-yellow"
                if "핑크" in postit_color:
                    color_class = "postit-pink"
                elif "블루" in postit_color:
                    color_class = "postit-blue"

                # 현재까지의 대화 복사본과 함께 포스트잇 저장
                st.session_state.x_room_notes.insert(0, {
                    "id": len(st.session_state.x_room_notes) + 1,
                    "timestamp": datetime.now().strftime("%Y.%m.%d %H:%M"),
                    "topic": target_topic.strip() or "이름 없는 밤의 고민",
                    "standard": my_standard.strip() or "나만의 기준 탐색 중",
                    "conclusion": my_message.strip() or "충분히 고민하고 내린 나만의 결론",
                    "color": color_class,
                    "mode": st.session_state.mode,
                    "chat_snapshot": list(st.session_state.messages)
                })
                st.toast("💌 속마음 포스트잇이 X-ROOM에 보관되었습니다!", icon="🚪")
                st.rerun()

# ---------------------------------------------------------
# 6. 상단 타이틀 & 네비게이션 바
# ---------------------------------------------------------
st.markdown('<div class="main-title">당신의 연애, 어떤 기준으로 이어가고 있나요?</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-caption">팩트 폭격부터 따뜻한 공감까지, 지금 내 감정에 맞는 대화를 시작해 보세요.</div>', unsafe_allow_html=True)

# 상단 액션 버튼 (새 고민 시작 / 속마음 문자 보내기)
top_col1, top_col2, top_col3 = st.columns([1.1, 1.4, 1.1])
with top_col1:
    if st.button("🔄 새 고민 시작", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
with top_col3:
    if st.button("💌 내 생각 정리하기", use_container_width=True):
        open_heart_sms_modal()

# ---------------------------------------------------------
# 7. 메인 탭 분리: [💬 이음 라운지] vs [🚪 X-ROOM (기억의 방)]
# ---------------------------------------------------------
tab_lounge, tab_xroom = st.tabs([
    "💬 이음 라운지 (대화하기)",
    f"🚪 X-ROOM ({len(st.session_state.x_room_notes)})"
])

# =========================================================
# TAB 1: 이음 라운지 (기존 메신저 UI + 모드 선택)
# =========================================================
with tab_lounge:
    st.markdown("<p style='text-align:center; font-size:0.84rem; font-weight:700; color:#6E6259; margin-bottom:8px;'>어떤 대화를 원하시나요?</p>", unsafe_allow_html=True)

    # 캡슐형 느낌의 모드 선택 버튼 2개 배치
    m_col1, m_col2 = st.columns(2)
    is_empathy = st.session_state.mode == "empathy"

    with m_col1:
        btn_label_emp = "🔘 💛 감성 공감 모드" if is_empathy else "⚪ 💛 감성 공감 모드"
        if st.button(btn_label_emp, use_container_width=True, type="primary" if is_empathy else "secondary"):
            st.session_state.mode = "empathy"
            st.rerun()
    with m_col2:
        btn_label_fact = "🔘 🔥 팩트 폭격 모드" if not is_empathy else "⚪ 🔥 팩트 폭격 모드"
        if st.button(btn_label_fact, use_container_width=True, type="primary" if not is_empathy else "secondary"):
            st.session_state.mode = "fact"
            st.rerun()

    # 선택된 모드 설명 캡션
    if is_empathy:
        st.markdown("<p style='text-align:center; font-size:0.8rem; color:#6E6259; margin-top:4px;'><b style='color:#8A5A00;'>Claude Sonnet 5.5</b>가 마음 이면의 바람을 함께 짚어줘요.</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align:center; font-size:0.8rem; color:#6E6259; margin-top:4px;'><b style='color:#1D3B9E;'>GPT-5.6 Sol</b>이 놓치고 있던 관점을 직설적으로 짚어줘요.</p>", unsafe_allow_html=True)

    # 초기 가이드 박스 및 빠른 시작 버튼
    st.markdown("""
    <div class="guide-box">
        <div class="guide-title">어떤 이야기든 괜찮아요. 이렇게 시작해 볼 수 있어요.</div>
        <ul class="guide-list">
            <li>연락이 뜸해져서 자꾸 마음이 쓰여요</li>
            <li>애인의 오랜 친구가 신경 쓰여요</li>
            <li>이 관계를 이어가도 될지 모르겠어요</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # 대화 기록 렌더링
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            bubble_cls = "user-bubble-empathy" if msg.get("mode", "empathy") == "empathy" else "user-bubble-fact"
            st.markdown(f'<div class="{bubble_cls}">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            m_mode = msg.get("mode", "empathy")
            icon = "💛" if m_mode == "empathy" else "🔥"
            badge_cls = "badge-empathy" if m_mode == "empathy" else "badge-fact"
            badge_icon = "💡" if m_mode == "empathy" else "⚡"
            badge_html = f'<div class="{badge_cls}">{badge_icon} {msg.get("badge", "")}</div>' if msg.get("badge") else ""

            st.markdown(f"""
            <div style="display:flex; gap:10px; align-items:flex-start;">
                <div style="width:34px; height:34px; border-radius:10px; background:#FFFFFF; border:1px solid #E5DEC9; display:flex; align-items:center; justify-content:center; flex-shrink:0; box-shadow:0 2px 4px rgba(0,0,0,0.04);">
                    {icon}
                </div>
                <div class="ai-card" style="flex:1;">
                    {badge_html}
                    <div class="ai-body">{msg["content"]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 대화가 3턴 이상 진행되면 '환승연애 속마음 문자' 작성 유도 배너 표시
    user_turn_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    if user_turn_count >= 2:
        st.info("🌙 대화가 깊어졌어요. 오늘 밤 당신의 기준은 무엇인지 상단의 **[💌 내 생각 정리하기]**를 눌러 X-ROOM 포스트잇으로 남겨보세요.")

# =========================================================
# TAB 2: 요구사항 1 & 2 - 환승연애 오마주 'X-ROOM (기억의 방)'
# =========================================================
with tab_xroom:
    st.markdown("""
    <div class="xroom-wrapper">
        <div class="xroom-header">
            <div class="xroom-badge">EXchange HOMAGE ARCHIVE</div>
            <div class="xroom-title">🚪 X-ROOM : 기억과 기준의 방</div>
            <div class="xroom-desc">
                흩어졌던 감정 끝에 내가 직접 적어 내려간 속마음 포스트잇과,<br>
                그날 밤 우리가 나눴던 대화의 기록들이 전시되는 비밀 공간입니다.
            </div>
        </div>
    """, unsafe_allow_html=True)

    if len(st.session_state.x_room_notes) == 0:
        st.markdown("""
        <div style="text-align:center; padding: 40px 20px; color:#9E94A0; font-family:'RIDIBatang', serif;">
            <p style="font-size:2rem; margin-bottom:10px;">🕯️</p>
            <p style="font-size:0.95rem; margin-bottom:6px;">아직 X-ROOM에 남겨진 포스트잇이 없습니다.</p>
            <p style="font-size:0.8rem; color:#7A707D;">이음 라운지에서 대화를 나눈 뒤 <b>[💌 내 생각 정리하기]</b> 버튼을 눌러<br>첫 번째 속마음 포스트잇을 붙여보세요.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 1) 상단: 포스트잇 월 (Wall of Post-its)
        st.markdown("<h4 style='color:#FAF6EE; font-family:RIDIBatang, serif; font-size:1.05rem; margin-bottom:12px;'>📌 벽에 남겨진 속마음 포스트잇</h4>", unsafe_allow_html=True)

        cards_html = '<div class="postit-grid">'
        for note in st.session_state.x_room_notes:
            mode_tag = "💛 감성 공감 대화" if note["mode"] == "empathy" else "🔥 팩트 폭격 대화"
            cards_html += f"""
            <div class="postit-card {note['color']}">
                <div class="postit-time">{note['timestamp']} · {mode_tag}</div>
                <div class="postit-to">To. {note['topic']}</div>
                <div class="postit-standard">⚖️ 내 기준: {note['standard']}</div>
                <div class="postit-body">"{note['conclusion']}"</div>
            </div>
            """
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

        st.markdown("<hr style='border-color:rgba(255,255,255,0.12); margin: 28px 0 18px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#FAF6EE; font-family:RIDIBatang, serif; font-size:1.05rem; margin-bottom:12px;'>🎞️ 그날 밤의 대화 기록 열어보기</h4>", unsafe_allow_html=True)

        # 2) 하단: 각 포스트잇 작성 당시의 대화 기록 아카이브 열람
        for note in st.session_state.x_room_notes:
            with st.expander(f"📂 [{note['timestamp']}] {note['topic']} — 대화 기록 ({len(note['chat_snapshot'])}개의 메시지)"):
                if not note["chat_snapshot"]:
                    st.caption("대화 기록 없이 작성된 단독 포스트잇입니다.")
                else:
                    for m in note["chat_snapshot"]:
                        speaker = "🗣️ 나의 이야기" if m["role"] == "user" else "🤖 이음의 질문"
                        badge_txt = f" | 💡 {m.get('badge')}" if m.get("badge") else ""
                        st.markdown(f"**{speaker}{badge_txt}**")
                        st.markdown(f"> {m['content']}")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. 하단 채팅 입력창 (항상 하단 고정)
# ---------------------------------------------------------
user_input = st.chat_input("연애 고민을 편하게 이야기해 주세요")
if user_input:
    current_mode = st.session_state.mode
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "mode": current_mode
    })

    with st.spinner("이음이 생각의 기준을 정리하고 있어요..."):
        ai_data = generate_ai_response(st.session_state.messages, current_mode)
        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_data.get("message", ""),
            "badge": ai_data.get("summary_badge", ""),
            "mode": current_mode
        })
    st.rerun()
