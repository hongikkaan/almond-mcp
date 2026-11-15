# MarketHall Session 요약

Market Hall 작업은 **하나의 `house` Plan과 10개 Step**으로 관리됐다. 에이전트는 기존 홀을 바닥·외피·구조 상세가 있는 단일 개방 공간으로 구체화하고, 실패한 형상 생성과 구조해석을 수정한 뒤 Room·자산·instance·저장 모델을 연결했다. 아래는 최종 상태만 나열한 것이 아니라 각 Step에서 실제 수행한 일, 관찰 가능한 판단 기준, 사용한 자료와 결과를 정리한 것이다.

- 세션명: `Sample modeling with orchestrate`
- 세션 ID: `01a15462-1c4f-74a1-8515-82528f6cc57f`
- 세션 링크: [원 작업 세션](codex://threads/01a15462-1c4f-74a1-8515-82528f6cc57f)
- Plan: `plan_84b6571b9076` / scope: `house`
- Scene: `scene_08670c8b6ec1` / `MARKET HALL`
- 당시 작업 문서: `C:\Users\hopho\Desktop\Untitled.3dm`
- 조사한 DB: `C:\Users\hopho\Desktop\.almond\Untitled\scene.sqlite3`
- 산출물 스냅샷: `C:\Users\hopho\Desktop\.almond\sample modeling\tmp\market_hall_yesterday`
- 원 로그: `C:\Users\hopho\.codex\sessions\2026\10\19\rollout-2026-10-19T22-37-58-01a15462-1c4f-74a1-8515-82528f6cc57f.jsonl.zst`

**검수 범위:** 원 세션의 실행 로그, DB의 Plan·Step·참조·검증 기록, 스냅샷의 스크립트·입력·실패/성공 결과·이미지를 대조했다. 이번 조사에서 Rhino를 실행하거나 당시 스크립트를 재실행하지 않았다. 아래 수치는 당시 실행 결과와 보관 자료의 확인이며 현재 원본 3DM의 재검증 결과는 아니다. 판단에 관한 서술은 당시 보고·코드·입력·수정 행동에서 확인되는 기준을 뜻하며, 기록되지 않은 내적 추론을 복원한 것은 아니다.

**순서에 관한 주의:** DB의 Step은 아래 순서로 연결됐지만 실제 작업은 재검토와 병행 작업을 포함했다. 구조 Step을 완료 표시한 뒤에도 재하 조건 검증과 접합 상세 보완이 이어졌고 참조가 갱신됐다. 최종 스냅샷의 `design_basis.json` 등에는 뒤의 수정까지 반영돼 있으므로 이를 초기 단계부터 확정된 내용으로 읽으면 안 된다. 세션 후반의 Sample-2·Test 작업은 이 요약에서 제외했다.

## 1. programme — 작업 목적·대상·보존 조건 설정

**수행한 일.** 기존 도시 모델의 그룹과 객체를 조사하고 `MARKET HALL`을 작업 대상으로 식별했다. 그룹명과 대응하는 Scene을 등록하고, Scene ID·그룹 ID·구성원 GUID를 연결하는 자료를 만들었다. 기존 약 24m 경간·30m 깊이와 트러스 6열을 출발점으로 삼아 바닥, 하나의 개방 실내, 출입구가 있는 외피, 구조 상세와 해석, 프로젝트 자산·instance 연결을 목표로 정했다. 사용자가 orchestrator 사용을 명시한 뒤 `create_generation_plan`으로 Plan을 만들고 `get_generation_plan`으로 생성된 Step을 다시 확인했다.

**판단 기준.** 이미 있는 건물의 위치·큰 구성을 기반으로 구체화하되 다른 여섯 그룹은 보존하는 것이 작업 경계였다. Scene의 이름만으로 실제 편집 범위를 가정하지 않고 그룹 ID와 멤버 GUID 집합을 확인했다. 구조·외피를 구현한다는 목표와 입지·풍설·지반·관할 조건까지 확정된 설계라는 주장을 구분했다.

**활용 자료.** Scene `scene_08670c8b6ec1`, 그룹 `17d48c4c-80d1-4341-96cb-a0d6d74df21e`, 당시 `city_kit/group_scenes/inventory.json`·그룹별 멤버 목록, 사용자 지시, 기존 모델 관측. 원 로그 L1041–1057은 Scene/그룹 연결, L1117–1132는 Plan 생성·재조회·`programme=running`을 보여 준다.

**기록과 결과.** Step은 Scene·그룹을 입력 참조로, Scene·inventory를 출력 참조로 남겼다. 이는 전체 평면이나 구법 대안을 이 Step에서 최종 확정했다는 기록이 아니다. 앞서 사용자가 지정한 단일 개방 홀의 상세화 방향과 뒤 Step에서 구체화·수정한 설계 조건을 구분해야 한다. Plan은 모델을 자동 생성하는 실행기가 아니라 목표·순서·근거를 이어 주는 장부로 사용됐다. Plan 사용은 작업 시작부터 자동 적용된 것이 아니라 사용자의 명시 지시 뒤 도입됐다.

## 2. retrieve_structural_logic — 구축 자료 조사와 설계·해석 가정 구체화

**수행한 일.** Almond의 `get_construction_guidance`·`search_detail_sources`와 외부 자료를 함께 조회했다. 강재 트러스, 강관 접합, 기둥 베이스, 금속 데크 단열 지붕 등의 구성을 검토하고 모델 생성용 명세를 작성했다. 6m 간격의 트러스 6열을 유지하면서 트러스 패널을 3m 단위로 세분하고, 부재 단면·접합 조건·해석 축·12개 지점을 명시하는 방향을 정했다.

**판단 기준.** 참고 자료의 일반 원리를 실제 모델의 지지·하중 전달·외피 구성에 연결하려 했다. 자료를 찾았다는 사실만으로 프로젝트의 상세가 검증됐다고 보지는 않았다. 실제 물리 형상과 해석 축의 편심·단순화, 지붕 데크의 단순 표현, 접합 저항·제작·화재·외피 성능 등의 미해결 범위를 별도 가정으로 남겼다.

**활용 자료.** [SCI Trusses](https://steelconstruction.info/topics/design/trusses/), [SCI P178](https://www.steelconstruction.info/images/2/24/SCI_P178.pdf), 최종 설계 근거에 포함된 [SCI P207](https://www.steelconstruction.info/images/0/08/SCI_P207.pdf)과 [Sika Warm Roofs](https://nzl.sika.com/en/construction/roofing/warm-roofs.html), Almond 구법 라이브러리, `prepare.py`·`members.json`·`design_basis.json`. 외부 자료는 당시 세션이 사용한 출처이며 이번 조사에서 최신 내용이나 설계 적합성을 새로 심사한 것은 아니다.

**기록과 결과.** Step 출력 참조는 설계 근거 JSON과 SCI 자료를 연결했다. 최종 근거 파일에는 S355, 12개 고정 지점, 선형 탄성 강재 골조 및 별도 안정성 검토 조건, 지붕 추가 고정하중 0.5kN/㎡와 활하중 1.0kN/㎡ 등이 기록돼 있다. 최종 수치·구성은 뒤의 실패 수정까지 반영한 것이다. 주요 조사·보고는 원 로그 L1065–1163에 있다.

## 3. generate_structure — 물리 형상과 해석 모델 생성·실패 수정

**수행한 일.** `prepare.py`로 바닥 구성층, 강재 부재, 가새, 기초·베이스·앵커·받침, 유리·멀리언·패널·문틀·후레싱, 지붕 구성과 해석 축을 생성할 명세를 준비했다. `apply.cs`를 `execute_rhino_script`로 실행해 대상 그룹의 기존 118개 객체를 교체했다. 물리 부재와 해석 축을 이름·역할·단면·release 및 GUID 자료로 연결했다.

**판단과 교정.** 첫 실행은 `Hollow extrusion failed`, 다음 실행은 `Invalid geometry C1-1`로 실패했다. 에이전트는 국소 중공 단면 생성 시험과 생성법 수정으로 대응하고, 실패 뒤 현재 문서·그룹 상태를 조회했다. 반환 GUID가 0개라는 이유만으로 원본 보존을 단정하지 않았다. 실제 모델에 넣기 전에 형상 유효성과 닫힘을 확인하고, 다른 그룹을 보존하는 조건을 스크립트의 문서 경로·그룹 검사와 연결했다.

**활용 자료.** `prepare.py`, `geometry.tsv`, `members.json`, `apply.cs`, `tube_test.txt`, `after_attempt.txt`, `objects.tsv`, `physical_guids.txt`, `axis_guids.txt`, `support_guids.txt`, 원 로그 L1172–1257. 실패 응답은 L1208·1225, 국소 시험·수정은 L1237–1245에 남아 있다.

**기록과 결과.** 최초 적용 뒤 그룹은 1,526개 객체로 보고됐다. 이후 구조·외피·접합 보완을 거쳐 최종 1,602개가 됐으며, 최종 구성은 물리 솔리드 1,195개·해석 축 395개·지점 12개다. 따라서 최초 생성 Step의 완료 표시를 최종 모델의 완결 시점과 같게 볼 수 없다. Step의 주요 출력 참조는 생성 객체와 역할·GUID를 기록한 `objects.tsv`다.

## 4. validate_structure — 해석 실패 진단·조건 수정·재계산

**수행한 일.** 물리 부재와 연결된 해석 축·지점을 대상으로 `validate_structure`를 호출했다. 처음에는 `design_basis`에 `S355`를 잘못 넣어 입력 오류를 받았고, 재료 등급과 하중 조합 기준을 구분해 입력을 바로잡았다. 이후 DB에 남은 native 구조 검증 기록 4개를 따라 실패·수정·비교 사례를 보존했다. 공개 MCP 호출 4회는 입력 오류 1회와 실제 계산 3회이고, DB의 계산 기록 4건은 그 MCP 계산 3건과 직접 API 계산 1건이다. 두 집계의 ‘4’는 같은 실행 집합이 아니다.

| 검증 기록 | 관찰된 결과 | 수행한 판단·수정 |
|---|---|---|
| 1 | Mechanism으로 실패 | 끝 수직재까지 pin 연결하면 종방향 힘을 기둥으로 전달하지 못한다고 진단하고 12개 끝 부재를 기둥 연속부로 수정했다. 하중을 줄여 통과시키지 않았다. |
| 2 | SLS 처짐 718.02mm, ULS 이용률 8.4492로 실패 | 같은 높이의 수평 가새도 면적하중을 받는 문제를 추적했다. 가새 높이·단면과 연결재를 수정하고 재계산했다. |
| 3 | 처짐 76.882mm, 이용률 0.5892로 pass | pass 뒤에도 실제 지붕 808.96㎡와 자동 재하 934.96㎡의 불일치를 발견했다. 아래로 이동한 가새의 폐합 영역도 자동 재하에 포함되는 문제를 구분했다. |
| 4 | 지붕 높이 9.2m를 명시한 API 사례: 처짐 25.141mm, 이용률 0.4133 | 당시 공개 MCP에는 재하 높이 선택 입력이 없어 같은 Almond 엔진의 Python API로 `floor_loads.levels=[9.2]`를 지정했다. 808.96㎡만 재하한 사례를 별도로 남겼다. |

**가치판단.** `pass`라는 결과보다 의도한 하중 조건과 실제 산정량의 일치를 판단 기준으로 삼았다. 모델의 연결 문제와 도구 입력의 표현 한계를 나눠 대응했다. 기본 재하 사례와 높이를 지정한 사례는 입력이 다르므로 수치 차이를 모두 형상 개선의 효과로 돌릴 수 없다. 같은 지붕의 하중 조건을 맞추기 위해 형상을 계속 왜곡하는 대신 명시적 입력이 가능한 API를 사용한 것이 관찰 가능한 전환점이다.

**활용 자료.** `gravity_case.json`, `gravity_result_1.json`, `gravity_result_2.json`, `gravity_case_final.json`, `gravity_result_final.json`, `conditioned_model.json`, `correct_roof.cs`, `solve_roof_case.py`, `roof_case_api.json`, `roof_result_api.json`, DB `validation_runs` 1–4. 원 로그 L1266·1287·1312·1508·1541–1603·1755가 입력 오류, 불안정 진단, 재하 한계와 최종 참조 갱신을 보여 준다.

당시 Slack 보고: [실패 진단](https://hih-z6k5791.slack.com/archives/C0C6M4NRTLZ/p1792421917024819) · [API 전환](https://hih-z6k5791.slack.com/archives/C0C6M4NRTLZ/p1792422386750989) · [정확한 재하 결과](https://hih-z6k5791.slack.com/archives/C0C6M4NRTLZ/p1792422827590279). 링크는 원 보고의 확인 경로이며 수치 대조는 위 실행 로그·DB·보관 결과를 근거로 했다.

**결과와 한계.** Step은 최종적으로 세 계산/입력 자료군을 출력 참조에 연결했다. `final_state_verification.json`은 지붕 SLS 변위 25.141mm, ULS 최대 이용률 0.4133, 평형 오차 8.8e-08kN, 이차 부재의 해당 L/250 검사를 보고한다. 이는 설정한 예비 검토 조건의 결과다. 입지 풍설·지진·지반, 접합 저항, 모든 부재의 상세 설계 및 시공 승인을 증명하지 않는다. 구조 Step 완료 뒤에도 정확한 재하 사례를 병행 계산하고 근거를 갱신했다.

## 5. define_rooms — 단일 개방 실내의 계획 영역 정의

**수행한 일.** `upsert_design_room`과 이후 `link_instance.py`의 store API로 `MARKET HALL — Main Hall` Room을 등록·갱신했다. Room ID는 `room_b368bc7ed563`이고 경계는 `[76250,2350,0,99750,31650,6750]`mm다. 평면상 23.5m × 29.3m의 보수적 실내 계획 영역을 정했다.

**판단 기준.** Room을 건물 전체의 형상이나 외피 범위와 구분했다. 기둥 안쪽의 하나의 개방 홀이라는 공간 의도와 사용할 수 있는 보수적 경계를 기록하고, AABB 면적 688.55㎡를 실측 순사용면적으로 표현하지 않았다. 이 면적은 구조해석의 지붕 재하면적 808.96㎡와 다른 대상이다.

**활용 자료.** 실제 부재·그룹 관측, `design_basis.json`의 `clear_room_mm`, `link_instance.py`, DB `rooms.metadata_json`. 자유 metadata에는 `kind=interior_clear_planning_zone`, `single_open_space=true`, `clear_area_m2=688.55`, `finished_floor_z_mm=0`, `enclosing_instance_id`, 출입구별 방향·계획폭·모델 유효폭·용도를 남겼다.

**기록과 결과.** Step 출력은 Room ID다. 기록된 출입구는 동쪽 주출입 3600/3450mm, 남·북 출구 각각 1800/1650mm, 서쪽 적재문 4200/4100mm이며 후자는 보행 피난구로 계산하지 않는다고 적었다. 이 key들은 세션이 정한 자유 metadata로, 필수 스키마나 자동 피난 검증 입력은 아니었다. 등록과 관련 상태 전환은 원 로그 L1624–1636에 있다.

## 6. retrieve_assets — 직접 만든 건물을 프로젝트 자산으로 등록

**수행한 일.** 이미 만든 물리 형상을 `market-hall-detailed.3dm`으로 내보내고 `index_project_asset.py`에서 AlmondStore의 정식 저장 API를 사용해 `project-market-hall-detailed-v1`을 등록했다. 현재 프로젝트 DB의 `project-market-hall` 라이브러리에 한정했으며 전역 Generated/Drawing 라이브러리에 배포하지 않았다. 등록 뒤 asset 재조회·검색과 치수 일치를 확인하고 다른 라이브러리의 자산 수가 보존됐는지 검사했다.

**판단 기준.** 이번 과업에 맞는 대상은 기존 가구 자산 검색·배치가 아니라 직접 생성한 건물 조립체였다. 따라서 `retrieve_assets`라는 고정 단계명을 자산의 등록·발견 가능성 확보로 해석해 수행했다. 템플릿 이름만으로 실제 행위가 무엇이었는지 알 수 없다는 사례다.

**활용 자료.** `market-hall-detailed.3dm`, `bounds.tsv`, `physical_guids.txt`, `axis_guids.txt`, `support_guids.txt`, `design_basis.json`, `index_project_asset.py`, `registered_asset.json`, `before_project_asset.sqlite3`. 자산에는 앵커 `[88000,17000,0]`mm와 local AABB, Scene·그룹·Plan·객체 목록·설계 근거를 연결했다.

**기록과 결과.** Step 출력은 자산 ID다. 최종 자산 3DM에는 물리 형상 1,195개가 기록돼 있고 해석 축·지점과 구분됐다. 모델·상세가 수정된 뒤에는 자산도 다시 내보내고 등록 내용을 갱신했다. 등록·검색 관련 작업은 원 로그 L1432–1462·1634–1647, 최종 갱신은 L1730 이후에 나타난다.

## 7. place_assets — 기존 건물 형상과 instance 장부 연결

**수행한 일.** `register_scene_instance` 호출과 `link_instance.py`의 store API를 사용해 `instance_market_hall_main`을 등록했다. 이미 만들어진 Market Hall을 Scene 소속의 건물 전체 조립체로 기록하고, Room과의 관계 및 기존 Rhino 그룹·객체 목록을 metadata에 연결했다.

**판단 기준.** 전체 건물은 내부 계획 Room보다 크므로 Room 안에 들어가는 가구처럼 취급하지 않았다. 공식 `room_id`와 `rhino_guid`는 null로 두고 `room_boundary_id`·설명으로 둘러싸는 관계를 남겼다. 이는 여러 GUID를 공식 단일 `rhino_guid` 필드에 배열로 넣은 것이 아니며 Rhino block으로 변환한 것도 아니다. 해당 Step에서 건물을 새 위치에 한 번 더 삽입한 것으로 읽으면 안 된다.

**활용 자료.** `registered_asset.json`, `registered_instance.json`, `link_instance.py`, DB `instances.metadata_json`. metadata는 `rhino_group_id`, `physical_guids`, `analysis_guids`, `support_guids`, `plan_id`, 설계 근거 등을 담는다. 최종 확인에서 물리 객체 목록은 1,195개, 해석 축은 395개다.

**기록과 결과.** Step 출력은 instance ID다. 후속 `finalize.cs`는 각 구성 객체를 건물 전체의 별도 자산 배치로 오인하지 않도록 `market:assembly_instance_id`·`market:assembly_asset_id`를 사용했다. 1,602개 객체 각각에 전체 건물의 `almond:asset_id`를 찍어 중복 배치로 해석하는 일을 피하려는 조치였다. 원 로그 L1646–1662·1722–1730에 등록과 속성 정정이 남아 있다.

## 8. validate_layout — 배치 검사와 실제 공간·보존 상태 검토

**수행한 일.** `validate_scene_layout`을 호출하고, 별도 Rhino 스크립트와 외관·실내 이미지로 실내 계획 영역, 물리 객체, 외피, 주변 보존 상태를 검토했다. `check_spatial.cs`는 보수적 Room 경계와 Brep AABB의 교차를 검사하고 다른 여섯 그룹의 멤버 집합과 보존 GUID 존재를 대조했다. `check_envelope.cs`는 벽·지붕·바닥에 대한 표본 ray 검사를 수행했다.

**판단 기준.** 내장 배치검사의 0건을 건물 전체의 공간·접합 검증으로 확대하지 않았다. 이 Scene은 instance 하나이고 공식 `room_id`가 null이어서 다른 instance와의 충돌 쌍이나 Room 이탈 검사 대상이 없었다. 따라서 실제 실내와 외피는 별도 검사로 보완했다. 렌더가 보인다는 사실과 실제 형상 조건의 성립도 구분했다.

**활용 자료.** `validate_scene_layout`의 `method=rtree_world_aabb_broad_phase` 출력, `check_spatial.cs`·`spatial_check.txt`, `check_envelope.cs`·`envelope_check.txt`, `exterior.png`, `interior.png`, 다른 그룹의 원래·최종 GUID 목록. 내장 검사 결과는 원 로그 L1663, 별도 검사·보고는 L1682–1707에 있다.

**기록과 결과.** 내장 출력은 collision 0·outside_room 0이었다. 별도 최종 보고에는 실내 계획 영역 AABB와의 물리 객체 침범 0건, 다른 여섯 그룹의 멤버 집합 일치, 물리 닫힌 솔리드 1,195개, 외피 표본 ray 638개 hit·0 gap이 기록됐다. 이는 보수적 경계·표본 검사의 근거이며 정확한 전체 기하 교차, 연속 외피 폐합, 통행·피난·수밀·기밀 성능을 모두 검증했다는 뜻은 아니다.

## 9. resolve_collisions — 외피·접합 불일치 수정과 재확인

**수행한 일.** 검토에서 남은 외피 모서리 연결부 네 곳에 `CORNER-SEAL` 형상을 추가하고, 트러스 seat 12개와 stiffener 24개의 위치·접촉 관계를 보완했다. 변경 뒤 공간·외피 검사를 하고 최종 객체 목록, Scene/그룹 대응표, 자산 및 instance 연결 자료를 갱신했다. 일부 보완은 이 Step을 running으로 표시하기 전에 이미 수행됐으므로 상태 기록과 실제 실행은 완전히 일대일 시간 구간이 아니다.

**판단 기준.** 닫힌 솔리드 개수나 구조해석 pass만으로 실제 부재 사이의 접촉·외피 연결까지 해결됐다고 보지 않았다. CHS 하부와 받침, 기둥 면과 stiffener, 외피 모서리를 구체적인 위치 관계로 확인했다. 동시에 그러한 형상 접촉이 용접·볼트·접합 저항 등 제작·구조 상세의 완전한 설계와 같다고 주장하지 않았다.

**활용 자료.** 수정한 `prepare.py`, `check_spatial.cs`, `seat_contact_check.txt`, `geometry.tsv`, `objects.tsv`, `groups_final.tsv`, `document_map_current.json`, `scene_map_current.json`, `finalize.cs`. 모서리 보완은 원 로그 L1682–1703, 받침·stiffener 보완은 L1765 이후, 링크·검증 갱신은 L1712–1780에 있다.

**기록과 결과.** Step 출력 참조는 `spatial_check.txt`·`envelope_check.txt`다. 최종 대상 그룹은 1,602개이며, 받침 접촉 보고는 seat 상면 z=6890.45mm, stiffener와 seat 하부의 접점 z=6865.45mm 등을 남겼다. 변경 사항은 모델·연결 대장·자산 파일에도 반영했다. 모든 부재 쌍의 충돌이나 접합 성능을 포괄 검사한 것은 아니다.

## 10. final_validation — 저장 모델·DB·해석 근거 교차 검수

**수행한 일.** 최종 모델을 저장하고 `verify_saved.py`에서 저장된 3DM을 rhino3dm으로 다시 읽었다. 대상 GUID의 존재·Geometry.IsValid·Scene/assembly 속성, 다른 여섯 그룹의 원래 GUID 존재, 자산용 3DM의 객체 수·유효성을 확인했다. `verify_final_state.py`는 DB 무결성, Room/instance 수와 연결값, 자산의 GUID 목록, 명시 재하 결과 및 이차 부재 처짐 조건을 검사했다. 실내 이미지도 다시 열어 보고 최종 결과와 한계를 Slack에 전달했다.

**판단 기준.** 실행 성공·화면 표시·저장 성공·디스크 파일의 내용·DB 연결·해석 조건을 각각 다른 근거로 확인했다. 지붕 재하면적과 평형 오차를 최종 검사에 포함해 pass 토큰만으로 완료하지 않았다. 구성 객체에 건물 전체 자산 ID가 중복 배치로 기록되지 않았는지도 검사했다.

**맥락을 저장한 위치.** `finalize.cs`는 3DM 문서 속성 `project:group_scenes`에 Scene↔그룹 대응 JSON, `market:design_basis`에 설계 근거 JSON을 기록했다. 문서의 `market:room_id`·`market:instance_id`·`market:asset_id`와 `market:analysis_case`·`market:analysis_result`에는 연결 ID와 해석 파일 경로를 남겼다. 각 구성 객체에는 `market:assembly_instance_id`·`market:assembly_asset_id`·`market:interior_room_id`를 기록했다. 저장된 맥락의 존재와 후속 세션이 이를 실제로 조회·활용했다는 증거는 별개이며, 이번 조사에서는 후속 재사용까지 확인하지 않았다.

**활용 자료.** `verify_saved.py`, `saved_file_verification.json`, `verify_final_state.py`, `final_state_verification.json`, `roof_result_api.json`, `generation_plan_final.json`, `interior.png`, DB의 Plan·Step·validation_runs. 최종 저장 파일 검증은 원 로그 L1743–1755, 마지막 검사·Step 완료·Plan 재조회와 보고는 L1780–1810에 있다.

**확인된 결과.** 최종 파일 검증 보고는 대상 1,602개 GUID가 저장 파일에 존재하고 유효하며 다른 여섯 그룹의 원래 GUID도 존재한다고 기록한다. 자산용 3DM은 1,195개 물리 객체를 포함한다. DB 검증 보고는 Market Hall Room 1개·instance 1개·프로젝트 자산 연결과 구조 결과를 확인한다. 이번 조사에서도 원 DB의 무결성 `ok`, Plan 1개·Step 10개·구조 검증 기록 4개를 읽기 전용으로 대조했다.

당시 Slack의 [최종 보고](https://hih-z6k5791.slack.com/archives/C0C6M4NRTLZ/p1792423023765579)에서 결과 전달 내용을 확인할 수 있다.

**완료 상태와 남은 범위.** 최종 DB의 10개 Step과 Plan은 모두 `completed`다. 당시 코드는 Step 상태를 집계해 Plan 상태를 자동 갱신했으므로 이 값만으로 사용자의 별도 설계 승인이나 모든 미해결 사항의 해소를 입증하지 않는다. 최종 모델은 예비 검토·구체화 결과이며 지반·입지 하중·관할 기준·접합 저항·제작·피난 및 외피 성능의 최종 승인을 포함하지 않는다. 일부 출력 참조와 스크립트의 절대경로는 이동 전 위치를 가리킨다. 이번 요약은 원본 자료를 수정하거나 그 경로를 자동 복구하지 않았다.
