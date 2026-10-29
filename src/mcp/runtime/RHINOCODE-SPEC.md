# RhinoCode 실행 계약

`execute_rhino_script`는 기존 Bridge C# Run 실행과 공식 Rhino ScriptServer 실행을 제공한다. 런타임은 연결된 Rhino·저장 문서를 확인하고 호출별 완료 근거를 관리한다. 입력 사용법은 `get_modeling_guide(tool="execute_rhino_script")`, 작업 판단은 [BASIC](../BASIC-INSTRUCTIONS.md), 고정 관찰과 캡처는 [관측 계약](../rhino/OBSERVATION-SPEC.md)을 따른다.

## 실행 경로와 언어

| language | 실행 계약 |
|---|---|
| `csharp` | 기본값. Bridge/Roslyn의 `public static Run(RhinoDoc doc)` 유지 |
| `python` | 공식 RhinoCode Python 3. 동기 본문에 `doc`, `result`, `artifact_dir` 제공 |
| `python2` | 해당 Rhino에서 확인된 공식 Python 2 실행 |
| `csharp-script` | 공식 C# statement body. Run 클래스를 감싸지 않고 `doc`, `result_json` 사용 |
| `command` | 확인된 ScriptRunner 문맥에서 완전한 Rhino command macro 실행 |

공식 모드는 해당 Rhino의 `StartScriptServer`와 현재 runtime capability를 요구한다. `rhinocode list --json`의 정확한 pipeId·프로세스 identity·문서를 확인하고 그 pipe를 `--rhino`로 지정한다. pipe와 Almond A–J 슬롯은 서로 다른 식별자다. 첫 Rhino나 PID 추정으로 대상을 선택하지 않는다.

패키지는 연결 runtime의 callback을 사용하며 외부 연결기 구현을 import하지 않는다. CLI는 Python worker의 자식 프로세스로, shell 없는 인자 배열로 실행한다. Rhino UI-thread handler 안에서 외부 CLI를 기다리지 않는다.

## 문서 identity와 실행 범위

전송 전 bound PID·시작 identity·pipe·저장 경로를 확인한다. 생성한 동기 wrapper는 실행 직전 문서 runtime serial과 경로를 다시 확인하고 명시적인 `doc`를 사용한다. 이 wrapper는 허가된 사용자 코드의 실행 문맥이며 sandbox가 아니다.

비동기 문서 변경·프롬프트·백그라운드 writer는 완료 계약 밖이다. 전송 뒤 다른 transport로 fallback하거나 같은 코드를 자동 재실행하지 않는다. 일반 설계 질문은 관련 면적·치수·관계를 한 번의 Python/C# 실행에서 함께 계산할 수 있다. 고정 블록 조회는 그 관찰 보장이 필요할 때 사용한다.

## journal과 완료 판정

CLI 실행 전에 token·operation·request·nonce·source hash·target process/document·생성 파일과 자식 프로세스 identity를 포함한 durable journal을 남긴다. **정확히 일치하는 최종 wrapper receipt와 CLI 프로세스 종료 확인이 모두 있어야 완료**다. stdout·exit code·대기 timeout만으로 완료를 판정하지 않는다.

최종 receipt는 결과 표시 한도와 독립적이며 실행·cleanup·Undo·결과 직렬화 오류를 구분한다. 반환 데이터를 표현하지 못해도 실행 근거는 남긴다. RequestBatch는 공식 CLI 실행을 native 요청과 별도로 관리하며 native sequence나 native-finally 응답을 합성하지 않는다.

Python·C# 오류 진단은 ASCII JSON으로 직렬화된 바이트 수로 제한한다. 부모·자식 receipt가 최종 64 KiB를 넘으면 diagnostics_truncated와 축약 진단을 남기고 identity·실행/부분 적용 상태·Undo·결과 근거를 보존한 완료 receipt를 기록한다. 부모와 공개 결과 조회에도 잘림 표시를 전달하며 진단 잘림을 성공이나 rollback으로 바꾸지 않는다.

ProjectRuntime, native release/drain과 종료 세션 회수는 durable external-execution fence를 확인한다. 실행 중·누락·손상 receipt는 worker가 종료돼도 재사용과 회수를 막는다. 자식 프로세스에 접근하지 못한 것은 종료 근거가 아니다. 대상 Rhino가 확실히 종료됐다면 지연 실행 가능성이 없으므로 정상적인 종료 세션 회수 조건으로 처리한다.

대기 timeout은 CLI를 종료하거나 재실행하거나 파일을 지우지 않는다. 늦게 도착한 정확한 결과를 조회해 pending·finishing·completed·unconfirmed를 구분한다. CLI에만 있던 불확실성이 해소돼도 무관한 native 불확실성은 유지한다. 무효화된 외부 binding은 재연결 필요로 표시하며 임의로 되살리지 않는다.

## Undo와 실패

wrapper는 자신이 소유한 0이 아닌 Undo record만 종료한다. 사용자 코드 실패는 앞선 작업의 자동 Undo를 뜻하지 않는다. 부분 적용·실행 오류·결과 표시 오류는 서로 다른 상태다. command 모드는 bound 문서에서 동기 완료가 확인되는 실행 문맥에 한정하며 event pumping으로 완료를 추정하지 않는다.

기존 `csharp` 경로의 반환 한도와 rollback 동작은 관측 계약의 C# 결과 반환 절을 따른다. `result_error`만으로 실제 변경이 취소됐다고 해석하지 않는다.

## 완료 결과 조회

`get_rhino_execution`은 같은 실행의 상태·결과를 재실행 없이 조회한다. request_id를 생략하면 현재 연결의 최근 실행을, 지정하면 정확한 요청을 읽는다. `result_fields`, offset/limit와 결과·stdout 선택을 통해 필요한 부분만 조회한다.

확인된 정상 완료 응답은 결과·페이지·요청한 로그·복구 대상 상태를 기본으로 보존한다. `include_diagnostics=true`는 전체 근거를 반환한다. pending·불확실·실패·부분 적용·0이 아닌 CLI exit·결과 표시 오류는 기본 응답에서도 상세 근거를 유지한다.

공개 응답 projection은 원본 journal을 읽고 정합한 뒤 적용한다. journal 저장·fence·완료 판단·worker schema 검사를 바꾸지 않는다. 클라이언트 재시작 후에는 정확한 request_id로 보관 파일을 조회할 수 있으며 이 경로는 Rhino를 재연결하거나 실행하지 않는다.

## 관찰과 자산 준비의 경계

캡처의 scale_percent는 픽셀 크기이며 기본 75, 명시적 100은 원본 크기다. Layout raster는 print color·width 설정을 요청하지만 출력은 Rhino의 실제 PrintDisplay·뷰 상태에 영향을 받을 수 있다. 성공한 PNG를 독립적인 인쇄 색·선폭·Detail 축척 검증으로 취급하지 않는다.

`prepare_drawing_asset` 및 preparation_job을 사용하는 등록은 현재 `acceptance_pending`으로 거절된다. 준비한 3DM의 일반 등록은 [자산 계약](../features/assets/SPEC.md)을 따른다. 비활성 준비 구현이나 preview 존재를 발행 기능의 성공으로 안내하지 않는다.

## 검증과 전달

오프라인 검사는 정확한 대상 선택, 오래된 identity, timeout·늦은 완료, worker 종료, 손상·불일치 receipt, native 회수 fence, 결과 선택과 실제 worker/catalog 일치를 다룬다. 실제 기능 검증은 사용자가 연결한 작업 문서에서 언어별 실행·실패·Undo/Redo·복구와 관련 결과를 확인한다.

[루트 작업 지침](../../../AGENTS.md)에 따라 사용자 모델·DB·다른 변경을 보존한다. RHP 빌드·파일 배치·등록·실제 로드·모델링 검증은 각각 다른 증거다. 프로토콜 검사만으로 설계 판단이나 실제 문서의 인쇄 표현이 검증됐다고 보고하지 않는다.

공식 실행 인터페이스 참고: [Rhino scripting CLI](https://developer.rhino3d.com/guides/scripting/advanced-cli/), [비동기 실행](https://developer.rhino3d.com/guides/scripting/advanced-async/), [PrintDisplay](https://docs.mcneel.com/rhino/8/help/en-us/commands/printdisplay.htm).
