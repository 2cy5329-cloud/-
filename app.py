from __future__ import annotations

import cgi
import html

from processor import summarize
from xlsx_reader import parse_uploaded_file


def render_table(rows: list[dict], title: str) -> str:
    if not rows:
        return f"<h3>{html.escape(title)}</h3><p>데이터 없음</p>"
    headers = list(rows[0].keys())
    head_html = ''.join(f'<th>{html.escape(str(h))}</th>' for h in headers)
    body = []
    for row in rows:
        tds = ''.join(f'<td>{html.escape(str(row.get(h, "")))}</td>' for h in headers)
        body.append(f'<tr>{tds}</tr>')
    return f"<h3>{html.escape(title)}</h3><table><thead><tr>{head_html}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def application(environ, start_response):
    if environ['REQUEST_METHOD'] == 'POST':
        form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ, keep_blank_values=True)
        try:
            target_region = form.getfirst('target_region', '익산').strip() or '익산'
            reference_year = int(form.getfirst('reference_year', '2025'))
            upload = form['source_file']
            if not getattr(upload, 'filename', None):
                raise ValueError('파일을 업로드해주세요.')

            file_content = upload.file.read()
            rows = parse_uploaded_file(upload.filename, file_content)
            result = summarize(rows, target_region=target_region, reference_year=reference_year)

            summary = [
                {"지표": "전체건수", "값": result.total_rows},
                {"지표": f"{target_region} 전입", "값": result.inbound},
                {"지표": f"{target_region} 전출", "값": result.outbound},
                {"지표": "순증감", "값": result.net},
            ]

            content = f"""
            <html><head><meta charset='utf-8'><title>집계 결과</title>
            <style>
              body {{ font-family: sans-serif; margin: 24px; }}
              table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
              th, td {{ border: 1px solid #ddd; padding: 8px; }}
              th {{ background: #f4f4f4; }}
              .btn {{ display:inline-block; padding:10px 12px; background:#1f6feb; color:#fff; text-decoration:none; border-radius:6px; }}
            </style></head>
            <body>
            <h1>전입/전출 자동 집계 결과</h1>
            <p><a class='btn' href='/'>다른 파일 다시 업로드</a></p>
            {render_table(summary, '요약')}
            {render_table(result.flow_table, '이전지역 → 새지역 흐름')}
            {render_table(result.age_table, '연령대별 전입/전출')}
            </body></html>
            """
            start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
            return [content.encode('utf-8')]
        except Exception as exc:
            msg = html.escape(str(exc))
            content = f"<html><head><meta charset='utf-8'></head><body><h2>오류</h2><p>{msg}</p><p><a href='/'>뒤로가기</a></p></body></html>"
            start_response('400 Bad Request', [('Content-Type', 'text/html; charset=utf-8')])
            return [content.encode('utf-8')]

    content = """
    <html><head><meta charset='utf-8'><title>전입/전출 자동 집계</title>
    <style>
      body { font-family: sans-serif; margin: 24px; max-width: 860px; }
      label { display:block; margin-top: 12px; }
      input[type='text'], input[type='number'] { width: 280px; padding:8px; }
      .card { border:1px solid #ddd; border-radius: 8px; padding: 16px; margin-top: 16px; }
      .btn { margin-top:16px; padding:10px 14px; background:#1f6feb; border:none; color:white; border-radius:6px; }
      ul { margin-top: 6px; }
    </style></head>
    <body>
      <h1>엑셀 업로드 자동 집계</h1>
      <p>엑셀/CSV를 업로드하면 전입·전출과 이동 흐름을 자동 계산합니다.</p>
      <div class='card'>
        <strong>필수 컬럼</strong>
        <ul>
          <li>이름</li><li>생년월일</li><li>이전주소</li><li>새주소</li><li>이동구분(전입/전출)</li>
        </ul>
      </div>
      <form method='post' enctype='multipart/form-data'>
        <label>기준 지역 <input type='text' name='target_region' value='익산' /></label>
        <label>연령 계산 기준 연도 <input type='number' name='reference_year' value='2025' /></label>
        <label>원본 파일 업로드 (.xlsx, .csv) <input type='file' name='source_file' accept='.xlsx,.csv' /></label>
        <button class='btn' type='submit'>자동 집계 실행</button>
      </form>
    </body></html>
    """
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    return [content.encode('utf-8')]

