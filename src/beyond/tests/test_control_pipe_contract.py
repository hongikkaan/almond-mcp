import asyncio
import json
import os
from uuid import uuid4

import pytest

from winpipe import ControlError, PipeControl


def test_pipe_authenticates_and_releases_original_owner():
    async def scenario():
        sdk = os.environ["ALMOND_TEST_DOTNET"]
        server = os.environ["ALMOND_PIPE_TEST_HOST"]
        child = await asyncio.create_subprocess_exec(
            sdk, server, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        )
        try:
            advertisement = json.loads(await child.stdout.readline())
            owner = uuid4().hex
            foreign = uuid4().hex
            bad_token = PipeControl({**advertisement, "access_token": "incorrect"})
            try:
                with pytest.raises(ControlError, match="Invalid AlmondRhino control token"):
                    await bad_token.request("attach", session_token=foreign)
            finally:
                await bad_token.close()

            stale_process = PipeControl({**advertisement, "process_start_ticks": "1"})
            with pytest.raises(ControlError, match="process has changed"):
                await stale_process.request("attach", session_token=foreign)

            client = PipeControl(advertisement)
            try:
                assert await client.request("attach", session_token=owner) == {"session": owner}
                with pytest.raises(ControlError, match="cannot change session owner"):
                    await client.request("attach", session_token=foreign)
            finally:
                await client.close()

            assert (await child.stdout.readline()).decode().strip() == owner
        finally:
            child.stdin.close()
            if await child.wait() != 0:
                raise RuntimeError("Offline pipe fixture did not shut down cleanly.")

    asyncio.run(asyncio.wait_for(scenario(), 15))
