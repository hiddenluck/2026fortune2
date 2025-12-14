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
        TEN_GAN_PERSONA
    )
    # 🔧 saju_data_updated.py에서 점수 계산 함수 임포트
    from saju_data_updated import (
        calculate_total_luck_score,
        JOHU_SCORES_LOOKUP,
        JIJI_SCORES_LOOKUP,
        SINJEONG_JOHU_SCORES_LOOKUP
    )
except ImportError as e:
    print(f"🚨 오류: saju_data.py 또는 saju_data_updated.py 파일이 없거나 상수가 누락되었습니다: {e}")
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
# 3. 십성 계산 관련 상수 및 함수 추가 (app.py의 calculate_sewoon_sipsin 호환)
# --------------------------------------------------------------------------

# 천간 십성 인덱스 (일간 기준)
# 🚨 십성 관계는 saju_data.py에 없으므로 여기에 임시로 정의합니다.
TEN_GODS_MAP_STEM = {
    # (일간_인덱스, 타천간_인덱스): 십성
    (0, 0): '일원', (0, 1): '겁재', (0, 2): '식신', (0, 3): '상관', (0, 4): '편재', (0, 5): '정재', (0, 6): '편관', (0, 7): '정관', (0, 8): '편인', (0, 9): '정인', 
    (1, 0): '겁재', (1, 1): '일원', (1, 2): '상관', (1, 3): '식신', (1, 4): '정재', (1, 5): '편재', (1, 6): '정관', (1, 7): '편관', (1, 8): '정인', (1, 9): '편인', 
    (2, 0): '편인', (2, 1): '정인', (2, 2): '비견', (2, 3): '겁재', (2, 4): '식신', (2, 5): '상관', (2, 6): '편재', (2, 7): '정재', (2, 8): '편관', (2, 9): '정관', 
    (3, 0): '정인', (3, 1): '편인', (3, 2): '겁재', (3, 3): '일원', (3, 4): '상관', (3, 5): '식신', (3, 6): '정재', (3, 7): '편재', (3, 8): '정관', (3, 9): '편관', 
    (4, 0): '편관', (4, 1): '정관', (4, 2): '편인', (4, 3): '정인', (4, 4): '일원', (4, 5): '겁재', (4, 6): '식신', (4, 7): '상관', (4, 8): '편재', (4, 9): '정재', 
    (5, 0): '정관', (5, 1): '편관', (5, 2): '정인', (5, 3): '편인', (5, 4): '겁재', (5, 5): '일원', (5, 6): '상관', (5, 7): '식신', (5, 8): '정재', (5, 9): '편재', 
    (6, 0): '편재', (6, 1): '정재', (6, 2): '편관', (6, 3): '정관', (6, 4): '편인', (6, 5): '정인', (6, 6): '일원', (6, 7): '겁재', (6, 8): '식신', (6, 9): '상관', 
    (7, 0): '정재', (7, 1): '편재', (7, 2): '정관', (7, 3): '편관', (7, 4): '정인', (7, 5): '편인', (7, 6): '겁재', (7, 7): '일원', (7, 8): '상관', (7, 9): '식신', 
    (8, 0): '식신', (8, 1): '상관', (8, 2): '편재', (8, 3): '정재', (8, 4): '편관', (8, 5): '정관', (8, 6): '편인', (8, 7): '정인', (8, 8): '일원', (8, 9): '겁재', 
    (9, 0): '상관', (9, 1): '식신', (9, 2): '정재', (9, 3): '편재', (9, 4): '정관', (9, 5): '편관', (9, 6): '정인', (9, 7): '편인', (9, 8): '겁재', (9, 9): '일원', 
}

# 지지 십성 인덱스 (지장간을 고려하지 않은, 지지의 대표 오행 기준)
JIJI_TO_STEM_INDEX = {
    '子': 9, '丑': 5, '寅': 0, '卯': 1, '辰': 4, '巳': 2, '午': 3, '未': 5, '申': 6, '酉': 7, '戌': 4, '亥': 8
}
# 🚨 壬(8), 癸(9)의 일원 인덱스가 0~9 기준으로 '비견'이 아닌 '일원'으로 처리되도록 TEN_GODS_MAP_STEM도 수정되었습니다.

def calculate_pillar_sipsin(day_master: str, ganji: str) -> Dict:
    """
    일간을 기준으로 특정 간지(柱)의 천간(Stem)과 지지(Branch)의 십성(Ten Gods)을 계산합니다.
    """
    if len(ganji) != 2 or day_master not in CHEONGAN:
        return {'stem_ten_god': 'N/A', 'branch_ten_god': 'N/A'}

    day_idx = CHEONGAN.index(day_master)
    stem = ganji[0]
    branch = ganji[1]

    # 1. 천간 십성 계산
    stem_idx = CHEONGAN.index(stem)
    stem_sipsin = TEN_GODS_MAP_STEM.get((day_idx, stem_idx), 'N/A')
    
    # 2. 지지 십성 계산 (대표 오행의 십성)
    # 지지에 해당하는 천간 인덱스를 가져와서 일간과 비교
    branch_stem_idx = JIJI_TO_STEM_INDEX.get(branch)
    if branch_stem_idx is not None:
        branch_sipsin = TEN_GODS_MAP_STEM.get((day_idx, branch_stem_idx), 'N/A')
    else:
        branch_sipsin = 'N/A'

    return {'stem_ten_god': stem_sipsin, 'branch_ten_god': branch_sipsin}

# app.py에서 calculate_sewoon_sipsin 이름으로 호환되도록 래핑
calculate_sewoon_sipsin = calculate_pillar_sipsin


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
    "key_actions": ["30일 이내 실전 행동 1", "30일 이내 실전 행동 2", "30일 이내 실전 행동 3"],
    
    // === 프리미엄 분석 섹션 (신규 추가) ===
    
    "wealth_timing": {
        "risk_months": [3, 6, 9],
        "opportunity_months": [5, 10, 11],
        "strategy": "상반기는 지출 통제에 집중하고, 하반기 금 기운이 강해지는 시점에 공격적 투자를 권장합니다. 월별 재물 흐름에 맞춰 현금 비중을 30-50% 유지하세요."
    },
    "weakness_missions": {
        "missing_element": "비겁",
        "monthly_missions": {
            "1": "주 1회 소규모 네트워크 모임에 참석하여 비견(동료) 에너지를 보충하세요.",
            "2": "혼자 결정하지 말고 신뢰할 수 있는 1인에게 의견을 구하는 습관을 만드세요.",
            "3": "팀 프로젝트나 협업 기회를 적극 수용하세요.",
            "4": "운동 파트너를 만들어 함께하는 활동을 시작하세요.",
            "5": "멘토링 관계를 형성하거나 스터디 그룹에 참여하세요.",
            "6": "가족이나 친구와 정기적인 모임 일정을 잡으세요.",
            "7": "공동 창작이나 협업 프로젝트를 기획해보세요.",
            "8": "커뮤니티 활동이나 동호회 가입을 고려하세요.",
            "9": "파트너십 기반의 사업 모델을 검토해보세요.",
            "10": "신뢰할 수 있는 조언자 그룹을 구축하세요.",
            "11": "함께 성장할 수 있는 동반자 관계를 강화하세요.",
            "12": "올해의 협업 경험을 정리하고 내년 네트워크 전략을 수립하세요."
        }
    },
    "psychological_relief": {
        "guilt_pattern": "완벽주의로 인한 자기 비판과 성과 압박",
        "reframing": "현재의 정체는 '실패'가 아니라 '뿌리를 내리는 시간'입니다. 운의 흐름상 지금은 '수확'보다 '파종'의 시기이니, 결과보다 과정에 집중하는 80% 전략을 권장합니다.",
        "affirmation": "나는 지금 이 순간에도 충분히 성장하고 있다. 멈춤은 깊어짐이다."
    },
    "relationship_strategy": {
        "pattern_name": "보호형 (Protector Type)",
        "boundary_guide": "1단계: 상대의 요청을 즉시 수락하지 말고 '생각해볼게'라고 말하는 습관 형성. 2단계: 나의 에너지 상태를 먼저 점검한 후 도움 여부 결정. 3단계: 거절해도 관계가 무너지지 않는다는 믿음 갖기.",
        "family_energy": "배우자의 일간이 금(金) 또는 수(水) 계열이면 상생 관계로 서로의 부족함을 채워주는 조합입니다. 자녀와는 목(木) 기운을 공유하면 소통이 원활해집니다."
    },
    "rest_calendar": {
        "burnout_months": [3, 6, 11],
        "rest_activities": "금(金) 일간에게는 수(水) 기운의 휴식이 필요합니다. 수영, 온천, 명상, 독서 등 '흐르는 물'과 '고요함'을 테마로 한 활동을 권장합니다. 특히 번아웃 위험 월에는 주말 중 하루를 완전한 디지털 디톡스 데이로 지정하세요."
    },
    "digital_amulet": {
        "yongsin_element": "수",
        "quote": "물은 장애물을 만나면 돌아 흐릅니다. 막히면 고이고, 고이면 깊어지고, 깊어지면 다시 흐릅니다.",
        "image_color": "#A2C2E0"
    }
}

[응답 지침]:
1. 모든 응답 텍스트는 **따뜻하고 감성적인** 문체(고객용)와 **전문적인 용어**(전문가용)를 구분하여 작성하십시오.
2. detailed_analysis의 내용은 **전문 용어를 상세히 풀어서** 설명해야 합니다. (운영자/전문가 참고용)
3. customer_analysis의 내용은 **쉬운 말**로 감성적이고 공감할 수 있도록 작성하십시오. 명리학 전문 용어(십성, 편관, 정재 등)를 사용하지 마십시오.
4. 텍스트 내에서 줄 바꿈이 필요한 경우 반드시 '\\n' 문자열을 사용하십시오.
5. '일원'을 제외하고 십성 용어 앞에 이중 별표를 붙이지 마십시오. (사용자 요구사항 반영)
6. 고객의 질문(q1, q2)에 대해 명리학적 근거를 바탕으로 구체적인 행동 지침을 제시하되, **qa_section의 답변(a1, a2)은 쉬운 일상 언어로 작성**하십시오. 전문 용어를 피하고 누구나 이해할 수 있게 설명하십시오.
7. customer_analysis의 health_advice는 반드시 포함해야 하며, 전문 용어 없이 일상적인 건강 조언으로 작성하십시오.
8. **프리미엄 섹션(wealth_timing, weakness_missions, psychological_relief, relationship_strategy, rest_calendar, digital_amulet)**: 시스템이 사주 데이터 기반으로 자동 생성합니다. AI는 보조적인 내용만 제공하며, 핵심 로직은 테이블 기반으로 처리됩니다.
9. monthly_guide는 반드시 1월부터 12월까지 모든 월의 데이터를 포함해야 합니다.
10. **monthly_flow 점수**: 시스템이 테이블 기반으로 자동 계산합니다. AI가 생성한 점수는 무시되고 테이블 점수로 대체됩니다.
11. **customer_analysis 작성 시 결론 명확화**:
    - 각 운세 분석의 마지막에 반드시 "그래서 ~하세요", "따라서 ~가 좋겠습니다" 등 구체적 행동 지침을 제시
    - 두리뭉실한 표현 금지 (예: "좋은 시기입니다" → "이 시기에 새로운 거래처를 적극 개척하세요")
12. **psychological_relief 섹션 쉬운 언어 규칙**:
    - guilt_pattern, reframing에 명리학 용어(丁火, 비겁, 관살, 십성 등) 사용 금지
    - 일상적인 심리 패턴과 해결책으로 표현 (예: "완벽해야 한다는 압박", "성과에 대한 불안")
13. **프리미엄 섹션 동적 생성 규칙** (시스템 참조용):
    - 개운법(weakness_missions): 원국 오행 분포 분석 → 부족/과다 오행 판단 → 해당 오행 보완 활동 추천
    - 마인드셋업(psychological_relief): 십성 분포 분석 → 성격 패턴(자립형/표현형/현실형/책임형/사색형) → 심리적 취약점 대응 문구
    - 관계가이드(relationship_strategy): 십성 패턴 기반 관계 스타일 분석 → 경계 설정 가이드
    - 에너지달력(rest_calendar): 월별 점수 기반 취약월 식별 → 용신 맞춤 휴식 활동 추천
    - 디지털부적(digital_amulet): 월지 기반 용신 산출 (토월지=목, 여름월지=수, 겨울월지=화 등)

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
    
    # 4. AI API 호출 및 응답 처리
    try:
        genai.configure(api_key=api_key)
        
        response = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=get_system_instruction()
        ).generate_content(
            contents=[prompt],
            # 수정 완료: 'config'를 'generation_config'로 변경
            generation_config={
                "temperature": 0.5,
                "response_mime_type": "application/json",
            }
        )
        
        response_text = response.text.strip()
        
        # JSON 파싱 시 오류 방지
        clean_json_str = re.sub(r'```json|```', '', response_text, flags=re.IGNORECASE).strip()
        
        try:
            result_json = json.loads(clean_json_str)
            
            # 🔧 월별 점수를 테이블 기반으로 덮어쓰기 (AI 생성 점수 대체)
            # 이로써 동일한 사주에 대해 항상 동일한 월별 점수가 반환됨
            monthly_scores = calculate_monthly_flow_scores(manse_info)
            result_json['monthly_flow'] = monthly_scores
            
            # 🔧 프리미엄 섹션 동적 생성 (사주 기반 맞춤 컨텐츠)
            result_json = ensure_premium_sections(result_json, ilgan, manse_info, monthly_scores)
            
        except json.JSONDecodeError as e:
             return {
                 "summary_card": {"keyword": f"❌ AI 응답 파싱 실패 (JSON 오류)", "best_month": "N/A", "risk": "N/A", "action_item": "N/A"},
                 "raw_response": clean_json_str
             }
        
        return result_json

    except Exception as e:
        return {
            "summary_card": {"keyword": f"❌ API 호출 실패 - {type(e).__name__}", "best_month": "N/A", "risk": "N/A", "action_item": "N/A"},
            "raw_response": f"API 호출 또는 응답 생성 중 예상치 못한 오류 발생: {str(e)}"
        }


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
    사주 원국 기반 용신(用神)을 산출합니다.
    
    핵심 규칙:
    1. 토(土) 월지(辰戌丑未): 목(木) 선 용신 - 땅을 뚫고 나오는 힘
    2. 여름 월지(巳午未): 수(水) 우선 - 더위를 식히는 조후
    3. 겨울 월지(亥子丑): 화(火) 우선 - 추위를 녹이는 조후
    4. 봄/가을: 일간 생(生)해주는 오행
    
    Returns:
        str: '목', '화', '토', '금', '수' 중 하나
    """
    wolji = manse_info.get('월주', '')[1] if len(manse_info.get('월주', '')) > 1 else ''
    ilgan = manse_info.get('일주', '')[0] if len(manse_info.get('일주', '')) > 0 else ''
    
    # 토 월지 (辰戌丑未) → 목(木) 선 용신
    if wolji in ['辰', '戌', '丑', '未']:
        return '목'
    
    # 여름 월지 (巳午未) → 수(水) 선 용신 (조후)
    if wolji in ['巳', '午']:
        return '수'
    
    # 겨울 월지 (亥子丑) → 화(火) 선 용신 (조후)
    if wolji in ['亥', '子']:
        return '화'
    
    # 봄/가을 및 기타: 일간 기준 생해주는 오행
    ilgan_yongsin_default = {
        '甲': '수', '乙': '수',  # 목을 생하는 수
        '丙': '목', '丁': '목',  # 화를 생하는 목
        '戊': '화', '己': '화',  # 토를 생하는 화
        '庚': '토', '辛': '토',  # 금을 생하는 토
        '壬': '금', '癸': '금',  # 수를 생하는 금
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
    🔧 프리미엄 섹션을 사주 데이터 기반으로 동적 생성합니다.
    
    [개선된 로직]:
    1. 개운법(weakness_missions): 원국 오행 분포 분석 → 부족/과다 오행 판단 → 보완 미션 생성
    2. 마인드셋업(psychological_relief): 십성 분포 → 성격 패턴 → 심리적 취약점 대응 문구
    3. 관계가이드(relationship_strategy): 십성 패턴 → 관계 스타일 가이드
    4. 에너지달력(rest_calendar): 월별 점수 → 취약월 식별 → 맞춤 휴식 활동
    5. 디지털부적(digital_amulet): 월지 기반 용신 산출 → 맞춤 메시지/색상
    """
    
    # === 1. 기본 분석 데이터 준비 ===
    oheng_analysis = _analyze_oheng_distribution(manse_info)
    yongsin = _calculate_yongsin(manse_info)
    sipsin_pattern = _get_sipsin_pattern(manse_info)
    
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
    else:
        risk_months = [3, 6, 9]
        opportunity_months = [5, 10, 11]
        burnout_months = [3, 6, 11]
    
    # === 2. wealth_timing (재물 타이밍 관리) ===
    if 'wealth_timing' not in result_json or not result_json['wealth_timing']:
        # 일간별 재물운 키워드
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
            "risk_months": risk_months[:3] if len(risk_months) >= 3 else risk_months + [12],
            "opportunity_months": opportunity_months[:3] if len(opportunity_months) >= 3 else opportunity_months + [1],
            "strategy": ilgan_wealth_style.get(ilgan, "상반기 지출 관리에 집중하고, 하반기 수익화 기회를 노리세요.")
        }
    
    # === 3. weakness_missions (개운법 - 부족 오행 보완) ===
    if 'weakness_missions' not in result_json or not result_json['weakness_missions']:
        missing = oheng_analysis['missing']
        weak = oheng_analysis['weak']
        
        # 부족한 오행 결정 (없는 오행 > 1개만 있는 오행 > 용신)
        if missing:
            target_element = missing[0]
            element_kr_name = {'목': '시작의 힘', '화': '열정의 힘', '토': '안정의 힘', '금': '결단의 힘', '수': '지혜의 힘'}
            weakness_desc = f"사주에 {target_element}({element_kr_name.get(target_element, '')})이 부족하여 보완이 필요합니다."
        elif weak:
            target_element = weak[0]
            element_kr_name = {'목': '시작의 힘', '화': '열정의 힘', '토': '안정의 힘', '금': '결단의 힘', '수': '지혜의 힘'}
            weakness_desc = f"사주에 {target_element}({element_kr_name.get(target_element, '')})이 약하여 보완이 필요합니다."
        else:
            target_element = yongsin
            weakness_desc = f"용신인 {target_element} 기운을 강화하면 전체 운기가 상승합니다."
        
        missions = _generate_weakness_missions(target_element if missing else '', weak)
        
        result_json['weakness_missions'] = {
            "missing_element": weakness_desc,
            "monthly_missions": missions
        }
    
    # === 4. psychological_relief (마인드셋업 - 심리 취약점 대응) ===
    if 'psychological_relief' not in result_json or not result_json['psychological_relief']:
        pattern = sipsin_pattern
        
        # 십성 기반 심리 패턴
        affirmations = {
            '비겁': "나는 도움을 받아도 괜찮은 사람이다. 함께하면 더 멀리 갈 수 있다.",
            '식상': "나의 표현은 충분히 가치있다. 모든 사람의 인정이 필요하지 않다.",
            '재성': "나는 물질 이상의 가치를 가진 사람이다. 풍요는 마음에서 시작된다.",
            '관성': "완벽하지 않아도 나는 충분하다. 나 자신을 돌보는 것도 책임이다.",
            '인성': "생각을 멈추고 행동해도 괜찮다. 실수해도 배울 수 있다."
        }
        
        result_json['psychological_relief'] = {
            "guilt_pattern": pattern['psychological_weakness'],
            "reframing": f"{pattern['pattern_name']} 성향의 당신에게 현재의 멈춤이나 지연은 '실패'가 아닙니다. 운의 흐름상 지금은 내면을 다지는 시간입니다. 결과보다 과정을 믿고, 80% 완성도로 먼저 시작하는 전략을 권합니다.",
            "affirmation": affirmations.get(pattern['dominant'], "나는 지금 이 순간에도 성장하고 있다.")
        }
    
    # === 5. relationship_strategy (관계 가이드) ===
    if 'relationship_strategy' not in result_json or not result_json['relationship_strategy']:
        pattern = sipsin_pattern
        
        family_guides = {
            '비겁': "가족에게도 도움을 요청하세요. 혼자 해결하려는 모습이 오히려 거리감을 만들 수 있습니다.",
            '식상': "가족의 반응에 너무 민감하지 마세요. 표현은 하되, 반응은 상대의 몫입니다.",
            '재성': "가족 관계에서 금전적 계산을 줄이세요. 정서적 교류가 더 중요합니다.",
            '관성': "가족에게 완벽한 모습만 보이려 하지 마세요. 약한 모습도 괜찮습니다.",
            '인성': "가족과의 대화에서 조언보다 경청을 먼저 하세요. 들어주는 것이 최고의 지지입니다."
        }
        
        result_json['relationship_strategy'] = {
            "pattern_name": f"{pattern['relationship_style']} ({pattern['pattern_name']})",
            "boundary_guide": pattern['boundary_guide'],
            "family_energy": family_guides.get(pattern['dominant'], "가족과 서로의 리듬을 존중하고, 강요보다는 제안의 형태로 소통하세요.")
        }
    
    # === 6. rest_calendar (에너지 달력) ===
    if 'rest_calendar' not in result_json or not result_json['rest_calendar']:
        rest_activities = _get_rest_activities_by_yongsin(yongsin)
        
        result_json['rest_calendar'] = {
            "burnout_months": burnout_months[:3] if len(burnout_months) >= 3 else burnout_months + [6],
            "rest_activities": rest_activities
        }
    
    # === 7. digital_amulet (디지털 부적) ===
    if 'digital_amulet' not in result_json or not result_json['digital_amulet']:
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
    
    return result_json


# --------------------------------------------------------------------------
# 5. 핵심 엔진 클래스 (SajuEngine) - 원국, 대운, 세운 계산 통합
# --------------------------------------------------------------------------

# astropy, numpy 등 필요한 라이브러리 임포트는 이 파일 상단에 이미 있습니다.
try:
    from astropy.time import Time
    from astropy.coordinates import solar_system_ephemeris, EarthLocation, get_sun, SkyCoord
    import astropy.units as u
    solar_system_ephemeris.set('de432s') 
except ImportError:
    # 이 환경에서 astropy가 불가능할 경우, SajuEngine은 작동하지 않습니다.
    pass


class SajuEngine:
    
    JEOLGI_DEGREES = {
        0: '立春', 30: '驚蟄', 60: '淸明', 90: '立夏',
        120: '芒種', 150: '小暑', 180: '立秋', 210: '白露',
        240: '寒露', 270: '立冬', 300: '大雪', 330: '小寒'
    }

    def __init__(self):
        self.ganji_60 = GANJI_60
        self.cheongan = CHEONGAN
        self.jiji = JIJI

    def _find_jeolgi_time(self, target_degree: int, target_year: int) -> datetime.datetime:
        """astropy를 사용하여 특정 황경 도달 시각 (KST)을 계산합니다. (기존 로직 유지)"""
        # ... (로직 생략)
        time_start = Time(f'{target_year}-01-01 00:00:00', format='iso', scale='utc')
        time_end = Time(f'{target_year+1}-03-01 00:00:00', format='iso', scale='utc')
        times = time_start + np.linspace(0, (time_end - time_start).to_value(u.day), 5000) * u.day
        sun_pos = get_sun(times)
        sun_ecliptic_lon = sun_pos.barycentrictrueecliptic.lon.to(u.deg).value
        target_lon = target_degree
        
        lon_diff = sun_ecliptic_lon - target_lon
        lon_diff[lon_diff > 180] -= 360
        lon_diff[lon_diff < -180] += 360
        
        crossing_index = np.where(np.diff(np.sign(lon_diff)))[0]
        
        if len(crossing_index) == 0:
             return self._find_jeolgi_time(target_degree, target_year + 1)

        idx = crossing_index[0]
        t1, t2 = times[idx], times[idx+1]
        l1, l2 = sun_ecliptic_lon[idx], sun_ecliptic_lon[idx+1]
        
        time_frac = (target_lon - l1) / (l2 - l1)
        time_jeolgi_utc = t1 + (t2 - t1) * time_frac
        
        return time_jeolgi_utc.to_datetime(timezone=TIME_ZONE)

    def _get_all_jeolgi_for_year(self, target_year: int) -> List[Dict]:
        """주어진 연도에 필요한 모든 '절(節)' 시각을 계산합니다. (기존 로직 유지)"""
        calculated_jeolgi = []
        for degree, name in self.JEOLGI_DEGREES.items():
            time_kst = self._find_jeolgi_time(degree, target_year)
            if time_kst and time_kst.year in [target_year, target_year + 1, target_year - 1]:
                 calculated_jeolgi.append({'datetime': time_kst, 'name': name, 'degree': degree})
        
        calculated_jeolgi.sort(key=lambda x: x['datetime'])
        return calculated_jeolgi

    def _get_day_ganji(self, dt: datetime.datetime) -> str:
        """일주 (日柱) 계산 함수 (기준일 甲戌日로 최종 변경, 기존 로직 유지)"""
        REF_DATE = datetime.date(1900, 1, 1) 
        REF_DAY_GANJI_INDEX = 10 
        date_obj = dt.date()
        days_passed = (date_obj - REF_DATE).days
        day_ganji_index = (REF_DAY_GANJI_INDEX + days_passed) % 60
        return self.ganji_60[day_ganji_index]

    def _get_shi_ganji(self, day_gan: str, birth_hour: int) -> str:
        """시주 (時柱) 계산 함수 (시두법 기반, 기존 로직 유지)"""
        hour_index = (birth_hour + 1) % 24 // 2
        shi_zhi = self.jiji[hour_index % 12] 
        start_stem_index = DAY_STEM_TO_TIME_STEM_START_INDEX[day_gan]
        shi_gan_index = (start_stem_index + hour_index) % 10
        shi_gan = self.cheongan[shi_gan_index]
        return shi_gan + shi_zhi
        
    def generate_saju_palja(self, birth_dt: datetime.datetime, gender: str) -> Dict:
        """
        최종 사주팔자 8글자 및 대운 계산에 필요한 정보 반환
        🚨 십성 결과를 포함하도록 최종 반환 구조를 수정했습니다.
        """
        
        if birth_dt.tzinfo is None:
             birth_dt = birth_dt.replace(tzinfo=TIME_ZONE)
             
        day_ganji = self._get_day_ganji(birth_dt)
        day_gan = day_ganji[0]
        shi_ganji = self._get_shi_ganji(day_gan, birth_dt.hour)

        try:
            jeolgi_db_current = self._get_all_jeolgi_for_year(birth_dt.year)
            jeolgi_db_prev = self._get_all_jeolgi_for_year(birth_dt.year - 1)
            jeolgi_db_full = sorted(jeolgi_db_current + jeolgi_db_prev, key=lambda x: x['datetime'])
        except Exception as e:
            raise ValueError(f"절기 계산 중 오류 발생: {e}")

        past_jeolgi = None
        future_jeolgi = None
        
        for dt_info in jeolgi_db_full:
            dt = dt_info['datetime']
            if dt <= birth_dt:
                past_jeolgi = dt_info
            elif dt > birth_dt:
                future_jeolgi = dt_info
                break

        if past_jeolgi is None:
             raise ValueError("절기 DB에 출생 시점보다 이전 데이터가 없습니다.")

        # 년주 확정 (立春 기준)
        lipchun_dt = next((j['datetime'] for j in jeolgi_db_full if j['name'] == '立春' and j['datetime'].year == birth_dt.year), None)
        year_index_naive = (birth_dt.year - 1900 + 33) % 60
        
        if lipchun_dt and birth_dt < lipchun_dt:
            year_ganji_final = GANJI_60[(year_index_naive - 1 + 60) % 60]
        else:
            year_ganji_final = GANJI_60[year_index_naive]

        # 월주 확정 (월건법, 년간 기준)
        month_zhi_index = (past_jeolgi['degree'] // 30) % 12
        month_zhi = JIJI[(month_zhi_index + 2) % 12]
        year_gan = year_ganji_final[0]
        month_stem_start_idx = YEAR_STEM_TO_MONTH_STEM_INDEX[year_gan]
        month_stem_idx = (month_stem_start_idx + month_zhi_index) % 10 
        month_gan = CHEONGAN[month_stem_idx]
        month_ganji = month_gan + month_zhi

        # 대운 정보 계산
        daewoon_info = self._calculate_full_daewoon(year_ganji_final, month_ganji, birth_dt, gender, past_jeolgi['datetime'], future_jeolgi['datetime'])
        
        # 십성 계산 (추가된 부분)
        pillars_ganji = [year_ganji_final, month_ganji, day_ganji, shi_ganji]
        ten_gods_array = [calculate_pillar_sipsin(day_gan, g) for g in pillars_ganji]

        return {
            "년주": year_ganji_final, "월주": month_ganji, "일주": day_ganji, "시주": shi_ganji,
            "대운_정보": daewoon_info,
            "출생일": birth_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "일간": day_gan,
            "십성_결과_배열": ten_gods_array
        }

    def _calculate_full_daewoon(self, year_ganji: str, month_ganji: str, birth_dt: datetime.datetime, gender: str, past_jeolgi: datetime.datetime, future_jeolgi: datetime.datetime) -> Dict:
        """대운수, 순/역행, 대운 간지 배열을 계산"""
        year_gan = year_ganji[0]
        # 년간의 음양 판단: 甲丙戊庚壬(양), 乙丁己辛癸(음)
        is_yang = year_gan in ['甲', '丙', '戊', '庚', '壬']
        
        # 순행/역행 결정: 양년생 남/음년생 여 = 순행, 양년생 여/음년생 남 = 역행
        is_forward = (is_yang and gender == 'M') or (not is_yang and gender == 'F')
        기준_절기 = future_jeolgi if is_forward else past_jeolgi
        
        if 기준_절기 is None: return {"error": "기준 절기 데이터 부족"}
        
        time_diff = abs(기준_절기 - birth_dt)
        days_diff = time_diff.total_seconds() / (24 * 3600)
        
        # 🚨 [수정 1] 대운수 계산 오버플로우 방지 및 올림 처리
        days_per_age = days_diff / 3.0
        
        # math.ceil 함수를 사용하여 무조건 올림 (대운수 계산 표준)
        # days_diff가 0보다 클 경우에만 ceil 적용, days_diff=0일 경우 1로 처리
        if days_diff > 0:
            daewoon_su = int(ceil(days_per_age))
        else:
            daewoon_su = 1

        # 최소 1, 최대 10세 범위로 강제 (100세 이상 오버플로우 방지)
        daewoon_su = max(1, min(10, daewoon_su)) 
            
        m_s_idx, m_b_idx = self.cheongan.index(month_ganji[0]), self.jiji.index(month_ganji[1])
        daewoon_list = []
        for i in range(1, 9): 
            # 🚨 [수정 2] 대운 시작 나이 계산 시 오버플로우 방지
            age_start = daewoon_su + (i - 1) * 10
            
            if is_forward:
                # 순행 (인덱스 증가)
                s_idx = (m_s_idx + i) % 10
                b_idx = (m_b_idx + i) % 12
            else:
                # 역행 (인덱스 감소)
                # 丙戌(2, 10)에서 역행하면 i=1일 때 乙酉(1, 9)가 됩니다.
                s_idx = (m_s_idx - i + 10) % 10
                b_idx = (m_b_idx - i + 12) % 12

            daewoon_list.append({"age": age_start, "ganji": self.cheongan[s_idx] + self.jiji[b_idx]})
        
        return {
            "대운수": daewoon_su,
            "순행_역행": "순행" if is_forward else "역행",
            "대운_간지_배열": daewoon_list
        }
        
    def get_sewoon(self, current_year: int, count: int = 10) -> List[Dict]:
        """세운 (歲運) 계산 함수 (기존 로직 유지)"""
        sewoon_list = []
        start_index = (33 + (current_year - 1900)) % 60
        
        for i in range(count):
            year = current_year + i
            index = (start_index + i) % 60
            ganji = self.ganji_60[index]
            sewoon_list.append({"year": year, "ganji": ganji})
            
        return sewoon_list

# --------------------------------------------------------------------------
# 이 아래에 get_final_ai_prompt, analyze_ai_report 함수 정의가 이어집니다.
# (위쪽 4. AI 프롬프트 및 분석 함수 추가 섹션에 이미 정의되어 있습니다.)
# --------------------------------------------------------------------------
