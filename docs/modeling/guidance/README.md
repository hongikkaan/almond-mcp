# 모델링 지침 편집

[모델링 지침](modeling-guide.md)과 `references/`가 MCP 안내의 편집 원본이다.
별도 설치형 `rhino-almond` 스킬은 제공하지 않는다. 클라이언트는 시작 안내와
도구별 조건에서 `get_modeling_guide`의 필요한 주제를 찾아 읽는다.

`mcp-guide-map.json`은 원본 절·조건·관련 도구·사진을 배분한다. 원본을 수정한 뒤
저장소 루트에서 아래 명령으로 배포 번들을 갱신하고 확인한다.

```powershell
& ./src/engine/.venv/Scripts/python.exe -B src/mcp/guide_build/build_modeling_guides.py
& ./src/engine/.venv/Scripts/python.exe -B src/mcp/guide_build/build_modeling_guides.py --check
```

번들은 `src/mcp/modeling_guides`에 포함된다. 실행 중에는 이 문서
폴더나 개인 스킬 경로를 읽지 않는다. 새 번들은 관련 MCP 세션을 정상 종료하고
다시 시작한 뒤 사용한다.

`authoring-request.md`는 작성 요청 원문이며 실행 지침이 아니다. 사용자 사례의
원문 구간과 사진 바이트는 보존한다. 사용하지 않는 참고 사진도 삭제하지 않고
배분표에 제외 이유를 기록한다. 기존 native 관찰 fixture는 소유 모듈의
[probe_observation 검사](../../../src/rhp/RhinoAlmondBridge/tests/probe_observation/README.md)에 둔다.
