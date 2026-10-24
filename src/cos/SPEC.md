# COS 계약

이 모듈은 Chat on Steroids와 Rhino 사이의 COS 통합을 소유한다.
[작업 지침](AGENTS.md)과 [공통 경계](../../SPEC.md)를 함께 따른다.

## 구성

| 위치 | 책임 |
|---|---|
| `cos_host.py`, `cos_worker.py` | 한 stdio host와 Rhino 연결마다 분리된 worker |
| `runtime.py`, `build_catalog.py`, `tool_catalog.json` | 의존 경로, 버전·source fingerprint·공개 schema 검사 |
| `binding_watch.py`, `winpipe.py` | 연결 변경 감시와 Windows 제어 채널 |
| `rhp/` | Rhino 내부 AlmondCOS 명령·host 탐색·문서 binding |
| `tests/`, `run_tests.ps1` | Python·native relay·host 수명·pipe·stdio 검사 |
| `build.ps1`, `runtime-manifest.json` | COS RHP 빌드와 소스·실행 파일 검증 기록 |

## 의존·연결 계약

Python worker는 MCP runtime의 기존 `main`, binding 검증·구성 훅과 완료 receipt를
사용한다. 저장소 잠금·native 완료·자산 helper 정책을 COS에 복제하지 않는다.
RHP는 [공용 Engine](../rhp/Engine/AGENTS.md)을 참조한다. Bridge·Terminal의 구현
소스를 COS에 링크하지 않는다.

catalog 생성은 원본 AST에서 schema만 읽고 DB를 소유하는 MCP server를 import하지
않는다. worker 시작 전 패키지 버전·fingerprint를, 연결 구성 시 실제 schema를
대조한다. 실패하면 모델링 요청을 보내지 않는다.

connection ID와 token·프로세스 identity·저장 문서를 함께 확인한다. 변경된 binding,
미확인 native 결과, 실행 중 작업의 해제·취소에 대한 기존 소유권 규칙을 유지한다.
다른 연결의 DB 접근은 기존 공유 lease·gate를 통과한다.

## 빌드·검증·설치

`configure.ps1`은 이 체크아웃의 catalog와 `cos-plugin.json`을 생성한다. CoS 앱
등록은 하지 않는다. 기존 command는 `../engine/.venv/Scripts/python.exe`와 이 폴더의
`cos_host.py`를 사용하므로 소스 재편 뒤에도 그대로 유지된다.

`build.ps1`은 `rhp/AlmondCOS.csproj`를 staging에서 빌드한 뒤 기존 등록 위치인
`../rhp/AlmondCOS/plugin-runtime`에 배치한다. 로드된 파일을 덮어쓰지 않으며
빌드가 Rhino 등록·실제 로드를 의미하지 않는다. plugin GUID·assembly identity는 유지한다.

COS 전용 C# 변경은 COS manifest만 갱신한다. Engine을 변경하면 두 소비자 RHP를
빌드하고 루트 통합 검사로 DLL 일치까지 확인한다. MCP 공개 도구 변경에 따른
catalog 갱신도 의도적인 통합 변경이다.
