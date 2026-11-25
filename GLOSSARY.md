# Almond

Rhino 작업의 설계 단위와 사용자가 선택하는 연결 경로를 구분한다.

## 설계 단위

**프로젝트 파일 (Project File)**:
프로젝트 기록에서 파일명으로 식별하는 파일. 카탈로그에 등록된 프로젝트 파일을 Phase와 Scene에서 선택할 수 있다.

**Worksession 첨부 파일**:
현재 Rhino Worksession에 참조로 붙어 있는 모델. 프로젝트 카탈로그 등록 여부는 첨부 상태와 별도로 정해진다.

**Scene**:
특정 공간에서 일어나는 행태·프로그램·장면·가치의 맥락.
_Avoid_: 모델 파일 전체를 뜻하는 Scene

**Ontological_Holon (홀론)**:
Scene을 가능하게 하는 건축 요소와 의미의 묶음. 등록하는 Scene 맥락에 귀속되며 여러 Scene에 참여할 수 있다.
호출 이름은 `ontological_holon`, DB 등록 테이블은 `ontological_holons`를 사용한다. 공개 입력·출력은 `holon_id`·`holon_ids` 계열로 통일한다. 기존 ID 값과 Rhino 내부 저장 형식은 유지한다.
_Avoid_: Design-Component, 설명 없는 Component, 일반 group과 동의어인 Component

**일반 group**:
함께 선택·편집할 실제 객체의 묶음. 의미 단위로 등록되는 것과 별개다.
_Avoid_: 자동 등록된 ontological_holon

**block**:
하나의 실물 형상 정의를 여러 위치·회전·축척으로 재사용하는 구성.
_Avoid_: 자산 배치 대장의 Instance

**구축 상세**
특정 객체의 접합이나 시공 방법을 사람이 읽도록 적은 설명.

**구법 참조**
객체에 적용한 구법을 라이브러리에서 다시 찾을 수 있는 식별 정보.

## 계획과 반복 작업

**Phase**:
프로젝트의 Plan을 묶는 상위 계획 단위. 등록 프로젝트 파일을 여러 개 연결할 수 있으며, Plan은 Phase를 하나 선택하거나 비워 둘 수 있다.

**Plan**:
목표와 Step 정의를 가진 작업 단위로, Dashboard에서는 Task로 표시한다. Plan 상태는 Step 상태와 독립이며 완료는 사용자가 판단한다.

**Step**: Plan 안의 고유 작업 단계. UUID인 step_id와 유형인 step_type/표시 이름을 구분한다. 같은 UUID가 여러 Loop에서 유지된다.

**Loop**: 같은 Plan을 수행하는 회차. 1부터 시작하며 최신 회차만 수정한다. 회차 자체의 진행·중단·완료 상태는 없고 Plan·Step에 상태를 기록한다. loop_no=0은 실행 전 기록의 식별값이며 실행 Loop가 아니다.

**Revision**: Plan·Step 메타데이터가 바뀔 때 자동 저장되는 전체 상태 기록. Plan ID + Loop 번호 + 해당 Loop의 revision 번호로 식별하며 파일 내용이나 Rhino 형상 백업은 아니다.

## 제품과 연결 경로

**Almond**:
Rhino에서 건축 모델·도면·자산을 다루는 전체 작업 환경. RhinoTerminal의 문서 전용 MCP 서버도 이 이름을 사용한다.
_Avoid_: 전체 환경을 뜻하는 beyond, COS

**beyond**:
외부 Codex에서 Almond에 직접 연결할 때 사용하는 MCP 연결기의 이름.
_Avoid_: CoS 연결기의 이름, 전체 Almond 환경의 이름

**CoS**:
Chat on Steroids와 이를 경유하는 Almond MCP 연결기의 이름. 제품·앱·경로를 표기할 때 대소문자를 CoS로 통일한다.
_Avoid_: COS, beyond와 동의어인 CoS

**AlmondRhino**:
beyond와 CoS의 요청을 Rhino 문서에 연결하는 공용 Rhino 플러그인.
_Avoid_: AlmondCOS, CoS 전용 플러그인

**CoS 경유 연결**:
Chat on Steroids를 통해 Almond를 사용하는 경로. 원격 대화에서는 CoS가 제공하는 터널도 이 경로에 속한다.
_Avoid_: Codex 직접 연결

**Codex 직접 연결 (beyond)**:
Rhino가 있는 Windows 컴퓨터의 외부 Codex가 beyond를 통해 Almond에 직접 연결하는 경로. Chat on Steroids 실행을 요구하지 않는다.
_Avoid_: COS 연결, 도구 전달 여부를 확인하지 않은 위임 연결

**RhinoTerminal 연결**:
Rhino 안의 터미널에서 시작하며 그 문서에 묶이는 Almond 작업 경로.
_Avoid_: 외부 Codex 연결

**외부 연결기**:
CoS 경유 연결과 Codex 직접 연결이 함께 사용하는 Almond의 연결 관리 부분.
_Avoid_: 공용 구현을 뜻하는 COS, CoS 앱, RhinoTerminal

**문서 전용 세션**:
시작할 때 선택한 Rhino 문서에 묶인 Almond 작업 세션. RhinoTerminal과 별도 창의 전용 시작기가 이 방식을 사용한다.
_Avoid_: 외부 창이라는 이유만으로 beyond 연결이라고 부르기
