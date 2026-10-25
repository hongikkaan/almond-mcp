"""Per-server services with call-local overrides for native helper reports.

Feature factories capture this object, never the sender or store itself. The
namespace remains owned by the assembling server, so runtime rebinding and
fixture replacement are visible on the next call without module-global state.
"""
from contextlib import contextmanager
from contextvars import ContextVar


class FeatureContext:
    def __init__(self, namespace: dict):
        self._namespace = namespace
        self._overrides = ContextVar("almond_feature_overrides", default=None)

    def __getattr__(self, name):
        overrides = self._overrides.get()
        if overrides is not None and name in overrides:
            return overrides[name]
        try:
            return self._namespace[name]
        except KeyError:
            raise AttributeError(name) from None

    @contextmanager
    def override(self, **values):
        token = self._overrides.set({**(self._overrides.get() or {}), **values})
        try:
            yield self
        finally:
            self._overrides.reset(token)
