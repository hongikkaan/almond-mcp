# 저장소 계약과 관례

- 공개 MCP 이름은 `<category>_<NN>-<name>`. 공개 설명·입력 설명·후속 안내의 도구 인용은 `<공개 도구명> tool`. Python 함수, Rhino 명령과 DB 식별자는 별도 이름이다.
- 소비자가 지켜야 할 계약은 모듈 SPEC을 따른다. 도구 설명·입출력의 원본은 `TOOL-DECLARATIONS-CURRENT.md`다. 두 실행 경로는 패키지의 `public_contract_data.json`에서 같은 선언을 읽는다. 시작 지침과 활동별 정책 Markdown은 제품이 읽는 입력이며, 작업 지침 `AGENTS.md`와 전달 경로가 다르다.
- 모델 경로와 Rhino GUID가 객체 identity를 구성한다. 모델 폴더 DB, 세션 token, A–J slot, lease, native 완료 확인을 보존한다. timeout·result_error는 rollback 증거가 아니므로 완료가 불확실한 수정을 자동 재시도하지 않는다.
- 모듈 전용 검사는 각 모듈의 tests, 모듈 간 계약은 루트 `tests/`. Windows PowerShell·UTF-8을 사용한다.
- 일상 폴더에서 `main`을 쓰는 경우 개발 워크트리는 작업 브랜치 또는 detached HEAD를 사용한다. `main` 체크아웃이 다른 워크트리 때문에 막히면 `git worktree list --porcelain`으로 소유 경로를 확인하고, 변경을 보존한 채 그 워크트리를 현재 커밋에서 detach한 다음 일상 폴더에서 체크아웃한다. 티켓 위임 전 HEAD와 일상 squash의 부모·파일 트리·체크아웃 검증은 `tests/verify_integration_worktree.ps1`을 사용한다.