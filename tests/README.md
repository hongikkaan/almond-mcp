# 개발 검사와 검증 범위

## 변경에 맞는 검사 선택

개발 검사는 Rhino를 사용하지 않는 오프라인 검사로 수행한다. 실행 중인 Rhino와 연결된 사용자 문서, RhinoCore를 사용하는 fixture는 개발 검사 범위 밖이다. 명령은 체크아웃 루트의 PowerShell에서 실행한다. 여러 변경 유형이 겹치면 각 유형이 영향을 주는 검사 범위를 함께 본다.

| 변경 유형 | 검사와 판단 기준 |
| --- | --- |
| 저장소 안내 문서만 변경 | 변경된 링크·앵커를 확인하고 명령·전제·설명은 해당 스크립트와 구현에 대조한다. 문서가 실제 제품 입력으로 쓰이는 경우에는 소비 경로에 맞는 검사도 선택한다. |
| MCP Python 구현 변경 | `./src/mcp/run_tests.ps1 -Development`로 모듈 회귀를 검사한다. 모듈 경계·공개 계약·패키징에 영향이 있으면 루트 검사도 사용한다. |
| Python 공개 도구 계약 변경 | MCP 모듈 검사와 `./tests/run_tests.ps1 -Development`를 사용한다. 구현 옆 지침·[출력 계약](../src/mcp/output_contracts.py)·[공개 스키마 기준](integration/tool_schemas.json)을 비교한다. 스키마 변경이 의도된 경우 기준의 차이를 검토한다. 루트 검사는 실제 stdio와 beyond·CoS 카탈로그의 계약을 확인한다. |
| 외부 연결기·native 계약 변경 | `./src/cos/run_tests.ps1 -Development`로 외부 연결기의 Python 계약과 Engine·Terminal·pipe fixture를 검사한다. Archive·패널 등 변경된 소비 경로는 [native 검사 안내](../src/rhp/tests/README.md)에서 고른다. |
| 공유 Engine 변경 | 외부 연결기 실행기의 Engine fixture를 실행하고 영향을 받는 소비 경로를 검사한다. [RHP 빌드 절차](../AGENTS.md#개발빌드반영)에 따라 Bridge와 AlmondRhino를 모두 빌드한 뒤 두 manifest와 Engine DLL 일치를 확인한다. 루트 전체 검사(`./tests/run_tests.ps1 -Development`)에는 배포 파일 대조가 포함되므로 빌드와 manifest 기록을 마친 상태에서 실행한다. |
| 배포용 자산 원본·출처 변경 | `& ./data/development/.venv/Scripts/python.exe -B tests/verify_library_sources.py`로 저장소에 포함된 생성 모델의 경로·바이트 해시·출처 기록을 확인한다. 설치된 AppData 라이브러리나 Rhino에서의 자산 사용은 별도 확인 범위다. |

## 오프라인 검사 준비

체크아웃별 개발 환경을 처음 준비하거나 잠금 의존성을 동기화할 때 실행한다.

```powershell
./src/mcp/rebuild_environment.ps1 -Development
```

세 `run_tests.ps1`은 `-Development`로 실행하면 이 체크아웃의 `data/development/.venv`를 사용한다. 실행기가 오프라인 경로를 직접 설정한다. 세 실행기 모두 .NET 8 SDK를 확인하며, 자동 탐색에 실패하면 `-DotNet`에 SDK의 `dotnet.exe` 경로를 전달한다.

로컬 도구를 별도 셸에서 직접 실행하면서 같은 데이터 경로가 필요한 경우에만 `./src/mcp/use_offline_environment.ps1 -Development`를 호출한다. 라이브러리는 체크아웃의 `asset/`을 사용하고, 해당 원본 폴더가 없으면 `data/offline/libraries/` 밑에 대체 경로를 만든다. 상태 DB는 `data/offline/state.sqlite3`, TEMP/TMP는 사용자 임시 폴더의 체크아웃별 짧은 경로를 사용한다. 설정은 현재 셸과 자식 프로세스에 적용되므로 일반 실행은 새 셸에서 시작한다. 검사의 오프라인 범위는 Rhino와 일상 연결·데이터를 사용하지 않는다는 뜻이다. 예를 들어 패키징 검사는 `uv build --offline`이 사용하는 로컬 uv 캐시에 빌드 의존성이 준비되어 있어야 한다.

## 실행기별 확인 범위

- [MCP 모듈 실행기](../src/mcp/run_tests.ps1)는 자체 `pytest.ini`로 `src/mcp/tests`를 실행한다.
- [외부 연결기 실행기](../src/cos/run_tests.ps1)는 Engine·Terminal·pipe fixture를 빌드하고 실행한 뒤 `src/cos/tests`를 실행한다.
- [루트 실행기](run_tests.ps1)는 독립 ArchiveHost를 빌드하고 절대 실행 파일 경로를 `ALMOND_ARCHIVE_TEST_HOST`로 지정한 뒤 루트 `tests/`를 실행한다. ArchiveHost가 필요한 검사를 pytest에서 직접 선택하면 해당 실행 파일이 필수이며, 누락 시 수집 단계에서 오류가 난다.
- [stdio 계약 검사](integration/test_stdio_contract.py)는 실제 Python MCP 서비스를 자식 프로세스로 시작한다. 문서 연결 fixture는 임시 경로와 합성 binding 메타데이터를 사용한다. 초기화 안내, 공개 도구 설명·가이드, worker 스키마와 두 외부 카탈로그의 일치를 확인한다. 실제 모델링 동작은 이 검사의 범위 밖이다.
- [설치된 CLI 실행기 검사](../src/mcp/tests/runtime/test_terminal_launch.ps1)는 `./src/mcp/tests/runtime/test_terminal_launch.ps1 -Codex <installed-codex.exe>`에서 실제 CLI의 설정 해석을 사용한다. OS의 binding 관측은 대역을 사용하고 대화형 실행은 가로챈다. 실제 RhinoTerminal 세션의 도구 목록은 연결 후 별도로 확인한다.

오프라인 검사에서 다루는 모델링·계산 동작의 범위는 실제로 실행한 사례에 한정된다.

Windows에서 symlink를 만드는 자산 경계 검사는 파일 시스템과 실행 환경의 symlink 생성 지원이 필요하다. `WinError 1314`가 symlink 생성에서 발생하면 해당 검사는 환경에서 중단된 것으로 기록하고, 전체 실행 결과에도 실패로 남긴다.

## 결과 보고 기준

| 확인한 단계 | 확보한 증거 |
| --- | --- |
| 오프라인 검사 | 실행한 모듈·계약·fixture에서 어떤 검사가 통과하거나 실패했는지. 현재 [native 검사 범위](../src/rhp/tests/README.md)와 [Undo·관측 검사 상태](../src/rhp/RhinoAlmondBridge/tests/script_executor_undo/README.md)도 확인한다. |
| RHP 빌드와 출력 검증 | 빌드한 구성요소, 생성·배치된 파일, `verify_runtime.py`로 확인한 소스·배포 파일의 manifest 정합성. 전체 검증은 양쪽 Engine DLL의 바이트 일치도 확인한다. `--record`는 manifest를 갱신하고 기본 호출은 기록을 대조한다. |
| Rhino 등록 | 일상 체크아웃에서 `./src/rhp/tools/install_runtime.ps1 -VerifyOnly`로 확인한 등록 파일 경로와 연결 명령 캐시. |
| 실제 플러그인 로드 | 별도 요청 시 Rhino 프로세스에서 확인한 플러그인과 실제 assembly 경로. |
| Rhino에서만 확인 가능한 동작 | 개발 검사 범위 밖으로 기록한다. 예를 들어 실제 모델링 결과, 뷰·Layout 표시, Rhino UI 동작이 해당한다. |

실행한 단계와 확인 범위를 근거와 함께 보고한다. 실패나 실행할 수 없었던 검사, 현재 자동 검사가 다루지 않는 동작도 명시한다.
