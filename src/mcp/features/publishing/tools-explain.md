# tools.py explain

## publish_objects_to_chestnut

<!-- instruction:publish_objects_to_chestnut -->
Rhino 객체를 물리·콜라이더 설정이 있는 GLB로 Chestnut에 게시합니다. 원본 문서 경로·GUID 등의 metadata도 업로드됩니다.

Args:
    guids: 내보낼 Rhino 객체 GUID입니다. 관련 없는 문서 객체는 제외합니다.
    asset_name: Chestnut에 표시할 사람이 읽을 수 있는 이름입니다.
    asset_id: 연결된 갱신에 사용할 선택적이고 안정적인 ID입니다. 생략하면 Rhino 문서와 GUID에서 결정적으로 생성합니다.
    body_type: 건축물은 "static", 고정되지 않은 소품은 "dynamic", 스크립트로 구동하는 객체는 "kinematic"입니다.
    collider: 의도한 콜라이더: "box", "convex", "compound", "trimesh". 현재 Chestnut은 필요하면 box로 대체합니다.
    preserve_scale: 모델을 1미터 크기의 전시 소품으로 정규화하지 않고 Rhino의 실제 치수를 유지합니다.
    mass: 물리 질량(kg)입니다. static 바디는 항상 0을 사용합니다.
<!-- /instruction:publish_objects_to_chestnut -->

## publish_to_chestnut

<!-- instruction:publish_to_chestnut -->
Rhino 객체를 동작 프리셋으로 Chestnut에 게시합니다. 원본 문서 경로·GUID 등의 metadata도 업로드됩니다.

Args:
    guids: 관찰, 선택 또는 모델링 결과에서 얻은 현재 Rhino 객체 GUID입니다. 스크립팅 호출은 필요하지 않습니다.
    asset_name: 사람이 읽을 수 있는 자산 이름입니다.
    behavior: 선택적인 의미 기반 프리셋입니다. auto는 이름에서 추론하고, architecture는 고정형, object는 이동 가능하고 중력의 영향을 받는 유형, animated는 스크립트 구동형입니다. 의도한 물리 설정을 선택하며 애니메이션을 생성하지 않습니다.
    asset_id: Chestnut 자산의 고정 ID입니다. 같은 ID로 게시하면 기존 자산을 갱신합니다. 비우면 서버가 생성합니다.
<!-- /instruction:publish_to_chestnut -->

## response-847

<!-- instruction:response-847 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-847 -->
