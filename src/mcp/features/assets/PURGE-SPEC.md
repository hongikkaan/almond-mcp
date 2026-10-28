# purge 작업명세서

상태: **Final — 전체 구현 승인 및 구현 가능성 검토 반영**

기준일: 2026-10-26 (Asia/Seoul). 사용자의 최신 지시는 “전체 구현하라는 말이었음. 바로 작업 진행하지 말고, 명세서에서 계획한 작업이 실제로 가능한지를 검토하고 작업명세서를 finalize한 다음 작업을 수행할 것.”이다. 이전의 전체 항목 제안 전용 제한은 이 지시로 해제됐다. 아래 기술적 한계를 숨기거나 다른 기능으로 대체하지 않는다.

## 목적과 작업 경계

RhinoTerminal 내부에서 사용하는 Almond 도구의 중복 출력과 반복 확인을 줄이고, worker가 절대경로를 기억하지 않아도 작업자료를 저장·조회·재개할 수 있게 한다. 중단·전환·미완료 상태를 정상으로 다룬다.

주 작업 모드는 구현·검증이다. 기존 `purge` 워크트리와 브랜치를 계속 사용한다. 선행 완료분 `af4769c`는 오류 응답 공통화와 중복 카탈로그 제거이며, 이번 기능 개선 완료와 구분한다. 개별 항목은 독립적으로 진행·보류할 수 있다.

COS·외부 MCP의 새 사용 흐름 설계, 시간 포맷 변경, 사용자 모델의 임의 편집, 기존 사용자 자료의 일괄 삭제는 제외한다. 공용 Engine/스키마 변경에 따른 소비자 빌드·호환 검증은 필요하다. 일상 등록 경로와 plugin identity, UI thread, Undo/Redo, native 완료 확인, 프로세스 identity와 공유 잠금은 보존한다.

## 구현 전 가능성 검토 기록

이 표의 구현 상태는 변경 전 조사 기록이다. 현재 사용 계약은 아래 확정 기능 계약과 [MCP SPEC](../../SPEC.md)을 따른다.

| 항목 | 검토 당시 구현 | 판단·구현 방법 |
|---|---|---|
| 프로젝트 정보와 live 검증 | `runtime/mcp_server.py`는 연결 당시 메타데이터를 반환하고 `live_document_checked=False`로 표시한다. 고정 native 관찰 경로가 이미 있다. | 가능. 한 `project_info` 호출 안에서 필요한 문서 관찰을 실행하고 선택 항목만 반환한다. worker의 별도 확인 호출은 없앤다. |
| 선택 Context 조회 | `DocumentObservation.GetContext`는 문서·선택·뷰를 모두 수집한다. | 가능. native 수집 단계부터 sections를 적용한다. 단순히 반환 JSON만 잘라내지 않는다. |
| 이름·ID 출력 | factory가 정적으로 함수를 등록하고 catalog는 해당 소스를 읽는다. | 가능. 공개 함수·설명·호출부·schema 검사를 함께 변경한다. 저장소의 내부 식별자와 기존 데이터는 유지한다. |
| Plan·Phase 관계와 파일명 | 계획의 JSON revision과 기존 schema migration 경로가 있다. Scene은 별도 명시적 serializer를 사용한다. | 가능. Plan의 `depends_on` JSON 배열, Phase·Scene의 `file_name` 기본 빈 문자열을 추가한다. 기존 revision은 보존하고 누락 필드 읽기를 정규화한다. |
| 비선형 진행 | `update_plan_step`에 선행 완료 및 후행 실행 상태를 근거로 거부하는 코드가 있다. | 가능. 이 실행 순서 제한을 없애고 paused/재개를 지원한다. revision 충돌 검사는 데이터 유실 방지이므로 유지한다. |
| 선택 객체 역참조 | native selection 및 Component·Plan·Step 관계 테이블이 있다. | 가능. 실제 선택 객체를 읽고 직접·상속 관계를 구분해 조회한다. 없는 관계를 만들어 반환하지 않는다. |
| 작업자료 폴더 | 현재 `artifact_dir`는 연결별 `call_root`의 별칭이고 일부 출력 기본값만 적용된다. | 가능하지만 연결 임시폴더와 작업 폴더를 분리해야 한다. Plan의 상대경로 및 작업자료 참조를 공유 DB에 기록하고 재개 시 재사용한다. |
| 상대경로 자동 적용 | Python worker의 cwd는 프로젝트 루트이나 Rhino C# 및 Codex 셸은 별도 프로세스다. | 관리되는 MCP 입출력, Python 실행, C# 파일 helper에서 자동 적용 가능. 임의 `System.IO`나 외부 셸의 상대경로까지 가로채는 전역 cwd 변경은 사용하지 않는다. worker는 관리 경로에 상대경로만 전달한다. |
| DB 이름 변경 | Python project 경로, Engine `SessionFiles`, Terminal `AlmondHost`가 `scene.sqlite3`를 지정한다. | 가능. 모두 `DB`로 맞춘다. 기존 DB는 다른 worker가 사용하지 않는 상태에서 checkpoint·close 후 이름을 원자적으로 변경한다. 충돌·사용 중·checkpoint 실패 시 기존 DB를 보존하고 이전을 중단한다. |
| 임시자료 정리 | 모든 도구 호출이 빈 operation 폴더를 만들며 테스트 4개 모듈이 `mktemp` DB를 남긴다. | 가능. 로컬 조회는 폴더를 만들지 않는다. Native 전송에는 기존 Bridge 소유권 검증에 필요한 operation 폴더를 전송 직전에 생성하고 완료 확인 후 회수한다. 실행 scratch와 보존 산출물을 분리하고 소유한 scratch만 정리한다. 테스트는 체크아웃 안에서 수명 관리한다. |
| `.sessions` 정리 | 연결·프로세스·lock·native 호출 완료 기록이다. Plan/Step 완료와 무관하다. | 가능. 정상 종료 또는 다음 시작 시 종료된 연결만 정리한다. 사용 중 handle·살아 있는 소유자·불명확한 실행은 건드리지 않고, 호출 재실행으로 해결하지 않는다. |
| 도면·Sheet DB 등록 제거 | Sheet CRUD/sync와 도면 library DB 색인, Component 삭제 제한에 등록 관계가 연결돼 있다. | 가능. 공개 등록/sync 경로와 자동 색인을 제거하고 도면 자산 조회는 manifest 기반으로 전환한다. 기존 DB 행·Layout·도면 파일은 삭제하지 않는다. |
| 뷰 이미지 | 기존 active-view JPEG 경로에 이어, 별도 fixture에서 문서 지정 capture 설정으로 Named View와 Layout PNG 생성에 성공했다. | 가능. 테스트 Rhino 8.34에서 headless 관찰 9개, 활성 뷰 검사 5개, 종류별 대상 검사 8개 통과. Named View는 화면을 전환하지 않으며 Layout은 A4 용지 픽셀 크기와 일치하고 실제 PNG도 열어 확인했다. |

## 확정 기능 계약

### 1. 프로젝트와 관찰

- `project_info(sections=...)`는 프로젝트 정보 도구로 유지한다. 기본은 간단한 project/document/artifacts 정보이고 runtime/instructions 등은 선택 조회한다.
- document를 요청한 한 번의 호출에 현재 열린 문서와 live 확인 결과를 포함한다. 실패를 성공처럼 표시하거나 연결 기록을 live 결과로 대신하지 않는다.
- 프로젝트 루트 절대경로 한 개와 실제 설정한 `ALMOND_PROJECT_ROOT` 변수를 project 항목에서 제공한다. 현재 파일명, 작업자료 폴더와 DB 등은 상대경로로 제공한다.
- `get_rhino_context(sections=["document", "selection", "viewport"], ...)`는 요청한 종류만 수집한다. 기본 조회는 최소 문서 정보다.
- 문서 전환 자동 정책을 새로 만들지 않는다. 반복적인 worker의 문서·binding 대조 절차를 없애되 내부 연결 보호는 유지한다.

### 2. 공개 이름과 출력

- Phase/Plan/Step 도구 이름의 `generation`을 제거한다. `list_phases`, `list_plans`, `get_plan`, `update_step`, `list_plan_revisions` 등을 사용한다. `generated` 공개 명칭도 일반 asset 명칭으로 정리한다. 비공개 helper를 새 공개 도구로 노출하지 않는다.
- 일반 list/get/search 조회에 `include_ids=False`를 기본 적용한다. 중첩된 `component_ids`, 객체 GUID와 관계 ID도 포함한다. 필요한 수·이름·상태·자료는 남긴다.
- 입력으로 확정된 get 대상 ID는 응답에 반복하지 않는다. 새로 생성된 객체의 ID 반환, 명시적 참조 ID 조회와 `view="a"`의 GUID 목록은 목적에 필요한 반환이다.
- 도구 스키마·설명·호출부가 일치해야 한다. 문자열 속 코드·원본 manifest·저장된 데이터에 무차별 치환을 적용하지 않는다.

### 3. 계획·Scene·참조

- Plan `depends_on`은 여러 관련 Plan/Phase ID를 담는 JSON 배열이다. CSV 문자열은 받지 않는다. 존재·완료·순서·순환·자기 참조 등의 조건으로 입력이나 실행을 제한하지 않는다. 기본값은 `[]`다.
- Plan 설명은 다른 Phase의 작업도 관련 ID로 참조할 수 있음을 명시한다.
- Step의 선행 완료 강제와 후행 작업 때문에 재개를 막는 제한을 제거한다. 중단·전환·재개를 지원하며 자료를 지우거나 강제로 completed로 바꾸지 않는다.
- Phase와 Scene에 `file_name`을 생성·수정·조회할 수 있게 한다. 미기입·기존 행에서도 `""`로 존재한다. 이 필드 저장은 실제 3DM 파일 이동·이름 변경을 수행하지 않는다.
- 선택 객체 참조 조회 도구는 현재 선택으로부터 Plan/Step/Component ID와 이름을 반환한다. Step 직접 참조와 Plan 대상 상속을 구분하며 미등록·불일치·잘림을 표시한다.

### 4. 작업자료와 상대경로

- 보존할 작업 폴더는 `<project>/tmp/YYMMDD_작업명`이다. 예: `tmp/261026_그리드정리`. 날짜는 사용자 로컬 날짜를 사용한다.
- 현재 Plan/Step을 선택하는 관리 도구가 폴더를 재사용하고 호출에 적용한다. 폴더는 실제 파일이 필요할 때 생성한다. 조회·재개·매 호출마다 새 UUID 폴더를 만들지 않는다.
- Plan에는 작업 폴더와 자료 참조를, Step에는 해당 작업의 input/output refs를 연결한다. 다른 worker가 Phase/Plan/Step 조회에서 자료를 찾을 수 있어야 한다.
- 관리 출력 인자는 현재 artifact 폴더를 기본으로 한다. 프로젝트 입력 경로와 산출물 경로의 기준을 설명에 구분한다. native 기대 문서 경로는 binding에서 자동 공급한다.
- Python은 관리 실행 도구의 cwd와 환경변수로 폴더를 적용한다. C#은 호출 범위의 파일 helper에 상대경로를 전달한다. Rhino 전체 프로세스 cwd를 바꾸지 않는다.
- 폴더 이름 변경은 실행기가 처리한다. 해당 폴더의 쓰기 작업과 직렬화하고 폴더 및 현재 참조를 함께 갱신한다. 실패 시 이전 위치·참조를 복구한다. 과거 immutable revision과 임의 로그 본문을 재작성하지 않는다.
- 폴더 선택을 다른 프로세스에 전파할 때 자식 환경변수 변경에 의존하지 않고 공유 상태를 각 호출에서 읽는다. `..` 이탈이나 기존 폴더 덮어쓰기는 허용하지 않는다.

### 5. DB·scratch·세션

- 공유 DB 파일명은 `DB`다. 작업·연결마다 DB를 복제하지 않는다. 기존 `scene.sqlite3`의 데이터는 이전 절차와 시험으로 보존한다.
- Python scratch는 보존 산출물 밖의 `.almond/tmp/python`에 둔다. 파일이 필요하거나 native 요청의 소유권 검증에 필요한 경우만 생성하고, 완료 확인 후 소유한 파일·빈 폴더를 정리한다. 로컬 조회에서는 생성하지 않으며 보존 산출물을 scratch로 취급하지 않는다.
- `.sessions` 정리는 연결 수명과 OS 소유권을 기준으로 한다. Plan·Step 상태를 조회하거나 정리 조건에 사용하지 않는다. `unconfirmed`는 native 호출 응답 확인 문제이며 작업계획 미완료가 아니다.
- 사용 중 세션 및 공용 lock을 강제로 지우지 않는다. 종료된 token 폴더만 검사하고 정상 종료와 다음 시작의 회수 경로를 마련한다.
- 테스트 DB/임시폴더는 개발 체크아웃에 격리하고 성공한 테스트의 잔여물을 정리한다. 사용자 프로젝트를 테스트 임시 경로로 사용하지 않는다.

### 6. 도면과 Sheet

- 도면·Sheet를 DB에 등록·갱신·동기화하는 공개 기능과 자동 시작 색인을 제거한다.
- 도면 자산 파일/manifest 등록과 조회에 프로젝트 DB 색인을 요구하지 않는다.
- Sheet 장부 때문에 Component 조작을 제한하는 연결을 제거한다.
- 기존 DB의 도면/Sheet 자료는 보존한다. Rhino Layout 작성·캡처·도면 파일 내보내기를 없애는 작업이 아니다.

### 7. 뷰 이미지

- `get_rhino_viewport_image(view="", scale_percent=50, include_usage=False)`.
- 빈 view는 현재 뷰, `a`는 viewport/named view/layout별 name·guid만 반환한다. GUID는 해당 대상을 캡처한다.
- 기본 결과는 PNG 이미지 하나다. 문서·경로·GUID JSON을 반복하지 않는다. `include_usage`에서만 크기와 명확히 표시한 추정량을 추가한다.
- 100%는 원본 크기다. Named View는 저장된 화면 크기(없으면 현재 뷰 크기), Layout은 용지를 96 dpi로 표현한 크기를 기준으로 한다. 기본 50%는 두 축을 각각 절반으로 줄인다.
- Named View는 현재 display mode와 저장된 카메라를 별도 viewport에서 그린다. 화면의 뷰를 활성화했다가 복원하는 방식은 사용하지 않는다.
- Layout은 용지와 Detail을 캡처한다. 현재 Layout의 Detail이 활성화돼 있어도 대상은 용지다.
- 메모리에서 처리하고 임시 이미지 파일을 만들지 않는다. 크기 한도를 넘으면 명시적으로 더 낮은 퍼센트를 요청하며 몰래 다른 크기로 바꾸지 않는다.

## 한계와 검증할 조건

- 파일 압축 바이트와 이미지 토큰은 같지 않다. 모델/detail 정보를 MCP에서 받지 못하므로 픽셀 기반 추정식은 실제 과금량이 아니다.
- 서로 다른 Windows 드라이브 사이의 일반 상대경로는 존재하지 않는다. 이 경우 절대경로를 상대경로인 것처럼 반환하지 않고 지원 불가를 명시한다. 현재 조사 대상은 같은 C: 드라이브다.
- `rhino_temp_at_attach`는 실제 구현상 Rhino 프로세스 TEMP이며 문서별 attachments 전용 경로라는 종전 설명은 잘못됐다. 필요할 때만 간단한 진단 정보로 제공한다.
- 임의 외부 셸·외부 프로그램·임의 C# IO의 저장 위치까지 자동으로 통제할 수는 없다. 위 관리 실행/파일 경로가 보장 범위이며 스킬도 이를 사용하도록 정렬한다.
- 기존 사용자 `.almond`는 16,044파일·약 13.08GB·DB 1,477개로 조사됐다. 이것을 모두 쓰레기로 간주하지 않는다. 이번 구현 검증에서는 원본 자료의 삭제·이동을 실행하지 않는다.

## 검증과 전달

1. 공개 schema/설명/호출부와 ID 기본 출력, 선택하지 않은 native 수집의 미실행을 검사한다.
2. 기존 DB migration, 빈 파일명, 자유로운 관련 ID 배열, 중단·재개, revision 충돌 보호를 테스트한다.
3. 두 연결의 동일 Plan 재사용·폴더 이름 변경 경쟁·상대경로 출력·자료 발견·실패 복구를 검사한다.
4. 반복 조회, 정상 종료, 취소·native 완료 불명확, 다음 시작 회수에서 임시자료 소유권과 누적 여부를 검사한다.
5. 도면/Sheet DB 등록 도구와 자동 색인이 사라지고 기존 자료가 보존됨을 검사한다.
6. disposable Rhino 문서에서 active/Named View/Layout의 PNG·퍼센트·용지 범위·비활성화·geometry/selection/Undo 불변을 확인한다.
7. 영향받는 MCP·native·Terminal 및 공용 소비자 계약 검사를 수행한다. Engine 변경 시 두 RHP와 Engine DLL 일치를 확인한다.
8. 소스, 실행 파일, manifest를 함께 검증해 로컬 commit한다. 빌드·배치·등록·실제 로드·일상 checkout 반영은 서로 다른 상태로 보고한다. 로드 중인 RHP를 덮어쓰거나 Rhino를 강제 종료하지 않는다.

## 추가 분석 과제

사용자가 요청한 ‘치수 객체를 그리드 블록으로 이동’의 rhino_session/rhino-native 비교는 별도 분석 결과로 제출한다. 실제 턴 시간·도구 시간·호출 수·탐색 범위·실수와 복구를 비교하고 사용자 체감 시간과 구분한다. 현재 rhino_session의 해당 턴은 확보했으며 rhino-native 대응 기록은 추가 식별 중이다. 비교 과제 때문에 이미 확인된 독립 구현 항목을 중단하지 않는다. 분석만으로 새로운 블록 편집 기능이나 사용자 모델 편집을 임의 추가하지 않는다.

## 실행 지시

이 명세서의 전체 요구를 기존 purge 작업에 구현한다. 파일/스키마 변경과 기능 테스트를 함께 진행하고, 실측 실패는 원인을 고쳐 재검증한다. 스킬 시작 절차·tool-map·workflow·FUNDAMENTAL/MODEL-CONTEXT도 실제 구현과 맞춘다. 현재 승인된 범위에 대한 재승인을 반복 요청하지 않는다. 해결 불가능한 조건이나 배포에 필요한 사용자 행동은 대상·이유·완료 범위와 함께 구체적으로 보고한다.
