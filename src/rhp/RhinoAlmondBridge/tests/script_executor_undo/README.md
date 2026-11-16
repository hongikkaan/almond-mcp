# Undo·관측 검증 상태

이전 native Undo·관측 fixture는 현재 테스트 구성에 없다. 이 폴더에 실행할 수 있는 Undo/Redo 또는 `ObservationTests.RunViewport` 검사가 있다는 뜻이 아니며, 현재 오프라인 검사를 통과해도 Undo/Redo, Rhino 문서 관측, geometry·layer·view·selection의 보존은 검증되지 않는다.

현재 실행 가능한 Engine·Terminal·Archive·패널 검사의 범위와 명령은 [native 오프라인 검사](../../../tests/README.md)를 참고한다. RHP 빌드, 등록, 실제 로드와 실제 문서의 기능 검증은 각각 별도의 근거다.

개발 검사에서 실제 Rhino 문서의 Undo/Redo와 관측은 검증 범위 밖으로 기록한다. 문서를 생성하거나 교체하는 fixture는 사용자 문서에 적용할 수 없으며 보호 조건을 유지한다.
