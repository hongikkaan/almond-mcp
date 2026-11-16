# 저장소 계약과 관례

- 공개 MCP 이름은 `<category>_<NN>-<name>`. 공개 설명·입력 설명·후속 안내의 도구 인용은 `<공개 도구명> tool`. Python 함수, Rhino 명령과 DB 식별자는 별도 이름이다.
- 소비자가 지켜야 할 계약을 모듈 SPEC에서 확인한다. 제품에 노출되는 `*-explain.md`와 정책 Markdown은 실행 중 읽히는 입력이다. 작업 지침 `AGENTS.md`와 전달 경로가 다르다.
- 모델 경로와 Rhino GUID가 객체 identity를 구성한다. 모델 폴더 DB, 세션 token, A–J slot, lease, native 완료 확인을 보존한다. timeout·result_error는 rollback 증거가 아니므로 완료가 불확실한 수정을 자동 재시도하지 않는다.
- 모듈 전용 검사는 각 모듈의 tests, 모듈 간 계약은 루트 `tests/`. Windows PowerShell·UTF-8을 사용한다.