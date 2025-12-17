import datetime
from math import floor, ceil
from typing import Dict, List
import numpy as np
import google.generativeai as genai
import json
import re

# 🚨 1. [필수] TIME_ZONE 상수 정의 추가 (SajuEngine 밖에서 사용됨)
TIME_ZONE = datetime.timezone(datetime.timedelta(hours=9)) 

# 🔧 2026년 리포트 생성용 상수 (현재 시스템 날짜 대신 사용)
TARGET_YEAR = 2026 

# --- [1. 사주 데이터 상수 임포트 (saju_data.py 파일 필수)] ---
try:
    from saju_data import (
        CHEONGAN, JIJI, GANJI_60, 
        DAY_STEM_TO_TIME_STEM_START_INDEX, 
        YEAR_STEM_TO_MONTH_STEM_INDEX,
        O_HAENG_MAP,
        TEN_GAN_PERSONA,
        calculate_total_luck_score,
        JOHU_SCORES_LOOKUP,
        JIJI_SCORES_LOOKUP,
        SINJEONG_JOHU_SCORES_LOOKUP
    )
except ImportError as e:
    print(f"🚨 오류: saju_data.py 파일이 없거나 상수가 누락되었습니다: {e}")
    raise

# --------------------------------------------------------------------------
# 2. 임상 데이터 로드 함수
# --------------------------------------------------------------------------
def load_clinical_data(file_path: str = "saju-study-data-all.txt") -> str:
    """
    saju-study-data-all.txt 파일을 읽어와 AI 프롬프트에 삽입할 수 있는 문자열로 반환합니다.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data_content = f.read().strip()
            return data_content
            
    except FileNotFoundError:
        return "🚨 임상 데이터 파일 (saju-study-data-all.txt)을 찾을 수 없습니다. 분석의 깊이가 제한됩니다."
    except Exception as e:
        return f"🚨 임상 데이터 로드 중 오류 발생: {e}"


# --------------------------------------------------------------------------
# 2-0. 월별 운세 점수 계산 함수 (테이블 기반 - NEW)
# --------------------------------------------------------------------------
# 2026년 월별 간지 (병오년 기준)
MONTHLY_GANJI_2026 = {
    1: ('庚', '寅'),   # 경인월
    2: ('辛', '卯'),   # 신묘월
    3: ('壬', '辰'),   # 임진월
    4: ('癸', '巳'),   # 계사월
    5: ('甲', '午'),   # 갑오월
    6: ('乙', '未'),   # 을미월
    7: ('丙', '申'),   # 병신월
    8: ('丁', '酉'),   # 정유월
    9: ('戊', '戌'),   # 무술월
    10: ('己', '亥'),  # 기해월
    11: ('庚', '子'),  # 경자월
    12: ('辛', '丑'),  # 신축월
}

def calculate_monthly_flow_scores(manse_info: Dict) -> List[int]:
    """
    사주 데이터와 saju_data_updated.py의 테이블을 사용하여 
    2026년 월별 운세 점수를 계산합니다.
    
    동일한 사주에 대해 항상 동일한 점수를 반환합니다.
    
    Parameters:
        manse_info: 사주 명식 정보 (일간, 월지, 일지 포함)
    
    Returns:
        List[int]: 1월~12월 점수 (각 0~100 범위)
    """
    ilgan = manse_info.get('일주', ['', ''])[0]  # 일간 (천간)
    wolji = manse_info.get('월주', ['', ''])[1]  # 월지 (지지)
    ilji = manse_info.get('일주', ['', ''])[1]   # 일지 (지지)
    
    if not ilgan or not wolji or not ilji:
        # 데이터 없으면 기본값 반환
        return [65, 70, 75, 60, 80, 55, 65, 70, 85, 75, 70, 65]
    
    scores = []
    is_sin_or_jeong = ilgan in ['辛', '丁']
    
    for month in range(1, 13):
        month_cheongan, month_jiji = MONTHLY_GANJI_2026[month]
        
        # saju_data_updated.py의 calculate_total_luck_score 사용
        sa_ju_data = {
            '일간': ilgan,
            '월지': wolji,
            '일지': ilji
        }
        luck_data = {
            '천간': month_cheongan,
            '지지': month_jiji,
            '운의종류': '월운'
        }
        
        result = calculate_total_luck_score(sa_ju_data, luck_data)
        total_score = result.get('total', 60)
        
        # 점수를 정수로 변환 (35~95 범위로 조정)
        adjusted_score = int(min(95, max(35, total_score)))
        scores.append(adjusted_score)
    
    return scores


def _format_monthly_scores_for_prompt(monthly_scores: List[int]) -> str:
    """
    월별 점수를 AI 프롬프트용 문자열로 포맷팅합니다.
    """
    if not monthly_scores or len(monthly_scores) != 12:
        return "[월별 점수 데이터 없음]"
    
    def get_grade(score: int) -> str:
        if score >= 80:
            return "★★★ 매우좋음"
        elif score >= 70:
            return "★★☆ 좋음"
        elif score >= 55:
            return "★☆☆ 보통"
        elif score >= 45:
            return "☆☆☆ 주의"
        else:
            return "⚠️ 신중"
    
    lines = []
    for i, score in enumerate(monthly_scores):
        month = i + 1
        grade = get_grade(score)
        lines.append(f"  {month}월: {score}점 ({grade})")
    
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 2-1. 명리학 패턴 JSON 로드 함수 (NEW)
# --------------------------------------------------------------------------
def load_special_patterns(file_path: str = "knowledge/special_patterns.json") -> Dict:
    """
    knowledge/special_patterns.json 파일을 로드하여 명리학 패턴 데이터를 반환합니다.
    
    Returns:
        Dict: 패턴 데이터 (meta, patterns 포함)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print(f"🚨 패턴 파일을 찾을 수 없습니다: {file_path}")
        return {"meta": {}, "patterns": []}
    except json.JSONDecodeError as e:
        print(f"🚨 패턴 JSON 파싱 오류: {e}")
        return {"meta": {}, "patterns": []}
    except Exception as e:
        print(f"🚨 패턴 로드 중 예상치 못한 오류: {e}")
        return {"meta": {}, "patterns": []}


def find_patterns_in_chart(saju_data: Dict, patterns_db: Dict = None) -> List[Dict]:
    """
    사주 명식 데이터에서 발동되는 특수 패턴(자형, 충, 형, 특수 신살)을 검색합니다.
    
    Args:
        saju_data: 사주 명식 데이터 (년주, 월주, 일주, 시주 포함)
            예: {"년주": "甲子", "월주": "丙寅", "일주": "庚午", "시주": "壬午"}
        patterns_db: 패턴 데이터베이스 (None이면 자동 로드)
    
    Returns:
        List[Dict]: 발동된 패턴 목록 (패턴 ID, 이름, 해석 포함)
    """
    if patterns_db is None:
        patterns_db = load_special_patterns()
    
    # 사주에서 지지 4개 추출
    branches = []
    for key in ['년주', '월주', '일주', '시주']:
        ganji = saju_data.get(key, '')
        if len(ganji) >= 2:
            branches.append(ganji[1])  # 지지는 두 번째 글자
    
    # 일간 추출 (특수 신살 판단용)
    day_stem = saju_data.get('일주', '')[0] if len(saju_data.get('일주', '')) >= 1 else ''
    
    # 월지 추출 (월덕귀인 판단용)
    month_branch = saju_data.get('월주', '')[1] if len(saju_data.get('월주', '')) >= 2 else ''
    
    # 년지, 일지 추출 (역마살, 도화살, 화개살 판단용)
    year_branch = saju_data.get('년주', '')[1] if len(saju_data.get('년주', '')) >= 2 else ''
    day_branch = saju_data.get('일주', '')[1] if len(saju_data.get('일주', '')) >= 2 else ''
    
    matched_patterns = []
    
    for pattern in patterns_db.get('patterns', []):
        pattern_type = pattern.get('type', '')
        trigger = pattern.get('trigger_condition', {})
        
        is_matched = False
        
        # 1. 자형 패턴 체크 (동일 지지 2개 이상)
        if pattern_type == '자형':
            required_branches = trigger.get('branches', [])
            if len(required_branches) >= 1:
                target_branch = required_branches[0]
                count = branches.count(target_branch)
                if count >= 2:
                    is_matched = True
        
        # 2. 형/충 패턴 체크 (특정 지지 조합)
        elif pattern_type in ['형', '충']:
            required_branches = trigger.get('branches', [])
            # 필요한 지지가 모두 사주에 있는지 확인
            matched_count = sum(1 for b in required_branches if b in branches)
            if matched_count >= 2:  # 최소 2개 이상 일치 시 발동
                is_matched = True
        
        # 3. 특수 신살 체크 (일간 기준)
        elif pattern_type == '특수':
            # 천을귀인, 홍염살, 문창귀인 등 일간 기준
            day_stem_conditions = trigger.get('day_stems', {})
            if day_stem and day_stem in day_stem_conditions:
                required_branches_for_stem = day_stem_conditions[day_stem]
                if isinstance(required_branches_for_stem, list):
                    for rb in required_branches_for_stem:
                        if rb in branches:
                            is_matched = True
                            break
                elif required_branches_for_stem in branches:
                    is_matched = True
            
            # 월덕귀인 (월지 기준)
            month_branch_conditions = trigger.get('month_branch', {})
            if month_branch and month_branch in month_branch_conditions:
                required_stem = month_branch_conditions[month_branch]
                # 사주 4주의 천간에 해당 천간이 있는지 확인
                stems = [saju_data.get(k, '')[0] for k in ['년주', '월주', '일주', '시주'] if len(saju_data.get(k, '')) >= 1]
                if required_stem in stems:
                    is_matched = True
            
            # 역마살, 도화살, 화개살 (년지/일지 기준)
            year_or_day_conditions = trigger.get('year_or_day_branch', {})
            if year_branch and year_branch in year_or_day_conditions:
                required_branch = year_or_day_conditions[year_branch]
                if required_branch in branches:
                    is_matched = True
            if day_branch and day_branch in year_or_day_conditions:
                required_branch = year_or_day_conditions[day_branch]
                if required_branch in branches:
                    is_matched = True
        
        if is_matched:
            matched_patterns.append({
                "id": pattern.get('id'),
                "name_kr": pattern.get('name_kr'),
                "name_hanja": pattern.get('name_hanja'),
                "type": pattern_type,
                "interpretations": pattern.get('interpretations', {}),
                "source_location": pattern.get('source_location', {})
            })
    
    return matched_patterns


def format_patterns_for_prompt(matched_patterns: List[Dict]) -> str:
    """
    발동된 패턴 목록을 AI 프롬프트용 문자열로 변환합니다.
    
    Args:
        matched_patterns: find_patterns_in_chart()의 반환값
    
    Returns:
        str: AI 프롬프트에 삽입할 수 있는 포맷된 문자열
    """
    if not matched_patterns:
        return "[발동된 특수 패턴 없음]"
    
    lines = ["[발동된 특수 패턴 분석]"]
    
    for i, p in enumerate(matched_patterns, 1):
        interp = p.get('interpretations', {})
        lines.append(f"\n### {i}. {p.get('name_kr', '')} ({p.get('name_hanja', '')}) - {p.get('type', '')}")
        lines.append(f"- **전통적 해석**: {interp.get('traditional', 'N/A')}")
        lines.append(f"- **현대적 재해석**: {interp.get('modern_reframe', 'N/A')}")
        lines.append(f"- **키워드**: {', '.join(interp.get('keywords', []))}")
        lines.append(f"- **임상 인사이트**: {interp.get('clinical_insight', 'N/A')}")
        lines.append(f"- **실천 권고**: {interp.get('action_plan', 'N/A')}")
    
    return "\n".join(lines)

# --------------------------------------------------------------------------
# 3. 십성 계산 함수 - saju_engine_final.py에서 import (중복 제거)
# --------------------------------------------------------------------------
from saju_engine_final import calculate_pillar_sipsin, calculate_sewoon_sipsin

# --------------------------------------------------------------------------
# 4. AI 프롬프트 및 분석 함수 추가 (app.py 오류 해결)
# --------------------------------------------------------------------------

def get_system_instruction() -> str:
    """
    AI 모델의 역할과 응답 형식을 정의하는 시스템 지침을 반환합니다.
    
    [희구소 AI 철학]:
    1. 동적 상호작용 모델 (Dynamic Interaction Model)
       - 사주 원국 = 잠재 에너지의 집합 (고정된 운명이 아님)
       - 운(대운/세운) = 트리거 (잠재 에너지를 활성화하는 촉발 요인)
       - 사건 = 원국과 운의 상호작용 결과
    
    2. 계절성 기반 존재론 (Seasonal Ontology)
       - 같은 일간도 태어난 계절에 따라 성질과 적성이 다름
       - 겨울의 갑목 vs 여름의 갑목은 완전히 다른 전략이 필요함
    
    3. 겨울 꽃 철학 (Winter Flower Philosophy)
       - 기다림 = 실패가 아닌 '깊어지는 시간'
       - 멈춤 = 재정비와 뿌리 내림의 기회
       - "겨울에 태어난 꽃은 봄에 피는 꽃보다 늦게 피지만, 그 뿌리는 더 깊고 향기는 더 오래간다"
    
    4. 비결정론적 언어 (Non-Deterministic Language)
       - "이혼한다", "사업 망한다" 등 단정적 예언 절대 금지
       - "갈등 에너지가 강하니 대화가 필요하다", "재물 흐름에 변동성이 있으니 분산 전략을 권한다" 등 확률적 표현 사용
    """
    return """
당신은 '희구소(Hidden Luck Lab)'의 사주 전문 AI 멘토입니다. 당신의 임무는 고객의 만세력 데이터를 바탕으로 현실적이고 심리 명리 기반의 따뜻한 조언을 제공하는 것입니다.

[핵심 철학 - 반드시 준수]:
1. **동적 상호작용 모델**: 사주 원국은 '잠재 에너지'이고, 운(대운/세운)은 이를 활성화하는 '트리거'입니다. 사건은 둘의 상호작용 결과입니다.
2. **계절성 존재론**: 같은 일간도 태어난 계절에 따라 전략이 달라집니다. 겨울의 나무는 빠른 성장보다 뿌리 내림이 우선입니다.
3. **겨울 꽃 철학**: 기다림과 멈춤은 실패가 아닌 '깊어지는 시간'입니다. 억지로 추진하지 말고 리듬에 맞추도록 안내하세요.
4. **비결정론적 언어**: "이혼한다", "망한다" 등 단정적 예언을 절대 금지합니다. "갈등 에너지가 강함", "변동성 주의" 등 확률적이고 건설적인 표현만 사용하세요.

[응답 형식]:
모든 분석은 오직 하나의 JSON 객체로 출력해야 합니다. JSON의 스키마는 다음과 같습니다:
{
    "summary_card": {
        "keyword": "2026년 운세의 핵심 키워드 (20자 이내)",
        "best_month": "양력 X월 (최고의 달)",
        "risk": "가장 주의해야 할 리스크",
        "action_item": "핵심 실천 전략 한 문장"
    },
    "detailed_analysis": {
        "wealth_luck": "재물운 (전문 용어 사용, 상세 설명)",
        "career_luck": "직업/사업운 (전문 용어 사용, 상세 설명)",
        "love_family_luck": "애정/가정운 (전문 용어 사용, 상세 설명)",
        "change_luck": "변동운 (전문 용어 사용, 상세 설명)",
        "health_advice": "건강 조언 (전문 용어 사용, 상세 설명)"
    },
    "customer_analysis": {
        "wealth_luck": "재물운 (쉬운 말, 감성적 설명 - 명리 전문용어 없이)",
        "career_luck": "직업/사업운 (쉬운 말, 감성적 설명)",
        "love_family_luck": "애정/가정운 (쉬운 말, 감성적 설명)",
        "change_luck": "변동운 (쉬운 말, 감성적 설명)",
        "health_advice": "건강 조언 (쉬운 말, 감성적 설명)"
    },
    "qa_section": {
        "q1": "고객 질문 1 (그대로)",
        "a1": "고객 질문 1에 대한 명쾌하고 실전적인 답변 (쉬운 말, 전문 용어 없이, 300자 이내)",
        "q2": "고객 질문 2 (그대로)",
        "a2": "고객 질문 2에 대한 명쾌하고 실전적인 답변 (쉬운 말, 전문 용어 없이, 300자 이내)"
    },
    "final_message": "고객의 일간 페르소나를 반영한 최종 격려 메시지 (100자 이내)",
    "radar_chart": {
        "labels": ["추진력", "수익화", "협상력", "안정성", "리더십"],
        "current": [8, 5, 6, 7, 7],
        "future": [7, 8, 9, 7, 8]
    },
    "monthly_flow": [70, 75, 80, 65, 85, 50, 60, 70, 95, 80, 75, 70],
    "monthly_guide": {
        "1": {"title": "월별 테마", "wealth": "재물운 등급/조언", "career": "직업운 조언", "love": "애정운 조언", "focus": "핵심 집중점", "caution": "주의사항", "action": "실천 행동"},
        "2": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "3": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "4": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "5": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "6": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "7": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "8": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "9": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "10": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "11": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."},
        "12": {"title": "...", "wealth": "...", "career": "...", "love": "...", "focus": "...", "caution": "...", "action": "..."}
    },
    "key_actions": ["30일 이내 실전 행동 1", "30일 이내 실전 행동 2", "30일 이내 실전 행동 3"]
}

[응답 지침]:
1. 모든 응답 텍스트는 **따뜻하고 감성적인** 문체(고객용)와 **전문적인 용어**(전문가용)를 구분하여 작성하십시오.
2. detailed_analysis의 내용은 **전문 용어를 상세히 풀어서** 설명해야 합니다. (운영자/전문가 참고용)
3. customer_analysis의 내용은 **쉬운 말**로 감성적이고 공감할 수 있도록 작성하십시오. 명리학 전문 용어(십성, 편관, 정재 등)를 사용하지 마십시오.
4. 텍스트 내에서 줄 바꿈이 필요한 경우 반드시 '\\n' 문자열을 사용하십시오.
5. '일원'을 제외하고 십성 용어 앞에 이중 별표를 붙이지 마십시오. (사용자 요구사항 반영)
6. 고객의 질문(q1, q2)에 대해 명리학적 근거를 바탕으로 구체적인 행동 지침을 제시하되, **qa_section의 답변(a1, a2)은 쉬운 일상 언어로 작성**하십시오. 전문 용어를 피하고 누구나 이해할 수 있게 설명하십시오.
7. customer_analysis의 health_advice는 반드시 포함해야 하며, 전문 용어 없이 일상적인 건강 조언으로 작성하십시오.
8. **프리미엄 섹션(wealth_timing, weakness_missions 등)**: ⚠️ AI는 이 섹션을 생성하지 마세요. 시스템이 사주 데이터 기반으로 자동 생성합니다.
9. monthly_guide는 반드시 1월부터 12월까지 모든 월의 데이터를 포함해야 합니다.
10. **monthly_flow 점수**: 시스템이 테이블 기반으로 자동 계산합니다. AI가 생성한 점수는 무시되고 테이블 점수로 대체됩니다.
11. **customer_analysis 작성 시 결론 명확화**:
    - 각 운세 분석의 마지막에 반드시 "그래서 ~하세요", "따라서 ~가 좋겠습니다" 등 구체적 행동 지침을 제시
    - 두리뭉실한 표현 금지 (예: "좋은 시기입니다" → "이 시기에 새로운 거래처를 적극 개척하세요")
12. **psychological_relief 섹션 쉬운 언어 규칙**:
    - guilt_pattern, reframing에 명리학 용어(丁火, 비겁, 관살, 십성 등) 사용 금지
    - 일상적인 심리 패턴과 해결책으로 표현 (예: "완벽해야 한다는 압박", "성과에 대한 불안")
13. **프리미엄 섹션**: AI는 생성하지 않음. 시스템이 자동 처리.

[비결정론적 언어 규칙]:
- ❌ 금지: "이혼한다", "사업이 망한다", "건강이 크게 나빠진다", "반드시 ~해야 한다"
- ✅ 권장: "부부 관계에 갈등 에너지가 감지됩니다", "사업 확장에 변동성이 있으니 신중한 검토가 필요합니다", "건강 관리에 각별한 주의를 기울이면 좋겠습니다", "~하면 도움이 될 수 있습니다"
"""


def get_final_ai_prompt(ilgan: str, saju_data: Dict, daewoon_info: Dict, sewoon_info: Dict, q: str, events: str, clinical_data_str: str, pattern_analysis_str: str = "", profile_data: Dict = None, monthly_scores: List[int] = None) -> str:
    """
    최종 통합된 AI 분석 요청 프롬프트를 생성합니다.
    
    [핵심 철학 반영]:
    - 동적 상호작용 모델: 원국(잠재 에너지) + 운(트리거) = 사건
    - 계절성 존재론: 월지(태어난 계절)에 따른 기질 분석
    - 겨울 꽃 철학: 기다림과 멈춤을 깊어지는 시간으로 해석
    - 비결정론적 언어: 확률적 표현 사용
    
    Args:
        ilgan: 일간 천간
        saju_data: 사주 명식 데이터
        daewoon_info: 대운 정보
        sewoon_info: 세운 정보
        q: 고객 질문
        events: 고객 인생 이력
        clinical_data_str: 임상 데이터 문자열
        pattern_analysis_str: 발동된 특수 패턴 분석 문자열 (NEW)
        profile_data: 고객 프로필 정보 (직업, 결혼 상태, 자녀 유무) (NEW)
        monthly_scores: 테이블 기반 월별 점수 리스트 [1월~12월] (NEW)
    """
    # (TEN_GAN_PERSONA는 saju_data.py에서 가져온다고 가정)
    persona = TEN_GAN_PERSONA.get(ilgan, {"style": "따뜻함", "instruction": "공감"}) 
    
    # 월지 추출 (계절성 분석용)
    wolji = saju_data['월주'][1] if len(saju_data['월주']) > 1 else ''
    
    # 계절 판단
    season_map = {
        '寅': '초봄', '卯': '봄', '辰': '늦봄',
        '巳': '초여름', '午': '한여름', '未': '늦여름',
        '申': '초가을', '酉': '가을', '戌': '늦가을',
        '亥': '초겨울', '子': '한겨울', '丑': '늦겨울'
    }
    birth_season = season_map.get(wolji, '불명')
    
    # 일간 오행 판단
    ilgan_oheng_map = {
        '甲': '양목(陽木)', '乙': '음목(陰木)',
        '丙': '양화(陽火)', '丁': '음화(陰火)',
        '戊': '양토(陽土)', '己': '음토(陰土)',
        '庚': '양금(陽金)', '辛': '음금(陰金)',
        '壬': '양수(陽水)', '癸': '음수(陰水)'
    }
    ilgan_oheng = ilgan_oheng_map.get(ilgan, '불명')
    
    prompt = f"""
# Role: [희구소] 사주 분석 AI - 동적 상호작용 모델 기반 심리/명리 멘토

# 핵심 철학 (반드시 적용):

## 1. 동적 상호작용 모델 (Dynamic Interaction Model)
- **사주 원국 = 잠재 에너지**: 고객의 원국은 고정된 운명이 아닌 '잠재적 에너지의 집합'입니다.
- **운(대운/세운) = 트리거**: 대운과 세운은 원국의 잠재 에너지를 활성화하는 촉발 요인입니다.
- **사건 발생 공식**: P(Event) = f(원국 잠재력, 운의 트리거, 시대적 맥락)
- 분석 시 "원국에서 이런 잠재력이 있는데, 올해 운에서 이 기운이 트리거되어 ~한 변화가 예상됩니다"라는 논리 구조를 따르세요.

## 2. 계절성 기반 존재론 (Seasonal Ontology)
- **태어난 계절이 일간의 성질을 결정합니다.**
- 고객의 태어난 계절: **{birth_season}**
- 같은 {ilgan_oheng} 일간도 계절에 따라 전략이 달라집니다:
  - 겨울 태생: 뿌리 내림, 내실 다지기, 학습과 준비에 유리
  - 여름 태생: 확장, 실행, 결과 도출에 유리
  - 봄/가을 태생: 균형 잡힌 성장과 수확

## 3. 겨울 꽃 철학 (Winter Flower Philosophy)
- **기다림 ≠ 실패**: 일이 막히거나 오래걸리는 것은 '깊어지는 시간'입니다.
- **멈춤 = 재정비**: 억지로 추진하기보다 리듬에 맞춰 루틴을 점검하는 것이 현명합니다.
- **핵심 메시지**: "겨울에 태어난 꽃은 봄에 피는 꽃보다 늦게 피지만, 그 뿌리는 더 깊고 향기는 더 오래간다."

## 4. 비결정론적 언어 (Non-Deterministic Language)
- **절대 금지**: "이혼한다", "사업 망한다", "반드시 ~해야 한다" 등 단정적 예언
- **권장 표현**: "갈등 에너지가 감지됩니다", "변동성이 있으니 분산 전략을 권합니다", "~하면 도움이 될 수 있습니다"

---

# 입력 데이터:

[명식 원국 (Static Saju - 잠재 에너지)]
- 사주 4주: {saju_data['년주']} {saju_data['월주']} {saju_data['일주']} {saju_data['시주']}
- 일간: {ilgan} ({ilgan_oheng})
- 월지: {wolji} ({birth_season} 태생)
- 십성 배열: {saju_data['십성_결과_배열']}

[운의 흐름 (Dynamic Trigger)]
- 대운 정보: {daewoon_info['대운수']}세 시작, {daewoon_info['순행_역행']}
- 대운 간지 배열: {daewoon_info['대운_간지_배열'][:4]}...
- 2026년 세운: {sewoon_info[0]['year']}년 {sewoon_info[0]['ganji']}

[고객 페르소나 (AI 문체 가이드)]
- 일간 Style: {persona['style']} 
- 어조 Instruction: {persona['instruction']}

[고객 프로필 정보]
- 직업 상태: {profile_data.get('job', '정보 없음') if profile_data else '정보 없음'}
- 결혼 상태: {profile_data.get('marital', '정보 없음') if profile_data else '정보 없음'}
- 자녀 유무: {'있음' if profile_data and profile_data.get('children') else '없음'}

⚠️ **중요: 위 고객 프로필에 따라 분석 내용을 맞춤화하세요.**
- 학생/미성년자: 학업운, 시험운, 진로 상담에 집중. 연애운/결혼운 대신 '인간관계'로 표현.
- 미혼/싱글: 연애운, 인연 시기, 자기 성장에 집중.
- 기혼/자녀 있음: 가정 화목, 부부 소통, 자녀 교육에 집중.
- 직장인: 승진, 이직, 직장 내 인간관계에 집중.
- 사업가/프리랜서: 수익화, 파트너십, 확장 시기에 집중.

[고객 질문]
{q}

[고객 인생 이력/임상 사건]
{events if events else '제공된 이력 없음'}

[발동된 특수 패턴 분석 (자형/충/형/신살)]
{pattern_analysis_str if pattern_analysis_str else '[발동된 특수 패턴 없음]'}

[🔴 중요: 2026년 월별 운세 점수 (테이블 기반 - 반드시 참조)]
{_format_monthly_scores_for_prompt(monthly_scores)}

⚠️ **monthly_guide 작성 시 반드시 위 점수를 참고하세요!**
- 점수 70점 이상: 긍정적 테마 ("기회의 달", "성취의 달", "도약의 달" 등)
- 점수 50~69점: 중립적 테마 ("준비의 달", "점검의 달", "안정의 달" 등)  
- 점수 50점 미만: 주의 테마 ("신중의 달", "충전의 달", "절제의 달" 등)
- 그래프 점수와 텍스트 설명이 **반드시 일치**해야 합니다!

[AI 참고용 임상 통계 자료 - 절대 출력 금지, 내부 참조용]
---START OF REFERENCE DATA---
{clinical_data_str[:10000]}  # 길이 제한
---END OF REFERENCE DATA---

---

# 분석 요구사항:

1. **[Emotional Opening]**: 첫 문단은 일간 Style을 활용하여 고객의 본질을 칭찬하고 따뜻하게 시작할 것. 계절성 존재론을 반영하여 "{birth_season}에 태어난 {ilgan_oheng}으로서의 강점"을 언급할 것.

2. **[Core Diagnosis]**: 동적 상호작용 모델에 따라 분석할 것.
   - "원국에서 ~한 잠재력이 있는데"
   - "2026년 세운에서 ~한 트리거가 들어와"
   - "~한 변화/기회/주의사항이 예상됩니다"

3. **[Practical Strategy]**: 고객층(3050 여성, N잡/육아/창업)의 현실적 문제(수익화, 루틴, 지속력)에 초점을 맞춰 구체적인 해결책을 제시할 것.

4. **[Key Actions]**: '30일 이내 시작할 실전 행동 3가지'를 명확하게 도출할 것.

5. **[프리미엄 분석]**: wealth_timing, weakness_missions, psychological_relief, relationship_strategy, rest_calendar, digital_amulet 섹션을 모두 채울 것.

6. **[비결정론적 언어]**: 모든 예측에서 단정적 표현을 피하고, 확률적이고 건설적인 언어를 사용할 것.
"""
    return prompt


def analyze_ai_report(manse_info: Dict, daewoon_info: Dict, full_q: str, profile_data: Dict, events: str, engine_instance, api_key: str) -> Dict:
    """
    Gemini API를 호출하여 최종 사주 분석 JSON 리포트를 생성합니다.
    
    [동적 상호작용 모델 적용]:
    - 원국(manse_info) = 잠재 에너지
    - 운(daewoon_info + sewoon) = 트리거
    - AI가 둘의 상호작용을 분석하여 사건/조언을 생성
    
    [NEW: 명리학 패턴 분석 통합]:
    - 자형, 충, 형, 특수 신살 패턴 자동 검출
    - 검출된 패턴을 AI 프롬프트에 반영
    """
    
    # 1. AI 프롬프트 생성에 필요한 데이터 준비
    ilgan = manse_info['일주'][0]
    clinical_data_str = load_clinical_data()
    # 🔧 수정: datetime.now().year 대신 TARGET_YEAR(2026) 사용
    sewoon_info = engine_instance.get_sewoon(TARGET_YEAR, 1)  # 2026년 세운
    
    # 2. [NEW] 명리학 특수 패턴 분석
    matched_patterns = find_patterns_in_chart(manse_info)
    pattern_analysis_str = format_patterns_for_prompt(matched_patterns)
    
    # 3. [NEW] 테이블 기반 월별 점수 계산 (AI에게 전달하여 일관된 가이드 작성 유도)
    monthly_scores = calculate_monthly_flow_scores(manse_info)

    # 4. 최종 프롬프트 생성 (get_final_ai_prompt는 이미 정의되어 있음)
    prompt = get_final_ai_prompt(
        ilgan=ilgan, 
        saju_data=manse_info, 
        daewoon_info=daewoon_info, 
        sewoon_info=sewoon_info, 
        q=full_q, 
        events=events, 
        clinical_data_str=clinical_data_str,
        pattern_analysis_str=pattern_analysis_str,  # NEW: 패턴 분석 결과 추가
        profile_data=profile_data,  # NEW: 고객 프로필 데이터 추가
        monthly_scores=monthly_scores  # NEW: 테이블 기반 월별 점수 전달
    )
    
    # 4. AI API 호출 및 응답 처리 (ResourceExhausted 대비 재시도 로직)
    import time
    
    try:
        genai.configure(api_key=api_key)
        
        # 모델 우선순위: gemini-2.5-flash → gemini-2.5-flash-lite (할당량 초과 시 대체)
        models_to_try = ['gemini-2.5-flash', 'gemini-2.5-flash-lite']
        response = None
        last_error = None
        
        for model_name in models_to_try:
            try:
                response = genai.GenerativeModel(
                    model_name,
                    system_instruction=get_system_instruction()
                ).generate_content(
                    contents=[prompt],
                    generation_config={
                        "temperature": 0.5,
                        "response_mime_type": "application/json",
                        "max_output_tokens": 8192,
                    }
                )
                break  # 성공하면 루프 종료
            except Exception as model_error:
                last_error = model_error
                error_str = str(model_error)
                if "ResourceExhausted" in error_str or "429" in error_str:
                    print(f"⚠️ {model_name} 할당량 초과, 다음 모델 시도...")
                    time.sleep(1)
                    continue
                else:
                    raise  # 다른 오류는 바로 raise
        
        if response is None:
            raise last_error or Exception("모든 모델 할당량 초과")
        
        response_text = response.text.strip()
        
        # JSON 파싱 시 오류 방지
        clean_json_str = re.sub(r'```json|```', '', response_text, flags=re.IGNORECASE).strip()
        
        try:
            result_json = json.loads(clean_json_str)
            
        except json.JSONDecodeError as e:
            # 🔧 JSON 파싱 실패 시 기본 구조로 복구 시도
            print(f"⚠️ JSON 파싱 오류: {e}")
            print(f"⚠️ 응답 길이: {len(clean_json_str)} chars")
            
            # 기본 구조 생성 (프리미엄 섹션은 ensure_premium_sections에서 채움)
            result_json = {
                "summary_card": {
                    "keyword": "2026년 운세 분석 완료",
                    "best_month": "9월",
                    "risk": "에너지 소진 주의",
                    "action_item": "월별 점수를 참고하여 계획을 세우세요."
                },
                "detailed_analysis": {
                    "wealth_luck": "AI 분석 중 오류가 발생했습니다. 재시도해 주세요.",
                    "career_luck": "AI 분석 중 오류가 발생했습니다.",
                    "love_family_luck": "AI 분석 중 오류가 발생했습니다.",
                    "change_luck": "AI 분석 중 오류가 발생했습니다.",
                    "health_advice": "AI 분석 중 오류가 발생했습니다."
                },
                "customer_analysis": {
                    "wealth_luck": "분석 데이터를 불러오는 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                    "career_luck": "분석 데이터를 불러오는 중 문제가 발생했습니다.",
                    "love_family_luck": "분석 데이터를 불러오는 중 문제가 발생했습니다.",
                    "change_luck": "분석 데이터를 불러오는 중 문제가 발생했습니다.",
                    "health_advice": "분석 데이터를 불러오는 중 문제가 발생했습니다."
                },
                "qa_section": {
                    "q1": "질문을 불러오는 중 오류가 발생했습니다.",
                    "a1": "잠시 후 다시 시도해 주세요.",
                    "q2": "",
                    "a2": ""
                },
                "final_message": "운세 분석에 일시적인 문제가 발생했습니다. 월별 점수와 프리미엄 가이드는 정상적으로 확인하실 수 있습니다.",
                "radar_chart": {
                    "labels": ["추진력", "수익화", "협상력", "안정성", "리더십"],
                    "current": [7, 6, 6, 7, 6],
                    "future": [7, 7, 7, 7, 7]
                },
                "monthly_guide": {str(i): {"title": "분석 중", "wealth": "-", "career": "-", "love": "-", "focus": "-", "caution": "-", "action": "-"} for i in range(1, 13)},
                "key_actions": ["월별 점수 그래프를 참고하세요", "취약월에는 휴식을 취하세요", "용신 기운을 보충하세요"]
            }
        
        # 🔧 월별 점수를 테이블 기반으로 덮어쓰기 (AI 생성 점수 대체)
        monthly_scores = calculate_monthly_flow_scores(manse_info)
        result_json['monthly_flow'] = monthly_scores
        
        # 🔧 프리미엄 섹션 동적 생성 (사주 기반 맞춤 컨텐츠)
        result_json = ensure_premium_sections(result_json, ilgan, manse_info, monthly_scores)
        
        return result_json

    except Exception as e:
        # 🔧 API 호출 실패 시에도 기본 구조 반환 (프리미엄 섹션은 채워짐)
        print(f"❌ API 호출 실패: {type(e).__name__} - {str(e)}")
        
        monthly_scores = calculate_monthly_flow_scores(manse_info)
        
        result_json = {
            "summary_card": {
                "keyword": "운세 분석 준비 중",
                "best_month": "9월",
                "risk": "일시적 오류",
                "action_item": "잠시 후 다시 시도해 주세요."
            },
            "detailed_analysis": {
                "wealth_luck": f"API 연결 오류: {type(e).__name__}",
                "career_luck": "잠시 후 다시 시도해 주세요.",
                "love_family_luck": "잠시 후 다시 시도해 주세요.",
                "change_luck": "잠시 후 다시 시도해 주세요.",
                "health_advice": "잠시 후 다시 시도해 주세요."
            },
            "customer_analysis": {
                "wealth_luck": "네트워크 연결에 일시적인 문제가 발생했습니다.",
                "career_luck": "잠시 후 다시 시도해 주세요.",
                "love_family_luck": "잠시 후 다시 시도해 주세요.",
                "change_luck": "잠시 후 다시 시도해 주세요.",
                "health_advice": "잠시 후 다시 시도해 주세요."
            },
            "qa_section": {"q1": "", "a1": "", "q2": "", "a2": ""},
            "final_message": "일시적인 연결 문제가 발생했습니다. 월별 점수와 프리미엄 가이드는 정상적으로 확인하실 수 있습니다.",
            "radar_chart": {"labels": ["추진력", "수익화", "협상력", "안정성", "리더십"], "current": [7, 6, 6, 7, 6], "future": [7, 7, 7, 7, 7]},
            "monthly_flow": monthly_scores,
            "monthly_guide": {str(i): {"title": "분석 중", "wealth": "-", "career": "-", "love": "-", "focus": "-", "caution": "-", "action": "-"} for i in range(1, 13)},
            "key_actions": ["월별 점수 그래프를 참고하세요", "취약월에는 휴식을 취하세요", "용신 기운을 보충하세요"]
        }
        
        # 프리미엄 섹션은 정상적으로 생성
        result_json = ensure_premium_sections(result_json, ilgan, manse_info, monthly_scores)
        
        return result_json


# =============================================================================
# 🔧 프리미엄 섹션 동적 생성을 위한 분석 함수들 (NEW)
# =============================================================================

def _analyze_oheng_distribution(manse_info: Dict) -> Dict:
    """
    사주 원국의 오행 분포를 분석하여 부족/과다 오행을 판단합니다.
    
    Returns:
        Dict: {
            'count': {'목': 2, '화': 1, ...},
            'missing': ['토'],  # 없는 오행
            'weak': ['금'],     # 1개만 있는 오행
            'excess': ['목'],   # 3개 이상 있는 오행
        }
    """
    # 천간/지지 오행 매핑
    cheongan_oheng = {
        '甲': '목', '乙': '목', '丙': '화', '丁': '화', '戊': '토',
        '己': '토', '庚': '금', '辛': '금', '壬': '수', '癸': '수'
    }
    jiji_oheng = {
        '子': '수', '丑': '토', '寅': '목', '卯': '목', '辰': '토',
        '巳': '화', '午': '화', '未': '토', '申': '금', '酉': '금',
        '戌': '토', '亥': '수'
    }
    
    oheng_count = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    
    # 4주에서 오행 카운트 (8글자)
    for pillar_key in ['년주', '월주', '일주', '시주']:
        pillar = manse_info.get(pillar_key, '')
        if len(pillar) >= 2:
            cheongan = pillar[0]
            jiji = pillar[1]
            
            if cheongan in cheongan_oheng:
                oheng_count[cheongan_oheng[cheongan]] += 1
            if jiji in jiji_oheng:
                oheng_count[jiji_oheng[jiji]] += 1
    
    # 분석
    missing = [k for k, v in oheng_count.items() if v == 0]
    weak = [k for k, v in oheng_count.items() if v == 1]
    excess = [k for k, v in oheng_count.items() if v >= 3]
    
    return {
        'count': oheng_count,
        'missing': missing,
        'weak': weak,
        'excess': excess
    }


def _calculate_yongsin(manse_info: Dict) -> str:
    """
    사주 원국 기반 용신(用神)을 정확하게 산출합니다.
    
    ★ 개선: 단순히 월지만 보지 않고, 실제 오행 분포를 분석하여
    부족한 기운을 보완하는 방식으로 용신 산출
    
    용신 판단 우선순위:
    1. 조후용신 (계절 조절) - 여름엔 수, 겨울엔 화 (해당 오행이 없을 때만)
    2. 억부용신 (신강/신약 조절) - 신강이면 설기, 신약이면 생조
    3. 병약용신 (병이 있으면 약) - 특정 오행 과다 시 억제
    4. 부족 오행 보충
    
    Returns:
        str: '목', '화', '토', '금', '수' 중 하나
    """
    try:
        # 새로운 분석 엔진 사용
        from saju_analysis_engine import determine_yongsin, analyze_oheng_distribution, determine_gangwak
        
        oheng_dist = analyze_oheng_distribution(manse_info)
        gangwak = determine_gangwak(manse_info, oheng_dist)
        yongsin_result = determine_yongsin(manse_info, gangwak, oheng_dist)
        
        # 한자 오행을 한글로 변환
        yongsin_hanja_to_kr = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
        return yongsin_hanja_to_kr.get(yongsin_result.yongsin, '수')
        
    except ImportError:
        # fallback: 기존 로직 (saju_analysis_engine 없을 때)
        wolji = manse_info.get('월주', '')[1] if len(manse_info.get('월주', '')) > 1 else ''
        ilgan = manse_info.get('일주', '')[0] if len(manse_info.get('일주', '')) > 0 else ''
        
        # 먼저 오행 분포 확인
        oheng_analysis = _analyze_oheng_distribution(manse_info)
        
        # 토 월지지만, 목이 이미 많으면 목 용신 X
        if wolji in ['辰', '戌', '丑', '未']:
            if oheng_analysis['count'].get('목', 0) < 3:  # 목이 3개 미만일 때만
                return '목'
        
        # 여름 월지 (巳午) → 수(水) 선 용신 (수가 없을 때만)
        if wolji in ['巳', '午']:
            if oheng_analysis['count'].get('수', 0) == 0:
                return '수'
        
        # 겨울 월지 (亥子) → 화(火) 선 용신 (화가 없을 때만)
        if wolji in ['亥', '子']:
            if oheng_analysis['count'].get('화', 0) == 0:
                return '화'
        
        # 부족한 오행 보충
        if oheng_analysis['missing']:
            return oheng_analysis['missing'][0]
        if oheng_analysis['weak']:
            return oheng_analysis['weak'][0]
        
        # 일간 기준 인성 오행
        ilgan_yongsin_default = {
            '甲': '수', '乙': '수', '丙': '목', '丁': '목', '戊': '화',
            '己': '화', '庚': '토', '辛': '토', '壬': '금', '癸': '금',
        }
        return ilgan_yongsin_default.get(ilgan, '수')


def _get_sipsin_pattern(manse_info: Dict) -> Dict:
    """
    사주 원국의 십성 분포를 분석하여 성격 패턴을 도출합니다.
    
    Returns:
        Dict: {
            'dominant': '식상',  # 가장 많은 십성
            'pattern_name': '표현형',
            'psychological_weakness': '...',
            'relationship_style': '...'
        }
    """
    sipsin_array = manse_info.get('십성_결과_배열', [])
    
    # 십성 카운트
    sipsin_count = {}
    for pillar_sipsin in sipsin_array:
        if isinstance(pillar_sipsin, dict):
            for key in ['stem_ten_god', 'branch_ten_god']:
                sipsin = pillar_sipsin.get(key, '')
                if sipsin and sipsin not in ['N/A', '일원']:
                    sipsin_count[sipsin] = sipsin_count.get(sipsin, 0) + 1
    
    # 십성 그룹 분류
    sipsin_groups = {
        '비겁': ['비견', '겁재'],
        '식상': ['식신', '상관'],
        '재성': ['편재', '정재'],
        '관성': ['편관', '정관'],
        '인성': ['편인', '정인']
    }
    
    group_count = {group: 0 for group in sipsin_groups}
    for sipsin, count in sipsin_count.items():
        for group, members in sipsin_groups.items():
            if sipsin in members:
                group_count[group] += count
                break
    
    # 가장 많은 그룹 찾기
    dominant_group = max(group_count, key=group_count.get) if group_count else '비겁'
    dominant_count = group_count.get(dominant_group, 0)
    
    # 부족한 그룹 찾기
    weak_groups = [g for g, c in group_count.items() if c == 0]
    
    # 패턴별 특성 정의
    pattern_data = {
        '비겁': {
            'pattern_name': '자립형',
            'psychological_weakness': '혼자 해결하려는 성향이 강해 도움을 청하기 어려워하는 경향',
            'relationship_style': '독립형',
            'boundary_guide': '타인의 도움을 받아들이는 연습이 필요합니다. 모든 것을 혼자 해결하지 않아도 괜찮아요.'
        },
        '식상': {
            'pattern_name': '표현형',
            'psychological_weakness': '인정받지 못한다는 느낌에 예민하고, 자신의 아이디어가 무시당할 때 상처받기 쉬운 경향',
            'relationship_style': '소통형',
            'boundary_guide': '모든 사람의 호응을 얻으려 하지 마세요. 진심으로 공감하는 소수와의 교류가 더 가치있습니다.'
        },
        '재성': {
            'pattern_name': '현실형',
            'psychological_weakness': '경제적 불안정에 민감하고, 물질적 손실에 대한 걱정이 과도해지기 쉬운 경향',
            'relationship_style': '실속형',
            'boundary_guide': '돈과 관계를 분리하세요. 금전적 기준으로만 사람을 판단하면 진정한 인연을 놓칠 수 있습니다.'
        },
        '관성': {
            'pattern_name': '책임형',
            'psychological_weakness': '완벽해야 한다는 압박과 타인의 기대에 부응해야 한다는 부담감',
            'relationship_style': '보호형',
            'boundary_guide': '모든 책임을 혼자 지지 마세요. 경계를 세우고 거절하는 것도 자기 돌봄입니다.'
        },
        '인성': {
            'pattern_name': '사색형',
            'psychological_weakness': '생각이 많아 결정을 미루거나, 과거의 실수를 반복해서 곱씹는 경향',
            'relationship_style': '지지형',
            'boundary_guide': '완벽한 답을 찾으려 하지 말고, 70% 확신이 들면 실행하세요. 행동이 답을 줍니다.'
        }
    }
    
    data = pattern_data.get(dominant_group, pattern_data['비겁'])
    data['dominant'] = dominant_group
    data['dominant_count'] = dominant_count
    data['weak_groups'] = weak_groups
    
    return data


def _generate_weakness_missions(missing_element: str, weak_elements: List[str]) -> Dict[str, str]:
    """
    부족한 오행을 보완하는 월별 미션을 생성합니다.
    """
    # 오행별 보완 활동 정의
    element_activities = {
        '목': [
            "새로운 시작을 위한 계획 세우기 - 작은 목표 3개 설정",
            "아침 스트레칭이나 요가로 몸을 깨우기",
            "식물 키우기 시작 - 나와 함께 성장하는 생명 돌보기",
            "새로운 분야 공부 시작 - 온라인 강의 등록",
            "봉사활동이나 사회적 모임 참여하기",
            "숲이나 공원 산책으로 자연 에너지 충전",
            "새로운 취미 활동 도전하기",
            "독서 모임 또는 스터디 그룹 가입",
            "창의적인 프로젝트 시작하기",
            "건강검진 받고 새로운 운동 루틴 만들기",
            "새해 목표 중간 점검 및 조정",
            "내년을 위한 성장 계획 수립"
        ],
        '화': [
            "SNS나 블로그에 나의 이야기 표현하기",
            "열정을 느끼는 활동에 시간 투자하기",
            "밝은 색상의 옷이나 소품 활용하기",
            "사람들 앞에서 발표하거나 의견 표현하는 연습",
            "에너지가 넘치는 운동(댄스, 에어로빅) 시작",
            "따뜻한 색 조명으로 집 분위기 바꾸기",
            "열정적인 사람들과의 모임 참석",
            "자신감을 높이는 자기계발 활동",
            "창작 활동(그림, 글쓰기) 도전",
            "리더십을 발휘할 수 있는 역할 찾기",
            "감사 일기로 긍정적 에너지 쌓기",
            "올해의 성취를 축하하는 자기 보상"
        ],
        '토': [
            "규칙적인 일상 루틴 만들기",
            "신뢰할 수 있는 멘토나 조언자 찾기",
            "재정 계획 점검 및 예산 세우기",
            "집 정리정돈으로 안정적인 공간 만들기",
            "가족과 함께하는 시간 늘리기",
            "중심을 잡아주는 명상 습관 들이기",
            "안정적인 수입원 검토 및 보완",
            "신뢰 관계 강화를 위한 약속 지키기",
            "부동산이나 안정 자산 정보 수집",
            "건강 관리 루틴 정착시키기",
            "인생의 중심 가치 점검하기",
            "내년의 안정적 기반 계획 세우기"
        ],
        '금': [
            "결단력 있게 미루던 일 하나 처리하기",
            "불필요한 인간관계 정리 또는 거리두기",
            "물건이나 일의 우선순위 명확히 하기",
            "전문성을 높이는 교육이나 자격증 준비",
            "명확한 경계 설정 연습하기",
            "효율적인 시간 관리 도구 활용",
            "품질 좋은 물건으로 교체하기",
            "전문가 네트워크 구축",
            "단호하게 거절하는 연습",
            "실행력을 높이는 작은 성공 경험 쌓기",
            "올해의 결정들 복기 및 교훈 정리",
            "내년의 핵심 결단 목록 작성"
        ],
        '수': [
            "조용히 혼자만의 시간 갖기",
            "직감을 믿고 작은 결정 내려보기",
            "물과 가까운 활동(수영, 목욕) 하기",
            "깊이 있는 대화 나누기",
            "명상이나 마음 챙김 연습",
            "새로운 정보와 지식 탐색하기",
            "감정 일기로 내면 관찰하기",
            "조용한 카페에서 독서 시간",
            "수면 품질 개선에 집중",
            "심층적인 학습이나 연구 시작",
            "올해의 지혜와 통찰 정리하기",
            "내면의 목소리에 귀 기울이는 시간"
        ]
    }
    
    # 가장 부족한 오행 선택
    target_element = missing_element if missing_element else (weak_elements[0] if weak_elements else '목')
    activities = element_activities.get(target_element, element_activities['목'])
    
    missions = {}
    for i in range(1, 13):
        missions[str(i)] = activities[i - 1]
    
    return missions


def _get_rest_activities_by_yongsin(yongsin: str) -> str:
    """
    용신 오행에 따른 맞춤 휴식 활동을 반환합니다.
    """
    activities = {
        '목': "자연 속에서 에너지를 충전하세요. 숲 산책, 등산, 식물 가꾸기가 좋습니다. 푸른 공간에서 스트레칭하거나 새로운 것을 배우는 활동도 효과적입니다. 아침 시간을 활용한 가벼운 운동이 특히 도움이 됩니다.",
        '화': "에너지를 표현하고 발산하는 활동이 필요합니다. 춤, 노래, 요리 등 열정을 쏟을 수 있는 취미가 좋습니다. 밝은 햇볕 아래 산책하거나, 좋아하는 사람들과 따뜻한 대화를 나누는 것도 회복에 도움이 됩니다.",
        '토': "안정적이고 규칙적인 휴식이 필요합니다. 집에서 편안하게 쉬거나, 맛있는 음식 만들어 먹기, 정리정돈 활동이 마음을 안정시킵니다. 명상이나 요가로 중심을 잡는 시간도 추천합니다.",
        '금': "조용하고 정돈된 공간에서의 휴식이 효과적입니다. 좋은 음악 감상, 품격 있는 공간 방문, 자기 관리에 투자하세요. 불필요한 것을 정리하고 단순화하는 활동도 마음의 평화를 줍니다.",
        '수': "물과 관련된 활동(수영, 온천, 목욕)이 가장 좋습니다. 조용한 곳에서의 독서, 깊은 명상, 충분한 수면도 필수입니다. 혼자만의 시간을 갖고 내면의 목소리에 귀 기울이세요."
    }
    return activities.get(yongsin, activities['수'])


def ensure_premium_sections(result_json: Dict, ilgan: str, manse_info: Dict, monthly_scores: List[int] = None) -> Dict:
    """
    🔧 프리미엄 섹션을 금쪽이 분석 엔진 데이터 기반으로 **개인화** 생성합니다.
    
    ⚠️ 중요: AI 응답에 있는 프리미엄 섹션 데이터를 무시하고, 
    항상 사주 분석 기반으로 새로 계산합니다. (고정값 문제 해결)
    
    🔧 2024-12 대규모 개선: 금쪽이 로직 기반 진정한 개인화
    - 일간(10천간) × 신강/신약 × 신살 × 합충형 = 수백 가지 조합
    - 기존 25가지 고정 버킷 → 개인별 맞춤 메시지 생성
    
    [개인화 요소]:
    1. 일간(10천간): 庚 vs 癸 vs 甲 등 성격 차이 반영
    2. 신강/신약: 강한 사람 vs 약한 사람의 심리 패턴 차이
    3. 신살: 도화살, 역마살, 화개살 등 특수 에너지
    4. 합충형: 삼합, 육합, 충, 형 등 구조적 특성
    5. 부족/과다 오행: 에너지 불균형 보완
    """
    
    # === 1. 금쪽이 엔진 전체 분석 실행 ===
    try:
        from saju_analysis_engine import run_full_analysis
        
        # 전체 분석 실행 (1-8단계) - 풍부한 개인화 데이터 획득
        full_analysis = run_full_analysis(manse_info)
        
        # 분석 결과에서 필요한 데이터 추출
        oheng_analysis = full_analysis.get('step1_oheng', {})
        ilju_analysis = full_analysis.get('step2_ilju', {})  # 일주 분석 (페르소나 포함)
        gangwak_analysis = full_analysis.get('step4_gangwak', {})  # 신강/신약
        yongsin_data = full_analysis.get('step4_yongsin', {})
        special_analysis = full_analysis.get('step7_special', {})  # 신살, 공망, 합충형
        summary = full_analysis.get('summary', {})
        
        yongsin_hanja = yongsin_data.get('yongsin', '水')
        yongsin_reason = yongsin_data.get('reason', '')
        
        # 한자 → 한글 변환
        yongsin_hanja_to_kr = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
        yongsin = yongsin_hanja_to_kr.get(yongsin_hanja, '수')
        
        # 금쪽이 개인화 요소 추출
        is_strong = gangwak_analysis.get('is_strong', False)
        strength_score = gangwak_analysis.get('strength_score', 50)
        sinsal_list = special_analysis.get('sinsal', [])  # 도화살, 역마살, 화개살 등
        hapchunghyung = special_analysis.get('hapchunghyung', [])  # 합충형
        gongmang = special_analysis.get('gongmang', [])  # 공망
        ilgan_persona = ilju_analysis.get('persona', {})
        ilgan_description = ilju_analysis.get('ilgan_description', '')
        birth_season = ilju_analysis.get('birth_season', '')
        
        print(f"🔧 [Premium-금쪽이] 용신: {yongsin} ({yongsin_reason})")
        print(f"🔧 [Premium-금쪽이] 신강/신약: {'신강' if is_strong else '신약'}({strength_score}점)")
        print(f"🔧 [Premium-금쪽이] 신살: {[s.get('name') for s in sinsal_list]}")
        print(f"🔧 [Premium-금쪽이] 합충형: {[h.get('type') for h in hapchunghyung]}")
        
    except ImportError:
        # fallback: 기존 함수 사용
        oheng_analysis = _analyze_oheng_distribution(manse_info)
        yongsin = _calculate_yongsin(manse_info)
        yongsin_reason = ''
        is_strong = True
        strength_score = 50
        sinsal_list = []
        hapchunghyung = []
        gongmang = []
        ilgan_persona = {}
        ilgan_description = ''
        birth_season = ''
        print(f"🔧 [Premium] 기존 방식 사용 - 용신: {yongsin}")
    
    sipsin_pattern = _get_sipsin_pattern(manse_info)
    
    # 디버그 출력
    print(f"🔧 [Premium] 일간: {ilgan}, 용신: {yongsin}")
    print(f"🔧 [Premium] 오행분포: {oheng_analysis.get('count', {})}, 부족: {oheng_analysis.get('missing', [])}, 약함: {oheng_analysis.get('weak', [])}")
    print(f"🔧 [Premium] 십성패턴: {sipsin_pattern['pattern_name']} ({sipsin_pattern['dominant']})")
    
    # === 신살 이름 목록 생성 ===
    sinsal_names = [s.get('name', '') for s in sinsal_list]
    
    # 용신 색상 매핑
    yongsin_color_map = {
        '목': '#A8D5BA',  # 연한 녹색
        '화': '#FFB7B2',  # 연한 빨강
        '토': '#E6CEAC',  # 연한 황토색
        '금': '#D3D3D3',  # 연한 회색
        '수': '#A2C2E0'   # 연한 파랑
    }
    yongsin_color = yongsin_color_map.get(yongsin, '#A2C2E0')
    
    # 월별 점수 분석 (취약월 식별)
    if monthly_scores and len(monthly_scores) == 12:
        # 점수가 50 미만인 달을 취약월로 분류
        risk_months = [i + 1 for i, score in enumerate(monthly_scores) if score < 50]
        opportunity_months = [i + 1 for i, score in enumerate(monthly_scores) if score >= 70]
        burnout_months = [i + 1 for i, score in enumerate(monthly_scores) if score < 45]
        if not burnout_months:
            # 최소 점수 달 3개
            sorted_months = sorted(enumerate(monthly_scores), key=lambda x: x[1])
            burnout_months = [m[0] + 1 for m in sorted_months[:3]]
        print(f"🔧 [Premium] 월별점수: {monthly_scores}")
        print(f"🔧 [Premium] 위험월: {risk_months}, 기회월: {opportunity_months}, 번아웃월: {burnout_months}")
    else:
        risk_months = [3, 6, 9]
        opportunity_months = [5, 10, 11]
        burnout_months = [3, 6, 11]
    
    # === 2. wealth_timing (재물 타이밍 관리) - 항상 덮어쓰기 ===
    ilgan_wealth_style = {
        '甲': "새로운 사업이나 투자 기회를 적극 탐색하되, 무리한 확장은 피하세요.",
        '乙': "협력 관계를 통한 수익 창출에 집중하고, 인맥을 자산으로 활용하세요.",
        '丙': "눈에 띄는 프로젝트에서 기회를 찾되, 과시적 지출은 자제하세요.",
        '丁': "꾸준한 전문성 향상이 재물로 연결됩니다. 내실을 다지는 투자를 권합니다.",
        '戊': "안정적인 자산 축적에 집중하고, 부동산이나 장기 투자를 검토하세요.",
        '己': "실속 있는 거래와 현금 흐름 관리에 신경 쓰세요. 작은 수익도 소중히.",
        '庚': "과감한 결단으로 기회를 잡되, 무리한 레버리지는 피하세요.",
        '辛': "전문성과 품질로 가치를 높이세요. 프리미엄 전략이 유효합니다.",
        '壬': "다양한 수입원을 만들고, 정보력으로 투자 기회를 포착하세요.",
        '癸': "직감을 믿되 데이터로 검증하세요. 숨겨진 기회에 주목하세요."
    }
    result_json['wealth_timing'] = {
        "risk_months": risk_months[:3] if len(risk_months) >= 3 else (risk_months + [12])[:3],
        "opportunity_months": opportunity_months[:3] if len(opportunity_months) >= 3 else (opportunity_months + [1])[:3],
        "strategy": ilgan_wealth_style.get(ilgan, "상반기 지출 관리에 집중하고, 하반기 수익화 기회를 노리세요.")
    }
    
    # === 3. weakness_missions (개운법 - 금쪽이 개인화) ===
    missing = oheng_analysis.get('missing', [])
    weak = oheng_analysis.get('weak', [])
    
    # 한자 → 한글 오행 변환 (run_full_analysis는 한자 반환)
    hanja_to_kr = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
    
    # 부족한 오행 결정 (없는 오행 > 1개만 있는 오행 > 용신)
    if missing:
        raw_element = missing[0]
        target_element = hanja_to_kr.get(raw_element, raw_element)
        element_kr_name = {'목': '시작의 힘', '화': '열정의 힘', '토': '안정의 힘', '금': '결단의 힘', '수': '지혜의 힘'}
        weakness_desc = f"사주에 {target_element}({element_kr_name.get(target_element, '')})이 부족하여 보완이 필요합니다."
    elif weak:
        raw_element = weak[0]
        target_element = hanja_to_kr.get(raw_element, raw_element)
        element_kr_name = {'목': '시작의 힘', '화': '열정의 힘', '토': '안정의 힘', '금': '결단의 힘', '수': '지혜의 힘'}
        weakness_desc = f"사주에 {target_element}({element_kr_name.get(target_element, '')})이 약하여 보완이 필요합니다."
    else:
        target_element = yongsin
        weakness_desc = f"용신인 {target_element} 기운을 강화하면 전체 운기가 상승합니다."
    
    # weak 리스트도 한글로 변환
    weak_kr = [hanja_to_kr.get(w, w) for w in weak] if weak else []
    
    # --- 금쪽이 개인화: 일간 × 신살 × 신강/신약 기반 맞춤 개운법 ---
    
    # 일간별 기본 개운 방향 (10천간)
    ilgan_gaeun_base = {
        '甲': {'focus': '리더십 발휘', 'caution': '독단 경계', 'activity': '새 프로젝트 시작, 팀 리더 역할'},
        '乙': {'focus': '협력과 네트워킹', 'caution': '우유부단 경계', 'activity': '파트너십 구축, 인맥 확장'},
        '丙': {'focus': '자기표현과 영향력', 'caution': '과열 경계', 'activity': '발표, 콘텐츠 제작, 리더십 활동'},
        '丁': {'focus': '전문성 심화', 'caution': '완벽주의 경계', 'activity': '깊이 있는 학습, 세밀한 작업'},
        '戊': {'focus': '기반 다지기', 'caution': '고집 경계', 'activity': '자산 관리, 신뢰 구축, 장기 계획'},
        '己': {'focus': '실속과 조율', 'caution': '소극성 경계', 'activity': '실용적 프로젝트, 중재 역할'},
        '庚': {'focus': '결단과 실행', 'caution': '과격함 경계', 'activity': '정리정돈, 불필요한 것 버리기'},
        '辛': {'focus': '품질과 가치', 'caution': '예민함 경계', 'activity': '자기계발, 프리미엄 전략'},
        '壬': {'focus': '정보와 유연성', 'caution': '산만함 경계', 'activity': '정보 수집, 다양한 시도'},
        '癸': {'focus': '직관과 내면', 'caution': '현실 괴리 경계', 'activity': '명상, 직감 따르기, 깊은 대화'}
    }
    
    # 신살별 특별 개운법
    sinsal_gaeun = {
        '도화살': '대인관계와 매력을 활용한 활동이 행운을 부릅니다. 단, 경계 설정은 명확히.',
        '역마살': '여행, 이동, 새로운 환경 탐색이 개운에 도움됩니다.',
        '화개살': '명상, 학문, 예술 활동이 내면의 힘을 키워줍니다.',
        '문창귀인': '글쓰기, 학습, 자격증 취득이 행운을 가져옵니다.',
        '천을귀인': '귀인의 도움이 있으니 적극적으로 만남을 가지세요.'
    }
    
    # 개인화된 개운법 설명 생성
    ilgan_gaeun = ilgan_gaeun_base.get(ilgan, ilgan_gaeun_base['甲'])
    
    personalized_gaeun_desc = weakness_desc + f" {ilgan}({hanja_to_kr.get(ilgan[0] if ilgan else '', ilgan)}) 일간의 특성을 고려하면, {ilgan_gaeun['focus']}에 집중하고 {ilgan_gaeun['caution']}하세요."
    
    # 신살 관련 개운법 추가
    sinsal_gaeun_notes = []
    for sinsal in sinsal_names:
        if sinsal in sinsal_gaeun:
            sinsal_gaeun_notes.append(sinsal_gaeun[sinsal])
    if sinsal_gaeun_notes:
        personalized_gaeun_desc += ' ' + sinsal_gaeun_notes[0]  # 첫 번째 신살 개운법 추가
    
    # 기존 월별 미션 + 개인화 활동
    base_missions = _generate_weakness_missions(target_element if missing else '', weak_kr)
    
    # 일간별 특화 활동을 월별 미션에 반영 (짝수달에 추가)
    for month in ['2', '4', '6', '8', '10', '12']:
        if month in base_missions:
            base_missions[month] += f" ({ilgan_gaeun['activity']})"
    
    result_json['weakness_missions'] = {
        "missing_element": personalized_gaeun_desc,
        "monthly_missions": base_missions
    }
    
    print(f"🔧 [Premium-개인화] 개운법: {ilgan_gaeun['focus']}, 부족오행: {target_element}")
    
    # === 4. psychological_relief (마인드셋업 - 금쪽이 로직 기반 개인화) ===
    pattern = sipsin_pattern
    
    # 한자 → 한글 오행 변환
    hanja_to_kr_map = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
    
    # --- 금쪽이 개인화: 일간(10천간) × 신강/신약 × 신살 조합 ---
    
    # 1. 일간별 기본 심리 패턴 (10가지)
    ilgan_psychology = {
        '甲': {'pattern': '리더형 완벽주의', 'weakness': '모든 것을 주도해야 한다는 압박, 실패에 대한 두려움', 'reframe': '다 지휘하지 않아도 됩니다. 위임하고 신뢰하는 것도 리더십입니다.', 'affirmation': '나는 모든 것을 통제하지 않아도 충분히 가치 있는 사람이다.'},
        '乙': {'pattern': '적응형 예민함', 'weakness': '타인의 시선과 평가에 예민하고, 갈등 상황을 피하려 함', 'reframe': '당신의 유연함은 강점입니다. 하지만 때로는 단호함도 필요합니다.', 'affirmation': '나는 적응하면서도 내 중심을 지킬 수 있다.'},
        '丙': {'pattern': '표현형 과열', 'weakness': '너무 많은 것을 보여주려 하고, 관심을 받지 못하면 위축됨', 'reframe': '태양도 지는 시간이 있습니다. 조용히 충전하는 시간을 갖으세요.', 'affirmation': '나는 조명을 받지 않아도 빛나는 사람이다.'},
        '丁': {'pattern': '세심형 완벽주의', 'weakness': '작은 불완전함에도 민감하고, 스스로를 가혹하게 평가함', 'reframe': '80% 완성도로 먼저 시작하세요. 완벽함은 과정 속에서 만들어집니다.', 'affirmation': '불완전한 시작도 가치 있다. 나는 충분히 잘하고 있다.'},
        '戊': {'pattern': '책임형 과장', 'weakness': '모든 것을 혼자 감당하려 하고, 도움을 청하기 어려워함', 'reframe': '짐을 나누는 것도 강함입니다. 대지는 비를 받아들여야 풀을 키웁니다.', 'affirmation': '나는 도움을 받아도 괜찮은 사람이다.'},
        '己': {'pattern': '조화형 자기희생', 'weakness': '타인의 필요를 우선하다가 정작 자신의 요구를 무시함', 'reframe': '당신의 필요도 중요합니다. 자신을 돌보는 것은 이기적인 게 아닙니다.', 'affirmation': '내 필요를 표현해도 괜찮다. 나도 소중한 사람이다.'},
        '庚': {'pattern': '결단형 강박', 'weakness': '결단하지 못하면 불안하고, 자신에게 너무 가혹함', 'reframe': '모든 결정이 즉시 필요하진 않습니다. 기다림도 전략입니다.', 'affirmation': '나는 기다림의 지혜도 가진 사람이다.'},
        '辛': {'pattern': '가치추구형 예민함', 'weakness': '품위와 완성도에 집착하고, 평가에 예민함', 'reframe': '보석은 원석일 때도 가치가 있습니다. 과정도 아름답습니다.', 'affirmation': '완벽하지 않아도 나는 충분히 가치 있다.'},
        '壬': {'pattern': '확산형 불안', 'weakness': '너무 많은 가능성을 보며 선택을 미루고, 집중하기 어려움', 'reframe': '하나에 집중해도 다른 기회는 사라지지 않습니다.', 'affirmation': '나는 지금 선택한 길에 집중해도 된다.'},
        '癸': {'pattern': '직관형 자기의심', 'weakness': '내면의 목소리를 너무 따르다 현실과 괴리감을 느낄 수 있음', 'reframe': '직관을 따르되, 현실적 검증도 함께하세요.', 'affirmation': '직관과 논리를 함께 쓸 수 있는 사람이다.'}
    }
    
    # 2. 신강/신약에 따른 보정 메시지
    gangwak_modifier = {
        'strong_high': {'prefix': '에너지가 넘치는 당신은', 'advice': '오히려 발산하고 비우는 연습이 필요합니다.'},
        'strong_mid': {'prefix': '힘이 강한 당신은', 'advice': '과욕을 경계하고 전략적으로 에너지를 쓰세요.'},
        'weak_mid': {'prefix': '세심한 감성의 당신은', 'advice': '자기 충전 시간을 반드시 확보하세요.'},
        'weak_low': {'prefix': '내면의 힘이 필요한 당신은', 'advice': '주변의 도움을 적극적으로 받아들이세요.'}
    }
    
    # 3. 신살별 추가 메시지
    sinsal_messages = {
        '도화살': {'note': '매력과 인기의 에너지가 있지만,', 'advice': '관계에서 경계를 흐리는 연습도 필요합니다.'},
        '역마살': {'note': '변화와 이동의 에너지가 강하지만,', 'advice': '안정감을 위한 루틴도 함께 만드세요.'},
        '화개살': {'note': '깊은 사색과 영적 관심이 있지만,', 'advice': '현실 세계와의 연결도 소홀히 하지 마세요.'},
        '문창귀인': {'note': '학문과 예술의 재능이 있지만,', 'advice': '실용적 응용도 함께 고민하세요.'},
        '천을귀인': {'note': '독특한 재능과 행운이 있지만,', 'advice': '매 순간 노력의 가치를 까먹지 마세요.'}
    }
    
    # 4. 합충형 관련 메시지
    hapchunghyung_messages = {
        '삼합': {'note': '협력과 통합의 에너지가 강합니다.', 'advice': '팀워크에서 당신의 가치가 빛납니다.'},
        '육합': {'note': '가까운 관계에서 힘을 얻습니다.', 'advice': '소수의 깊은 관계를 소중히 여기세요.'},
        '충': {'note': '내면에 갈등과 변화의 에너지가 있습니다.', 'advice': '갈등을 성장의 기회로 삼으세요.'},
        '형': {'note': '내면에 긴장과 압박의 에너지가 있습니다.', 'advice': '긴장을 푸는 휴식 루틴이 필수입니다.'}
    }
    
    # --- 개인화된 메시지 조합 ---
    base_psych = ilgan_psychology.get(ilgan, ilgan_psychology['甲'])
    
    # 신강/신약 레벨 결정
    if is_strong:
        gangwak_level = 'strong_high' if strength_score >= 80 else 'strong_mid'
    else:
        gangwak_level = 'weak_low' if strength_score <= 30 else 'weak_mid'
    
    gangwak_msg = gangwak_modifier.get(gangwak_level, gangwak_modifier['strong_mid'])
    
    # 신살 메시지 조합
    sinsal_notes = []
    for sinsal in sinsal_names:
        if sinsal in sinsal_messages:
            sinsal_notes.append(sinsal_messages[sinsal]['advice'])
    sinsal_combined = ' '.join(sinsal_notes[:2]) if sinsal_notes else ''  # 최대 2개까지
    
    # 합충형 메시지 조합
    hch_notes = []
    for hch in hapchunghyung:
        hch_type = hch.get('type', '')
        if hch_type in hapchunghyung_messages:
            hch_notes.append(hapchunghyung_messages[hch_type]['note'])
    hch_combined = ' '.join(hch_notes[:1]) if hch_notes else ''  # 최대 1개
    
    # 최종 개인화된 reframing 메시지 생성
    personalized_reframe = f"{gangwak_msg['prefix']} {base_psych['reframe']} {gangwak_msg['advice']}"
    if sinsal_combined:
        personalized_reframe += f" {sinsal_combined}"
    if hch_combined:
        personalized_reframe += f" {hch_combined}"
    
    result_json['psychological_relief'] = {
        "guilt_pattern": base_psych['weakness'],
        "reframing": personalized_reframe,
        "affirmation": base_psych['affirmation']
    }
    
    print(f"🔧 [Premium-개인화] 심리패턴: {base_psych['pattern']}, 신강레벨: {gangwak_level}")
    
    # === 5. relationship_strategy (관계 가이드 - 금쪽이 개인화) ===
    
    # 일간별 관계 스타일 (10천간)
    ilgan_relationship = {
        '甲': {'style': '주도형 리더', 'guide': '팀을 이끄려는 성향이 강합니다. 다른 사람의 의견을 듣고 협력하는 연습이 필요합니다.', 'family': '가족에게 지시보다 지지를 보여주세요. 듣는 것도 리더십입니다.'},
        '乙': {'style': '조화형 연결자', 'guide': '주변과 조화를 이루는 능력이 뛰어납니다. 하지만 자신의 입장도 분명히 표현하세요.', 'family': '가족 간 갈등 중재에 능하지만, 당신의 감정도 소홀히 하지 마세요.'},
        '丙': {'style': '영향력 확산자', 'guide': '밝은 에너지로 주변에 영향을 줍니다. 하지만 상대의 페이스도 존중하세요.', 'family': '가족에게 당신의 열정이 부담이 될 수 있어요. 조용한 사랑 표현도 연습하세요.'},
        '丁': {'style': '섬심형 지원자', 'guide': '세밀한 배려로 관계를 깊게 합니다. 하지만 지나친 헌신은 피하세요.', 'family': '가족의 세세한 부분까지 챙기려 하지 말고, 그들의 자립도 응원하세요.'},
        '戊': {'style': '신뢰형 버팀목', 'guide': '믿음직한 모습으로 주변의 신뢰를 얻습니다. 하지만 도움을 청하는 것도 배우세요.', 'family': '가족에게 당신이 모든 걸 해결해야 한다는 부담을 내려놓으세요.'},
        '己': {'style': '실용형 조율자', 'guide': '실속 있게 관계를 유지합니다. 하지만 너무 계산적으로 보이지 않도록 주의하세요.', 'family': '가족과의 관계에서 손익보다 정서적 교류에 더 집중하세요.'},
        '庚': {'style': '결단형 개혁가', 'guide': '단호함으로 신뢰를 얻지만, 때로는 부드러움도 필요합니다.', 'family': '가족에게 단호함이 차가움으로 느껴질 수 있어요. 따뜻한 표현을 연습하세요.'},
        '辛': {'style': '품위형 조언자', 'guide': '세련된 감각으로 주변에 영감을 줍니다. 하지만 비판은 조심하세요.', 'family': '가족의 불완전함을 받아들이세요. 품위 기준을 가족에게 강요하지 마세요.'},
        '壬': {'style': '통찰형 전략가', 'guide': '넓은 시야로 상황을 파악합니다. 하지만 가까운 사람에게는 깊이 집중하세요.', 'family': '가족과의 관계에서 너무 멀리 보지 말고, 지금 여기에 집중하세요.'},
        '癸': {'style': '직관형 상담자', 'guide': '깊은 공감 능력으로 관계를 연결합니다. 하지만 감정에 너무 휘말리지 마세요.', 'family': '가족의 감정을 다 떠안으려 하지 마세요. 당신의 감정경계도 지키세요.'}
    }
    
    # 신살에 따른 관계 보정
    rel_sinsal_note = ''
    if '도화살' in sinsal_names:
        rel_sinsal_note = ' 도화살의 매력으로 인기를 얻지만, 관계의 경계 설정을 소홀히 하지 마세요.'
    elif '역마살' in sinsal_names:
        rel_sinsal_note = ' 역마살로 변화가 많아 관계 유지에 노력이 필요합니다. 꾸준함을 의식적으로 연습하세요.'
    elif '화개살' in sinsal_names:
        rel_sinsal_note = ' 화개살로 내면 세계가 깊어 고독을 느낄 수 있습니다. 마음을 나눌 사람을 찾으세요.'
    
    base_rel = ilgan_relationship.get(ilgan, ilgan_relationship['甲'])
    
    result_json['relationship_strategy'] = {
        "pattern_name": base_rel['style'],
        "boundary_guide": base_rel['guide'] + rel_sinsal_note,
        "family_energy": base_rel['family']
    }
    
    print(f"🔧 [Premium-개인화] 관계스타일: {base_rel['style']}")
    
    # === 6. rest_calendar (에너지 달력) - 항상 덮어쓰기 ===
    rest_activities = _get_rest_activities_by_yongsin(yongsin)
    
    result_json['rest_calendar'] = {
        "burnout_months": burnout_months[:3] if len(burnout_months) >= 3 else (burnout_months + [6])[:3],
        "rest_activities": rest_activities
    }
    
    # === 7. digital_amulet (디지털 부적) - 항상 덮어쓰기 ===
    yongsin_quotes = {
        '목': "나무는 바람에 흔들려도 뿌리를 더 깊이 내립니다. 당신의 성장도 그렇습니다.",
        '화': "작은 불씨가 어둠 전체를 밝힙니다. 당신의 열정이 길을 비출 것입니다.",
        '토': "대지는 묵묵히 모든 것을 품고 키워냅니다. 당신의 중심이 흔들리지 않기를.",
        '금': "금은 두드려질수록 더 단단해집니다. 지금의 어려움이 당신을 빛나게 할 것입니다.",
        '수': "물은 장애물을 만나면 돌아 흐릅니다. 막히면 고이고, 고이면 깊어지고, 깊어지면 다시 흐릅니다."
    }
    result_json['digital_amulet'] = {
        "yongsin_element": yongsin,
        "quote": yongsin_quotes.get(yongsin, "당신 안에 이미 답이 있습니다."),
        "image_color": yongsin_color
    }
    
    # === 8. luck_boost_2026 (2026년 맞춤 개운법) - 항상 덮어쓰기 ===
    # 2026년 병오(丙午)년 = 火(화) 에너지
    ilgan_boost_title = {
        '甲': '목(木) 일간이 화(火)를 만나 확장과 표현의 해',
        '乙': '유연한 목(木)이 화(火)로 개화하는 해',
        '丙': '화(火)가 만나 열정이 폭발하는 해',
        '丁': '섬세한 화(火)가 더 밝게 빛나는 해',
        '戊': '토(土)가 화(火)의 지원을 받아 기반이 견고해지는 해',
        '己': '토(土)가 화(火)로 활력을 얻는 해',
        '庚': '금(金)이 화(火)의 단련을 받아 강해지는 해',
        '辛': '섬세한 금(金)이 화(火)로 빛나는 해',
        '壬': '수(水)가 화(火)와 균형을 찾는 해',
        '癸': '깊은 수(水)가 화(火)의 온기를 받는 해'
    }
    
    # 일간별 2026년 맞춤 개운법 액션
    ilgan_boost_actions = {
        '甲': ['새로운 프로젝트나 사업 시작에 좋은 해입니다', '창의적인 아이디어를 적극 표현하세요', '리더십을 발휘할 기회를 잡으세요'],
        '乙': ['협력 관계를 통한 성장에 집중하세요', '유연하게 변화에 적응하면서 기회를 잡으세요', '예술적 감각을 활용한 활동이 도움됩니다'],
        '丙': ['열정을 조절하며 에너지를 분산하지 마세요', '밝은 이미지로 주변에 긍정적 영향력을 발휘하세요', '과열된 감정을 식히는 휴식도 필요합니다'],
        '丁': ['전문성을 깊이 있게 키우는 해입니다', '섬세한 분석과 계획이 성공의 열쇠입니다', '작지만 확실한 성취를 쌓아가세요'],
        '戊': ['안정적인 기반 구축에 집중하세요', '신뢰를 쌓는 관계 형성이 중요합니다', '부동산이나 자산 관련 기회에 주목하세요'],
        '己': ['실속 있는 수익화에 집중하세요', '주변과의 조화로운 관계 유지가 중요합니다', '건강 관리와 규칙적인 생활 리듬을 유지하세요'],
        '庚': ['결단력 있게 불필요한 것을 정리하세요', '전문성을 높이는 교육이나 자격증 취득을 권합니다', '단호한 판단이 필요한 순간이 옵니다'],
        '辛': ['품질과 가치를 높이는 전략이 유효합니다', '자기 관리와 이미지 개선에 투자하세요', '세련된 취향을 살린 활동이 도움됩니다'],
        '壬': ['다양한 정보와 인맥을 활용하세요', '유연하게 상황에 대처하는 지혜가 필요합니다', '수면과 휴식의 질을 높이세요'],
        '癸': ['직감을 믿되 데이터로 검증하세요', '깊이 있는 학습과 연구에 좋은 해입니다', '내면의 목소리에 귀 기울이는 시간을 가지세요']
    }
    
    result_json['luck_boost_2026'] = {
        "title": ilgan_boost_title.get(ilgan, '2026년 맞춤 개운법'),
        "description": f"2026년 병오(丙午)년의 火 에너지와 {ilgan} 일간의 조화를 분석한 맞춤 개운법입니다. 용신 {yongsin} 기운을 보충하며 아래 실천 사항을 참고하세요.",
        "actions": ilgan_boost_actions.get(ilgan, ['월별 운세를 참고하세요', '용신 기운을 보충하세요', '건강 관리에 신경 쓰세요'])
    }
    
    print(f"✅ [Premium] 생성완료 - 용신:{yongsin}, 부적색상:{yongsin_color}")
    
    return result_json


# --------------------------------------------------------------------------
# 5. SajuEngine 클래스 - saju_engine_final.py에서 import (중복 제거)
# --------------------------------------------------------------------------
# 🔧 SajuEngine은 saju_engine_final.py에 정의되어 있습니다.
# app.py에서 직접 from saju_engine_final import SajuEngine으로 사용합니다.
# 이 파일에서는 SajuEngine을 정의하지 않습니다 (약 200줄 중복 코드 제거)
# --------------------------------------------------------------------------
