#! python 2
# -*- coding: utf-8 -*-
"""Interactive duu entry; computation and preview are shared with Almond MCP."""
import System
import Rhino


def main():
    helper = None
    for assembly in System.AppDomain.CurrentDomain.GetAssemblies():
        if assembly.GetName().Name == "RhinoAlmondBridge":
            helper = assembly.GetType("RhinoAlmondBridge.IntersectionTools", False)
            break
    if helper is None:
        Rhino.RhinoApp.WriteLine(
            "[TrueOverlap] Load the updated Almond Bridge in this Rhino before running duu.")
        return
    helper.GetMethod("RunInteractive").Invoke(None, None)


if __name__ == "__main__":
    main()
