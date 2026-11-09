# 원본 리포의 Python 자동 선택

Git이 알려주는 **원본 체크아웃의 Python**을 자동 선택합니다.
작업 워크트리는 원본과 다른 폴더나 드라이브에 있어도 됩니다.
워크트리의 소스 위치와 Python 환경의 위치를 구분합니다.

## 복원·업데이트

이 폴더의 파일이 Git으로 보존되는 원본입니다. PowerShell에서 실행합니다.

```powershell
./install.ps1
```

설치 위치는 `C:\Users\hopho\.config\auto-venv`입니다.
`auto-venv.cmd`, `auto-venv.ps1`, `repository.ps1`을 설치합니다.
내용이 달라진 기존 파일은 설치 폴더의 `backups`에 보관합니다.
기존 CMD AutoRun·PowerShell 프로필 등록은 유지합니다.
해당 등록이 없는 컴퓨터에서는 수동으로 불러 쓸 수 있습니다.

```powershell
. "$env:USERPROFILE\.config\auto-venv\auto-venv.ps1"
```

```bat
call "%USERPROFILE%\.config\auto-venv\auto-venv.cmd"
```

## 원본 리포를 찾는 방법

1. Git의 `rev-parse --show-toplevel`로 현재 작업 워크트리를 확인합니다.
2. `rev-parse --path-format=absolute --git-common-dir`로 공통 Git 메타데이터 경로를 구합니다.
3. **공통 디렉터리를 Git 디렉터리로 지정**해 원본 체크아웃의 `core.worktree`를 읽습니다.
   `extensions.worktreeConfig`를 사용하는 경우 원본의 `config.worktree`도 반영됩니다.
4. 별도 설정이 없는 일반 `.git` 디렉터리는 그 디렉터리의 부모가 원본 체크아웃입니다.
5. 찾은 원본 경로가 같은 Git 공통 디렉터리에 연결된 실제 체크아웃인지 검증합니다.

상위 폴더를 하나씩 훑어 가상환경을 찾지 않습니다.
원본 경로를 Git 메타데이터만으로 확인할 수 없는 경우 다른 환경을 추측하지 않습니다.
특히 별도 Git 디렉터리를 쓰면서 원본 `core.worktree` 연결도 없는 저장소는 자동 선택하지 않습니다.
Git이 없거나 저장소 밖인 경우에도 자동 선택하지 않습니다.

## 제공하는 변수와 Python 선택 순서

| 변수 | 의미 |
| --- | --- |
| `AUTO_VENV_WORKTREE_ROOT` | 현재 작업 워크트리의 Git 루트 |
| `AUTO_VENV_REPO_ROOT` | 원본 체크아웃의 Git 루트 |
| `AUTO_VENV_PYTHON` | 원본 체크아웃에서 선택한 Python의 절대경로 |

원본 체크아웃 아래에서 다음 순서로 선택합니다.
`pyvenv.cfg`와 `Scripts/python.exe`가 모두 있어야 합니다.

1. `.venv`
2. `venv`
3. `data/development/.venv`
4. `src/engine/.venv`

환경 생성·복사·패키지 설치는 하지 않습니다. 프로젝트의 활성화 스크립트를 실행하지 않고
`PATH`·`VIRTUAL_ENV`를 설정합니다. 직접 활성화한 다른 환경은 유지합니다.
자동 선택한 저장소에서 벗어나면 선택 전 환경을 복원합니다.

PowerShell은 시작 시 및 폴더 이동 후 다음 프롬프트에서 다시 선택합니다.
기존 프롬프트를 유지합니다. CMD는 새 창 시작 시 선택하며,
폴더 이동 후에는 위 `call` 명령으로 갱신합니다.
CMD의 Git 경로 처리 중 UTF-8 코드 페이지를 사용하고 즉시 원래 코드 페이지로 복원합니다.
`AUTO_VENV_DISABLE`을 설정하면 자동 선택을 잠시 끌 수 있습니다.

## 변수로 실행할 Python 확인

새 PowerShell 창에서 작업 워크트리로 이동한 다음 실행합니다.

```powershell
Update-AutoVenv
$repo = $env:AUTO_VENV_REPO_ROOT
$python = $env:AUTO_VENV_PYTHON
$repo
$python
if ($python) { & $python --version }
```

CMD에서는 다음과 같습니다.

```bat
call "%USERPROFILE%\.config\auto-venv\auto-venv.cmd"
echo %AUTO_VENV_REPO_ROOT%
if defined AUTO_VENV_PYTHON "%AUTO_VENV_PYTHON%" --version
```

## Dashboard 실행

Dashboard 실행은 [해당 폴더의 사용법](../dashboard/README.md)을 따른다.

경로 해석은 [Git rev-parse](https://git-scm.com/docs/git-rev-parse)와
[Git core.worktree 설정](https://git-scm.com/docs/git-config#Documentation/git-config.txt-coreworktree)을 따릅니다.
