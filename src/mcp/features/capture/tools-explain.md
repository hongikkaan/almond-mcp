# tools.py explain

## capture_conditioning_pass

<!-- instruction:capture_conditioning_pass -->
활성 Rhino 뷰의 카메라 경로를 따라 RGB·에지·깊이 PNG와 카메라 기록을 저장합니다. 관리형 연결은 Plan 작업 공간을 먼저 선택합니다. 촬영 중 활성 뷰가 변경되며 전체 뷰 상태의 복원은 보장되지 않습니다.

status와 frames_captured는 촬영 실행 결과이며 대상이 잘 보인다는 보장은 아닙니다. videos의 null은 MP4가 생성되지 않았음을 뜻합니다. 같은 출력 폴더를 재사용하면 기존 프레임·기록을 덮어쓰고 잔여 프레임이 남을 수 있습니다.

Args:
    shot: 카메라 경로를 담은 JSON 문자열입니다. type=orbit은 center:[x,y,z], radius, height와 선택적 start_deg/end_deg/lens/target_height; type=track은 cam0/cam1/target0/target1 좌표와 선택적 lens; type=keyframes는 camera·target·선택적 lens를 가진 keyframes 배열입니다. frames 기본값은 81, lens는 mm, 좌표는 문서 단위입니다.
    out_dir: 관리형 세션: 선택한 Plan의 산출물 디렉터리 아래 상대 폴더이며, 기본값은 conditioning입니다. 먼저 Plan을 선택합니다. 독립 실행: 출력 폴더이며, 기본값은 현재 작업 디렉터리입니다.
    width: 짝수, 기본 832px.
    height: 짝수, 기본 480px.
    passes: 쉼표 구분: rgb, edge, depth. 기본 전체.
    fps: 초당 프레임 수. 기본 16.
    chunk: 청크당 프레임 수. 기본 16.
    rgb_mode: RGB 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Rendered입니다.
    edge_mode: 에지 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Technical입니다.
    invert_depth: 기본 false: 가까울수록 밝음.
<!-- /instruction:capture_conditioning_pass -->
