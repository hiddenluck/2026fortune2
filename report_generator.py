"""
희구소 2026 리포트 생성기
- 글래스피치 (Warm 3D Glassmorphism) 디자인 적용
- Python 데이터를 HTML에 동적으로 주입
- 무료/프리미엄 리포트 생성 함수 제공

[복구된 기능]:
1. 컬러풀한 사주명식 (오행별 색상: 木=녹색, 火=빨강, 土=노랑, 金=흰색, 水=파랑)
2. 십신 클릭 시 설명 표시 (모달 팝업)
3. 나의 스탯 변화 레이더 차트 (radar_chart 데이터 기반)
4. 월별 가이드 (라인 그래프 + 월 버튼 클릭 시 상세 설명)
"""

import json
from typing import Dict, List, Optional
from datetime import datetime


# ============================================================
# 📊 HTML 템플릿 정의 (글래스피치.html - Warm 3D Style + 누락 기능 복구)
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
            --bg-gradient: linear-gradient(135deg, #FFF6E5 0%, #FFD1BC 100%);
            --app-bg: #FFFBF5;
            
            /* Section Gradients */
            --gradient-wealth: linear-gradient(135deg, #FF9966 0%, #FF5E62 100%);
            --gradient-career: linear-gradient(135deg, #F6D365 0%, #FDA085 100%);
            --gradient-love: linear-gradient(135deg, #EE9CA7 0%, #FFDDE1 100%);
            --gradient-change: linear-gradient(135deg, #A18CD1 0%, #FBC2EB 100%);
            --gradient-health: linear-gradient(135deg, #84FAB0 0%, #8FD3F4 100%);
            
            /* 오행 색상 (Five Elements Colors) */
            --color-wood: #4CAF50;    /* 木 - 녹색 */
            --color-fire: #F44336;    /* 火 - 빨강 */
            --color-earth: #FFC107;   /* 土 - 노랑 */
            --color-metal: #9E9E9E;   /* 金 - 흰색/회색 */
            --color-water: #2196F3;   /* 水 - 파랑 */
            
            /* Text Colors */
            --text-dark: #4A3B32;
            --text-gray: #8D7B68;
            --text-white: #FFFFFF;
            --accent-orange: #FF7E5F;
            
            /* Shadows */
            --shadow-card: 8px 8px 20px rgba(166, 142, 133, 0.15), 
                           -8px -8px 20px rgba(255, 255, 255, 1);
            --shadow-float: 0 20px 50px -12px rgba(255, 126, 95, 0.3);
            --shadow-inner: inset 4px 4px 8px rgba(166, 142, 133, 0.1),
                            inset -4px -4px 8px rgba(255, 255, 255, 0.9);
            
            /* Layout */
            --app-width: 480px;
            --nav-height: 60px;
            --radius-lg: 28px;
            --radius-md: 20px;
        }

        /* ==================== Global Layout ==================== */
        body {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            background: #FFE8D6;
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
            background: var(--bg-gradient);
            min-height: 100vh;
            position: relative;
            box-shadow: 0 0 60px rgba(255, 126, 95, 0.15);
            padding: 0 24px 100px 24px;
            overflow-x: hidden;
            z-index: 1;
        }

        /* ==================== 3D Elements ==================== */
        .shape-3d {
            position: absolute;
            border-radius: 50%;
            z-index: -1;
            filter: blur(2px);
            animation: float 6s ease-in-out infinite;
        }

        .shape-1 {
            top: -50px;
            right: -60px;
            width: 200px;
            height: 200px;
            background: radial-gradient(circle at 30% 30%, #FFDAC1, #FF9A9E);
            box-shadow: 20px 20px 60px rgba(255, 154, 158, 0.4);
        }

        .shape-2 {
            top: 120px;
            left: -40px;
            width: 120px;
            height: 120px;
            background: radial-gradient(circle at 30% 30%, #FFF1EB, #F6D365);
            box-shadow: 10px 10px 30px rgba(246, 211, 101, 0.3);
            animation-delay: 1s;
        }

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

        /* ==================== Navigation ==================== */
        .nav-bar {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            width: calc(var(--app-width) - 48px);
            max-width: calc(100% - 48px);
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
            text-shadow: 0 2px 0 rgba(255,255,255,0.5);
        }
        
        .main-title strong {
            position: relative;
            z-index: 1;
        }
        
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

        /* 카드 클릭 시 움직임 제거됨 */

        .section-title {
            font-size: 1.5rem;
            font-weight: 800;
            margin-bottom: 20px;
            color: var(--text-dark);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .section-title i {
            background: linear-gradient(135deg, #FF9966, #FF5E62);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 1.2em;
        }

        /* ==================== 컬러풀한 사주명식 (Colorful Saju Grid) ==================== */
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
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .saju-pillar:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        
        .saju-label {
            font-size: 0.75rem;
            color: var(--text-gray);
            margin-bottom: 8px;
        }
        
        /* 십신 클릭 가능 스타일 */
        .saju-ten-god {
            font-size: 0.85rem;
            color: var(--accent-orange);
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 8px;
            transition: background 0.2s, transform 0.2s;
        }
        
        .saju-ten-god:hover {
            background: rgba(255, 126, 95, 0.15);
            transform: scale(1.05);
        }
        
        .saju-ten-god:active {
            transform: scale(0.95);
        }
        
        /* 오행별 색상이 적용된 한자 */
        .saju-hanja {
            font-size: 2rem;
            font-weight: 800;
            margin: 10px 0;
            transition: transform 0.2s;
        }
        
        .saju-hanja:hover {
            transform: scale(1.1);
        }
        
        /* 오행별 색상 클래스 */
        .element-wood { color: var(--color-wood); text-shadow: 0 2px 4px rgba(76, 175, 80, 0.3); }
        .element-fire { color: var(--color-fire); text-shadow: 0 2px 4px rgba(244, 67, 54, 0.3); }
        .element-earth { color: var(--color-earth); text-shadow: 0 2px 4px rgba(255, 193, 7, 0.3); }
        .element-metal { color: var(--color-metal); text-shadow: 0 2px 4px rgba(158, 158, 158, 0.3); }
        .element-water { color: var(--color-water); text-shadow: 0 2px 4px rgba(33, 150, 243, 0.3); }

        /* ==================== 십신 설명 모달 ==================== */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 2000;
            justify-content: center;
            align-items: center;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .modal-overlay.active {
            display: flex;
            opacity: 1;
        }
        
        .modal-content {
            background: white;
            border-radius: 24px;
            padding: 30px;
            max-width: 350px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            transform: scale(0.9);
            transition: transform 0.3s;
            text-align: center;
        }
        
        .modal-overlay.active .modal-content {
            transform: scale(1);
        }
        
        .modal-title {
            font-size: 1.5rem;
            font-weight: 800;
            color: var(--accent-orange);
            margin-bottom: 15px;
        }
        
        .modal-body {
            color: var(--text-gray);
            line-height: 1.8;
            margin-bottom: 20px;
        }
        
        .modal-close {
            background: var(--gradient-wealth);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 30px;
            font-weight: 700;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .modal-close:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 25px rgba(255, 94, 98, 0.4);
        }

        /* ==================== 나의 스탯 변화 (레이더 차트) ==================== */
        .stat-chart-box {
            height: 280px;
            margin: 20px 0;
            background: #FFFBF5;
            border-radius: 16px;
            padding: 15px;
            position: relative;
        }
        
        .stat-legend {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 15px;
            font-size: 0.85rem;
        }
        
        .stat-legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .stat-legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .stat-legend-dot.current { background: rgba(255, 126, 95, 0.6); }
        .stat-legend-dot.future { background: rgba(255, 94, 98, 1); }

        /* ==================== 월별 운세 차트 + 월 버튼 ==================== */
        .flow-chart-box {
            height: 250px;
            margin: 20px 0;
            background: #FFFBF5;
            border-radius: 16px;
            padding: 15px;
        }

        /* ==================== 대운/세운 섹션 스타일 ==================== */
        .daewoon-timeline {
            display: flex;
            overflow-x: auto;
            gap: 10px;
            padding: 10px 0;
            margin-bottom: 20px;
            scrollbar-width: thin;
        }
        
        .daewoon-item {
            flex-shrink: 0;
            text-align: center;
            padding: 12px 16px;
            background: #FFFBF5;
            border-radius: 16px;
            border: 2px solid #F0E6D8;
            transition: all 0.3s;
            min-width: 70px;
        }
        
        .daewoon-item.current {
            background: linear-gradient(135deg, #B8E0D2 0%, #D6EAF8 100%);
            border-color: #5DADE2;
            box-shadow: 0 4px 15px rgba(93, 173, 226, 0.3);
        }
        
        .daewoon-item .age {
            font-size: 0.75rem;
            color: var(--text-gray);
            margin-bottom: 5px;
        }
        
        .daewoon-item .sipsin {
            font-size: 0.7rem;
            color: var(--accent-orange);
            margin-bottom: 3px;
        }
        
        .daewoon-item .ganji {
            font-size: 1.3rem;
            font-weight: 800;
        }
        
        .daewoon-item .ganji-sub {
            font-size: 0.7rem;
            color: var(--text-gray);
            margin-top: 3px;
        }
        
        /* 대운 진행률 */
        .daewoon-progress-section {
            background: #FFFBF5;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #F0E6D8;
        }
        
        .daewoon-progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .daewoon-progress-title {
            font-weight: 700;
            color: var(--text-dark);
            font-size: 1rem;
        }
        
        .daewoon-progress-link {
            font-size: 0.85rem;
            color: var(--accent-orange);
            text-decoration: none;
        }
        
        .daewoon-progress-bar {
            background: #E0D4C5;
            height: 10px;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 8px;
        }
        
        .daewoon-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #B8E0D2 0%, #5DADE2 100%);
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        
        .daewoon-progress-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: var(--text-gray);
        }
        
        /* 세운 섹션 */
        .sewoon-section {
            margin-top: 20px;
        }
        
        .sewoon-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--accent-orange);
            text-align: center;
            margin-bottom: 15px;
        }
        
        .sewoon-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
        }
        
        .sewoon-item {
            text-align: center;
            padding: 10px 5px;
            background: #FFF;
            border-radius: 12px;
            border: 1px solid #F0E6D8;
            transition: all 0.3s;
        }
        
        .sewoon-item.current-year {
            background: linear-gradient(135deg, #FFD1BC 0%, #FF9966 100%);
            border-color: var(--accent-orange);
            box-shadow: 0 4px 12px rgba(255, 126, 95, 0.3);
        }
        
        .sewoon-item.current-year .year,
        .sewoon-item.current-year .ganji,
        .sewoon-item.current-year .sipsin {
            color: white;
        }
        
        .sewoon-item .year {
            font-size: 0.75rem;
            color: var(--text-gray);
            margin-bottom: 3px;
        }
        
        .sewoon-item .sipsin {
            font-size: 0.65rem;
            color: var(--accent-orange);
            margin-bottom: 2px;
        }
        
        .sewoon-item .ganji {
            font-size: 1rem;
            font-weight: 700;
        }
        
        .sewoon-item .ganji-sipsin {
            font-size: 0.6rem;
            color: var(--text-gray);
            margin-top: 2px;
        }
        
        /* 월별 버튼 그리드 */
        .month-buttons {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
            margin-top: 20px;
        }
        
        .month-btn {
            padding: 10px 5px;
            border: 2px solid #F0E6D8;
            border-radius: 12px;
            background: #FFFBF5;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text-gray);
            transition: all 0.3s;
        }
        
        .month-btn:hover {
            border-color: var(--accent-orange);
            color: var(--accent-orange);
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(255, 126, 95, 0.2);
        }
        
        .month-btn.active {
            background: var(--gradient-wealth);
            color: white;
            border-color: transparent;
            box-shadow: 0 8px 20px rgba(255, 94, 98, 0.3);
        }
        
        /* 월별 상세 설명 박스 */
        .month-detail-box {
            margin-top: 20px;
            background: white;
            border-radius: 16px;
            padding: 20px;
            border: 2px dashed #E0D4C5;
            display: none;
        }
        
        .month-detail-box.active {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .month-detail-title {
            font-size: 1.2rem;
            font-weight: 800;
            color: var(--text-dark);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .month-detail-content {
            display: grid;
            gap: 12px;
        }
        
        .month-detail-item {
            display: flex;
            gap: 10px;
            padding: 12px;
            background: #FFFBF5;
            border-radius: 12px;
        }
        
        .month-detail-item .label {
            font-weight: 700;
            color: var(--accent-orange);
            min-width: 60px;
        }
        
        .month-detail-item .value {
            color: var(--text-gray);
            flex: 1;
        }

        /* ==================== Summary Grid ==================== */
        .summary-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        .summary-box {
            background: #FFF;
            padding: 20px;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-inner);
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

        .summary-box.highlight {
            grid-column: 1 / -1;
            background: var(--gradient-wealth) !important;
            box-shadow: 0 15px 30px rgba(255, 94, 98, 0.3);
            border: none;
            color: white !important;
            position: relative;
            overflow: hidden;
        }
        
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

        /* ==================== Detail Box ==================== */
        .detail-box {
            padding: 0;
            overflow: hidden;
            background: #FFF;
        }

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

        .detail-box.career h3 span { background: var(--gradient-career); box-shadow: 0 8px 16px rgba(253, 160, 133, 0.3); }
        .detail-box.love h3 span { background: var(--gradient-love); box-shadow: 0 8px 16px rgba(255, 221, 225, 0.4); }
        .detail-box.change h3 span { background: var(--gradient-change); box-shadow: 0 8px 16px rgba(161, 140, 209, 0.3); }
        .detail-box.health h3 span { background: var(--gradient-health); box-shadow: 0 8px 16px rgba(132, 250, 176, 0.3); }
        
        .detail-content-wrapper {
            padding: 28px;
        }

        .detail-content {
            font-size: 1rem;
            color: #6D5D50;
            line-height: 1.8;
        }

        .detail-content strong {
            background: linear-gradient(120deg, rgba(255, 218, 121, 0.5) 0%, rgba(255, 218, 121, 0) 100%);
            padding: 0 4px;
        }

        /* ==================== Premium Inner Box ==================== */
        .inner-box {
            background: #FFFBF5;
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
        
        .inner-box li::before {
            content: '';
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--accent-orange);
            flex-shrink: 0;
        }

        /* ==================== Action & Amulet ==================== */
        .key-action-box {
            background: #FFF;
            border: 2px solid var(--accent-orange);
        }
        
        .key-action-box h3 {
            color: var(--accent-orange);
        }

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
            .month-buttons {
                grid-template-columns: repeat(4, 1fr);
            }
        }

    </style>
</head>
<body>

    <!-- 3D 배경 요소 -->
    <div class="container">
        <div class="shape-3d shape-1"></div>
        <div class="shape-3d shape-2"></div>
        <div class="shape-3d shape-3"></div>
        
        <!-- ==================== 헤더 ==================== -->
        <header>
            <span class="brand">HIDDEN LUCK LAB REPORT</span>
            <h1 class="main-title" id="mainTitle">2026년 {DAY_MASTER}일간 {CUSTOMER_NAME} 님,<br><strong>{MAIN_KEYWORD}</strong></h1>
        </header>

        <!-- ==================== 1. 사주 명식 섹션 (컬러풀 + 클릭 가능) ==================== -->
        <section id="saju" class="card no-click">
            <h2 class="section-title"><i class="fas fa-meteor"></i> 나의 에너지 (Energy)</h2>
            <p style="color: var(--text-gray); font-size: 0.9rem; margin-bottom: 15px;">타고난 기질과 흐름을 분석합니다. <span style="color: var(--accent-orange);">십신을 클릭하면 설명을 볼 수 있어요!</span></p>
            
            <div class="saju-grid" id="sajuGrid">
                <!-- JavaScript에서 렌더링 -->
            </div>
        </section>

        <!-- ==================== 인생의 흐름 (대운/세운) ==================== -->
        <section id="life-path" class="card no-click">
            <h2 class="section-title"><i class="fas fa-route"></i> 인생의 흐름 (Life Path)</h2>
            
            <!-- 대운 타임라인 -->
            <div class="daewoon-timeline" id="daewoonTimeline">
                <!-- JavaScript에서 렌더링 -->
            </div>
            
            <!-- 현재 대운 진행률 -->
            <div class="daewoon-progress-section" id="daewoonProgress">
                <!-- JavaScript에서 렌더링 -->
            </div>
            
            <!-- 현재 대운의 세운 흐름 -->
            <div class="sewoon-section">
                <h3 class="sewoon-title" id="sewoonTitle">현재 대운의 세운 흐름</h3>
                <div class="sewoon-grid" id="sewoonGrid">
                    <!-- JavaScript에서 렌더링 -->
                </div>
            </div>
        </section>

        <!-- ==================== 나의 스탯 변화 (레이더 차트) ==================== -->
        <section id="stat-chart" class="card no-click">
            <h2 class="section-title"><i class="fas fa-chart-radar"></i> 나의 스탯 변화</h2>
            <p style="color: var(--text-gray); font-size: 0.9rem; margin-bottom: 10px;">2026년, 당신의 에너지는 어떻게 변화할까요?</p>
            <div class="stat-chart-box">
                <canvas id="radarChart"></canvas>
            </div>
            <div class="stat-legend">
                <div class="stat-legend-item">
                    <div class="stat-legend-dot current"></div>
                    <span>현재</span>
                </div>
                <div class="stat-legend-item">
                    <div class="stat-legend-dot future"></div>
                    <span>2026년</span>
                </div>
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

        <!-- ==================== 월별 운세 차트 + 월별 가이드 ==================== -->
        <section id="monthly-chart" class="card no-click">
            <h2 class="section-title"><i class="fas fa-chart-line"></i> 2026 월별 운세 흐름</h2>
            <div class="flow-chart-box">
                <canvas id="monthlyFlowChart"></canvas>
            </div>
            
            <!-- 월별 버튼 -->
            <div class="month-buttons" id="monthButtons">
                <!-- JavaScript에서 렌더링 -->
            </div>
            
            <!-- 월별 상세 설명 -->
            <div class="month-detail-box" id="monthDetailBox">
                <!-- JavaScript에서 렌더링 -->
            </div>
        </section>

        <!-- ==================== Q&A 섹션 ==================== -->
        <section id="qa" class="card no-click">
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
                <strong style="color:#FFD1BC;">{KEY_MESSAGE_2026}</strong><br><br>
            </p>
        </section>
        
        <!-- 하단 여백 확보 -->
        <div style="height: 100px;"></div>

    </div>

    <!-- ==================== 십신 설명 모달 ==================== -->
    <div class="modal-overlay" id="sipsinModal">
        <div class="modal-content">
            <h3 class="modal-title" id="modalTitle">십신명</h3>
            <p class="modal-body" id="modalBody">설명이 여기에 표시됩니다.</p>
            <button class="modal-close" onclick="closeSipsinModal()">확인</button>
        </div>
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
        // 🎨 오행 -> 색상 매핑
        // ============================================================
        const OHENG_MAP = {
            '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土', 
            '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水', 
            '子': '水', '丑': '土', '寅': '木', '卯': '木', '辰': '土', 
            '巳': '火', '午': '火', '未': '土', '申': '金', '酉': '金', 
            '戌': '土', '亥': '水'
        };
        
        const ELEMENT_CLASS_MAP = {
            '木': 'element-wood',
            '火': 'element-fire',
            '土': 'element-earth',
            '金': 'element-metal',
            '水': 'element-water'
        };
        
        function getElementClass(char) {
            const oheng = OHENG_MAP[char];
            return ELEMENT_CLASS_MAP[oheng] || '';
        }

        // ============================================================
        // 🔮 십신 설명 데이터
        // ============================================================
        const SIPSIN_DESCRIPTIONS = {
            '비견': {
                title: '비견 (比肩)',
                desc: '나와 같은 오행, 같은 음양입니다. 형제, 친구, 동료를 의미하며 독립심과 자존심이 강합니다. 경쟁심이 있고 자기 주관이 뚜렷합니다.'
            },
            '겁재': {
                title: '겁재 (劫財)',
                desc: '나와 같은 오행, 다른 음양입니다. 형제, 친구 중 라이벌 관계를 의미합니다. 승부욕이 강하고 재물에 대한 욕심이 있습니다.'
            },
            '식신': {
                title: '식신 (食神)',
                desc: '내가 생하는 오행, 같은 음양입니다. 먹을 복, 표현력, 창의력을 의미합니다. 여유롭고 낙천적이며 예술적 감각이 있습니다.'
            },
            '상관': {
                title: '상관 (傷官)',
                desc: '내가 생하는 오행, 다른 음양입니다. 예리한 통찰력과 비판력을 의미합니다. 자유로운 영혼이며 기존 질서에 도전합니다.'
            },
            '편재': {
                title: '편재 (偏財)',
                desc: '내가 극하는 오행, 같은 음양입니다. 유동적인 재물, 투자, 사업을 의미합니다. 활동적이고 사교적이며 돈의 흐름이 역동적입니다.'
            },
            '정재': {
                title: '정재 (正財)',
                desc: '내가 극하는 오행, 다른 음양입니다. 안정적인 재물, 월급, 저축을 의미합니다. 성실하고 검소하며 계획적입니다.'
            },
            '편관': {
                title: '편관 (偏官)',
                desc: '나를 극하는 오행, 같은 음양입니다. 도전, 압박, 스트레스를 의미하지만 이를 이겨내면 큰 성취를 이룹니다. 카리스마가 있습니다.'
            },
            '정관': {
                title: '정관 (正官)',
                desc: '나를 극하는 오행, 다른 음양입니다. 명예, 직장, 규율을 의미합니다. 책임감이 강하고 조직 내에서 인정받습니다.'
            },
            '편인': {
                title: '편인 (偏印)',
                desc: '나를 생하는 오행, 같은 음양입니다. 특별한 재능, 학문, 종교, 예술을 의미합니다. 비범한 아이디어와 영감이 있습니다.'
            },
            '정인': {
                title: '정인 (正印)',
                desc: '나를 생하는 오행, 다른 음양입니다. 어머니, 학문, 자격증을 의미합니다. 배움을 좋아하고 인내심이 강합니다.'
            },
            '일원': {
                title: '일원 (日元)',
                desc: '본인 자신을 의미합니다. 일간(日干)과 동일한 것으로, 사주팔자의 중심이 되는 나 자신입니다.'
            }
        };

        // ============================================================
        // 🔮 십신 모달 함수
        // ============================================================
        function showSipsinModal(sipsin) {
            const modal = document.getElementById('sipsinModal');
            const title = document.getElementById('modalTitle');
            const body = document.getElementById('modalBody');
            
            const info = SIPSIN_DESCRIPTIONS[sipsin] || { title: sipsin, desc: '설명 준비 중입니다.' };
            
            title.textContent = info.title;
            body.textContent = info.desc;
            
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
        
        function closeSipsinModal() {
            const modal = document.getElementById('sipsinModal');
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
        
        // 모달 바깥 클릭 시 닫기
        document.getElementById('sipsinModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeSipsinModal();
            }
        });

        // ============================================================
        // 🎨 렌더링 함수들
        // ============================================================
        
        // 대운 타임라인 렌더링
        function renderDaewoonTimeline() {
            const container = document.getElementById('daewoonTimeline');
            if (!container || !REPORT_DATA.saju) return;
            
            const daewoonList = REPORT_DATA.saju.daewoon_list || [];
            const currAge = REPORT_DATA.saju.curr_age || 0;
            const daewoonSipsin = REPORT_DATA.saju.daewoon_sipsin || {};
            
            let html = '';
            daewoonList.forEach(d => {
                const isCurrent = currAge >= d.age && currAge < d.age + 10;
                const sipsinInfo = daewoonSipsin[d.ganji] || {stem: '', branch: ''};
                const stemClass = getElementClass(d.ganji[0]);
                const branchClass = getElementClass(d.ganji[1]);
                
                html += `
                    <div class="daewoon-item ${isCurrent ? 'current' : ''}">
                        <div class="age">${d.age}세</div>
                        <div class="sipsin">${sipsinInfo.stem || ''}</div>
                        <div class="ganji">
                            <span class="${stemClass}">${d.ganji[0] || ''}</span><span class="${branchClass}">${d.ganji[1] || ''}</span>
                        </div>
                        <div class="ganji-sub">${sipsinInfo.branch || ''}</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
            
            // 현재 대운으로 스크롤
            const currentItem = container.querySelector('.daewoon-item.current');
            if (currentItem) {
                setTimeout(() => {
                    currentItem.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                }, 100);
            }
        }
        
        // 대운 진행률 렌더링
        function renderDaewoonProgress() {
            const container = document.getElementById('daewoonProgress');
            if (!container || !REPORT_DATA.saju) return;
            
            const daewoonList = REPORT_DATA.saju.daewoon_list || [];
            const currAge = REPORT_DATA.saju.curr_age || 0;
            const currentDwStartYear = REPORT_DATA.saju.current_dw_start_year || new Date().getFullYear();
            
            // 현재 대운 찾기
            let currentDw = daewoonList[0] || { age: 0, ganji: '--' };
            for (const d of daewoonList) {
                if (currAge >= d.age && currAge < d.age + 10) {
                    currentDw = d;
                    break;
                }
            }
            
            // 진행률 계산 (대운 10년 기준)
            const yearsInDw = currAge - currentDw.age;
            const progressPercent = Math.min(Math.max((yearsInDw / 10) * 100, 0), 100);
            const endYear = currentDwStartYear + 10 - yearsInDw;
            
            const stemClass = getElementClass(currentDw.ganji[0]);
            const branchClass = getElementClass(currentDw.ganji[1]);
            
            container.innerHTML = `
                <p style="text-align:center; margin-bottom:15px; color:var(--text-gray); font-size:0.95rem;">
                    <span class="${stemClass}" style="font-size:1.1rem; font-weight:700;">${currentDw.ganji[0] || ''}</span><span class="${branchClass}" style="font-size:1.1rem; font-weight:700;">${currentDw.ganji[1] || ''}</span> 대운이 ${currentDw.age}세(${currentDwStartYear}년)부터 진행 중입니다.
                </p>
                <div class="daewoon-progress-header">
                    <span class="daewoon-progress-title"><span class="${stemClass}">${currentDw.ganji[0] || ''}</span><span class="${branchClass}">${currentDw.ganji[1] || ''}</span> 대운 (${currentDw.age}세~)</span>
                    <span class="daewoon-progress-link">인생의 여정</span>
                </div>
                <div class="daewoon-progress-bar">
                    <div class="daewoon-progress-fill" style="width: ${progressPercent}%"></div>
                </div>
                <div class="daewoon-progress-info">
                    <span>${currentDwStartYear}년</span>
                    <span>${Math.round(progressPercent)}% 진행</span>
                    <span>${endYear}년 종료</span>
                </div>
            `;
        }
        
        // 세운 그리드 렌더링
        function renderSewoonGrid() {
            const container = document.getElementById('sewoonGrid');
            const titleEl = document.getElementById('sewoonTitle');
            if (!container || !REPORT_DATA.saju) return;
            
            const sewoonGanji = REPORT_DATA.saju.sewoon_ganji || {};
            const sewoonSipsin = REPORT_DATA.saju.sewoon_sipsin_map || {};
            const currentDwStartYear = REPORT_DATA.saju.current_dw_start_year || new Date().getFullYear();
            const currentYear = new Date().getFullYear();
            
            // 세운 연도 범위
            const years = Object.keys(sewoonGanji).map(Number).sort((a, b) => a - b);
            const startYear = years[0] || currentDwStartYear;
            const endYear = years[years.length - 1] || startYear + 9;
            
            // 제목 업데이트
            if (titleEl) {
                titleEl.textContent = `현재 대운의 세운 흐름 (${startYear}~${endYear})`;
            }
            
            let html = '';
            years.forEach(year => {
                const ganji = sewoonGanji[year] || '--';
                const sipsin = sewoonSipsin[year] || { stem: '', branch: '' };
                const isCurrentYear = year === 2026; // 2026년 강조
                const stemClass = getElementClass(ganji[0]);
                const branchClass = getElementClass(ganji[1]);
                
                html += `
                    <div class="sewoon-item ${isCurrentYear ? 'current-year' : ''}">
                        <div class="year">${year}</div>
                        <div class="sipsin">${sipsin.stem || ''}</div>
                        <div class="ganji">
                            <span class="${isCurrentYear ? '' : stemClass}">${ganji[0] || ''}</span><span class="${isCurrentYear ? '' : branchClass}">${ganji[1] || ''}</span>
                        </div>
                        <div class="ganji-sipsin">${sipsin.branch || ''}</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        // 컬러풀한 사주 명식 렌더링 (십신 클릭 가능)
        function renderSaju() {
            const container = document.getElementById('sajuGrid');
            if (!container || !REPORT_DATA.saju) return;
            
            const pillars = REPORT_DATA.saju.pillars || [];
            const tenGods = REPORT_DATA.saju.ten_gods || [];
            const labels = ['년주', '월주', '일주', '시주'];
            
            let html = '';
            pillars.forEach((pillar, idx) => {
                const tenGod = tenGods[idx] || {};
                const stemClass = getElementClass(pillar.stem);
                const branchClass = getElementClass(pillar.branch);
                
                const stemTenGod = tenGod.stem_ten_god || '';
                const branchTenGod = tenGod.branch_ten_god || '';
                
                html += `
                    <div class="saju-pillar">
                        <p class="saju-label">${labels[idx]}</p>
                        <p class="saju-ten-god" onclick="showSipsinModal('${stemTenGod}')" title="클릭하여 설명 보기">${stemTenGod}</p>
                        <p class="saju-hanja ${stemClass}">${pillar.stem || ''}</p>
                        <p class="saju-hanja ${branchClass}">${pillar.branch || ''}</p>
                        <p class="saju-ten-god" onclick="showSipsinModal('${branchTenGod}')" title="클릭하여 설명 보기">${branchTenGod}</p>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }

        // 레이더 차트 렌더링 (나의 스탯 변화)
        function renderRadarChart() {
            const ctx = document.getElementById('radarChart');
            if (!ctx) return;
            
            // REPORT_DATA에서 radar_chart 데이터 가져오기
            const radarData = REPORT_DATA.radar_chart || {
                labels: ['추진력', '수익화', '협상력', '안정성', '리더십'],
                current: [7, 6, 5, 7, 6],
                future: [8, 8, 7, 7, 8]
            };
            
            new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: radarData.labels,
                    datasets: [
                        {
                            label: '현재',
                            data: radarData.current,
                            borderColor: 'rgba(255, 126, 95, 0.6)',
                            backgroundColor: 'rgba(255, 126, 95, 0.15)',
                            borderWidth: 2,
                            pointBackgroundColor: 'rgba(255, 126, 95, 0.8)',
                            pointRadius: 4
                        },
                        {
                            label: '2026년',
                            data: radarData.future,
                            borderColor: 'rgba(255, 94, 98, 1)',
                            backgroundColor: 'rgba(255, 94, 98, 0.25)',
                            borderWidth: 3,
                            pointBackgroundColor: 'rgba(255, 94, 98, 1)',
                            pointRadius: 5
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 10,
                            min: 0,
                            ticks: {
                                stepSize: 2,
                                display: false
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            pointLabels: {
                                font: {
                                    size: 12,
                                    weight: '600'
                                },
                                color: '#8D7B68'
                            }
                        }
                    }
                }
            });
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

        // 월별 버튼 및 상세 설명 렌더링
        function renderMonthlyGuide() {
            const buttonsContainer = document.getElementById('monthButtons');
            const detailBox = document.getElementById('monthDetailBox');
            
            if (!buttonsContainer || !detailBox) return;
            
            const monthlyGuide = REPORT_DATA.monthly_guide || {};
            
            // 월 버튼 생성
            let buttonsHtml = '';
            for (let i = 1; i <= 12; i++) {
                buttonsHtml += `<button class="month-btn" data-month="${i}">${i}월</button>`;
            }
            buttonsContainer.innerHTML = buttonsHtml;
            
            // 버튼 클릭 이벤트
            const buttons = buttonsContainer.querySelectorAll('.month-btn');
            buttons.forEach(btn => {
                btn.addEventListener('click', function() {
                    const month = this.dataset.month;
                    
                    // 활성 버튼 토글
                    buttons.forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    
                    // 상세 내용 표시
                    showMonthDetail(month, monthlyGuide);
                });
            });
        }
        
        function showMonthDetail(month, monthlyGuide) {
            const detailBox = document.getElementById('monthDetailBox');
            const data = monthlyGuide[month] || monthlyGuide[String(month)] || {};
            
            if (!data || Object.keys(data).length === 0) {
                detailBox.innerHTML = `
                    <div class="month-detail-title">📅 ${month}월 가이드</div>
                    <p style="color: var(--text-gray);">이 달의 상세 정보가 아직 준비되지 않았습니다.</p>
                `;
            } else {
                detailBox.innerHTML = `
                    <div class="month-detail-title">📅 ${month}월: ${data.title || '월별 가이드'}</div>
                    <div class="month-detail-content">
                        ${data.wealth ? `<div class="month-detail-item"><span class="label">💰 재물</span><span class="value">${data.wealth}</span></div>` : ''}
                        ${data.career ? `<div class="month-detail-item"><span class="label">💼 직업</span><span class="value">${data.career}</span></div>` : ''}
                        ${data.love ? `<div class="month-detail-item"><span class="label">❤️ 애정</span><span class="value">${data.love}</span></div>` : ''}
                        ${data.focus ? `<div class="month-detail-item"><span class="label">🎯 집중</span><span class="value">${data.focus}</span></div>` : ''}
                        ${data.caution ? `<div class="month-detail-item"><span class="label">⚠️ 주의</span><span class="value">${data.caution}</span></div>` : ''}
                        ${data.action ? `<div class="month-detail-item"><span class="label">✨ 행동</span><span class="value">${data.action}</span></div>` : ''}
                    </div>
                `;
            }
            
            detailBox.classList.add('active');
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
            renderDaewoonTimeline();
            renderDaewoonProgress();
            renderSewoonGrid();
            renderRadarChart();
            renderSummary();
            renderDetails();
            renderMonthlyChart();
            renderMonthlyGuide();
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

            <!-- 2026년 맞춤 개운법 (원국+세운 분석 기반) -->
            <div class="detail-box premium-section" id="personal-luck-boost">
                <h3><span>🌟</span> 2026년 {CUSTOMER_NAME}님만의 개운법</h3>
                <div class="detail-content-wrapper">
                    <div class="inner-box">
                        <p style="margin-bottom:15px; font-weight:600; color:var(--accent-orange);">{LUCK_BOOST_TITLE}</p>
                        <p style="margin-bottom:10px; color:var(--text-gray); line-height:1.7;">{LUCK_BOOST_DESC}</p>
                        <ul>
                            {LUCK_BOOST_ACTIONS}
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
    
    # 월별 가이드 데이터 (NEW - 월 클릭 시 상세 설명)
    monthly_guide = analysis.get('monthly_guide', {})
    
    # 레이더 차트 데이터 (NEW - 나의 스탯 변화)
    radar_chart = analysis.get('radar_chart', {
        'labels': ['추진력', '수익화', '협상력', '안정성', '리더십'],
        'current': [7, 6, 5, 7, 6],
        'future': [8, 8, 7, 7, 8]
    })
    
    # 개운법 데이터
    actions = analysis.get('key_actions', [])
    
    # 대운/세운 데이터 (NEW - 인생의 흐름 섹션용)
    daewoon_list = manse.get('daewoon_list', [])
    curr_age = manse.get('curr_age', 0)
    current_dw_start_year = manse.get('current_dw_start_year', datetime.now().year)
    daewoon_sipsin = manse.get('daewoon_sipsin', {})
    sewoon_ganji = manse.get('sewoon_ganji', {})
    sewoon_sipsin_map = manse.get('sewoon_sipsin_map', {})
    
    return {
        'saju': {
            'pillars': pillars,
            'ten_gods': ten_gods,
            'day_master': manse.get('day_master', ''),
            'customer_name': manse.get('customer_name', '고객'),
            # 대운/세운 데이터 추가
            'daewoon_list': daewoon_list,
            'curr_age': curr_age,
            'current_dw_start_year': current_dw_start_year,
            'daewoon_sipsin': daewoon_sipsin,
            'sewoon_ganji': sewoon_ganji,
            'sewoon_sipsin_map': sewoon_sipsin_map
        },
        'summary': {
            'keyword': summary_card.get('keyword', ''),
            'best_month': summary_card.get('best_month', ''),
            'risk': summary_card.get('risk', ''),
            'action_item': summary_card.get('action_item', '')
        },
        'details': details,
        'monthly_flow': monthly_flow,
        'monthly_guide': monthly_guide,  # NEW
        'radar_chart': radar_chart,      # NEW
        'qa': qa_section,
        'actions': actions
    }


# ============================================================
# 📊 무료 리포트 생성 함수 (5개 기본 섹션)
# ============================================================

def generate_free_report_html(data: Dict) -> str:
    """
    무료 기본 HTML 리포트 생성 (5개 기본 섹션만)
    - 사주 명식 (컬러풀 + 십신 클릭 설명)
    - 나의 스탯 변화 (레이더 차트)
    - 핵심 요약
    - 상세 분석
    - 월별 운세 (그래프 + 월 클릭 상세 설명)
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
    
    # 2026년 핵심 한 문장 (AI가 생성한 key_message 또는 기본값)
    key_message_2026 = analysis.get('key_message_2026', summary_card.get('action_item', '2026년, 당신의 운명이 펼쳐집니다.'))
    
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
    html = html.replace('{KEY_MESSAGE_2026}', key_message_2026)
    
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
    
    # 2026년 맞춤 개운법 (원국+세운 분석 기반)
    manse = data.get('manse', {})
    customer_name = manse.get('customer_name', '고객')
    luck_boost = analysis.get('luck_boost_2026', {})
    
    luck_boost_title = luck_boost.get('title', '올해 당신에게 필요한 에너지를 채우세요')
    luck_boost_desc = luck_boost.get('description', '2026년 병오(丙午)년의 火 에너지와 당신의 원국을 분석한 맞춤 개운법입니다.')
    luck_boost_actions_list = luck_boost.get('actions', [])
    if luck_boost_actions_list:
        luck_boost_actions = ''.join([f'<li>{action}</li>' for action in luck_boost_actions_list])
    else:
        luck_boost_actions = monthly_missions  # 폴백: 기존 monthly_missions 사용
    
    premium_html = premium_html.replace('{CUSTOMER_NAME}', customer_name)
    premium_html = premium_html.replace('{LUCK_BOOST_TITLE}', luck_boost_title)
    premium_html = premium_html.replace('{LUCK_BOOST_DESC}', luck_boost_desc)
    premium_html = premium_html.replace('{LUCK_BOOST_ACTIONS}', luck_boost_actions)
    
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
                'wealth_luck': '<strong>"지출은 곧 투자입니다."</strong><br>현재 재물운은 명예(火)로 인해 지출을 동반합니다.',
                'career_luck': '냉철한 분석력과 판단력이 빛을 발하는 시기입니다.',
                'love_family_luck': '리더십이 과하면 독선이 됩니다.',
                'change_luck': '사업장 확장이나 이사 운이 강합니다.',
                'health_advice': '강한 관살(火)로 인한 스트레스 주의보.'
            },
            'qa_section': {
                'q1': '2026년에 사업 확장을 해도 될까요?',
                'a1': '현재 대운과 세운을 분석한 결과, 2026년은 기반을 다지는 시기입니다.',
                'q2': '재물운이 가장 좋은 월은 언제인가요?',
                'a2': '9월, 11월, 12월이 재물운이 상승하는 시기입니다.'
            },
            'final_message': '논리적인 시스템만이 당신의 추진력을 완성합니다.',
            'monthly_flow': [70, 75, 80, 65, 85, 50, 60, 70, 95, 80, 75, 70],
            # NEW: 레이더 차트 데이터
            'radar_chart': {
                'labels': ['추진력', '수익화', '협상력', '안정성', '리더십'],
                'current': [8, 5, 6, 7, 7],
                'future': [7, 8, 9, 7, 8]
            },
            # NEW: 월별 가이드 데이터
            'monthly_guide': {
                '1': {'title': '새로운 시작', 'wealth': '안정적 흐름', 'career': '계획 수립에 집중', 'love': '소통 강화', 'focus': '목표 설정', 'caution': '과욕 금물', 'action': '연간 계획 작성'},
                '2': {'title': '준비의 시간', 'wealth': '지출 관리', 'career': '역량 강화', 'love': '가족 시간', 'focus': '자기계발', 'caution': '건강 주의', 'action': '건강검진'},
                '3': {'title': '도전의 시기', 'wealth': '투자 검토', 'career': '새 기회 탐색', 'love': '관계 확장', 'focus': '네트워킹', 'caution': '급한 결정', 'action': '인맥 관리'},
                '4': {'title': '성장의 계절', 'wealth': '수입 증가 예상', 'career': '승진/이직 기회', 'love': '로맨스 운 상승', 'focus': '실행력', 'caution': '체력 관리', 'action': '프로젝트 착수'},
                '5': {'title': '열정의 시기', 'wealth': '재물운 최고조', 'career': '리더십 발휘', 'love': '깊은 유대감', 'focus': '집중력', 'caution': '과로 주의', 'action': '중요 결정'},
                '6': {'title': '조정의 시간', 'wealth': '지출 증가', 'career': '방향 재검토', 'love': '갈등 조심', 'focus': '균형', 'caution': '감정 조절', 'action': '휴식 확보'},
                '7': {'title': '재충전', 'wealth': '보합세', 'career': '학습 기회', 'love': '여행 추천', 'focus': '재정비', 'caution': '무리한 계획', 'action': '휴가 계획'},
                '8': {'title': '반등의 시작', 'wealth': '회복세', 'career': '새 프로젝트', 'love': '만남 운', 'focus': '도전정신', 'caution': '급진적 변화', 'action': '새 시작 준비'},
                '9': {'title': '수확의 시기', 'wealth': '최고 재물운', 'career': '성과 인정', 'love': '결실 운', 'focus': '마무리', 'caution': '자만심', 'action': '감사 표현'},
                '10': {'title': '정리의 시간', 'wealth': '안정세 유지', 'career': '평가 시기', 'love': '깊은 대화', 'focus': '성찰', 'caution': '비교 금물', 'action': '피드백 수용'},
                '11': {'title': '도약 준비', 'wealth': '저축 권장', 'career': '내년 계획', 'love': '가족 행사', 'focus': '계획 수립', 'caution': '건강 관리', 'action': '건강검진'},
                '12': {'title': '마무리와 감사', 'wealth': '지출 조절', 'career': '성과 정리', 'love': '감사 전달', 'focus': '회고', 'caution': '과음 주의', 'action': '새해 목표'}
            },
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
                'boundary_guide': '당신의 에너지가 먼저 채워져야 남도 도울 수 있습니다.'
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
