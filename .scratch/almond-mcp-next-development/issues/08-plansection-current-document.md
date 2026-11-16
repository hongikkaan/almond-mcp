# 08: 활성 모델의 PlanSection 생성·갱신·이동과 결과 반환

**What to build:** 사용자가 활성 모델의 평면·단면을 생성하고, 유효 도면을 갱신하거나 옮긴 뒤 생성 도구에서 결과를 바로 확인할 수 있다.

**Blocked by:** None (can start immediately)

**Status:** integrated

- [ ] 공개 elevation·expected_model_path를 제거하고 small_details 기본값을 false로 적용한다. 내부 문서 바인딩 보호는 유지한다.
- [ ] Create·Update·Move를 실제 배치, clipping 식별 및 이후 Update 가능 여부로 검증한다.
- [ ] 생성 응답에 draw plane, clipping 식별, 실제 적용 레이어와 소스 객체 수 및 hidden·locked 처리 조건을 제공한다. 활성 모델에서 첨부 미포함이 실제 동작과 일치한다.
- [ ] 별도 결과 도구의 등록과 후속 안내를 제거하고, 성공·부분 결과·취소·실패 응답 및 공유 스키마의 정합성을 확인한다.

**검증 상태**

`ddf08a3d`에 구현 통합, `0fb74fe`에서 공개 계약 연결. MCP·네이티브 모의 52개, 형상 알고리즘·API 모의 80개와 이후 stdio 계약 통과. 실모델 생성·이동·갱신 검수 대기.
