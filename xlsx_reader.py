from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET


def parse_uploaded_file(filename: str, content: bytes) -> list[dict[str, str]]:
    lower = filename.lower()
    if lower.endswith('.csv'):
        return parse_csv(content)
    if lower.endswith('.xlsx'):
        return parse_xlsx(content)
    raise ValueError('지원하지 않는 파일 형식입니다. xlsx 또는 csv 파일을 업로드하세요.')


def parse_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    return [{k.strip(): (v or '').strip() for k, v in row.items()} for row in reader]


def _col_index(cell_ref: str) -> int:
    col_letters = re.sub(r'\d', '', cell_ref)
    col = 0
    for c in col_letters:
        col = col * 26 + (ord(c.upper()) - ord('A') + 1)
    return col - 1


def parse_xlsx(content: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        shared_strings = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
            ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in root.findall('a:si', ns):
                texts = [t.text or '' for t in si.findall('.//a:t', ns)]
                shared_strings.append(''.join(texts))

        sheet_path = 'xl/worksheets/sheet1.xml'
        if sheet_path not in zf.namelist():
            raise ValueError('첫 번째 시트를 찾을 수 없습니다.')

        sheet_root = ET.fromstring(zf.read(sheet_path))
        ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

        rows = []
        for row in sheet_root.findall('.//a:sheetData/a:row', ns):
            values: dict[int, str] = {}
            for cell in row.findall('a:c', ns):
                ref = cell.attrib.get('r', '')
                idx = _col_index(ref) if ref else 0
                ctype = cell.attrib.get('t')
                v = cell.find('a:v', ns)
                if v is None or v.text is None:
                    value = ''
                elif ctype == 's':
                    sidx = int(v.text)
                    value = shared_strings[sidx] if sidx < len(shared_strings) else ''
                else:
                    value = v.text
                values[idx] = value.strip() if isinstance(value, str) else str(value)
            if values:
                max_idx = max(values.keys())
                rows.append([values.get(i, '') for i in range(max_idx + 1)])

    if not rows:
        return []

    headers = [h.strip() for h in rows[0]]
    data = []
    for row in rows[1:]:
        row_dict = {}
        for i, head in enumerate(headers):
            if not head:
                continue
            row_dict[head] = row[i].strip() if i < len(row) else ''
        if any(row_dict.values()):
            data.append(row_dict)
    return data
