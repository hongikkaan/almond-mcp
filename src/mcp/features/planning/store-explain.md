# store.py explain

Step 판단 takeaways/design_rationale는 Loop별 선택 문자열이다. 생략/None 유지, 빈 문자열 비움이며 이전 Loop·immutable revision JSON은 다시 쓰지 않는다. 공개 완료 호출은 모든 입력·revision 검증 뒤 `_before_complete` hook에서 native 정리 완료를 확인하고 한 번의 DB revision으로 완료한다. hook의 외부 효과는 SQL rollback으로 복구되지 않는다.

## response-803

<!-- instruction:response-803 -->
Plan revision conflict: expected {0}, current {1}. Read the current plan before updating; no change was made.
<!-- /instruction:response-803 -->
