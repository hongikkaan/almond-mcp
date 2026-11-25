# 작업 완료 검증

- 필드명·타입·기본값만으로 충분하면 원본의 `description`을 생략한다. 단순 목록의 빈 값·조회 실패 표현도 반복하지 않는다. 호출 조건, 단위·범위, 실패 복구, 실행 완료와 검사 통과의 차이는 짧은 한국어로 쓰고 존대 종결어미를 생략한다. 외부 stdio 통합 검사는 실제 선언 전체의 SHA-256을 문서와 대조한다.

- `tests/README.md`의 변경 유형별 표가 기준이다. 안내 문서는 링크·앵커와 명령·전제를 정적 대조한다. 공개 Python 도구 변경은 MCP 모듈 검사와 루트 통합 검사로 검증하고, 설명 원본·`src/mcp/output_contracts.py`·`tests/integration/tool_schemas.json`과 실제 공개 스키마를 비교한다.
- 커밋 전 격리된 데이터 폴더에서 beyond와 RhinoTerminal의 stdio `initialize` 및 `tools/list`를 수집한다. 각 연결의 도구 목록·설명·입출력 스키마(문자열 wrapper와 중첩 `contentSchema` 포함)를 `TOOL-DECLARATIONS-CURRENT.md`와 대조하고, 시작 안내의 출처·전달 위치는 `initialize`에서 확인한다. 선언이 바뀌면 문서의 해당 항목뿐 아니라 상단의 도구 수와 이름순 tools 전체 배열 SHA-256도 갱신한다. 직렬화 방식은 해당 문서에 명시한다. 이 검사는 Rhino 연결 없이 실행한다.
- RhinoTerminal stdio 검사와 선언 문서 생성에 쓸 3DM 자리표시자는 부모 검사 프로세스가 임시 폴더 안에 새로 만든다. 기존 파일과 이름이 겹치면 중단하며, 재연결 검사는 처음 준비한 실행 인자로 동일한 시험 파일을 재사용한다.
- 공유 Engine 변경은 오프라인 Engine fixture와 영향받는 소비 경로를 확인한다. RHP는 Rhino 실행 여부와 관계없이 대상 출력의 사용 가능 여부를 확인한 뒤 빌드하고 양쪽 manifest·Engine DLL 일치를 확인한다. 통합 검수는 사용자가 허가한 범위에서 `tests/README.md`의 일상 체크아웃·빌드 판단·Beyond 연결 절차를 따른다.
- 오프라인 결과, 빌드·배치, 등록 확인, 실제 로드와 모델·뷰·Layout 동작을 각각 보고한다. Windows symlink 생성 권한 오류 등 환경 실패는 전체 결과에 실패로 남긴다.
