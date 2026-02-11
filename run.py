"""실행용 진입점 파일.

사용자는 이 파일만 실행하면 됩니다:
    python run.py
"""

from wsgiref.simple_server import make_server

from app import application


if __name__ == '__main__':
    with make_server('0.0.0.0', 8000, application) as httpd:
        print('실행 파일: run.py')
        print('접속 주소: http://localhost:8000')
        httpd.serve_forever()
