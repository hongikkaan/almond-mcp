# Almond — 개인 Rhino 작업 환경

Rhino 8의 모델링·도면·자산·구조해석을 MCP, Engine, COS와 연결하는 개인 포크입니다.
Bridge·패널·RhinoTerminal은 하나의 RHP, COS는 별도 RHP로 구성됩니다.

- [작업 지침·설치·실행·빌드·검증](AGENTS.md)
- [저장소 구조와 데이터 계약](SPEC.md)
- [모듈별 개발·테스트와 워크트리 병렬 작업](docs/development/module-boundaries.md)
- [Rhino 패널 사용법](docs/assets/rhino-archive-quickstart.md)
- [자산 검색·배치·도면·출처 관리](docs/assets/assets-and-drawings.md)
- [Scene·Component·계획·Drawing Sheet](docs/modeling/component-system.md)
- [현재 문서·화면·고정 probe·C# 반환값](docs/modeling/native-observation.md)
- [구조해석 사용법](docs/structure/structural-tutorial.md) · [native solver](docs/structure/native-solver.md) · [Karamba 경로](docs/structure/structural-validation.md) · [설계 코드](docs/structure/design-codes.md)
- [구법 안내](docs/construction/construction-guidance.md) · [구법 참조표](docs/construction/construction-spec-register.md)

최초 설치 후에는 Rhino를 닫고 이 일상 폴더에서 `git pull --ff-only`한 뒤 다시 시작합니다.
Git에 포함된 `src/rhp/*/plugin-runtime`을 사용하므로 매번 빌드하거나 등록할 필요가 없습니다.
