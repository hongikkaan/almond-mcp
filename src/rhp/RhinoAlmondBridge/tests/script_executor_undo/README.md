# Undo·관측 검증 상태

이전 native Undo·관측 fixture는 현재 테스트 구성에 없다. 이 폴더에 실행할 수 있는 Undo/Redo 또는 `ObservationTests.RunViewport` 검사가 있다는 뜻이 아니며, GH·도면 스타일 fixture는 production `NativeUndoRecord`의 소유권·빈 record·실패 복구를 SDK 대역으로 검사한다. 이 결과는 실제 Rhino 문서의 Undo/Redo, geometry·layer·view·selection 보존 검증과 구분한다.

현재 실행 가능한 Engine·Terminal·Archive·패널 검사의 범위와 명령은 [native 오프라인 검사](../../../tests/README.md)를 참고한다. RHP 빌드, 등록, 실제 로드와 실제 문서의 기능 검증은 각각 별도의 근거다.

개발 검사에서 실제 Rhino 문서의 Undo/Redo와 관측은 검증 범위 밖으로 기록한다. 문서를 생성하거나 교체하는 fixture는 사용자 문서에 적용할 수 없으며 보호 조건을 유지한다.
