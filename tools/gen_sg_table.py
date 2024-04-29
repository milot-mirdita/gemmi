#!/usr/bin/env cctbx.python
#
# symmetry.hpp can be checked with:
# python3 tools/gen_sg_table.py $CCP4/lib/data/syminfo.lib > gen.txt
# sed -n '/gen_sg_table/,/^}/p' include/gemmi/symmetry.hpp > cur.txt
# diff cur.txt gen.txt

import shlex
import sys

from cctbx import sgtbx
try:
    import gemmi
except ImportError:
    gemmi = None

syminfo_path = sys.argv[1]

def parse_syminfo(path):
    data = []
    cur = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line[0] == '#':
                continue
            if line == 'begin_spacegroup':
                assert cur is None, line
                cur = {'symops': [], 'cenops': []}
                continue
            assert cur is not None, line
            if line == 'end_spacegroup':
                for must_have in ['basisop', 'ccp4', 'number', 'hall', 'xhm']:
                    assert must_have in cur, must_have
                for must_have_list in ['symops', 'cenops']:
                    assert len(cur[must_have_list]) > 0
                verify_hall_symbol(cur)
                data.append(cur)
                cur = None
            elif line.startswith('number '):
                cur['number'] = int(line[6:])
            elif line.startswith('basisop '):
                cur['basisop'] = line[8:]
            elif line.startswith('symbol ccp4 '):
                cur['ccp4'] = int(line[12:])
                assert cur['ccp4'] == 0 or cur['ccp4'] % 1000 == cur['number']
            elif line.startswith('symbol Hall '):
                cur['hall'] = line[12:].strip(" '")
            elif line.startswith('symbol xHM '):
                cur['xhm'] = line[11:].strip(" '").replace(' :', ':')
            elif line.startswith('symbol old '):
                cur['old'] = shlex.split(line[11:])
            elif line.startswith('symop '):
                cur['symops'].append(line[6:])
            elif line.startswith('cenop '):
                cur['cenops'].append(line[6:])
    return data

def verify_hall_symbol(entry):
    if not gemmi:
        return
    hall_ops = gemmi.symops_from_hall(entry['hall'])
    assert len(hall_ops.sym_ops) == len(entry['symops'])
    assert len(hall_ops.cen_ops) == len(entry['cenops'])
    # centering vectors are exactly the same
    assert (set(gemmi.Op().translated(tr) for tr in hall_ops.cen_ops)
            == set(gemmi.Op(e) for e in entry['cenops'])), entry
    # symops differ in some cases but are the same modulo centering vectors
    given = set(gemmi.Op(s) * c for s in entry['symops']
                for c in entry['cenops'])
    assert given == set(hall_ops), entry

basisops = []

def get_basisop(sgtbx_info):
    to_ref = sgtbx_info.change_of_basis_op_to_reference_setting()
    from_ref = to_ref.inverse()
    b_str = str(from_ref.c())
    try:
        b_idx = basisops.index(b_str)
    except ValueError:
        b_idx = len(basisops)
        basisops.append(b_str)
    #print('FR %s' % from_ref.c())
    #print('TR %s' % to_ref.c())
    return b_str, b_idx

shorter_halls = {
    'C 2y (x+1/4,y+1/4,-x+z-1/4)': 'I 2yb',
    'C 2y (x+1/4,y+1/4,z)': 'C 2yb',
    'P 2 2ab (x+1/4,y+1/4,z)': 'P 2ab 2a',
    'C 2c 2 (x+1/4,y,z)': 'C 2ac 2',
    'C 2 2 (x+1/4,y+1/4,z)': 'C 2ab 2b',
    'F 2 2 (x,y,z+1/4)': 'F 2 2c',
    'I 2 2 (x-1/4,y+1/4,z-1/4)': 'I 2ab 2bc',
    'P 4n 2n (x-1/4,y-1/4,z-1/4)': 'P 4bc 2a',
    'I 2 2 3 (x+1/4,y+1/4,z+1/4)': 'I 2ab 2bc 3',
}

syminfo_data = parse_syminfo(syminfo_path)
syminfo_dict = {}
for info in syminfo_data:
    # handle duplicates in syminfo.lib: pick the the one with ccp4 number
    if info['xhm'] not in syminfo_dict or info['ccp4'] != 0:
        syminfo_dict[info['xhm']] = info


print('''\
  // This table was generated by tools/gen_sg_table.py.
  // First 530 entries in the same order as in SgInfo, sgtbx and ITB.
  // Note: spacegroup 68 has three duplicates with different H-M names.''')

hall_to_idx = {}
counter = 0
def check_dup(hall):
    n = hall_to_idx.setdefault(hall, counter)
    return '' if n == counter else f'(=={n})'
fmt = '  {%3d, %4d, %-12s, %s, %6s, %-16s, %-2d}, // %3d%s'
def quot(s):
    return '"%s"' % s.replace('"', r'\"')
for s in sgtbx.space_group_symbol_iterator():
    xhm = s.hermann_mauguin()
    ext = '  0'
    if s.extension() != '\0':
        xhm += ':%s' % s.extension()
        ext = "'%c'" % s.extension()
    info = syminfo_dict.pop(xhm)
    assert info['number'] == s.number()
    cctbx_sg = sgtbx.space_group(s.hall())
    cctbx_info = sgtbx.space_group_info(group=cctbx_sg)
    from_ref, basisop_idx = get_basisop(cctbx_info)
    assert from_ref == info['basisop'], (from_ref, info['basisop'])
    if gemmi:
        assert (set(gemmi.symops_from_hall(s.hall()))
                == set(gemmi.symops_from_hall(info['hall']))), xhm
    hall = s.hall().strip()
    print(fmt % (s.number(), info['ccp4'], quot(s.hermann_mauguin()),
                 ext, quot(s.qualifier()), quot(hall),
                 basisop_idx, counter, check_dup(hall)))
    counter += 1
print('  // And extra entries from syminfo.lib')
for info in syminfo_data:
    if info['xhm'] in syminfo_dict:  # i.e. it was not printed yet
        hm = info['xhm']
        if not hm:
            hm = info['old'][0]
            if hm == 'P 21 21 2 (a)':  # slightly too long
                hm = 'P 21212(a)'
        ext = '  0'
        if ':' in hm:
            hm, ext = hm.split(':')
            hm = hm.strip()
            ext = "'%c'" % ext
        hall = shorter_halls[info['hall']]
        if gemmi:
            assert (set(gemmi.symops_from_hall(hall))
                    == set(gemmi.symops_from_hall(info['hall']))), hm
        cctbx_sg = sgtbx.space_group(hall)
        cctbx_info = sgtbx.space_group_info(group=cctbx_sg)
        from_ref, basisop_idx = get_basisop(cctbx_info)
        print(fmt % (info['number'], info['ccp4'], quot(hm), ext, '""',
                     quot(hall), basisop_idx, counter, check_dup(hall)))
        counter += 1
print('  // And ...')
additional = [
    'triclinic - enlarged unit cells',
    ('A 1', 'A 1'),
    ('B 1', 'B 1'),
    ('C 1', 'C 1'),
    ('F 1', 'F 1'),
    ('I 1', 'I 1'),
    ('A -1', '-A 1'),
    ('B -1', '-B 1'),
    ('C -1', '-C 1'),
    ('F -1', '-F 1'),
    ('I -1', '-I 1'),
    'monoclinic',
    ('B 1 2 1', 'B 2y'),  # 3
    ('C 1 1 2', 'C 2'),  # 3
    ('B 1 21 1', 'B 2yb'), # 4
    ('C 1 1 21', 'C 2c'), # 4
    ('F 1 2/m 1', '-F 2y'), # 12
    'orthorhombic',
    ('A b a m', '-A 2 2ab'),
    'tetragonal - enlarged C- and F-centred unit cells',
    ('C 4 2 2', 'C 4 2'),
    ('C 4 2 21', 'C 4a 2'),
    ('F 4 2 2', 'F 4 2'),
    ('C -4 2 m', 'C -4 2'),
    ('C -4 2 b', 'C -4 2ya'),
    ('F 4/m m m', '-F 4 2'),
]
system = None
for item in additional:
    if type(item) == str:
        print('  // ' + item)
        system = item.split()[0]
        continue
    hm, hall = item
    cctbx_sg = sgtbx.space_group(hall)
    cctbx_info = sgtbx.space_group_info(group=cctbx_sg)
    from_ref, basisop_idx = get_basisop(cctbx_info)
    number = cctbx_info.type().number()
    print(fmt % (number, 0, quot(hm), '  0', '""', quot(hall),
                 basisop_idx, counter, check_dup(hall)))
    if gemmi:
        assert gemmi.SpaceGroup(number).crystal_system_str() == system
    counter += 1

print('\n')
for n, b in enumerate(basisops):
    nice_b = gemmi.Op(b).triplet()
    print('    "%s",  // %d' % (nice_b, n))
