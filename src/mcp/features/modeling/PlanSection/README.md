# PlanSection

Clipping plane에서 단면선·해치·입면선을 추출한다. 재료·구축 레이어 설정 코드 옆에 기존 `C:\TOOL\Rhino\01_WorkFlow\01_PlanSection` 폴더를 복사한 구현이며 원본 폴더는 그대로 남는다. 형상 계산과 PDF 출력은 기존 코드를 사용한다.

## Rhino에서 사용

작업할 모델을 열고 Rhino 명령행에서 실행한다. 아래는 일상 폴더로 통합된 후의 경로다. 개발 중에는 같은 상대 경로의 개발 워크트리 파일을 실행한다.

```text
_-RunPythonScript "C:\TOOL\Rhino\mcp\almond-mcp\src\mcp\features\modeling\PlanSection\PlanSection.py"
```

1. 먼저 **User / Agent** 중 사용 방식을 고른다. User는 기존 clipping 목록 UI, Agent는 GUID 입력 방식이다.
2. **Create / Update / Move / PDF** 중 작업을 고른다. User는 목록 창에서 Ctrl/Shift로 여러 개를 선택한다. Agent는 clipping GUID를 쉼표나 공백으로 구분해 입력한다.
3. Create·Update·PDF는 Enter로 현재 표현 옵션을 사용하거나 Change로 수정한다. Move는 표현 옵션 없이 각 도면의 새 원점을 찍는다.
4. Create는 기본 Document로 현재 문서에 출력한다. Change의 Output=Files는 도면별 3dm을 만든다. PDF와 Files는 저장 폴더를 고른다.

| 작업 | 동작 |
|---|---|
| Create | 단면을 생성한다. 같은 clipping의 기존 로컬 도면은 교체한다. PickPlacement=True이면 도면별 원점을 찍고, 기본값 False는 clipping의 draft_plane 또는 WorldXY 원점을 사용한다. |
| Update | 기존 도면의 저장된 위치를 유지해 재계산한다. 도면이 없으면 건너뛴다. |
| Move | 기존 도면의 원점만 XY로 옮긴다. 재계산하지 않으며 객체 GUID와 수동 형상·시각 속성 편집을 유지한다. |
| PDF | clipping의 Paper·Scale로 재계산한 벡터 PDF를 만든다. 수동 편집한 출력의 그대로 인쇄 기능은 아니다. 활성 모델과 배치점을 바꾸지 않는다. |

대상은 현재 문서의 모든 레이어에 있는 clipping이며 Worksession 참조 clipping도 포함한다. 이름·GUID·레이어를 함께 표시하고 원본 레이어를 옮기지 않는다. 모든 도면은 Z=0이다. 저장되지 않은 원본 모델을 자동 저장하지 않는다. 도면 변경은 실행 단위 Undo이며 외부 PDF/3dm 파일은 Undo로 지워지지 않는다. 상세 속성·형상 계약은 [SPEC.md](SPEC.md)에 있다.

## 에이전트에서 사용

기존 `execute_rhino_script(language="python")` 경로에서 아래처럼 스크립트를 읽고 `run`을 호출한다. 런타임이 검증해 제공한 `doc`를 전달하며 다른 문서를 자동으로 열지 않는다. 이 함수는 목록·점·폴더 입력 창을 열지 않는다. 일반 `main()`의 Agent 선택은 GUID를 직접 타이핑하는 사용자용 진입이며, 무인 실행은 `run()`이다.

```python
import json
import runpy

ps = runpy.run_path(r"C:\TOOL\Rhino\mcp\almond-mcp\src\mcp\features\modeling\PlanSection\PlanSection.py")
ids = ["첫 번째 clipping GUID", "두 번째 clipping GUID"]  # 실제 GUID로 교체
result = ps["run"](doc, "Create", ids,
                   points={ids[0]: [10000, 0], ids[1]: [20000, 0]})
print(json.dumps(result, ensure_ascii=False))
```

작업별 호출은 다음과 같다. 좌표는 현재 문서 단위이며 clipping 원점의 **새 절대 위치**다. 배치점은 GUID별 `[x,y]` 또는 `[x,y,0]`으로 전달한다.

```python
result = ps["run"](doc, "Update", ids)
result = ps["run"](doc, "Move", ids, points={ids[0]: [12000, 0], ids[1]: [22000, 0]})
result = ps["run"](doc, "PDF", ids, folder=r"프로젝트 Plan 산출물의 기존 폴더")
```

GUID 전체를 먼저 검증하며 중복 GUID는 한 번만 처리한다. Move는 모든 GUID의 좌표가 필요하다. Update·PDF에 이동 좌표를 주면 오류다. Create의 좌표 생략은 기존 draft_plane 또는 원점 배치다. 여러 clipping의 기본 원점이 같으면 출력이 겹치므로 필요한 위치를 각각 전달한다.

결과의 `status`는 `completed` / `partial` / `cancelled`, `results`에는 GUID별 완료·건너뜀·실패·취소와 생성 객체 ID 또는 파일 경로·보고서가 들어간다. 한 도면 실패가 이미 완료한 다른 도면을 되돌리지 않는다. MCP 실행이 timeout이면 재실행하지 말고 `get_rhino_execution`으로 완료를 회수한다. 파일 출력 전에 `set_working_plan`으로 프로젝트 산출물 폴더를 정한다.

## 개발 검사

리포 루트에서 개발 환경을 구성한 뒤 실행한다. 실제 Rhino나 모델을 열지 않는다.

```powershell
./src/mcp/use_offline_environment.ps1 -Development
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m unittest discover -s src/mcp/features/modeling/PlanSection/tests -p 'test_*.py'
```

기존 `TEST.3dm`과 native 검사 도구도 함께 보관하지만, 실제 사용 검증은 사용자가 지정한 연결 문서에서 별도로 수행한다. 모의 API 검사 통과를 실제 단면·UI·PDF 품질 검증으로 간주하지 않는다. 이 Python 스크립트 변경은 RHP 빌드나 플러그인 등록을 요구하지 않는다.
