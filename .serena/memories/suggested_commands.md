# 명령 진입점

- 저장소 루트의 PowerShell에서 개발 환경 준비: `./src/mcp/rebuild_environment.ps1 -Development`.
- MCP 모듈: `./src/mcp/run_tests.ps1 -Development`. 외부 연결기·Engine dispatch/GH/해석 수명/Terminal/pipe fixture: `./src/cos/run_tests.ps1 -Development`. 모듈 경계·실제 Python stdio·공개 스키마·ArchiveHost·배포 파일 대조: `./tests/run_tests.ps1 -Development`.
- 세 실행기가 오프라인 경로를 준비하며 임시 파일은 체크아웃 data/t에 둔다. 실제 .NET 8 SDK 자동 탐색이 실패하면 `-DotNet`에 SDK의 `dotnet.exe` 경로를 준다. 수동 오프라인 경로가 필요한 별도 셸에서만 `./src/mcp/use_offline_environment.ps1 -Development`.
- 오프라인 검사와 RHP 빌드는 SDK 호출 전에 현재 프로세스에 `DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=false`와 `DOTNET_GENERATE_ASPNET_CERTIFICATE=false`를 설정한다. 별도 SDK 명령을 직접 실행할 때도 같은 설정을 적용한다.
- 자산 해시·출처: `& ./data/development/.venv/Scripts/python.exe -B tests/verify_library_sources.py`. 패널 Node·기타 native fixture 명령은 `src/rhp/tests/README.md`.
- 제품 빌드는 `AGENTS.md`의 대상 출력 확인과 전달 절차에 따라 Bridge에 `./src/rhp/build.ps1`, AlmondRhino에 `./src/cos/build.ps1`. `src/rhp/tools/verify_runtime.py`의 기본 호출은 기록 대조, `--record`는 빌드 기록 갱신이다.
