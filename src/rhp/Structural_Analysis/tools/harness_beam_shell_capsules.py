"""Surgery for beam + shell capsules (run in scratchpad dir)."""
import xml.etree.ElementTree as ET
import uuid

if __package__:
    from .capsule_xml import make_param, rewire_input
else:
    from capsule_xml import make_param, rewire_input

PARAM_CURVE = "d5967b9f-e8ee-436b-a8ad-29fdcecf32d5"
PARAM_NUMBER = "3e8ca6be-fda8-4aaf-b5c0-3c54c8bb7312"
PARAM_POINT = "fbac3e32-f100-4292-8692-77240a42fd1a"
PARAM_MESH = "1e936df3-0eea-4246-8549-514cb8862b7a"


def get_containers(root):
    out = {}
    for obj in root.iter('chunk'):
        if obj.get('name') != 'Object':
            continue
        tname = next((it.text for it in obj.find('items').iter('item') if it.get('name') == 'Name'), '?')
        cont = next((c for c in obj.find('chunks').findall('chunk') if c.get('name') == 'Container'), None)
        if cont is None:
            continue
        inst = next((it.text for it in cont.find('items').iter('item') if it.get('name') == 'InstanceGuid'), None)
        nick = next((it.text for it in cont.find('items').iter('item') if it.get('name') == 'NickName'), None)
        out[inst] = (tname, nick, cont)
    return out


def output_inst(cont, needle):
    for pc in cont.iter('chunk'):
        if pc.get('name') not in ('param_output', 'p'):
            continue
        pits = pc.find('items')
        if pits is None:
            continue
        nm = next((it.text for it in pits.iter('item') if it.get('name') == 'Name'), '')
        if nm and needle in nm:
            return next((it.text for it in pits.iter('item') if it.get('name') == 'InstanceGuid'), None)
    return None


def add_params(root, specs):
    defobjs = next(c for c in root.iter('chunk') if c.get('name') == 'DefinitionObjects')
    oc = next(it for it in defobjs.find('items').iter('item') if it.get('name') == 'ObjectCount')
    count = int(oc.text)
    holder = defobjs.find('chunks')
    for i, (tg, tn, inst, nick, desc, src) in enumerate(specs):
        holder.append(make_param(count + i, tg, tn, inst, nick, desc, src, 60, 40 + i * 70))
    holder.set('count', str(count + len(specs)))
    oc.text = str(count + len(specs))


# ------ BEAM ------
t = ET.parse('01_SimpleBeam.xml')
root = t.getroot()
C = get_containers(root)
lineelem = next(v for v in C.values() if 'Create Linear Element' in v[0])
loads = next(v for v in C.values() if v[0].strip() == 'Loads (Karamba3D)')
supp = next(v for v in C.values() if v[0].strip() == 'Support (Karamba3D)')
unitz = next(v for v in C.values() if v[0] == 'Unit Z')
analyse = next(v for v in C.values() if 'Analyse' in v[0])
assemble = next(v for v in C.values() if 'Assemble Model' in v[0])
G_LINES, G_LOAD, G_SUP, G_DISP, G_MASS = (str(uuid.uuid4()) for _ in range(5))
disp_out = output_inst(analyse[2], 'Maximum Displacement')
mass_out = output_inst(assemble[2], 'Mass')
lineelem_pts = output_inst(lineelem[2], 'Points')
assert disp_out and mass_out and lineelem_pts, (disp_out, mass_out, lineelem_pts)
add_params(root, [
    (PARAM_CURVE, 'Curve', G_LINES, 'ALMOND_IN_LINES',
     'Almond harness: beam axis curves in metres.', None),
    (PARAM_NUMBER, 'Number', G_LOAD, 'ALMOND_IN_LOAD_KN',
     'Almond harness: vertical point load in kN at every node (Unit-Z factor).', None),
    (PARAM_POINT, 'Point', G_SUP, 'ALMOND_IN_SUPPORTS',
     'Almond harness: support positions in metres; validator supplies lowest-Z nodes when empty.', None),
    (PARAM_NUMBER, 'Number', G_DISP, 'ALMOND_OUT_DISP_MM',
     'Almond harness: max displacement from Analyse (cm).', disp_out),
    (PARAM_NUMBER, 'Number', G_MASS, 'ALMOND_OUT_MASS_KG',
     'Almond harness: structural mass [kg].', mass_out),
])
n1 = rewire_input(lineelem[2], 'Line', G_LINES)
n2 = rewire_input(unitz[2], 'Factor', G_LOAD)
n3 = rewire_input(supp[2], 'Pos|Ind', G_SUP)
n4 = rewire_input(loads[2], 'Pos|Ind', lineelem_pts)
print("BEAM rewires: line=%d loadfactor=%d supp=%d loadpts=%d" % (n1, n2, n3, n4))
assert (n1, n2, n3, n4) == (1, 1, 1, 1)
t.write('01_SimpleBeam_harnessed.xml', encoding='utf-8', xml_declaration=True)

# ------ SHELL ------
t = ET.parse('01_InputSurfacesAsShell.xml')
root = t.getroot()
C = get_containers(root)
surfelem = next(v for v in C.values() if 'Create Surface Element' in v[0])
analyse = next(v for v in C.values() if 'Analyse (Karamba3D)' in v[0])
assemble = next(v for v in C.values() if 'Assemble Model' in v[0])
supps = [v for v in C.values() if v[0].strip() == 'Support (Karamba3D)']
slider_full = next(k for k, v in C.items()
                   if v[0] == 'Number Slider' and v[1] == 'live load')
G_MESH, G_LOAD, G_SUP, G_DISP, G_MASS = (str(uuid.uuid4()) for _ in range(5))
disp_out = output_inst(analyse[2], 'Maximum Displacement')
mass_out = output_inst(assemble[2], 'Mass')
assert disp_out and mass_out, (disp_out, mass_out)
add_params(root, [
    (PARAM_MESH, 'Mesh', G_MESH, 'ALMOND_IN_MESH',
     'Almond harness: shell mesh in metres (breps are meshed by the runner).', None),
    (PARAM_NUMBER, 'Number', G_LOAD, 'ALMOND_IN_LOAD_KNM2',
     'Almond harness: area load factor, drives the Unit-Z load vector.', None),
    (PARAM_POINT, 'Point', G_SUP, 'ALMOND_IN_SUPPORTS',
     'Almond harness: support positions in metres; validator supplies lowest-Z nodes when empty.', None),
    (PARAM_NUMBER, 'Number', G_DISP, 'ALMOND_OUT_DISP_MM',
     'Almond harness: max displacement from Analyse (cm).', disp_out),
    (PARAM_NUMBER, 'Number', G_MASS, 'ALMOND_OUT_MASS_KG',
     'Almond harness: structural mass [kg].', mass_out),
])
n1 = rewire_input(surfelem[2], 'Mesh', G_MESH)
n2 = 0
for it in root.iter('item'):
    if it.get('name') == 'Source' and it.text == slider_full:
        it.text = G_LOAD
        n2 += 1
n3 = sum(rewire_input(s[2], 'Pos|Ind', G_SUP) for s in supps)
print("SHELL rewires: mesh=%d loadfactor=%d supp=%d (comps=%d)" % (n1, n2, n3, len(supps)))
assert n1 == 1 and n2 >= 1 and n3 >= len(supps)
t.write('01_InputSurfacesAsShell_harnessed.xml', encoding='utf-8', xml_declaration=True)
print("both saved")
