"""Populate the pre-authored Excel template without third-party dependencies.

Layout, styles, formula definitions, conditional formatting and freeze panes
are authored in template.xlsx by the Artifact Tool builder. This program only
fills its designated data cells and formula caches from history.json.
"""
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ET.register_namespace('', NS)
TAG = lambda name: '{' + NS + '}' + name
CAPACITY = 2600
START = 7

def serial(value):
    return (date.fromisoformat(value) - date(1899, 12, 30)).days if value else None

def colname(index):
    result = ''
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result

def value_cell(cell, value):
    for child in list(cell):
        cell.remove(child)
    cell.attrib.pop('t', None)
    if value is None:
        return
    if isinstance(value, (int, float)):
        ET.SubElement(cell, TAG('v')).text = str(value)
    else:
        cell.set('t', 'inlineStr')
        ET.SubElement(ET.SubElement(cell, TAG('is')), TAG('t')).text = str(value)

def cache(cell, value):
    # The existing formula is retained exactly as authored.
    for node in list(cell):
        if node.tag in (TAG('v'), TAG('is')):
            cell.remove(node)
    if value is None:
        cell.set('t', 'str')
        ET.SubElement(cell, TAG('v')).text = ''
    else:
        cell.attrib.pop('t', None)
        ET.SubElement(cell, TAG('v')).text = str(value)

def sheet_data(root, records, market):
    cells = {c.attrib['r']: c for c in root.iter(TAG('c'))}
    rows = {int(r.attrib['r']): r for r in root.iter(TAG('row'))}
    if len(records) > CAPACITY:
        raise ValueError('Workbook capacity exceeded. Increase the template capacity before updating.')
    for offset, (session, item) in enumerate(sorted(records.items())):
        r = START + offset
        if market == 'india':
            values = [serial(session), item.get('nifty'), item.get('nifty_points'), item.get('nifty_pct'),
                      item.get('vix'), item.get('vix_points'), item.get('vix_pct'), serial(item.get('expiry')),
                      item.get('near_put'), item.get('near_call'), None, item.get('all_put'), item.get('all_call'),
                      None, item.get('status'), item.get('updated_at'), item.get('indices_source'),
                      item.get('options_source'), item.get('detail')]
            ratios = {11: ('near_put', 'near_call'), 14: ('all_put', 'all_call')}
            calculated = {}
            for column, (num, den) in ratios.items():
                calculated[column] = item[num] / item[den] if item.get(num) is not None and item.get(den, 0) > 0 else None
        else:
            values = [serial(session), item.get('nasdaq'), item.get('nasdaq_previous'), None, None,
                      item.get('dow'), item.get('dow_previous'), None, None, item.get('status'),
                      item.get('updated_at'), item.get('nasdaq_source'), item.get('dow_source'), item.get('detail')]
            calculated = {}
            for name, points, pct in [('nasdaq', 4, 5), ('dow', 8, 9)]:
                current, previous = item.get(name), item.get(name + '_previous')
                valid = current is not None and previous is not None and previous > 0
                calculated[points] = current - previous if valid else None
                calculated[pct] = current / previous - 1 if valid else None
        for column, value in enumerate(values, 1):
            address = colname(column) + str(r)
            if address not in cells:
                cell = ET.SubElement(rows[r], TAG('c'), {'r': address})
                cells[address] = cell
            if column in calculated:
                if cells[address].find(TAG('f')) is None:
                    raise ValueError('Missing template formula at ' + address)
                cache(cells[address], calculated[column])
            else:
                value_cell(cells[address], value)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)

def build(history, template=ROOT/'template.xlsx', output=ROOT/'Market_Close_Tracker.xlsx'):
    with ZipFile(template) as archive:
        content = {entry.filename: archive.read(entry) for entry in archive.infolist()}
    for number, market in [(1, 'india'), (2, 'us')]:
        path = f'xl/worksheets/sheet{number}.xml'
        root = ET.fromstring(content[path])
        content[path] = sheet_data(root, history[market], market)
    temp = output.with_suffix('.tmp.xlsx')
    with ZipFile(temp, 'w', ZIP_DEFLATED) as archive:
        for path, data in content.items():
            archive.writestr(path, data)
    temp.replace(output)
    return output

if __name__ == '__main__':
    history = json.loads((ROOT/'history.json').read_text())
    print(build(history))
