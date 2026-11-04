# Dashboard 실행과 자료 안내

대시보드 작업 워크트리는 `C:\TOOL\Rhino\mcp\almond-mcp\data\worktrees\DashBoard`입니다.
이 폴더는 예시 DB 등 대시보드 관련 자료를 보관합니다.

## 바로 실행

PowerShell에서 아래 한 줄을 그대로 실행합니다. 현재 폴더를 바꿀 필요가 없습니다.

```powershell
& 'C:\TOOL\Rhino\mcp\almond-mcp\data\worktrees\DashBoard\src\mcp\runtime\Almond DB Dashboard.cmd'
```

파일 선택 창에서 SQLite DB를 선택하면 브라우저에 대시보드가 열립니다.
확장자 없는 `DB` 파일은 파일 형식을 **All files**로 바꿔 선택합니다.
다른 DB는 화면 오른쪽 위 **파일 열기**로 선택합니다.

실행기가 설치된 PowerShell 7(`pwsh.exe`)을 우선 사용하고, 없으면 Windows 기본 PowerShell로 실행합니다.
PowerShell 경로나 환경 변수를 별도 명령으로 입력할 필요 없이 위 `.cmd` 명령을 사용합니다.

`demo.sqlite3`는 화면 확인용 예시 자료입니다. 파일 선택 창에서 이 파일을 골라 볼 수도 있습니다.
종료는 실행한 창에서 **Ctrl+C**입니다. 브라우저 탭만 닫으면 서버는 계속 실행됩니다.

## 프로그램과 자료 위치

| 항목 | 위치 |
| --- | --- |
| 실행기 | `src\mcp\runtime\Almond DB Dashboard.cmd` |
| PowerShell 실행 스크립트 | `src\mcp\runtime\dashboard.ps1` |
| 프로그램 소스와 전체 사용법 | `src\mcp\runtime\dashboard\README.md` |
| 이 README와 예시 DB | `data\dashboard` |
| 현재 사용하는 Python | `C:\TOOL\Rhino\mcp\almond-mcp\.venv\Scripts\python.exe` |
| 자동 환경 선택 원본·복원 방법 | `src\mcp\runtime\auto-venv\README.md` |

표의 상대 경로는 작업 워크트리 기준입니다. 실행기는 위 워크트리의 프로그램을
Git으로 확인한 원본 리포의 Python으로 실행합니다. SQLite 원본은 읽기 전용으로 열며,
Rhino 연결이나 플러그인 등록은 필요하지 않습니다.
이 README는 Git으로 추적합니다. 예시 DB·진단 자료와 컴퓨터별 Python 환경은 로컬 생성 자료로 제외합니다.
실행에 필요한 `.cmd`·`.ps1`·Python 프로그램 소스는 `src/mcp/runtime`에서 Git으로 추적합니다.
전체 사용법과 실행 명령은 프로그램 폴더의 README에도 보존합니다.

자동 환경 선택과 Dashboard 실행기는 Git 공통 메타데이터에서 원본 리포 경로를 구합니다.
`AUTO_VENV_REPO_ROOT`는 `C:\TOOL\Rhino\mcp\almond-mcp`,
`AUTO_VENV_WORKTREE_ROOT`는 이 Dashboard 워크트리,
`AUTO_VENV_PYTHON`은 위 표의 원본 Python 경로입니다.
워크트리가 원본과 다른 위치에 있어도 원본 Python을 참조하고 프로그램은 워크트리에서 읽습니다.

자동 환경 선택 설치본은 `C:\Users\hopho\.config\auto-venv`에 있습니다.
원본 스크립트와 사용법은 `src/mcp/runtime/auto-venv`에서 Git으로 보존합니다.
