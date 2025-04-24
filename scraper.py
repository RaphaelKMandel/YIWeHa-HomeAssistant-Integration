"""Scraper for YIWH calendar."""
import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


def totime(datetime):
    return datetime.strftime("%I:%M%p")


def tostring(datetime):
    return datetime.strftime("%Y-%m-%d %I:%M%p")


def fromstring(string):
    return datetime.strptime(string, "%Y-%m-%d %I:%M%p")


class Event:
    def __init__(self, title, _datetime):
        self.title = title
        self.datetime = fromstring(_datetime) if _datetime else None
        self.date = self.datetime.date() if _datetime else None
        self.time = self.datetime.time() if _datetime else None

    def to_dict(self):
        return {
            "title": self.title,
            "datetime": self.datetime
        }

    def __eq__(self, other):
        return self.datetime == other.datetime

    def __lt__(self, other):
        return self.datetime < other.datetime

    def __str__(self):
        if self.datetime:
            return tostring(self.datetime)

        return self.title

    def __repr__(self):
        if not self.datetime:
            return str(self)

        return f"{totime(self.datetime)}: {self.title}"


class Sedra:
    def __init__(self, title):
        self.title = title

    def to_dict(self):
        return {"title": self.title}

    def __repr__(self):
        return self.title


class CalendarDay:
    def __init__(self, day_cell):
        self.candle_lighting = None
        self.havdalah = None
        self.omer = None
        self.rosh_chodesh = False
        self.hebcal = None
        self.events = []
        self.sedras = []
        self.init(day_cell)

    def to_dict(self):
        result = {}
        for key in {"candle_lighting", "havdalah", "omer", "rosh_chodesh", "hebcal", "events", "sedras"}:
            value = getattr(self, key)
            if isinstance(value, list) and hasattr(value[0], "to_dict"):
                value = [v.to_dict() for v in value]

            if isinstance(value, Event | Sedra):
                value = value.to_dict()

            result[key] = value

        return result

    def init(self, day_cell):
        try:
            """Parse the calendar HTML and extract events"""
            # Get the date information
            day_header = day_cell.find('div', class_='dayhead')
            if not day_header:
                return

            date_link = day_header.find('a')
            if not date_link:
                return

            self.date_str = date_link.get('href', '').split('cal_date=')[-1]
            self.date = datetime.strptime(self.date_str, "%Y-%m-%d").date()
            self.parse_jewish_day(day_cell)
            self.parse_sedra(day_cell)
            self.parse_events(day_cell)
        except Exception as e:
            _LOGGER.exception("YIWeHa: Error processing day cell: %s", str(e))

    def parse_jewish_day(self, day_cell):
        text = day_cell.find("span", class_="jewishDay")
        if text:
            self.hebcal = text.get_text(strip=True)

    def parse_sedra(self, day_cell):
        sedra_divs = day_cell.find_all("div", class_="sedra")
        for sedra_div in sedra_divs:
            text = sedra_div.get_text(strip=True)
            if "Day Omer" in text:
                self.omer = text

            if "Rosh Chodesh" in text:
                self.rosh_chodesh = True

            self.sedras += [Sedra(text)]

    def parse_events(self, day_cell):
        # Find all events for this day
        day_events = day_cell.find_all('li', class_='calendar_popover_trigger')

        for day_event in day_events:
            event = self.parse_event_data(day_event, self.date_str)
            if not event:
                continue

            self.events += [event]

            if "Candle Lighting" in event.title and "Earliest" not in event.title:
                self.candle_lighting = event
            elif "Shabbat Ends" in event.title or "Yom Tov Ends" in event.title:
                self.havdalah = event

        self.events.sort()

    def parse_event_data(self, event_element, date_str):
        """Parse individual event data from the calendar popover"""
        try:
            # Get the data-popuphtml attribute and parse it
            popup_html = event_element.get('data-popuphtml', '')
            if not popup_html:
                _LOGGER.debug("YIWeHa: Found no popup HTML for event")
                return None

            # Parse the HTML content of the popup
            popup_soup = BeautifulSoup(popup_html, 'html.parser')

            # Extract event details
            title = popup_soup.find('h3').get_text() if popup_soup.find('h3') else ''
            if not title:
                _LOGGER.debug("YIWeHa: Found no title in event popup")
                return None

            # Get the visible text (usually contains time and title)
            visible_text = event_element.get_text().strip()
            time_str = visible_text.split()[0]

            # Create datetime string in format "YYYY-MM-DD HH:MMam/pm"
            datetime_str = f"{date_str} {time_str}"

            return Event(title, datetime_str)

        except Exception as e:
            _LOGGER.exception("YIWeHa: Error parsing event: %s", str(e))
            return None


class YIWHScraper:
    def __init__(self):
        self.base_url = "https://www.youngisraelwh.org/calendar"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.days = {}

    def get_candle_lightings(self):
        candle_lightings = sorted([day.candle_lighting for day in self.days.values() if day.candle_lighting])
        _LOGGER.debug("YIWeHa: Found %d candle lighting times", len(candle_lightings))
        return candle_lightings

    def get_havdalahs(self):
        havdalahs = sorted([day.havdalah for day in self.days.values() if day.havdalah])
        _LOGGER.debug("YIWeHa: Found %d havdalah times", len(havdalahs))
        return havdalahs

    def get_today(self):
        return self.days[datetime.now().date()]

    def parse_calendar_html(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        day_cells = soup.find_all('td', id=lambda x: x and x.startswith('td'))

        if not day_cells:
            _LOGGER.error("YIWeHa: No calendar day cells found in HTML")
            raise ValueError("YIWeHa: Calendar structure not found in response")

        _LOGGER.debug("YIWeHa: Found %d day cells in calendar", len(day_cells))

        self.days = {}
        for cell in day_cells:
            day = CalendarDay(cell)
            self.days[day.date] = day

        return {
            "candle_lighting": self.get_candle_lightings(),
            "havdalah": self.get_havdalahs(),
            "today": self.get_today()
        }

    def scrape_calendar(self, delta=15):
        """Scrape calendar events directly from the website."""
        try:
            today = datetime.now()
            start_date = today - timedelta(days=delta)
            end_date = today + timedelta(days=delta)

            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            url = (
                f"{self.base_url}?advanced=Y&calendar=&"
                f"date_start=specific+date&date_start_x=0&date_start_date={start_date_str}&"
                f"has_second_date=Y&date_end=specific+date&date_end_x=0&date_end_date={end_date_str}&"
                f"view=month&month_view_type="
            )

            _LOGGER.debug(f"YIWeHa: Fetching calendar from URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code != 200:
                _LOGGER.error("YIWeHa: Failed to fetch calendar. Status code: %d", response.status_code)
                raise ConnectionError(f"YIWeHa: HTTP {response.status_code}: Failed to fetch calendar")

            _LOGGER.debug("YIWeHa: Successfully fetched calendar page")
            with open("response.html", "w") as f:
                f.write(response.text)
            return self.parse_calendar_html(response.text)

        except requests.RequestException as e:
            _LOGGER.error("YIWeHa: Network error while fetching calendar: %s", str(e))
            raise ConnectionError(f"YIWeHa: Network error: {str(e)}")
        except Exception as e:
            _LOGGER.exception("YIWeHa: Unexpected error while scraping calendar")
            raise


class DummyScraper:
    def __init__(self):
        now = datetime.now()

        self.candle_lightings = [
            Event(tostring(now - timedelta(minutes=40))),
            Event(tostring(now + timedelta(minutes=2))),
            Event(tostring(now + timedelta(minutes=4))),
            Event(tostring(now + timedelta(minutes=30)))
        ]
        self.havdalahs = [
            Event(tostring(now - timedelta(minutes=30))),
            Event(tostring(now + timedelta(minutes=3))),
            Event(tostring(now + timedelta(minutes=35)))
        ]

    def scrape_calendar(self, delta=15):
        return {
            "candle_lighting": self.candle_lightings,
            "havdalah": self.havdalahs,
            "today": [
                (fromstring("2025-04-22 09:00am"), "Shacharit1"),
                (fromstring("2025-04-23 09:00am"), "Shacharit2"),
                (fromstring("2025-04-24 09:00am"), "Shacharit3"),
                (fromstring("2025-04-25 09:00am"), "Shacharit4"),
            ]
        }


if __name__ == "__main__":
    scraper = YIWHScraper()
    # scraper = DummyScraper()
    events = scraper.scrape_calendar(delta=6)

    print("\nCandle Lighting Times:")
    print("=====================")
    for event in events["candle_lighting"]:
        print(event)

    print("\nHavdalah Times:")
    print("==============")
    for event in events["havdalah"]:
        print(event)

    print("\nToday:")
    print("==============")
    for event in events["today"].__dict__.items():
        print(repr(event))
