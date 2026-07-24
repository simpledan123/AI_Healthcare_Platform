# Validation record

검증일: 2026-07-24

| 항목 | 결과 |
| --- | --- |
| Python 구문 컴파일 | 통과 |
| Backend pytest | 6 passed |
| Demo API smoke test | 통과 |
| SQL dashboard/update flow | 통과 |
| High-severity human-review branch | 통과 |
| OpenCV import | 4.11.0 |
| MediaPipe import | 0.10.21 |
| Frontend clean install | 통과 |
| Frontend production build | 통과 |
| n8n workflow JSON parse | 통과 |
| Docker Compose YAML parse | 통과 |

검증 환경에 Docker 실행기가 없어 실제 컨테이너 기동은 수행하지 못했습니다.
실제 영상 파일이 제공되지 않아 영상 업로드의 전체 분석 결과는 만들지
않았지만, OpenCV·MediaPipe 의존성 로드와 영상 분석 모듈의 구문·테스트
경로를 확인했습니다. 데모 API는 실제 서버를 기동해 응답까지 확인했습니다.

