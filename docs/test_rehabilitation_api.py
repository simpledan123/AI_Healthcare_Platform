"""
test_rehabilitation_api.py
재활 운동 추천 API 테스트 스크립트
"""

import requests
import json
from datetime import datetime

# API 기본 URL
BASE_URL = "http://localhost:8000"

# 테스트 데이터
TEST_CASES = [
    {
        "name": "손목 통증 - 경미",
        "data": {
            "user_id": 1,
            "pain_area": "손목",
            "severity": 3,
            "pain_description": "마우스 사용 후 약간 뻐근함"
        }
    },
    {
        "name": "어깨 통증 - 중간",
        "data": {
            "user_id": 1,
            "pain_area": "어깨",
            "severity": 6,
            "pain_description": "컴퓨터 작업 후 어깨가 묵직함"
        }
    },
    {
        "name": "허리 통증 - 심함",
        "data": {
            "user_id": 1,
            "pain_area": "허리",
            "severity": 8,
            "pain_description": "오래 앉아있으면 허리가 아픔"
        }
    },
    {
        "name": "무릎 통증 - 보통",
        "data": {
            "user_id": 1,
            "pain_area": "무릎",
            "severity": 5,
            "pain_description": "계단 오를 때 무릎이 시큰거림"
        }
    }
]

def print_section(title):
    """섹션 제목 출력"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_ai_recommendation():
    """AI 추천 API 테스트"""
    print_section("🤖 AI 재활 운동 추천 API 테스트")
    
    for test_case in TEST_CASES:
        print(f"\n📋 테스트 케이스: {test_case['name']}")
        print(f"   통증 부위: {test_case['data']['pain_area']}")
        print(f"   통증 강도: {test_case['data']['severity']}/10")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/rehabilitation/recommend",
                json=test_case['data'],
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ 성공!")
                print(f"   추천 운동 수: {len(result['exercises'])}개")
                print(f"   예상 소요 시간: {result['estimated_duration_minutes']}분")
                
                # 첫 번째 운동 정보 출력
                if result['exercises']:
                    first_exercise = result['exercises'][0]
                    print(f"\n   💪 첫 번째 추천 운동:")
                    print(f"      - 이름: {first_exercise['name']}")
                    print(f"      - 난이도: {first_exercise['difficulty']}")
                    print(f"      - 세트: {first_exercise['sets']}세트 × {first_exercise['reps']}회")
            else:
                print(f"   ❌ 실패: HTTP {response.status_code}")
                print(f"   오류: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("   ❌ 서버 연결 실패. 백엔드 서버가 실행 중인지 확인하세요.")
            print(f"   명령어: uvicorn app.main:app --reload")
            break
        except Exception as e:
            print(f"   ❌ 오류 발생: {str(e)}")

def test_get_history():
    """재활 기록 조회 API 테스트"""
    print_section("📊 재활 기록 조회 API 테스트")
    
    user_id = 1
    try:
        response = requests.get(
            f"{BASE_URL}/api/rehabilitation/history/{user_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공!")
            print(f"총 기록 수: {result['total_records']}개")
            
            if result['records']:
                print(f"\n최근 기록:")
                for i, record in enumerate(result['records'][:3], 1):
                    created_date = datetime.fromisoformat(
                        record['created_at'].replace('Z', '+00:00')
                    )
                    print(f"{i}. {record['pain_area']} (강도: {record['severity']}/10)")
                    print(f"   - 날짜: {created_date.strftime('%Y-%m-%d %H:%M')}")
                    print(f"   - 상태: {'✅ 완료' if record['completed'] else '⏳ 진행중'}")
            else:
                print("아직 기록이 없습니다.")
        else:
            print(f"❌ 실패: HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버 연결 실패")
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

def test_statistics():
    """통계 조회 API 테스트"""
    print_section("📈 통계 조회 API 테스트")
    
    user_id = 1
    try:
        response = requests.get(
            f"{BASE_URL}/api/rehabilitation/statistics/{user_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공!")
            print(f"총 추천 횟수: {result['total_recommendations']}회")
            print(f"완료한 운동: {result['completed_exercises']}회")
            print(f"완료율: {result['completion_rate']}%")
            print(f"평균 통증 강도: {result['average_severity']}/10")
            
            if result['top_pain_areas']:
                print(f"\n주요 통증 부위:")
                for area_info in result['top_pain_areas']:
                    print(f"  - {area_info['area']}: {area_info['count']}회")
        else:
            print(f"❌ 실패: HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버 연결 실패")
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

def main():
    """메인 테스트 실행"""
    print("\n" + "🏥"*30)
    print("AI 재활 운동 추천 API 테스트 스크립트")
    print("🏥"*30)
    
    print(f"\n📍 테스트 대상 서버: {BASE_URL}")
    print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. AI 추천 테스트
    test_ai_recommendation()
    
    # 2. 기록 조회 테스트
    test_get_history()
    
    # 3. 통계 조회 테스트
    test_statistics()
    
    # 마무리
    print_section("🎉 테스트 완료")
    print("\n💡 Tip: Swagger 문서에서 더 자세한 테스트를 할 수 있습니다.")
    print(f"   URL: {BASE_URL}/docs")
    print()

if __name__ == "__main__":
    main()
