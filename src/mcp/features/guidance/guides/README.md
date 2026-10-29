# 모델링 지침 원본

이 폴더의 모델링 가이드와 참고자료는 `get_modeling_guide`가 직접 읽는 원본이다. `mcp-guide-map.json`은 주제와 본문 절·이미지를 연결한다. 문서 생성 단계나 복사본은 없다.

최초 사용 시 `get_modeling_guide(topic="basic")`로 [BASIC-INSTRUCTIONS.md](../../../BASIC-INSTRUCTIONS.md)를 읽는다. `topic="index"`는 주제별 가이드를 안내한다.

독립 개발 검사는 `src/mcp/run_tests.ps1 -Development` 및 루트 통합 검사를 사용한다. 원본·이미지·지침 파일의 정규화 해시로 `guide_version`을 계산하고, 실행 중 source fingerprint가 바뀌면 새 클라이언트 세션이 필요하다.

`authoring-request.md`는 원래 작성 요청을 보존하는 참고자료다. 실행 지침과 구분한다.
