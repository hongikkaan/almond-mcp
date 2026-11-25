# Almond — 개인 Rhino 작업 환경

Rhino 8의 모델링·도면·자산·구조해석을 공통 MCP 도구·Engine·외부 연결기로 구성한 개인 포크입니다.
Bridge·패널·RhinoTerminal은 하나의 RHP, AlmondRhino는 별도 RHP로 구성됩니다.

- [작업 지침·설치·실행·빌드·검증](AGENTS.md)
- [저장소 구조와 데이터 계약](SPEC.md)
- [용어](GLOSSARY.md) · [RhinoTerminal·beyond 연결 경로](src/mcp/runtime/CONNECTION-SPEC.md)
- [모듈 소유권과 의존 방향](SPEC.md#소유권과-의존-방향)
- [Codex·외부 MCP 클라이언트 연결](src/beyond/EXTERNAL_CLIENTS.md)
- [Rhino 패널 사용법](src/mcp/features/assets/guides/rhino-archive-quickstart.md)
- [DB Dashboard — SQLite 자료·구조 자동 탐색](src/mcp/runtime/dashboard/README.md)
- [자산 검색·배치·도면·출처 관리](src/mcp/features/assets/SPEC.md)
- [RhinoBeyond 스킬](.agents/skills/rhinobeyond/SKILL.md) · [Component 등록·계층·동기화](src/mcp/features/components/SPEC.md) · [Phase·Plan·Step 저장·참조](src/mcp/SPEC.md#계획-저장참조)
- [PlanSection: 단면 생성·업데이트·배치점 이동·PDF](src/mcp/features/modeling/PlanSection/README.md)
- [현재 문서·화면·고정 probe·C# 반환값](src/mcp/rhino/OBSERVATION-SPEC.md)
- [공식 Rhino CLI·Python/C# 실행 지침](src/mcp/RHINOCODE-INSTRUCTIONS.md) · [구현 범위·현재 검증 상태](src/mcp/runtime/RHINOCODE-SPEC.md)
- [구조해석 사용법](src/mcp/features/structure/guides/tutorial.md) · [native solver](src/mcp/features/structure/SPEC.md) · [Karamba 경로](src/mcp/features/structure/validation/SPEC.md) · [설계 코드](src/mcp/features/structure/PROFILES-SPEC.md)
- [구법 안내](src/mcp/features/guidance/construction-guide.md) · [구법 참조표](src/mcp/profiles/construction_system/SPEC.md)

Codex의 직접 연결 주소와 복구 기록을 새 위치로 옮길 때는 [일회성 전환 절차](src/beyond/EXTERNAL_CLIENTS.md#기존-설치-전환)를 따릅니다.
`almondconnect`가 없으면 [AlmondRhino 등록 경로](AGENTS.md#일상-실행과-최초-설치)부터 확인합니다. 올바른 RHP가 아직 로드되지 않은 프로세스에서는 공식 `Rhino.PlugIns.PlugIn.LoadPlugIn(fullPath)`로 기존 파일을 직접 로드할 수 있습니다. Python에서는 반환값이 `(LoadPlugInResult, Guid)`이며, 로드 후 명령 존재와 실제 assembly 경로를 확인합니다. 이 방식은 로드된 구형 assembly를 교체하는 기능이 아닙니다.
이미 새 경로로 등록된 환경과 이후 업데이트는 Rhino 종료 → `git pull --ff-only` → Rhino 시작 순서입니다.
Git에 실행 파일이 포함되어 있어 일반 업데이트마다 빌드하거나 재등록할 필요는 없습니다.

Python 의존성이 바뀐 업데이트에서는 `git pull` 뒤, 클라이언트를 시작하기 전에 환경도 확인합니다.

```powershell
./src/mcp/rebuild_environment.ps1 -VerifyOnly
```

이 명령은 일상 실행용 `src/engine/.venv`와 이미 존재하는 루트 `.venv`를 모두 검사합니다. 루트 환경은 저장소 셸·`uv run`에서 사용하며, Rhino 실행기·beyond·solver는 일상 환경을 사용합니다. 검사에서는 패키지나 lock을 변경하지 않으므로 연결 중에도 실행할 수 있습니다. `uv.lock`과 설치 목록, 중복 패키지, Python 버전, editable 출처와 의존성 메타데이터를 확인합니다.

검사가 실패하면 해당 환경의 MCP 클라이언트·host/worker와 관리형 Rhino 연결을 정상 종료한 상태에서 `./src/mcp/rebuild_environment.ps1`을 실행합니다. 두 환경 중 하나라도 사용 중이면 변경 전에 경로·PID를 알리고 중단합니다. 정리 후 같은 검증까지 통과해야 완료됩니다. 없는 루트 `.venv`는 만들지 않으며, `-Development`는 해당 체크아웃의 `data/development/.venv`만 처리합니다. 일반 시작은 의존성을 자동 동기화하지 않습니다. 의존성 변경을 전달하는 작업자는 두 환경의 검증까지 마친 뒤 사용자에게 업데이트 완료를 보고합니다.

프로젝트 DB는 `.almond/scene.sqlite3`를 사용합니다. 기존 확장자 없는 `DB`의 파일명 이전과 작업자료·임시자료 정리 기준은 [조회와 작업자료 계약](src/mcp/SPEC.md#조회와-작업자료-계약)을 따릅니다. 구형 `.almond/tmp/calls`에 남은 보고서·백업은 자동 삭제하지 않고 현재 자료 참조와 함께 이전합니다.
