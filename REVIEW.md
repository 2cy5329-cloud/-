# 코드 리뷰 (인증기 통합 관리 및 결산 시스템)

## 총평
- 전반적으로 UI/UX, 인쇄 레이아웃, 로컬 스토리지 기반 데이터 복구 흐름까지 잘 구성되어 있습니다.
- 특히 `inputMachines`/`historyMachines` 분리, `parseCurrency` 방어 로직, `importFullBackup`의 DOM 존재 체크 등은 실무 안정성이 높습니다.

## 개선 권장 사항

### 1) `document.write` 기반 UI 렌더링 제거 권장
- 현재 인증기 카드 렌더링을 `<script>` 내부 `document.write`로 생성하고 있습니다.
- 페이지 로딩 이후 재호출 시 문서 전체를 덮어쓸 수 있고, 유지보수/디버깅이 어렵습니다.
- 권장: 템플릿 문자열을 `container.innerHTML += ...`로 삽입하거나, `createElement` 기반 렌더 함수로 전환.

### 2) 히스토리 중복 키를 `date`만으로 판단하는 구조
- `saveDailyClosing()`에서 같은 날짜면 기존 항목을 덮어씁니다.
- 의도된 정책일 수 있으나, 동일 날짜 다중 마감(오전/오후 보정 등)이 필요하면 손실 위험이 있습니다.
- 권장: `date + time` 또는 `fullDate` 기반으로 별도 버전 누적 옵션 제공.

### 3) 전역 상태 변수 증가로 인한 결합도 상승
- `localDataStore`, `localHistory`, `isCopyMode`, `isViewMode`, `selectedHistoryDate`, `currentPage`, `isDataSaved`가 모두 전역입니다.
- 기능이 늘어날수록 사이드이펙트 가능성이 커집니다.
- 권장: `state` 객체로 일원화하고, 상태 변경 함수(setter) 경유 패턴으로 정리.

### 4) 포맷팅/파싱 로직 중복
- 숫자 표시/복사 시 `replace('원','')`, `replace('매','')`, `parseCurrency` 등이 여러 함수에 반복됩니다.
- 권장: `toWonText`, `toCountText`, `fromDisplayText` 유틸로 공통화.

### 5) 접근성(Accessibility) 보완 여지
- 버튼/입력 위주의 풍부한 UI이지만 `aria-label`이나 라이브 리전 사용이 거의 없습니다.
- 권장: 주요 액션 버튼(`일일 마감`, `익일 준비`, 복사 버튼 등)에 `aria-label` 추가, 토스트를 `aria-live="polite"`로 지정.

### 6) 인쇄 CSS의 강한 선택자 의존성
- `@media print`에서 특정 구조(`section:last-of-type` 등)에 의존하는 숨김 규칙이 있어 레이아웃 변경 시 오동작 가능성이 있습니다.
- 권장: `print-only`, `no-print` 클래스 중심으로 명시적 제어.

### 7) 로컬스토리지 용량/무결성 대비
- 히스토리 증가 시 localStorage 제한(브라우저별 약 5MB 내외)에 근접할 수 있습니다.
- 권장: 저장 시 최대 개수 제한(예: 최근 365건), 오래된 항목 자동 삭제, 복구 실패 시 백업 안내 강화.

## 강점
- 방어적 파싱과 null-safe 처리(`parseCurrency`, optional chaining) 적용.
- 백업/복구 UX(자동 백업 + 수동 백업 + 파일 복구) 제공.
- 업무 규칙(2주 전 월~금 카드결제 반영)을 코드 주석과 함께 명확히 반영.
- 입력 모드/복사 모드/조회 모드 분리가 명확하고 사용자 안내(토스트/배너)가 충분함.

## 우선순위 제안
1. `document.write` 제거 (안정성/유지보수성)
2. 히스토리 저장 정책 강화 (데이터 손실 방지)
3. 상태/유틸 구조화 (확장 대비)
4. 접근성 및 인쇄 CSS 정리
