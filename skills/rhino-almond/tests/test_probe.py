import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

SKILL = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("almond_probe", SKILL / "scripts" / "almond_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="probe-", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.model = self.base / "모형 __CALL__ (1).3dm"
        self.model.write_bytes(b"fixture path only; native runner separately tests real 3dm")
        self.job = self.base / "input.json"
        self.request = dict(tool="outline", model_path=str(self.model),
                            artifact_dir=str(self.base), options={"scope":"document"})
        self.job.write_text(json.dumps(self.request), encoding="utf-8")

    def prepared(self):
        return probe.prepare(self.job)

    def report(self, manifest, **override):
        value = dict(schema="rhino-almond-result/1", run_id=manifest["run_id"],
                     tool=manifest["tool"], expected_model_path=manifest["model_path"],
                     model_path=manifest["model_path"], status="ok", data={"records":[]})
        value.update(override)
        Path(manifest["result_path"]).write_text(json.dumps(value), encoding="utf-8")

    def test_separate_runs_and_model_path_are_preserved(self):
        a,b = self.prepared(),self.prepared()
        self.assertNotEqual(a["run_id"], b["run_id"])
        source = Path(a["query_path"]).read_text(encoding="utf-8")
        self.assertIn("__CALL__ (1).3dm", source)
        self.assertIn('report["data"] = AlmondSpatial.Outline(doc, options);', source)
        self.assertNotIn('JObject.Parse(__OPTIONS__)', source)
        self.assertEqual(source.count("public static List<Guid> Run("), 1)

    def test_no_helper_usings_after_type_declarations(self):
        source=Path(self.prepared()["query_path"]).read_text(encoding="utf-8")
        body=source[source.index("public static class AlmondSpatial"):]
        self.assertNotRegex(body, r"(?m)^using [\w.]+;")

    def test_missing_and_partial_are_not_success(self):
        m=self.prepared()
        data,code=probe.read_result(m["manifest_path"])
        self.assertEqual((data["status"],code), ("report_not_ready",3))
        Path(m["result_path"]+".partial").write_text("{",encoding="utf-8")
        data,code=probe.read_result(m["manifest_path"])
        self.assertEqual(code,3)
        self.assertTrue(data["partial_exists"])

    def test_valid_and_failed_reports_remain_distinct(self):
        m=self.prepared();self.report(m)
        self.assertEqual(probe.read_result(m["manifest_path"])[1],0)
        self.report(m,status="error",message="geometry query failed")
        self.assertEqual(probe.read_result(m["manifest_path"])[1],2)

    def test_other_run_cannot_be_read_as_this_result(self):
        m=self.prepared();self.report(m,run_id=uuid.uuid4().hex)
        with self.assertRaisesRegex(ValueError,"run_id"):
            probe.read_result(m["manifest_path"])

    def test_other_model_cannot_be_reported_as_success(self):
        m=self.prepared();self.report(m,model_path=str(self.base/"different.3dm"))
        with self.assertRaisesRegex(ValueError,"different model"):
            probe.read_result(m["manifest_path"])

    def test_read_budget_is_enforced(self):
        m=self.prepared();self.report(m,data={"text":"x"*2000})
        with self.assertRaisesRegex(ValueError,"budget"):
            probe.read_result(m["manifest_path"],1024)

    def test_invalid_job_does_not_create_run_folder(self):
        for change in ({"tool":"missing"}, {"model_path":"relative.3dm"},
                       {"options":[]}, {"options":{"x":float("nan")}}):
            with self.subTest(change=change):
                value=dict(self.request,**change)
                self.job.write_text(json.dumps(value),encoding="utf-8")
                with self.assertRaises((ValueError,TypeError)):
                    self.prepared()
        self.assertEqual(list(self.base.glob("rhino-almond-*")),[])

    def test_resolve_block_requires_a_real_path_array(self):
        for options in ({}, {"path":[]}, {"path":["bad"]}, {"path":[1]},
                        {"path":[str(uuid.uuid4())]*66},
                        {"path":[str(uuid.uuid4())],"scope":"document"}):
            with self.subTest(options=options), self.assertRaises((ValueError,TypeError)):
                probe.compose_source("resolve-block",options,self.model,self.base/"out.json","id")
        source=probe.compose_source("resolve-block",{"path":[str(uuid.uuid4())]},
                                    self.model,self.base/"out.json","id")
        self.assertIn("AlmondSpatial.ResolveBlock(doc,",source)

if __name__=="__main__":
    unittest.main(verbosity=2)
