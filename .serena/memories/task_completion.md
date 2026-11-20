# 작업 완료 검증

- `tests/README.md`의 변경 유형별 표가 기준이다. 안내 문서는 링크·앵커와 명령·전제를 정적 대조한다. 공개 Python 도구 변경은 MCP 모듈 검사와 루트 통합 검사로 검증하고, 설명 원본·`src/mcp/output_contracts.py`·`tests/integration/tool_schemas.json`과 실제 공개 스키마를 비교한다.
- 커밋 전 격리된 데이터 폴더에서 beyond·CoS stdio `initialize`와 `tools/list`를 수집한다. 두 경로의 도구 목록·설명·입출력 스키마(문자열 wrapper와 중첩 `contentSchema` 포함)를 `TOOL-DECLARATIONS-CURRENT.md`와 대조하고, 시작 안내의 출처·전달 위치는 `initialize`에서 확인한다. 선언이 바뀌면 문서의 해당 항목뿐 아니라 상단의 도구 수와 이름순 tools 전체 배열 SHA-256도 갱신한다. 직렬화 방식은 해당 문서에 명시한다. 이 검사는 Rhino 연결 없이 실행한다.
- 공유 Engine 변경은 오프라인 Engine fixture와 영향받는 소비 경로를 확인한다. RHP는 Rhino 실행 여부와 관계없이 대상 출력의 사용 가능 여부를 확인한 뒤 빌드하고 양쪽 manifest·Engine DLL 일치를 확인한다. 통합 검수는 사용자가 허가한 범위에서 `tests/README.md`의 일상 체크아웃·빌드 판단·Beyond 연결 절차를 따른다.
- 오프라인 결과, 빌드·배치, 등록 확인, 실제 로드와 모델·뷰·Layout 동작을 각각 보고한다. Windows symlink 생성 권한 오류 등 환경 실패는 전체 결과에 실패로 남긴다.
