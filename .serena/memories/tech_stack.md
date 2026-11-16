# 개발 환경과 기술 스택

- 패키지 이름/공개 import는 `almond_mcp`, 소스는 `src/mcp`. FastMCP·Pydantic과 SQLite 상태 저장소. `pyproject.toml`의 Hatchling 설정이 소스와 배포 경계를 정의한다.
- Windows PowerShell에서 `uv.lock`으로 의존성을 고정하고 개발 환경 스크립트는 Python 3.12.12를 검증한다. 체크아웃별 `data/development/.venv`는 개발 검사, `src/engine/.venv`는 같은 체크아웃의 일상 런타임용이다. editable 설치는 다른 체크아웃과 공유하지 않는다.
- .NET 8 SDK 선택은 `global.json`을 따른다. RHP는 Windows Rhino 8 SDK를 참조한다. 오프라인 C# fixture와 제품 RHP는 별도 빌드 대상이다. Asset Panel은 Node의 `node --test`로 검사한다.