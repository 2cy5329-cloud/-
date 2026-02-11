from processor import summarize


def test_summarize_counts():
    rows = [
        {
            "이름": "홍길동",
            "생년월일": "1990-01-01",
            "이전주소": "전북 익산시",
            "새주소": "서울특별시 강남구",
            "이동구분": "전출",
        },
        {
            "이름": "김영희",
            "생년월일": "1980-05-03",
            "이전주소": "서울특별시 중구",
            "새주소": "전북 익산시",
            "이동구분": "전입",
        },
    ]

    result = summarize(rows, target_region="익산", reference_year=2025)
    assert result.total_rows == 2
    assert result.inbound == 1
    assert result.outbound == 1
    assert result.net == 0
    assert sum(row["인원"] for row in result.flow_table) == 2
