# 작업 완료 검증

- `tests/README.md`의 변경 유형별 표가 기준이다. 안내 문서는 링크·앵커와 명령·전제를 정적 대조한다. 공개 Python 도구 변경은 MCP 모듈 검사와 루트 통합 검사로 검증하고, 설명 원본·`src/mcp/output_contracts.py`·`tests/integration/tool_schemas.json`과 실제 공개 스키마를 비교한다.
- 공유 Engine 변경은 오프라인 Engine fixture와 영향받는 소비 경로를 확인한다. RHP 빌드는 Rhino를 닫고 양쪽 manifest·Engine DLL 일치를 확인한다. 통합 검수는 사용자가 허가한 범위에서 `tests/README.md`의 일상 체크아웃·빌드 판단·Beyond 연결 절차를 따른다.
- 오프라인 결과, 빌드·배치, 등록 확인, 실제 로드와 모델·뷰·Layout 동작을 각각 보고한다. Windows symlink 생성 권한 오류 등 환경 실패는 전체 결과에 실패로 남긴다.
