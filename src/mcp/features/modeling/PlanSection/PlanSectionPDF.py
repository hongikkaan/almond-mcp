# -*- coding: utf-8 -*-
"""Run PlanSectionPDF.ps1; shares PlanSection's RhinoCommon geometry and PDF code."""
import os
import sys
import json
import traceback
import clr
import Rhino as R
import System
sys.path.insert(0, os.path.dirname(__file__))
import PlanSection as ps


def choose_planes(planes, keep):
    import System.Windows.Forms as F
    from System.Drawing import Size
    form = F.Form(Text='PlanSection PDF - drawings', ClientSize=Size(650,480),
                  StartPosition=F.FormStartPosition.CenterScreen)
    choices = F.CheckedListBox(Dock=F.DockStyle.Fill, CheckOnClick=True)
    for cp in planes: choices.Items.Add(cp.Name or str(cp.Id), False)
    detail = F.CheckBox(Text='Keep small elevation details (unchecked = Omit)', Checked=keep,
                        AutoSize=True, Dock=F.DockStyle.Top)
    buttons = F.FlowLayoutPanel(Dock=F.DockStyle.Bottom, Height=42)
    all_button = F.Button(Text='Select all', AutoSize=True)
    ok = F.Button(Text='Export PDF', AutoSize=True, DialogResult=F.DialogResult.OK)
    cancel = F.Button(Text='Cancel', AutoSize=True, DialogResult=F.DialogResult.Cancel)
    def select_all(sender, event):
        for i in range(choices.Items.Count): choices.SetItemChecked(i,True)
    all_button.Click += select_all
    for control in (all_button,ok,cancel): buttons.Controls.Add(control)
    for control in (choices,detail,buttons): form.Controls.Add(control)
    form.AcceptButton, form.CancelButton = ok, cancel
    try:
        if form.ShowDialog()!=F.DialogResult.OK: return [], keep
        return [planes[i] for i in choices.CheckedIndices], bool(detail.Checked)
    finally:
        form.Dispose()


def main():
    options = json.loads(os.environ.get('PLANSECTION_PDF_OPTIONS') or '{}')
    model, folder = options.get('model'), options.get('output')
    keep = options.get('small_details',True)
    interactive = not model
    clr.AddReference('System.Windows.Forms')
    import System.Windows.Forms as F
    if interactive:
        picker = F.OpenFileDialog(Title='Select source Rhino model', Filter='Rhino model (*.3dm)|*.3dm',
                                  CheckFileExists=True, Multiselect=False)
        try:
            if picker.ShowDialog()!=F.DialogResult.OK: return
            model = picker.FileName
        finally: picker.Dispose()
    if not model or not os.path.isfile(model) or os.path.splitext(model)[1].lower()!='.3dm':
        raise ValueError('Select an existing .3dm file')
    doc = R.RhinoDoc.OpenHeadless(model)
    if doc is None: raise IOError('Cannot open source model')
    model_cache = None
    try:
        planes = ps.clipping_planes(doc)
        if not planes: raise ValueError('No clipping planes in this document')
        if interactive:
            planes,keep = choose_planes(planes,keep)
            if not planes: return
        elif options.get('clipping'):
            wanted = set(name.lower() for name in options['clipping'])
            found = set()
            selected = []
            for cp in planes:
                matches = wanted.intersection([(cp.Name or '').lower(),str(cp.Id).lower()])
                if matches: selected.append(cp); found.update(matches)
            if wanted-found: raise ValueError('Clipping not found: '+', '.join(sorted(wanted-found)))
            planes = selected
        if not folder:
            picker = F.FolderBrowserDialog(Description='Folder for drawing PDFs', ShowNewFolderButton=True)
            picker.SelectedPath = os.path.dirname(model)
            try:
                if picker.ShowDialog()!=F.DialogResult.OK: return
                folder = picker.SelectedPath
            finally: picker.Dispose()
        if not os.path.isdir(folder): os.makedirs(folder)
        errors = []
        model_cache = ps.ModelCache(doc) if len(planes)>1 else None
        for index,cp in enumerate(planes,1):
            name = cp.Name or str(cp.Id)
            drawing = None
            def progress(stage): System.Console.WriteLine(u'{0}/{1} {2}: {3}'.format(index,len(planes),name,stage))
            try:
                paper,scale = ps.pdf_settings(cp)
                drawing = ps.generate(doc,cp,target=R.Geometry.Plane.WorldXY,
                                      small_details=keep,progress=progress,model_cache=model_cache)
                path = ps.export_pdf(doc,drawing,folder,name,paper,scale)
                System.Console.WriteLine(u'Exported: '+path)
                System.Console.WriteLine(json.dumps(drawing['report']))
            except Exception as error:
                errors.append(name)
                System.Console.WriteLine(u'FAILED {0}: {1}'.format(name,error))
            finally:
                if drawing is not None:
                    ps.dispose_drawing_items(drawing['objects'])
        if errors: raise RuntimeError('Failed drawings: '+', '.join(errors))
    finally:
        if model_cache is not None: model_cache.Dispose()
        doc.Dispose()


if __name__=='__main__':
    try: main()
    except Exception:
        System.Console.WriteLine(traceback.format_exc())
        raise
