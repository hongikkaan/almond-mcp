# Almond — 개인 Rhino 작업 환경

Rhino 8의 모델링·도면·자산·구조해석을 공통 MCP 도구·Engine·외부 연결기로 구성한 개인 포크입니다.
Bridge·패널·RhinoTerminal은 하나의 RHP, AlmondRhino는 별도 RHP로 구성됩니다.

- [작업 지침·설치·실행·빌드·검증](AGENTS.md)
- [저장소 구조와 데이터 계약](SPEC.md)
- [용어](GLOSSARY.md) · [RhinoTerminal·beyond·CoS 연결 경로](src/mcp/runtime/CONNECTION-SPEC.md)
- [모듈 소유권과 의존 방향](SPEC.md#소유권과-의존-방향)
- [Codex·CoS·외부 MCP 클라이언트 연결](src/cos/EXTERNAL_CLIENTS.md)
- [Rhino 패널 사용법](src/mcp/features/assets/guides/rhino-archive-quickstart.md)
- [자산 검색·배치·도면·출처 관리](src/mcp/features/assets/SPEC.md)
- [Rhino 모델링 지침](src/mcp/BASIC-INSTRUCTIONS.md) · [Component 등록·계층·동기화](src/mcp/features/components/SPEC.md) · [Phase·Plan·Step 저장·참조](src/mcp/SPEC.md#계획-저장참조)
- [PlanSection: 단면 생성·업데이트·배치점 이동·PDF](src/mcp/features/modeling/PlanSection/README.md)
- [현재 문서·화면·고정 probe·C# 반환값](src/mcp/rhino/OBSERVATION-SPEC.md)
- [공식 Rhino CLI·Python/C# 실행 지침](src/mcp/features/guidance/guides/references/rhino-scripting.md) · [구현 범위·현재 검증 상태](src/mcp/runtime/RHINOCODE-SPEC.md)
- [구조해석 사용법](src/mcp/features/structure/guides/tutorial.md) · [native solver](src/mcp/features/structure/SPEC.md) · [Karamba 경로](src/mcp/features/structure/validation/SPEC.md) · [설계 코드](src/mcp/features/structure/PROFILES-SPEC.md)
- [구법 안내](src/mcp/features/guidance/construction-guide.md) · [구법 참조표](src/mcp/profiles/construction_system/SPEC.md)

기존 AlmondCOS 설치에서 이번 버전으로 업데이트할 때는 등록 경로가 AlmondRhino로 바뀌므로 **한 번 재등록해야 합니다**.
Rhino와 해당 MCP 연결을 정상 종료한 뒤 일상 폴더 `C:\TOOL\Rhino\mcp\almond-mcp`에서 다음 순서로 실행하고 Rhino를 다시 시작합니다.

```powershell
git pull --ff-only
./src/rhp/tools/install_runtime.ps1
./src/rhp/tools/install_runtime.ps1 -VerifyOnly
```

설치 스크립트는 기존 등록을 `data/runtime-install`에 백업하고 동일 GUID의 경로를 `src/rhp/AlmondCOS/plugin-runtime/AlmondCOS.rhp`에서 `src/rhp/AlmondRhino/plugin-runtime/AlmondRhino.rhp`로 전환하며 명령 캐시도 갱신합니다.
`-VerifyOnly`는 확인만 하므로 최초 전환에는 그 앞의 설치 명령이 필요합니다.
`almondconnect`가 없으면 이 등록 경로부터 확인합니다. 올바른 RHP가 아직 로드되지 않은 프로세스에서는 공식 `Rhino.PlugIns.PlugIn.LoadPlugIn(fullPath)`로 기존 파일을 직접 로드할 수 있습니다. Python에서는 반환값이 `(LoadPlugInResult, Guid)`이며, 로드 후 명령 존재와 실제 assembly 경로를 확인합니다. 이 방식은 로드된 구형 assembly를 교체하는 기능이 아닙니다.
이미 새 경로로 등록된 환경과 이후 업데이트는 Rhino 종료 → `git pull --ff-only` → Rhino 시작 순서입니다.
Git에 실행 파일이 포함되어 있어 일반 업데이트마다 빌드하거나 재등록할 필요는 없습니다.
프로젝트 DB는 `.almond/scene.sqlite3`를 사용합니다. 기존 확장자 없는 `DB`의 파일명 이전과 작업자료·임시자료 정리 기준은 [조회와 작업자료 계약](src/mcp/SPEC.md#조회와-작업자료-계약)을 따릅니다. 구형 `.almond/tmp/calls`에 남은 보고서·백업은 자동 삭제하지 않고 현재 자료 참조와 함께 이전합니다.
