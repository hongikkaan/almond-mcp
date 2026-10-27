# Almond

Rhino 작업의 설계 단위와 사용자가 선택하는 연결 경로를 구분한다.

## 설계 단위

**Scene**:
특정 공간에서 일어나는 행태·프로그램·장면·가치의 맥락.
_Avoid_: 모델 파일 전체를 뜻하는 Scene

**ontological_component**:
Scene을 가능하게 하는 건축 요소와 의미의 묶음. 등록하는 Scene 맥락에 귀속되며 여러 Scene에 참여할 수 있다.
_Avoid_: Design-Component, 설명 없는 Component, 일반 group과 동의어인 Component

**일반 group**:
함께 선택·편집할 실제 객체의 묶음. 의미 단위로 등록되는 것과 별개다.
_Avoid_: 자동 등록된 ontological_component

**block**:
하나의 실물 형상 정의를 여러 위치·회전·축척으로 재사용하는 구성.
_Avoid_: 자산 배치 대장의 Instance

**Almond Instance**:
기존 자산의 Scene 내 배치를 나타내는 별도 기록. 실제 Rhino block instance와 구별한다.
_Avoid_: 모든 모델 객체의 필수 대장

## 연결 경로

**CoS 경유 연결**:
Chat on Steroids를 통해 Almond를 사용하는 경로. 원격 대화에서는 CoS가 제공하는 터널도 이 경로에 속한다.
_Avoid_: Codex 직접 연결

**Codex 직접 연결**:
Rhino가 있는 Windows 컴퓨터의 Codex가 Almond에 직접 연결하는 경로. Chat on Steroids 실행을 요구하지 않는다.
_Avoid_: COS 연결, 도구 전달 여부를 확인하지 않은 위임 연결

**RhinoTerminal 연결**:
Rhino 안의 터미널에서 시작하며 그 문서에 묶이는 Almond 작업 경로.
_Avoid_: 외부 Codex 연결

**외부 연결기**:
CoS 경유 연결과 Codex 직접 연결이 함께 사용하는 Almond의 연결 관리 부분.
_Avoid_: CoS 앱, RhinoTerminal
