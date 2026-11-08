# PlanSection

Clipping plane에서 단면선·해치·입면선을 추출한다. 재료·구축 레이어 설정 코드 옆에 기존 `C:\TOOL\Rhino\01_WorkFlow\01_PlanSection` 폴더를 복사한 구현이며 원본 폴더는 그대로 남는다. 형상 계산과 PDF 출력은 기존 코드를 사용한다.

## Rhino에서 사용

작업할 모델을 열고 Rhino 명령행에서 실행한다. 아래는 일상 폴더로 통합된 후의 경로다. 개발 중에는 같은 상대 경로의 개발 워크트리 파일을 실행한다.

```text
_-RunPythonScript "C:\TOOL\Rhino\mcp\almond-mcp\src\mcp\features\modeling\PlanSection\PlanSection.py"
```

1. 먼저 **Project / CurrentDocument** 중 사용 방식을 고른다. 둘 다 현재 연결된 문서를 대상으로 한다.
2. **Create / Update / Move / PDF** 중 작업을 고른다. Project는 출력된 clipping 번호 하나, `All`, 또는 `List`를 입력한다. `List`는 Ctrl/Shift 다중 선택 창을 연다. 쉼표로 구분한 숫자는 받지 않는다. CurrentDocument는 clipping GUID를 쉼표나 공백으로 구분해 입력한다.
3. Create·Update·PDF는 처음 열린 옵션 프롬프트에서 바로 Hatch·Elevation·SmallDetails·선 표현을 바꾸거나 Enter로 확정한다. Esc로 취소하면 옵션 기본값을 저장하지 않는다. Move는 표현 옵션 없이 각 도면의 새 원점을 찍는다.
4. Create는 기본 Document로 현재 문서에 출력한다. 같은 옵션 프롬프트의 Output=Files는 도면별 3dm을 만든다. PDF와 Files는 저장 폴더를 고른다.

| 작업 | 동작 |
|---|---|
| Create | 단면을 생성한다. 같은 clipping의 기존 로컬 도면은 교체한다. PickPlacement=True이면 도면별 원점을 찍고, 기본값 False는 clipping의 draft_plane 또는 WorldXY 원점을 사용한다. |
| Update | 기존 도면의 저장된 위치를 유지해 재계산한다. 도면이 없으면 건너뛴다. |
| Move | 기존 도면의 원점만 XYZ로 옮긴다. 재계산하지 않으며 객체 GUID와 수동 형상·시각 속성 편집을 유지한다. |
| PDF | clipping의 Paper·Scale로 재계산한 벡터 PDF를 만든다. 수동 편집한 출력의 그대로 인쇄 기능은 아니다. 활성 모델과 배치점을 바꾸지 않는다. |

해치는 `Drawing::Hatch`에 생성하며 해당 레이어의 화면색·인쇄색은 90% 검정, 인쇄 두께는 No Print다. 단면 곡선의 인쇄색과 인쇄 두께는 출력 레이어를 따르고, 입면 곡선은 거리별 객체 인쇄 속성을 유지한다. 기존 `Drawing::Hatch` 레이어도 이 설정으로 갱신한다. 모든 Document 출력은 ModelSpace에 생성하고 ViewportId를 비우며, 생성 후 원래 Layout·Detail을 활성 상태로 복원한다.

대상은 현재 문서의 모든 레이어에 있는 clipping이며 Worksession 참조 clipping도 포함한다. 이름·GUID·레이어를 함께 표시하고 원본 레이어를 옮기지 않는다. 도면은 WorldXY와 평행하며 지정 배치점의 Z를 유지한다. 기본 원점과 PDF는 Z=0이다. 저장되지 않은 원본 모델을 자동 저장하지 않는다. 도면 변경은 실행 단위 Undo이며 외부 PDF/3dm 파일은 Undo로 지워지지 않는다. 상세 속성·형상 계약은 [SPEC.md](SPEC.md)에 있다.

원본의 SectionStyle과 표시 속성을 해석하고, 기여 원본의 Name이 모두 같을 때만 출력 Name으로 보존한다. 기여자 중 무명이 있거나 이름이 충돌하면 출력 Name은 빈 값이다. 같은 값으로 합의된 일반 user text·지원되는 UserDictionary 값만 복사하며 충돌 항목과 원본 경로는 `report.metadata_conflicts`에서 확인한다. 생성 출력의 UserDictionary `Floor`는 clipping 이름으로 정하고 원본의 단일·다층 Floor는 건드리지 않는다. Move는 기존 도면의 이름·Floor·기타 수동 속성을 변경하지 않는다.

## 에이전트에서 사용

Almond 전용 `plan_section` 도구를 사용한다. 이 도구는 Bridge에 포함된 기존 PlanSection 알고리즘을 Rhino 내부 Python 런타임에서 실행한다. RhinoCode·StartScriptServer나 사용자 작성 script/path를 사용하지 않는다. 연결된 저장 문서의 관측된 clipping GUID와 typed 옵션을 전달하며 목록·점·폴더 입력 창을 열지 않는다.

```json
{
  "operation": "Create",
  "clipping_ids": ["00000000-0000-0000-0000-000000000001"],
  "points": {"00000000-0000-0000-0000-000000000001": [10000, 0, 0]},
  "hatch": true,
  "elevation": true
}
```

예시 GUID를 실제 관측 GUID로 교체한다. 전용 도구의 범위는 **Create/Update의 Document 출력**이다. Update는 `operation="Update"`로 지정하고 points를 생략한다. Move·PDF·Files는 기존 Rhino 직접 실행에서 제공되지만 이 전용 API에 노출하지 않는다. 출력은 ModelSpace이며 Layout을 자동으로 만들지 않는다. 도면을 Layout Detail로 구성한 뒤 `get_defined_viewcapture(target_kind="layout", target=Layout_ID)`로 용지를 캡처한다.

좌표는 현재 문서 단위이며 clipping 원점의 **새 절대 위치**다. GUID별 `[x,y]`(Z=0) 또는 `[x,y,z]`를 전달한다. Update는 저장된 높이를 유지한다. clipping 평면의 로컬 `(u,v)`는 배치점 `(Tx,Ty,Tz)`에 대해 `(Tx+u,Ty-v,Tz)`로 옮겨진다. 비수평 단면의 상하는 clipping의 로컬 Y 방향에 달려 있다. GUID 전체를 먼저 검증하며 중복 GUID는 한 번만 처리한다. Create의 좌표 생략은 기존 draft_plane 또는 원점 배치이므로 여러 도면이 겹치지 않도록 필요한 위치를 지정한다.

로컬 clipping의 `draft_plane`은 UserDictionary의 RhinoCommon `Plane`, 출력의 `ps:placement`는 UserDictionary의 `Point3d`로 저장한다. 기존 user text JSON도 호환을 위해 함께 기록한다. 두 값이 모두 있으면 좌표·(Plane의 경우) 축을 검증하며 불일치는 오류다. typed 값이 없는 구 도면은 기존 JSON으로 읽을 수 있다. 비수평 clipping은 실제 CPlane의 방향을 확인하고 설정 지침에 따라 축을 지정해야 하며, 스크립트가 CPlane을 자동 회전시키지 않는다.

전용 응답의 `status`는 전체 완료 `success`, 일부 완료 `partial`, 취소 `cancelled` 또는 `error`다. `result.status`에는 기존 알고리즘의 completed/partial/cancelled가 보존되고 `results`에는 GUID별 완료·건너뜀·실패·취소, 생성 object_ids와 보고서가 들어간다. `algorithm_sha256`는 실제 RHP에 포함된 알고리즘의 해시다. 부분 완료는 이미 완료한 도면을 되돌리지 않는다. 시간 초과·결과 불명은 rollback을 뜻하지 않으며 native 완료 상태와 기존 도면을 확인하기 전 재실행하지 않는다. 실행기 Undo 안에서 기존 `run_selected`가 같은 record를 재사용한다. 기존 직접 실행의 `run`·Create/Update/Move/PDF 계약과 출력 알고리즘은 유지한다.

거리별 입면선 0.09→0.04mm·darkness 80→45% 기본값은 내부 style 구분과 최종 객체 인쇄 속성에 모두 적용된다. 단면선·해치는 기존 레이어 인쇄 속성을 따른다.

전용 도구는 작은 결과를 직접 반환하고 큰 결과는 `result_delivery=paged`, `result_id`, `result_sha256`, 처리 수를 반환한다. `get_plan_section_result(result_id, offset=0)`부터 `next_offset`이 null일 때까지 `json_chunk`를 순서대로 연결해 원래 JSON을 회수한다. offset은 UTF-16 단위이며 반환값을 그대로 사용한다. 페이지는 최대 4096 UTF-16 단위로 서로게이트 쌍을 자르지 않으며, SHA256은 원래 UTF-8 JSON 기준이다. 조회는 도면을 재생성하거나 Undo를 시작하지 않는다. 보관은 Bridge 프로세스·동일 문서 인스턴스 내 최대 1시간, 최근 8개·총 64 MiB(UTF-16) 범위로 오래된 결과부터 제거된다. 즉시 회수하고 필요한 경우 작업 산출물에 보존한다. 단일 결과가 보관 한도보다 크면 명시적인 미확인 오류로 남긴다. 만료·재시작·전달 실패를 rollback으로 간주하거나 자동 재생성하지 않는다. 공통 64 KiB·16-container 제한은 유지한다. metadata_conflicts의 기존 64개 표본과 전체 count도 유지한다. native runtime_error는 native_status에 보존하고 외부 status=error/MCP isError=true로 전달하며 partial/cancelled는 구조화된 미완료 결과다.

## 개발 검사

리포 루트에서 개발 환경을 구성한 뒤 실행한다. 실제 Rhino나 모델을 열지 않는다.

```powershell
./src/mcp/use_offline_environment.ps1 -Development
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m unittest discover -s src/mcp/features/modeling/PlanSection/tests -p 'test_*.py'
```

기존 `TEST.3dm`과 native 검사 도구도 함께 보관하지만, 실제 사용 검증은 사용자가 지정한 연결 문서에서 별도로 수행한다. 모의 API 검사 통과를 실제 단면·UI·PDF 품질 검증으로 간주하지 않는다. 직접 Rhino에서 실행하는 Python 파일과 전용 도구의 embedded 알고리즘은 배포 경로가 다르다. 전용 `plan_section` 경로는 `PlanSection.py` 변경 시 Bridge RHP 재빌드와 runtime manifest 갱신이 필요하며, 실제 Rhino 로드 확인은 별도 검증이다. typed Point3d·Plane 조회를 지원하는 `features/context/native/ObjectObservation.cs` 변경도 Bridge 재빌드·로드 검증이 필요하다.
