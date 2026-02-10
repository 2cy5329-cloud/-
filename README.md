# 인증기 통합 관리 및 결산 시스템 실행 방법

깃허브를 몰라도 **아래 순서대로** 하면 바로 실행할 수 있습니다.

## 0) 먼저 파일 다운로드 (GitHub 웹에서)

### 방법 A. 저장소 전체를 ZIP으로 받기 (추천)
1. GitHub 저장소 페이지로 이동
2. 초록색 **`Code`** 버튼 클릭
3. **`Download ZIP`** 클릭
4. 내려받은 ZIP 압축 해제
5. 압축 해제한 폴더 안의 `index.html` 실행

### 방법 B. `index.html` 파일만 받기
1. GitHub에서 `index.html` 파일 클릭
2. 우측 상단 **`Raw`** 버튼 클릭
3. 브라우저에서 열린 내용을 `Ctrl + S`로 저장 (파일명: `index.html`)

---

## 1) 파일 바로 열기 (가장 쉬움)
1. 다운로드한 폴더에서 `index.html` 파일을 더블클릭합니다.
2. 브라우저(크롬/엣지)에서 화면이 열리면 바로 사용하면 됩니다.

> 참고: 일부 브라우저/환경에서는 로컬 파일 제한 때문에 기능이 제한될 수 있습니다. 이 경우 아래 "로컬 서버" 방법을 사용하세요.

---

## 2) 로컬 서버로 실행 (권장)

### A. Linux/macOS
```bash
cd <압축해제한_폴더_경로>
python3 -m http.server 4173
```
브라우저에서 아래 주소 접속:
- http://localhost:4173/index.html

### B. Windows (PowerShell)
```powershell
cd <압축해제한_폴더_경로>
python -m http.server 4173
```
브라우저에서 아래 주소 접속:
- http://localhost:4173/index.html

---

## 3) `start.sh`로 한 번에 실행 (Linux/macOS)
```bash
cd <압축해제한_폴더_경로>
./start.sh
```

---

## 종료 방법
서버를 실행한 터미널에서 `Ctrl + C`를 누르면 종료됩니다.

---

## 파일 구성
- `index.html`: 메인 프로그램 (단일 파일)
- `start.sh`: 원클릭 로컬 서버 실행 스크립트
