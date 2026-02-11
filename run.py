"""실행용 진입점 파일.

사용자는 이 파일만 실행하면 됩니다:
    python run.py
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser
from wsgiref.simple_server import make_server

from app import application


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="전입/전출 자동 집계 웹앱 실행")
    parser.add_argument("--host", default="127.0.0.1", help="바인딩 호스트 (기본값: 127.0.0.1)")
    parser.add_argument("--port", default=8000, type=int, help="바인딩 포트 (기본값: 8000)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="실행 시 브라우저 자동 열기를 비활성화",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = f"http://{args.host}:{args.port}"

    print("[시작] 전입/전출 자동 집계 웹앱", flush=True)
    print(f"[안내] 접속 주소: {url}", flush=True)
    print("[안내] 종료하려면 Ctrl+C 를 누르세요.", flush=True)

    if not args.no_browser:
        threading.Thread(target=lambda: (time.sleep(0.8), webbrowser.open(url)), daemon=True).start()

    try:
        with make_server(args.host, args.port, application) as httpd:
            print("[상태] 서버가 정상적으로 실행되었습니다.", flush=True)
            httpd.serve_forever()
    except OSError as exc:
        print(f"[오류] 서버 실행 실패: {exc}", flush=True)
        print("[해결] 다른 프로그램이 포트를 사용 중이면 --port 8010 같이 바꿔서 실행하세요.", flush=True)
        return 1
    except KeyboardInterrupt:
        print("\n[종료] 서버를 종료했습니다.", flush=True)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
