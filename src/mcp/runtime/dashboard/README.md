# Almond Project Dashboard

저장된 SQLite DB에서 **File·Scene·Holon·Phase·Task·Step**을 읽는 로컬 Dashboard입니다. DB와 Rhino 모델을 수정하지 않습니다.

## 실행

이 Dashboard 체크아웃의 루트에서 PowerShell로 실행합니다.

```powershell
& '.\src\mcp\runtime\Almond DB Dashboard.cmd'
```

DB를 선택하면 브라우저가 열립니다. 확장자 없는 파일은 파일 선택 창의 **All files**에서 선택합니다. 종료는 실행 창에서 **Ctrl+C**입니다. 브라우저 탭만 닫으면 서버는 유지됩니다.

독립 실행기는 Git으로 원본 저장소를 찾아 그곳의 기존 Python을 선택하고, 실행한 워크트리의 Dashboard 소스를 읽습니다. Python 환경을 새로 만들거나 복사하지 않습니다. 원본 `.venv`, `venv`, `data/development/.venv`, `src/engine/.venv` 순서로 선택하며 `-Development`는 원본 개발 환경을 명시합니다. Rhino 패널은 로드된 Bridge가 속한 체크아웃의 `src/engine/.venv`와 Dashboard 소스를 사용하며, 다른 체크아웃을 탐색하지 않습니다.

```powershell
./src/mcp/runtime/dashboard.ps1 -Database 'C:\프로젝트\.almond\scene.sqlite3'
./src/mcp/runtime/dashboard.ps1 -NoBrowser
```

새 RHP가 배포된 환경에서는 **AlmondDashboard** 명령으로 같은 화면을 Rhino 패널 안에서 엽니다. Rhino의 기본 명령 탐색을 사용하고, 패널은 명령을 처음 실행할 때 등록됩니다. Almond 홈에는 Dashboard 버튼을 추가하지 않습니다. 패널은 Rhino 표준 도킹·분리 동작을 사용합니다. 같은 명령은 기존 패널을 다시 열며, DB를 재선택할 때 기존 소유 서버를 정리해 중복 없이 교체합니다. 마지막 Dashboard 패널을 닫으면 해당 패널이 시작한 조회 프로세스만 정리합니다. Rhino나 모델링 MCP 연결을 시작하는 기능은 아닙니다.

Rhino 진입은 현재 저장된 문서의 기존 프로젝트 DB를 자동 선택합니다. 문서 활성화·저장·닫기에서 맥락을 갱신하며, 미저장 문서·DB 없음·읽기 실패는 상태로 알리고 이전 문서 화면을 숨깁니다. DB를 새로 만들지 않습니다. 정상 로드 후에는 Rhino 패널의 상태 영역이 접히고 웹 화면이 패널 전체를 사용합니다. 실제 선택 DB 이름·경로는 웹 화면에서 확인합니다. 수동으로 다른 DB를 열었더라도 `AlmondDashboard`를 다시 실행하면 현재 문서 DB로 돌아갑니다. 오류 화면에서는 **현재 문서 DB 다시 열기**를 사용할 수 있습니다. 일반 패널 숨김·표시는 현재 조회 상태를 유지합니다.

RHP 소스 수정·빌드·등록·실제 로드는 별개입니다. 개발 워크트리를 Rhino에 등록하지 않으며, 배포 절차는 [저장소 지침](../../../../AGENTS.md)을 따릅니다.

## 저장된 맥락 읽기

- **File 목록**: DB에 기록된 프로젝트 파일과 연결된 Scene·Holon·Phase·Task를 표시합니다. Holon 등의 모델 관계를 위해 식별 정보가 저장된 파일도 표시할 수 있습니다. Phase나 Scene에서 파일을 직접 선택할 때는 프로젝트 카탈로그에 등록된 파일을 사용합니다.
- **Scene 조회**: 장면의 Holon·객체 이름 기록·Task를 읽습니다.
- **Holon 조회**: 저장된 이름·Scene·부모 Holon·객체 수 요약·등록 상태를 읽습니다. Rhino의 실시간 형상 검사가 아닙니다.
- **Phase**: Phase별 Task와 Phase 미지정 작업을 읽습니다.
- **Task**: 목표·Scope·파일·Phase·Scene, 관계 유형을 구분한 인접 작업, 현재 Loop의 Step을 읽습니다.
- **Step**: 소속 Task와 현재 Loop의 상태·판단 기록·설계 근거·입출력 참조를 읽습니다. UUID인 `step_id`와 `step_type`·표시 이름은 구분합니다.

Task·Step의 파일명·Phase·Scene 드롭다운은 AND로 적용됩니다. 파일 연결은 Phase의 여러 파일 및 실제 Scene 연결을 사용합니다. 검색·선택·필터·펼침은 같은 브라우저 세션에서 DB별로 보관합니다. 다른 조회로 이동하거나 새로고침해도 해당 맥락으로 돌아옵니다. 다른 DB의 상태와 섞지 않습니다.

Step 왼쪽 화살표를 누르면 같은 자리에서 기록을 펼칩니다. 항목 이름의 상세 버튼은 팝업을 열며 **닫기**, **Escape**, 팝업 바깥 클릭으로 닫습니다. 팝업 내부를 클릭하면 유지합니다.

새로운 일반 DB를 열어도 원시 테이블 목록이나 내부 테이블은 표시하지 않습니다. 지원되는 도메인 저장 구조가 없는 경우 안내합니다. DB의 테이블·뷰를 숨기려고 삭제하거나 migration하지 않습니다.

## Rhino dock와 웹 레이아웃

Task 헤더의 왼쪽은 Phase 값 → 파일명 → Task 제목의 세로 순서입니다. 오른쪽은 상태·REV를 윗줄에, 큰 LOOP를 그 아래에 둡니다. 메인·관련 Task 카드 모두 같은 배치를 사용합니다. Step은 `kind`를 왼쪽에, `loop_no`와 `step_id`를 오른쪽에 표시합니다. Task 본문·Step·여섯 도메인의 상세 팝업은 같은 항목/값 표시를 사용합니다. 원래 field 이름은 큰 굵은 글자로 유지하며 본문 값은 흰색 박스로 구분합니다. JSON 목록과 URL을 포함한 저장값은 그대로 읽습니다.

Task는 파일·Phase·Scene·검색 조건에 맞는 드롭다운에서 한 개를 선택합니다. 관련 Task의 관계 유형과 선택·비교 기능은 함께 유지됩니다. 선택한 Task는 같은 DB에서 탐색·새로고침 후에도 복원됩니다. Phase·Scene 페이지에서는 파일 필터를, Holon 페이지에서는 파일+Scene 필터를 조합할 수 있습니다.

Phase 값은 파일명 위에 크게 표시하며, Step 전체 기록 링크는 오른쪽 아래에 둡니다. `takeaways`, `design_rationale`, `input_refs_json`, `output_refs_json`은 원래 field 이름과 세로 배치를 사용합니다. 유효한 JSON 참조는 원래 값과 URL을 목록으로 읽으며 중괄호·대괄호 dump로 표시하지 않습니다. 표시 한도를 넘거나 JSON이 유효하지 않은 저장 문자열은 원문과 제한 안내를 유지합니다.

standalone 웹과 Rhino 패널은 같은 읽기 전용 화면을 사용합니다. 넓은 웹에서는 왼쪽 탐색과 Task 나란히 비교를 유지합니다. 900px 이하에서는 여섯 도메인을 상단 탐색으로 모으고 File·Scene·Holon·Phase 목록을 필드 이름이 붙은 카드로 바꿉니다. 긴 참조는 줄바꿈하고 본문을 세로로 스크롤합니다.

좁은 화면의 파일·Phase·Scene 필터와 관련 Task 비교는 처음에 접혀 있습니다. 제목을 눌러 펼치며 필터 적용 개수와 펼침 선택은 탐색 후에도 유지됩니다. 460px 이하에서는 탐색을 두 줄로 배치합니다. 패널 크기에서의 브라우저 검증은 실제 Rhino RHP 로드·패널 실행 검증과 별개입니다.

## 읽기 계약

선택한 기존 파일을 `mode=ro`·`query_only=ON`으로 엽니다. `AlmondStore` 초기화나 migration, DB 생성·편집 API를 호출하지 않습니다. 기존 호환 뷰도 파일에 남아 있으면 보존합니다. `immutable`을 사용하지 않아 커밋된 WAL 자료를 포함합니다.

현재 관계 구조가 있으면 그 구조만 사용합니다. 비었거나 불완전한 관계를 과거 JSON·호환 자료로 보충하지 않습니다. 현재 Loop 기록이 없으면 이전 회차의 상태·판단을 현재 값으로 가져오지 않습니다. 비어 있는 내용은 **미기록**, 실제 없는 관계는 **미등록**으로 구분합니다. 저장되지 않은 판단·객체 이름·목표는 만들지 않습니다.

산출물 참조는 저장된 문자열로 표시합니다. 외부 이미지·도면·모델 파일 자체를 DB가 포함한다는 뜻이 아니며 해당 경로의 파일을 자동으로 열지 않습니다.

조회는 약 2초, 목록은 20개 단위, 한 부모의 하위 기록은 200개, 관계 탐색은 2,000개로 제한하며 생략을 알립니다. 긴 값은 셀당 8,192자까지 표시합니다. 각 요청은 짧은 읽기 트랜잭션으로, 전체 화면이 하나의 고정 스냅샷은 아닙니다. 잠금 오류가 나면 잠시 후 새로고침합니다. 다른 연결의 잠금을 해제하지 않습니다.

서버는 `127.0.0.1`에서 실행하며 실행별 토큰과 Host/Origin 검사를 사용합니다. 자료를 외부 서버에 올리거나 임의 SQL을 실행하는 UI는 없습니다.

## 개발 검사

[Dashboard 작업 지침](AGENTS.md)과 [개발 검사 안내](../../../../tests/README.md)를 따릅니다. 개발 검사는 일회용 DB와 host 대역을 사용하며 Rhino·RhinoCore를 실행하거나 연결하지 않습니다.

```powershell
./src/mcp/run_tests.ps1 -Development -TestArgs @('-q', '-k', 'dashboard')
dotnet run --project src/rhp/Asset_Panel/tests/DashboardHostContracts -c Release
node --check src/mcp/runtime/dashboard/web/app.js
node --check src/mcp/runtime/dashboard/web/domain.js
```

브라우저 검사는 개발용 Playwright가 필요합니다. 런타임 의존성에는 추가하지 않습니다. 개발용 위치에 Playwright를 준비하고 해당 디렉터리를 지정한 뒤 실행합니다.

```powershell
$env:PLAYWRIGHT_MODULE = '<개발용 node_modules>\playwright'
node src/mcp/tests/runtime/dashboard_browser.cjs
```

브라우저 검사는 임시 DB·자체 서버로 여섯 조회, 원시 UI 미노출, 현재 Step 판단, 필터·펼침 복원과 팝업 닫기를 확인합니다. RHP의 경로·중복 실행·주소 검증·실패·종료 계약은 [Dashboard host fixture](../../../rhp/Asset_Panel/tests/DashboardHostContracts/README.md)를 따릅니다. 이 fixture의 SDK 컴파일은 실제 Rhino 패널 로드 검증과 다릅니다.
