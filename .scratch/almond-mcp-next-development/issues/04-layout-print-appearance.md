# 04: 모델 viewport와 Layout의 출력 표현 구분

**What to build:** 모델 viewport는 일반 표시로 보고, Layout은 인쇄용 선폭과 색으로 확인할 수 있다.

**Blocked by:** None (can start immediately)

**Status:** integrated

- [ ] 의도적으로 PrintDisplay 상태를 구분한 복제본에서 viewport와 Layout의 실제 이미지 및 선폭을 비교한다.
- [ ] 표시 상태와 실제 가시 객체를 대조한다. 숨겨진 내용만 있는 종이는 정상적인 빈 출력으로 처리한다.
- [ ] Detail이 있는 별도 사례에서 clipping과 잠금 상태의 영향, 기존 상태 복원을 조사한다. 제품 범위가 바뀌는 조정은 사용자 답변을 받은 뒤 처리한다.

**검증 상태**

Layout `1a04ebc`, Model `77d3935`에 통합. 각 변경에서 캡처 관련 검사 57개와 Rhino SDK 참조 컴파일 통과. 실제 Model 색·선폭과 Layout Detail clipping·가시성 검수 대기.
