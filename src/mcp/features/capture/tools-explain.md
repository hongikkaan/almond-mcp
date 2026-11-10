# tools.py explain

## capture_conditioning_pass

<!-- instruction:capture_conditioning_pass -->
Rhino 카메라 경로를 따라 RGB·에지·깊이 프레임과 카메라 기록을 저장합니다. 활성 카메라·디스플레이와 출력 파일이 변경되며 카메라 복원은 실패할 수 있습니다. 깊이 출력은 8비트 회색조입니다.

반환: frames_requested·frames_captured·errors, out_dir·camera_json·videos와 document 정보를 반환합니다. videos는 인코딩을 사용할 수 없으면 null일 수 있습니다. 프레임 파일은 rgb/edge/depth 폴더, 카메라 기록은 camera.json에 저장됩니다.

Args:
    shot: 카메라 경로를 담은 JSON 문자열입니다. type=orbit은 center:[x,y,z], radius, height와 선택적 start_deg/end_deg/lens/target_height; type=track은 cam0/cam1/target0/target1 좌표와 선택적 lens; type=keyframes는 camera·target·선택적 lens를 가진 keyframes 배열입니다. frames 기본값은 81, lens는 mm, 좌표는 문서 단위입니다.
    out_dir: 관리형 세션: 선택한 Plan의 산출물 디렉터리 아래 상대 폴더이며, 기본값은 conditioning입니다. 먼저 Plan을 선택합니다. 독립 실행: 출력 폴더이며, 기본값은 현재 작업 디렉터리입니다.
    width: 출력 프레임의 픽셀 너비이며, 짝수여야 합니다.
    height: 출력 프레임의 픽셀 높이이며, 짝수여야 합니다.
    passes: 쉼표로 구분한 패스 이름: rgb, edge, depth.
    fps: 샷에 기록할 초당 프레임 수입니다.
    chunk: Rhino 실행 청크마다 캡처할 프레임 수입니다.
    rgb_mode: RGB 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Rendered입니다.
    edge_mode: 에지 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Technical입니다.
    invert_depth: true이면 깊이 패스를 반전합니다.
<!-- /instruction:capture_conditioning_pass -->
