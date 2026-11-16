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

`drawing_06-generate_plan_section` tool을 사용한다. 이 도구는 Bridge에 포함된 기존 PlanSection 알고리즘을 Rhino 내부 Python 런타임에서 실행한다. RhinoCode·StartScriptServer나 사용자 작성 script/path를 사용하지 않는다. 연결된 저장 문서의 관측된 clipping GUID와 typed 옵션을 전달하며 목록·점·폴더 입력 창을 열지 않는다.

```json
{
  "operation": "Create",
  "clipping_ids": ["00000000-0000-0000-0000-000000000001"],
  "points": {"00000000-0000-0000-0000-000000000001": [10000, 0, 0]},
  "hatch": true,
  "small_details": false,
  "include_attachments": true
}
```

예시 GUID를 활성 모델이나 현재 Worksession에 첨부한 파일의 클리핑 GUID로 교체한다. 지원 작업은 모델 공간의 Create·Update·Move다. Update는 기존 도면과 같은 클리핑 GUID를 사용하고 points를 생략한다. Move는 요청한 모든 클리핑 GUID의 points를 지정한다. Move를 마친 위치는 이후 Update에 사용된다. PDF·Files는 Rhino에서 스크립트를 직접 실행해 이용한다. 도면을 Layout Detail로 구성한 뒤 `capture_04-defined_view` tool로 용지를 캡처할 수 있다.

`include_attachments=true`는 호출 시 Worksession에 실제로 첨부된 모델에서 형상을 가져온다. 필요한 파일을 먼저 첨부한다. Create에서 생략하거나 false를 전달하면 활성 모델의 형상만 계산한다. Update에서 생략하면 이전 도면의 선택을 유지하며, 범위를 바꾸려면 true 또는 false를 지정한다. 이전 버전의 도면은 활성 모델만 사용한 것으로 처리한다. 첨부 clipping은 활성 모델만 계산하는 경우에도 절단 기준으로 사용할 수 있다. 새 계산 결과가 비어 있으면 Update는 기존 도면을 빈 결과로 교체하며 `object_ids`는 빈 목록이다.

좌표는 현재 문서 단위이며 clipping 원점의 **새 절대 위치**다. GUID별 `[x,y]`(Z=0) 또는 `[x,y,z]`를 전달한다. Update는 저장된 높이를 유지한다. clipping 평면의 로컬 `(u,v)`는 배치점 `(Tx,Ty,Tz)`에 대해 `(Tx+u,Ty-v,Tz)`로 옮겨진다. 비수평 단면의 상하는 clipping의 로컬 Y 방향에 달려 있다. GUID 전체를 먼저 검증하며 중복 GUID는 한 번만 처리한다. Create의 좌표 생략은 기존 draft_plane 또는 원점 배치이므로 여러 도면이 겹치지 않도록 필요한 위치를 지정한다.

로컬 clipping의 `draft_plane`은 UserDictionary의 RhinoCommon `Plane`, 출력의 `ps:placement`는 UserDictionary의 `Point3d`로 저장한다. 기존 user text JSON도 호환을 위해 함께 기록한다. 두 값이 모두 있으면 좌표·(Plane의 경우) 축을 검증하며 불일치는 오류다. typed 값이 없는 구 도면은 기존 JSON으로 읽을 수 있다. 비수평 clipping은 실제 CPlane의 방향을 확인하고 설정 지침에 따라 축을 지정해야 하며, 스크립트가 CPlane을 자동 회전시키지 않는다.

전용 응답의 `status`는 전체 완료 `success`, 일부 완료 `partial`, 취소 `cancelled` 또는 `error`다. `result.status`에는 알고리즘의 completed/partial/cancelled/failed가 보존되고 `results`에는 GUID별 완료·건너뜀·실패·취소, 생성·이동된 object_ids, 배치 평면과 보고서가 들어간다. `algorithm_sha256`는 실제 RHP에 포함된 알고리즘의 해시다. 부분 완료는 이미 완료한 도면을 되돌리지 않는다. 시간 초과·결과 불명은 rollback을 뜻하지 않으며 native 완료 상태와 기존 도면을 확인하기 전 재실행하지 않는다. 실행기 Undo 안에서 기존 `run_selected`가 같은 record를 재사용한다. Rhino에서 스크립트를 직접 실행할 때는 활성 모델의 형상을 사용한다. 첨부 형상을 포함해 생성한 도면을 다시 계산할 때는 `drawing_06-generate_plan_section` tool에서 Update를 사용한다.

거리별 입면선 0.09→0.04mm·darkness 80→45% 기본값은 내부 style 구분과 최종 객체 인쇄 속성에 모두 적용된다. 단면선·해치는 기존 레이어 인쇄 속성을 따른다.

`drawing_06-generate_plan_section` tool의 응답에서 클리핑별 결과를 읽는다. 완료된 항목의 `draw_plane`은 도면이 놓인 수평 평면의 `origin`·`xaxis`·`yaxis`를 XYZ 배열로 돌려준다. Create·Update의 `extraction.layers`와 `source_object_count`는 참여 목록·지원 형상·깊이 필터를 통과해 계산에 들어간 원본의 전체 레이어 경로와 형상 레코드 수다. 블록은 배치와 구성원 경로별로 계산된다. `include_hidden`과 `include_locked`는 숨김·잠금을 제외 조건으로 삼지 않는다는 의미다. `extraction.include_attachments`는 계산에서 첨부 형상을 허용했는지 나타낸다. 참여 목록과 깊이 조건을 적용한 뒤 남은 원본은 앞의 레이어와 객체 수에 반영한다. Move는 이동한 객체의 GUID와 배치 평면을 돌려준다.

## 개발 검사

리포 루트에서 개발 환경을 구성한 뒤 실행한다. 실제 Rhino나 모델을 열지 않는다.

```powershell
./src/mcp/use_offline_environment.ps1 -Development
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m unittest discover -s src/mcp/features/modeling/PlanSection/tests -p 'test_*.py'
```

기존 `TEST.3dm`과 native 검사 도구도 함께 보관하지만, 실제 사용 검증은 사용자가 지정한 연결 문서에서 별도로 수행한다. 모의 API 검사 통과를 실제 단면·UI·PDF 품질 검증으로 간주하지 않는다. 직접 Rhino에서 실행하는 Python 파일과 전용 도구의 embedded 알고리즘은 배포 경로가 다르다. 전용 도구 경로는 `PlanSection.py` 변경 시 Bridge RHP 재빌드와 runtime manifest 갱신이 필요하며, 실제 Rhino 로드 확인은 별도 검증이다. typed Point3d·Plane 조회를 지원하는 `features/context/native/ObjectObservation.cs` 변경도 Bridge 재빌드·로드 검증이 필요하다.
