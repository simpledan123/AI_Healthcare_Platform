# app/services/rehabilitation_ai.py

import json
import os
from typing import List, Dict
from anthropic import Anthropic

# Claude API 클라이언트 초기화
# API 키는 환경변수에서 가져오거나, 개발 환경에서는 직접 설정
client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", "your-api-key-here")
)


class RehabilitationAI:
    """AI 기반 재활 운동 추천 엔진"""
    
    # 부위별 전문 지식 베이스 (프롬프트 최적화용)
    PAIN_AREA_CONTEXT = {
        "손목": "손목터널증후군, 반복성 긴장 손상(RSI), 수근관증후군",
        "어깨": "회전근개 손상, 오십견, 충돌증후군",
        "허리": "요추 디스크, 근막통증증후군, 척추측만증",
        "무릎": "슬개건염, 반월상연골 손상, 퇴행성 관절염",
        "목": "거북목증후군, 경추 디스크, 근막통증",
        "발목": "발목 염좌, 아킬레스건염, 족저근막염"
    }
    
    @staticmethod
    def generate_recommendation(
        pain_area: str,
        pain_description: str,
        severity: int
    ) -> Dict:
        """
        Claude API를 사용하여 맞춤형 재활 운동 추천
        
        Args:
            pain_area: 통증 부위
            pain_description: 통증 상세 설명
            severity: 통증 강도 (1-10)
            
        Returns:
            추천 운동 정보가 담긴 딕셔너리
        """
        
        # 컨텍스트 정보
        context = RehabilitationAI.PAIN_AREA_CONTEXT.get(
            pain_area, 
            "일반적인 근골격계 통증"
        )
        
        # 프롬프트 구성
        prompt = f"""
당신은 20년 경력의 물리치료 전문가입니다. 다음 환자 정보를 바탕으로 재활 운동을 추천해주세요.

**환자 정보:**
- 통증 부위: {pain_area}
- 관련 질환: {context}
- 통증 설명: {pain_description if pain_description else "특이사항 없음"}
- 통증 강도: {severity}/10 (1=경미, 10=극심)

**요구사항:**
1. 통증 강도에 맞는 3-5가지 재활 운동을 추천하세요
2. 각 운동은 다음 정보를 포함해야 합니다:
   - 운동 이름
   - 상세한 실행 방법 (단계별)
   - 권장 세트/횟수 또는 유지 시간
   - 주의사항 (최소 2가지)
   - 난이도 (초급/중급/고급)
3. 전체적인 재활 조언을 추가하세요

**출력 형식 (반드시 유효한 JSON으로만 응답):**
{{
  "exercises": [
    {{
      "name": "운동 이름",
      "description": "1. 첫 번째 단계\\n2. 두 번째 단계\\n3. 세 번째 단계",
      "sets": 3,
      "reps": 10,
      "duration_seconds": 15,
      "cautions": ["주의사항 1", "주의사항 2"],
      "difficulty": "초급"
    }}
  ],
  "general_advice": "전체 재활 조언 (하루 권장 횟수, 진행 기간 등)",
  "estimated_duration_minutes": 10
}}

**중요:** 다른 설명 없이 오직 JSON만 출력하세요. 마크다운 코드 블록(```)도 사용하지 마세요.
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
            
            # JSON 파싱 (혹시 모를 마크다운 제거)
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            recommendation = json.loads(response_text)
            
            # 추가 메타데이터
            recommendation["pain_area"] = pain_area
            recommendation["severity"] = severity
            
            return recommendation
            
        except json.JSONDecodeError as e:
            # JSON 파싱 실패 시 기본 추천 반환
            print(f"JSON 파싱 오류: {e}")
            return RehabilitationAI._get_fallback_recommendation(pain_area, severity)
            
        except Exception as e:
            # API 호출 실패 시 기본 추천 반환
            print(f"AI 추천 생성 오류: {e}")
            return RehabilitationAI._get_fallback_recommendation(pain_area, severity)
    
    @staticmethod
    def _get_fallback_recommendation(pain_area: str, severity: int) -> Dict:
        """API 실패 시 기본 추천 반환"""
        return {
            "pain_area": pain_area,
            "severity": severity,
            "exercises": [
                {
                    "name": f"{pain_area} 기본 스트레칭",
                    "description": "1. 편안한 자세로 앉으세요\n2. 천천히 해당 부위를 움직이세요\n3. 15초간 유지하세요",
                    "sets": 3,
                    "reps": 10,
                    "duration_seconds": 15,
                    "cautions": [
                        "통증이 심해지면 즉시 중단하세요",
                        "무리하지 말고 천천히 진행하세요"
                    ],
                    "difficulty": "초급"
                }
            ],
            "general_advice": "하루 2-3회 반복하며, 증상이 지속되면 전문의 상담을 권장합니다.",
            "estimated_duration_minutes": 10
        }
