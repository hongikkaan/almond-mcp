# SKILL 워크트리와 고정 probe의 실제 Rhino 적용

2026-10-23, PR #4의 [고정 probe 변이 실행 경로 지적](https://github.com/hongikkaan/almond-mcp/pull/4#discussion_r4357113053)을 수정한 뒤 확인한 기록이다.
기준 main은 `e41e4e46c7b22d3b895b1e33c49b6c112915a1ff`이며 작업 브랜치는 `work/skill`이다.

## 실행 경로

`C:\TOOL\Almond-worktrees\skill`에 독립 체크아웃과 Python 3.12.12 환경을 만들었다.
기존 `C:\TOOL\Rhino\mcp\almond-mcp`의 로컬 `skill` 브랜치와 사용자 파일은 보존했다.

| 구성요소 | 실제 확인 경로 |
|---|---|
| Bridge RHP | `C:\TOOL\Almond-worktrees\skill\src\rhp\RhinoAlmondBridge\plugin-probe-20261023\RhinoAlmondBridge.rhp` |
| COS RHP | `C:\TOOL\Almond-worktrees\skill\src\rhp\AlmondCOS\plugin-build\AlmondCOS.rhp` |
| 로드된 Engine | `C:\TOOL\Almond-worktrees\skill\src\rhp\AlmondCOS\plugin-build\Almond.Engine.dll` |
| Python host/worker | `C:\TOOL\Almond-worktrees\skill\src\engine\.venv\Scripts\python.exe` |
| editable package | `C:\TOOL\Almond-worktrees\skill\src\mcp\almond_mcp` |

기존 Bridge/COS 레지스트리 키를 백업하고 두 `PlugIn\FileName`을 위 경로로 변경했다.
Bridge/COS 출력의 Engine SHA-256 일치를 확인했다. 등록 후 새 Rhino PID 7744에서
실제 로드된 RHP·Engine 모듈 경로를 확인했다. Rhino 버전은 `8.34.26223.11001`이다.
Bridge MVID는 `bf20744d-ce8c-4720-bc66-f3edf23973be`,
COS MVID는 `ff979ac7-f465-41c7-9b16-6970c95c9a0a`다.

기존 `RHINO_MCP_*_DIR` 환경을 그대로 전달했다. native validator·definition runner·
drawing asset manager의 라이브러리 경로 5곳이 기존 설정과 일치했다.
Python public client·host·worker 세 프로세스도 이 워크트리의 venv를 사용했다.

## 검증 결과

| 검증 | 결과 |
|---|---|
| Python/COS/Engine 관련 검사 | 77개와 13 subtest 통과. 새 체크아웃의 COS data 폴더가 없던 stdio fixture를 보완한 뒤 해당 1개도 통과 |
| inert catalog | 60개 schema, package/source fingerprint 및 worker schema 검사 유지 |
| Bridge/COS 빌드 | 성공. Bridge의 기존 `ResultsPanel.Load` 경고 1개, COS 경고 0개 |
| 고정 handler fixture | 5종 전부 통과; 모델 경로 불일치·알 수 없는 도구 거절 및 문서 상태 보존 확인 |
| native Undo·결과 반환 회귀 | 별도 headless 문서 40/40 통과 |
| native context/image 회귀 | headless 9/9, 실제 viewport 4/4 통과 |
| 실제 Bridge dispatch | 알 수 없는 request type을 `unsupported_request`로 거절하고 문서 상태 보존 |
| 공개 COS stdio | 63개 도구, 실제 연결·project_info·context·5종 probe·viewport image·disconnect 성공 |

공개 호출은 `data/probe-review/fixture.3dm`의 자체 큐브·블록을 대상으로 했다.
sections는 닫힌 단면 2개, vertical-probe는 표본 중복 깊이 10,
joint-pairs는 교차 체적 500, resolve-block은 정확한 루트 블록 ID를 반환했다.
잘못된 문서 경로와 빈 단면 위치도 native 오류로 거절했다.

독립 native snapshot으로 공개 호출 전후 문서 identity·기하 CRC·속성·선택·
레이어·뷰/카메라·modified·Undo 상태를 비교했다. **변경 필드 0개**다.
레이어 1개, 최상위 객체 3개, `modified=false`, `current_record=0`,
`next_record=156`을 유지했다. A-WALL/A-STRC/A-GLAZ는 생성되지 않았다.
fixture 파일의 SHA-256도 같았다.

MCP JPEG 262×348, 17,917 bytes를 수신·디코딩하고 실제 이미지를 열어 확인했다.
이는 테스트 큐브가 보이는 현재 뷰의 전달 검증이며 사용자 모델의 설계 검수가 아니다.

## 근거와 적용 범위

재현 코드·등록 백업·빌드 로그·공개 호출·독립 snapshot은 ignored
`data/probe-review/`의 `activate_worktree.ps1`, `bootstrap_rhino.py`,
`verify_public.py`, `bridge-before.reg`, `cos-before.reg`, `bootstrap.json`,
`public-report.json`, `native-final.json`, `viewport.jpg`에 남겼다.
고정 handler fixture 결과는 `skills/rhino-almond/tests/.artifacts/`에 있다.

기존 사용자 Rhino PID 10524는 다른 모델을 열고 있어 종료하거나 assembly를
교체하지 않았다. 새 등록은 이후 정상적으로 시작하는 Rhino에 적용되며, 이번에는
별도 프로세스에서 그 로드와 공개 COS 연결을 실제 확인했다.
상위 Rhino 저장소는 다른 작업 브랜치와 미커밋 변경이 있어 gitlink를 수정하지 않았다.

검증은 새 워크트리의 `src/cos/cos-plugin.json`과 같은 command/args의 공개 stdio
클라이언트를 사용했다. CoS 앱의 기존 플러그인 등록은 이 검증과 별도다.
앱 설정 폴더 `chat-on-steroids`는 현재 Core 승인 루트 밖이어서 기존 등록을 읽거나
변경하지 못했다. `src/cos/cos-plugin.json`은 적용할 새 경로로 준비돼 있다.
