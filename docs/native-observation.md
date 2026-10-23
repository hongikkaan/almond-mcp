# 현재 문서·화면 조회와 C# 결과 반환

기존 모델 작업에서는 먼저 `almond_project_info`로 연결을 확인하고,
`get_rhino_context`로 실제 활성 문서를 조회한다. 현재 화면이 판단에 필요할 때
`get_rhino_viewport_image`를 호출한다. COS의 공개 이름은 각각
`almond_cos_project_info`, `almond_cos_get_rhino_context`,
`almond_cos_get_rhino_viewport_image`이며 기존과 같이 `connection_id`를 전달한다.

두 조회는 기존 Engine의 문서 binding·UI thread·호출 identity·native 완료 확인을
거친다. 파일 경로를 임의로 골라 다른 모델을 조회하는 기능은 없다.

## 현재 상태

```json
{"selection_limit": 50}
```

`get_rhino_context`는 다음 구조의 JSON 문자열을 반환한다.

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
{"max_width": 1280, "max_height": 960}
```

`get_rhino_viewport_image`는 **MCP image content** 한 개와 JSON metadata를 반환한다.
두 입력은 각각 64–2048 정수이며, 원래 화면의 비율을 유지하고 확대하지 않는다.
JPEG 원본 한도는 4 MiB이다. 모델/viewport identity와 원본 화면 크기를 metadata에
기록하고, 실제 JPEG 크기는 `image.width`와 `image.height`에 기록한다.
`structuredContent`에는 base64 데이터를 중복해서 넣지 않는다.

화면을 얻기 위해 zoom, Named View, display mode, clipping, selection을 바꾸지 않는다.
페이지 뷰에서는 전체 페이지를 캡처하므로 `viewport`는 MainViewport를 설명하며,
활성 detail ID는 `active_viewport_id`에 따로 표시한다. `capture_scope`와 `warnings`로
이 차이를 알 수 있다. 상태 도구의 `viewport`는 활성 detail 자체를 가리킬 수 있다.

뷰가 없거나 bitmap/JPEG 생성이 실패하거나 캡처 중 문서·뷰가 바뀌면 이미지 없이
`isError`와 오류 JSON을 반환한다. Python 측에서도 JPEG 형식·실제 크기·한도를
검사한다. 기존 경로의 오래된 이미지로 대체하지 않는다. 의도적으로 카메라를
움직이며 여러 패스를 얻으려면 기존 `capture_conditioning_pass`를 사용한다.
이 도구의 카메라 복원은 best effort이다.

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

재검토 근거와 범위 선택은 [작업 계획](native-observation-plan.md), 실제 실행한 검증과
남은 항목은 [검증 기록](native-observation-verification.md)에 기록했다.
Python 검증은 실제 MCP content/schema와 위조·누락 이미지/크기 오류를 다룬다.
`tests/rhp/RhinoAlmondBridge/script_executor_undo`의 native suite는 기존 Undo 회귀,
반환 제한과 headless 조회를 검사하고, `ObservationTests.RunViewport(doc)`는 호출자가
지정한 실제 문서의 geometry/attributes/layer/view/selection/Undo 상태를 전후 비교한다.
후보 RHP 빌드, 실제 로드 경로, 실제 클라이언트 수신은 각각 별도로 확인해야 한다.
