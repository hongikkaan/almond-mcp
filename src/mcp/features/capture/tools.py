"""MCP registration for camera-path conditioning capture."""
from almond_mcp.tool_response import error_payload
from almond_mcp.tool_declarations import public_tool
import json

from fastmcp.tools import ToolResult
from pydantic import StrictFloat
from typing import Literal

from almond_mcp.features.capture import conditioning, manipulation


def register(mcp, context):
    """Register capture tools against this server's live connection context."""
    @public_tool(mcp, wrapped=True, errors=True)
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
            rgb_mode: RGB 패스에 사용할 뷰 메뉴의 래스터 표시 모드 이름 또는 GUID. 기본 Rendered. 이름이 중복되면 GUID 사용.
            edge_mode: 에지 패스에 사용할 뷰 메뉴의 래스터 표시 모드 이름 또는 GUID. 기본 Technical. depth는 별도 깊이 버퍼를 사용.
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


    @public_tool(mcp, wrapped=False, annotations={"readOnlyHint": False, "destructiveHint": False,
                                                  "idempotentHint": False})
    def manipulate_view(
        operation: Literal["rotate", "zoom"],
        mode: Literal["look", "orbit"] = None,
        yaw_deg: StrictFloat = None,
        pitch_deg: StrictFloat = None,
        factor: StrictFloat = None,
        expected_viewport_id: str = None,
        expected_model_path: str = None,
    ) -> ToolResult:
        """카메라를 조작하여 뷰포트를 조작하는 툴이다. 활성 일반 원근 모델 뷰포트에서만 rotate 또는 zoom을 적용한다. 확대 검수는 실제 뷰포트를 확대한 뒤 capture_03-current_view tool을 대상 없이 호출해 확인한다.

        Args:
            operation: rotate는 시점 회전, zoom은 실제 뷰포트 확대·축소.
            mode: rotate 전용. look은 카메라 위치 고정, orbit은 바라보는 지점과 카메라 거리 고정.
            yaw_deg: rotate 전용. 상대 좌우 각도(도). 양수는 오른쪽, 생략하면 0. pitch_deg와 둘 다 0이거나 회전 결과가 수직이면 적용하지 않는다.
            pitch_deg: rotate 전용. 상대 상하 각도(도). 양수는 위쪽, 생략하면 0. yaw_deg 적용 후 회전한다.
            factor: zoom 전용. 0보다 큰 유한 배율. 2는 2배 확대, 0.5는 절반으로 축소.
            expected_viewport_id: 주면 현재 활성 뷰포트 ID와 일치해야 한다.
            expected_model_path: 주면 현재 문서의 모델 경로와 일치해야 한다.
        """
        return manipulation.execute(
            context._send_and_receive, operation, mode=mode, yaw_deg=yaw_deg,
            pitch_deg=pitch_deg, factor=factor, expected_viewport_id=expected_viewport_id,
            expected_model_path=expected_model_path,
        )

    return {"capture_conditioning_pass": capture_conditioning_pass, "manipulate_view": manipulate_view}
