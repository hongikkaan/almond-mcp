"""Selection regressions; optional live smoke uses only a newly created sleeper."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import purge

E = Path('C:/src/mcp/runtime')


def proc(pid, name, args, parent=0, started=None):
    return purge.Process(pid, parent, started or 1000+pid, name,
                         'C:/Apps/'+name, [name]+args)


def mcp(pid=4, slot='A', parent=0):
    return proc(pid, 'python.exe', ['-B', '-X', 'utf8', '-u', str(E/'mcp_server.py'),
                                   '--port', str(5501+'ABCDEFGHIJ'.index(slot))], parent)


def codex(pid=3, slot='A', parent=0):
    return proc(pid, 'codex.exe', ['-c', "mcp_servers.rhino_session.command='"+str(E/'.venv/Scripts/python.exe')+"'",
            '-c', "mcp_servers.rhino_session.args=['-B','"+str(E/'mcp_server.py')+"','--port','"+str(5501+'ABCDEFGHIJ'.index(slot))+"']"], parent)


def rhino(pid=2, parent=0):
    return proc(pid, 'Rhino.exe', ['C:/Models/House.3dm', '/nosplash',
                '/runscript=-_RunPythonScript ('+str(E/'rhino_start.py')+')'], parent)


class SelectionTests(unittest.TestCase):
    def classify(self, rows, records=(), protected=()):
        return purge.classify(rows, E, records, protected)

    def test_unrelated_names_not_selected(self):
        self.assertEqual(self.classify([proc(1,'Rhino.exe',[]), proc(2,'python.exe',['x.py']), proc(3,'codex.exe',[])]), [])

    def test_python_code_mention_not_selected(self):
        self.assertEqual(self.classify([proc(1,'python.exe',['-c',"print('"+str(E/'mcp_server.py')+"')"])]), [])

    def test_powershell_command_mention_not_selected(self):
        self.assertEqual(self.classify([proc(1,'powershell.exe',['-Command',str(E/'launch.ps1')])]), [])

    def test_codex_prompt_mention_not_selected(self):
        self.assertEqual(self.classify([proc(1,'codex.exe',['Please read '+str(E/'mcp_server.py')])]), [])

    def test_other_installation_not_selected(self):
        p=mcp();p.argv=[x.replace(str(E),str(E.parent.parent/'Almond-backup/_engine')) for x in p.argv]
        self.assertEqual(self.classify([p]), [])

    def test_cmd_explorer_double_quotes(self):
        p=proc(1,'cmd.exe',['/c',str(E/'Almond 시작.cmd')])
        self.assertEqual(self.classify([p])[0].kind,'launcher')

    def test_cmd_drop_file(self):
        p=proc(1,'cmd.exe',['/c','not a parsed direct path'])
        p.command='cmd.exe /c ""'+str(E/'Almond 시작.cmd')+'" "C:\\Model Folder\\House.3dm""'
        self.assertEqual(self.classify([p])[0].kind,'launcher')

    def test_cmd_shell_expression_not_selected(self):
        p=proc(1,'cmd.exe',['/c','echo '+str(E/'Almond 시작.cmd')])
        p.command='cmd.exe /c echo "'+str(E/'Almond 시작.cmd')+'"'
        self.assertEqual(self.classify([p]),[])

    def test_managed_roots_selected(self):
        self.assertEqual({t.kind for t in self.classify([rhino(),codex(),mcp()])}, {'rhino','codex','mcp'})

    def test_previous_cli_namespace_is_still_recognized_for_existing_processes(self):
        p = codex()
        p.argv = [arg.replace('rhino_session', 'almond_parallel_cli') for arg in p.argv]
        self.assertEqual(self.classify([p])[0].kind, 'codex')

    def test_fields_from_different_namespaces_do_not_establish_ownership(self):
        p = codex()
        p.argv[-1] = p.argv[-1].replace('rhino_session', 'almond_parallel_cli')
        self.assertEqual(self.classify([p]), [])

    def test_stable_interpreter_requires_this_checkouts_mcp_entry(self):
        p = codex()
        old = str(E / '.venv/Scripts/python.exe')
        current = str(E.parent.parent / 'engine/.venv/Scripts/python.exe')
        p.argv = [arg.replace(old, current) for arg in p.argv]
        self.assertEqual(self.classify([p])[0].kind, 'codex')
        p.argv = [arg.replace(str(E / 'mcp_server.py'), 'C:/another-checkout/mcp_server.py') for arg in p.argv]
        self.assertEqual(self.classify([p]), [])

    def test_orphan_mcp_is_leftover(self):
        rows=self.classify([mcp()]);self.assertTrue(rows[0].orphan)
        self.assertEqual(len(purge.planned(rows,'leftovers')),1)

    def test_running_codex_protects_mcp(self):
        self.assertEqual(purge.planned(self.classify([codex(),mcp()]),'leftovers'),[])

    def test_all_ten_ports_keep_slot_identity_and_live_mcp_protection(self):
        for port, slot in enumerate('ABCDEFGHIJ', 5501):
            with self.subTest(slot=slot):
                self.assertEqual(purge.slot_for_port(str(port)), slot)
                rows = self.classify([codex(slot=slot), mcp(slot=slot)])
                self.assertEqual({r.slot for r in rows}, {slot})
                self.assertEqual(purge.planned(rows, 'leftovers'), [])
        for value in ('5000', '5500', '5511', 'invalid', None):
            self.assertIsNone(purge.slot_for_port(value))

    def test_other_slot_does_not_protect_orphan(self):
        self.assertEqual([t.process.pid for t in purge.planned(self.classify([codex(slot='B'),mcp()]),'leftovers')],[4])

    def test_auto_launcher_protects_uncertain_helpers(self):
        launcher=proc(1,'powershell.exe',['-File',str(E/'launch.ps1')])
        self.assertEqual(purge.planned(self.classify([launcher,mcp()]),'leftovers'),[])

    def test_rhino_never_default_target(self):
        self.assertEqual(purge.planned(self.classify([rhino()]),'leftovers'),[])

    def test_records_do_not_establish_ownership(self):
        r=dict(pid=9,process_start_ticks='1009',label='A')
        self.assertEqual(self.classify([proc(9,'Rhino.exe',[])],[r]),[])

    def test_record_start_time_mismatch_ignored(self):
        rows=self.classify([rhino()],[dict(pid=2,process_start_ticks='999',label='A')])
        self.assertIsNone(rows[0].slot)

    def test_record_corrobates_slot(self):
        rows=self.classify([rhino()],[dict(pid=2,process_start_ticks='1002',label='E')])
        self.assertEqual(rows[0].slot,'E')

    def test_helper_descendant_selected(self):
        child=proc(8,'node.exe',['some-helper.js'],parent=3)
        self.assertEqual({t.process.pid for t in self.classify([codex(),child])},{3,8})

    def test_reused_parent_not_followed(self):
        child=proc(8,'node.exe',[],parent=3,started=500)
        self.assertEqual({t.process.pid for t in self.classify([codex(),child])},{3})

    def test_no_rhino_plugin_sweep(self):
        child=proc(8,'python.exe',['plugin.py'],parent=2)
        self.assertEqual({t.process.pid for t in self.classify([rhino(),child])},{2})

    def test_no_terminal_or_gui_sweep(self):
        rows=[codex(),proc(8,'WindowsTerminal.exe',[],parent=3),proc(9,'Rhino.exe',[],parent=3)]
        self.assertEqual({t.process.pid for t in self.classify(rows)},{3})

    def test_cleanup_and_parent_are_protected(self):
        rows=[codex(),mcp(parent=3)]
        self.assertEqual(self.classify(rows,protected=(4,)),[])

    def test_action_rechecks_orphan_status(self):
        selection=self.classify([mcp()])
        class System:
            def snapshot(self):return [codex(),mcp()]
            def terminate(self,p):raise AssertionError('must not terminate')
        result=purge.execute(selection,'leftovers',System(),E)
        self.assertIn('건너뜀',result[0]['result'])

    def test_action_rechecks_pid_reuse(self):
        selection=self.classify([mcp()])
        newer=mcp();newer.started+=1
        class System:
            def snapshot(self):return [newer]
            def terminate(self,p):raise AssertionError('must not terminate')
        result=purge.execute(selection,'force',System(),E)
        self.assertIn('건너뜀',result[0]['result'])

    def test_close_does_not_force_rhino(self):
        calls=[]
        class System:
            def snapshot(self):return [rhino()]
            def close_window(self,p):calls.append(p.pid);return 'close requested'
            def terminate(self,p):raise AssertionError('must not terminate Rhino')
        purge.execute(self.classify([rhino()]),'close',System(),E)
        self.assertEqual(calls,[2])


class WindowsSmoke(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='win32' and os.environ.get('ALMOND_PURGE_SMOKE')=='1', 'opt-in disposable-process test')
    def test_disposable_orphan_termination_and_unrelated_survival(self):
        root=Path(__file__).resolve().parent/'data'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='_purge_test_',dir=root) as tmp:
            engine=Path(tmp)/'_engine';engine.mkdir()
            script=engine/'mcp_server.py'
            script.write_text('import time\ntime.sleep(60)\n',encoding='utf-8')
            sleeper=subprocess.Popen([sys.executable,'-B',str(script),'--port','5505'],creationflags=subprocess.CREATE_NO_WINDOW)
            other=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(60)'],creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                system=purge.Windows();rows=system.snapshot()
                targets=purge.classify(rows,engine,protected=(os.getpid(),))
                candidates=purge.planned(targets,'leftovers')
                self.assertTrue(candidates)
                self.assertNotIn(other.pid,{t.process.pid for t in candidates})
                original=next(t.process for t in candidates if t.process.pid==sleeper.pid)
                wrong=purge.Process(original.pid,original.parent,original.started+1,original.name,original.exe)
                with self.assertRaises(RuntimeError):system.open_match(wrong,True)
                self.assertIsNone(sleeper.poll())
                results=purge.execute(candidates,'leftovers',system,engine)
                sleeper.wait(timeout=10)
                self.assertIsNone(other.poll())
                self.assertTrue(any('종료됨' in r['result'] for r in results))
            finally:
                for p in (sleeper,other):
                    if p.poll() is None:p.terminate()
                    p.wait(timeout=10)


if __name__=='__main__':unittest.main()
