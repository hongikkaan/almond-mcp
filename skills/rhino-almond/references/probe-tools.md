# C# 실행과 결과 읽기

## 직접 계산값 반환

현재 상태·화면은 먼저 [고정 조회 도구](../SKILL.md#almond-mcp-도구-선택)를 사용하라. 그 범위를 넘는 C# 계산은 `execute_rhino_script`의 `public static object Run(RhinoDoc doc)`에서 익명 객체·문자열 키 dictionary·list/1차원 배열·유한 scalar/Guid를 반환하면 응답의 `result`로 받을 수 있다. 작은 계산값을 회수하기 위해 별도 JSON 파일을 만들 필요는 없다.

`result`는 compact JSON 기준 UTF-8 65,536 bytes·container 깊이 16 이내다. Rhino geometry, `JObject/JArray`, 임의 POCO와 lazy enumerable을 그대로 반환하지 말고 필요한 수치·ID를 지원 값으로 투영하라. `status=success`와 `result_error`가 함께 오면 실행은 끝났지만 반환값을 표현하지 못한 것이므로 변경을 자동 재실행하지 마라. `RhinoApp.WriteLine`이 이 결과 채널로 수집된다고 가정하지 마라.

기존 `List<Guid>`는 `guids`와 자동 치수 동작을 유지하며 `result`를 추가하지 않는다. `void`/`null`도 새 결과 필드가 없다. `guids`는 코드가 선언한 ID로 전체 변경 이력이 아니다. 일반 C# 실행은 자동 레이어·Undo 등 부수 효과가 있으므로 계산만 하더라도 읽기 전용 subagent에게 맡기지 마라.

## 제공 probe의 파일 결과

`scripts/almond_probe.py`는 제공 C# 함수를 완전한 실행 소스로 조립하고 해당 실행의 JSON 결과를 읽는다. Rhino 연결이나 실행을 대신하지 않는다. 실제 실행에는 기존 Almond MCP `execute_rhino_script`를 사용하라.

## 호출

1. `almond_project_info` 또는 COS `almond_cos_project_info`에서 실제 `model_path`와 `artifact_dir`를 얻고 `get_rhino_context`로 열린 문서와 대조하라. 출력 경로는 해당 `.almond` 아래 반환된 artifact_dir를 사용하라.
2. artifact_dir 안에 작업 요청 JSON을 작성하라. 아래 경로 자리에는 조회한 절대경로를 넣어라. 도구별 인자는 `options`에 넣어라.
3. prepare를 실행하고 반환된 `script_path`의 **전체 내용**을 기존 `execute_rhino_script`의 `script` 인자로 전달하라. CoS에서는 확인한 connection_id를 함께 사용하라.
4. read로 같은 실행의 결과를 회수하라. MCP 내부 실행 상태와 JSON의 `status`·`data`를 함께 확인하라. 오류 뒤 이전 고정 경로의 결과를 대신 읽어 성공으로 처리하지 마라.

```json
{
  "tool": "outline",
  "model_path": "<project_info에서 확인한 저장된 .3dm 절대경로>",
  "artifact_dir": "<project_info에서 확인한 실제 artifact_dir>",
  "options": {"scope": "selected", "depth": 2, "include_geometry": true}
}
```

스킬 폴더를 작업 디렉터리로 삼아 실행하라. 실행 결과의 manifest_path를 두 번째 명령에 사용하라.

```powershell
python -B scripts/almond_probe.py prepare --job "<요청 JSON 절대경로>"
python -B scripts/almond_probe.py read --manifest "<반환된 manifest_path>"
```

prepare는 매번 새 run_id와 폴더를 만들고 script.cs·query.cs·job.json·result.json 경로를 정한다. `query_path`는 검토할 형상 코드이며, MCP에는 이를 포함한 `script_path`의 전체 내용을 전달하라. 실행기는 Rhino에 두 Newtonsoft JSON 라이브러리가 함께 로드된 경우에도 사용할 참조를 하나로 정해 query를 컴파일한다. 현재 문서의 저장 경로가 요청과 다르면 조회를 중단하고 오류를 기록한다. 기존 결과가 있는 스크립트는 다시 실행하지 않는다.

## probe 파일 결과 해석

| 결과 | 의미·후속 행동 |
|---|---|
| read 종료 코드 0, `status: ok` | 조회·계산이 완료됨. `data`의 실제 측정값, 오류·생략·미확정 항목을 읽어라. 설계 합격 판정이 아니다. |
| 종료 코드 2, `status: error` | 함수 실행 중 오류. message와 MCP 오류를 확인하라. |
| 종료 코드 3, `report_not_ready` | 완성된 결과 파일이 없음. 컴파일 오류·미실행·실행 중·프로세스 중단 등을 구분해야 한다. 타임아웃만으로 롤백됐다고 추정하거나 실행을 반복하지 마라. |
| 종료 코드 1 | 요청·파일·형식·실행 ID·모델 경로·출력 크기 검사가 실패함. 오류를 고친 후 새 요청을 준비하라. |

read는 run_id·도구·모델 경로가 manifest와 일치하는 결과만 받아들인다. 기본 읽기 한도는 262,144 bytes다. 출력이 크면 먼저 각 함수의 요청 범위를 좁혀라. 전체 결과가 꼭 필요할 때만 `--max-bytes`를 늘려라.

제공 함수는 형상·선택·뷰를 편집하지 않는다. 다만 현재 Almond 브리지의 실행 경로 자체가 Undo 기록과 AIA 레이어를 준비할 수 있으므로 문서의 modified 상태까지 보존한다고 가정하지 마라. 따라서 읽기 전용 설계 subagent에게 이 실행 경로를 맡기지 마라. 주 에이전트가 필요한 결과를 확보하여 전달한다. 반환 GUID가 빈 배열인 조회는 정상이다. 보조 코드가 생성하지 않은 객체를 새 GUID로 돌려주지 마라.

## 도구

| tool | 함수·문서 | options |
|---|---|---|
| `sections` | `AlmondTerrain.Sections` · [지형 검사](terrain-probes.md) | `ids`, `axis`, `stations`, 선택적 표본·예산 |
| `vertical-probe` | `AlmondTerrain.VerticalProbe` · [지형 검사](terrain-probes.md) | `ids`, `xy`, 선택적 Z범위·예산 |
| `joint-pairs` | `AlmondJoints.AuditPairs` · [접합부 검사](joint-probes.md) | `pairs`, 선택적 `compare_operations`·공차·예산 |
| `outline` | `AlmondSpatial.Outline` · [블록과 주석](blocks-and-notes.md) | 문서의 Outline 옵션 |
| `resolve-block` | `AlmondSpatial.ResolveBlock` · [블록과 주석](blocks-and-notes.md) | `{"path": ["root GUID", "direct member GUID", "..."]}` |

제공 helper는 `JObject/JArray`를 사용하며 `almond_probe.py`는 기존 파일 결과 경로를 유지한다. 위의 직접 반환 한도와 probe 파일의 읽기 한도는 별개다. 함수를 별도 C# 작업에 직접 결합할 때는 필요한 using 문과 helper class, `Script.Run(RhinoDoc)`을 한 소스로 컴파일하고, 결과를 JSON-safe 값으로 투영하거나 해당 artifact_dir의 명시적 경로에 기록하라.

## 스킬 유지보수에서 코드 변경 후 검증

아래 명령은 사용자가 스킬 코드 유지보수를 별도로 요청한 때의 검증이다. 스킬 폴더·`tests/.artifacts/`에 쓰거나 별도 Rhino를 실행하므로, 현재 문서와 `.almond`만 편집하는 일반 모델링 작업이나 읽기 전용 subagent는 실행하지 마라. 지침 문서만 바꾼 경우에는 관련 링크·내용과 diff를 검토하라.

`python -B tests/test_probe.py`는 요청·실행 ID·모델 경로·결과 상태 검사를 실행한다. Windows에 Rhino 8과 .NET SDK가 있는 환경에서는 `dotnet build tests/NativeSkillCheck.csproj -c Release` 후 `tests/bin/Release/net48/NativeSkillCheck.exe tests "<새 JSON 보고서 절대경로>"`로 기하 회귀 검사를 실행하라. 기본 Rhino 설치 위치가 다르면 `RHINO_SYSTEM_DIR`로 System 폴더를 지정하라.

`python -B tests/verify_pipeline.py`는 다섯 tool의 prepare → C# 컴파일·실행 → read를 확인한다. 검증은 별도 Rhino 프로세스의 자체 문서만 사용하며, 임시 모델과 결과는 `tests/.artifacts/`에 남긴다.
