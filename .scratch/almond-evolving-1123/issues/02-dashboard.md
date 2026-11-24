# 06b · Dashboard의 Plan 관계 표기

상세와 비교 선택기에 이전/후속, 선행 의존/후속 의존이 섞여 있다. 직전·다음·관련·부모·자식 Plan으로 표기한다.

**선행 티켓** 없음

## 구현 경계

읽기 전용 Dashboard에서 표시한다. 저장·실행 규칙을 보존한다.

## 수용 기준과 오프라인 검증

임시 DB에 동일 Plan이 직전이면서 관련인 경우, 상호 의존, 한쪽에서만 기록한 상하위, 사라진 참조를 넣어 두 화면의 의미·중복·누락을 살핀다.

## 결과

상세 카드와 비교 선택기에서 같은 다섯 가지 관계명을 사용한다. 양방향 의존은 같은 Plan을 한 번만 표시하고, 순서와 관련이 겹치면 두 관계를 보존한다. 한쪽 Plan에만 기록된 상하위 관계도 반대편 카드에 보인다. 기존 브라우저에 저장한 비교 선택은 다시 열 때 새 관계명에 연결된다.

오프라인 Dashboard pytest 66개와 `node --check src/mcp/runtime/dashboard/web/domain.js`가 통과했다. `PLAYWRIGHT_MODULE`에 설치된 Playwright 경로를 지정해 `node src/mcp/tests/runtime/dashboard_browser.cjs`를 실행했다. 임시 DB와 헤드리스 Chromium에서 두 화면의 실제 라벨과 중복 제거를 확인했다.
