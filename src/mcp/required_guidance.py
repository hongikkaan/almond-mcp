"""Read the two mandatory documents without inventing their storage location.

The owner of the final documents supplies their paths. A missing, blank,
unreadable or changing source fails the whole bundle; partial guidance is never
returned as a successful initialization. Each initialized server keeps its own
bundle until the next server start.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping


REQUIRED_DOCUMENTS = ("BASIC-INSTRUCTIONS.md", "design_judgment.md")


class RequiredGuidanceError(RuntimeError):
    """The complete mandatory instruction bundle could not be loaded."""


def _read(path: Path) -> str:
    try:
        text = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    except (OSError, UnicodeError) as exc:
        raise RequiredGuidanceError(f"Cannot read required guidance {path.name}: {exc}") from exc
    if not text.strip():
        raise RequiredGuidanceError(f"Required guidance is empty: {path.name}")
    return text


@dataclass(frozen=True)
class RequiredDocument:
    name: str
    text: str
    sha256: str


@dataclass(frozen=True)
class RequiredGuidance:
    documents: tuple[RequiredDocument, ...]
    version: str

    def fields(self) -> dict:
        """Filename fields contain full text; metadata contains no body copy."""
        return {**{document.name: document.text for document in self.documents},
                "_metadata": {"required_guidance_version": self.version,
                              "sha256": {document.name: document.sha256 for document in self.documents}}}

    def instructions(self) -> str:
        """Render labelled document blocks, without a content size cap.

        These blocks do not represent separate messages or guarantee an
        agent's execution order.
        """
        parts = [f"Almond required guidance version={self.version}"]
        for document in self.documents:
            parts.append(f"BEGIN REQUIRED DOCUMENT {document.name} sha256={document.sha256}\n"
                         f"{document.text}\nEND REQUIRED DOCUMENT {document.name}")
        return "\n\n".join(parts)


def load_required_guidance(sources: Mapping[str, Path]) -> RequiredGuidance:
    """Load a complete, stable snapshot from explicitly supplied source paths.

    Reopening a server calls this again, so content edits change the version.
    The returned immutable snapshot does not silently refresh mid-session.
    """
    if set(sources) != set(REQUIRED_DOCUMENTS):
        raise RequiredGuidanceError("Configure exactly these required documents: "
                                    + ", ".join(REQUIRED_DOCUMENTS))
    paths = [Path(sources[name]) for name in REQUIRED_DOCUMENTS]
    try:
        identities = [path.resolve() for path in paths]
    except OSError as exc:
        raise RequiredGuidanceError(f"Cannot resolve required guidance sources: {exc}") from exc
    if len(set(identities)) != len(paths):
        raise RequiredGuidanceError("Each required document must have its own source file.")
    texts = [_read(path) for path in paths]
    if texts != [_read(path) for path in paths]:
        raise RequiredGuidanceError("Required guidance changed while reading; start a new session.")
    documents = tuple(RequiredDocument(name, text, hashlib.sha256(text.encode("utf-8")).hexdigest())
                      for name, text in zip(REQUIRED_DOCUMENTS, texts))
    identity = [(document.name, document.sha256) for document in documents]
    version = hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode("utf-8")).hexdigest()
    return RequiredGuidance(documents, version)
