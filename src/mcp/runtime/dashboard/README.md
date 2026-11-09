# Almond DB Dashboard

SQLite 파일을 선택하면 **그 파일의 현재 구조**로 테이블·뷰·열·외래키를 읽고,
자료 표를 보여 주는 로컬 읽기 전용 초안입니다.
Almond의 `.almond/scene.sqlite3`뿐 아니라 다른 SQLite DB도 열 수 있습니다.
테이블명이나 열명을 미리 등록할 필요가 없습니다.

## 현재 Dashboard 워크트리에서 실행

작업 워크트리는 `C:\TOOL\Rhino\mcp\almond-mcp\data\worktrees\DashBoard`입니다.
PowerShell의 현재 폴더와 관계없이 아래 명령을 그대로 실행하면 이 워크트리의 프로그램이 열립니다.

```powershell
& 'C:\TOOL\Rhino\mcp\almond-mcp\data\worktrees\DashBoard\src\mcp\runtime\Almond DB Dashboard.cmd'
```

파일 선택 창에서 조회할 SQLite DB를 고르면 브라우저가 열립니다.
실행기는 설치된 PowerShell 7(`pwsh.exe`)을 먼저 찾고, 없으면 Windows 기본 PowerShell을 사용합니다.
필요한 경로는 실행기 안에서 설정하므로 시스템 `PATH`를 직접 바꿀 필요가 없습니다.
Git의 공통 저장소 정보에서 원본 리포를 찾고 그곳의 Python을 사용합니다.
현재 Python은 `C:\TOOL\Rhino\mcp\almond-mcp\.venv\Scripts\python.exe`이고,
Dashboard 소스는 위 `DashBoard` 워크트리의 `src/mcp/runtime/dashboard`에서 읽습니다.
워크트리가 원본과 떨어진 위치에 있어도 같은 방식으로 연결합니다.

자동 환경 선택 원본과 경로 변수 사용법은 [auto-venv 안내](../auto-venv/README.md)에 있습니다.
`AUTO_VENV_REPO_ROOT`는 원본 리포, `AUTO_VENV_WORKTREE_ROOT`는 작업 워크트리,
`AUTO_VENV_PYTHON`은 원본 Python의 절대경로입니다.
실행기는 호출한 셸의 환경과 관계없이 Git으로 원본 경로를 다시 확인합니다.

프로그램 소스는 `src\mcp\runtime\dashboard`에 있습니다.
작업 지침은 [AGENTS.md](AGENTS.md)를 따릅니다.
종료는 실행한 창에서 **Ctrl+C**입니다.

실행에 필요한 `.cmd`·`.ps1`·Python 소스와 문서는 Git으로 추적합니다.
Python 환경과 로컬 DB는 Git 추적에서 제외합니다.
Dashboard 실행은 원본 리포에 이미 구성된 환경을 참조하며 워크트리에 venv를 복사하지 않습니다.

## 열어 보기

1. 이 체크아웃의 `src/mcp/runtime/Almond DB Dashboard.cmd`를 더블클릭합니다.
2. 파일 선택 창에서 DB를 선택합니다. 확장자 없는 `DB`는 파일 형식을 **All files**로 바꿔 선택합니다.
3. 자동으로 열린 브라우저에서 왼쪽 테이블을 선택합니다.
4. 다른 DB는 오른쪽 위 **파일 열기**를 누르고 파일 선택 창에서 선택합니다. 취소하면 현재 DB를 유지합니다.
5. 종료할 때 실행 창에서 **Ctrl+C**를 누릅니다. 브라우저 탭만 닫으면 서버는 유지됩니다.

더블클릭 실행기는 Git으로 확인한 원본 리포에서 `.venv`, `venv`,
`data/development/.venv`, `src/engine/.venv` 순서로 기존 Python 환경을 선택합니다.
원본 경로나 환경을 찾을 수 없으면 오류로 안내합니다.

PowerShell에서 직접 실행할 수도 있습니다. 아래 명령은 저장소 루트 기준입니다.

```powershell
# 원하는 DB 지정. 파일을 수정하거나 초기화하지 않음
./src/mcp/runtime/dashboard.ps1 -Database 'C:\프로젝트\.almond\scene.sqlite3'

# 파일 선택 버튼이 있는 화면부터 시작
./src/mcp/runtime/dashboard.ps1
```

`-Development`를 명시하면 원본 리포의 `data/development/.venv`를 사용합니다.
기본 실행과 이 옵션 모두 프로그램 소스는 명령을 실행한 워크트리에서 읽습니다.
Dashboard에는 예시 DB 생성 옵션을 포함해 DB를 작성하는 기능이 없습니다.
기존 SQLite 파일만 선택하여 조회합니다.
`-NoBrowser`를 주면 브라우저를 자동으로 열지 않고 실행 창에 주소만 표시합니다.
기본 포트는 빈 포트로 자동 선택하며 `-Port 8765`처럼 지정할 수도 있습니다.

## 화면에서 할 수 있는 일

### Scene·ontological_holon·Phase·Task 조회

DB를 열면 상단에서 네 종류의 조회 탭과 **전체 테이블**을 선택합니다.
각 탭은 선택한 파일에 필요한 테이블이 있을 때 사용할 수 있습니다.
일반 SQLite 파일도 기존 **전체 테이블**의 검색·필터·구조 화면으로 계속 조회합니다.

| 탭 | 표의 구성과 이동 |
| --- | --- |
| Scene 조회 | Scene 이름, 연결된 ontological_holon 이름, 기록된 객체 이름, Scene의 Task 이름 목록. Holon 이름을 누르면 해당 ID의 Holon 조회로 이동합니다. |
| ontological_holon 조회 | 이름을 먼저 보여 주고 Scene·부모 Holon·기록된 객체 이름·저장된 객체 수·등록 상태를 표시합니다. |
| Phase | Phase 이름 셀을 병합하고, 그 Phase를 참조하는 Task를 한 행씩 표시합니다. 같은 이름의 다른 Phase는 합치지 않습니다. Task가 없는 Phase와 Phase 미지정 Task도 표시합니다. |
| Task | 기존 `generation_plans`를 Task 단위로 표시합니다. 이름·revision, Task 목표, scope 셀을 Step 행 수만큼 병합하며, Step 이름·상태·목표는 저장된 position 순서로 보여 줍니다. |

표의 행을 누르거나 키보드 Enter/Space를 누르면 상세가 열립니다. Step 상세에는 소속 Task의
revision과 해당 Step의 입력·출력 기록 등이 표시됩니다. 링크로 선택한 항목은 ID로 구별하고,
**전체 목록**을 누르면 선택 범위를 해제합니다. 객체 이름은 링크로 만들지 않습니다.

현재 Almond DB는 Holon의 의미와 객체 개수 요약을 저장하지만 개별 객체 이름을 저장하지 않습니다.
Step에도 별도의 목표 필드가 없습니다. 이 값은 **미기록**으로 표시하며 Task 목표를 Step 목표로
대체하지 않습니다. 선택한 DB에 `document_objects.name` 또는 Holon의 `object_names_json`,
Step의 `goal`/`objective`가 실제로 있으면 그 기록을 읽습니다. Rhino에 연결하거나 새 필드를 추가하지 않습니다.

부모 항목을 페이지당 최대 20개 읽으며 Step·Task 그룹을 페이지 중간에서 나누지 않습니다.
한 부모의 하위 행은 최대 200개, 관계 링크는 조회별 최대 2,000개로 제한하고 생략이 있으면 알립니다.
상세의 긴 값은 기존과 같이 8,192자까지 읽고 일부 표시 여부를 보존합니다.

조회 도구·표 라이브러리와 SQLite 확장자에 대한 [조사 결과](research-domain-views.md)를 먼저 확인했습니다.
기존 Python `sqlite3`·로컬 HTTP 인증·상세 대화상자와 HTML 표준 `rowspan`을 재사용합니다.
추가 런타임 패키지나 외부 CDN은 사용하지 않습니다.

### 전체 테이블 조회

넓은 화면에서는 테이블 제목·탭·자료 검색을 한 줄에 표시합니다. 좁은 화면에서는
순서대로 줄을 바꿉니다. 열 자료형은 열 제목 오른쪽에 표시하고, 값 필터는 그 아래에 둡니다.

- **자료 보기**: 페이지당 50행, 문자열 검색, 열 제목을 눌러 오름차순/내림차순 정렬.
  열 제목 아래에서 값을 선택해 여러 열을 동시에 필터합니다. 검색과 열 필터는 함께 적용되며,
  정렬·페이지 이동 중에도 유지됩니다. **필터 해제**로 모든 열 조건을 지웁니다.
  값 하나라도 100자를 넘는 열과 BLOB이 있는 열은 드롭다운을 표시하지 않습니다.
  옵션은 전체 열의 고유값이며 100개씩 **값 100개 더 보기**로 이어 읽습니다.
  자료를 다시 조회할 때 값 목록도 다시 읽습니다. 현재 목록에 없는 선택값은 **적용 중인 조건**으로 구분합니다.
  NULL·빈 문자열·숫자·문자열은 구분합니다. 행을 누르면 필드별 상세와 펼친 JSON을 확인합니다.
- **테이블 접기**: 왼쪽 일반 목록 위의 **접은 테이블** 영역으로 끌면 접습니다. 목록을 펼쳐
  선택하거나 아래 일반 목록으로 다시 끌어 복원합니다. 각 테이블의 화살표 버튼도 같은 동작을 합니다.
  접은 목록은 DB별로 이 브라우저에 저장됩니다.
- **구조와 관계**: 열 타입·기본값·PK·NULL 명시 제약, 원본 CREATE SQL, 들어오고 나가는 외래키 연결.
  연결된 테이블 이름을 누르면 자료 보기의 해당 키 열로 이동하고 강조합니다.
  복합 외래키는 하나로 묶고 관련된 모든 열을 강조합니다.
- **구조 새로고침**: 현재 DB의 구조와 자료를 다시 읽습니다. 새 테이블·새 열·변경된 관계가 자동 반영됩니다.
  별도 schema 설정이나 코드 수정은 필요 없습니다. 검색·정렬·열 필터·페이지는 초기화하고
  드롭다운 옵션도 다시 읽습니다.
- SQLite의 FTS/rtree shadow 테이블과 `sqlite_*`는 기본 숨김이며, 왼쪽 체크박스로 표시할 수 있습니다.

## 읽기 범위와 제한

- 지원 형식은 SQLite입니다. 다른 DB 서버·암호화 DB·Rhino `.3dm` 자체를 여는 기능은 없습니다.
- `mode=ro`와 `query_only`로 열고 AlmondStore 초기화·migration·Rhino 연결을 호출하지 않습니다.
  SQL 입력·수정·저장·잠금 해제 기능도 없습니다.
  `_component_records` 같은 기존 뷰의 행은 원본 테이블의 조회 결과이며 별도 복제 자료가 아닙니다.
  Dashboard는 기존 뷰도 그대로 읽으며 삭제하거나 migration하지 않습니다. `immutable`을 쓰지 않아 커밋된 WAL도 읽습니다.
  SQLite가 WAL을 읽기 위해 기존 공유 메모리를 사용하는 동작은 SQLite의 기본 계약을 따릅니다.
- 다른 작업이 DB를 독점 잠근 경우 오류 안내 후 사용자가 다시 조회합니다. 기존 연결을 종료하지 않습니다.
  긴 조회는 약 2초 후 중단하며, 느린 검색·정렬은 해제하고 다시 조회할 수 있습니다.
- 표는 처음 128개 열, 텍스트는 셀당 8,192자까지 표시합니다. 생략 여부를 화면에 표시합니다.
  BLOB은 크기와 처음 32바이트의 16진수만 상세에 표시합니다. 큰 정수는 문자열로 보존합니다.
- 키 없는 표·중복값 정렬 또는 동시에 갱신되는 DB에서는 페이지 사이 순서·행 위치가 바뀔 수 있습니다.
  각 요청은 짧은 읽기 트랜잭션이며, 전체 화면을 고정한 스냅샷은 아닙니다.
- 관계는 DB에 **선언된 외래키**만 표시합니다. JSON 안의 의미 관계나 3D 형상을 추정하지 않습니다.
  사용자 모델의 설계·구조 검증을 실행하는 기능이 아닙니다.
- 브라우저와 서버는 이 컴퓨터의 `127.0.0.1`에서만 통신합니다. 자료를 외부 서버로 업로드하지 않습니다.
  API는 실행별 토큰과 Host/Origin 검사를 사용합니다. 표시된 주소는 실행 중에만 유효합니다.

## 개발과 검사

구현은 이 폴더의 Python 표준 라이브러리와 `web/`의 정적 HTML/CSS/JS입니다.
RHP에 들어가는 기존 Asset Panel과 독립된 화면이므로 RHP 빌드·등록·Rhino 재시작이 필요하지 않습니다.
기존 MCP 도구 schema·source fingerprint 대상·worker 생명주기도 바꾸지 않습니다.

```powershell
./src/mcp/run_tests.ps1 -Development -TestArgs @('-q', '-k', 'dashboard')
node --check src/mcp/runtime/dashboard/web/app.js
```

검사는 일회용 SQLite만 사용합니다. 읽기 전용·WAL·잠금 보존·동적 schema·따옴표 있는 이름·
JSON/큰 셀·실제 Almond schema 읽기·느린 쿼리 제한·로컬 HTTP 접근을 확인합니다.
열 필터의 조합·자료형·100자 경계·옵션 페이지와 파일 선택의 성공·취소·실패도 확인합니다.
도메인 조회는 중복 이름의 ID 구별, 다중 Scene 관계, Phase/Task 그룹, Step 정렬·상세,
미기록 값 구별, 그룹 단위 페이지·조회 제한, DB 바이트 보존과 HTTP 인증을 검사합니다.
브라우저 화면은 별도 headless 브라우저의 스크린샷으로 검수할 수 있습니다.

현재 관계 테이블이 있으면 그 관계를 사용하며, 비어 있어도 과거 호환 뷰·JSON·단일 Scene 필드로 관계를 보충하지 않습니다. 과거 구조는 현재 관계 구조가 없는 DB에서만 읽습니다.

현재 Loop 스키마에서는 Task의 `loop_no`와 일치하는 `generation_loop_steps`에서 Step 상태·입출력을 읽습니다. 현재 Loop에 기록이 없거나 저장 구조가 불완전하면 미기록으로 표시합니다. `loop_no`가 없는 기존 DB에서는 Step 직접 저장 필드를 읽을 수 있습니다.
