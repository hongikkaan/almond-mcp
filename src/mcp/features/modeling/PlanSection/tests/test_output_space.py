"""Offline drawing-output transaction and view-state contracts; no Rhino document."""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from test_logic import ps


class Attributes:
    def __init__(self):
        self.Space, self.ViewportId = 'page', 'source-page'
        self.values = {'ps:source_layer':'Model', 'ps:placement':'height-100'}
        self.PlotColor, self.PlotWeight = 'manual-color', 0.2
    def Duplicate(self): return deepcopy(self)
    def GetUserString(self, key): return self.values.get(key)
    def SetUserString(self, key, value): self.values[key] = value
    def DeleteAllUserStrings(self): self.values.clear()
    def GetCustomSectionStyle(self): return None


class Page:
    def __init__(self, detail):
        self.ActiveDetailId = detail
        self.SetPageAsActive = Mock(side_effect=self.activate_page)
        self.SetActiveDetail = Mock(side_effect=self.activate_detail)
    def activate_page(self): self.ActiveDetailId = 'empty'
    def activate_detail(self, detail):
        self.ActiveDetailId = detail
        return True


class Views:
    def __init__(self, original, model):
        self.original, self.model, self._active = original, model, original
        self.GetViewList = Mock(return_value=[model])
    @property
    def ActiveView(self): return self._active
    @ActiveView.setter
    def ActiveView(self, value):
        self._active = value
        if isinstance(value, Page): value.ActiveDetailId = 'empty'


class Document:
    @property
    def ActiveSpace(self):
        return 'model' if self.Views.ActiveView is self.Views.model and not self.force_page else 'page'


class ModelSpaceOutput(unittest.TestCase):
    def scenario(self, initial='page', failure=None, no_model=False, local=False):
        model = object()
        original = model if initial == 'model' else Page('detail-1' if initial == 'detail' else 'empty')
        doc = Document()
        doc.force_page = failure == 'activate'
        doc.Views = Views(original, model)
        if failure == 'restore': original.SetActiveDetail.side_effect = lambda detail:False
        if no_model: doc.Views.GetViewList.return_value = []
        source = Attributes()
        old = NS(Id='old', RuntimeSerialNumber=17, Attributes=Attributes())
        old2 = NS(Id='old2', RuntimeSerialNumber=18, Attributes=Attributes())
        stored = {'old':old}
        if failure == 'late-delete': stored['old2'] = old2
        observed = []
        def add(geometry, attrs):
            observed.append((doc.ActiveSpace, attrs.Space, attrs.ViewportId))
            if failure == 'add': raise ValueError('native add failure')
            attrs = attrs.Duplicate()
            if failure == 'space': attrs.Space = 'page'
            if failure == 'viewport': attrs.ViewportId = 'wrong-page'
            stored['new'] = NS(Id='new', Attributes=attrs)
            return 'new'
        def delete(obj, *args):
            key = obj.Id if hasattr(obj, 'Id') else obj
            if failure == 'late-delete' and key == 'old2':
                return False
            stored.pop(key, None)
            return True
        def undelete(serial):
            if serial == old.RuntimeSerialNumber:
                stored['old'] = old
                return True
            return False
        def lookup(guid):
            if failure == 'lookup' and guid == 'new': return None
            return stored.get(guid)
        doc.Objects = NS(Add=Mock(side_effect=add), FindId=Mock(side_effect=lookup),
                         Delete=Mock(side_effect=delete), Undelete=Mock(side_effect=undelete),
                         ModifyAttributes=Mock())
        cp = NS(Id='clip', IsReference=not local, Attributes=Attributes())
        drawing = dict(objects=[dict(geometry=object(),attributes=source,role='section')])
        objects = NS(ActiveSpace=NS(ModelSpace='model'),
                     ObjectPlotColorSource=NS(PlotColorFromLayer='by-layer'),
                     ObjectPlotWeightSource=NS(PlotWeightFromLayer='by-layer'))
        error = None
        with patch.object(ps,'D',objects), patch.object(ps,'R',NS(Display=NS(RhinoPageView=Page))), \
             patch.object(ps,'System',NS(Guid=NS(Empty='empty'))), \
             patch.object(ps,'drawing_objects',return_value=[old,old2] if failure == 'late-delete' else [old]), \
             patch.object(ps,'local_output_layer',return_value=2) as layer, \
             patch.object(ps,'write_saved_plane',side_effect=ValueError('typed write failed')) if failure == 'write' else patch.object(ps,'write_saved_plane',ps.write_saved_plane), \
             patch.object(ps,'save_drawing_registry',return_value='old-registry') as registry:
            try: result = ps.bake(doc,cp,drawing,target='target' if local else None)
            except ValueError as exc: error = exc; result = None
        return NS(doc=doc,original=original,source=source,stored=stored,observed=observed,
                  layer=layer,registry=registry,result=result,error=error)

    def assert_restored(self, run, initial):
        self.assertIs(run.doc.Views.ActiveView,run.original)
        if initial == 'page': self.assertEqual(run.original.ActiveDetailId,'empty')
        if initial == 'detail': self.assertEqual(run.original.ActiveDetailId,'detail-1')

    def test_bake_uses_model_space_and_restores_page_detail_or_model(self):
        for initial in ('page','detail','model'):
            with self.subTest(initial=initial):
                run = self.scenario(initial)
                self.assertIsNone(run.error)
                self.assertEqual(run.result,['new'])
                self.assertEqual(run.observed,[('model','model','empty')])
                self.assertEqual(set(run.stored),{'new'})
                self.assertEqual(run.source.Space,'page')
                self.assertEqual(run.source.ViewportId,'source-page')
                self.assertEqual(run.stored['new'].Attributes.PlotColor,'manual-color')
                self.assert_restored(run,initial)

    def test_native_failure_or_wrong_saved_space_retains_old_drawing_and_registry(self):
        for initial in ('page','detail','model'):
            for failure in ('add','space','viewport','lookup'):
                with self.subTest(initial=initial,failure=failure):
                    run = self.scenario(initial,failure)
                    self.assertIsInstance(run.error,ValueError)
                    self.assertEqual(set(run.stored),{'old'})
                    run.registry.assert_not_called()
                    run.doc.Objects.Undelete.assert_not_called()
                    if failure == 'add': run.doc.Objects.Delete.assert_not_called()
                    else:
                        deleted = run.doc.Objects.Delete.call_args.args[0]
                        self.assertEqual(deleted if isinstance(deleted,str) else deleted.Id,'new')
                    self.assert_restored(run,initial)

    def test_activation_failure_preserves_drawing_and_restores_view(self):
        run = self.scenario('detail','activate')
        self.assertRegex(str(run.error),'Cannot activate model space')
        self.assertEqual(set(run.stored),{'old'})
        run.doc.Objects.Add.assert_not_called()
        run.doc.Objects.Delete.assert_not_called()
        run.registry.assert_not_called()
        self.assert_restored(run,'detail')

    def test_detail_restore_failure_rolls_back_before_old_drawing_is_removed(self):
        run = self.scenario('detail','restore')
        self.assertRegex(str(run.error),'Cannot restore')
        self.assertEqual(set(run.stored),{'old'})
        run.registry.assert_not_called()
        self.assertEqual(run.doc.Objects.Delete.call_args.args[0].Id,'new')
        self.assertIs(run.doc.Views.ActiveView,run.original)

    def test_no_model_view_fails_before_layer_or_object_changes(self):
        run = self.scenario(no_model=True)
        self.assertRegex(str(run.error),'existing model viewport')
        self.assertEqual(set(run.stored),{'old'})
        run.layer.assert_not_called()
        run.doc.Objects.Add.assert_not_called()
        run.doc.Objects.Delete.assert_not_called()
        run.registry.assert_not_called()
        self.assertIs(run.doc.Views.ActiveView,run.original)

    def test_clipping_typed_write_failure_rolls_back_added_output(self):
        run = self.scenario('detail','write',local=True)
        self.assertRegex(str(run.error),'typed write failed')
        self.assertEqual(set(run.stored),{'old'})
        run.registry.assert_not_called()
        self.assert_restored(run,'detail')

    def test_late_old_delete_failure_restores_old_ids_registry_and_removes_new_output(self):
        run = self.scenario('detail','late-delete')
        self.assertRegex(str(run.error),'Cannot remove previous drawing object old2')
        self.assertEqual(set(run.stored),{'old','old2'})
        self.assertEqual((run.stored['old'].RuntimeSerialNumber,
                          run.stored['old2'].RuntimeSerialNumber),(17,18))
        self.assertEqual(run.doc.Objects.Undelete.call_args_list[0].args,(17,))
        deleted = [call.args[0].Id for call in run.doc.Objects.Delete.call_args_list]
        self.assertEqual(deleted,['old','old2','new'])
        updates = [call.args[2] for call in run.registry.call_args_list]
        self.assertEqual(len(updates),2)
        self.assertEqual(updates[0],'["new"]')
        self.assertEqual(updates[1],'old-registry')
        self.assert_restored(run,'detail')


if __name__ == '__main__': unittest.main()
