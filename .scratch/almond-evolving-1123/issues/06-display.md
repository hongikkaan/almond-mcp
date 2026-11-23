# 13 · 뷰 메뉴에 등재된 기존 표시 모드 선택

목록·이름·GUID 해석이 모든 설치 모드를 사용한다. Rhino SDK의 InMenu와 SupportsShadeCommand는 별도 속성이다.

**선행 티켓** 없음

## 구현 경계

캡처·기존 표시 모드 조회/선택 경로에 View Display Mode Menu 기준을 적용한다. 새 모드 생성이나 테스트 모드명 하드코딩은 제외한다. 대상별 일시 적용/뷰 유지 계약을 보존한다.

## 수용 기준과 오프라인 검증

메뉴·Shade 설정 네 조합으로 후보 노출과 선택을 검사한다. 기본 프로필의 list-01~04와 실제 메뉴의 대조는 승인된 live 검수에 남긴다.

## 구현 및 검증 결과

기준은 dev의 `dbdb6f3`이다. `DisplayModeMenu.cs`가 Rhino의 현재 `GetDisplayModes()`에서 `InMenu`가 참인 모드를 읽는다. `inspect_03-get_document_context` tool은 메뉴 필터를 먼저 적용하고 이름과 GUID를 128개까지 반환한다. 캡처의 이름·GUID 해석에는 목록 출력 상한을 적용하지 않는다. 메뉴에 중복 이름이 있으면 GUID가 필요하다. 영문 이름과 현지화 이름을 대소문자 구분 없이 지원한다.

`capture_02-inspection` tool은 기존 독립 뷰와 실제 그리기의 모드 GUID 검사를 유지한다. `capture_03-current_view` tool은 선택한 모드를 작업 뷰에 적용한 직후 해당 뷰의 GUID를 확인한다. `capture_04-defined_view` tool은 Named View의 독립 파이프라인을 초기화한 뒤 모드 GUID를 확인한다. Layout은 기존 Detail별 모드를 사용한다. 명시한 실시간 렌더 모드에는 기존 비동기 렌더 제약을 적용한다.

기존 코드에서는 Shade 전용 모드도 GUID로 현재 뷰에 적용됐고 비메뉴 130개가 앞에 있으면 메뉴 항목이 공개 목록에서 사라졌다. 작업 뷰가 대입을 무시한 경우에도 변경 성공을 보고했다. 각각 오프라인 실패를 확인한 후 수정했다.

- `./src/mcp/run_tests.ps1 -Development -TestArgs '-k','test_stage2_native_feedback or test_inspection_display or test_inspection_block_capture or test_context_sections or test_layout_viewport_state or (test_view_capture and not public_schema)','-q'`에서 96개가 통과했다. 메뉴·Shade 네 조합, 목록 한도와 경고, 현지화 이름·GUID·이름 중복, 숨겨진 후보, 비동기 모드 거절, 작업 뷰의 GUID 확인을 포함한다. 스키마 기준은 통합 단계에서 함께 대조한다.
- `./src/rhp/RhinoTerminal/data/sdk/dotnet.exe build data/t/display-menu-sdk/DisplayMenu.csproj --no-restore -c Release --nologo -p:UseSharedCompilation=false -nodeReuse:false`로 공용 모드 코드를 설치된 Rhino 8의 `RhinoCommon.dll`과 컴파일했다. SDK 8.0.426, 경고 0개, 오류 0개였다. 배포 RHP 빌드와 manifest는 통합 단계에서 다룬다.

구형 Bridge와 새 worker 조합에서 비메뉴 모드를 조회하거나 적용하는 회귀도 확인했다. 새 Bridge는 `display_mode_menu=1`을 광고하고, Python은 기존 문서·capability 응답에서 이 값을 확인한다. 기본 문서 조회, 표시 모드 목록, 명시한 모드가 있는 검사 타일·현재 뷰, Shaded를 선택하는 Named View가 구형 Bridge에서 오류를 반환한다. 모드 선택이 없는 현재 뷰·검사 타일과 Layout은 기존 경로를 사용한다. 조회 요청 횟수도 검사했다.

- `./src/mcp/run_tests.ps1 -Development -TestArgs '-k','test_stage2_native_feedback or test_inspection_display or test_inspection_block_capture or test_inspection_shared_scope or test_capture_pixel_size or test_capture_artifacts or test_context_sections or test_layout_viewport_state or (test_view_capture and not public_schema)','-q'`에서 139개 통과. 이후 추가한 기존 Bridge 무지정 모드 검사 `-k test_old_bridge_can_capture_without_selecting_a_display_mode`에서 3개 통과.
- `./src/mcp/use_offline_environment.ps1 -Development -RequireDotNet` 후 `& $env:ALMOND_TEST_PYTHON -B -X utf8 -m pytest -q tests/integration/test_capture_workspace_isolation.py`에서 Named View의 두 연결 간 작업 폴더 격리 검사 1개 통과.

기본 프로필의 저장 XML에는 `list-01`에 SupportsShadeCmd=True, `list-02`에 SupportsShadeCmd=True와 AddToMenu=False, `list-03`에는 두 필드 모두 생략, `list-04`에는 AddToMenu=False가 기록돼 있다. 생략값의 Rhino 적용과 실행 중 메뉴 상태는 실제 검수 대상으로 남긴다. 승인된 시험 Rhino에서 View Display Mode Menu와 Shade 명령의 목록을 각각 조회해 네 이름·GUID를 대조하고, 메뉴 모드를 선택하여 02의 실제 타일 모드, 03 작업 뷰 변경, 04 작업 뷰 보존을 확인한다.

`capture_01-conditioning_pass`에는 별도의 RGB·edge 모드 해석과 depth 패스가 있다. RGB·edge에서 이름이 없으면 현재 뷰를 사용하는 기존 동작이 있어, 같은 메뉴와 오류 처리를 적용하면 공개 동작이 달라진다. 기본 Rendered·Technical과 호출자가 같은 이름을 명시한 경우도 하위 경로에서 구별하지 못한다. 동지에게 RGB·edge의 명시적 선택만 통일하고 전용 depth 패스를 보존하는 안을 제안했다. 이번 구현 대상은 문서의 모드 목록과 capture_02·03·04다.
