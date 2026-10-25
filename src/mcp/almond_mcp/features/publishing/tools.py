"""Chestnut publishing tools and their standard-library upload helpers.

The context supplies the current bridge sender, target URL and exported helper
bindings at call time, preserving per-server runtime and monkeypatch behavior.
"""

import hashlib
import json
import os
import re
import socket
import tempfile
import urllib.error
import urllib.request
import uuid


def register(mcp, context):
    """Register publishing tools and return their server compatibility bindings."""
    def _slug(value: str) -> str:
        """Create a filesystem/API-safe identifier without losing stable identity."""
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug[:48] or "rhino-asset"

    def _post_multipart(url: str, fields: dict[str, str], file_path: str) -> dict:
        """POST a GLB and text fields using only the Python standard library."""
        boundary = f"----AlmondMCP{uuid.uuid4().hex}"
        chunks: list[bytes] = []

        for name, value in fields.items():
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ])

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as glb:
            file_bytes = glb.read()
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: model/gltf-binary\r\n\r\n",
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])

        request = urllib.request.Request(
            url,
            data=b"".join(chunks),
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Chestnut returned HTTP {exc.code}: {detail}") from exc

    @mcp.tool()
    def publish_objects_to_chestnut(
        guids: list[str],
        asset_name: str,
        asset_id: str = "",
        body_type: str = "static",
        collider: str = "box",
        preserve_scale: bool = True,
        mass: float = 0.0,
    ) -> str:
        """
        Exports specific Rhino objects as one GLB and publishes them to Chestnut.

        Use this after execute_rhino_script (and optionally validate_structure), passing
        the returned object GUIDs. Reusing asset_id updates the existing Chestnut asset
        without changing placements that already reference it.

        Args:
            guids: Rhino object GUIDs to export. Unrelated document objects are excluded.
            asset_name: Human-readable name shown in Chestnut.
            asset_id: Stable optional ID for linked updates. Generated deterministically
                      from the Rhino document and GUIDs when omitted.
            body_type: "static" for architecture, "dynamic" for loose props, or
                       "kinematic" for script-driven objects.
            collider: Collider intent: "box", "convex", "compound", or "trimesh".
                      Chestnut currently falls back to a box where needed.
            preserve_scale: Keep Rhino's real-world dimensions instead of normalizing
                            the model to a one-metre display prop.
            mass: Physics mass in kilograms. Static bodies always use zero.
        Returns:
            JSON containing the stable Chestnut asset ID, URL, metadata, and whether
            the operation created or updated the asset.
        """
        if not guids:
            return json.dumps({"status": "error", "message": "At least one Rhino object GUID is required."})
        if not asset_name.strip():
            return json.dumps({"status": "error", "message": "asset_name is required."})

        body_type = body_type.lower()
        collider = collider.lower()
        if body_type not in {"static", "dynamic", "kinematic"}:
            return json.dumps({"status": "error", "message": "body_type must be static, dynamic, or kinematic."})
        if collider not in {"box", "convex", "compound", "trimesh"}:
            return json.dumps({"status": "error", "message": "collider must be box, convex, compound, or trimesh."})
        if mass < 0:
            return json.dumps({"status": "error", "message": "mass cannot be negative."})

        output_path = os.path.join(tempfile.gettempdir(), f"almond_{uuid.uuid4().hex}.glb")
        payload = json.dumps({
            "type": "export_glb",
            "guids": guids,
            "output_path": output_path,
        }).encode("utf-8")

        try:
            export_result = json.loads(context._send_and_receive(payload, timeout=90.0))
            if export_result.get("status") != "success":
                return json.dumps(export_result)

            source_key = "|".join([
                export_result.get("document_path", ""),
                *sorted(export_result.get("object_guids", guids)),
            ])
            source_hash = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:12]
            stable_id = asset_id.strip() or f"{context._slug(asset_name)}-{source_hash}"
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", stable_id):
                return json.dumps({
                    "status": "error",
                    "message": "asset_id must contain only letters, numbers, dot, underscore, or hyphen (max 80).",
                })

            metadata = {
                "assetId": stable_id,
                "name": asset_name.strip(),
                "preserveScale": preserve_scale,
                "bodyType": body_type,
                "collider": collider,
                "mass": 0.0 if body_type == "static" else (mass or 1.0),
                "units": export_result.get("units", "Unknown"),
                "axisConvention": "glTF Y-up",
                "source": {
                    "application": "Rhino",
                    "documentPath": export_result.get("document_path", ""),
                    "documentSerial": export_result.get("document_serial"),
                    "objectGuids": export_result.get("object_guids", guids),
                    "sourceId": f"rhino:{source_hash}",
                },
                "bounds": export_result.get("bounds"),
            }
            chestnut_result = context._post_multipart(
                f"{context.CHESTNUT_URL}/api/props/upsert",
                {"metadata": json.dumps(metadata)},
                output_path,
            )
            if not chestnut_result.get("success"):
                return json.dumps({"status": "error", "message": chestnut_result.get("error", "Chestnut rejected asset.")})
            return json.dumps({
                "status": "success",
                "chestnut_url": context.CHESTNUT_URL,
                **chestnut_result,
            })
        except ConnectionRefusedError:
            return json.dumps({"status": "error", "message": "Rhino bridge is unavailable. Start RhinoAlmondBridge first."})
        except socket.timeout:
            return json.dumps({"status": "error", "message": "Rhino GLB export timed out."})
        except Exception as exc:
            return json.dumps({
                "status": "error",
                "chestnut_url": context.CHESTNUT_URL,
                "message": str(exc),
            })
        finally:
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except OSError:
                pass

    @mcp.tool()
    def publish_to_chestnut(
        guids: list[str],
        asset_name: str,
        behavior: str = "auto",
        asset_id: str = "",
    ) -> str:
        """
        Publishes Rhino objects to Chestnut using safe semantic defaults.

        This is the preferred publishing tool for normal use. It hides collider,
        scale, mass, and rigid-body details. Call it when the user says things such
        as "publish that to Chestnut".

        Args:
            guids: Rhino object GUIDs returned by execute_rhino_script.
            asset_name: Human-readable asset name.
            behavior: Optional semantic preset:
                "auto"         — infer architecture versus movable object from name
                "architecture" — fixed building, terrain, structure, or enclosure
                "object"       — movable physical prop affected by gravity
                "animated"     — script-driven door, lift, platform, or mechanism
            asset_id: Optional stable link ID. Omit for a deterministic Rhino link.
        """
        behavior = behavior.lower().strip()
        if behavior not in {"auto", "architecture", "object", "animated"}:
            return json.dumps({
                "status": "error",
                "message": "behavior must be auto, architecture, object, or animated.",
            })

        if behavior == "auto":
            architecture_words = {
                "architecture", "building", "pavilion", "house", "wall", "floor",
                "roof", "terrain", "landscape", "bridge", "structure", "room",
                "facade", "tower", "canopy", "shell", "frame",
            }
            words = set(re.findall(r"[a-z]+", asset_name.lower()))
            behavior = "architecture" if words & architecture_words else "object"

        presets = {
            "architecture": {"body_type": "static", "collider": "box", "mass": 0.0},
            "object": {"body_type": "dynamic", "collider": "box", "mass": 1.0},
            "animated": {"body_type": "kinematic", "collider": "box", "mass": 0.0},
        }
        preset = presets[behavior]
        return context.publish_objects_to_chestnut(
            guids=guids,
            asset_name=asset_name,
            asset_id=asset_id,
            body_type=preset["body_type"],
            collider=preset["collider"],
            preserve_scale=True,
            mass=preset["mass"],
        )

    return {
        "_slug": _slug,
        "_post_multipart": _post_multipart,
        "publish_objects_to_chestnut": publish_objects_to_chestnut,
        "publish_to_chestnut": publish_to_chestnut,
    }
