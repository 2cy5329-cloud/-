from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


AGE_BUCKETS = [
    (0, 17, "17세 이하"),
    (18, 19, "18-19세"),
    (20, 24, "20-24세"),
    (25, 29, "25-29세"),
    (30, 34, "30-34세"),
    (35, 39, "35-39세"),
    (40, 49, "40대"),
    (50, 59, "50대"),
    (60, 150, "60세 이상"),
]

REQUIRED_COLUMNS = {"이름", "생년월일", "이전주소", "새주소", "이동구분"}


@dataclass
class SummaryResult:
    total_rows: int
    inbound: int
    outbound: int
    net: int
    flow_table: list[dict[str, Any]]
    age_table: list[dict[str, Any]]


def validate_columns(columns: list[str]) -> None:
    missing = REQUIRED_COLUMNS - set(columns)
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {', '.join(sorted(missing))}")


def extract_region(address: str) -> str:
    if not address:
        return "미상"
    first = address.strip().split()[0]
    replacements = {
        "서울특별시": "서울",
        "서울시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
        "경기도": "경기",
        "강원특별자치도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전북특별자치도": "전북",
        "전라북도": "전북",
        "전라남도": "전남",
        "경상북도": "경북",
        "경상남도": "경남",
        "제주특별자치도": "제주",
    }
    return replacements.get(first, first)


def parse_birth_year(value: str) -> int | None:
    if not value:
        return None
    text = str(value).strip()

    if text.isdigit() and len(text) >= 7:
        # yyyymmdd or yymmdd
        if len(text) == 8:
            return int(text[:4])

    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).year
        except ValueError:
            continue

    # excel serial date
    try:
        serial = float(text)
        base = datetime(1899, 12, 30)
        return (base + timedelta(days=serial)).year
    except ValueError:
        return None


def age_bucket(age: int | None) -> str:
    if age is None:
        return "기타"
    for low, high, label in AGE_BUCKETS:
        if low <= age <= high:
            return label
    return "기타"


def summarize(rows: list[dict[str, str]], target_region: str, reference_year: int) -> SummaryResult:
    if not rows:
        return SummaryResult(0, 0, 0, 0, [], [])

    validate_columns(list(rows[0].keys()))

    flow_counter: dict[tuple[str, str], int] = defaultdict(int)
    inbound = 0
    outbound = 0

    age_in = Counter()
    age_out = Counter()

    for row in rows:
        from_region = extract_region(row.get("이전주소", ""))
        to_region = extract_region(row.get("새주소", ""))
        move_type = str(row.get("이동구분", "")).strip()

        flow_counter[(from_region, to_region)] += 1

        birth_year = parse_birth_year(str(row.get("생년월일", "")))
        age = reference_year - birth_year if birth_year else None
        bucket = age_bucket(age)

        if "전입" in move_type:
            if target_region in str(row.get("새주소", "")):
                inbound += 1
            age_in[bucket] += 1
        if "전출" in move_type:
            if target_region in str(row.get("이전주소", "")):
                outbound += 1
            age_out[bucket] += 1

    flow_table = [
        {"이전시도": key[0], "새시도": key[1], "인원": cnt}
        for key, cnt in sorted(flow_counter.items(), key=lambda item: item[1], reverse=True)
    ]

    all_buckets = [label for _, _, label in AGE_BUCKETS] + ["기타"]
    age_table = []
    for label in all_buckets:
        row_in = age_in.get(label, 0)
        row_out = age_out.get(label, 0)
        if row_in == 0 and row_out == 0:
            continue
        age_table.append(
            {
                "연령대": label,
                "전입자": row_in,
                "전출자": row_out,
                "전입-전출": row_in - row_out,
            }
        )

    return SummaryResult(
        total_rows=len(rows),
        inbound=inbound,
        outbound=outbound,
        net=inbound - outbound,
        flow_table=flow_table,
        age_table=age_table,
    )
