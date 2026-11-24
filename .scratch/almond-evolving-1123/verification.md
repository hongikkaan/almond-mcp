# 11월 23일 개발 워크트리 검증

일상 폴더의 `skill` 기준 커밋은 `dbdb6f37cd25903883ca33227cf8b6c0f6dd9b01`이다. 당시 `dev`의 `ff9572b17e3b7b4fdd1ff947f6b1bfd49ac3766e`에서 좌우 고유 커밋 수는 0/5였고 양쪽 커밋 모두 `코드 개선 명세.md`를 추적하지 않았다. dev의 인덱스와 추적 파일에 변경이 없는 것을 확인하고 fast-forward했다. 미추적 파일의 전후 SHA-256은 `0efb55f279da0481e951786700c32baa9fcd64860eb02bb47165271e04d7610f`다.

## 합의한 동작과 검수 범위

| 건 | 개발 결과 | 근거 |
|---|---|---|
| 04b | 기존 검수 Plan의 네 Step에서 판정 기준·검수·결함 처리·재검수를 설명한다. 기존 mini-workflow와 같은 가림 결함을 비교하는 사례를 마련했다. | [템플릿과 fixture](issues/01-inspection.md) |
| 06b | Dashboard의 상세와 비교 화면이 직전·다음·관련·부모·자식을 동일하게 표시한다. | [임시 DB와 브라우저 검사](issues/02-dashboard.md) |
| 06c | 요청의 저장 결과를 updated/no_change/partial_success로 구분한다. 건너뛴 항목과 완료 후 안내를 검사했다. | [공개 호출과 인계](issues/03-update.md) |
| 07 | 생성할 Codex 클라이언트 설정은 240초, 현재 등록값은 30초다. native는 120초에 취소를 요청하고 정리가 끝나야 중단을 확정한다. | [컷 상태·복구·대기와 전역 조회](issues/04-section.md) |
| 08 | 83회 중 PNG 저장 성공 80회. 남은 원본 19개와 반환 이미지 45개의 해시를 확인했다. 동일 호출의 UI 실패 화면 확보 후 결함 위치를 판정한다. | [세션·PNG 대조](issues/05-preview.md) |
| 13 | 현재 문서의 표시 모드와 capture_02·03·04에서 Rhino 표시 메뉴 등재 모드를 이름·GUID로 선택한다. capture_01 적용 범위는 협의 대상이다. | [SDK·등록 능력·메뉴 조합](issues/06-display.md) |
| 14 | #43의 뷰포트 범위, 조건, 출력 선택 예시와 기존 평면 호출·페이지 이동을 확인했다. 그룹·메타데이터의 새 다중 조건과 상속 재질의 의미는 미결이다. | [재현과 결과 집합](issues/07-objects.md) |
| 15 | 기존 선택형 labels를 유지했다. 객체의 가시 픽셀을 식별할 수 있는지 확인할 가림·클리핑·블록 배치 사례가 남아 있다. | [시험 장면·SDK 한계](issues/08-labels.md) |

## 실행 명령과 결과

모든 명령의 작업 폴더는 개발 워크트리다. 설치된 Rhino 8 SDK, .NET SDK 8.0.426과 dev 전용 Python을 사용했다.

```powershell
./tests/verify_integration_worktree.ps1 -TicketWorktree (Get-Location).Path -ExpectedBase dbdb6f37cd25903883ca33227cf8b6c0f6dd9b01
./src/rhp/build.ps1 -PythonExecutable (Resolve-Path ./data/development/.venv/Scripts/python.exe).Path
./src/cos/build.ps1
& ./data/development/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py --record
& ./data/development/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py
./src/mcp/run_tests.ps1 -Development -TestArgs @('-q','--tb=short')
./src/cos/run_tests.ps1 -Development -TestArgs @('-q','--tb=short')
./tests/run_tests.ps1 -Development -TestArgs @('-q','--tb=short')
& ./data/development/.venv/Scripts/python.exe -B -X utf8 .scratch/almond-evolving-1123/verify_catalog.py
```

- 워크트리 기준 검사와 양쪽 빌드가 통과했다. 첫 Bridge 빌드의 Engine이 기존 AlmondRhino 출력과 달라 같은 dev에서 AlmondRhino도 빌드했다. Bridge 472개 소스·461개 런타임 파일, CoS 21개 소스·6개 런타임 파일의 기록과 검증이 통과했다.
- MCP 전체는 979개와 하위 사례 3개 통과, 6개 실패다. 여섯 건 모두 `test_stage2_asset_paths.py`의 파일·폴더 심볼릭 링크 fixture를 만들 때 Windows가 `WinError 1314`를 반환했다.
- CoS 전체는 Python 116개와 .NET fixture 6묶음이 통과했다. 저장소 통합 검사는 53개 통과, 4개 실패다. 네 건은 `test_stdio_contract.py:58`의 한국어 종결형 검사에서 멈췄다. 기준 커밋 선언 문서의 1225·4138행 ‘아니다.’에서도 같은 패턴이 일치한다.
- 문서의 설명 문구와 실제 카탈로그 설명 사이에는 기존 차이가 남아 있다. 별도의 실제 stdio 검사에서 worker 76개의 설명·스키마와 소스 카탈로그를 대조하고 beyond·CoS 각 81개에 대해 initialize, tools/list, 경로별 스키마·선언 해시, 문서에 적힌 공개 이름을 확인했다.
- Dashboard는 임시 DB와 헤드리스 Chromium에서 상세·비교 화면, Plan 개요와 반복 이력을 확인했다. 별도 검수 모델을 사용하는 실제 Rhino 동작은 후속 승인 대상이다.

| dev 출력 | SHA-256 |
|---|---|
| RhinoAlmondBridge/plugin-runtime/RhinoAlmondBridge.rhp | `38fd41784d36721694010de0152484ef201815ce9e49d7dd8d0fda59989615b0` |
| AlmondRhino/plugin-runtime/AlmondRhino.rhp | `b1954a8c0a1c5127b47ecc8e3e6ad9824066073ae4e355c8dc93fddbac5bf406` |
| 두 출력의 Almond.Engine.dll | `48b59e6245519fefc0a2e084f7973295cdc75451171ab58765946d6037764bf0` |

manifest는 `src/rhp/RhinoAlmondBridge/runtime-manifest.json`과 `src/cos/runtime-manifest.json`이다. 빌드 산출물은 이 dev의 `src/rhp` 아래에 있다. 생성된 실행 파일을 활용할 실제 모델 검수와 일상 폴더 병합은 별도 결정 단계다.


## 11/24 루트 dev 실검수

#14 객체 필터의 실제 결과와 예측값은 [객체 필터 티켓](issues/07-objects.md)에 기록했다. 표준 Beyond에서 수동으로 열린 시험 문서에 연결했다. 자동 파일 열기의 부모 Job 제한은 별도로 남아 있다. 이번 실제 검수는 #14를 대상으로 했으며, #08은 익환이 이번 회차에서 제외했고 #15는 보류했다.

루트의 관련 자동 테스트 115개, worker 76개·CoS/Beyond 각 81개 공개 도구 선언 검사가 통과했다. 두 manifest 검증 결과는 Bridge 소스 473개·런타임 461개, CoS 소스 21개·런타임 6개다. 루트 검수본의 SHA-256은 Bridge RHP 45e6df04d158b69ae15a6c701b44a17dfeb0aa824156c008f5722a40731a62b0, AlmondRhino RHP 04cfc16bfcbcff4a6fb9930a3f6ba9f4a72125c61b934e4bd1f01cfbedcc3106, 공용 Engine DLL 71c43d32848650c7e046190e63d7bb524161213378f1948e9526f25e0e712726이다.
