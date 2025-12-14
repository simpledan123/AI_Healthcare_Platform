# app/services/rehabilitation_ai.py

import json
import os
from typing import List, Dict
from anthropic import Anthropic

# Claude API 클라이언트 초기화
client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", "your-api-key-here")
)


class RehabilitationAI:
    """AI 기반 운동 추천 엔진 (정규화 버전)"""
    
    # 부위별 기본 정보
    PAIN_AREA_INFO = {
        "손목": "컴퓨터 작업, 스마트폰 사용",
        "어깨": "잘못된 자세, 장시간 앉아있기",
        "허리": "구부정한 자세, 무거운 물건 들기",
        "무릎": "계단 오르내리기, 쪼그려 앉기",
        "목": "거북목 자세, 베개 높이",
        "발목": "발목 접질림, 하이힐 착용"
    }
    
    @staticmethod
    def generate_recommendation(
        pain_area: str,
        pain_description: str,
        severity: int
    ) -> Dict:
        """
        AI 기반 운동 추천
        
        정규화된 구조에 맞게 exercises를 리스트로 반환
        (DB 저장은 API 레이어에서 처리)
        """
        
        # 컨텍스트 정보
        context = RehabilitationAI.PAIN_AREA_INFO.get(
            pain_area, 
            "일반적인 근육 통증"
        )
        
        # 프롬프트 구성
        prompt = f"""
다음 정보를 바탕으로 스트레칭 및 운동을 추천해주세요.

**상황:**
- 부위: {pain_area}
- 주요 원인: {context}
- 설명: {pain_description if pain_description else "특별한 설명 없음"}
- 불편함 정도: {severity}/10

**중요 안내:**
- 이것은 의료 조언이 아닙니다
- 심한 통증이나 부상이 의심되면 반드시 의료 전문가와 상담하세요

**요구사항:**
1. 해당 부위에 도움이 될 수 있는 3-5가지 스트레칭/운동을 추천하세요
2. 각 운동은 다음 정보를 포함:
   - 운동 이름
   - 실행 방법 (간단 명료하게, 줄바꿈 \\n 사용)
   - 권장 세트/횟수 또는 유지 시간
   - 주의사항 (배열)
   - 난이도 (쉬움/보통/어려움)
   - YouTube 검색 키워드 (한글 + 영어)
3. 통증 강도({severity}/10)를 고려한 일반적인 조언

**출력 형식 (JSON만 출력):**
{{
  "exercises": [
    {{
      "name": "운동 이름",
      "description": "1. 자세 설명\\n2. 동작 설명\\n3. 호흡 및 팁",
      "sets": 3,
      "reps": 10,
      "duration_seconds": 15,
      "cautions": ["주의사항 1", "주의사항 2"],
      "difficulty": "쉬움",
      "youtube_keywords": ["손목 스트레칭", "wrist stretch"]
    }}
  ],
  "general_advice": "일반적인 조언",
  "estimated_duration_minutes": 10
}}

**반드시 유효한 JSON만 출력하세요. 마크다운(```)은 사용하지 마세요.**
"""

        try:
            # Claude API 호출
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 응답 파싱
            response_text = message.content[0].text.strip()
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            recommendation = json.loads(response_text)
            
            # 메타데이터 추가
            recommendation["pain_area"] = pain_area
            recommendation["severity"] = severity
            
            # 각 운동에 유튜브 검색 URL 생성
            for exercise in recommendation["exercises"]:
                if "youtube_keywords" in exercise and len(exercise["youtube_keywords"]) > 0:
                    primary_keyword = exercise["youtube_keywords"][0]
                    search_url = f"https://www.youtube.com/results?search_query={primary_keyword.replace(' ', '+')}"
                    exercise["youtube_search_url"] = search_url
                else:
                    exercise["youtube_search_url"] = None
            
            return recommendation
            
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return RehabilitationAI._get_fallback_recommendation(pain_area, severity)
            
        except Exception as e:
            print(f"AI 추천 생성 오류: {e}")
            return RehabilitationAI._get_fallback_recommendation(pain_area, severity)
    
    @staticmethod
    def _get_fallback_recommendation(pain_area: str, severity: int) -> Dict:
        """API 실패 시 기본 추천"""
        return {
            "pain_area": pain_area,
            "severity": severity,
            "exercises": [
                {
                    "name": f"{pain_area} 기본 스트레칭",
                    "description": "1. 편안한 자세로 시작하세요\n2. 천천히 해당 부위를 움직이세요\n3. 15초간 유지하세요",
                    "sets": 3,
                    "reps": 10,
                    "duration_seconds": 15,
                    "cautions": [
                        "통증이 심해지면 즉시 중단하세요",
                        "무리하지 말고 천천히 진행하세요"
                    ],
                    "difficulty": "쉬움",
                    "youtube_keywords": [f"{pain_area} 스트레칭", f"{pain_area} stretch"],
                    "youtube_search_url": f"https://www.youtube.com/results?search_query={pain_area}+스트레칭"
                }
            ],
            "general_advice": "하루 2-3회 반복하며, 증상이 지속되면 전문가와 상담하세요.",
            "estimated_duration_minutes": 10
        }
