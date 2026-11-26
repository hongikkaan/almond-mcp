"""Shared XML edits for the capsule harness scripts."""
import xml.etree.ElementTree as ET


def make_param(idx, type_guid, type_name, inst, nick, desc, source, x, y):
    """Build a Grasshopper parameter with an optional source connection."""
    obj = ET.Element('chunk', {'name': 'Object', 'index': str(idx)})
    items = ET.SubElement(obj, 'items', {'count': '2'})

    def item(parent, name, text, tn='gh_string', tc='10', extra=None):
        a = {'name': name, 'type_name': tn, 'type_code': tc}
        if extra:
            a.update(extra)
        e = ET.SubElement(parent, 'item', a)
        e.text = text
        return e

    item(items, 'GUID', type_guid, 'gh_guid', '9')
    item(items, 'Name', type_name)
    chunks = ET.SubElement(obj, 'chunks', {'count': '1'})
    cont = ET.SubElement(chunks, 'chunk', {'name': 'Container'})
    ci = ET.SubElement(cont, 'items', {'count': str(7 + (1 if source else 0))})
    item(ci, 'Description', desc)
    item(ci, 'InstanceGuid', inst, 'gh_guid', '9')
    item(ci, 'Mapping', '1', 'gh_int32', '3')
    item(ci, 'Name', type_name)
    item(ci, 'NickName', nick)
    item(ci, 'Optional', 'true', 'gh_bool', '1')
    if source:
        item(ci, 'Source', source, 'gh_guid', '9', {'index': '0'})
    item(ci, 'SourceCount', '1' if source else '0', 'gh_int32', '3')
    cch = ET.SubElement(cont, 'chunks', {'count': '1'})
    att = ET.SubElement(cch, 'chunk', {'name': 'Attributes'})
    ai = ET.SubElement(att, 'items', {'count': '2'})
    b = ET.SubElement(ai, 'item', {'name': 'Bounds', 'type_name': 'gh_drawing_rectanglef', 'type_code': '35'})
    for tag, val in (('X', str(x)), ('Y', str(y)), ('W', '160'), ('H', '24')):
        ET.SubElement(b, tag).text = val
    p = ET.SubElement(ai, 'item', {'name': 'Pivot', 'type_name': 'gh_drawing_pointf', 'type_code': '31'})
    for tag, val in (('X', str(x + 80)), ('Y', str(y + 12))):
        ET.SubElement(p, tag).text = val
    return obj


def rewire_input(cont, in_name, new_src):
    """Replace the sources on each connected input with the given name."""
    n = 0
    for pc in cont.iter('chunk'):
        if pc.get('name') not in ('param_input', 'p'):
            continue
        pits = pc.find('items')
        if pits is None:
            continue
        nm = next((it.text for it in pits.iter('item') if it.get('name') == 'Name'), None)
        if nm != in_name:
            continue
        srcs = [it for it in pits.findall('item') if it.get('name') == 'Source']
        if not srcs:
            continue
        for i, it in enumerate(srcs):
            if i == 0:
                it.text = new_src
                it.set('index', '0')
            else:
                pits.remove(it)
        sc = next((it for it in pits.iter('item') if it.get('name') == 'SourceCount'), None)
        if sc is not None:
            sc.text = '1'
        pits.set('count', str(len(pits.findall('item'))))
        n += 1
    return n
