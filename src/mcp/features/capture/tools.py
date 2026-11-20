"""MCP registration for camera-path conditioning capture."""
from almond_mcp.tool_response import error_payload
from almond_mcp.tool_declarations import public_tool
import json

from almond_mcp.features.capture import conditioning


def register(mcp, context):
    """Register capture tools against this server's live connection context."""
    @public_tool(mcp, wrapped=True)
    def capture_conditioning_pass(
        shot: str,
        out_dir: str = "",
        width: int = 832,
        height: int = 480,
        passes: str = "rgb,edge,depth",
        fps: int = 16,
        chunk: int = 16,
        rgb_mode: str = "Rendered",
        edge_mode: str = "Technical",
        invert_depth: bool = False,
    ) -> str:
        """활성 Rhino 뷰의 카메라 경로를 따라 RGB·에지·깊이 PNG 및 카메라 기록 저장. 촬영 중 뷰가 바뀌며 전체 뷰 상태가 복원되지 않을 수 있음. 패스별 PNG 생성과 대상 가시성은 출력 파일에서 확인. 같은 출력 폴더를 재사용하면 기존 파일을 덮어쓰고 일부 이전 프레임이 남을 수 있음.

        Args:
            shot: 카메라 경로를 담은 JSON 문자열. orbit은 center:[x,y,z], radius, height, 선택 start_deg·end_deg·lens·target_height. track은 cam0·cam1·target0·target1 좌표, 선택 lens. keyframes는 camera·target·선택 lens를 가진 keyframes 배열. type으로 경로 유형 지정. frames 생략 시 81, lens는 mm, 좌표는 문서 단위.
            out_dir: 관리형은 먼저 Plan을 선택한 뒤 산출물 폴더 기준 상대 경로 사용(생략 시 conditioning). 독립 실행에서 생략 시 현재 작업 폴더.
            width: 짝수 픽셀.
            height: 짝수 픽셀.
            passes: 쉼표로 구분한 rgb, edge, depth.
            chunk: 청크당 프레임 수.
            rgb_mode: 설치된 Rhino 디스플레이 모드 이름.
            edge_mode: 설치된 Rhino 디스플레이 모드 이름.
            invert_depth: false이면 가까울수록 밝게 표현.
        """
        try:
            shot_dict = json.loads(shot)
            frames = conditioning.build_path(shot_dict)
        except (ValueError, KeyError, TypeError) as e:
            return json.dumps(error_payload(f"Bad shot description: {e}"))
        pass_list = tuple(p.strip() for p in passes.split(",") if p.strip())
        try:
            summary = conditioning.capture_conditioning_pass(
                frames, out_dir, context._send_and_receive, width=width, height=height, passes=pass_list,
                rgb_mode=rgb_mode, edge_mode=edge_mode, invert_depth=invert_depth, chunk=chunk, fps=fps)
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"))
        except Exception as e:  # noqa: BLE001
            return json.dumps(error_payload(f"Conditioning pass failed: {e}"))
        return json.dumps(summary)


    return {"capture_conditioning_pass": capture_conditioning_pass}
