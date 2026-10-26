# C# 실행과 결과 읽기

## 직접 계산값 반환

현재 상태·화면은 먼저 [고정 조회 도구](tool-map.md#almond-mcp-도구-선택)를 사용하라. 그 범위를 넘는 C# 계산은 `execute_rhino_script`의 `public static object Run(RhinoDoc doc)`에서 익명 객체·문자열 키 dictionary·list/1차원 배열·유한 scalar/Guid를 반환하면 응답의 `result`로 받을 수 있다. 작은 계산값을 회수하기 위해 별도 JSON 파일을 만들 필요는 없다.

`result`는 compact JSON 기준 UTF-8 65,536 bytes·container 깊이 16 이내다. Rhino geometry, `JObject/JArray`, 임의 POCO와 lazy enumerable을 그대로 반환하지 말고 필요한 수치·ID를 지원 값으로 투영하라. `status=success`와 `result_error`가 함께 오면 실행은 끝났지만 반환값을 표현하지 못한 것이므로 변경을 자동 재실행하지 마라. `RhinoApp.WriteLine`이 이 결과 채널로 수집된다고 가정하지 마라.

기존 `List<Guid>`는 `guids`와 자동 치수 동작을 유지하며 `result`를 추가하지 않는다. `void`/`null`도 새 결과 필드가 없다. `guids`는 코드가 선언한 ID로 전체 변경 이력이 아니다. 일반 C# 실행은 Undo 범위에서 동작하고 `List<Guid>` 반환에 자동 치수를 추가할 수 있으므로 계산만 하더라도 읽기 전용 subagent에게 맡기지 마라. 재료별 레이어 자동 생성·이동 후처리는 없으며 [레이어는 호출자가 명시한다](modeling-materials.md).

## 고정 probe 조회

제공 probe는 `get_rhino_probe`로 호출하라. COS에서는 `get_rhino_probe`에 `connection_id`를 함께 전달한다. Bridge에 컴파일된 다섯 함수만 UI thread에서 실행하며 C# 소스·출력 파일 경로를 받지 않는다. Undo 기록·레이어·기하·선택·뷰·문서의 modified 상태를 변경하지 않는다.

1. 이미 확인한 문서를 다시 두 도구로 확인하지 않는다. 프로젝트 정보가 필요하면 `project_info` 한 번으로 live 문서 정보도 얻는다.
2. 아래 인자로 `get_rhino_probe`를 호출하라. 런타임이 연결된 모델 경로를 자동 적용하므로 `expected_model_path`를 기억하거나 입력하지 않는다. 도구별 인자는 `options`에 넣는다.
3. 같은 응답의 `status`, `probe`, `document.path`·단위·공차와 `data`를 확인하라. 이전 실행의 파일로 결과를 대신하지 마라. 기록이 필요하면 `set_working_plan`으로 선택한 Plan의 `artifact_dir`에 저장하라.

```json
{
  "probe": "outline",
  "options": {"scope": "selected", "depth": 2, "include_geometry": true}
}
```

현재 문서의 저장 경로가 다르면 계산 전에 `document_mismatch`로 거절한다. 연결 binding·호출 identity·native 완료 확인은 기존 Engine/COS 경로를 따른다. 요청과 응답은 각각 UTF-8 JSON 262,144 bytes 이내다. 출력이 크면 GUID·표본·깊이·출력 예산을 줄여라.

## 결과 해석

| 결과 | 의미·후속 행동 |
|---|---|
| `status: success` | 계산 완료. `data`의 실제 측정값·오류·생략·미확정 항목을 읽어라. 설계 합격 판정이 아니다. |
| `document_mismatch` | 연결의 모델과 실제 문서를 다시 확인하라. |
| `invalid_arguments` / `probe_too_large` | 인자·요청 범위·출력 예산을 수정하라. |
| `unsupported_probe` | 로드한 Bridge가 `fixed_probes=1`을 지원하지 않는다. 플러그인 갱신·로드 검증이 필요하다. |
| `probe_failed` / `bridge_error` | message와 연결 상태·native 완료를 확인하라. 타임아웃만으로 실행을 자동 반복하지 마라. |

호출 전에 기존 문서 조회로 capability를 확인하여 이전 Bridge에 알 수 없는 probe 요청을 보내지 않는다. 예전 `almond_probe.py`와 C# bootstrap은 제거했다. 고정 조회 도구가 없으면 일반 `execute_rhino_script`로 우회하지 마라.

## 도구

| probe | 함수·문서 | options |
|---|---|---|
| `sections` | `AlmondTerrain.Sections` · [지형 검사](terrain-probes.md) | `ids`, `axis`, `stations`, 선택적 표본·예산 |
| `vertical-probe` | `AlmondTerrain.VerticalProbe` · [지형 검사](terrain-probes.md) | `ids`, `xy`, 선택적 Z범위·예산 |
| `joint-pairs` | `AlmondJoints.AuditPairs` · [접합부 검사](joint-probes.md) | `pairs`, 선택적 `compare_operations`·공차·예산 |
| `outline` | `AlmondSpatial.Outline` · [블록과 주석](blocks-and-notes.md) | 문서의 Outline 옵션 |
| `resolve-block` | `AlmondSpatial.ResolveBlock` · [블록과 주석](blocks-and-notes.md) | `{"path": ["root GUID", "direct member GUID", "..."]}` |

`src/rhp/RhinoAlmondBridge/Probes`의 C# 파일은 이 고정 API의 구현 원본이다. 위의 일반 C# 반환 한도 64 KiB와 고정 probe 응답 한도 256 KiB는 별개다.

## 스킬 유지보수에서 코드 변경 후 검증

아래 명령은 사용자가 스킬 코드 유지보수를 별도로 요청한 때의 검증이다. 스킬 폴더·`tests/.artifacts/`에 쓰거나 별도 Rhino를 실행하므로, 현재 문서와 `.almond`만 편집하는 일반 모델링 작업이나 읽기 전용 subagent는 실행하지 마라. 지침 문서만 바꾼 경우에는 관련 링크·내용과 diff를 검토하라.

저장소의 `src/mcp/tests/test_rhino_observation.py`는 공개 probe 인자·capability·schema를 검사한다. Windows에 Rhino 8과 .NET SDK가 있는 환경에서는 스킬 폴더에서 `dotnet build tests/NativeSkillCheck.csproj -c Release` 후 `tests/bin/Release/net48/NativeSkillCheck.exe tests "<새 JSON 보고서 절대경로>"`로 기하 회귀 검사를 실행하라. 기본 Rhino 설치 위치가 다르면 `RHINO_SYSTEM_DIR`로 System 폴더를 지정하라.

`python -B tests/verify_pipeline.py`는 컴파일된 고정 handler의 다섯 probe와 잘못된 문서·도구 거절을 확인한다. 별도 Rhino 프로세스의 자체 문서에서 기하·속성·선택·레이어·modified·Undo 상태를 전후 대조한다. 임시 모델과 결과는 `tests/.artifacts/`에 남긴다. 실제 RHP의 dispatch와 공개 COS 호출은 별도 로드 검증에서 확인한다.
