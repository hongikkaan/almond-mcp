{server_name}는 Almond의 외부 MCP 연결기입니다. AlmondRhino 플러그인에 연결해 Rhino에서 2D/3D 건축 설계·디자인 작업을 수행합니다.

다음 4개는 Rhino 문서와의 연결 관리 도구의 설명이자 사용설명서이며, 4개 외 나머지는 모델링 도구입니다.

1. `list_connections`: 먼저 연결 가능한 Rhino 문서와 현재 연결을 확인합니다.
2. `connect`: 목록의 `host_id`와 `model_path`로 문서에 연결합니다. 반환된 `connection_id`는 이후 모델링 도구에 사용합니다.
3. `start_session`: 새 창이 필요하면 저장된 `.3dm` 파일을 새 Rhino 창으로 열고 연결합니다. 반환된 `connection_id`로 모델링 도구를 사용합니다.

---

- `disconnect`: 작업이 끝나면 `connection_id`로 연결을 해제합니다. Rhino를 저장하거나 닫지는 않습니다.
