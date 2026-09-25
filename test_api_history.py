import requests

API_URL = "https://biquote.io/api/XAUUSD/ohlc"


def test_period(name, date_from, date_to):
    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    params = {
        "interval": "15m",
        "limit": 1000,
        "from": date_from,
        "to": date_to,
    }

    print("FROM:", date_from)
    print("TO  :", date_to)

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=30
        )

        print("STATUS:", response.status_code)

        if response.status_code != 200:
            print(response.text[:1000])
            return

        data = response.json()
        bars = data.get("bars", [])

        print("BARS:", len(bars))

        if bars:
            print("FIRST:", bars[0]["openTime"])
            print("LAST :", bars[-1]["openTime"])

    except Exception as e:
        print("XATO:", repr(e))


print("=" * 70)
print("BIQUOTE FROM/TO FILTER TEST")
print("=" * 70)

# Juda eski davr
test_period(
    "2026-08-01 -> 2026-08-05",
    "2026-08-01T00:00:00Z",
    "2026-08-05T00:00:00Z"
)

# O'rtadagi davr
test_period(
    "2026-09-01 -> 2026-09-05",
    "2026-09-01T00:00:00Z",
    "2026-09-05T00:00:00Z"
)

# Hozirgi davr
test_period(
    "2026-09-23 -> 2026-09-25",
    "2026-09-23T00:00:00Z",
    "2026-09-25T23:59:59Z"
)

print("\n" + "=" * 70)
print("TEST YAKUNLANDI")
print("=" * 70)