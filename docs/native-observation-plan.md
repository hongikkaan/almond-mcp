# Rhino 관측·실행 결과 계약 재검토와 작업 계획

2026-10-22. 시작 기준은 `c578115`이며, 단일 RHP 통합 이후의 개인 fork에 적용한다.
이 작업은 Native의 성공 속도를 재현했다고 주장하는 작업이 아니다. 에이전트가
현재 문서와 화면, 실행에서 계산한 값을 직접 읽을 수 있게 하는 계약 개선이다.

완료한 구현의 사용법은 [기능 계약](native-observation.md), 실제 실행 결과와 검증 한계는
[검증 기록](native-observation-verification.md)에 정리했다.

## 재검토 결과

인계 원문과 자료 28개의 크기/SHA256을 확인한 뒤 현행 호출자를 다시 읽었다.
과거 실행에서 다음 핵심 사례도 직접 확인했다. 세션 원문의 번호는 물리 줄이다.

| 확인 | 원문/현행 근거 | 판단과 한계 |
|---|---|---|
| H2 조사 코드의 WriteLine이 성공 응답에 없음 | H2 L120, L123, L127; ScriptExecutor.cs의 기존 4개 반환 필드 | 임의 조사 결과를 파일로 회수해야 했던 구체적 사례다. 모든 시간 차이의 원인이라는 증거는 아니다. |
| H2의 빈 Difference를 성공으로 처리한 뒤 원객체를 숨김 | H2 L3515, L3518; L3540/L3544의 복구 | 실행 성공과 수정 의도의 충족은 다르다. 출력 기능만으로 이 잘못된 조건을 고칠 수 없다. |
| Native도 잘못된 결과와 API 오판을 겪음 | Native L252/L255의 2.992123 m³ 제거 시험; L259–283의 component 조회·정정 | Python이나 Native가 정확도를 자동 보장하지 않는다. 적용 전 시험과 목적에 맞는 보존 검사가 중요하다. |
| Native는 현재 상태/화면/출력을 한 응답에서 제공 | Native L22/L26, L28/L32, 고정 소스 GetContext/GetViewportImage/RunScript | 필요한 관측 경로가 준비돼 있다. 전체 기하 이해나 건축 판단이 자동으로 제공되지는 않는다. |
| 착수 시 공개 도구의 이름·입력은 누락되지 않았음 | 변경 전 server 공개 56개, catalog 57개, host 관리 3개; catalog fingerprint 일치 | 새 도구를 많이 추가하거나 기존 전문 기능을 삭제할 이유가 되지 않는다. |
| 캡처 입력 설명의 일부가 실제 도구 메타데이터에서 사라짐 | server.py의 shot JSON 문단과 catalog 비교; 동일 FastMCP의 inert AST 등록 재현 | COS만의 잘림이 아니다. source docstring을 FastMCP가 처리하는 방식에 맞춰 수정해야 한다. |
| 기존 전문 기능도 live 수치를 돌려줌 | conditioning summary.document, export_asset_contract, 구조/자산 export | 일반적인 현재 상태와 임의 실행 결과의 경로가 부족하다는 뜻이지, 모든 수치 반환이 없다는 뜻이 아니다. |

비교 세션의 초기 모델·요구 범위·명시 effort가 같지 않다. 과거 시간·토큰을
성능 배수로 쓰지 않는다. 모델 상태·요구·판정 기준을 고정한 별도 실험 전에는
정확도 향상, 시간 단축, Native와 동등한 성능을 완료 사실로 보고하지 않는다.

## 이번 변경의 경계

1. 기존 C# 실행에서 JSON으로 표현 가능한 반환값을 직접 돌려준다. 기존
   `List<Guid>`와 `void Run` 및 현재 입력 schema, 자동 레이어/치수, Undo 복구는
   유지한다. 일반 실행을 read-only라고 부르지 않는다.
2. 별도 고정 조회 `get_rhino_context`를 제공한다. 현재 문서의 identity·단위·공차,
   객체 수, 제한된 선택 목록, 현재 viewport/camera를 조회한다. 이 경로는
   자유 코드 실행기의 자동 레이어·치수·Undo를 거치지 않는다.
3. `get_rhino_viewport_image`는 현재 뷰 한 장과 같은 시점의 metadata를 반환한다.
   자동 zoom, Named View 전환, clipping 변경, display mode 전환은 하지 않는다.
   현재 화면 비율을 유지하고 픽셀/바이트 한도를 둔다. Python은 실제 MCP
   ImageContent를 반환한다. JSON의 base64 문자열만으로 이미지 전달을 주장하지 않는다.
4. 기존 캡처 도구의 문서 형식을 고쳐 필요한 shot 입력 예시와 복원/출력 계약이
   실제 메타데이터에 남도록 한다. server instructions와 해당 도구 설명에는
   현재 상태 확인, 조사/검사 값 반환, 성공 상태와 의미 검증의 차이만 짧게 안내한다.

이번에 추가하지 않는 것은 Python 실행기, 프로세스 전역 stdout 가로채기,
영구 기하 캐시, 모든 변경의 이벤트 원장, 범용 자동 건축/Boolean 승인기다.
필요성이 입증되지 않았고, 반환값과 고정 조회로 해결할 수 있는 문제보다
수명·간섭·상태 판정 비용이 크다. 별도 세션에서 수정 중인 rhino-almond 스킬은
이번 구현 범위에 포함하지 않는다.

## 반환과 오류의 의미

- 실행 결과의 기존 status/message/guids/error_trace 의미를 보존한다.
- 추가 result는 JSON-safe 값으로 제한하고 크기·깊이·순환 참조를 검사한다.
  큰 결과를 정상 데이터처럼 일부 잘라 보내지 않는다.
- 결과 변환 실패는 스크립트 실행 실패와 구분해 result_error로 알린다.
  이미 끝난 수정이 취소됐다고 보고하거나 자동 재실행하지 않는다.
- runtime/Undo 오류와 timeout의 기존 의미를 변경하지 않는다. 문서 binding,
  UI-thread 검사, request identity, native acknowledgement를 그대로 경유한다.
- context의 실제 선택 수와 반환 수를 분리한다. 실패한 항목을 빈 상태로
  위장하지 않고 경고/미확인으로 표시한다. bbox/visible count로 정확성을 인증하지 않는다.

## 파일 소유와 실행 순서

| 담당 | 변경 범위 | 검토 포인트 |
|---|---|---|
| 실행 담당 | ScriptExecutor.cs 및 실행 결과 테스트와 필요한 국소 helper | 기존 Run·Undo 호환, 결과 직렬화 실패/한도 |
| 상태·화면 담당 | 새 DocumentObservation.cs 및 BridgeServer.cs의 두 dispatch | 조회 부작용 없음, 같은 문서·뷰, aspect ratio, 이미지 한도 |
| 주 담당 | server.py, shared_store.py, catalog annotation/도구수·메타데이터, 통합 문서 | 원 sender·DB/native guard 보존, typed 이미지, 정확한 설명 |
| 검증 담당 | 독립 검증 fixture·테스트 코드 | fake transport와 실제 Rhino/실제 모델 과제의 증거 구분 |

순서: 재검토와 경계 확정 → 독립 구현 → 코드 상호 검토 → 관련 Python/.NET
검증 → 별도 Rhino 검증 문서에서 실제 API/화면 확인 → 후보 빌드/연결 검증.
이미 로드된 RHP와 사용자의 문서는 덮어쓰거나 강제로 닫지 않는다. 후보 출력은
기존 build.ps1의 `RhinoAlmondBridge/plugin-*` 경로 규칙을 사용한다.

## 완료 증거

- 기존 공개 입력과 전문 도구의 계약이 보존된다. 새 catalog를 AST로 생성하고
  source/schema 검사를 통과한다. 설명은 원문 문자열뿐 아니라 노출 메타데이터로 검증한다.
- 반환값이 실제 직렬화된 응답까지 도달한다. 일반 자료, null/void/GUID,
  순환/과대/깊은 값, getter/변환 예외를 구분하고 Undo 상태를 확인한다.
- fresh 문서에서 context/capture 전후 객체·레이어·Modified/Undo와 카메라·선택·
  display/clipping 상태를 비교한다. 기존 AIA layer가 있는 fixture만으로 대체하지 않는다.
- 뷰 없는 문서, 유효하지 않은 크기, 이미지 생성 실패, 문서 전환/응답 미확정을
  명확히 보고한다. 실제 ImageContent 수신·decode와 metadata 일치를 확인한다.
- 기존 native Undo 21개 회귀를 포함한다. 테스트가 linked source를 실행했는지,
  후보 RHP가 실제 로드됐는지, 실제 클라이언트로 이미지가 들어왔는지를 따로 기록한다.
- 동일 초기 3DM·요청·모델/effort·참조/스킬의 비교 실험은 기능 검증과 별개다.
  국소 접합의 기준면/두께/Z/변경 GUID/비대상 보존/기대 교차·제거량을 미리 정한
  실험이 없으면 성능 개선 수치를 만들지 않는다.

## 근거 위치

아래 인계 자료와 세션 원문은 조사 당시 근거이며 Git/PR에 포함하지 않는다.
로컬 인계 MD·ZIP·추출 폴더는 후속 정리에서 제거됐다. 구현 계약과 검증 요약은
위의 기능 문서와 검증 기록에 보존했다. 구현 후 COS catalog는 59개, 관리 도구를
포함한 공개 COS 도구는 62개다. 위 표의 수량은 변경 전 조사 기준이다.

- 인계 원문: [Slack handoff](https://hih-z6k5791.slack.com/archives/C0CA8BC1SS1/p1792678172602669?thread_ts=1792678092.873709&channel=C0CA8BC1SS1&message_ts=1792678172.602669).
- 조사 당시 로컬 인계: `HANDOFF-native-advantages-to-almond-2026-10-22.md`,
  전체 자료: `native-vs-almond-handoff-materials-2026-10-22/` (현재 checkout 필수 파일이 아님).
- Native 원문: `/sessions-2/2026/10/19/rollout-2026-10-19T01-40-34-01a14fe2-eb05-7ef1-a5ff-6ffb10652ab3.jsonl`.
- H2 원문: `/sessions/2026/10/18/rollout-2026-10-18T16-37-22-01a14df1-9b8b-7e42-bacd-739f0b84a6de.jsonl`.
- 현재 호출 경계: `ScriptExecutor.cs` → `BridgeServer.cs` → Engine
  `BoundBridge.cs`/`native_request.py`/`shared_store.py` → MCP server → COS worker/host.
