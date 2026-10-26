#### Block·주석

Rhino block instance는 하나의 형상 정의를 위치·회전·축척별로 배치한 객체다. 정의를 수정하면 이를 사용하는 모든 배치에 반영된다. ontological-component에 블록을 포함할 때는 정의 내부 객체 대신 최상위 배치 GUID를 등록한다.

중첩 구조는 `get_rhino_probe(probe="outline", options={"ids":[최상위_GUID], "depth":깊이})`로 재귀 조회한다. 경로는 최상위 배치에서 내부 멤버로 이어지며, 누적 변환으로 문서 좌표를 읽는다. 내부 GUID와 현재 선택 가능한 객체 ID는 다를 수 있다.

BlockEditNew에서는 부모를 연 뒤 `resolve-block`에 `path`를 한 단계씩 늘려 편집 후보를 확인한다. 정의 저장·멤버 교체 뒤에는 경로를 다시 조회한다. TextDot의 동명 대상은 같은 정의 안에서 찾고 주변 관계와 함께 읽는다.

의미와 편집 목적에 맞춰 block을 생성·재사용하거나 Explode할 수 있다. block/group이라는 이유만으로 항상 보존하거나 항상 해체하지 않는다. 반복 실물의 블록 이름은 `UNIT A`처럼 특정 배치에 고정하지 않는다. 폴딩도어 실물과 개폐 궤적은 구별하며, 문짝·프레임은 재사용 block으로, 함께 설명할 사용 관계는 일반 group으로 구성할 수 있다.

등록된 객체를 block으로 교체하거나 해체하기 전에는 현재 직접 소유 객체·영속 group GUID와 관련 등록을 확인한다. 등록 정보를 담은 원본 객체를 먼저 삭제한 뒤 sync만 하면 복구된다고 가정하지 않는다. 현재 공개 API가 지원하는 전환 순서와 교체 후 live 정합을 확인하고, 안전한 전환이 지원되지 않으면 도구 개선 대상으로 남긴다. DB나 소유권 UserString 직접 삭제로 오류를 우회하지 않는다.

#### Group

일반 group은 선택·편집 편의를 위한 객체 묶음이다. 내부에 일반 group·block을 둘 수 있고, 멤버십이 겹칠 수도 있다. group의 겹치는 멤버십과 block 정의의 중첩은 다르다. 블록 내부 중첩은 위의 `outline` 재귀 조회와 `resolve-block` 경로 조회를 사용한다.

등록 ontological-component의 부모 group에는 자손 객체도 포함되지만 직접 소유권은 자식에 남는다. 자식을 해제하려면 부모에서 먼저 분리하고, 부모를 해제하면 자식은 root로 남는다. 객체는 저장된 모델 경로+GUID, group은 영속 group GUID로 식별한다. ontological-component group은 의미 있는 이름을 쓰고 객체 Name은 필요할 때만 채운다.
