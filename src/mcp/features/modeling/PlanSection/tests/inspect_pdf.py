"""Inspect the real-model PDF from check_model.py; CPython + pypdf."""
import json
import os
from pathlib import Path
import tempfile
from pypdf import PdfReader
from pypdf.generic import ContentStream

folder = Path(os.environ.get('PLANSECTION_TEST_OUTPUT') or Path(tempfile.gettempdir()) / 'PlanSection-checks')
report = json.loads((folder / 'model.json').read_text())
assert report['passed'], 'Run check_model.py successfully first'
pdf = report['pdf']
reader = PdfReader(pdf['file'])
assert len(reader.pages) == 1, 'Expected one page'
page = reader.pages[0]
assert not list(page.images), 'Expected vector PDF'
paper = [float(value)*25.4/72 for value in (page.mediabox.width,page.mediabox.height)]
assert all(abs(a-b) < .02 for a,b in zip(paper,pdf['paper_mm'])), 'Wrong paper size'
ops = ContentStream(page.get_contents(),reader).operations
assert any(op in (b'W',b'W*') for args,op in ops), 'Missing page clipping'
assert sum(op in (b'l',b'c') for args,op in ops) > 100, 'Unexpectedly empty drawing'
result = dict(passed=True,file=pdf['file'],vector=True,paper_mm=paper,
              code_sha256=report['code_sha256'],operations=len(ops))
(folder / 'pdf.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
