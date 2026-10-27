# -*- coding: utf-8 -*-
"""Public editor commands against a source-linked detector, in an owned CLI process."""
import json
import os
import traceback
import Rhino
import System
from System import Action, Array, Object
from System.IO import File, Path
from System.Reflection import Assembly
from Eto.Forms import Application


def start(fixture_dll, new_output_directory, scheme='AlmondObservationBDD'):
    """Schedule the BDD after the launching script returns; never use a working process."""
    if '/scheme=' + scheme not in System.Environment.GetCommandLineArgs():
        raise RuntimeError('The dedicated fixture scheme is required')
    initial = Rhino.RhinoDoc.ActiveDoc
    if initial is not None and (initial.Modified or initial.Path or initial.Objects.Count):
        raise RuntimeError('An empty, unmodified startup document is required')
    dll = Path.GetFullPath(fixture_dll)
    out = Path.GetFullPath(new_output_directory)
    if not File.Exists(dll):
        raise RuntimeError('The source-linked fixture DLL is missing')
    if os.path.exists(out):
        raise RuntimeError('The output directory must be new')
    os.makedirs(out)
    result_path = os.path.join(out, 'result.json')
    report = {'status': 'starting', 'stages': [], 'version': str(Rhino.RhinoApp.Version),
              'validation_mode': 'installed_public_editor_commands_and_source_linked_detector'}
    state = {}

    def persist():
        File.WriteAllText(result_path, json.dumps(report, ensure_ascii=True, indent=2))

    def check(condition, message):
        if not condition:
            raise RuntimeError(message)

    def observe(stage):
        raw = state['observe'].Invoke(None, Array[Object]([state['doc']]))
        value = json.loads(str(raw))
        report['stages'].append({'stage': stage, 'editor': value})
        persist()
        return value

    def close():
        if state.get('doc') is not None:
            state['doc'].Modified = False
            state['doc'].Dispose()
        persist()
        Rhino.RhinoApp.Exit()

    def fail(error):
        report.update(status='failed', error=str(error), traceback=traceback.format_exc())
        persist()
        try:
            if state.get('editor_active'):
                Rhino.RhinoApp.RunScript('_BlockCancel', False)
        finally:
            Application.Instance.AsyncInvoke(Action(close))

    def after_block_cancel():
        try:
            current = observe('after_block_cancel')
            check(current['mode'] == 'model' and current['stable'] is True,
                  'BlockCancel did not restore stable model context')
            state['editor_active'] = False
            report['status'] = 'passed'
            close()
        except Exception as error:
            fail(error)

    def inspect_block():
        try:
            current = observe('block_edit')
            check(current['mode'] == 'block' and current['stable'] is False,
                  'BlockEditNew was not identified as unstable block editing')
            target = current.get('target') or {}
            check(target.get('instance_id') == str(state['instance']) and
                  target.get('definition_id') == str(state['definition']),
                  'The editor target does not identify the fixture instance/definition')
            check(Rhino.RhinoApp.RunScript('_BlockCancel', False), 'BlockCancel was not accepted')
            Application.Instance.AsyncInvoke(Action(after_block_cancel))
        except Exception as error:
            fail(error)

    def after_group_cancel():
        try:
            current = observe('after_group_cancel')
            check(current['mode'] == 'model' and current['stable'] is True,
                  'Group cancel did not restore stable model context')
            state['editor_active'] = False
            doc = state['doc']
            geometry = Rhino.Geometry.BoundingBox(0, 0, 0, 10, 10, 10).ToBrep()
            try:
                index = doc.InstanceDefinitions.Add('BDD block', '', Rhino.Geometry.Point3d.Origin,
                    Array[Rhino.Geometry.GeometryBase]([geometry]),
                    Array[Rhino.DocObjects.ObjectAttributes]([Rhino.DocObjects.ObjectAttributes()]))
            finally:
                geometry.Dispose()
            check(index >= 0, 'Could not create the fixture block definition')
            state['definition'] = doc.InstanceDefinitions[index].Id
            state['instance'] = doc.Objects.AddInstanceObject(index, Rhino.Geometry.Transform.Translation(30, 0, 0))
            doc.Objects.UnselectAll()
            check(doc.Objects.Select(state['instance']), 'Could not select the fixture block')
            state['editor_active'] = True
            check(Rhino.RhinoApp.RunScript('_BlockEditNew', False), 'BlockEditNew was not accepted')
            Application.Instance.AsyncInvoke(Action(inspect_block))
        except Exception as error:
            fail(error)

    def inspect_group():
        try:
            current = observe('group_edit')
            check(current['mode'] == 'group' and current['stable'] is False,
                  'GroupEdit was not identified as unstable group editing')
            target = current.get('target') or {}
            check(target.get('editor_label') == 'BDD group' and target.get('original_member_count') == 2,
                  'The editor lost the original fixture group label/member count')
            check(Rhino.RhinoApp.RunScript('_BlockCancel', False), 'Group BlockCancel was not accepted')
            Application.Instance.AsyncInvoke(Action(after_group_cancel))
        except Exception as error:
            fail(error)

    def run():
        try:
            Assembly.LoadFrom(Path.Combine(Path.GetDirectoryName(dll), 'Newtonsoft.Json.dll'))
            assembly = Assembly.LoadFrom(dll)
            state['observe'] = assembly.GetType('RhinoAlmondBridge.EditingContext').GetMethod('Observe')
            path = os.path.join(out, 'editor.3dm')
            seed = Rhino.RhinoDoc.CreateHeadless(None)
            options = Rhino.FileIO.FileWriteOptions()
            try:
                options.SuppressDialogBoxes = True
                options.SuppressAllInput = True
                check(seed.WriteFile(path, options), 'Could not seed the disposable document')
            finally:
                options.Dispose()
                seed.Dispose()
            doc, already_open = Rhino.RhinoDoc.Open(path)
            state['doc'] = doc
            check(doc is not None and not already_open and not doc.IsHeadless, 'Expected a fresh visible fixture document')
            current = observe('before_editor')
            check(current['mode'] == 'model' and current['stable'] is True, 'Clean model was not stable')
            first = doc.Objects.AddPoint(Rhino.Geometry.Point3d(0, 0, 0))
            second = doc.Objects.AddPoint(Rhino.Geometry.Point3d(20, 0, 0))
            check(doc.Groups.Add('BDD group', Array[System.Guid]([first, second])) >= 0, 'Could not create the fixture group')
            check(doc.Objects.Select(first) and doc.Objects.Select(second), 'Could not select both fixture members')
            state['editor_active'] = True
            check(Rhino.RhinoApp.RunScript('_GroupEdit', False), 'GroupEdit was not accepted')
            Application.Instance.AsyncInvoke(Action(inspect_group))
        except Exception as error:
            fail(error)

    persist()
    Application.Instance.AsyncInvoke(Action(run))
