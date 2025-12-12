from typing import Dict, List, Optional
from datetime import datetime


# ============================================================
# 📊 HTML 템플릿 정의 (디자이너 수정본 + Rich Chart.js 통합)
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>희구소_Hiddenlucklab_2026_리포트</title>
    
    <!-- 외부 라이브러리 CDN -->
    <link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>

    <style>
        /* ========== 기본 설정 ========== */
        :root {
            /* 색상 팔레트 */
            --color-primary: #1A1A1A;
            --color-secondary: #4A4A4A;
            --color-accent: #FF6B6B;
            --color-bg: #FFFFFF;
            --color-surface: #F8F9FA;
            
            /* 운세 카테고리 색상 */
            --color-wealth: #FFB347;      /* 재물: 주황 */
            --color-career: #87CEEB;      /* 직업: 하늘색 */
            --color-health: #90EE90;      /* 건강: 연두 */
            --color-relationship: #FFB6C1; /* 관계: 핑크 */
            --color-study: #DDA0DD;       /* 학업: 보라 */
            
            /* 타이포그래피 */
            --font-main: 'Noto Sans KR', sans-serif;
            --font-accent: 'Gowun Batang', serif;
            
            /* 간격 */
            --spacing-xs: 8px;
            --spacing-sm: 16px;
            --spacing-md: 24px;
            --spacing-lg: 32px;
            --spacing-xl: 48px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: var(--font-main);
            font-size: 16px;
            line-height: 1.6;
            color: var(--color-primary);
            background: var(--color-bg);
            padding-top: 80px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 0 var(--spacing-md) 100px var(--spacing-md);
        }

        /* ========== 네비게이션 바 ========== */
        .nav-bar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0,0,0,0.08);
            padding: var(--spacing-sm);
            display: flex;
            justify-content: center;
            gap: var(--spacing-sm);
            z-index: 1000;
            flex-wrap: wrap;
        }

        .nav-item {
            text-decoration: none;
            color: var(--color-secondary);
            font-size: 0.9rem;
            font-weight: 500;
            padding: var(--spacing-xs) var(--spacing-sm);
            border-radius: 20px;
            transition: all 0.3s ease;
        }

        .nav-item:hover {
            background: var(--color-surface);
            color: var(--color-primary);
        }

        /* ========== 헤더 ========== */
        .header {
            text-align: center;
            margin-bottom: var(--spacing-xl);
            padding: var(--spacing-xl) 0;
        }

        .main-title {
            font-family: var(--font-accent);
            font-size: 3rem;
            font-weight: 700;
            color: var(--color-primary);
            margin-bottom: var(--spacing-sm);
            line-height: 1.2;
        }

        .subtitle {
            font-size: 1.2rem;
            color: var(--color-secondary);
            font-weight: 300;
        }

        /* ========== 카드 스타일 ========== */
        .card {
            background: var(--color-bg);
            border-radius: 16px;
            padding: var(--spacing-lg);
            margin-bottom: var(--spacing-lg);
            box-shadow: 0 4px 24px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.04);
        }

        .section-title {
            font-family: var(--font-accent);
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: var(--spacing-md);
            color: var(--color-primary);
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
        }

        /* ========== 사주 명식 ========== */
        .saju-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: var(--spacing-md);
            margin-top: var(--spacing-md);
        }

        .saju-pillar {
            text-align: center;
            padding: var(--spacing-md);
            background: var(--color-surface);
            border-radius: 12px;
            transition: all 0.3s ease;
        }

        .saju-pillar:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }

        .saju-label {
            font-size: 0.85rem;
            color: var(--color-secondary);
            margin-bottom: var(--spacing-xs);
            font-weight: 500;
        }

        .saju-hanja {
            font-size: 2rem;
            font-weight: 700;
            margin: var(--spacing-sm) 0;
            color: var(--color-primary);
        }

        .saju-korean {
            font-size: 0.9rem;
            color: var(--color-secondary);
        }

        /* ========== 핵심 요약 카드 ========== */
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--spacing-md);
            margin-top: var(--spacing-md);
        }

        .summary-item {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: var(--spacing-md);
            border-radius: 12px;
            border-left: 4px solid var(--color-accent);
        }

        .summary-item h3 {
            font-size: 1.1rem;
            margin-bottom: var(--spacing-xs);
            color: var(--color-primary);
        }

        .summary-item p {
            font-size: 0.95rem;
            color: var(--color-secondary);
            line-height: 1.6;
        }

        /* ========== 상세 분석 박스 ========== */
        .detail-box {
            background: var(--color-bg);
            padding: var(--spacing-lg);
            border-radius: 12px;
            margin-bottom: var(--spacing-md);
            border: 1px solid rgba(0,0,0,0.04);
        }

        .detail-title {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: var(--spacing-md);
            color: var(--color-primary);
        }

        .detail-content {
            font-size: 1rem;
            line-height: 1.8;
            color: var(--color-secondary);
        }

        /* ========== 월별 가이드 ========== */
        .month-btn-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: var(--spacing-xs);
            margin-bottom: var(--spacing-md);
        }

        .month-btn {
            padding: var(--spacing-sm);
            border: 1px solid #ddd;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        .month-btn:hover {
            background: var(--color-surface);
            border-color: var(--color-accent);
        }

        .month-btn.active {
            background: var(--color-accent);
            color: white;
            border-color: var(--color-accent);
        }

        /* ========== 차트 스타일 ========== */
        .flow-chart-box {
            height: 300px;
            margin: var(--spacing-md) 0;
            background: var(--color-surface);
            border-radius: 12px;
            padding: var(--spacing-md);
        }

        /* ========== 개운법 ========== */
        .guide-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: var(--spacing-md);
            margin-top: var(--spacing-md);
        }

        .guide-item {
            background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
            padding: var(--spacing-md);
            border-radius: 12px;
            border: 1px solid rgba(0,0,0,0.06);
        }

        .guide-item h4 {
            font-size: 1.2rem;
            margin-bottom: var(--spacing-sm);
            color: var(--color-primary);
        }

        .guide-item p {
            font-size: 0.95rem;
            color: var(--color-secondary);
            line-height: 1.6;
        }

        /* ========== 반응형 디자인 ========== */
        @media (max-width: 768px) {
            .saju-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .summary-grid {
                grid-template-columns: 1fr;
            }
            
            .month-btn-grid {
                grid-template-columns: repeat(4, 1fr);
            }
            
            .main-title {
                font-size: 2rem;
            }
        }

        /* ========== 프리미엄 섹션 컬러 ========== */
        .premium-mint { background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-left: 4px solid #0ea5e9; }
        .premium-peach { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-left: 4px solid #f59e0b; }
        .premium-green { background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%); border-left: 4px solid #22c55e; }
        .premium-pink { background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%); border-left: 4px solid #ec4899; }
        .premium-blue { background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%); border-left: 4px solid #6366f1; }
        .premium-purple { background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%); border-left: 4px solid #a855f7; }
    </style>
</head>
<body>
    <!-- 네비게이션 바 -->
    <div class="nav-bar">
        <a href="#saju" class="nav-item">나의 사주</a>
        <a href="#summary" class="nav-item">핵심 요약</a>
        <a href="#detail" class="nav-item">상세 분석</a>
        <a href="#premium" class="nav-item">프리미엄 가이드</a>
        <a href="#actions" class="nav-item">솔루션</a>
    </div>

    <div class="container">
        <!-- 헤더 -->
        <div class="header">
            <h1 class="main-title">희구소: 2026 마스터 리포트</h1>
            <p class="subtitle">당신만의 맞춤형 운세 분석</p>
        </div>

        <!-- 사주 명식 -->
        <div class="card" id="saju">
            <h2 class="section-title">
                <i class="fas fa-yin-yang"></i> 나의 사주 명식
            </h2>
            <div class="saju-grid" id="sajuGrid"></div>
        </div>

        <!-- 핵심 요약 -->
        <div class="card" id="summary">
            <h2 class="section-title">
                <i class="fas fa-star"></i> 핵심 요약
            </h2>
            <div class="summary-grid" id="summaryGrid"></div>
        </div>

        <!-- 상세 분석 -->
        <div class="card" id="detail">
            <h2 class="section-title">
                <i class="fas fa-book-open"></i> 상세 분석
            </h2>
            <div id="detailContent"></div>
        </div>

        <!-- 🆕 프리미엄 섹션 (Python에서 동적 삽입) -->
        <div id="premium-sections"></div>

        <!-- 개운법 -->
        <div class="card" id="actions">
            <h2 class="section-title">
                <i class="fas fa-lightbulb"></i> 개운법 & 실천 가이드
            </h2>
            <div class="guide-grid" id="guideGrid"></div>
        </div>

        <!-- 월별 운세 -->
        <div class="card" id="monthly">
            <h2 class="section-title">
                <i class="fas fa-calendar-alt"></i> 2026 월별 운세
            </h2>
            <div class="month-btn-grid" id="monthBtnGrid"></div>
            <div class="flow-chart-box">
                <canvas id="monthlyFlowChart"></canvas>
            </div>
            <div id="monthDetail" class="detail-box"></div>
        </div>

        <!-- 최종 메시지 -->
        <div class="card" style="text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
            <h2 style="color: white; margin-bottom: var(--spacing-md);">🌟 당신의 2026년을 응원합니다</h2>
            <p style="font-size: 1.1rem; line-height: 1.8;">
                이 리포트가 당신의 삶에 긍정적인 변화를 가져오길 바랍니다.<br>
                더 자세한 상담이 필요하시면 언제든 연락주세요.
            </p>
        </div>
    </div>

    <script>
        // ============================================================
        // 📊 Mock 데이터 (실제 운영 시 Python에서 주입)
        // ============================================================
        const MOCK_REPORT_DATA = {
            saju: {
                year: { cheon: '갑(甲)', ji: '인(寅)' },
                month: { cheon: '을(乙)', ji: '묘(卯)' },
                day: { cheon: '병(丙)', ji: '진(辰)' },
                hour: { cheon: '정(丁)', ji: '사(巳)' }
            },
            summary: {
                yongsin: '목(木)',
                character: '적극적이고 창의적인 성격',
                wealth: '2026년 상반기 재물운 상승',
                caution: '건강 관리 필요'
            },
            detail: {
                character: '타고난 리더십과 창의성을 가진 사람입니다...',
                career: '새로운 도전이 필요한 시기입니다...',
                wealth: '투자보다는 저축을 추천합니다...',
                health: '규칙적인 운동이 필요합니다...'
            },
            monthly: [
                { month: 1, score: 75, daewoon: '갑인(甲寅)', yeonwoon: '경자(庚子)', advice: '새로운 시작의 달' },
                { month: 2, score: 68, daewoon: '갑인(甲寅)', yeonwoon: '신축(辛丑)', advice: '인내가 필요한 시기' },
                { month: 3, score: 82, daewoon: '갑인(甲寅)', yeonwoon: '임인(壬寅)', advice: '기회의 달' },
                { month: 4, score: 70, daewoon: '갑인(甲寅)', yeonwoon: '계묘(癸卯)', advice: '안정된 운세' },
                { month: 5, score: 55, daewoon: '갑인(甲寅)', yeonwoon: '갑진(甲辰)', advice: '주의가 필요한 달' },
                { month: 6, score: 78, daewoon: '갑인(甲寅)', yeonwoon: '을사(乙巳)', advice: '재물운 상승' },
                { month: 7, score: 85, daewoon: '갑인(甲寅)', yeonwoon: '병오(丙午)', advice: '최고의 운세' },
                { month: 8, score: 72, daewoon: '갑인(甲寅)', yeonwoon: '정미(丁未)', advice: '평온한 시기' },
                { month: 9, score: 60, daewoon: '갑인(甲寅)', yeonwoon: '무신(戊申)', advice: '조심스러운 결정' },
                { month: 10, score: 88, daewoon: '갑인(甲寅)', yeonwoon: '기유(己酉)', advice: '큰 성과 예상' },
                { month: 11, score: 75, daewoon: '갑인(甲寅)', yeonwoon: '경술(庚戌)', advice: '마무리의 시기' },
                { month: 12, score: 80, daewoon: '갑인(甲寅)', yeonwoon: '신해(辛亥)', advice: '내년 준비' }
            ],
            actions: [
                { category: '색상', content: '초록색과 파란색을 활용하세요' },
                { category: '방향', content: '동쪽과 북쪽이 길합니다' },
                { category: '숫자', content: '3, 8번이 행운의 숫자' }
            ]
        };

        // ============================================================
        // 🎨 렌더링 함수들
        // ============================================================
        
        // 사주 명식 렌더링
        function renderSaju(saju) {
            const grid = document.getElementById('sajuGrid');
            ['year', 'month', 'day', 'hour'].forEach(pillar => {
                const div = document.createElement('div');
                div.className = 'saju-pillar';
                div.innerHTML = `
                    <div class="saju-label">${{ year: '년주', month: '월주', day: '일주', hour: '시주' }[pillar]}</div>
                    <div class="saju-hanja">${saju[pillar].cheon}<br>${saju[pillar].ji}</div>
                    <div class="saju-korean">${saju[pillar].cheon} ${saju[pillar].ji}</div>
                `;
                grid.appendChild(div);
            });
        }

        // 핵심 요약 렌더링
        function renderSummary(summary) {
            const grid = document.getElementById('summaryGrid');
            Object.entries(summary).forEach(([key, value]) => {
                const div = document.createElement('div');
                div.className = 'summary-item';
                div.innerHTML = `
                    <h3>${{ yongsin: '용신', character: '성격', wealth: '재물운', caution: '주의사항' }[key]}</h3>
                    <p>${value}</p>
                `;
                grid.appendChild(div);
            });
        }

        // 상세 분석 렌더링
        function renderDetail(detail) {
            const content = document.getElementById('detailContent');
            Object.entries(detail).forEach(([key, value]) => {
                const div = document.createElement('div');
                div.className = 'detail-box';
                div.innerHTML = `
                    <h3 class="detail-title">${{ character: '성격 분석', career: '직업운', wealth: '재물운', health: '건강운' }[key]}</h3>
                    <p class="detail-content">${value}</p>
                `;
                content.appendChild(div);
            });
        }

        // 🆕 월별 운세 그래프 (Rich Style)
        function renderMonthlyFlowChart(monthlyData) {
            const ctx = document.getElementById('monthlyFlowChart').getContext('2d');
            const currentYear = new Date().getFullYear();
            const currentMonth = new Date().getMonth() + 1;
            
            // 데이터 준비
            const labels = monthlyData.map(m => `${m.month}월`);
            const scores = monthlyData.map(m => m.score);
            
            // 포인트 색상 (현재 월 강조)
            const pointColors = monthlyData.map(m => 
                m.month === currentMonth ? '#FF6347' : '#4169E1'
            );
            
            const pointRadius = monthlyData.map(m => 
                m.month === currentMonth ? 8 : 5
            );

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '월별 운세 점수',
                        data: scores,
                        borderColor: '#4169E1',
                        backgroundColor: 'rgba(65, 105, 225, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: pointColors,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: pointRadius,
                        pointHoverRadius: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 16,
                            titleFont: { size: 14, weight: 'bold' },
                            bodyFont: { size: 13 },
                            bodySpacing: 6,
                            callbacks: {
                                title: function(context) {
                                    const idx = context[0].dataIndex;
                                    const month = monthlyData[idx].month;
                                    return `${month}월${month === currentMonth ? ' (현재)' : ''}`;
                                },
                                label: function(context) {
                                    return null; // 기본 라벨 제거
                                },
                                afterLabel: function(context) {
                                    const idx = context.dataIndex;
                                    const data = monthlyData[idx];
                                    
                                    // 운세 등급 판정
                                    let grade = '';
                                    if (data.score >= 80) grade = '🌟 매우 좋음';
                                    else if (data.score >= 70) grade = '😊 좋음';
                                    else if (data.score >= 60) grade = '😐 보통';
                                    else grade = '⚠️ 주의';
                                    
                                    return [
                                        `점수: ${data.score}점 (${grade})`,
                                        `대운: ${data.daewoon}`,
                                        `연운: ${data.yeonwoon}`,
                                        ``,
                                        `💡 ${data.advice}`
                                    ];
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            min: 40,
                            max: 100,
                            ticks: {
                                stepSize: 10,
                                callback: function(value) {
                                    return value + '점';
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    },
                    // 현재 월 세로 점선 추가
                    plugins: [{
                        afterDatasetsDraw: function(chart) {
                            const currentIdx = monthlyData.findIndex(m => m.month === currentMonth);
                            if (currentIdx === -1) return;
                            
                            const ctx = chart.ctx;
                            const xAxis = chart.scales.x;
                            const yAxis = chart.scales.y;
                            const x = xAxis.getPixelForValue(currentIdx);
                            
                            ctx.save();
                            ctx.beginPath();
                            ctx.setLineDash([5, 5]);
                            ctx.moveTo(x, yAxis.top);
                            ctx.lineTo(x, yAxis.bottom);
                            ctx.lineWidth = 2;
                            ctx.strokeStyle = '#FF6347';
                            ctx.stroke();
                            ctx.restore();
                        }
                    }]
                }
            });
        }

        // 개운법 렌더링
        function renderActions(actions) {
            const grid = document.getElementById('guideGrid');
            actions.forEach(action => {
                const div = document.createElement('div');
                div.className = 'guide-item';
                div.innerHTML = `
                    <h4>${action.category}</h4>
                    <p>${action.content}</p>
                `;
                grid.appendChild(div);
            });
        }

        // ============================================================
        // 🚀 초기화
        // ============================================================
        document.addEventListener('DOMContentLoaded', function() {
            renderSaju(MOCK_REPORT_DATA.saju);
            renderSummary(MOCK_REPORT_DATA.summary);
            renderDetail(MOCK_REPORT_DATA.detail);
            renderMonthlyFlowChart(MOCK_REPORT_DATA.monthly);
            renderActions(MOCK_REPORT_DATA.actions);
        });
    </script>
</body>
</html>
"""


# ============================================================
# 📊 무료 리포트 생성 함수 (5개 기본 섹션만)
# ============================================================

def generate_free_report_html(data: Dict) -> str:
    """
    무료 기본 HTML 리포트 생성 (5개 기본 섹션만)
    - 사주 명식
    - 핵심 요약
    - 상세 분석
    - 월별 운세
    - 개운법
    """
    return HTML_TEMPLATE


# ============================================================
# 📊 유료 리포트 생성 함수 (alias)
# ============================================================

def generate_report_html(data: Dict) -> str:
    """
    기본 HTML 리포트 생성 (무료 버전과 동일)
    """
    return generate_free_report_html(data)


# ============================================================
# 🎁 프리미엄 리포트 생성 함수 (STEP 1 신규 6개 섹션 추가)
# ============================================================

def generate_premium_report_html(data: Dict) -> str:
    """
    유료 프리미엄 리포트 생성 (전체 11개 섹션)
    - 기존 섹션 5개 + STEP 1 신규 6개 프리미엄 섹션
    """
    # 1. 기존 리포트 생성
    base_html = generate_free_report_html(data)
    
    # 2. 분석 데이터 추출
    analysis = data.get('analysis', {})
    
    # 신규 프리미엄 섹션 데이터
    wealth_timing = analysis.get('wealth_timing', {})
    weakness_missions = analysis.get('weakness_missions', {})
    psychological_relief = analysis.get('psychological_relief', {})
    relationship_strategy = analysis.get('relationship_strategy', {})
    rest_calendar = analysis.get('rest_calendar', {})
    digital_amulet = analysis.get('digital_amulet', {})
    
    # 🆕 동적 제목 생성 로직
    missing_element = weakness_missions.get('missing_element', '비겁')
    weakness_title = f"{missing_element} 부족 보완 미션"
    
    guilt_pattern = psychological_relief.get('guilt_pattern', '죄책감')
    psychological_title = f"{guilt_pattern} 해소 가이드"
    
    # 3. 프리미엄 섹션 HTML 생성 (디자이너 수정본 스타일 적용)
    premium_sections = f"""
    <!-- ========== 신규 프리미엄 섹션 ========== -->
    
    <div class="card detail-box premium-mint" id="wealth-timing" style="margin-bottom: 15px;">
        <h3 style="color: #0369a1; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.5rem;">💰</span> 재물운 타이밍 관리
        </h3>
        <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 15px;">
            <p style="margin: 10px 0; line-height: 1.8;"><strong style="color: #dc2626;">⚠️ 위험 월:</strong> {', '.join(map(str, wealth_timing.get('risk_months', []))) or '정보 없음'}</p>
            <p style="margin: 10px 0; line-height: 1.8;"><strong style="color: #16a34a;">✨ 기회 월:</strong> {', '.join(map(str, wealth_timing.get('opportunity_months', []))) or '정보 없음'}</p>
            <p style="margin: 10px 0; line-height: 1.8;"><strong>📊 전략:</strong> {wealth_timing.get('strategy', '프리미엄 분석 데이터를 생성 중입니다.')}</p>
        </div>
    </div>
    
    <div class="card detail-box premium-peach" id="weakness-missions" style="margin-bottom: 15px;">
        <h3 style="color: #92400e; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.5rem;">🎯</span> {weakness_title}
        </h3>
        <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 15px;">
            <p style="margin: 10px 0; line-height: 1.8;"><strong>🔍 결핍 요소:</strong> {weakness_missions.get('missing_element', '정보 없음')}</p>
            <h4 style="color: #92400e; margin-top: 20px; margin-bottom: 15px;">📅 월별 미션</h4>
            <ul style="list-style: none; padding: 0;">
                {''.join([f"<li style='padding: 12px; margin: 8px 0; background: #fffbeb; border-left: 3px solid #f59e0b; border-radius: 4px;'><strong>{month}월:</strong> {mission}</li>" for month, mission in weakness_missions.get('monthly_missions', {}).items()]) or '<li style="color: #6b7280;">프리미엄 분석 데이터를 생성 중입니다.</li>'}
            </ul>
        </div>
    </div>
    
    <div class="card detail-box premium-green" id="psychological-relief" style="margin-bottom: 15px;">
        <h3 style="color: #15803d; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.5rem;">💚</span> {psychological_title}
        </h3>
        <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 15px;">
            <p style="margin: 10px 0; line-height: 1.8;"><strong>🔄 패턴:</strong> {psychological_relief.get('guilt_pattern', '정보 없음')}</p>
            <p style="margin: 10px 0; line-height: 1.8;"><strong>💡 재해석:</strong> {psychological_relief.get('reframing', '프리미엄 분석 데이터를 생성 중입니다.')}</p>
            <p style="margin: 10px 0; line-height: 1.8; background: #f0fdf4; padding: 15px; border-radius: 8px; font-style: italic; color: #15803d;"><strong>✨ 긍정 선언:</strong> "{psychological_relief.get('affirmation', '정보 없음')}"</p>
        </div>
    </div>
    
    <div class="card detail-box premium-pink" id="relationship-strategy" style="margin-bottom: 15px;">
        <h3 style="color: #9f1239; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.5rem;">👥</span> 관계 경계 조정 전략
        </h3>
        <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 15px;">
            <p style="margin: 10px 0; line-height: 1.8;"><strong>📌 패턴명:</strong> {relationship_strategy.get('pattern_name', '정보 없음')}</p>
            <p style="margin: 10px 0; line-height: 1.8;"><strong>🛡️ 경계 가이드:</strong> {relationship_strategy.get('boundary_guide', '프리미엄 분석 데이터를 생성 중입니다.')}</p>
            <p style="margin: 10px 0; line-height: 1.8;"><strong>👨‍👩‍👧‍👦 가족 에너지:</strong> {relationship_strategy.get('family_energy', '정보 없음')}</p>
        </div>
    </div>
    
    <div class="card detail-box premium-blue" id="rest-calendar" style="margin-bottom: 15px;">
        <h3 style="color: #3730a3; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.5rem;">🌙</span> 에너지 레벨링 달력
        </h3>
        <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 15px;">
            <p style="margin: 10px 0; line-height: 1.8;"><strong>⚠️ 번아웃 위험 월:</strong> {', '.join(map(str, rest_calendar.get('burnout_months', []))) or '정보 없음'}</p>
            <p style="margin: 10px 0; line-height: 1.8;"><strong>🧘 휴식 활동:</strong> {rest_calendar.get('rest_activities', '프리미엄 분석 데이터를 생성 중입니다.')}</p>
        </div>
    </div>
    
    <div class="card detail-box premium-purple" id="digital-amulet" style="margin-bottom: 15px;">
        <h3 style="color: #6b21a8; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.5rem;">🪬</span> 디지털 부적 카드
        </h3>
        <div style="background: {digital_amulet.get('image_color', '#ffffff')}; padding: 30px; border-radius: 12px; text-align: center; margin-top: 15px;">
            <p style="margin: 15px 0; font-size: 1.1rem;"><strong>🌟 용신 요소:</strong> {digital_amulet.get('yongsin_element', '정보 없음')}</p>
            <p style="font-size: 1.4rem; font-style: italic; margin-top: 20px; font-weight: 500; color: #1f2937;">"{digital_amulet.get('quote', '당신의 운을 응원합니다')}"</p>
        </div>
    </div>
    """
    
    # 4. 삽입 위치 찾기: "상세 분석" 섹션 바로 다음
    insert_marker = '<div id="premium-sections"></div>'
    
    if insert_marker in base_html:
        final_html = base_html.replace(insert_marker, premium_sections)
    else:
        # 마커를 찾지 못한 경우 "개운법" 섹션 직전에 삽입 (폴백)
        fallback_marker = '<div class="card" id="actions">'
        if fallback_marker in base_html:
            final_html = base_html.replace(fallback_marker, premium_sections + fallback_marker)
        else:
            # 최후의 수단: </body> 직전에 삽입
            final_html = base_html.replace("</body>", premium_sections + "</body>")
    
    return final_html


# ============================================================
# 🧪 테스트 실행 코드 (선택 사항)
# ============================================================

if __name__ == "__main__":
    # 테스트 데이터
    test_data = {
        'analysis': {
            'wealth_timing': {
                'risk_months': [3, 7, 11],
                'opportunity_months': [2, 5, 9],
                'strategy': '상반기에는 보수적 투자, 하반기에는 적극적 투자 권장'
            },
            'weakness_missions': {
                'missing_element': '목(木)',
                'monthly_missions': {
                    1: '공원 산책하기',
                    2: '식물 키우기',
                    3: '명상 시작하기'
                }
            },
            'psychological_relief': {
                'guilt_pattern': '완벽주의 죄책감',
                'reframing': '완벽하지 않아도 괜찮습니다',
                'affirmation': '나는 충분히 잘하고 있다'
            },
            'relationship_strategy': {
                'pattern_name': '과도한 책임감 패턴',
                'boundary_guide': '타인의 문제와 내 문제를 분리하세요',
                'family_energy': '부모님과의 적절한 거리 유지'
            },
            'rest_calendar': {
                'burnout_months': [4, 8, 12],
                'rest_activities': '요가, 명상, 온천욕'
            },
            'digital_amulet': {
                'yongsin_element': '목(木)',
                'image_color': '#90EE90',
                'quote': '자연과 함께 성장하라'
            }
        }
    }
    
    # 무료 리포트 생성 테스트
    free_html = generate_free_report_html(test_data)
    with open('free_report_output.html', 'w', encoding='utf-8') as f:
        f.write(free_html)
    print("✅ 무료 리포트 생성 완료: free_report_output.html")
    
    # 프리미엄 리포트 생성 테스트
    premium_html = generate_premium_report_html(test_data)
    with open('premium_report_output.html', 'w', encoding='utf-8') as f:
        f.write(premium_html)
    print("✅ 프리미엄 리포트 생성 완료: premium_report_output.html")
