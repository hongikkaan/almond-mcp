# Almond 공통 구조

이 문서는 모듈 사이의 공통 경계와 문서의 진입점만 유지한다.
기능·검사·내부 구조의 변경은 해당 모듈 문서에 기록한다.

| 모듈 | 책임 | 상세 계약·작업 지침 |
|---|---|---|
| MCP | 모델링 도구·계산·자산 API, CLI와 Python 실행기 | [SPEC](src/mcp/SPEC.md) · [AGENTS](src/mcp/AGENTS.md) |
| COS | Chat on Steroids host/worker와 Rhino COS 플러그인 | [SPEC](src/cos/SPEC.md) · [AGENTS](src/cos/AGENTS.md) |
| RHP | Rhino Bridge·패널·Terminal과 공용 native Engine | [SPEC](src/rhp/SPEC.md) · [AGENTS](src/rhp/AGENTS.md) |
| 호환 진입점 | 기존 시작 버튼과 Python 환경 위치 보존 | [설명](src/engine/README.md) |

## 공통 경계

- COS는 MCP runtime의 확장 훅과 공용 native Engine을 사용한다. MCP는 COS 구현을 import하지 않고 native Engine은 개별 호스트를 참조하지 않는다.
- Bridge는 MCP 소유의 C# 모델링 코드·재료 정책을 컴파일한다. Python 패키지는 RHP 소유의 공용 패널 웹 원본을 포함한다. 공유 원본을 복제하지 않는다.
- 모델 폴더의 `.almond/scene.sqlite3`와 `.almond/tmp`는 공유한다. 연결별 token·session·call과 프로세스 identity를 구분하며 잠금·lease·native 완료 확인을 유지한다.
- 객체 identity는 정규화한 모델 경로와 Rhino GUID의 조합이다. timeout은 rollback이나 자동 재실행 허가가 아니다.
- 기존 사용자 변경·모델·DB·라이브러리, 공개 tool schema, plugin identity와 Undo/Redo 계약을 보존한다.
- 모듈 전용 테스트와 검증 기록은 모듈이 소유한다. 루트 `tests/`는 여러 모듈의 계약을 확인한다. 워크트리는 실행 중 Rhino와 모델 DB를 자동 격리하지 않는다.

## 공통 안내

- [작업 원칙·설치·배포](AGENTS.md)
- [모듈별 개발·병렬 작업·이전 경로 대응](docs/development/module-boundaries.md)
- [기능별 사용 문서](README.md)

모듈 내부만 변경되는 작업은 이 문서를 수정할 필요가 없다. 공통 의존 방향이나
설치·저장소 계약이 실제로 바뀔 때만 함께 갱신한다.
