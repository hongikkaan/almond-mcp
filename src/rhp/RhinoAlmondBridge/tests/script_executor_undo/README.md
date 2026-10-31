# Undo·관측 검증 상태

이전 native Undo·관측 fixture는 현재 테스트 구성에 없다. 이 폴더에 실행할 수 있는 Undo/Redo 또는 `ObservationTests.RunViewport` 검사가 있다는 뜻이 아니며, 현재 오프라인 검사를 통과해도 Undo/Redo, Rhino 문서 관측, geometry·layer·view·selection의 보존은 검증되지 않는다.

현재 실행 가능한 Engine·Terminal·Archive·패널 검사의 범위와 명령은 [native 오프라인 검사](../../../tests/README.md)를 참고한다. RHP 빌드, 등록, 실제 로드와 실제 문서의 기능 검증은 각각 별도의 근거다.

실제 기능 테스트가 필요한 경우 사용자가 작업에 연결한 Rhino 문서의 기존 형상과 도면 맥락을 보존해 수행한다. 빈 문서나 일회용 문서를 전제로 내용을 생성·교체하는 fixture를 사용자 문서에서 실행하지 않고, 그러한 fixture의 보호 검사를 해제하지 않는다. 테스트만을 위해 Rhino 문서를 자동 생성하거나 별도 Rhino를 실행하지 않는다.
