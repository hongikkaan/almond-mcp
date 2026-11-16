# Python MCP와 연결 실행기

- `src/mcp/server.py`는 공통 MCP 도구를 조립한다. `src/mcp/runtime`은 checkout CLI·세션 바인딩·저장소·Rhino 문서 연결 실행기이며 외부 연결기에는 공개 확장 훅을 제공한다. Python MCP가 외부 연결기 구현을 import하지 않는다.
- 모델링·도면·Scene/Component·Plan·자산의 책임과 계약은 `src/mcp/SPEC.md`와 기능별 문서. 고정 조회와 일반 수정 실행은 `src/mcp/rhino/OBSERVATION-SPEC.md`를 따른다.
- Rhino 문서 연결 실행기는 initialize에 시작 안내를 제공한다. 상세 정책은 context_01-get_policy tool, 도구별 공개 설명은 구현 옆 Markdown, 동적 후속 안내는 `tool_guidance.py` 경로로 전달된다.