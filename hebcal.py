import requests
from datetime import datetime, timedelta


def get_datetime(string):
    try:
        return datetime.strptime(string, "%Y-%m-%dT%H:%M:%S%z")
    except:
        return datetime.strptime(string, "%Y-%m-%d")


class HebCal:
    BASE_URL = "https://www.hebcal.com/hebcal"

    def __init__(self, zipcode):
        self.zipcode = zipcode

    def get_zmanim(self, days_before=7, days_after=7):
        now = datetime.now().date()
        start_date = now - timedelta(days=days_before)
        end_date = now + timedelta(days=days_after)
        params = {
            "v": 1,
            "cfg": "json",
            "start": start_date,
            "end": end_date,
            "zip": self.zipcode,
            "m": 50,  # minutes after sunset for havdalah (adjust if needed)
            "maj": "on",  # major holidays
            "min": "on",  # minor holidays
            "mod": "on",  # modern holidays
        }

        response = requests.get(self.BASE_URL, params=params)
        if response.status_code != 200:
            print(f"Failed to get data for dates")
            return

        candle_lightings = []
        havdalahs = []
        data = response.json()
        items = data["items"]
        for item in items:
            print(item)
            date = get_datetime(item["date"])
            if item["category"] == "candles":
                candle_lightings.append(date)
            elif item["category"] == "havdalah":
                havdalahs.append(date)

        return candle_lightings, havdalahs


if __name__ == "__main__":
    print(HebCal("06117").get_zmanim())
