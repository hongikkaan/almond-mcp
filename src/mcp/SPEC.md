# MCP 계약

이 모듈은 공개 MCP 도구, 계산·자산 API, CLI 실행과 연결별 Python runtime을 소유한다.
작업 규칙은 [AGENTS.md](AGENTS.md), 공통 경계는 [루트 SPEC](../../SPEC.md)를 따른다.

## 구성과 의존 관계

- `almond_mcp/`: 배포되는 Python package와 공개 도구·계산·라이브러리 API.
- `runtime/`: CLI 시작·재연결, 모델 binding, A–J 슬롯, 공유 저장소와 native 완료 확인.
- `tools/`: MCP 자산·모델링 자료의 생성·검증 도구.
- `tests/`, `pytest.ini`, `run_tests.ps1`: 모듈 검사. COS import 없이 실행한다.
- `rebuild_environment.ps1`: 이 체크아웃의 환경을 구성하며 COS catalog는 수정하지 않는다.
- `use_offline_environment.ps1`: 현재 셸과 자식에만 로컬 검사 경로를 설정한다.

COS는 runtime의 binding 검증·구성 훅을 사용한다. MCP는 COS 구현을 참조하지 않는다.
Python package 이름은 `almond_mcp`이며 외부 entry point와 도구 schema를 보존한다.
`almond_mcp/rhino`의 C# 모델링 코드와 재료 정책은 MCP 소유지만 Bridge에 컴파일되므로,
변경 시 Bridge 빌드가 필요하다. Python package가 사용하는 웹 원본은
[RHP Asset Panel](../rhp/SPEC.md)의 공유 자원이다.

공개 API 내부 동작을 바꾸더라도 COS fingerprint 대상 파일이 바뀌면 COS catalog를
재생성하고 루트 통합 검사를 수행한다. 공유 계약 변경을 임의로 우회하지 않는다.

## 실행·관측 계약

연결마다 token·session·call 디렉터리와 프로세스 identity를 확인한다. 모델 폴더의
DB/tmp는 공유하며 저장소 lease·DB 잠금·native 완료 확인을 유지한다.

`get_rhino_context`, `get_rhino_viewport_image`, `get_rhino_probe`는 고정 관찰 경로다.
조회가 geometry·layer·selection·camera·Undo를 바꾸면 안 된다.
`execute_rhino_script`의 `result_error`는 이미 끝난 수정을 취소하지 않는다.
요청·반환 제한과 미확인 값의 의미는 [관측 계약](../../docs/modeling/native-observation.md)을 따른다.

기존 CoS command를 유지하기 위해 Python 환경은 `../engine/.venv`에 둔다.
구현 위치와 실행 파일 위치는 별개다. 이전 시작 버튼은 호환 스크립트를 거쳐
`runtime/` 실행기를 호출한다. 사용자 모델·DB·라이브러리를 자동 이동하지 않는다.

## Scene·Component·계획

- Scene은 공간의 의도와 맥락이다. 일반 객체를 직접 참조하거나 Component를 포함한다.
- Component는 명시적으로 등록한 Rhino group이다. 일반 group을 자동 등록하지 않는다. 한 객체의 직접 소유자는 최대 하나이고 Component는 하나 이상의 Scene에 속한다.
- 중첩 Component의 부모 group은 하위 객체를 포함하지만 직접 소유권은 자식에 남는다. block occurrence는 포함할 수 있고 공유 block definition 내부를 occurrence별 객체로 소유하지 않는다.
- Rhino group의 UserString 대신 기존 멤버의 `almond:component_record`를 `ModifyAttributes`로 변경해 Undo를 보존한다. 관리용 가짜 객체는 만들지 않는다.
- DB 사전검사 → native 수정 → 완전한 snapshot 확인 → DB commit 순서다. 캐시 조회는 `live_verified=false`, live 조회는 불일치·pending objects를 드러내고 명시적 sync가 장부와 group을 정합시킨다. timeout은 재실행 허가가 아니다.
- Room·asset instance는 기존 충돌·containment·하중 검사에 남는다. `validate_scene_layout`의 통과를 Component 기하 검증으로 해석하지 않는다.
- Phase 아래 Plan, Plan 아래 Step을 둔다. Plan은 여러 Scene·Component, Step은 Component를 참조한다. 참조 생략은 상속, 빈 목록은 대상 없음이다.
- Plan 변경은 immutable revision으로 기록하며 `expected_revision`은 오래된 상태의 수정을 거절한다. 이 기록은 기하 백업이나 자동 실행기가 아니다.

세부 입력·계층·동기화·도면 계약은 [Component 시스템](../../docs/modeling/component-system.md)에 둔다.

## 재료·도면·자산

재료 manifest의 `layer_path`와 `modeling_policy.json`을 기준으로 `assign_material`과 `ModelingMaterials.CreateAttributes`가 같은 native 구현을 사용한다. MCP C# 실행은 추가 객체·직접 재료 변경을 모아 최종 속성으로 레이어를 적용한 뒤 같은 Undo record를 닫는다. 시작 시 전체 문서를 변경하지 않으며 ByLayer·ByParent는 추측하지 않는다. 외부 스크립트는 factory를 명시적으로 사용한다.

새 모델링 metadata는 필요한 material ID·floor·construction detail·typed source에 한정한다. Component 등록이 소유권을 기록하고 PBR 값은 native material에 둔다. 이름은 자유롭게 사용하며 기존 unrelated UserString을 지우지 않는다.

Drawing Sheet는 모델 공간 World XY의 작성 영역을 Rhino Layout의 Top detail로 지정 축척에 연결한다. 영역이 용지·축척에 맞지 않으면 생성 전에 거절한다. 도면 형상이나 단면 대상을 자동 추측하지 않으며 등록 해제는 geometry·Layout 삭제가 아니다.

저장소 `asset/`, wheel `almond_mcp/data/`, AppData 라이브러리의 배치는 다르다. 명시적 `RHINO_MCP_*_DIR`이 우선하며 기존 사용자 파일·manifest 상대 경로·계약/모델 해시를 보존한다. 다운로드한 community model과 원시 생성 파일은 기본 패키지에 포함하지 않는다. 자산·도면 도구와 단위·출처 계약은 [자산 안내](../../docs/assets/assets-and-drawings.md)를 따른다.
