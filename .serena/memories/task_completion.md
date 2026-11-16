# 작업 완료 검증

- `tests/README.md`의 변경 유형별 표가 기준이다. 안내 문서는 링크·앵커와 명령·전제를 정적 대조한다. 공개 Python 도구 변경은 MCP 모듈 검사와 루트 통합 검사로 검증하고, 설명 원본·`src/mcp/output_contracts.py`·`tests/integration/tool_schemas.json`과 실제 공개 스키마를 비교한다.
- 공유 Engine 변경은 오프라인 Engine fixture와 영향받는 소비 경로를 확인하고, 제품 전달에는 사전 Rhino 종료 확인 후 양쪽 RHP 빌드와 manifest·Engine DLL 일치 검증이 따른다. Rhino·RhinoCore를 테스트에 실행하거나 연결하지 않는다.
- 오프라인 결과, 빌드·배치, 등록 확인, 실제 로드 증거를 각각 보고한다. 모델링·뷰·Layout·Undo 등 Rhino에서만 확인할 수 있는 동작은 개발 검사 범위 밖으로 기록한다. Windows symlink 생성 권한 오류 등 환경 실패는 전체 결과에 실패로 남긴다.