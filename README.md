# Almond — 개인 Rhino 작업 환경

Almond MCP와 사용자 제작 Engine·COS·RhinoTerminal을 함께 관리하는 개인 포크입니다.
Engine과 MCP는 별도 코드로 유지합니다. 배포 자동화는 사용하지 않습니다.

- [구조와 구성요소 계약](SPEC.md)
- [환경 구성·빌드·검증](LOCAL_SETUP.md)
- [작업 지침](AGENTS.md)
- [Rhino Archive 사용법](docs/rhino-archive-quickstart.md)

| 위치 | 내용 |
|---|---|
| `src/engine` | 실행기, 공유 저장소 연결, Almond.Engine.dll |
| `src/mcp/almond_mcp` | Python MCP 서버·구조해석 계산·라이브러리 API |
| `src/cos` | COS Python host/worker |
| `src/rhp` | Rhino 플러그인과 패널 소스·로컬 빌드 결과 |
| `asset` | 유형별 라이브러리 원본·manifest·capsule |
| `tests` | engine/mcp/cos/rhp별 검증 |
| `tools` | 빌드·자산 생성·검증 도구 |
| `docs`, `examples` | 기능 문서와 사용 예제 |

환경은 `src/engine/rebuild_environment.ps1`로 준비합니다.
외부 실행기는 `src/engine/Almond 시작.cmd`, Rhino 내부 실행기는 `RhinoTerminal` → `almond`입니다.
설치된 Rhino bridge와 COS/RhinoTerminal의 등록 상태는 [설치 문서](LOCAL_SETUP.md)를 따릅니다.

이 리포는 상위 Rhino 리포의 `mcp/almond-mcp` 서브모듈입니다.
코드 라이선스와 자산·vendor 고지는 [LICENSE](LICENSE), [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)에 유지합니다.
