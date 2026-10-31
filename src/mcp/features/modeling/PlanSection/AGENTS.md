# Plan/Section

Rhino 8 Windows에서 clipping plane으로 단면선·해치·입면선을 생성하는 RhinoCommon Python 스크립트다. Grasshopper 없이 실행한다. 이 파일은 폴더 안내와 에이전트 지침을 함께 담는다. 현재 동작 계약은 [SPEC.md](SPEC.md), 작업 기록은 [log.md](log.md)를 따른다.

## 실행

```text
_-RunPythonScript "C:\TOOL\Rhino\mcp\almond-mcp\src\mcp\features\modeling\PlanSection\PlanSection.py"
```

먼저 Project/CurrentDocument 사용 방식, 이어서 Create·Update·Move·PDF 중 하나를 고른다. Project는 출력된 번호 하나 또는 `All`로 선택하거나 `List`로 목록 창에서 다중 선택한다. 쉼표로 구분한 숫자는 받지 않는다. CurrentDocument는 GUID를 쉼표·공백으로 입력한다. 무인 실행은 `run(doc, operation, clipping_ids, points=..., folder=...)`이다. Worksession 참조 clipping도 포함한다. Create의 Document/Files는 생성 위치를, PickPlacement는 생성 후 도면별 배치점 지정을 선택한다. Update는 기존 저장 위치에서 재계산하며 기존 도면이 없으면 건너뛴다. Move는 재계산 없이 배치점만 옮긴다. PDF는 clipping의 Paper/Scale을 사용한다. 실행 예시는 [README.md](README.md)를 따른다.

출력 객체의 user text는 `ps:source_layer`, `ps:placement`만 저장한다. 재생성 소유 정보는 로컬 Drawing 루트 레이어에 보관하며 참조 clipping의 속성은 수정하지 않는다.

단면선은 로컬 Drawing::Section, 해치는 Drawing::Hatch, 입면선은 Drawing::Elevation에 생성한다. 필요한 원본 객체/레이어/부모 속성을 상속하며 해치는 적용 Section Style의 패턴·스케일을 따른다. 기본/None에는 해치를 만들지 않는다. 해치 레이어의 화면색·인쇄색은 90% 검정, 인쇄 두께는 No Print다. 단면·입면 곡선의 인쇄색과 인쇄 두께는 ByLayer다. 출력은 WorldXY에 정렬·상하 반전되고 Z=0, 객체 이름은 clipping 이름이다. PDF는 clipping 원점을 종이 중심에 두며 종이 밖은 잘라낸다. 원본 문서와 draft_plane을 변경하지 않는다.

## 작업 지침

clipping 대상의 객체·레이어·블록 가지는 숨김/잠금 여부와 관계없이 모델 입력에 포함한다. HLD의 연속 가시 구간 재결합과 중복 제거 뒤 동일 적용 속성끼리 Join한다. SmallDetails=Keep은 유효한 작은 디테일을 유지하고, Omit은 20mm 이하 bbox를 정리하되 긴 윤곽과 양끝이 연결된 bridge를 보호한다. 단면·해치에는 크기 필터를 적용하지 않는다. Rhino 창을 미리 열지 않는 PDF 출력은 같은 폴더의 PlanSectionPDF.ps1을 사용한다. 설치된 Rhino 8 런타임이 필요하며 상세 실행법은 SPEC을 따른다.

- Almond 저장소 루트의 [AGENTS.md](../../../../../AGENTS.md)와 [MCP 지침](../../../AGENTS.md)을 따른다. 작업 전 SPEC의 현재 계약과 관련 코드를 읽는다. 이전 GH 백업을 구현 기준으로 사용하지 않는다.
- Computer Use 없이 Rhino MCP/RhinoCommon으로 작업한다. 동작 변경 전 연구 위임 규칙은 상위 지침을 따른다. 문서 수정 때문에 모델을 실행하거나 기능을 변경하지 않는다.
- 같은 원본 레이어·동일 적용 속성의 surface union, 구멍 보존, Section Style, disjoint mesh별 solid 판정과 Surface의 선 출력 계약을 보존한다. 정렬 전 원본 좌표의 Z를 수정하지 않는다.
- 변경한 계약에 맞는 검사를 선택한다. `tests/test_*.py`는 모델·Rhino 없는 유지보수 검사다. 실제 기능 검증은 사용자가 지정해 연결한 문서에서 한다. 복사된 `TEST.3dm`과 native fixture는 보존 자료이며, 검사만을 위한 별도 Rhino 문서를 자동으로 열지 않는다. 모의 API 검사 통과를 실제 형상 검증으로 보고하지 않는다.
- 실제 문서에서 작업할 때 원본·기존 출력·clipping 속성을 보존한다. 원본 3dm은 별도 요청 없이 저장하지 않는다.
- SPEC은 현재 상태로 갱신한다. `log.md`는 **해야 했던 일 / 작업 방법 / 결과** 세 항목으로 작성한다. 한계는 필요한 경우 결과에 덧붙인다. 커밋별로 덮어쓰고 이전 기록은 Git history에서 확인한다. JSON·명령 로그 원문은 넣지 않고 필요한 경우 임시 결과 폴더의 파일명과 재현 명령을 참조한다.
- 테스트 모델 입력은 기존 `TEST.3dm` **한 개만** 보관한다. 추출 실패 형상·개발용 모델·A/B 분리 파일 등 추가 `.3dm`을 쌓지 않는다. 실제 건물 모델을 코드로 재모델링해서 대체하지 않는다. 한 파일로 재현되지 않는 native 문제는 검증 공백과 필요한 실제 입력을 명시하고 모델 교체/추가가 필요하면 사용자에게 확인한다.
- 테스트 코드는 `tests/`에 둔다. `data/run_native_check.ps1`은 PDF 실행기도 사용하는 공용 native 실행기다. 생성 JSON/PDF/host는 `%TEMP%/PlanSection-checks`, `%TEMP%/PlanSection-runtime`에 두며 커밋하지 않는다. `PLANSECTION_TEST_OUTPUT`으로 결과 폴더를 지정할 수 있다. export/reopen 검사용 임시 `.3dm`은 실행 후 지운다. 이 기준은 과거 산출물 영구 보관 규칙을 대체한다.
- 사용자 작업 원본 모델과 다른 작업 변경은 정리 대상이 아니다. 관련 없는 자료는 수정·삭제하거나 stage하지 않는다. 삭제한 기존 회귀 자료는 Git history에 남지만 현재 검사와 동등한 검증 범위라고 주장하지 않는다.
- stage·commit은 사용자 지정 범위만 포함한다. 커밋 메시지는 `[Plan/Section]`으로 시작한다. 커밋하지 말라는 요청이 있으면 stage도 하지 않는다.
