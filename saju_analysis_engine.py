"""
=============================================================================
금쪽이 사주 분석 엔진 (Gumjjok Saju Analysis Engine)
=============================================================================

목적: 9단계 알고리즘으로 정확한 사주 분석 수행
- 1단계: 데이터 확정 및 오행 분포 분석
- 2단계: 일주(日柱) 기준점 분석
- 3단계: 격국/조후 판단 (AI 보조)
- 4단계: 신강/신약 + 용신 판단 (AI 보조)
- 5단계: 통근 및 지장간 스캔
- 6단계: 십신/궁위 상호작용
- 7단계: 특수 변수 적용 (신살/공망/합충형)
- 8단계: 대운/세운 타임라인 매칭
- 9단계: 종합 해석 (AI)

설계 원칙:
1. 경량화: 필요한 데이터만 import
2. 구조 단순화: 명확한 함수 책임 분리
3. 효율화: 중복 계산 방지, 캐싱 활용
4. AI 보조: 복잡한 판단은 AI에게 위임

참조 파일:
- saju_data.py: 기본 상수, 점수 테이블
- saju_engine_final.py: SajuEngine 클래스, 십성 계산
=============================================================================
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json

# =============================================================================
# 1. 상수 정의 (saju_data.py에서 중앙화된 데이터 import)
# 🔧 리팩토링: Fallback 제거 - saju_data.py는 핵심 모듈이므로 반드시 존재해야 함
# =============================================================================

from saju_data import (
    CHEONGAN, JIJI, GANJI_60, O_HAENG_MAP,
    TEN_GAN_PERSONA, TWELVE_STAR,
    calculate_total_luck_score, generate_interpretation_flags
)


# =============================================================================
# 2. 지장간 (藏干) 데이터 - 정확한 명리학 정의
# =============================================================================

# 지장간: 각 지지에 숨어있는 천간들 (본기, 중기, 여기 순)
JIJANGGAN = {
    '子': ['癸'],                    # 자: 계수 (본기만)
    '丑': ['己', '癸', '辛'],        # 축: 기토(본), 계수(중), 신금(여)
    '寅': ['甲', '丙', '戊'],        # 인: 갑목(본), 병화(중), 무토(여)
    '卯': ['乙'],                    # 묘: 을목 (본기만)
    '辰': ['戊', '乙', '癸'],        # 진: 무토(본), 을목(중), 계수(여)
    '巳': ['丙', '戊', '庚'],        # 사: 병화(본), 무토(중), 경금(여)
    '午': ['丁', '己'],              # 오: 정화(본), 기토(중)
    '未': ['己', '丁', '乙'],        # 미: 기토(본), 정화(중), 을목(여)
    '申': ['庚', '壬', '戊'],        # 신: 경금(본), 임수(중), 무토(여)
    '酉': ['辛'],                    # 유: 신금 (본기만)
    '戌': ['戊', '辛', '丁'],        # 술: 무토(본), 신금(중), 정화(여)
    '亥': ['壬', '甲']               # 해: 임수(본), 갑목(중)
}

# 지장간 본기만 (간단 계산용)
JIJANGGAN_BONGI = {
    '子': '癸', '丑': '己', '寅': '甲', '卯': '乙', '辰': '戊', '巳': '丙',
    '午': '丁', '未': '己', '申': '庚', '酉': '辛', '戌': '戊', '亥': '壬'
}

# 지지별 계절
JIJI_SEASON = {
    '寅': '초봄', '卯': '봄', '辰': '늦봄',
    '巳': '초여름', '午': '한여름', '未': '늦여름',
    '申': '초가을', '酉': '가을', '戌': '늦가을',
    '亥': '초겨울', '子': '한겨울', '丑': '늦겨울'
}

# 계절별 오행 강약 (월지 기준)
SEASON_OHENG_STRENGTH = {
    # 봄(寅卯辰): 목왕, 화상, 토휴, 금수, 수사
    '寅': {'木': 100, '火': 80, '土': 40, '金': 20, '水': 60},
    '卯': {'木': 100, '火': 80, '土': 40, '金': 20, '水': 60},
    '辰': {'木': 80, '火': 60, '土': 60, '金': 40, '水': 40},
    # 여름(巳午未): 화왕, 토상, 금휴, 수수, 목사
    '巳': {'火': 100, '土': 80, '金': 40, '水': 20, '木': 60},
    '午': {'火': 100, '土': 80, '金': 40, '水': 20, '木': 60},
    '未': {'土': 100, '火': 80, '金': 60, '水': 40, '木': 40},
    # 가을(申酉戌): 금왕, 수상, 목휴, 화수, 토사
    '申': {'金': 100, '水': 80, '木': 40, '火': 20, '土': 60},
    '酉': {'金': 100, '水': 80, '木': 40, '火': 20, '土': 60},
    '戌': {'土': 100, '金': 80, '水': 60, '木': 40, '火': 40},
    # 겨울(亥子丑): 수왕, 목상, 화휴, 토수, 금사
    '亥': {'水': 100, '木': 80, '火': 40, '土': 20, '金': 60},
    '子': {'水': 100, '木': 80, '火': 40, '土': 20, '金': 60},
    '丑': {'土': 100, '水': 80, '金': 60, '木': 40, '火': 40},
}


# =============================================================================
# 3. 오행 관계 정의
# =============================================================================

class OhengRelation(Enum):
    """오행 간 관계"""
    SAME = "비화"      # 동일 오행
    GENERATE = "생"    # 생(生)해주는 관계 (인성)
    GENERATED = "설"   # 생(生)받는 관계 (식상)
    CONTROL = "극"     # 극(剋)하는 관계 (재성)
    CONTROLLED = "피극"  # 극(剋)당하는 관계 (관성)


# 오행 생극 관계
OHENG_GENERATE = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}  # 목생화 화생토...
OHENG_CONTROL = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}   # 목극토 화극금...


def get_oheng_relation(oheng1: str, oheng2: str) -> OhengRelation:
    """두 오행 간의 관계를 반환"""
    if oheng1 == oheng2:
        return OhengRelation.SAME
    if OHENG_GENERATE.get(oheng1) == oheng2:
        return OhengRelation.GENERATED  # 내가 생하면 설기
    if OHENG_GENERATE.get(oheng2) == oheng1:
        return OhengRelation.GENERATE   # 나를 생하면 생
    if OHENG_CONTROL.get(oheng1) == oheng2:
        return OhengRelation.CONTROL    # 내가 극하면 극
    if OHENG_CONTROL.get(oheng2) == oheng1:
        return OhengRelation.CONTROLLED # 나를 극하면 피극
    return OhengRelation.SAME  # 기본값


# =============================================================================
# 4. 합/충/형/파/해 데이터
# =============================================================================

# 천간합 (甲己土, 乙庚金, 丙辛水, 丁壬木, 戊癸火)
CHEONGAN_HAP = {
    ('甲', '己'): '土', ('己', '甲'): '土',
    ('乙', '庚'): '金', ('庚', '乙'): '金',
    ('丙', '辛'): '水', ('辛', '丙'): '水',
    ('丁', '壬'): '木', ('壬', '丁'): '木',
    ('戊', '癸'): '火', ('癸', '戊'): '火',
}

# 지지 육합 (子丑土, 寅亥木, 卯戌火, 辰酉金, 巳申水, 午未土/火)
JIJI_YUKHAP = {
    ('子', '丑'): '土', ('丑', '子'): '土',
    ('寅', '亥'): '木', ('亥', '寅'): '木',
    ('卯', '戌'): '火', ('戌', '卯'): '火',
    ('辰', '酉'): '金', ('酉', '辰'): '金',
    ('巳', '申'): '水', ('申', '巳'): '水',
    ('午', '未'): '土', ('未', '午'): '土',
}

# 지지 삼합 (寅午戌-火, 巳酉丑-金, 申子辰-水, 亥卯未-木)
JIJI_SAMHAP = {
    frozenset(['寅', '午', '戌']): '火',
    frozenset(['巳', '酉', '丑']): '金',
    frozenset(['申', '子', '辰']): '水',
    frozenset(['亥', '卯', '未']): '木',
}

# 지지 방합 (寅卯辰-木, 巳午未-火, 申酉戌-金, 亥子丑-水)
JIJI_BANGHAP = {
    frozenset(['寅', '卯', '辰']): '木',
    frozenset(['巳', '午', '未']): '火',
    frozenset(['申', '酉', '戌']): '金',
    frozenset(['亥', '子', '丑']): '水',
}

# 지지충 (子午, 丑未, 寅申, 卯酉, 辰戌, 巳亥)
JIJI_CHUNG = {
    '子': '午', '午': '子', '丑': '未', '未': '丑',
    '寅': '申', '申': '寅', '卯': '酉', '酉': '卯',
    '辰': '戌', '戌': '辰', '巳': '亥', '亥': '巳',
}

# 지지형 (寅巳申-무은지형, 丑戌未-지세지형, 子卯-무례지형, 辰辰/午午/酉酉/亥亥-자형)
JIJI_HYUNG = {
    frozenset(['寅', '巳', '申']): '무은지형',
    frozenset(['丑', '戌', '未']): '지세지형',
    frozenset(['子', '卯']): '무례지형',
    frozenset(['辰', '辰']): '자형', frozenset(['午', '午']): '자형',
    frozenset(['酉', '酉']): '자형', frozenset(['亥', '亥']): '자형',
}

# 공망 (각 일주별 공망 지지)
GONGMANG = {
    '甲子': ['戌', '亥'], '乙丑': ['戌', '亥'], '丙寅': ['戌', '亥'], '丁卯': ['戌', '亥'], '戊辰': ['戌', '亥'],
    '己巳': ['戌', '亥'], '庚午': ['申', '酉'], '辛未': ['申', '酉'], '壬申': ['申', '酉'], '癸酉': ['申', '酉'],
    '甲戌': ['申', '酉'], '乙亥': ['申', '酉'], '丙子': ['午', '未'], '丁丑': ['午', '未'], '戊寅': ['午', '未'],
    '己卯': ['午', '未'], '庚辰': ['午', '未'], '辛巳': ['午', '未'], '壬午': ['辰', '巳'], '癸未': ['辰', '巳'],
    '甲申': ['辰', '巳'], '乙酉': ['辰', '巳'], '丙戌': ['辰', '巳'], '丁亥': ['辰', '巳'], '戊子': ['寅', '卯'],
    '己丑': ['寅', '卯'], '庚寅': ['寅', '卯'], '辛卯': ['寅', '卯'], '壬辰': ['寅', '卯'], '癸巳': ['寅', '卯'],
    '甲午': ['子', '丑'], '乙未': ['子', '丑'], '丙申': ['子', '丑'], '丁酉': ['子', '丑'], '戊戌': ['子', '丑'],
    '己亥': ['子', '丑'], '庚子': ['戌', '亥'], '辛丑': ['戌', '亥'], '壬寅': ['戌', '亥'], '癸卯': ['戌', '亥'],
    '甲辰': ['戌', '亥'], '乙巳': ['戌', '亥'], '丙午': ['申', '酉'], '丁未': ['申', '酉'], '戊申': ['申', '酉'],
    '己酉': ['申', '酉'], '庚戌': ['申', '酉'], '辛亥': ['申', '酉'], '壬子': ['午', '未'], '癸丑': ['午', '未'],
    '甲寅': ['午', '未'], '乙卯': ['午', '未'], '丙辰': ['午', '未'], '丁巳': ['午', '未'], '戊午': ['辰', '巳'],
    '己未': ['辰', '巳'], '庚申': ['辰', '巳'], '辛酉': ['辰', '巳'], '壬戌': ['辰', '巳'], '癸亥': ['辰', '巳'],
}


# =============================================================================
# 5. 신살 데이터
# =============================================================================

# 역마살 (년지/일지 기준)
YEOKMA = {
    '寅': '申', '午': '申', '戌': '申',
    '申': '寅', '子': '寅', '辰': '寅',
    '巳': '亥', '酉': '亥', '丑': '亥',
    '亥': '巳', '卯': '巳', '未': '巳',
}

# 도화살 (년지/일지 기준)
DOHWA = {
    '寅': '卯', '午': '卯', '戌': '卯',
    '申': '酉', '子': '酉', '辰': '酉',
    '巳': '午', '酉': '午', '丑': '午',
    '亥': '子', '卯': '子', '未': '子',
}

# 화개살 (년지/일지 기준)
HWAGAE = {
    '寅': '戌', '午': '戌', '戌': '戌',
    '申': '辰', '子': '辰', '辰': '辰',
    '巳': '丑', '酉': '丑', '丑': '丑',
    '亥': '未', '卯': '未', '未': '未',
}


# =============================================================================
# 6. 분석 결과 데이터 클래스
# =============================================================================

@dataclass
class OhengDistribution:
    """오행 분포 분석 결과"""
    count: Dict[str, int]           # 각 오행별 개수
    strength: Dict[str, float]      # 각 오행별 강도 (계절 고려)
    missing: List[str]              # 없는 오행
    weak: List[str]                 # 약한 오행 (1개 또는 힘 약함)
    excess: List[str]               # 과다 오행 (3개 이상)
    dominant: str                   # 가장 강한 오행


@dataclass
class GangwakAnalysis:
    """신강/신약 분석 결과"""
    is_strong: bool                 # 신강 여부
    strength_score: float           # 신강도 점수 (0~100, 50 기준)
    ilgan_oheng: str               # 일간 오행
    support_count: int              # 일간을 돕는 요소 수 (비겁+인성)
    suppress_count: int             # 일간을 억제하는 요소 수 (관성+재성+식상)
    tonggeun_count: int             # 통근 수
    details: str                    # 상세 설명


@dataclass
class YongsinResult:
    """용신 판단 결과"""
    yongsin: str                    # 용신 오행
    huisin: str                     # 희신 오행 (용신을 생하는 오행)
    gisin: str                      # 기신 오행 (용신을 극하는 오행)
    reason: str                     # 판단 근거
    confidence: float               # 판단 확신도 (0~1)


@dataclass
class GeokgukResult:
    """격국 판단 결과"""
    geokguk_name: str               # 격국 이름
    geokguk_type: str               # 격국 유형 (정격/변격)
    strength: str                   # 격의 강도 (성격/파격)
    description: str                # 격국 설명


# =============================================================================
# 7. 1단계: 데이터 확정 및 오행 분포 분석
# =============================================================================

def analyze_oheng_distribution(manse_info: Dict) -> OhengDistribution:
    """
    [1단계] 사주 원국의 오행 분포를 정확하게 분석합니다.
    
    분석 요소:
    1. 8글자(4천간 + 4지지) 오행 카운트
    2. 지장간까지 포함한 확장 카운트
    3. 월지(계절)에 따른 오행 강약 반영
    4. 부족/과다/누락 오행 식별
    
    Args:
        manse_info: 사주 명식 정보 {'년주': 'XX', '월주': 'XX', '일주': 'XX', '시주': 'XX'}
    
    Returns:
        OhengDistribution: 오행 분포 분석 결과
    """
    # 기본 카운트 (8글자)
    oheng_count = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
    
    # 지장간 포함 확장 카운트
    oheng_extended = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
    
    # 4주에서 오행 카운트
    for pillar_key in ['년주', '월주', '일주', '시주']:
        pillar = manse_info.get(pillar_key, '')
        if len(pillar) >= 2:
            # 천간 오행
            cheongan = pillar[0]
            cheongan_oh = O_HAENG_MAP.get(cheongan)
            if cheongan_oh:
                oheng_count[cheongan_oh] += 1
                oheng_extended[cheongan_oh] += 1
            
            # 지지 오행
            jiji = pillar[1]
            jiji_oh = O_HAENG_MAP.get(jiji)
            if jiji_oh:
                oheng_count[jiji_oh] += 1
                oheng_extended[jiji_oh] += 1
            
            # 지장간 오행 (확장 카운트에만 추가)
            jijanggan_list = JIJANGGAN.get(jiji, [])
            for jj in jijanggan_list:
                jj_oh = O_HAENG_MAP.get(jj)
                if jj_oh:
                    # 본기는 1, 중기는 0.6, 여기는 0.3 가중치
                    weight = 1.0 if jijanggan_list.index(jj) == 0 else (0.6 if jijanggan_list.index(jj) == 1 else 0.3)
                    oheng_extended[jj_oh] += weight
    
    # 계절(월지)에 따른 오행 강도 계산
    wolji = manse_info.get('월주', '')[1] if len(manse_info.get('월주', '')) > 1 else ''
    season_strength = SEASON_OHENG_STRENGTH.get(wolji, {'木': 50, '火': 50, '土': 50, '金': 50, '水': 50})
    
    # 최종 오행 강도 계산 (카운트 * 계절 강도 / 100)
    oheng_strength = {}
    for oh in ['木', '火', '土', '金', '水']:
        base_strength = oheng_extended.get(oh, 0) * 10  # 기본 점수 (카운트 * 10)
        season_factor = season_strength.get(oh, 50) / 100  # 계절 보정
        oheng_strength[oh] = round(base_strength * season_factor, 1)
    
    # 부족/과다/누락 판단
    missing = [k for k, v in oheng_count.items() if v == 0]
    weak = [k for k, v in oheng_count.items() if v == 1 and k not in missing]
    excess = [k for k, v in oheng_count.items() if v >= 3]
    
    # 가장 강한 오행
    dominant = max(oheng_strength, key=oheng_strength.get)
    
    return OhengDistribution(
        count=oheng_count,
        strength=oheng_strength,
        missing=missing,
        weak=weak,
        excess=excess,
        dominant=dominant
    )


# =============================================================================
# 8. 2단계: 일주 기준점 분석
# =============================================================================

def analyze_ilju_baseline(manse_info: Dict) -> Dict:
    """
    [2단계] 일주(日柱)를 기준으로 기본 분석을 수행합니다.
    
    분석 요소:
    1. 일간 오행/음양 특성
    2. 일지 특성 (배우자궁)
    3. 일간-일지 관계 (앉은 자리 분석)
    4. 일간 페르소나 (성격 특성)
    5. 월지 기준 계절성
    
    Returns:
        Dict: 일주 기준점 분석 결과
    """
    ilju = manse_info.get('일주', '')
    if len(ilju) < 2:
        return {'error': '일주 데이터 부족'}
    
    ilgan = ilju[0]  # 일간 (천간)
    ilji = ilju[1]   # 일지 (지지)
    
    # 일간 오행
    ilgan_oheng = O_HAENG_MAP.get(ilgan, '불명')
    
    # 일간 음양
    ilgan_yinyang = '양' if ilgan in ['甲', '丙', '戊', '庚', '壬'] else '음'
    
    # 일지 오행
    ilji_oheng = O_HAENG_MAP.get(ilji, '불명')
    
    # 일간-일지 관계 (앉은 자리)
    ilgan_ilji_relation = get_oheng_relation(ilgan_oheng, ilji_oheng)
    
    # 지장간 본기
    ilji_bongi = JIJANGGAN_BONGI.get(ilji, '')
    ilji_bongi_oheng = O_HAENG_MAP.get(ilji_bongi, '')
    
    # 통근 여부 (일간과 일지 지장간 본기가 같은 오행인지)
    is_tonggeun = ilgan_oheng == ilji_bongi_oheng
    
    # 월지 계절
    wolji = manse_info.get('월주', '')[1] if len(manse_info.get('월주', '')) > 1 else ''
    birth_season = JIJI_SEASON.get(wolji, '불명')
    
    # 계절에서 일간의 강약
    season_strength_data = SEASON_OHENG_STRENGTH.get(wolji, {})
    ilgan_season_strength = season_strength_data.get(ilgan_oheng, 50)
    
    # 일간 페르소나 (saju_data.py에서 가져옴)
    persona = TEN_GAN_PERSONA.get(ilgan, {'style': '미정의', 'instruction': '미정의'})
    
    # 일간별 특성 설명
    ilgan_description = {
        '甲': '대들보 나무처럼 곧고 강직한 성품. 리더십과 추진력이 강하며, 새로운 시작에 능함.',
        '乙': '덩굴식물처럼 유연하고 적응력이 뛰어남. 부드럽지만 끈질긴 생명력.',
        '丙': '태양처럼 밝고 따뜻한 에너지. 확산력과 영향력이 크며, 리더 기질.',
        '丁': '촛불처럼 섬세하고 집중력이 강함. 통찰력과 정밀함의 소유자.',
        '戊': '큰 산처럼 묵직하고 안정적. 신뢰감과 포용력이 있으며 중심을 잡는 역할.',
        '己': '논밭의 흙처럼 실속 있고 포용력이 큼. 조율 능력과 실용적 감각.',
        '庚': '원석처럼 강인하고 결단력이 있음. 개혁과 실행의 에너지.',
        '辛': '보석처럼 정제되고 가치를 추구함. 섬세한 감각과 완성도 중시.',
        '壬': '큰 바다처럼 넓고 유연함. 지혜와 정보력, 스케일이 큰 사고.',
        '癸': '이슬비처럼 은밀하고 깊이 있음. 직관력과 잠재적 영향력.',
    }
    
    return {
        'ilju': ilju,
        'ilgan': ilgan,
        'ilji': ilji,
        'ilgan_oheng': ilgan_oheng,
        'ilgan_yinyang': ilgan_yinyang,
        'ilji_oheng': ilji_oheng,
        'ilgan_ilji_relation': ilgan_ilji_relation.value,
        'is_tonggeun': is_tonggeun,
        'ilji_bongi': ilji_bongi,
        'birth_season': birth_season,
        'ilgan_season_strength': ilgan_season_strength,
        'persona': persona,
        'ilgan_description': ilgan_description.get(ilgan, '정보 없음')
    }


# =============================================================================
# 9. 5단계: 통근 및 지장간 스캔
# =============================================================================

def scan_tonggeun_and_jijanggan(manse_info: Dict) -> Dict:
    """
    [5단계] 일간의 통근(通根) 여부와 지장간 분포를 스캔합니다.
    
    통근: 일간과 같은 오행이 지지의 지장간에 있는 경우
    뿌리가 있다 = 통근이 많다 = 신강에 유리
    
    Returns:
        Dict: 통근 분석 결과
    """
    ilgan = manse_info.get('일주', '')[0] if len(manse_info.get('일주', '')) > 0 else ''
    if not ilgan:
        return {'error': '일간 데이터 부족'}
    
    ilgan_oheng = O_HAENG_MAP.get(ilgan, '')
    
    tonggeun_positions = []  # 통근 위치
    jijanggan_analysis = {}  # 지장간 분석
    
    pillar_names = ['년지', '월지', '일지', '시지']
    pillar_keys = ['년주', '월주', '일주', '시주']
    
    for i, pillar_key in enumerate(pillar_keys):
        pillar = manse_info.get(pillar_key, '')
        if len(pillar) < 2:
            continue
        
        jiji = pillar[1]
        jijanggan_list = JIJANGGAN.get(jiji, [])
        
        # 지장간 분석
        jijanggan_analysis[pillar_names[i]] = {
            'jiji': jiji,
            'jijanggan': jijanggan_list,
            'jijanggan_oheng': [O_HAENG_MAP.get(jj, '') for jj in jijanggan_list]
        }
        
        # 통근 체크 (지장간에 일간과 같은 오행이 있는지)
        for jj in jijanggan_list:
            jj_oheng = O_HAENG_MAP.get(jj, '')
            if jj_oheng == ilgan_oheng:
                tonggeun_positions.append({
                    'position': pillar_names[i],
                    'jiji': jiji,
                    'jijanggan': jj,
                    'is_bongi': jj == jijanggan_list[0]  # 본기인지 여부
                })
    
    # 통근 강도 계산 (본기 통근은 더 강함)
    tonggeun_strength = 0
    for tg in tonggeun_positions:
        tonggeun_strength += 2 if tg['is_bongi'] else 1
    
    return {
        'ilgan': ilgan,
        'ilgan_oheng': ilgan_oheng,
        'tonggeun_count': len(tonggeun_positions),
        'tonggeun_strength': tonggeun_strength,
        'tonggeun_positions': tonggeun_positions,
        'jijanggan_analysis': jijanggan_analysis,
        'has_root': len(tonggeun_positions) >= 1
    }


# =============================================================================
# 10. 4단계: 신강/신약 판단 (AI 보조 필요 시 플래그)
# =============================================================================

def determine_gangwak(manse_info: Dict, oheng_dist: OhengDistribution = None) -> GangwakAnalysis:
    """
    [4단계] 신강/신약을 판단합니다.
    
    판단 기준:
    1. 통근(뿌리) 여부 - 가장 중요
    2. 월령(계절) 득령 여부
    3. 비겁(같은 오행) 개수
    4. 인성(나를 생하는 오행) 개수
    5. 관성/재성/식상(나를 억제하는 오행) 개수
    
    신강: 일간의 힘이 강함 (비겁+인성 많음, 통근 있음)
    신약: 일간의 힘이 약함 (관성+재성+식상 많음, 통근 없음)
    
    Returns:
        GangwakAnalysis: 신강/신약 분석 결과
    """
    if oheng_dist is None:
        oheng_dist = analyze_oheng_distribution(manse_info)
    
    # 통근 분석
    tonggeun_result = scan_tonggeun_and_jijanggan(manse_info)
    
    # 일간 정보
    ilgan = manse_info.get('일주', '')[0] if len(manse_info.get('일주', '')) > 0 else ''
    ilgan_oheng = O_HAENG_MAP.get(ilgan, '')
    
    if not ilgan_oheng:
        return GangwakAnalysis(
            is_strong=False, strength_score=50, ilgan_oheng='',
            support_count=0, suppress_count=0, tonggeun_count=0,
            details='일간 데이터 부족'
        )
    
    # 월지(계절) 득령 여부
    wolji = manse_info.get('월주', '')[1] if len(manse_info.get('월주', '')) > 1 else ''
    season_strength_data = SEASON_OHENG_STRENGTH.get(wolji, {})
    is_deukryung = season_strength_data.get(ilgan_oheng, 50) >= 80
    
    # 오행 관계별 카운트
    # 비겁: 같은 오행
    bigyup_count = oheng_dist.count.get(ilgan_oheng, 0) - 1  # 일간 자신 제외
    
    # 인성: 나를 생하는 오행 (수생목, 목생화, 화생토, 토생금, 금생수)
    insung_oheng = {'木': '水', '火': '木', '土': '火', '金': '土', '水': '金'}.get(ilgan_oheng, '')
    insung_count = oheng_dist.count.get(insung_oheng, 0) if insung_oheng else 0
    
    # 관성: 나를 극하는 오행
    gwansung_oheng = {'木': '金', '火': '水', '土': '木', '金': '火', '水': '土'}.get(ilgan_oheng, '')
    gwansung_count = oheng_dist.count.get(gwansung_oheng, 0) if gwansung_oheng else 0
    
    # 재성: 내가 극하는 오행
    jaesung_oheng = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}.get(ilgan_oheng, '')
    jaesung_count = oheng_dist.count.get(jaesung_oheng, 0) if jaesung_oheng else 0
    
    # 식상: 내가 생하는 오행
    siksang_oheng = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}.get(ilgan_oheng, '')
    siksang_count = oheng_dist.count.get(siksang_oheng, 0) if siksang_oheng else 0
    
    # 지지 요소 (비겁, 인성)
    support_count = bigyup_count + insung_count
    suppress_count = gwansung_count + jaesung_count + siksang_count
    tonggeun_count = tonggeun_result.get('tonggeun_count', 0)
    
    # 신강도 점수 계산 (0~100, 50이 기준)
    # 기본 50점에서 시작
    strength_score = 50.0
    
    # 통근 가산 (가장 중요)
    strength_score += tonggeun_count * 10
    if tonggeun_result.get('tonggeun_strength', 0) >= 3:
        strength_score += 5  # 본기 통근 보너스
    
    # 득령 가산
    if is_deukryung:
        strength_score += 15
    elif season_strength_data.get(ilgan_oheng, 50) >= 60:
        strength_score += 5
    
    # 비겁/인성 가산
    strength_score += bigyup_count * 5
    strength_score += insung_count * 4
    
    # 관성/재성/식상 감산
    strength_score -= gwansung_count * 4
    strength_score -= jaesung_count * 3
    strength_score -= siksang_count * 2
    
    # 범위 제한 (0~100)
    strength_score = max(0, min(100, strength_score))
    
    # 신강/신약 판정 (50 기준)
    is_strong = strength_score >= 50
    
    # 상세 설명 생성
    details_parts = []
    if is_deukryung:
        details_parts.append(f"월령 득령({wolji}월)")
    if tonggeun_count >= 2:
        details_parts.append(f"뿌리 강함(통근 {tonggeun_count}개)")
    elif tonggeun_count == 1:
        details_parts.append("뿌리 보통(통근 1개)")
    else:
        details_parts.append("뿌리 약함(통근 없음)")
    
    if support_count >= 3:
        details_parts.append("도움 많음")
    if suppress_count >= 4:
        details_parts.append("억제 요소 많음")
    
    return GangwakAnalysis(
        is_strong=is_strong,
        strength_score=round(strength_score, 1),
        ilgan_oheng=ilgan_oheng,
        support_count=support_count,
        suppress_count=suppress_count,
        tonggeun_count=tonggeun_count,
        details=', '.join(details_parts) if details_parts else '보통'
    )


# =============================================================================
# 11. 4단계 확장: 용신 판단 (AI 보조 필요 시 플래그)
# =============================================================================

def determine_yongsin(manse_info: Dict, gangwak: GangwakAnalysis = None, 
                       oheng_dist: OhengDistribution = None) -> YongsinResult:
    """
    [4단계 확장] 용신(用神)을 판단합니다.
    
    ★ 핵심 수정: 단순히 월지만 보지 않고, 실제 오행 분포를 분석하여 
    부족한 기운을 보완하는 방식으로 용신 산출
    
    용신 판단 우선순위:
    1. 조후용신 (계절 조절) - 여름엔 수, 겨울엔 화
    2. 억부용신 (신강/신약 조절) - 신강이면 설기, 신약이면 생조
    3. 병약용신 (병이 있으면 약) - 특정 오행 과다 시 억제
    4. 통관용신 (충돌 조절) - 두 오행이 충돌 시 중재
    
    Returns:
        YongsinResult: 용신 판단 결과
    """
    if oheng_dist is None:
        oheng_dist = analyze_oheng_distribution(manse_info)
    if gangwak is None:
        gangwak = determine_gangwak(manse_info, oheng_dist)
    
    ilgan = manse_info.get('일주', '')[0] if len(manse_info.get('일주', '')) > 0 else ''
    ilgan_oheng = O_HAENG_MAP.get(ilgan, '')
    wolji = manse_info.get('월주', '')[1] if len(manse_info.get('월주', '')) > 1 else ''
    
    yongsin = ''
    reason = ''
    confidence = 0.7
    
    # ----- 1단계: 조후용신 (계절 극단 시) -----
    # 여름(巳午) 출생: 수(水)가 조후 용신
    if wolji in ['巳', '午'] and oheng_dist.count.get('水', 0) == 0:
        yongsin = '水'
        reason = f"여름({wolji}월) 출생으로 열기가 강해 수(水)로 조절 필요 (조후용신)"
        confidence = 0.9
    
    # 겨울(亥子) 출생: 화(火)가 조후 용신
    elif wolji in ['亥', '子'] and oheng_dist.count.get('火', 0) == 0:
        yongsin = '火'
        reason = f"겨울({wolji}월) 출생으로 한기가 강해 화(火)로 온기 필요 (조후용신)"
        confidence = 0.9
    
    # ----- 2단계: 억부용신 (신강/신약 기준) -----
    elif not yongsin:
        if gangwak.is_strong:
            # 신강: 일간의 힘을 빼주는 오행 필요
            # 우선순위: 관성(억제) > 재성(소모) > 식상(설기)
            gwansung = {'木': '金', '火': '水', '土': '木', '金': '火', '水': '土'}.get(ilgan_oheng, '')
            jaesung = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}.get(ilgan_oheng, '')
            siksang = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}.get(ilgan_oheng, '')
            
            # 가장 부족한 것 중에서 선택
            candidates = [(gwansung, '관성'), (jaesung, '재성'), (siksang, '식상')]
            for cand, cand_name in candidates:
                if cand and oheng_dist.count.get(cand, 0) <= 1:
                    yongsin = cand
                    reason = f"신강(점수 {gangwak.strength_score})하여 {cand_name}({cand})으로 조절 필요 (억부용신)"
                    confidence = 0.8
                    break
            
            # 모두 있으면 가장 약한 것
            if not yongsin:
                min_count = min(oheng_dist.count.get(gwansung, 0), 
                               oheng_dist.count.get(jaesung, 0), 
                               oheng_dist.count.get(siksang, 0))
                for cand, cand_name in candidates:
                    if oheng_dist.count.get(cand, 0) == min_count:
                        yongsin = cand
                        reason = f"신강(점수 {gangwak.strength_score})하여 {cand_name}({cand})으로 설기 필요 (억부용신)"
                        confidence = 0.7
                        break
        else:
            # 신약: 일간을 도와주는 오행 필요
            # 우선순위: 인성(생조) > 비겁(보조)
            insung = {'木': '水', '火': '木', '土': '火', '金': '土', '水': '金'}.get(ilgan_oheng, '')
            bigyup = ilgan_oheng
            
            if insung and oheng_dist.count.get(insung, 0) <= 1:
                yongsin = insung
                reason = f"신약(점수 {gangwak.strength_score})하여 인성({insung})으로 생조 필요 (억부용신)"
                confidence = 0.8
            else:
                yongsin = bigyup
                reason = f"신약(점수 {gangwak.strength_score})하여 비겁({bigyup})으로 힘 보충 필요 (억부용신)"
                confidence = 0.75
    
    # ----- 3단계: 병약용신 (과다 오행 억제) -----
    if oheng_dist.excess:
        excess_oh = oheng_dist.excess[0]
        # 과다 오행을 극하는 오행
        control_oh = {'木': '金', '火': '水', '土': '木', '金': '火', '水': '土'}.get(excess_oh, '')
        if control_oh and not yongsin:
            yongsin = control_oh
            reason = f"{excess_oh}이 과다({oheng_dist.count.get(excess_oh, 0)}개)하여 {control_oh}으로 억제 필요 (병약용신)"
            confidence = 0.75
    
    # ----- 4단계: 토월 기본 처리 (목 선용신) -----
    if wolji in ['辰', '戌', '丑', '未'] and not yongsin:
        yongsin = '木'
        reason = f"토월({wolji}) 출생으로 목(木)이 기본 선 용신 (토월 원칙)"
        confidence = 0.65
    
    # 기본값
    if not yongsin:
        # 가장 부족한 오행
        if oheng_dist.missing:
            yongsin = oheng_dist.missing[0]
            reason = f"원국에 {yongsin}이 없어 보충 필요"
            confidence = 0.6
        elif oheng_dist.weak:
            yongsin = oheng_dist.weak[0]
            reason = f"원국에 {yongsin}이 약해 보충 필요"
            confidence = 0.6
        else:
            # 일간 기준 기본 용신
            default_yongsin = {'木': '水', '火': '木', '土': '火', '金': '土', '水': '金'}
            yongsin = default_yongsin.get(ilgan_oheng, '水')
            reason = "기본 인성 용신 적용"
            confidence = 0.5
    
    # 희신 (용신을 생하는 오행)
    huisin = {'木': '水', '火': '木', '土': '火', '金': '土', '水': '金'}.get(yongsin, '')
    
    # 기신 (용신을 극하는 오행)
    gisin = {'木': '金', '火': '水', '土': '木', '金': '火', '水': '土'}.get(yongsin, '')
    
    return YongsinResult(
        yongsin=yongsin,
        huisin=huisin,
        gisin=gisin,
        reason=reason,
        confidence=confidence
    )


# =============================================================================
# 12. 3단계: 격국 판단 (기본 로직 + AI 보조 플래그)
# =============================================================================

def determine_geokguk(manse_info: Dict, gangwak: GangwakAnalysis = None) -> GeokgukResult:
    """
    [3단계] 격국(格局)을 판단합니다.
    
    정격(正格): 월지 기준 정해지는 일반적인 격
    변격(變格): 특수한 구조 (종격, 화격 등)
    
    ★ 복잡한 격국은 AI 분석 시 추가 판단 필요
    
    Returns:
        GeokgukResult: 격국 판단 결과
    """
    if gangwak is None:
        gangwak = determine_gangwak(manse_info)
    
    ilgan = manse_info.get('일주', '')[0] if len(manse_info.get('일주', '')) > 0 else ''
    ilgan_oheng = O_HAENG_MAP.get(ilgan, '')
    wolji = manse_info.get('월주', '')[1] if len(manse_info.get('월주', '')) > 1 else ''
    wolji_bongi = JIJANGGAN_BONGI.get(wolji, '')
    wolji_bongi_oheng = O_HAENG_MAP.get(wolji_bongi, '')
    
    # 일간과 월지 본기의 관계로 기본 격 판단
    relation = get_oheng_relation(ilgan_oheng, wolji_bongi_oheng)
    
    # 정격 매핑
    geokguk_map = {
        OhengRelation.GENERATE: '인수격',     # 월지가 나를 생 (인성)
        OhengRelation.GENERATED: '식신격',    # 내가 월지를 생 (식상)
        OhengRelation.CONTROL: '재성격',      # 내가 월지를 극 (재성)
        OhengRelation.CONTROLLED: '관성격',   # 월지가 나를 극 (관성)
        OhengRelation.SAME: '비겁격',         # 같은 오행 (비겁)
    }
    
    geokguk_name = geokguk_map.get(relation, '혼합격')
    geokguk_type = '정격'
    strength = '성격'  # 기본: 격이 성립함
    
    # 변격 체크 (극단적 신강/신약)
    if gangwak.strength_score >= 85:
        # 극신강: 종강격 가능성
        geokguk_name = '종강격 가능성'
        geokguk_type = '변격'
        strength = '변격 검토 필요'
    elif gangwak.strength_score <= 15:
        # 극신약: 종격 가능성
        geokguk_name = '종격 가능성'
        geokguk_type = '변격'
        strength = '변격 검토 필요'
    
    # 격국 설명
    descriptions = {
        '인수격': '학문과 지식을 통해 성장하며, 명예와 권위를 중시합니다.',
        '식신격': '표현력과 창의력이 뛰어나며, 생산과 창조에 능합니다.',
        '재성격': '현실적이고 실속을 추구하며, 재물 관리에 능합니다.',
        '관성격': '책임감이 강하고 리더십이 있으며, 조직에서 역할을 잘합니다.',
        '비겁격': '독립심이 강하고 자기주관이 뚜렷하며, 경쟁에 강합니다.',
        '종강격 가능성': '일간의 힘이 극도로 강해 특수 격국 검토 필요',
        '종격 가능성': '일간의 힘이 극도로 약해 특수 격국 검토 필요',
    }
    
    return GeokgukResult(
        geokguk_name=geokguk_name,
        geokguk_type=geokguk_type,
        strength=strength,
        description=descriptions.get(geokguk_name, '상세 분석 필요')
    )


# =============================================================================
# 13. 6단계: 십신/궁위 상호작용 분석
# =============================================================================

def analyze_sipsin_interaction(manse_info: Dict) -> Dict:
    """
    [6단계] 십신(十神)과 궁위(宮位)의 상호작용을 분석합니다.
    
    궁위:
    - 년주: 조상궁, 사회궁 (어린 시절, 외부 환경)
    - 월주: 부모궁, 사업궁 (청년기, 직업 환경)
    - 일주: 본인궁, 배우자궁 (중년, 가정)
    - 시주: 자녀궁, 미래궁 (노년, 결과)
    
    Returns:
        Dict: 십신/궁위 분석 결과
    """
    sipsin_array = manse_info.get('십성_결과_배열', [])
    
    if len(sipsin_array) < 4:
        return {'error': '십성 데이터 부족'}
    
    # 궁위별 십성 정리
    gungwi_analysis = {
        '년주': {
            'name': '조상궁/사회궁',
            'period': '어린 시절 (0~15세)',
            'domain': '조상, 외부 환경, 사회적 배경',
            'cheongan_sipsin': sipsin_array[0].get('stem_ten_god', 'N/A'),
            'jiji_sipsin': sipsin_array[0].get('branch_ten_god', 'N/A'),
        },
        '월주': {
            'name': '부모궁/사업궁',
            'period': '청년기 (15~30세)',
            'domain': '부모, 직업 환경, 사업',
            'cheongan_sipsin': sipsin_array[1].get('stem_ten_god', 'N/A'),
            'jiji_sipsin': sipsin_array[1].get('branch_ten_god', 'N/A'),
        },
        '일주': {
            'name': '본인궁/배우자궁',
            'period': '중년기 (30~45세)',
            'domain': '본인, 배우자, 가정',
            'cheongan_sipsin': sipsin_array[2].get('stem_ten_god', 'N/A'),
            'jiji_sipsin': sipsin_array[2].get('branch_ten_god', 'N/A'),
        },
        '시주': {
            'name': '자녀궁/미래궁',
            'period': '노년기 (45세 이후)',
            'domain': '자녀, 미래, 결과물',
            'cheongan_sipsin': sipsin_array[3].get('stem_ten_god', 'N/A'),
            'jiji_sipsin': sipsin_array[3].get('branch_ten_god', 'N/A'),
        }
    }
    
    # 십신별 통계
    sipsin_stats = {}
    for pillar_sipsin in sipsin_array:
        for key in ['stem_ten_god', 'branch_ten_god']:
            sipsin = pillar_sipsin.get(key, '')
            if sipsin and sipsin not in ['N/A', '일원']:
                sipsin_stats[sipsin] = sipsin_stats.get(sipsin, 0) + 1
    
    # 주요 십신 패턴 분석
    dominant_sipsin = max(sipsin_stats, key=sipsin_stats.get) if sipsin_stats else None
    missing_sipsin_groups = []
    
    # 십성 그룹별 존재 여부
    sipsin_groups = {
        '비겁': ['비견', '겁재'],
        '식상': ['식신', '상관'],
        '재성': ['편재', '정재'],
        '관성': ['편관', '정관'],
        '인성': ['편인', '정인']
    }
    
    for group_name, members in sipsin_groups.items():
        group_count = sum(sipsin_stats.get(m, 0) for m in members)
        if group_count == 0:
            missing_sipsin_groups.append(group_name)
    
    # 특수 조합 분석
    special_patterns = []
    
    # 관살혼잡 (편관 + 정관 동시 존재)
    if sipsin_stats.get('편관', 0) >= 1 and sipsin_stats.get('정관', 0) >= 1:
        special_patterns.append({
            'name': '관살혼잡',
            'description': '편관과 정관이 혼재하여 권위/책임 관련 혼란 가능',
            'advice': '명확한 역할 정립과 선택적 집중 필요'
        })
    
    # 재다신약 (재성 과다)
    jaesung_count = sipsin_stats.get('편재', 0) + sipsin_stats.get('정재', 0)
    if jaesung_count >= 3:
        special_patterns.append({
            'name': '재다신약 가능',
            'description': '재성이 많아 몸이 고단할 수 있음',
            'advice': '건강 관리와 체력 보충에 신경 쓰세요'
        })
    
    # 식상생재 (식상 → 재성 연결)
    siksang_count = sipsin_stats.get('식신', 0) + sipsin_stats.get('상관', 0)
    if siksang_count >= 2 and jaesung_count >= 1:
        special_patterns.append({
            'name': '식상생재',
            'description': '표현/기술이 재물로 연결되는 구조',
            'advice': '자신의 재능을 수익화하는 전략이 유효합니다'
        })
    
    return {
        'gungwi_analysis': gungwi_analysis,
        'sipsin_stats': sipsin_stats,
        'dominant_sipsin': dominant_sipsin,
        'missing_sipsin_groups': missing_sipsin_groups,
        'special_patterns': special_patterns
    }


# =============================================================================
# 14. 7단계: 특수 변수 적용 (신살/공망/합충형)
# =============================================================================

def analyze_special_variables(manse_info: Dict) -> Dict:
    """
    [7단계] 특수 변수(신살, 공망, 합충형)를 분석합니다.
    
    Returns:
        Dict: 특수 변수 분석 결과
    """
    result = {
        'sinsal': [],           # 신살
        'gongmang': [],         # 공망
        'hapchunghyung': [],    # 합충형
    }
    
    # 4주 지지 추출
    jiji_list = []
    for pillar_key in ['년주', '월주', '일주', '시주']:
        pillar = manse_info.get(pillar_key, '')
        if len(pillar) >= 2:
            jiji_list.append(pillar[1])
    
    ilju = manse_info.get('일주', '')
    nyunji = jiji_list[0] if len(jiji_list) > 0 else ''
    ilji = jiji_list[2] if len(jiji_list) > 2 else ''
    
    # --- 신살 분석 ---
    # 역마살
    yeokma_target = YEOKMA.get(nyunji) or YEOKMA.get(ilji)
    if yeokma_target and yeokma_target in jiji_list:
        result['sinsal'].append({
            'name': '역마살',
            'description': '이동, 변화, 활동성이 강한 에너지',
            'interpretation': '변화와 이동이 많은 인생. 해외, 여행, 출장 등과 인연.',
            'advice': '한 곳에 머무르기보다 다양한 경험을 통해 성장하세요.'
        })
    
    # 도화살
    dohwa_target = DOHWA.get(nyunji) or DOHWA.get(ilji)
    if dohwa_target and dohwa_target in jiji_list:
        result['sinsal'].append({
            'name': '도화살',
            'description': '매력, 인기, 이성운과 관련된 에너지',
            'interpretation': '대인관계에서 매력이 있고 인기를 끄는 구조.',
            'advice': '매력을 긍정적으로 활용하되, 관계 경계 설정에 주의하세요.'
        })
    
    # 화개살
    hwagae_target = HWAGAE.get(nyunji) or HWAGAE.get(ilji)
    if hwagae_target and hwagae_target in jiji_list:
        result['sinsal'].append({
            'name': '화개살',
            'description': '예술성, 종교성, 학문적 깊이와 관련',
            'interpretation': '철학적, 예술적, 종교적 관심이 깊은 구조.',
            'advice': '깊이 있는 공부나 예술 활동이 마음의 안정을 줍니다.'
        })
    
    # --- 공망 분석 ---
    if ilju in GONGMANG:
        gongmang_jiji = GONGMANG[ilju]
        for gm in gongmang_jiji:
            if gm in jiji_list:
                position = ['년지', '월지', '일지', '시지'][jiji_list.index(gm)]
                result['gongmang'].append({
                    'position': position,
                    'jiji': gm,
                    'interpretation': f'{position}({gm})에 공망. 해당 영역에서 빈 공간의 에너지.',
                    'advice': '공망 위치의 기대를 낮추고, 다른 영역에서 보완하세요.'
                })
    
    # --- 합충형 분석 ---
    # 지지 충(衝)
    for i, j1 in enumerate(jiji_list):
        for j, j2 in enumerate(jiji_list):
            if i < j and JIJI_CHUNG.get(j1) == j2:
                positions = ['년지', '월지', '일지', '시지']
                result['hapchunghyung'].append({
                    'type': '충',
                    'positions': f'{positions[i]}-{positions[j]}',
                    'jiji': f'{j1}-{j2}',
                    'interpretation': '충돌과 변화의 에너지. 갈등과 분리 가능성.',
                    'advice': '대립을 피하고 유연하게 대처하세요. 변화를 기회로 삼으세요.'
                })
    
    # 지지 삼합
    jiji_set = frozenset(jiji_list)
    for samhap_set, result_oh in JIJI_SAMHAP.items():
        intersection = jiji_set & samhap_set
        if len(intersection) >= 2:
            result['hapchunghyung'].append({
                'type': '삼합',
                'jiji': f"{', '.join(intersection)} ({result_oh} 기운 강화)",
                'interpretation': f'{result_oh} 기운이 합으로 강화됨',
                'advice': f'{result_oh} 오행의 특성을 적극 활용하세요.'
            })
    
    # 지지 육합
    for i, j1 in enumerate(jiji_list):
        for j, j2 in enumerate(jiji_list):
            if i < j:
                hap_result = JIJI_YUKHAP.get((j1, j2))
                if hap_result:
                    positions = ['년지', '월지', '일지', '시지']
                    result['hapchunghyung'].append({
                        'type': '육합',
                        'positions': f'{positions[i]}-{positions[j]}',
                        'jiji': f'{j1}-{j2} → {hap_result}',
                        'interpretation': f'{j1}{j2} 육합으로 {hap_result} 기운 형성',
                        'advice': '합의 에너지를 긍정적 관계 형성에 활용하세요.'
                    })
    
    # 자형(自刑)
    for jiji in jiji_list:
        if jiji_list.count(jiji) >= 2 and jiji in ['辰', '午', '酉', '亥']:
            result['hapchunghyung'].append({
                'type': '자형',
                'jiji': f'{jiji}-{jiji}',
                'interpretation': f'{jiji}가 중복되어 자기 충돌의 에너지',
                'advice': '자기 비판을 줄이고 자신을 수용하는 연습을 하세요.'
            })
    
    return result


# =============================================================================
# 15. 8단계: 대운/세운 타임라인 분석
# =============================================================================

def analyze_fortune_timeline(manse_info: Dict, daewoon_info: Dict, target_year: int = 2026) -> Dict:
    """
    [8단계] 대운/세운 타임라인을 분석합니다.
    
    Args:
        manse_info: 사주 명식
        daewoon_info: 대운 정보
        target_year: 분석 대상 연도
    
    Returns:
        Dict: 운세 타임라인 분석 결과
    """
    ilgan = manse_info.get('일주', '')[0] if len(manse_info.get('일주', '')) > 0 else ''
    ilgan_oheng = O_HAENG_MAP.get(ilgan, '')
    wolji = manse_info.get('월주', '')[1] if len(manse_info.get('월주', '')) > 1 else ''
    ilji = manse_info.get('일주', '')[1] if len(manse_info.get('일주', '')) > 1 else ''
    
    # 세운 간지 계산 (target_year 기준)
    sewoon_idx = (target_year - 1864) % 60
    sewoon_ganji = GANJI_60[sewoon_idx]
    sewoon_gan = sewoon_ganji[0]
    sewoon_ji = sewoon_ganji[1]
    
    # 세운 오행
    sewoon_gan_oheng = O_HAENG_MAP.get(sewoon_gan, '')
    sewoon_ji_oheng = O_HAENG_MAP.get(sewoon_ji, '')
    
    # 현재 대운 찾기
    current_daewoon = None
    daewoon_list = daewoon_info.get('대운_간지_배열', [])
    
    # 간단하게 target_year 기준 대운 추정
    # (실제로는 출생년도와 대운수를 고려해야 함)
    birth_year_str = manse_info.get('출생일', '')
    try:
        if birth_year_str:
            birth_year = int(birth_year_str[:4])
            age_at_target = target_year - birth_year + 1  # 한국 나이
            
            # 대운 찾기
            daewoon_su = daewoon_info.get('대운수', 1)
            for dw in daewoon_list:
                dw_age = dw.get('age', 0)
                if dw_age <= age_at_target < dw_age + 10:
                    current_daewoon = dw
                    break
    except:
        pass
    
    # 대운이 없으면 첫 번째 대운 사용
    if current_daewoon is None and daewoon_list:
        current_daewoon = daewoon_list[0]
    
    daewoon_ganji = current_daewoon.get('ganji', '') if current_daewoon else ''
    daewoon_gan = daewoon_ganji[0] if len(daewoon_ganji) >= 2 else ''
    daewoon_ji = daewoon_ganji[1] if len(daewoon_ganji) >= 2 else ''
    
    # 세운과 원국의 상호작용 분석
    sewoon_analysis = {
        'year': target_year,
        'ganji': sewoon_ganji,
        'gan_oheng': sewoon_gan_oheng,
        'ji_oheng': sewoon_ji_oheng,
    }
    
    # 일간과 세운 천간 관계
    if sewoon_gan_oheng and ilgan_oheng:
        sewoon_gan_relation = get_oheng_relation(ilgan_oheng, sewoon_gan_oheng)
        sewoon_analysis['gan_relation'] = sewoon_gan_relation.value
    
    # 세운 지지와 충 체크
    sewoon_chung = []
    for pillar_key, idx in [('년주', 0), ('월주', 1), ('일주', 2), ('시주', 3)]:
        pillar = manse_info.get(pillar_key, '')
        if len(pillar) >= 2:
            pillar_ji = pillar[1]
            if JIJI_CHUNG.get(pillar_ji) == sewoon_ji:
                sewoon_chung.append({
                    'position': pillar_key,
                    'jiji': f'{pillar_ji}-{sewoon_ji}',
                    'type': '세운충'
                })
    
    sewoon_analysis['chung'] = sewoon_chung
    
    # 대운 분석
    daewoon_analysis = {
        'current': current_daewoon,
        'ganji': daewoon_ganji,
    }
    
    if daewoon_gan and daewoon_ji:
        daewoon_gan_oheng = O_HAENG_MAP.get(daewoon_gan, '')
        daewoon_ji_oheng = O_HAENG_MAP.get(daewoon_ji, '')
        daewoon_analysis['gan_oheng'] = daewoon_gan_oheng
        daewoon_analysis['ji_oheng'] = daewoon_ji_oheng
        
        if daewoon_gan_oheng and ilgan_oheng:
            daewoon_analysis['gan_relation'] = get_oheng_relation(ilgan_oheng, daewoon_gan_oheng).value
    
    # saju_data.py의 점수 계산 함수 활용
    sa_ju_data = {
        '일간': ilgan,
        '월지': wolji,
        '일지': ilji
    }
    sewoon_luck_data = {
        '천간': sewoon_gan,
        '지지': sewoon_ji,
        '운의종류': '세운'
    }
    
    try:
        sewoon_score = calculate_total_luck_score(sa_ju_data, sewoon_luck_data)
        sewoon_analysis['score'] = sewoon_score.get('total', 50)
    except:
        sewoon_analysis['score'] = 50
    
    return {
        'sewoon': sewoon_analysis,
        'daewoon': daewoon_analysis,
        'target_year': target_year
    }


# =============================================================================
# 16. 종합 분석 함수 (1-8단계 통합)
# =============================================================================

def run_full_analysis(manse_info: Dict, daewoon_info: Dict = None, target_year: int = 2026) -> Dict:
    """
    [종합] 금쪽이 분석 엔진의 1-8단계를 모두 실행합니다.
    
    9단계(종합 해석)는 AI가 담당하므로 여기서는 데이터만 준비합니다.
    
    Args:
        manse_info: 사주 명식 정보
        daewoon_info: 대운 정보
        target_year: 분석 대상 연도
    
    Returns:
        Dict: 전체 분석 결과
    """
    result = {
        'step1_oheng': None,
        'step2_ilju': None,
        'step3_geokguk': None,
        'step4_gangwak': None,
        'step4_yongsin': None,
        'step5_tonggeun': None,
        'step6_sipsin': None,
        'step7_special': None,
        'step8_timeline': None,
        'summary': {},
        'ai_needed': []  # AI 추가 분석이 필요한 항목
    }
    
    try:
        # 1단계: 오행 분포 분석
        oheng_dist = analyze_oheng_distribution(manse_info)
        result['step1_oheng'] = {
            'count': oheng_dist.count,
            'strength': oheng_dist.strength,
            'missing': oheng_dist.missing,
            'weak': oheng_dist.weak,
            'excess': oheng_dist.excess,
            'dominant': oheng_dist.dominant
        }
        
        # 2단계: 일주 기준점 분석
        result['step2_ilju'] = analyze_ilju_baseline(manse_info)
        
        # 4단계: 신강/신약 판단 (3단계보다 먼저)
        gangwak = determine_gangwak(manse_info, oheng_dist)
        result['step4_gangwak'] = {
            'is_strong': gangwak.is_strong,
            'strength_score': gangwak.strength_score,
            'ilgan_oheng': gangwak.ilgan_oheng,
            'support_count': gangwak.support_count,
            'suppress_count': gangwak.suppress_count,
            'tonggeun_count': gangwak.tonggeun_count,
            'details': gangwak.details
        }
        
        # 3단계: 격국 판단
        geokguk = determine_geokguk(manse_info, gangwak)
        result['step3_geokguk'] = {
            'geokguk_name': geokguk.geokguk_name,
            'geokguk_type': geokguk.geokguk_type,
            'strength': geokguk.strength,
            'description': geokguk.description
        }
        
        # 격국이 변격이면 AI 추가 분석 필요
        if geokguk.geokguk_type == '변격':
            result['ai_needed'].append('geokguk_verification')
        
        # 4단계 확장: 용신 판단
        yongsin = determine_yongsin(manse_info, gangwak, oheng_dist)
        result['step4_yongsin'] = {
            'yongsin': yongsin.yongsin,
            'huisin': yongsin.huisin,
            'gisin': yongsin.gisin,
            'reason': yongsin.reason,
            'confidence': yongsin.confidence
        }
        
        # 용신 확신도가 낮으면 AI 추가 분석 필요
        if yongsin.confidence < 0.7:
            result['ai_needed'].append('yongsin_verification')
        
        # 5단계: 통근 및 지장간 스캔
        result['step5_tonggeun'] = scan_tonggeun_and_jijanggan(manse_info)
        
        # 6단계: 십신/궁위 상호작용
        result['step6_sipsin'] = analyze_sipsin_interaction(manse_info)
        
        # 7단계: 특수 변수 적용
        result['step7_special'] = analyze_special_variables(manse_info)
        
        # 8단계: 대운/세운 타임라인
        if daewoon_info:
            result['step8_timeline'] = analyze_fortune_timeline(manse_info, daewoon_info, target_year)
        
        # 요약 정보 생성
        result['summary'] = {
            'ilgan': result['step2_ilju'].get('ilgan', ''),
            'ilgan_oheng': result['step2_ilju'].get('ilgan_oheng', ''),
            'birth_season': result['step2_ilju'].get('birth_season', ''),
            'is_strong': gangwak.is_strong,
            'strength_description': '신강' if gangwak.is_strong else '신약',
            'yongsin': yongsin.yongsin,
            'yongsin_reason': yongsin.reason,
            'geokguk': geokguk.geokguk_name,
            'missing_oheng': oheng_dist.missing,
            'dominant_sipsin': result['step6_sipsin'].get('dominant_sipsin'),
            'sinsal_count': len(result['step7_special'].get('sinsal', [])),
            'has_chung': len([h for h in result['step7_special'].get('hapchunghyung', []) if h.get('type') == '충']) > 0
        }
        
    except Exception as e:
        result['error'] = str(e)
        result['ai_needed'].append('full_analysis_retry')
    
    return result


# =============================================================================
# 17. 프리미엄 섹션 생성 함수 (개선된 버전)
# =============================================================================

def generate_premium_content(manse_info: Dict, analysis_result: Dict = None) -> Dict:
    """
    분석 결과를 바탕으로 프리미엄 섹션 콘텐츠를 생성합니다.
    
    기존 analysis_core_final.py의 ensure_premium_sections를 대체하며,
    더 정확한 용신과 오행 분석 결과를 반영합니다.
    """
    if analysis_result is None:
        analysis_result = run_full_analysis(manse_info)
    
    # 분석 결과에서 필요한 데이터 추출
    yongsin = analysis_result.get('step4_yongsin', {}).get('yongsin', '水')
    yongsin_reason = analysis_result.get('step4_yongsin', {}).get('reason', '')
    missing_oheng = analysis_result.get('step1_oheng', {}).get('missing', [])
    weak_oheng = analysis_result.get('step1_oheng', {}).get('weak', [])
    ilgan = analysis_result.get('summary', {}).get('ilgan', '')
    is_strong = analysis_result.get('summary', {}).get('is_strong', False)
    
    # 십신 패턴
    sipsin_stats = analysis_result.get('step6_sipsin', {}).get('sipsin_stats', {})
    dominant_sipsin = analysis_result.get('step6_sipsin', {}).get('dominant_sipsin', '')
    
    # 용신 색상 매핑
    yongsin_color_map = {
        '木': '#A8D5BA', '화': '#A8D5BA', '목': '#A8D5BA',
        '火': '#FFB7B2', '화': '#FFB7B2',
        '土': '#E6CEAC', '토': '#E6CEAC',
        '金': '#D3D3D3', '금': '#D3D3D3',
        '水': '#A2C2E0', '수': '#A2C2E0'
    }
    yongsin_color = yongsin_color_map.get(yongsin, '#A2C2E0')
    
    # 용신 한글 변환
    yongsin_kr = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}.get(yongsin, yongsin)
    
    premium_content = {}
    
    # === digital_amulet (디지털 부적) ===
    yongsin_quotes = {
        '木': "나무는 바람에 흔들려도 뿌리를 더 깊이 내립니다. 당신의 성장도 그렇습니다.",
        '火': "작은 불씨가 어둠 전체를 밝힙니다. 당신의 열정이 길을 비출 것입니다.",
        '土': "대지는 묵묵히 모든 것을 품고 키워냅니다. 당신의 중심이 흔들리지 않기를.",
        '金': "금은 두드려질수록 더 단단해집니다. 지금의 어려움이 당신을 빛나게 할 것입니다.",
        '水': "물은 장애물을 만나면 돌아 흐릅니다. 막히면 고이고, 고이면 깊어지고, 깊어지면 다시 흐릅니다."
    }
    premium_content['digital_amulet'] = {
        'yongsin_element': yongsin_kr,
        'quote': yongsin_quotes.get(yongsin, "당신 안에 이미 답이 있습니다."),
        'image_color': yongsin_color
    }
    
    # === weakness_missions (개운법) - 정확한 용신 기반 ===
    element_activities = {
        '木': ["새로운 시작을 위한 계획 세우기", "아침 스트레칭이나 요가", "식물 키우기 시작",
               "새로운 분야 공부 시작", "봉사활동 참여", "숲이나 공원 산책",
               "새로운 취미 도전", "독서 모임 참여", "창의적 프로젝트 시작",
               "건강검진 및 운동 루틴", "목표 중간 점검", "내년 성장 계획 수립"],
        '火': ["SNS나 블로그에 나의 이야기 표현", "열정 느끼는 활동에 시간 투자", "밝은 색상 옷 활용",
               "발표하거나 의견 표현 연습", "에너지 넘치는 운동 시작", "따뜻한 색 조명 활용",
               "열정적인 사람들과 모임", "자신감 높이는 자기계발", "창작 활동 도전",
               "리더십 역할 찾기", "감사 일기 쓰기", "올해 성취 축하"],
        '土': ["규칙적인 일상 루틴 만들기", "신뢰할 수 있는 멘토 찾기", "재정 계획 점검",
               "집 정리정돈", "가족과 함께하는 시간", "중심 잡는 명상",
               "안정적 수입원 검토", "신뢰 관계 강화", "부동산 정보 수집",
               "건강 관리 루틴 정착", "인생 중심 가치 점검", "안정적 기반 계획"],
        '金': ["결단력 있게 미루던 일 처리", "불필요한 관계 정리", "우선순위 명확히 하기",
               "전문성 높이는 교육", "명확한 경계 설정 연습", "효율적 시간 관리",
               "품질 좋은 물건으로 교체", "전문가 네트워크 구축", "단호하게 거절 연습",
               "작은 성공 경험 쌓기", "올해 결정들 복기", "핵심 결단 목록 작성"],
        '水': ["조용히 혼자만의 시간 갖기", "직감 믿고 작은 결정 내리기", "물 관련 활동",
               "깊이 있는 대화 나누기", "명상이나 마음 챙김", "새로운 정보 탐색",
               "감정 일기 쓰기", "조용한 카페에서 독서", "수면 품질 개선",
               "심층적 학습 시작", "올해 지혜 정리", "내면의 목소리에 귀 기울이기"]
    }
    
    target_element = yongsin
    activities = element_activities.get(target_element, element_activities['水'])
    
    # 부족 오행 설명
    if missing_oheng:
        missing_kr = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
        element_kr_name = {'木': '시작의 힘', '火': '열정의 힘', '土': '안정의 힘', '金': '결단의 힘', '水': '지혜의 힘'}
        first_missing = missing_oheng[0]
        weakness_desc = f"사주에 {missing_kr.get(first_missing, first_missing)}({element_kr_name.get(first_missing, '')})이 없어 보완이 필요합니다."
    elif weak_oheng:
        missing_kr = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
        element_kr_name = {'木': '시작의 힘', '火': '열정의 힘', '土': '안정의 힘', '金': '결단의 힘', '水': '지혜의 힘'}
        first_weak = weak_oheng[0]
        weakness_desc = f"사주에 {missing_kr.get(first_weak, first_weak)}({element_kr_name.get(first_weak, '')})이 약하여 보완이 필요합니다."
    else:
        weakness_desc = f"용신인 {yongsin_kr} 기운을 강화하면 전체 운기가 상승합니다. {yongsin_reason}"
    
    monthly_missions = {}
    for i in range(1, 13):
        monthly_missions[str(i)] = activities[(i - 1) % len(activities)]
    
    premium_content['weakness_missions'] = {
        'missing_element': weakness_desc,
        'monthly_missions': monthly_missions
    }
    
    return premium_content


# =============================================================================
# 테스트 코드
# =============================================================================

if __name__ == "__main__":
    # 테스트용 사주 데이터 (庚일간, 戌월, 목 3개, 화 0개)
    test_manse = {
        '년주': '壬寅',
        '월주': '庚戌',
        '일주': '庚午',
        '시주': '甲申',
        '출생일': '1982-10-15 14:30:00',
        '십성_결과_배열': [
            {'stem_ten_god': '편인', 'branch_ten_god': '편재'},
            {'stem_ten_god': '비견', 'branch_ten_god': '편인'},
            {'stem_ten_god': '일원', 'branch_ten_god': '정관'},
            {'stem_ten_god': '편재', 'branch_ten_god': '비견'}
        ]
    }
    
    test_daewoon = {
        '대운수': 3,
        '순행_역행': '순행',
        '대운_간지_배열': [
            {'age': 3, 'ganji': '辛亥'},
            {'age': 13, 'ganji': '壬子'},
            {'age': 23, 'ganji': '癸丑'},
            {'age': 33, 'ganji': '甲寅'},
            {'age': 43, 'ganji': '乙卯'},
        ]
    }
    
    print("=" * 60)
    print("금쪽이 사주 분석 엔진 테스트")
    print("=" * 60)
    
    # 전체 분석 실행
    result = run_full_analysis(test_manse, test_daewoon, 2026)
    
    print(f"\n📊 요약:")
    print(f"  일간: {result['summary'].get('ilgan')} ({result['summary'].get('ilgan_oheng')})")
    print(f"  출생 계절: {result['summary'].get('birth_season')}")
    print(f"  신강/신약: {result['summary'].get('strength_description')}")
    print(f"  격국: {result['summary'].get('geokguk')}")
    print(f"  용신: {result['summary'].get('yongsin')} - {result['summary'].get('yongsin_reason')}")
    
    print(f"\n🔍 오행 분포:")
    print(f"  카운트: {result['step1_oheng'].get('count')}")
    print(f"  부족: {result['step1_oheng'].get('missing')}")
    print(f"  과다: {result['step1_oheng'].get('excess')}")
    
    print(f"\n🎯 특수 변수:")
    print(f"  신살: {len(result['step7_special'].get('sinsal', []))}개")
    print(f"  공망: {len(result['step7_special'].get('gongmang', []))}개")
    print(f"  합충형: {len(result['step7_special'].get('hapchunghyung', []))}개")
    
    if result.get('ai_needed'):
        print(f"\n⚠️ AI 추가 분석 필요: {result['ai_needed']}")
    
    print("\n✅ 테스트 완료!")
