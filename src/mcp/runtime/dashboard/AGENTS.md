# Dashboard 작업 지침

이 폴더는 로컬 SQLite 조회 프로그램이다. 실행 진입점은 상위 폴더의 `dashboard.ps1`과 `Almond DB Dashboard.cmd`, 사용법과 화면 계약은 [README.md](README.md)를 따른다.

## DB 보존

- 선택한 기존 파일을 `Database.connect()`의 `mode=ro`·`query_only=ON`으로 조회한다. 커밋된 WAL을 읽기 위해 `immutable`은 사용하지 않는다.
- Dashboard와 실행기에 DB 생성·편집·삭제·migration 기능을 넣지 않는다. `AlmondStore` 생성자는 스키마를 변경하므로 호출하지 않는다. 과거 호환 뷰도 조회 대상이며 여기서 제거하지 않는다.
- HTTP POST는 파일 선택만 담당한다. SQL 실행·저장 API를 추가하지 않는다. 파일 선택 취소·실패 시 현재 DB를 유지한다.
- schema·열·관계는 선택 파일에서 읽는다. 도메인 탭은 실제 존재하는 테이블과 필드에 맞춰 조회하며 미기록 값이나 과거 Loop 자료를 현재 값으로 만들어 채우지 않는다.
- 조회 시간·행·셀 크기 제한, loopback 바인딩, 실행별 토큰과 Host/Origin 검사를 보존한다. 다른 연결의 잠금을 해제하거나 프로세스를 종료하지 않는다.

## 실행과 검증

- 사용자의 명시적 선택에 따라 Git 공통 저장소 정보로 **원본 리포의 Python**을 찾고, **명령을 실행한 워크트리의 Dashboard 소스**를 실행한다. 워크트리별 환경을 쓰는 일반 개발 원칙의 Dashboard 실행 예외다. 원본 환경을 생성·수정하거나 복사하지 않는다.
- 이 프로그램은 RHP와 독립적이다. Dashboard만 변경했을 때 RHP 빌드·등록·Rhino 재시작은 필요하지 않다.
- 회귀 검사는 `src/mcp/tests/runtime/test_dashboard*.py`에 둔다. 테스트 데이터 생성은 테스트의 일회용 DB에서만 수행한다.
- 읽기 경로 변경 시 DB 바이트·스키마 보존, DML/DDL 거절, WAL 읽기, 잠금 보존과 HTTP 접근을 확인한다. 검사 명령은 README를 따른다.
