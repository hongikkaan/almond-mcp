# Dashboard 도메인 조회 화면을 위한 재사용 조사

조사일: 2026-11-04 (UTC). 범위: Scene조회 / ontological_holon조회 / Phase / Task 탭, 부모 셀의 세로 병합, 특정 holon으로 이동, 행·step 상세, 로컬·오프라인 제공. 공식 문서·공식 저장소·표준만 근거로 삼았다. 이 문서 작성 외에 구현, 의존성 설치, 서비스 실행, 실제 모델·DB 접근은 하지 않았다.

## 권고

**이번 범위에는 기존 Python `sqlite3` 조회 계층과 HTML `<table>`을 재사용하고, Phase·Task 표에 표준 `rowspan`을 적용하는 안을 권고한다.** 이미 있는 읽기 전용 연결, 조회 제한, 행 상세, 관계 이동, 로컬 정적 파일 제공을 유지하면서 필요한 도메인 JOIN과 표시만 더할 수 있다. 이는 아래 확인 사실에 기초한 설계 판단이다. 기존 코드는 [database.py](database.py), [server.py](server.py), [web/app.js](web/app.js), [web/index.html](web/index.html), [README.md](README.md)에서 확인했다. HTML의 실제 세로 병합은 브라우저 표준 기능이다. [HTML Standard](https://html.spec.whatwg.org/multipage/tables.html#attr-tdth-rowspan)

외부 도구도 활용할 곳이 있다. **Datasette는 별도 범용 DB 조사 화면**, **sqlite-utils는 개발용 구조·쿼리 조사**, **AG Grid Community는 정렬·필터·열 제어·가상 스크롤까지 확대할 때 채택 가능한 표 위젯**이다. AG Grid의 현재 공식 row spanning 예제는 `ag-grid-community`에서 `CellSpanModule`을 가져온다. 이 병합 기능을 Enterprise 전용으로 분류하면 안 된다. TanStack 최신 v9도 실제 cell spanning을 제공하므로 과거 v8의 기능 설명을 그대로 적용하면 안 된다. [Datasette](https://docs.datasette.io/en/stable/), [sqlite-utils](https://sqlite-utils.datasette.io/en/stable/python-api.html), [AG Grid row spanning](https://www.ag-grid.com/javascript-data-grid/row-spanning/), [TanStack cell spanning](https://tanstack.com/table/latest/docs/framework/react/guide/cell-spanning)

## 1. `.sqlite3`, `.db`, 확장자 없는 `DB`의 의미

SQLite는 데이터베이스 이름에 특정 확장자를 요구하지 않으며 확장자가 없어도 동작한다. 따라서 `scene.sqlite3`, `project.db`, `DB`라는 이름만으로 서로 다른 저장 형식이라고 판단할 수 없다. `.sqlite3`는 SQLite 파일임을 사람이 알아보기 쉬운 관례이지 별도 변환 단계가 필요한 형식명이 아니다. 확장자를 바꾸는 작업은 이 조회 기능에 필요하지 않다. [SQLite naming rules](https://www.sqlite.org/shortnames.html), [SQLite as an application file format](https://www.sqlite.org/aff_short.html)

일반 SQLite 3 파일은 처음 16바이트의 `SQLite format 3` 문자열과 NUL 바이트로 식별하며, 파일 안에는 테이블·인덱스·스키마 등이 들어간다. 조회 가능 여부는 확장자 필터보다 SQLite로 정상적으로 열어 스키마를 읽을 수 있는지가 기준이다. 기존 `Database.__init__`도 파일 존재를 확인한 뒤 `sqlite_schema` SELECT를 실행한다. [SQLite file format](https://www.sqlite.org/fileformat.html#the_database_header), [database.py](database.py)

WAL 사용 중에는 커밋 내용이 `-wal`에 있을 수 있고 `-shm`도 연관된다. 라이브 DB를 파일 하나만 복사·이름 변경해도 동일한 최신 상태가 보장된다고 전제하지 않는다. `mode=ro`는 읽기 전용이고, `immutable=1`은 외부 변경조차 없다고 선언하여 잠금·변경 감지를 생략한다. 갱신되는 모델 DB에 후자를 적용하지 않는 현재 방식을 유지한다. 읽기 전용 WAL 접근은 보조 파일의 존재·읽기 권한 또는 생성 가능 여부 등 SQLite 조건을 따른다. [SQLite WAL](https://www.sqlite.org/wal.html#read_only_databases), [SQLite URI parameters](https://www.sqlite.org/uri.html#uri_query_string)

## 2. 기존 DB 조회 도구·라이브러리

| 후보 | 확인된 재사용 기능 | 이번 네 탭에 남는 일 | 실행·운영 비용 / 판단 |
|---|---|---|---|
| 기존 Python `sqlite3` + `Database` | SQL JOIN·바인딩, 구조/FK 읽기, `mode=ro`, `query_only`, 제한된 행·셀 크기·시간. 기존 API와 동일한 DB 선택·보안 경계 사용 | Scene·holon·Phase·Task의 의미와 표시 순서를 명시하는 조회, 원하는 부모·자식 표시 | 새 Python 의존성 없음. **현재 백엔드 권고**. [Python docs](https://docs.python.org/3/library/sqlite3.html#how-to-work-with-sqlite-uris), [database.py](database.py) |
| Datasette | SQLite를 웹 표·정렬·필터·행 상세·FK 레이블·역참조·JSON API로 제공. 파라미터 canned query는 DB에 view를 만들지 않고도 JOIN 조회를 재사용 가능 | 네 전용 탭, 정확한 부모 셀 병합, 기존 Dashboard의 특정 탭 선택은 custom page/template/JS로 연결 필요 | 독립 ASGI 웹앱·서버 운영과 인증/실행기 통합이 추가됨. **별도 범용 조사 도구로 가치가 큼**. [pages](https://docs.datasette.io/en/stable/pages.html), [JSON/FK](https://docs.datasette.io/en/stable/json_api.html#expanding-foreign-key-references), [canned queries](https://docs.datasette.io/en/stable/sql_queries.html#canned-queries) |
| sqlite-utils | `db.query()`, 열·PK·FK·인덱스·스키마 introspection, CLI JSON/표 출력 등 | 웹 UI·탭·셀 병합·화면 이동은 제공하지 않으므로 직접 연결 | Python `sqlite3`를 감싸는 유틸리티. **개발 중 스키마·쿼리 점검에 사용 가능**, 현재 짧은 조회 계층을 교체할 이익은 제한적. [API](https://sqlite-utils.datasette.io/en/stable/python-api.html), [CLI](https://sqlite-utils.datasette.io/en/stable/cli.html) |
| 공식 `sqlite3` CLI | `-readonly`, `.schema`, `.tables`, 표/JSON 출력과 직접 SELECT | 웹 화면은 없음 | 개발자가 복제한 개발 DB의 관계·JOIN 결과를 점검할 때 활용 가능. 설치 여부는 조사하지 않았고 실행하지 않았다. [CLI](https://www.sqlite.org/cli.html) |

Datasette는 도메인 전용 화면을 포기해야 하는 도구가 아니다. 정적 파일과 Jinja 템플릿, custom page를 지원하므로 네 탭을 그 위에 만들 수도 있다. 다만 기존 표·상세·보안·실행기를 갖춘 이 프로젝트에서는 교체·이식 작업이 추가된다는 판단이다. 현재 Dashboard와 별개로 임시 개발 DB를 살펴보는 용도라면 자동 행 URL/FK 역참조와 canned query를 바로 활용할 수 있다. [custom pages/templates/static files](https://docs.datasette.io/en/stable/custom_templates.html)

읽기 전용이라는 이름만으로 기존 보호가 자동 승계되는 것은 아니다. Datasette는 기본 인증이 없고 임의 읽기 SQL을 제공하므로, 현재 실행별 token·Host/Origin 검증과 동등한 제한을 별도로 구성해야 한다. immutable 모드는 변경되지 않는 DB에 한정한다. writable canned query/쓰기 플러그인을 사용하지 않는 구성도 확인해야 한다. [authentication defaults](https://docs.datasette.io/en/stable/authentication.html), [immutable mode](https://docs.datasette.io/en/stable/performance.html#immutable-mode), [writable canned query opt-in](https://docs.datasette.io/en/stable/sql_queries.html#writable-canned-queries), [server.py](server.py)

sqlite-utils는 경로로 생성하면 보통 `sqlite3.connect(path)`를 사용하며 DB가 없으면 생성할 수 있다. 이미 읽기 전용으로 연 연결도 받을 수 있지만, 조사한 4.2.1 소스의 기본 생성자는 `recursive_triggers` 설정 및 플러그인 connection hook을 실행한다. 런타임에서 사용한다면 명시적으로 보호된 연결과 생성자 옵션·거래 처리 호환성을 검토해야 한다. 단순 도메인 SELECT를 위해 현재 연결을 기본 생성자로 바꾸는 안은 권고하지 않는다. [공식 constructor source](https://raw.githubusercontent.com/simonw/sqlite-utils/main/sqlite_utils/db.py)

## 3. 화면 표 라이브러리 비교

아래의 “링크 가능”은 위젯이 링크/클릭을 지원한다는 뜻이다. 어느 후보도 Almond의 holon ID와 탭 의미를 스스로 알아내지는 않는다. 연결 대상 ID·선택 상태는 앱이 공급해야 한다.

| 후보 | Phase 셀 / Task 이름·revision 세로 병합 | 링크·행/step 상세 | 오프라인·이식비용 | 판단 |
|---|---|---|---|---|
| 표준 HTML table + 기존 JS | `rowspan`으로 정확히 표현. 같은 부모의 첫 행에만 셀을 만들고 덮인 셀은 생략 | 기존 행 상세·키보드 Enter/Space·탭 전환·관계 이동을 확장. 링크는 DOM anchor/button으로 처리 | 기존 JS/CSS만 사용, 추가 패키지·빌드 없음 | **이번 요구의 기본안**. [HTML Standard](https://html.spec.whatwg.org/multipage/tables.html#attr-tdth-rowspan), [app.js](web/app.js) |
| Tabulator 6.x | 공식 문서에서 요청과 같은 **본문 세로 병합 API를 확인하지 못함**. `groupBy`는 별도 접이식 그룹 헤더. rowspan을 가진 HTML 표 가져오기도 지원하지 않는다고 명시 | link formatter, `rowClick`/`cellClick`으로 연결 가능. 일반 탐색 표의 필터·정렬·페이지 기능 재사용 가능 | 로컬 prebuilt JS+CSS를 바로 포함 가능. 그룹 헤더로 바꾸면 요구 표시와 달라짐 | **Scene/holon의 큰 일반 표 후보**. 병합 핵심 표의 우선 후보는 아님. [group](https://www.tabulator.info/docs/6.x/group/), [import restriction](https://www.tabulator.info/docs/6.x/data/), [link](https://www.tabulator.info/docs/6.x/format/#format-link), [events](https://www.tabulator.info/docs/6.x/events/), [install](https://www.tabulator.info/docs/6.x/install/) |
| TanStack Table 최신 v9 | `cellSpanningFeature`, 열 `spanRows`, `cell.getRowSpan()` 제공. 덮인 셀을 렌더러가 생략하며 HTML rowspan 설정. 최종 정렬/필터/페이지의 인접 행 기준으로 재계산 | headless이므로 DOM·링크·상세·스타일을 앱에서 구현. React 필수 아님, 공식 vanilla core 예제 있음 | `@tanstack/table-core` 및 ESM 의존성의 로컬 번들/모듈 제공 필요. 기존 JS의 상태·렌더 구조를 맞추는 작업 | **상태 관리/복잡한 표 기능을 선택적으로 재사용할 때 후보**. 이번 작은 병합에만 쓰기에는 연결 코드가 남음. [span](https://tanstack.com/table/latest/docs/framework/react/guide/cell-spanning), [vanilla](https://tanstack.com/table/latest/docs/framework/vanilla/quick-start) |
| AG Grid Community | `CellSpanModule`, `enableCellSpan`, `spanRows`로 인접 행 병합. callback으로 병합 조건 지정 가능. 이름·revision 열을 같은 task identity 기준으로 설정 가능 | custom cell renderer의 DOM/링크·버튼 및 `rowClicked`/`cellClicked`를 기존 상세와 연결 가능 | vanilla JS 지원, 로컬 배포 bundle 제공. 표 DOM·테마·상태 통합 및 현재 CSP 검토 필요 | **외부 라이브러리를 실제 채택한다면 가장 직접적인 완성형 대안**. [span](https://www.ag-grid.com/javascript-data-grid/row-spanning/), [cell renderer](https://www.ag-grid.com/javascript-data-grid/component-cell-renderer/), [events](https://www.ag-grid.com/javascript-data-grid/grid-events/), [install](https://www.ag-grid.com/javascript-data-grid/installation/) |

Tabulator의 `rowFormatter`나 CSS로 억지로 부모 셀을 겹쳐 보이게 하면 가상 스크롤·행 높이·필터·정렬과 함께 다시 구현·검증해야 한다. 이번 조사에서는 그러한 우회 구현이 표준 rowspan과 동등하다고 보증하지 않는다. “공식 API를 찾지 못함”을 라이브러리의 모든 사용자 확장까지 불가능하다는 주장으로 확대하지 않는다.

AG Grid의 **Master/Detail은 Enterprise 기능**이다. 현재 요구인 “행/step을 눌러 기존 상세 대화상자를 열기”는 별도 그리드를 행 아래에 삽입하는 Master/Detail과 구분된다. Community 클릭 이벤트를 기존 상세에 연결하는 안으로 요구를 충족할 수 있다는 설계 판단이며, 이 때문에 Enterprise를 도입할 필요는 없다. [Master/Detail](https://www.ag-grid.com/javascript-data-grid/master-detail/), [click events](https://www.ag-grid.com/javascript-data-grid/grid-events/)

## 4. 라이선스, 의존성 크기, 로컬 배포

| 후보 | 확인한 라이선스·의존성 | 자산·운영 비용 |
|---|---|---|
| 기존 SQLite/Python/HTML | SQLite 원본은 public domain. 현재 Python 표준 라이브러리 사용을 계속하므로 새 Python 패키지 없음 | 기존 로컬 서버·파일만 재사용. [SQLite copyright](https://www.sqlite.org/copyright.html) |
| Datasette stable 0.65.5 | Apache-2.0. 해당 태그 `setup.py`는 Python >=3.10 및 20개 직접 runtime 요구사항을 선언(Jinja2, Uvicorn, HTTPX, Pluggy 등) | 프런트엔드 단일 파일만의 교체가 아닌 Python 웹앱 추가. 패키지·라이선스·서버 lifecycle 유지 필요. [manifest](https://raw.githubusercontent.com/simonw/datasette/0.65.5/setup.py), [license](https://raw.githubusercontent.com/simonw/datasette/0.65.5/LICENSE) |
| sqlite-utils 조사 소스 4.2.1 | Apache-2.0. `pyproject.toml`은 Python >=3.10 및 7개 직접 의존성 선언(click, click-default-group, pluggy, python-dateutil, sqlite-fts4, tabulate, pip) | 웹 UI가 아니며 라이브러리·CLI용. [manifest](https://raw.githubusercontent.com/simonw/sqlite-utils/main/pyproject.toml), [license](https://raw.githubusercontent.com/simonw/sqlite-utils/main/LICENSE) |
| Tabulator | MIT. 조사한 master 6.7.1 manifest에는 일반 dependencies 항목이 없고 개발 의존성이 있음. XLSX/PDF export·일부 날짜 기능은 별도 라이브러리 선택 필요 | 공식 6.x 설치 문서는 core를 120kb라고 설명하나 압축·측정 조건은 적지 않음. 전체 번들이나 다른 후보의 gzip 크기와 같은 기준으로 비교하지 않았다. 로컬 JS+CSS 및 선택 모듈 지원. [manifest](https://raw.githubusercontent.com/olifolkerd/tabulator/master/package.json), [license](https://raw.githubusercontent.com/olifolkerd/tabulator/master/LICENSE), [install](https://www.tabulator.info/docs/6.x/install/), [optional dependencies](https://www.tabulator.info/docs/6.x/dependencies/) |
| TanStack Table core 조사 소스 9.3.1 | MIT. 현재 core manifest의 직접 의존성은 `@tanstack/store`. 패키지의 Node engine 표기는 >=20 | 프레임워크 전체를 추가할 필요는 없으나, bare ESM 의존성을 브라우저에 제공할 번들/모듈 전략은 필요. headless라 CSS·상세 구현은 계속 앱 소유. 번들 산출물을 배포하면 사용자에게 Node 실행을 요구할 필요가 없다는 판단. [manifest](https://raw.githubusercontent.com/TanStack/table/main/packages/table-core/package.json), [license](https://raw.githubusercontent.com/TanStack/table/main/LICENSE), [vanilla rendering](https://tanstack.com/table/latest/docs/framework/vanilla/quick-start) |
| AG Grid Community | MIT. 조사한 `latest` branch manifest는 36.2.0 beta 표기이며 `ag-stack`·`ag-charts-types` 직접 의존성 선언. 공식 문서는 36.2.0 표기 | 직접 다운로드 bundle은 JS+CSS 포함판과 noStyle판 제공. NPM 사용 시 필요한 모듈만 등록해 크기를 줄일 수 있음. 실제 도입 버전은 release tag를 고정해야 함. [manifest](https://raw.githubusercontent.com/ag-grid/ag-grid/latest/packages/ag-grid-community/package.json), [license](https://raw.githubusercontent.com/ag-grid/ag-grid/latest/packages/ag-grid-community/LICENSE.txt), [install/modules](https://www.ag-grid.com/javascript-data-grid/installation/) |

위 크기 비교는 manifest와 공식 배포 방식에 근거한 비용 분류다. 실제 설치 용량·압축 전송 바이트·메모리·성능은 측정하지 않았다. Tabulator 공식 6.x 문서의 상단은 6.5.0, 저장소 master manifest는 6.7.1이었고, AG Grid 문서 버전과 branch manifest의 beta 표기도 일치하지 않았다. `latest`/`main`/`master` 링크를 곧바로 확정 배포 버전으로 취급하지 않는다.

오프라인은 가능하지만 후보별 작업이 다르다. Tabulator/AG Grid는 검증한 prebuilt 자산을 저장소에 포함하여 기존 서버가 제공할 수 있다. TanStack은 로컬 ESM 의존성을 포함한 빌드 산출물을 제공하는 방식이 적절하다. Datasette도 패키지·정적 자산이 준비되면 로컬 실행할 수 있으나 Python 서버가 추가된다. CDN·외부 폰트는 필수 조건이 아니다. 외부 자산을 포함할 때 해당 MIT/Apache 라이선스·저작권 고지를 함께 보존하는 범위를 확인한다. [Tabulator local files](https://www.tabulator.info/docs/6.x/install/), [AG Grid direct download](https://www.ag-grid.com/javascript-data-grid/installation/), [TanStack vanilla](https://tanstack.com/table/latest/docs/framework/vanilla/quick-start), [Datasette static files](https://docs.datasette.io/en/stable/custom_templates.html#serving-static-files)

**AG Grid는 현재 CSP와 추가 연결 작업이 필요하다.** 기존 서버는 `style-src 'self'; img-src 'self'`를 설정한다. AG Grid 공식 보안 문서는 현재 테마가 CSS를 주입하므로 `styleNonce`와 페이지별 CSP nonce, SVG data URL을 위한 `img-src data:`가 필요하다고 설명한다. 문자열 expression 대신 함수 callback을 쓰면 `unsafe-eval` 요구를 피할 수 있다. 따라서 “로컬 JS 한 파일 추가만으로 현재 보호 정책 그대로 동작한다”고 단정할 수 없다. [공식 CSP 가이드](https://www.ag-grid.com/javascript-data-grid/security/), [server.py](server.py)

## 5. 구현 전에 확정할 표시·조회 계약

다음은 라이브 DB에서 확인한 결과가 아니라, 어느 표 후보를 택하더라도 필요한 설계 조건이다. 실제 테이블·열명·revision 계약은 소스 스키마를 확인하여 매핑해야 한다.

1. **부모 identity 기준 병합**: Phase 표는 같은 Phase에 속한 task 행만 병합한다. Task 표의 이름·revision은 같은 task identity와 표시 대상 revision에 속한 step들만 병합한다. 이름이 같거나 revision 숫자만 같다는 이유로 다른 task를 합치지 않는다. 라이브러리의 “같은 표시 값 자동 병합”을 그대로 켜는 것으로 도메인 계약이 완성되지는 않는다. AG Grid/TanStack 모두 사용자 병합 조건을 지원한다. [AG Grid callback](https://www.ag-grid.com/javascript-data-grid/row-spanning/#custom-row-spanning), [TanStack predicate](https://tanstack.com/table/latest/docs/framework/react/guide/cell-spanning)
2. **순서·빈 자식·페이지**: step의 저장된 순서를 명시적으로 적용하고 동순위에는 안정적인 키를 쓴다. task/step이 없는 부모도 보여 줄지 정한다. 부모가 여러 페이지로 나뉘면 각 페이지에 부모 레이블을 다시 표시하거나 부모 단위로 페이지를 자른다. 표준 rowspan은 실제 렌더한 행에만 적용되며 TanStack도 페이지 경계를 넘는 span을 만들지 않는다. [HTML table model](https://html.spec.whatwg.org/multipage/tables.html#table-model), [TanStack pagination behavior](https://tanstack.com/table/latest/docs/framework/react/guide/cell-spanning)
3. **holon 링크의 대상**: 셀에는 표시 이름과 별도로 실제 holon ID를 보존한다. 클릭하면 ontological_holon 탭을 활성화하고 해당 ID를 조회·선택한다. 현재 페이지 DOM에 보이는 이름을 검색해서만 이동하지 않는다. 링크 클릭은 부모 행의 상세 열기와 충돌하지 않게 연결한다. 이는 앱의 책임이며 라이브러리는 클릭/renderer만 제공한다. [Tabulator events](https://www.tabulator.info/docs/6.x/events/), [AG Grid renderer events](https://www.ag-grid.com/javascript-data-grid/component-cell-renderer/)
4. **기존 token·상세 재사용**: 현재 `location.hash`는 실행 token을 전달하고 sessionStorage에 저장한다. 새 탐색 상태를 추가할 때 이를 덮어쓰지 않는다. 기존 DOM 생성·텍스트 표시·행 키보드 동작·상세 대화상자와 token API 호출을 재사용하는 것이 유리하다. [app.js](web/app.js), [server.py](server.py)
5. **조회 전용 보존**: 기존 연결 컨텍스트 안에서 파라미터 SELECT/JOIN으로 읽는다. 화면 편의를 위해 모델 DB에 view·인덱스·FTS·migration을 생성하지 않는다. 새 탭에 필요한 묶음을 무제한으로 읽는 대신 조회 한도와 화면 페이지 정책을 함께 정한다. 이는 현재 데이터 읽기 계약을 유지하기 위한 권고다. [database.py](database.py), [README.md](README.md)

## 6. 채택 가능한 범위

- **바로 재사용할 기반**: 기존 `Database.connect`, schema/FK introspection, 필터/페이지/시간·셀 한도, API token·Host/Origin 검사, 표·상세 대화상자·탭 전환·관계 이동. Python sqlite3의 SQL JOIN/바인딩과 브라우저 rowspan으로 요청한 화면을 구성한다.
- **개발 조사 보조 도구**: 실제 모델과 분리한 개발용 DB가 준비될 때 sqlite-utils 또는 공식 sqlite3 CLI로 스키마·JOIN 결과를 확인한다. 범용 웹 탐색·북마크 가능한 조회·자동 FK 역참조가 필요하면 Datasette를 별도로 사용할 수 있다. 이번 조사에서는 설치·실행하지 않았다.
- **외부 표 위젯을 채택할 경우**: AG Grid Community를 먼저 검토한다. 실제 재사용 기능은 row spanning, 열 정렬·필터, 셀 링크 renderer, row/step click, 가상 스크롤이다. 기존 상세를 연결하고 로컬 자산·CSP까지 검증한다. Enterprise Master/Detail은 이번 요구의 선행조건이 아니다.
- **추가 복잡성의 근거가 생길 때**: 표 상태·기능 조합을 깊게 제어하려면 TanStack v9, Scene/holon 일반 표의 완성된 탐색 기능이 우선이면 Tabulator도 유효하다. 병합 요구만으로 프레임워크나 서버를 교체할 근거는 현재 조사에서 찾지 못했다.

이 조사 문서는 구현 승인이나 동작 검증 결과가 아니다. 확정된 것은 공식 기능·배포·라이선스와 현재 Dashboard의 재사용 지점이며, 도메인 스키마 매핑·실제 데이터 규모·브라우저 동작은 구현 단계에서 따로 확인해야 한다.