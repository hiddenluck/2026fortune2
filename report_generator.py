"""
희구소 2026 리포트 생성기
- 글래스피치 (Warm 3D Glassmorphism) 디자인 적용
- Python 데이터를 HTML에 동적으로 주입
- 무료/프리미엄 리포트 생성 함수 제공
"""

import json
from typing import Dict, List, Optional
from datetime import datetime


# ============================================================
# 📊 HTML 템플릿 정의 (글래스피치.html - Warm 3D Style)
# ============================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>희구소: 2026 마스터 리포트 (Warm 3D Style)</title>
    
    <!-- 폰트: Pretendard, 고운바탕 -->
    <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css" />
    <link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">
    <!-- 아이콘 -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    
    <style>
        /* ==================== Reset & Variables ==================== */
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        :root {
            /* 🎨 Warm Color Palette (Peach, Coral, Gold) */
            --bg-gradient: linear-gradient(135deg, #FFF6E5 0%, #FFD1BC 100%); /* Cream to Peach */
            --app-bg: #FFFBF5; /* Warm White */
            
            /* Section Gradients (Warm & Vivid) */
            --gradient-wealth: linear-gradient(135deg, #FF9966 0%, #FF5E62 100%);   /* Sunset Orange */
            --gradient-career: linear-gradient(135deg, #F6D365 0%, #FDA085 100%);   /* Mango Gold */
            --gradient-love: linear-gradient(135deg, #EE9CA7 0%, #FFDDE1 100%);     /* Soft Pink */
            --gradient-change: linear-gradient(135deg, #A18CD1 0%, #FBC2EB 100%);   /* Warm Lavender */
            --gradient-health: linear-gradient(135deg, #84FAB0 0%, #8FD3F4 100%);   /* Mint (Fresh accent) */
            
            /* Text Colors */
            --text-dark: #4A3B32; /* Dark Brown (Softer than Black) */
            --text-gray: #8D7B68; /* Warm Gray */
            --text-white: #FFFFFF;
            --accent-orange: #FF7E5F;
            
            /* Shadows (Warm & Clay) */
            --shadow-card: 8px 8px 20px rgba(166, 142, 133, 0.15), 
                           -8px -8px 20px rgba(255, 255, 255, 1);
            --shadow-float: 0 20px 50px -12px rgba(255, 126, 95, 0.3);
            --shadow-inner: inset 4px 4px 8px rgba(166, 142, 133, 0.1),
                            inset -4px -4px 8px rgba(255, 255, 255, 0.9);
            
            /* Layout */
            --app-width: 480px;
            --nav-height: 60px;
            --radius-lg: 28px; /* 더 둥글게 (Clay 느낌) */
            --radius-md: 20px;
        }

        /* ==================== Global Layout ==================== */
        body {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            background: #FFE8D6; /* Desktop Warm Background */
            color: var(--text-dark);
            line-height: 1.6;
            display: flex;
            justify-content: center;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .container {
            width: 100%;
            max-width: var(--app-width);
            background: var(--bg-gradient); /* 전체 배경 그라데이션 */
            min-height: 100vh;
            position: relative;
            box-shadow: 0 0 60px rgba(255, 126, 95, 0.15);
            padding: 0 24px 100px 24px;
            overflow-x: hidden; /* 가로 스크롤 방지 */
            z-index: 1;
        }

        /* ==================== 3D Elements (CSS Objects) ==================== */
        /* 배경에 떠다니는 3D 구체들 */
        .shape-3d {
            position: absolute;
            border-radius: 50%;
            z-index: -1; /* 컨텐츠 뒤로 */
            filter: blur(2px);
            animation: float 6s ease-in-out infinite;
        }

        /* 1. Big Orange Sphere (Top Right) */
        .shape-1 {
            top: -50px;
            right: -60px;
            width: 200px;
            height: 200px;
            background: radial-gradient(circle at 30% 30%, #FFDAC1, #FF9A9E);
            box-shadow: 20px 20px 60px rgba(255, 154, 158, 0.4);
        }

        /* 2. Small Gold Sphere (Top Left) */
        .shape-2 {
            top: 120px;
            left: -40px;
            width: 120px;
            height: 120px;
            background: radial-gradient(circle at 30% 30%, #FFF1EB, #F6D365);
            box-shadow: 10px 10px 30px rgba(246, 211, 101, 0.3);
            animation-delay: 1s;
        }

        /* 3. Purple Blob (Bottom) */
        .shape-3 {
            bottom: 150px;
            right: -20px;
            width: 150px;
            height: 150px;
            background: radial-gradient(circle at 30% 30%, #E0C3FC, #8EC5FC);
            box-shadow: 15px 15px 40px rgba(142, 197, 252, 0.3);
            animation-delay: 2s;
        }

        @keyframes float {
            0% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(5deg); }
            100% { transform: translateY(0px) rotate(0deg); }
        }

        /* ==================== Navigation (Warm Glass) ==================== */
        .nav-bar {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            width: calc(var(--app-width) - 48px);
            max-width: calc(100% - 48px);
            
            /* Warm Glassmorphism */
            background: rgba(255, 255, 255, 0.65);
            backdrop-filter: blur(16px) saturate(180%);
            -webkit-backdrop-filter: blur(16px) saturate(180%);
            
            border-radius: 40px;
            display: flex;
            justify-content: space-between;
            padding: 12px 24px;
            box-shadow: 0 10px 30px rgba(255, 126, 95, 0.2);
            z-index: 1000;
            border: 1px solid rgba(255, 255, 255, 0.8);
        }

        .nav-item {
            text-decoration: none;
            color: var(--text-gray);
            font-size: 0.75rem;
            font-weight: 600;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            padding: 6px 10px;
            border-radius: 16px;
            transition: 0.3s;
        }

        .nav-item:hover, .nav-item.active {
            color: var(--accent-orange);
            background: rgba(255, 126, 95, 0.1);
            transform: translateY(-3px);
        }
        
        .nav-item::before {
            font-family: "Font Awesome 6 Free";
            font-weight: 900;
            font-size: 1.2rem;
            margin-bottom: 2px;
        }
        .nav-item[href="#saju"]::before { content: "\\f007"; }
        .nav-item[href="#summary"]::before { content: "\\f0e7"; }
        .nav-item[href="#details"]::before { content: "\\f080"; }
        .nav-item[href="#premium"]::before { content: "\\f3a5"; }
        .nav-item[href="#actions"]::before { content: "\\f058"; }

        /* ==================== Header ==================== */
        header {
            padding: 60px 0 30px 0;
            position: relative;
            z-index: 2;
        }

        .brand {
            font-size: 0.8rem;
            font-weight: 800;
            color: var(--accent-orange);
            background: rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(5px);
            padding: 8px 16px;
            border-radius: 30px;
            display: inline-block;
            margin-bottom: 20px;
            box-shadow: 0 4px 10px rgba(255, 126, 95, 0.1);
            border: 1px solid rgba(255,255,255,0.8);
        }

        .main-title {
            font-family: 'Gowun Batang', serif;
            font-size: 2rem;
            line-height: 1.35;
            color: var(--text-dark);
            text-shadow: 0 2px 0 rgba(255,255,255,0.5); /* 텍스트 입체감 */
        }
        
        .main-title strong {
            position: relative;
            z-index: 1;
        }
        
        /* 형광펜 효과 (따뜻한 색) */
        .main-title strong::after {
            content: '';
            position: absolute;
            bottom: 2px;
            left: 0;
            width: 100%;
            height: 10px;
            background: rgba(255, 218, 121, 0.6);
            z-index: -1;
            border-radius: 4px;
        }

        /* ==================== Clay Cards ==================== */
        /* 둥글고 두께감 있는 클레이모피즘 스타일 */
        .card, .detail-box, .key-action-box {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(10px);
            border-radius: var(--radius-lg);
            padding: 28px;
            margin-bottom: 28px;
            border: 1px solid rgba(255, 255, 255, 0.9);
            box-shadow: var(--shadow-card);
            position: relative;
            z-index: 2;
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .card:active {
            transform: scale(0.98); /* 눌리는 느낌 */
        }

        .section-title {
            font-size: 1.5rem;
            font-weight: 800;
            margin-bottom: 20px;
            color: var(--text-dark);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* 섹션 아이콘도 Warm Color로 변경 */
        .section-title i {
            background: linear-gradient(135deg, #FF9966, #FF5E62);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 1.2em; /* 아이콘 살짝 키움 */
        }

        /* ==================== Saju Grid (사주 명식) ==================== */
        .saju-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }
        
        .saju-pillar {
            text-align: center;
            background: #FFFBF5;
            border-radius: 20px;
            padding: 20px 10px;
        }
        
        .saju-label {
            font-size: 0.75rem;
            color: var(--text-gray);
            margin-bottom: 8px;
        }
        
        .saju-ten-god {
            font-size: 0.85rem;
            color: var(--accent-orange);
        }
        
        .saju-hanja {
            font-size: 2rem;
            font-weight: 800;
            margin: 10px 0;
        }

        /* ==================== 2. Summary Grid ==================== */
        .summary-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        .summary-box {
            background: #FFF;
            padding: 20px;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-inner); /* 눌린 듯한 효과 */
            border: 1px solid #FFF;
        }

        .summary-box p:first-child {
            font-size: 0.85rem;
            color: var(--text-gray);
            font-weight: 700;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .summary-box p:last-child {
            font-size: 1.2rem;
            font-weight: 800;
            color: var(--text-dark);
        }

        /* Highlighted Summary (Warm Gradient) */
        .summary-box.highlight {
            grid-column: 1 / -1;
            background: var(--gradient-wealth) !important;
            box-shadow: 0 15px 30px rgba(255, 94, 98, 0.3);
            border: none;
            color: white !important;
            position: relative;
            overflow: hidden;
        }
        
        /* 반짝이는 효과 추가 */
        .summary-box.highlight::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 60%);
            opacity: 0.5;
            transform: rotate(30deg);
        }

        /* ==================== 3. Detail Box ==================== */
        .detail-box {
            padding: 0;
            overflow: hidden;
            background: #FFF;
        }

        /* 헤더 디자인: 그라데이션 대신 3D 버튼 느낌 */
        .detail-box h3 {
            padding: 24px;
            font-size: 1.3rem;
            color: var(--text-dark);
            font-weight: 800;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 12px;
            background: #FFF;
            border-bottom: 1px solid #F0F0F0;
        }

        /* 3D Icon Container */
        .detail-box h3 span {
            width: 44px;
            height: 44px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            background: var(--gradient-wealth);
            box-shadow: 0 8px 16px rgba(255, 94, 98, 0.25);
            color: white;
            text-shadow: 0 2px 2px rgba(0,0,0,0.1);
        }

        /* 섹션별 아이콘 배경색 변경 */
        .detail-box.career h3 span { background: var(--gradient-career); box-shadow: 0 8px 16px rgba(253, 160, 133, 0.3); }
        .detail-box.love h3 span { background: var(--gradient-love); box-shadow: 0 8px 16px rgba(255, 221, 225, 0.4); }
        .detail-box.change h3 span { background: var(--gradient-change); box-shadow: 0 8px 16px rgba(161, 140, 209, 0.3); }
        .detail-box.health h3 span { background: var(--gradient-health); box-shadow: 0 8px 16px rgba(132, 250, 176, 0.3); }
        
        .detail-content-wrapper {
            padding: 28px;
        }

        .detail-content {
            font-size: 1rem;
            color: #6D5D50; /* Warm Gray Text */
            line-height: 1.8;
        }

        .detail-content strong {
            background: linear-gradient(120deg, rgba(255, 218, 121, 0.5) 0%, rgba(255, 218, 121, 0) 100%);
            padding: 0 4px;
        }

        /* ==================== 4. Premium Inner Box ==================== */
        .inner-box {
            background: #FFFBF5; /* 아주 연한 베이지 */
            border: 2px dashed #E0D4C5;
            border-radius: 16px;
            padding: 20px;
            box-shadow: none;
        }

        .inner-box li {
            background: #FFF;
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 10px;
            border: 1px solid #F0E6D8;
            box-shadow: 0 4px 10px rgba(166, 142, 133, 0.05);
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 10px;
            list-style: none;
        }
        
        /* 리스트 앞의 컬러 바를 원형 점으로 변경 */
        .inner-box li::before {
            content: '';
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--accent-orange);
            flex-shrink: 0;
        }

        /* ==================== 5. Action & Amulet ==================== */
        .key-action-box {
            background: #FFF;
            border: 2px solid var(--accent-orange);
        }
        
        .key-action-box h3 {
            color: var(--accent-orange);
        }

        /* 부적 카드 (3D 기울기 효과 강화) */
        .amulet-card {
            background: linear-gradient(135deg, #F6D365 0%, #FDA085 100%);
            border-radius: 24px;
            padding: 30px;
            color: white;
            box-shadow: 0 20px 40px rgba(253, 160, 133, 0.4);
            transform: perspective(1000px) rotateX(5deg) rotateY(-5deg);
            transition: transform 0.5s ease;
            text-align: center;
            border: 2px solid rgba(255,255,255,0.3);
        }
        
        .amulet-card:hover {
            transform: perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1.05);
        }

        .final-message-card {
            background: var(--text-dark) !important;
            color: #FFE8D6;
            text-align: center;
            border: none;
            border-radius: var(--radius-lg) !important; 
            box-shadow: 0 20px 50px rgba(74, 59, 50, 0.4);
        }
        
        .final-message-card p {
            font-family: 'Gowun Batang', serif;
            font-size: 1.2rem;
            line-height: 1.6;
        }

        /* ==================== Monthly Flow Chart ==================== */
        .flow-chart-box {
            height: 250px;
            margin: 20px 0;
            background: #FFFBF5;
            border-radius: 16px;
            padding: 15px;
        }

        /* ==================== Q&A Section ==================== */
        .qa-item {
            background: #FFFBF5;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 15px;
        }
        
        .qa-question {
            font-weight: 700;
            color: var(--accent-orange);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .qa-answer {
            color: var(--text-gray);
            line-height: 1.7;
            padding-left: 28px;
        }

        /* ==================== Responsive ==================== */
        @media (max-width: 480px) {
            .saju-grid {
                grid-template-columns: repeat(4, 1fr);
                gap: 8px;
            }
            .saju-pillar {
                padding: 15px 5px;
            }
            .saju-hanja {
                font-size: 1.5rem;
            }
            .summary-grid {
                grid-template-columns: 1fr;
            }
        }

    </style>
</head>
<body>

    <!-- 3D 배경 요소 (둥둥 떠다니는 구체) -->
    <div class="container">
        <div class="shape-3d shape-1"></div>
        <div class="shape-3d shape-2"></div>
        <div class="shape-3d shape-3"></div>
        
        <!-- ==================== 헤더 ==================== -->
        <header>
            <span class="brand">HIDDEN LUCK LAB REPORT</span>
            <h1 class="main-title" id="mainTitle">2026년 {DAY_MASTER}일간 {CUSTOMER_NAME} 님,<br><strong>{MAIN_KEYWORD}</strong></h1>
        </header>

        <!-- ==================== 1. 사주 명식 섹션 ==================== -->
        <section id="saju" class="card">
            <h2 class="section-title"><i class="fas fa-meteor"></i> 나의 에너지 (Energy)</h2>
            <p style="color: var(--text-gray); font-size: 0.9rem; margin-bottom: 15px;">타고난 기질과 흐름을 분석합니다.</p>
            
            <div class="saju-grid" id="sajuGrid">
                <!-- JavaScript에서 렌더링 -->
            </div>
        </section>

        <!-- ==================== 2. 핵심 요약 카드 ==================== -->
        <section id="summary">
            <h2 class="section-title"><i class="fas fa-star"></i> 2026 핵심 요약</h2>
            <div class="summary-grid" id="summaryGrid">
                <!-- JavaScript에서 렌더링 -->
            </div>
        </section>

        <!-- ==================== 3. 상세 분석 섹션 ==================== -->
        <section id="details">
            <h2 class="section-title"><i class="fas fa-layer-group"></i> 상세 분석</h2>
            <div id="detailsContent">
                <!-- JavaScript에서 렌더링 -->
            </div>
        </section>

        <!-- ==================== 월별 운세 차트 ==================== -->
        <section id="monthly-chart" class="card">
            <h2 class="section-title"><i class="fas fa-chart-line"></i> 2026 월별 운세 흐름</h2>
            <div class="flow-chart-box">
                <canvas id="monthlyFlowChart"></canvas>
            </div>
        </section>

        <!-- ==================== Q&A 섹션 ==================== -->
        <section id="qa" class="card">
            <h2 class="section-title"><i class="fas fa-question-circle"></i> 자주 묻는 질문</h2>
            <div id="qaContent">
                <!-- JavaScript에서 렌더링 -->
            </div>
        </section>

        <!-- ==================== 4. 프리미엄 섹션 (동적 삽입 마커) ==================== -->
        <!-- PREMIUM_SECTIONS_MARKER -->

        <!-- ==================== 5. 개운법 섹션 ==================== -->
        <section id="actions">
            <div class="key-action-box">
                <h3>🎯 2026 실속 솔루션</h3>
                <ul class="key-action-list" id="actionsList">
                    <!-- JavaScript에서 렌더링 -->
                </ul>
            </div>
        </section>

        <!-- ==================== 최종 메시지 ==================== -->
        <section class="final-message-card" id="finalMessage">
            <p id="finalMessageText">
                <br>{FINAL_MESSAGE}<br><br>
                <strong style="color:#FFD1BC;">오직 실속과 결과에 집중하세요.</strong><br><br>
            </p>
        </section>
        
        <!-- 하단 여백 확보 -->
        <div style="height: 100px;"></div>

    </div>

    <!-- ==================== Navigation Bar (Floating) ==================== -->
    <nav class="nav-bar">
        <a href="#saju" class="nav-item">원국</a>
        <a href="#summary" class="nav-item">요약</a>
        <a href="#details" class="nav-item active">분석</a>
        <a href="#premium" class="nav-item">심화</a>
        <a href="#actions" class="nav-item">개운</a>
    </nav>

    <script>
        // ============================================================
        // 📊 리포트 데이터 (Python에서 주입됨)
        // ============================================================
        const REPORT_DATA = {REPORT_DATA_JSON};

        // ============================================================
        // 🎨 렌더링 함수들
        // ============================================================
        
        // 사주 명식 렌더링
        function renderSaju() {
            const container = document.getElementById('sajuGrid');
            if (!container || !REPORT_DATA.saju) return;
            
            const pillars = REPORT_DATA.saju.pillars || [];
            const tenGods = REPORT_DATA.saju.ten_gods || [];
            const labels = ['년주', '월주', '일주', '시주'];
            
            let html = '';
            pillars.forEach((pillar, idx) => {
                const tenGod = tenGods[idx] || {};
                html += `
                    <div class="saju-pillar">
                        <p class="saju-label">${labels[idx]}</p>
                        <p class="saju-ten-god">${tenGod.stem_ten_god || ''}</p>
                        <p class="saju-hanja">${pillar.stem || ''}</p>
                        <p class="saju-hanja">${pillar.branch || ''}</p>
                        <p class="saju-ten-god">${tenGod.branch_ten_god || ''}</p>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }

        // 핵심 요약 렌더링
        function renderSummary() {
            const container = document.getElementById('summaryGrid');
            if (!container || !REPORT_DATA.summary) return;
            
            const summary = REPORT_DATA.summary;
            
            let html = `
                <div class="summary-box">
                    <p>🔥 Best Month</p>
                    <p style="color: #FF7E5F;">${summary.best_month || '정보 없음'}</p>
                </div>
                <div class="summary-box">
                    <p>⚠️ 주의할 점</p>
                    <p style="color: #FF9966;">${summary.risk || '정보 없음'}</p>
                </div>
                <div class="summary-box highlight">
                    <div style="display:flex; flex-direction:column; align-items:flex-start; position:relative; z-index:2;">
                        <p style="opacity:0.9; font-weight:400; color:white;">🚀 행동 지침</p>
                        <p style="font-size:1.1rem; color:white;">${summary.action_item || '정보 없음'}</p>
                    </div>
                    <i class="fas fa-arrow-right" style="position:relative; z-index:2; color:white; font-size:1.2rem;"></i>
                </div>
            `;
            
            container.innerHTML = html;
        }

        // 상세 분석 렌더링
        function renderDetails() {
            const container = document.getElementById('detailsContent');
            if (!container || !REPORT_DATA.details) return;
            
            const details = REPORT_DATA.details;
            const sections = [
                { key: 'wealth', icon: '💰', title: '재물운', class: '' },
                { key: 'career', icon: '💼', title: '사업운', class: 'career' },
                { key: 'love', icon: '❤️', title: '애정/가족운', class: 'love' },
                { key: 'change', icon: '🏠', title: '변동운', class: 'change' },
                { key: 'health', icon: '🏥', title: '건강운', class: 'health' }
            ];
            
            let html = '';
            sections.forEach(section => {
                if (details[section.key]) {
                    html += `
                        <div class="detail-box ${section.class}">
                            <h3><span>${section.icon}</span> ${section.title}</h3>
                            <div class="detail-content-wrapper">
                                <p class="detail-content">${details[section.key]}</p>
                            </div>
                        </div>
                    `;
                }
            });
            
            container.innerHTML = html;
        }

        // 월별 운세 차트 렌더링
        function renderMonthlyChart() {
            const ctx = document.getElementById('monthlyFlowChart');
            if (!ctx || !REPORT_DATA.monthly_flow) return;
            
            const monthlyFlow = REPORT_DATA.monthly_flow;
            const labels = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '월별 운세',
                        data: monthlyFlow,
                        borderColor: '#FF7E5F',
                        backgroundColor: 'rgba(255, 126, 95, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#FF7E5F',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(74, 59, 50, 0.9)',
                            padding: 12,
                            titleFont: { size: 14, weight: 'bold' },
                            bodyFont: { size: 13 },
                            callbacks: {
                                label: function(context) {
                                    const score = context.raw;
                                    let grade = '';
                                    if (score >= 85) grade = '🌟 매우 좋음';
                                    else if (score >= 70) grade = '😊 좋음';
                                    else if (score >= 55) grade = '😐 보통';
                                    else grade = '⚠️ 주의';
                                    return `점수: ${score}점 (${grade})`;
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
                    }
                }
            });
        }

        // Q&A 섹션 렌더링
        function renderQA() {
            const container = document.getElementById('qaContent');
            if (!container || !REPORT_DATA.qa) return;
            
            const qa = REPORT_DATA.qa;
            let html = '';
            
            if (qa.q1 && qa.a1) {
                html += `
                    <div class="qa-item">
                        <p class="qa-question"><i class="fas fa-question"></i> ${qa.q1}</p>
                        <p class="qa-answer">${qa.a1}</p>
                    </div>
                `;
            }
            
            if (qa.q2 && qa.a2) {
                html += `
                    <div class="qa-item">
                        <p class="qa-question"><i class="fas fa-question"></i> ${qa.q2}</p>
                        <p class="qa-answer">${qa.a2}</p>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }

        // 개운법 렌더링
        function renderActions() {
            const container = document.getElementById('actionsList');
            if (!container || !REPORT_DATA.actions) return;
            
            let html = '';
            REPORT_DATA.actions.forEach(action => {
                html += `
                    <li style="display:flex; gap:10px; margin-bottom:15px;">
                        <span>✨</span>
                        <span>${action}</span>
                    </li>
                `;
            });
            
            container.innerHTML = html;
        }

        // ============================================================
        // 🚀 초기화
        // ============================================================
        document.addEventListener('DOMContentLoaded', function() {
            renderSaju();
            renderSummary();
            renderDetails();
            renderMonthlyChart();
            renderQA();
            renderActions();
            
            // 네비게이션 활성화
            document.querySelectorAll('.nav-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                    this.classList.add('active');
                });
            });
        });
    </script>
</body>
</html>"""


# ============================================================
# 📊 프리미엄 섹션 HTML 템플릿
# ============================================================

PREMIUM_SECTIONS_TEMPLATE = """
        <!-- ==================== 4. 프리미엄 섹션 ==================== -->
        <section id="premium">
            <h2 class="section-title"><i class="fas fa-crown" style="color: #F6D365;"></i> 프리미엄 가이드</h2>
            
            <!-- 재물운 타이밍 관리 -->
            <div class="detail-box premium-section" id="wealth-timing">
                <h3><span>📅</span> 재물운 타이밍</h3>
                <div class="detail-content-wrapper">
                    <div class="inner-box">
                        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                            <span style="color:#e53e3e; font-weight:700;">📉 위험: {RISK_MONTHS}</span>
                            <span style="color:#38a169; font-weight:700;">📈 기회: {OPPORTUNITY_MONTHS}</span>
                        </div>
                        <p style="font-size:0.9rem; color:var(--text-gray);">{WEALTH_STRATEGY}</p>
                    </div>
                </div>
            </div>

            <!-- 비겁 부족 보완 미션 -->
            <div class="detail-box premium-section" id="weakness-missions">
                <h3><span>🌳</span> {MISSING_ELEMENT} 부족 보완</h3>
                <div class="detail-content-wrapper">
                    <div class="inner-box">
                        <p style="margin-bottom:10px; font-weight:600;">결핍 요소: {MISSING_ELEMENT_DESC}</p>
                        <ul>
                            {MONTHLY_MISSIONS}
                        </ul>
                    </div>
                </div>
            </div>

            <!-- 죄책감 해소 가이드 -->
            <div class="detail-box premium-section" id="psychological-relief">
                <h3><span>🧘</span> 마인드 셋업</h3>
                <div class="detail-content-wrapper">
                    <div class="inner-box">
                        <p><strong>{GUILT_PATTERN}</strong><br>{REFRAMING}</p>
                        <div style="background:#FFF0E6; padding:15px; border-radius:12px; margin-top:10px; color:#D97706; font-weight:700; text-align:center; border:1px solid #FFD1BC;">
                            "{AFFIRMATION}"
                        </div>
                    </div>
                </div>
            </div>

            <!-- 관계 경계 조정 전략 -->
            <div class="detail-box premium-section" id="relationship-strategy">
                <h3><span>🛡️</span> 관계 가이드</h3>
                <div class="detail-content-wrapper">
                    <div class="inner-box">
                        <p><strong>[{PATTERN_NAME}]</strong><br>{BOUNDARY_GUIDE}</p>
                    </div>
                </div>
            </div>

            <!-- 에너지 레벨링 달력 -->
            <div class="detail-box premium-section" id="rest-calendar">
                <h3><span>⚡</span> 에너지 달력</h3>
                <div class="detail-content-wrapper">
                    <div class="inner-box">
                        <p><strong>⚠️ 번아웃 주의:</strong> {BURNOUT_MONTHS}</p>
                        <p style="font-size:0.9rem; margin-top:5px; color:#8D7B68;">{REST_ACTIVITIES}</p>
                    </div>
                </div>
            </div>

            <!-- 디지털 부적 카드 -->
            <div class="detail-box premium-section" id="digital-amulet">
                <h3><span>🪬</span> 디지털 부적</h3>
                <div class="detail-content-wrapper" style="padding-bottom:40px;">
                    <div class="amulet-card" style="background: linear-gradient(135deg, {AMULET_COLOR} 0%, #FDA085 100%);">
                        <div style="display:flex; justify-content:space-between; align-items:center; opacity:0.8;">
                            <span style="font-size:0.8rem; letter-spacing:1px;">LUCKY CHARM</span>
                            <i class="fas fa-gem"></i>
                        </div>
                        <p style="margin: 25px 0; font-size: 1.3rem; font-weight:800; text-shadow:0 2px 5px rgba(0,0,0,0.1);">
                            용신 요소: {YONGSIN_ELEMENT}
                        </p>
                        <p style="font-family: 'Gowun Batang', serif; font-size: 1.2rem; opacity:0.95;">
                            "{AMULET_QUOTE}"
                        </p>
                    </div>
                </div>
            </div>

        </section>
"""


# ============================================================
# 🔧 헬퍼 함수들
# ============================================================

def _format_monthly_missions(missions: Dict) -> str:
    """월별 미션을 HTML 리스트 아이템으로 변환"""
    if not missions:
        return '<li>프리미엄 분석 데이터를 생성 중입니다.</li>'
    
    html = ''
    for month, mission in missions.items():
        html += f'<li><strong>{month}월:</strong> {mission}</li>'
    return html


def _extract_report_data(data: Dict) -> Dict:
    """Python 데이터에서 JavaScript용 데이터 추출"""
    manse = data.get('manse', {})
    analysis = data.get('analysis', {})
    
    # 사주 데이터
    pillars = manse.get('pillars', [])
    ten_gods = manse.get('ten_gods_result', [])
    
    # 요약 카드 데이터
    summary_card = analysis.get('summary_card', {})
    
    # 상세 분석 데이터
    detailed = analysis.get('detailed_analysis', {})
    customer = analysis.get('customer_analysis', {})
    
    # 상세 분석 - 전문가/고객 분석 선택 (customer가 있으면 customer 사용)
    details = {
        'wealth': customer.get('wealth_luck') or detailed.get('wealth_luck', ''),
        'career': customer.get('career_luck') or detailed.get('career_luck', ''),
        'love': customer.get('love_family_luck') or detailed.get('love_family_luck', ''),
        'change': customer.get('change_luck') or detailed.get('change_luck', ''),
        'health': customer.get('health_advice') or detailed.get('health_advice', '')
    }
    
    # Q&A 데이터
    qa_section = analysis.get('qa_section', {})
    
    # 월별 운세 데이터
    monthly_flow = analysis.get('monthly_flow', [70, 75, 80, 65, 85, 50, 60, 70, 95, 80, 75, 70])
    
    # 개운법 데이터
    actions = analysis.get('key_actions', [])
    
    return {
        'saju': {
            'pillars': pillars,
            'ten_gods': ten_gods,
            'day_master': manse.get('day_master', ''),
            'customer_name': manse.get('customer_name', '고객')
        },
        'summary': {
            'keyword': summary_card.get('keyword', ''),
            'best_month': summary_card.get('best_month', ''),
            'risk': summary_card.get('risk', ''),
            'action_item': summary_card.get('action_item', '')
        },
        'details': details,
        'monthly_flow': monthly_flow,
        'qa': qa_section,
        'actions': actions
    }


# ============================================================
# 📊 무료 리포트 생성 함수 (5개 기본 섹션)
# ============================================================

def generate_free_report_html(data: Dict) -> str:
    """
    무료 기본 HTML 리포트 생성 (5개 기본 섹션만)
    - 사주 명식
    - 핵심 요약
    - 상세 분석
    - 월별 운세
    - 개운법
    
    Args:
        data: report_package_data (manse + analysis)
    
    Returns:
        완성된 HTML 문자열
    """
    # 1. 데이터 추출
    manse = data.get('manse', {})
    analysis = data.get('analysis', {})
    
    # 2. 헤더 정보
    day_master = manse.get('day_master', '甲')
    customer_name = manse.get('customer_name', '고객')
    summary_card = analysis.get('summary_card', {})
    main_keyword = summary_card.get('keyword', '당신의 2026년')
    final_message = analysis.get('final_message', '논리적인 시스템만이 당신의 추진력을 완성합니다.')
    
    # 3. JavaScript용 데이터 추출 및 JSON 변환
    report_data = _extract_report_data(data)
    report_data_json = json.dumps(report_data, ensure_ascii=False, indent=2)
    
    # 4. HTML 템플릿에 데이터 주입
    html = HTML_TEMPLATE
    
    # 헤더 텍스트 치환
    html = html.replace('{DAY_MASTER}', day_master)
    html = html.replace('{CUSTOMER_NAME}', customer_name)
    html = html.replace('{MAIN_KEYWORD}', main_keyword)
    html = html.replace('{FINAL_MESSAGE}', final_message)
    
    # JavaScript 데이터 주입
    html = html.replace('{REPORT_DATA_JSON}', report_data_json)
    
    # 프리미엄 섹션 마커 제거 (무료 버전)
    html = html.replace('<!-- PREMIUM_SECTIONS_MARKER -->', '')
    
    return html


# ============================================================
# 📊 유료 리포트 생성 함수 (alias)
# ============================================================

def generate_report_html(data: Dict) -> str:
    """
    기본 HTML 리포트 생성 (무료 버전과 동일)
    """
    return generate_free_report_html(data)


# ============================================================
# 🎁 프리미엄 리포트 생성 함수 (11개 전체 섹션)
# ============================================================

def generate_premium_report_html(data: Dict) -> str:
    """
    유료 프리미엄 리포트 생성 (전체 11개 섹션)
    - 기존 섹션 5개 + STEP 1 신규 6개 프리미엄 섹션
    
    프리미엄 섹션:
    1. 재물운 타이밍 관리
    2. 비겁 부족 보완 미션
    3. 죄책감 해소 가이드
    4. 관계 경계 조정 전략
    5. 에너지 레벨링 달력
    6. 디지털 부적 카드
    
    Args:
        data: report_package_data (manse + analysis)
    
    Returns:
        완성된 HTML 문자열
    """
    # 1. 기존 무료 리포트 생성
    base_html = generate_free_report_html(data)
    
    # 2. 프리미엄 섹션 데이터 추출
    analysis = data.get('analysis', {})
    
    wealth_timing = analysis.get('wealth_timing', {})
    weakness = analysis.get('weakness_missions', {})
    psychological = analysis.get('psychological_relief', {})
    relationship = analysis.get('relationship_strategy', {})
    rest = analysis.get('rest_calendar', {})
    amulet = analysis.get('digital_amulet', {})
    
    # 3. 프리미엄 섹션 데이터 포맷팅
    risk_months = ', '.join(map(str, wealth_timing.get('risk_months', []))) + '월' if wealth_timing.get('risk_months') else '정보 없음'
    opportunity_months = ', '.join(map(str, wealth_timing.get('opportunity_months', []))) + '월' if wealth_timing.get('opportunity_months') else '정보 없음'
    burnout_months = ', '.join(map(str, rest.get('burnout_months', []))) + '월' if rest.get('burnout_months') else '정보 없음'
    monthly_missions = _format_monthly_missions(weakness.get('monthly_missions', {}))
    
    # 4. 프리미엄 섹션 HTML 생성
    premium_html = PREMIUM_SECTIONS_TEMPLATE
    
    # 재물운 타이밍
    premium_html = premium_html.replace('{RISK_MONTHS}', risk_months)
    premium_html = premium_html.replace('{OPPORTUNITY_MONTHS}', opportunity_months)
    premium_html = premium_html.replace('{WEALTH_STRATEGY}', wealth_timing.get('strategy', '프리미엄 분석 데이터를 생성 중입니다.'))
    
    # 비겁 부족 보완
    missing_element = weakness.get('missing_element', '비겁')
    premium_html = premium_html.replace('{MISSING_ELEMENT}', missing_element)
    premium_html = premium_html.replace('{MISSING_ELEMENT_DESC}', f'{missing_element} (창의력과 유연성)')
    premium_html = premium_html.replace('{MONTHLY_MISSIONS}', monthly_missions)
    
    # 심리 해소
    premium_html = premium_html.replace('{GUILT_PATTERN}', psychological.get('guilt_pattern', '패턴 분석 중'))
    premium_html = premium_html.replace('{REFRAMING}', psychological.get('reframing', ''))
    premium_html = premium_html.replace('{AFFIRMATION}', psychological.get('affirmation', '당신은 충분히 잘하고 있습니다'))
    
    # 관계 전략
    premium_html = premium_html.replace('{PATTERN_NAME}', relationship.get('pattern_name', '관계 패턴'))
    premium_html = premium_html.replace('{BOUNDARY_GUIDE}', relationship.get('boundary_guide', ''))
    
    # 에너지 달력
    premium_html = premium_html.replace('{BURNOUT_MONTHS}', burnout_months)
    premium_html = premium_html.replace('{REST_ACTIVITIES}', rest.get('rest_activities', '휴식이 필요합니다'))
    
    # 디지털 부적
    premium_html = premium_html.replace('{AMULET_COLOR}', amulet.get('image_color', '#F6D365'))
    premium_html = premium_html.replace('{YONGSIN_ELEMENT}', amulet.get('yongsin_element', '정보 없음'))
    premium_html = premium_html.replace('{AMULET_QUOTE}', amulet.get('quote', '당신의 운을 응원합니다'))
    
    # 5. 프리미엄 섹션 삽입
    # 마커 위치에 프리미엄 섹션 삽입
    if '<!-- PREMIUM_SECTIONS_MARKER -->' in base_html:
        final_html = base_html.replace('<!-- PREMIUM_SECTIONS_MARKER -->', premium_html)
    else:
        # 폴백: 개운법 섹션 바로 앞에 삽입
        actions_marker = '<section id="actions">'
        if actions_marker in base_html:
            final_html = base_html.replace(actions_marker, premium_html + '\n        ' + actions_marker)
        else:
            # 최후의 수단: </body> 직전에 삽입
            final_html = base_html.replace("</body>", premium_html + "\n</body>")
    
    return final_html


# ============================================================
# 🧪 테스트 실행 코드
# ============================================================

if __name__ == "__main__":
    # 테스트 데이터 (app.py에서 전달되는 형식)
    test_data = {
        'manse': {
            'pillars': [
                {'stem': '甲', 'branch': '子'},  # 년주
                {'stem': '乙', 'branch': '丑'},  # 월주
                {'stem': '丙', 'branch': '寅'},  # 일주
                {'stem': '丁', 'branch': '卯'}   # 시주
            ],
            'ten_gods_result': [
                {'stem_ten_god': '편인', 'branch_ten_god': '정재'},  # 년주 십성
                {'stem_ten_god': '정인', 'branch_ten_god': '편재'},  # 월주 십성
                {'stem_ten_god': '비견', 'branch_ten_god': '식신'},  # 일주 십성
                {'stem_ten_god': '겁재', 'branch_ten_god': '상관'}   # 시주 십성
            ],
            'day_master': '丙',
            'customer_name': '홍길동',
            'curr_age': 41
        },
        'analysis': {
            'summary_card': {
                'keyword': '2026년 화(火) 기운으로 명예운 상승',
                'best_month': '양력 9월',
                'risk': '과도한 자신감으로 인한 충동적 결정',
                'action_item': '수익 모델 구조화 및 브랜드 IP 확보'
            },
            'detailed_analysis': {
                'wealth_luck': '<strong>"지출은 곧 투자입니다."</strong><br>현재 재물운은 명예(火)로 인해 지출을 동반합니다. 돈을 벌기보다 명예와 기반을 다지는 투자에 집중하는 것이 실속을 챙기는 길입니다.',
                'career_luck': '냉철한 분석력과 판단력이 빛을 발하는 시기입니다. 조직 내 갈등이나 압박이 예상되니, <strong>꼼꼼한 문서 처리</strong>가 생명입니다.',
                'love_family_luck': '리더십이 과하면 독선이 됩니다. 가정에서는 "결과"가 아닌 "과정"을 존중하는 부드러움을 보여주세요.',
                'change_luck': '사업장 확장이나 이사 운이 강합니다. 모든 계약 과정에서 전문가의 조언을 반드시 구하세요.',
                'health_advice': '강한 관살(火)로 인한 스트레스 주의보. 심혈관 및 호흡기를 체크하세요.<br><br>운동은 선택이 아니라 생존을 위한 필수 루틴입니다.'
            },
            'qa_section': {
                'q1': '2026년에 사업 확장을 해도 될까요?',
                'a1': '현재 대운과 세운을 분석한 결과, 2026년은 기반을 다지는 시기입니다. 과도한 확장보다는 내실을 다지는 것이 좋습니다.',
                'q2': '재물운이 가장 좋은 월은 언제인가요?',
                'a2': '9월, 11월, 12월이 재물운이 상승하는 시기입니다. 특히 9월에는 적극적인 투자를 고려해보세요.'
            },
            'final_message': '논리적인 시스템만이 당신의 추진력을 완성합니다.',
            'monthly_flow': [70, 75, 80, 65, 85, 50, 60, 70, 95, 80, 75, 70],
            'key_actions': [
                '분산된 아이디어를 <strong>"수익화 파이프라인"</strong> 하나로 모으는 데 80%의 시간을 쓰세요.',
                '단기 수익보다 브랜딩, IP 확보에 필요한 <strong>"실속 지출"</strong>만 허용하세요.',
                '가정에서는 논리가 아닌 <strong>공감</strong>의 언어를 사용하세요.'
            ],
            # 프리미엄 섹션
            'wealth_timing': {
                'risk_months': [6, 7, 10],
                'opportunity_months': [9, 11, 12],
                'strategy': '위험 월에는 지갑을 닫고, 기회 월에 과감히 투자하십시오.'
            },
            'weakness_missions': {
                'missing_element': '목(木)',
                'monthly_missions': {
                    '1': '새로운 시작 계획하기',
                    '2': '낯선 창의적 활동 시도',
                    '3': '숲이나 공원 산책하기'
                }
            },
            'psychological_relief': {
                'guilt_pattern': '완벽주의는 성장의 적입니다.',
                'reframing': '실수는 데이터 수집 과정일 뿐입니다.',
                'affirmation': '나는 성장하는 중이며, 모든 경험은 나를 완성시킨다.'
            },
            'relationship_strategy': {
                'pattern_name': '과도한 희생 금지',
                'boundary_guide': '당신의 에너지가 먼저 채워져야 남도 도울 수 있습니다. 건강한 이기주의가 필요합니다.'
            },
            'rest_calendar': {
                'burnout_months': [4, 8, 12],
                'rest_activities': '이 시기에는 의식적으로 업무량을 70%로 줄이세요.'
            },
            'digital_amulet': {
                'yongsin_element': '토(土)',
                'quote': '안정된 마음이 당신의 가장 큰 자산입니다',
                'image_color': '#F6D365'
            }
        }
    }
    
    # 무료 리포트 생성 테스트
    free_html = generate_free_report_html(test_data)
    with open('test_free_report.html', 'w', encoding='utf-8') as f:
        f.write(free_html)
    print("✅ 무료 리포트 생성 완료: test_free_report.html")
    
    # 프리미엄 리포트 생성 테스트
    premium_html = generate_premium_report_html(test_data)
    with open('test_premium_report.html', 'w', encoding='utf-8') as f:
        f.write(premium_html)
    print("✅ 프리미엄 리포트 생성 완료: test_premium_report.html")
