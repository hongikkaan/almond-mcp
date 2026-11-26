# 07 · PlanSection의 대기와 취소 결과

기준 커밋 dbdb6f3에서 사용자 rhino 등록 대기는 30초, 저장소 Codex 생성 기본은 600초였다. Rhino SDK는 취소 토큰을 받는 HLD 오버로드를 제공하지만 원본 호출은 토큰을 전달하지 않았다. Codex용 생성 기본 240초와 전용 작업의 120초 취소 요청을 구현했다.

**선행 티켓** 없음

## 구현 경계

사용자 전역 설정과 당시 별도 앱의 대기는 유지한다. 배치 한 번의 Undo와 보상 경계를 보존한다. 취소 가능 SDK 호출과 안전 경계에 신호를 전달한다.

## 수용 기준과 오프라인 검증

종료가 확인된 중단, 응답 소실·정리 실패, 완료 컷, 미시작 컷, 영향 미확인 컷을 가짜 시계/취소 신호·transport로 구분한다. 성공/타임아웃 안내를 분리한다. 비선점 구간에서 클라이언트의 240초가 먼저 끝날 수 있다.

## 구현 결과

- Codex의 `[mcp_servers.rhino].tool_timeout_sec` 생성값은 240초다. 기존 생성기와 정확히 일치하는 600초 설정은 명시적인 설치 실행 시 백업 후 이전된다. fixture에서 사용자 지정 30초와 다른 설정 보존을 확인했다. 사용자 실제 등록 읽기 전용 조회 `codex mcp get rhino --json`의 enabled는 true, startup은 120초, tool은 30초였다. 당시 별도 앱의 600초는 유지했다.
- 전용 worker는 Bridge capability `plan_section=3`을 확인한 뒤 요청을 한 번만 보낸다. Rhino의 전용 처리에 진입한 뒤 120초에 CTS가 신호를 보내고, 기존 단일 스레드 HLD의 토큰 오버로드와 계산 단계·문서 쓰기 전·컷 사이에서 처리한다. Move 준비 중 신호가 오면 복제 형상을 해제하고 Replace·보상 작업 없이 종료한다. 실행 중인 쓰기와 Undo·복구를 기다린다.
- 정상 완료는 도면 GUID·배치 평면 확인을, 실제 중단·정리가 확인된 `timeout`은 완료·취소·미시작 결과와 미완료 범위 확인을 안내한다. 쓰기 후 오류는 관찰된 GUID와 미확인 컷을 보존한다. 바깥 Undo 종료가 실패하면 이미 반환된 컷 결과는 `unconfirmed`, 이후 컷은 `not_started`로 남기며 완료 수는 단정하지 않는다. 컨텍스트 복원 실패와 transport 소실도 중단 확정으로 표시하지 않는다.
- 비선점 Move가 가짜 241초에 끝나고 Undo 정리가 251초에 끝나는 fixture에서 첫 컷 완료·두 번째 미시작을 검증했다. 클라이언트가 먼저 대기를 끝내면 이 응답을 받을 수 없다. 당시 별도 앱에서 기본 300초 외부 broker 대기가 먼저 끝나는 사례는 worker 전송 이후에만 컷과 미확인 오류·재실행 금지 안내를 반환한다. 시작 전 오류, 예약·잠금·호스트 대기는 기존 계약을 사용한다.

검사는 dev에서 `. ./src/mcp/use_offline_environment.ps1 -Development -RequireDotNet` 실행 후 아래처럼 별도의 pytest 프로세스로 수행했다. 첫 통합 수집 시 저장소의 mcp와 SDK 동명 패키지가 충돌하여 모듈별 경로로 다시 검사했다. 개발 전용 .NET SDK는 8.0.426이다.

```powershell
& $env:ALMOND_TEST_PYTHON -B -X utf8 -m pytest -q src/mcp/tests/test_plan_section.py --tb=short
& $env:ALMOND_TEST_PYTHON -B -X utf8 -m pytest -q src/mcp/features/modeling/PlanSection/tests --tb=short
```

위 두 검사에서 각각 71개, 98개 및 subtest 95개가 통과했다. 당시 외부 연결기의 `test_client_deadline.py`, `test_execution_timeout.py`, `test_invocation_cancellation.py`에서도 24개가 통과했다. 실제 Rhino HLD의 중단 지연, 실제 문서의 컷 보존·Undo, 등록·로드는 별도 승인 후 검수 대상이다.
