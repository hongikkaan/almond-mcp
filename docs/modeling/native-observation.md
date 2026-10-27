# 현재 문서·화면 조회와 C# 결과 반환

프로젝트 정보가 필요하면 `project_info`를 조회한다. 기본 document 항목이 실제 활성 문서를
함께 확인하므로 같은 live 확인을 위해 `get_rhino_context`를 다시 호출하지 않는다. 현재 화면이 판단에 필요할 때
`get_rhino_viewport_image`를 호출한다. COS에서도 같은 이름을 사용하고 `connection_id`를 전달한다.

두 조회는 기존 Engine의 문서 binding·UI thread·호출 identity·native 완료 확인을
거친다. 파일 경로를 임의로 골라 다른 모델을 조회하는 기능은 없다.

MCP 서버와 COS host의 초기 안내 모두 현황 조회, 관련 객체 조사, 수정 후보 검증 후
원본 교체 순서를 전달한다. COS host의 외부 클라이언트도 이 안내를 받는다.

## 현재 상태

```json
{"sections": ["selection"], "selection_limit": 50}
```

`get_rhino_context`는 document/selection/viewport 중 요청한 항목만 수집한다. 기본은 document이며,
여러 section을 조합할 수 있다. 일반 ID는 include_ids=true일 때만 반환한다.

| 필드 | 내용 |
|---|---|
| `status` | `success` 또는 명시적 오류 |
| `document` | runtime serial, path, name, units, 절대/각도 공차, modified, 객체/레이어 수 |
| `selection` | 전체 선택 수 `total`, 반환 수 `returned`, `truncated`, 객체별 id/name/layer/type |
| `viewport` | 활성 viewport ID/이름, 원본 픽셀 크기, display mode, projection, camera/target/up/lens |
| `warnings` | 확인하지 못한 값이나 viewport 부재에 관한 설명 |

`selection_limit`의 기본값은 50이고 범위는 0–200이다. 0이면 목록을 생략하면서
전체 선택 수는 조회한다. 객체 수는 정상·숨김·잠금·reference·light를 포함하며
삭제 객체·블록 정의의 내부 객체·grip은 제외한다. 레이어 수는 삭제 레이어를 제외한다.
조회 실패 값을 0이나 빈 문서로 바꾸지 않고 `null`과 경고로 표시한다.

이 경로는 레이어·치수·geometry·Undo record를 생성하지 않는다. 현재 viewport가
보는 모든 객체를 계산하거나 단면·접합·치수의 정확성을 판정하지는 않는다.

## 현재 화면

```json
{"view": "a"}
```

`view="a"`는 `viewports`, `named_views`, `layouts`별로 이름(`name`)과 GUID(`guid`)만
반환한다. 원하는 GUID를 `view`에 넣으면 그 이미지가 나온다. `view`를 생략하면
현재 뷰를 캡처한다. 같은 이름이 있어도 GUID로 대상을 구분한다.

```json
{"view": "목록에서 받은 GUID", "scale_percent": 50}
```

기본 반환은 **PNG MCP image content 한 개**이며 경로·문서·GUID metadata를 반복하지 않는다.
`scale_percent`는 1–100 정수, 기본 50이다. 100은 원본 픽셀 크기, 50은 가로·세로
각각 절반이다. Named View는 저장된 화면 크기(없으면 현재 뷰 크기), Layout은
용지를 96 dpi로 표현한 크기를 100%로 삼는다. Layout은 주변 작업창을 빼고 용지와
그 안의 Detail을 캡처하며, 현재 Layout에서 Detail이 활성화돼 있어도 용지가 대상이다.

Named View는 현재 display mode를 사용해 별도 viewport에서 저장된 카메라를 그린다.
화면의 활성 뷰 전환·Named View 복원·zoom·selection·Undo 변경을 하지 않는다.
PNG와 base64 모두 메모리에서 처리하므로 임시 이미지 파일을 만들지 않는다.
특정 clipping이나 display mode를 새로 설정하는 기능은 아니다.

`include_usage=true`일 때만 크기와 토큰 추정치를 덧붙인다. 추정식은
`ceil(width/32) × ceil(height/32) × 1.2`를 올림한 예시이며 공급자의 추가 리사이즈를
가정하지 않는다. 클라이언트의 모델·detail 설정을 MCP가 알 수 없으므로 실제 사용량이
아니다. PNG 압축 바이트 수보다 픽셀 크기를 줄이는 것이 이 추정량을 줄인다.
[공식 이미지 비용 안내](https://developers.openai.com/api/docs/guides/images-vision#calculating-costs)를 참고한다.

16 메가픽셀 또는 PNG 4 MiB를 넘으면 축소율을 낮추라는 오류를 반환하며 몰래 추가
축소하지 않는다. 없는 GUID·실패한 캡처·캡처 중 문서/뷰 변경도 이미지 없이 오류로
반환한다. Python에서도 실제 PNG 형식과 크기를 검사한다. 캡처 성공은 형상의 정확성을
증명하지 않는다. 의도적인 카메라 경로와 여러 패스는 `capture_conditioning_pass`를 사용한다.

## 고정 geometry probe

`get_rhino_probe` / COS `get_rhino_probe`는 컴파일된 `outline`,
`resolve-block`, `sections`, `vertical-probe`, `joint-pairs` 중 하나를 실행한다.
`probe`와 도구별 `options`를 전달한다. 연결된 runtime은 기대 문서 경로를 내부에서
공급하므로 worker가 절대 `expected_model_path`를 기억해 반복 입력하지 않는다.
COS에서는 동일하게 `connection_id`를 사용한다. 활성 문서 경로가 다르면 계산 전에
거절하며 새 문서를 열거나 파일에 결과를 기록하지 않는다.

Bridge UI thread의 고정 handler가 스킬의 C# helper를 직접 호출한다.
일반 스크립트 실행기·Roslyn·BeginUndoRecord·EnsureAiaLayers를 거치지 않으며
기하·속성·레이어·선택·뷰·modified·Undo 상태를 보존한다. 응답의 `status`, `probe`,
`document` identity·units·tolerance와 `data`를 함께 읽는다. 요청과 응답은 각각
UTF-8 JSON 262,144 bytes 이내이며 한도 초과는 명시적 오류다. helper의
`unknown`, `truncated`, 미지원 객체·미평가 표본을 0이나 설계 통과로 해석하지 않는다.

Python은 기존 문서 조회의 `capabilities.fixed_probes`를 먼저 확인한다.
이 capability가 없는 이전 관찰용 Bridge에는 알 수 없는 probe 요청을 보내지 않고
`unsupported_probe`를 반환한다. 새 Bridge의 알 수 없는 request type도 실행 없이
`unsupported_request`로 거절한다. `execute`와 type 생략의 기존 스크립트 동작은 유지한다.
입력·출력 요약은 [조회·화면 지침](guidance/modeling-guide.md#조회화면-도구)에 있다.

## C#에서 계산값 반환

`execute_rhino_script`의 입력은 기존 `script` 하나다. `public static Run(RhinoDoc doc)`
진입점에서 JSON으로 표현 가능한 값을 반환하면 응답의 `result`에 들어간다.

```csharp
public class Script
{
    public static object Run(RhinoDoc doc)
    {
        return new {
            name = doc.Name,
            units = doc.ModelUnitSystem.ToString(),
            tolerance = doc.ModelAbsoluteTolerance
        };
    }
}
```

지원 값은 문자열/문자/불리언/유한 숫자/Guid, 문자열 키 dictionary, list/1차원 배열,
그리고 C# 익명 객체다. 그 안의 값도 같은 조건을 만족해야 한다. 기하 객체나 임의
클래스를 그대로 넘기지 말고 필요한 수치·ID를 익명 객체에 투영한다. 임의 POCO의
property getter, lazy enumerable, 사용자 JSON converter는 자동 실행하지 않는다.

`result` 자체의 compact JSON을 UTF-8로 계산해 최대 65,536 bytes, 중첩 container는
최대 16개까지 허용한다. 순환 참조·비유한 숫자·미지원 타입·과대 결과는 일부만 잘라
정상 데이터처럼 보내지 않고 `result_error`로 설명한다. 반환 데이터는 응답 생성 전에
분리한 JSON tree이므로 최종 직렬화가 사용자 객체를 다시 탐색하지 않는다.

| 결과 | 의미 |
|---|---|
| `status=success`, `result` | 스크립트가 끝났으며 표현 가능한 계산값을 받음 |
| `status=success`, `result_error` | 스크립트는 끝났으나 반환값을 표현하지 못함. 적용된 변경은 이 이유로 rollback되지 않음 |
| runtime/Undo 오류 | 기존 실행·복구 오류. 성공 데이터처럼 보일 수 있는 새 결과 필드는 제거됨 |
| timeout/완료 미확정 | 기존 Engine의 격리·완료 확인 규칙을 따름. rollback로 간주하거나 자동 재시도하지 않음 |

`List<Guid>` 반환은 기존 `guids` 및 자동 치수 동작을 유지하며 `result`를 추가하지
않는다. `void`와 `null`도 새 결과 필드를 만들지 않는다. `guids`는 스크립트가 선언한
ID이며 전체 변경 내역을 보장하지 않는다. 일반 실행기는 기존 자동 레이어와 Undo
동작을 유지하므로, 계산값만 돌려주는 코드여도 read-only 도구로 간주하지 않는다.

## 수정의 판정과 검증

실행 성공, `IsValid`/`IsSolid`, 현재 화면은 각각 다른 근거다. 예를 들어 Boolean
수정에서는 결과 배열이 비어 있지 않은지, 기대 제거량·접합 범위·기준면이 맞는지,
원본의 비대상 부분이 보존되는지 확인한 뒤 Replace/Delete를 적용한다. 검사값을
반환하면 후속 판단을 쉽게 할 수 있지만 검사 조건 자체의 정확성을 보장하지는 않는다.

Python 검증은 실제 MCP content/schema와 위조·누락 이미지/크기 오류를 다룬다.
`src/rhp/RhinoAlmondBridge/tests/script_executor_undo`의 native suite는 기존 Undo 회귀,
반환 제한과 headless 조회를 검사하고, `ObservationTests.RunViewport(doc)`는 호출자가
지정한 실제 문서의 geometry/attributes/layer/view/selection/Undo 상태를 전후 비교한다.
후보 RHP 빌드, 실제 로드 경로, 실제 클라이언트 수신은 각각 별도로 확인해야 한다.
