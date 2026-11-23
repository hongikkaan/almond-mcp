# 14 · 객체 조회의 범위·조건·결과 선택

사용자 편집 #43의 예시는 scope=inside_viewport, filters.layer.include=[2F::Wall], output.include_ids=true다. 기존 구현은 평면 입력과 레거시 필터 다섯 개만 받는다.

**선행 티켓** 없음

## 구현 경계

#43의 합의 구조와 기존 호출을 양립시킨다. 단일값 조건과 뜻이 확정된 조건부터 지원하며, 미구현 조건을 광고하지 않는다. legacy group_ids의 계층 시작점 동작을 보존한다.

## 수용 기준과 오프라인 검증

공개 입력→native 요청→조회 결과에 대해 이름/레이어 이름·GUID, 포함/제외, 불명·모호 값, 기존 조건, 페이지·스냅샷, 선택 상태 무수정을 확인한다. any/all와 상속 재질의 사용자 판단이 필요한 지점은 근거를 기록한다.

## 재현과 구현 근거

기준 dbdb6f37의 실제 FastMCP 인메모리 호출에서 #43 예시가 `output: Unexpected keyword argument`로 실패했다. C# fixture는 1F·2F·Roof 3개 중 하나를 찾는 레이어 조건을 무시해 세 객체 모두를 반환했다.

공개 모델에서 inside_viewport는 기존 current+inside_window 조회를 사용하고 응답 scope에는 요청한 이름을 반환한다. output의 동명 항목이 평면 인자보다 우선한다. objects/hierarchy/summary, 그룹 GUID 시작점과 기존 필터·행 페이지·면 CRC 경로를 유지한다. Python과 inert 카탈로그가 같은 입력 타입을 읽고, 새 include/exclude는 object_observation 6을 확인한 후 고정 조회로 전달한다.

레이어는 전체 경로/GUID, 배치 블록은 직접 참조하는 정의 이름/GUID를 문서 테이블에서 해석한다. 정의·레이어 이름의 모호성, 존재하지 않는 참조, 잘못된 Rhino 유형을 오류로 반환한다. 객체 이름은 대소문자 무시 정확 일치이고, 동명 객체는 모두 후보가 된다. 기존 name_contains는 부분 검색이다. 모든 조건은 최상위 후보에 적용한 뒤 집계·계층화한다.

재질은 SDK의 RhinoObject.GetRenderMaterial(Boolean)이 앞/뒷면을 구분하고 null이면 GetMaterial을 사용한다. MaterialFromParent는 정의 구성원·면에서 상속하며 명시적 부모가 없으면 레이어를 쓴다. 렌더 재질 GUID와 legacy Material 테이블 GUID, 블록 배치와 자손 표면 중 조회 기준이 정해져야 한다.

기존 계층 fixture에서 그룹 A={1,2}, B={2,3}의 include=[A,B]는 any면 1·2·3, all이면 2 한 건이다. 기존 group_ids는 두 그룹의 합집합을 범위로 잡고 계층 시작 그룹도 제한한다. 기존 메타데이터 조건 배열은 서로 다른 key 조건을 모두 통과해야 하고 조건 안 any_of는 목록 중 하나를 찾는다. 객체 조회에서 새 group/메타데이터 복수 조건의 규칙은 기존 경로의 뜻만으로 정할 수 없다.

동지에게 새 그룹·메타데이터 조건의 include와 exclude에 각각 한 항목만 허용하는 안과, 복수 조건 규칙까지 정한 뒤 새 형식을 추가하는 안을 전달했다. 기존 메타데이터 배열은 그대로 쓸 수 있다. 재질은 적용 대상과 상속 기준을 정하는 별도 결정이 남았다.

## 오프라인 검증 경로

```powershell
./src/mcp/use_offline_environment.ps1 -Development -RequireDotNet
& $env:ALMOND_TEST_PYTHON -B -X utf8 -m pytest -q -c src/mcp/pytest.ini src/mcp/tests/test_object_queries.py src/mcp/tests/test_object_hierarchy.py src/mcp/tests/test_observation_errors.py src/mcp/tests/test_tool_declarations.py src/mcp/tests/test_intersection_workflow.py
```

개발 SDK 8.0.426과 현재 체크아웃의 venv로 116개 통과. FastMCP 경계에서 오류·버전 게이트·scope·output·행/면 페이지를 검증했다. C# doubles는 범위·그룹·블록·참조 해석·필터를 검증한다. 실행 중인 Rhino의 문서 상태와 실제 SDK 가시성·편집기는 별도 통합 검수 범위다.

중첩 output 호출의 후속 안내는 output.offset과 output.expected_snapshot을 가리킨다. 공개 호출로 3개 페이지(0, 1, 2)에서 서로 다른 GUID와 마지막 next_offset=null을 확인했고, 평면 호출의 기존 안내도 확인했다.

## 11/24 후속 구현

object_observation 7은 group과 material을 문서 테이블에서 해석한다. group의 양측에는 이름 또는 GUID 한 개씩을 지정한다. A={front,partial}, B={hidden,partial}에서 include A와 exclude B는 front 한 개다. 그룹 필터는 기존 scope와 hierarchy 시작점을 유지한다. include에 A와 B를 함께 넣는 경우 any는 세 객체, all은 partial 한 객체라서 다중 멤버십 의미는 조율 중이다.

User Text와 User Dictionary는 기존 최대 16개 AND 배열 외에 include·exclude 각각 단일 조건을 받는다. 없는 키는 include에 걸리지 않고 exclude 조건으로도 제외되지 않는다. Dictionary의 attributes·geometry 소스와 숫자·문자열·불리언 자료형이 보존된다. 구 Bridge는 이 입력을 받기 전에 오류를 반환한다.

재질은 최상위 객체에 대해 Rhino가 반환한 전면 RenderMaterial, 없으면 GetMaterial(true)를 사용한다. 연결된 legacy 재질 GUID와 RenderMaterial GUID는 한 재질의 이름·별칭으로 처리한다. 서로 다른 재질의 동명은 오류다. 배치 인스턴스 내부 면 검색과 별개다. 재질 이름·연결과 실효 재질의 페이지 간 변경을 snapshot에 반영한다.

공개 FastMCP 입력과 native C# fixture에서 그룹 결과, 재질 별칭·모호성, 메타데이터 자료형과 제외 동작을 검증했다. 실제 시험 모델의 레이어 상속 재질과 직접 지정 재질 결과·선택 상태 검사는 열려 있다.

저장된 8객체 시험 3DM을 다시 읽었다. A와 B의 include-any는 front·partial·hidden 3개, include-all은 partial 1개다. exclude-any는 두 그룹 밖의 5개, exclude-all은 partial을 제외한 7개다. 여러 그룹을 입력한 쪽에 any/all을 명시하는 안과 생략 시 any로 처리하는 안을 동지에게 전달했다. 제외 결과의 차이가 커서 명시하는 안을 추천한다. 단일 조건과 기존 group_ids 동작은 두 안에서 같다.

**11/24 결정과 구현.** 동지는 여러 그룹을 준 쪽에만 모드를 명시하는 안을 채택했다. 필드명은 `include_mode`와 `exclude_mode`다. 각 측에서 그룹 2..64개를 보내면 해당 모드가 필수이고 하나 또는 미지정이면 모드를 생략한다. exclude-all은 지정한 모든 그룹에 함께 속한 객체만 제외한다. 그룹의 이름·GUID를 함께 쓸 수 있으며 같은 그룹을 가리켜도 결과를 중복하지 않는다. 알 수 없는 그룹이나 확인할 수 없는 편집 중 멤버십은 오류다. 새 모드에는 object_observation 8이 필요하며 기존 단일 그룹은 버전 7부터 동작한다. 별도 group_ids, 레거시 메타데이터 배열, 스코프와 선택 상태 계약은 유지한다.


## 11/24 표준 RhinoBeyond 실검수

루트 dev에서 빌드한 Bridge·AlmondRhino·Engine의 디스크 모듈 ID와 Rhino 프로세스 40952가 로드한 모듈 ID가 일치했다. connect_01-list_up과 connect_02-session으로 전용 Beyond-Acceptance.3dm을 선택하고 inspect_02-get_objects로 결과 GUID를 대조했다.

| 조회 | 예상 | 실제 |
|---|---|---|
| A·B 포함 any / all | front·hidden·partial / partial | 3개 / 1개, 각 GUID 일치 |
| A·B 제외 any / all | 두 그룹 바깥 / partial을 제외한 전체 | 5개 / 7개, 각 GUID 일치 |
| User Text test_case=partial | 포함 1개, 제외 7개 | 새 양식·기존 배열 포함 1개, 제외 7개 |
| User Dictionary 임시 점 | 속성 정수 2, 형상 문자열 "2"만 일치 | 각각 1개, 소스와 값 형식을 교차하면 0개. 기존 배열 1개, 제외 0개 |
| LayerFinish | 레이어 상속 5개 | 이름·legacy GUID·render GUID 모두 같은 5개 |
| ObjectFinish | 독립 재질 두 개의 동명 오류. GUID별로 객체 2개와 블록 배치 1개 | 이름은 invalid_arguments, 연결된 GUID는 partial·sliver, 독립 GUID는 instance_2. 두 GUID 포함 3개, 제외 5개 |
| 그룹 필터 결과 모드·페이지 | summary·hierarchy 각각 3객체, 페이지당 1개씩 3개 | 수량과 3개 고유 ID 일치, 끝 페이지 next_offset=null |

저장 파일의 재질 이름만 보고 직접 지정 세 객체를 하나의 재질로 예상한 부분은 실제 문서의 재질 ID로 교정했다. instance_2에는 별도 legacy GUID가 있고 RenderMaterial 연결이 없다. 실제 조회는 서로 다른 동명 재질을 구별하는 공개 계약과 일치했다.

기존 group_ids, 레이어·객체 이름·유형·블록 필터, 그룹과 재질 결합, 잘못된 그룹 및 다중 그룹 모드 누락 오류도 확인했다. inside_viewport와 기존 current + inside_window는 같은 8개였다. 임시 점을 제거한 뒤 원래 GUID 8개와 선택 0개를 확인했다. 시험 파일은 저장하지 않았고 SHA-256은 전후 동일했다. 열린 시험 문서에는 임시 객체의 생성·제거로 미저장 표시가 남았다.

로컬 원본 응답은 data/worktrees/dev/data/acceptance-1124의 public-filter-20261124T043243, public-filter-20261124T043520, public-filter-20261124T043735에 있다. filter-live-loaded-build.json에는 실제 로드와 디스크를 대조한 결과가 있다.
