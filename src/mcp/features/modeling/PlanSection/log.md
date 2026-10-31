# Plan/Section 작업 기록

## 해야 했던 일

- 사용자가 연 `군대 초소.3dm`에서 PlanSection을 사용하고, 필요한 기능·지침만 실사용 체크아웃에서 수정한다.

## 작업 방법

- Project/CurrentDocument 선택과 Project의 단일 번호·All·List 입력을 반영하고 쉼표 구분 숫자 입력을 제거했다.

- 공식 RhinoCode로 AlmondConnect를 실행한 뒤 공개 MCP 실행기로 기존 지하 평면·장단면 clipping을 사용했다. Create·Move·Update와 벡터 PDF를 확인하고 원본 3dm은 저장하지 않았다.
- 같은 원본·형상 CRC·속성·입력 순서로 반복 생성했다. 병렬 HLD 경로는 후처리 전 입면 수와 길이가 달랐고, 단일 스레드 진단 사본은 두 회차의 원시·최종 형상 서명이 같았다. 이 실행 옵션만 생산 코드에 반영했다.
- 별도 검수 캡처에서 같은 Rhino 뷰의 새 managed wrapper를 다른 뷰로 오판하는 문제를 재현했다. 뷰 비교를 RuntimeSerialNumber로 바꾸고 나머지 상태 검사는 유지했다.
- BASIC의 PlanSection 안내에 해치 생성 조건, 입면 인쇄 속성, Move·Update 차이와 PDF 기준을 보완했다. 특정 모델의 층·시점·작업 순서는 추가하지 않았다.

## 결과

- Move는 출력 GUID와 수동 색상을 유지했다. Update는 기존 출력과 수동 편집을 교체하고 저장된 배치점을 유지했다.
- 단일 스레드로 지하 평면 324개, 장단면 610개 곡선을 생성했다. 모두 유효하고 Z=0이며 장단면 반복 생성 개수도 일치했다. 입력 SectionStyle이 모두 비어 있어 해치 0개는 계약에 맞으며, 실제 해치 생성은 이번 문서에서 검증하지 않았다.
- 평면·단면 PDF는 각각 A3 420×297mm 한 페이지, raster image 0개인 벡터 출력이었다. 렌더링해 전체 도면과 선 표현을 확인했다. 장단면의 방향은 기존 clipping의 X축=WorldZ, Y축=WorldX를 따른다.
- 테스트 도면 934개와 Layout을 제거했다. 원본 6,293개 객체의 GUID·형상은 보존됐고 추가 객체와 레이어는 없다. 두 clipping의 속성·사용자 데이터 내용은 원본과 일치한다. 직렬화 해시 차이는 내부 UserData 복제 카운터와 해당 CRC에만 있다. 원본 모델 파일은 저장하지 않았으며 Rhino의 modified 표시는 유지했다.
- 오프라인 PlanSection 49개, 관련 MCP 27개 통과. 외부 연결기 108개 검사에서 실패·오류 0, 기존 skip 1; native 대역 19개와 lifecycle 대역 7개 통과. Rhino 종료 확인 후 Bridge·AlmondRhino를 경고·오류 없이 빌드·배치했고 manifest·공용 Engine 일치·일상 등록을 검증했다. 사용자가 원본 모델을 다시 연 뒤 일상 경로의 새 RHP 실제 로드·해시를 확인했다. 수정된 생산 코드의 두 평면 계산은 모두 324개와 같은 형상 서명을 냈다. 전체 문서와 전층 기둥 141개를 각각 두 시점으로 캡처해 이미지 반환과 범위 제외를 확인했고, 객체·속성·가시성·선택·카메라·modified 상태는 전후 동일했다.
- 재현 자료는 프로젝트 `tmp/261031_PlanSection_live`의 `hld-repeat.json`, `hld-serial.json`, `section-pdf-checks.json`, `cleanup-checks.json`, `attribute-diff.json`과 두 PDF에 있다. 재시작 이후 검증은 `postbuild-verification.json`, `capture-state-checks.json`, `capture-document.png`, `capture-columns.png`에 보관했다. 재시작 전후 CRC 차이는 clipping 23개에만 있으며 원점·법선은 같고, 나머지 원본 형상의 CRC는 동일하다. 원시 HLD 통계는 RejoinCompatibleVisible 이후 측정으로, Compute와 Rejoin 중 최초 차이 지점을 분리한 결과는 아니다.
