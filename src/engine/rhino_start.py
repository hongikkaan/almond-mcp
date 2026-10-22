# -*- coding: utf-8 -*-
"""Bind the selected saved model to an owned, document-checked native transport.

No Python listener/Idle handler; no model edits, saves, or stock C# queries.
The .NET file lease remains held until this Rhino process closes.
"""
from __future__ import print_function
import json
import os
import sys
import traceback
import System
import Rhino
import scriptcontext as sc

ENGINE = os.path.dirname(os.path.abspath(__file__))
SLOTS = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J')
try:
    text_type = unicode
except NameError:
    text_type = str


def canonical(path):
    return os.path.normcase(os.path.abspath(text_type(path)))


def read(path):
    return json.loads(text_type(System.IO.File.ReadAllText(path)))


def write(path, value):
    temporary = path + '.new-' + System.Guid.NewGuid().ToString('N')
    try:
        System.IO.File.WriteAllText(temporary, json.dumps(value, ensure_ascii=True, indent=2),
                                   System.Text.UTF8Encoding(False))
        if System.IO.File.Exists(path):
            System.IO.File.Replace(temporary, path, None)
        else:
            System.IO.File.Move(temporary, path)
    finally:
        if System.IO.File.Exists(temporary):
            System.IO.File.Delete(temporary)


def main():
    folder = text_type(System.Environment.GetEnvironmentVariable('ALMOND_SESSION_FOLDER') or '')
    token = text_type(System.Environment.GetEnvironmentVariable('ALMOND_SESSION_TOKEN') or '')
    if not folder or not token:
        raise RuntimeError('Use Almond Start and select a saved model.')
    process = System.Diagnostics.Process.GetCurrentProcess()
    lease = None
    shared = None
    try:
        for unused in range(100):
            launch = read(os.path.join(folder, 'launch.json'))
            if launch.get('pid'):
                break
            System.Threading.Thread.Sleep(50)
        slot = launch.get('label')
        model = text_type(launch.get('model_path') or '')
        storage = os.path.join(os.path.dirname(model), '.almond')
        expected = os.path.join(storage, '.sessions', token)
        if (launch.get('schema') != 'almond-project' or slot not in SLOTS
                or launch.get('storage_protocol') != 2
                or launch.get('token') != token or launch.get('pid') != int(process.Id)
                or launch.get('process_start_ticks') != str(process.StartTime.ToUniversalTime().Ticks)
                or int(launch.get('port', 0)) != 5501 + SLOTS.index(slot)
                or canonical(folder) != canonical(expected)
                or canonical(launch.get('storage') or '') != canonical(storage)
                or canonical(launch.get('engine') or '') != canonical(ENGINE)):
            raise RuntimeError('Model, project folder, token, process, or slot binding mismatch.')
        if (System.DateTime.Now - process.StartTime).TotalSeconds > 360:
            raise RuntimeError('Startup expired. Close this Rhino and start the slot again.')
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None or not doc.Path or canonical(doc.Path) != canonical(model):
            raise RuntimeError('Rhino did not open the selected .3dm. No bridge was attached.')
        # Environment variables were set BEFORE Rhino launched, not after a library cached TEMP.
        expected_temp = canonical(os.path.join(storage, 'tmp'))
        if canonical(System.IO.Path.GetTempPath()) != expected_temp:
            raise RuntimeError('Rhino temp directory does not match the selected project.')
        assemblies = [a for a in System.AppDomain.CurrentDomain.GetAssemblies()
                      if a.GetName().Name == 'RhinoAlmondBridge']
        if len(assemblies) != 1:
            raise RuntimeError('RhinoAlmondBridge plugin is not uniquely loaded.')
        versions = [str(a.InformationalVersion) for a in assemblies[0].GetCustomAttributes(False)
                    if a.GetType().FullName == 'System.Reflection.AssemblyInformationalVersionAttribute']
        if versions != ['0.7.0-rc.2']:
            raise RuntimeError('Unreviewed Rhino bridge version: ' + str(versions))
        if 'Almond.project_lease' in sc.sticky:
            raise RuntimeError('This Rhino already owns a project. Close it before changing models.')
        from System.Reflection import Assembly
        native_dll = os.path.join(ENGINE, 'native', 'bin', 'Release', 'net8.0', 'Almond.Engine.dll')
        native = Assembly.LoadFrom(native_dll)
        shared_type = native.GetType('AlmondEngine.SharedStorageLease', True)
        shared = System.Activator.CreateInstance(shared_type, System.Array[System.Object]([storage]))
        lease = System.IO.FileStream(os.path.join(folder, 'rhino.lock'), System.IO.FileMode.OpenOrCreate,
                                     System.IO.FileAccess.ReadWrite, getattr(System.IO.FileShare, 'None'))
        if ENGINE not in sys.path:
            sys.path.insert(0, ENGINE)
        from bridge import BridgeManager, RhinoBackend
        ready_path = os.path.join(folder, 'ready.json')
        backend = RhinoBackend(ready_path, token, model, doc.RuntimeSerialNumber)
        manager = BridgeManager(sc.sticky, backend)
        # Keep the lease if bridge startup partially succeeds; never allow another writer into it.
        sc.sticky['Almond.project_lease'] = lease
        sc.sticky['Almond.shared_storage_lease'] = shared
        lease = None
        shared = None
        status = manager.start(int(launch['port']))
        ready = dict(schema='almond-project', storage_protocol=2, valid=True,
                     label=slot, token=token, port=int(launch['port']),
                     pid=int(process.Id), process_start_ticks=str(process.StartTime.ToUniversalTime().Ticks),
                     status=status, owners=sorted(backend.owners(int(launch['port']))),
                     document_serial=str(doc.RuntimeSerialNumber), model_path=model,
                     document_path=text_type(doc.Path), storage=storage,
                     session_dir=folder, ready_path=ready_path,
                     state_db=os.path.join(storage, 'scene.sqlite3'),
                     temp=os.path.join(storage, 'tmp'), rhino_temp=text_type(System.IO.Path.GetTempPath()),
                     model_units=str(doc.ModelUnitSystem))
        write(ready_path, ready)
        Rhino.RhinoApp.WriteLine('Almond {0}: {1}'.format(slot, model))
        Rhino.RhinoApp.WriteLine('Shared data: {0}'.format(storage))
    except Exception:
        System.IO.File.WriteAllText(os.path.join(folder, 'last-error.txt'), traceback.format_exc())
        Rhino.RhinoApp.WriteLine('Almond startup failed; no model command or save was sent.')
    finally:
        if lease is not None:
            lease.Dispose()
        if shared is not None:
            shared.Dispose()
        process.Dispose()


if __name__ == '__main__':
    main()
