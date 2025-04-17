"""Scraper for YIWH calendar."""
import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


class Event:
    def __init__(self, _datetime):
        self.datetime = datetime.strptime(_datetime, "%Y-%m-%d %I:%M%p")

    def __eq__(self, other):
        return self.datetime == other.datetime

    def __lt__(self, other):
        return self.datetime < other.datetime

    def __str__(self):
        return self.datetime.strftime("%Y-%m-%d %I:%M%p")

    @staticmethod
    def is_candle_lighting(title):
        return "Candle Lighting" in title and "Earliest" not in title

    @staticmethod
    def is_havdalah(title):
        return "Shabbat Ends" in title or "Yom Tov Ends" in title


class YIWHScraper:
    def __init__(self):
        self.base_url = "https://www.youngisraelwh.org/calendar"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def parse_event_data(self, event_element, date_str):
        """Parse individual event data from the calendar popover"""
        try:
            # Get the data-popuphtml attribute and parse it
            popup_html = event_element.get('data-popuphtml', '')
            if not popup_html:
                _LOGGER.debug("No popup HTML found for event")
                return None, None
                
            # Parse the HTML content of the popup
            popup_soup = BeautifulSoup(popup_html, 'html.parser')
            
            # Extract event details
            title = popup_soup.find('h3').get_text() if popup_soup.find('h3') else ''
            if not title:
                _LOGGER.debug("No title found in event popup")
                return None, None
            
            # Skip if not a target event
            if not Event.is_candle_lighting(title) and not Event.is_havdalah(title):
                return None, None
            
            # Get the visible text (usually contains time and title)
            visible_text = event_element.get_text().strip()
            time_str = visible_text.split()[0]
            
            # Create datetime string in format "YYYY-MM-DD HH:MMam/pm"
            datetime_str = f"{date_str} {time_str}"
            
            return title, datetime_str
            
        except Exception as e:
            _LOGGER.exception("Error parsing event: %s", str(e))
            return None, None

    def parse_calendar_html(self, html_content):
        """Parse the calendar HTML and extract events"""
        soup = BeautifulSoup(html_content, 'html.parser')
        candle_lighting = []
        havdalah = []
        
        # Find all calendar day cells
        day_cells = soup.find_all('td', id=lambda x: x and x.startswith('td'))
        
        if not day_cells:
            _LOGGER.error("No calendar day cells found in HTML")
            raise ValueError("Calendar structure not found in response")
        
        _LOGGER.debug("Found %d day cells in calendar", len(day_cells))
        
        for cell in day_cells:
            try:
                # Get the date information
                day_header = cell.find('div', class_='dayhead')
                if not day_header:
                    continue
                    
                date_link = day_header.find('a')
                if not date_link:
                    continue
                    
                date_str = date_link.get('href', '').split('cal_date=')[-1]
                
                # Find all events for this day
                day_events = cell.find_all('li', class_='calendar_popover_trigger')
                
                for event in day_events:
                    title, datetime_str = self.parse_event_data(event, date_str)
                    if title:
                        if Event.is_candle_lighting(title):
                            candle_lighting.append(Event(datetime_str))
                        elif Event.is_havdalah(title):
                            havdalah.append(Event(datetime_str))
                    
            except Exception as e:
                _LOGGER.exception("Error processing day cell: %s", str(e))
                continue
        
        # Sort both lists
        candle_lighting.sort()
        havdalah.sort()
        
        _LOGGER.debug("Found %d candle lighting times and %d havdalah times", 
                     len(candle_lighting), len(havdalah))
                
        return candle_lighting, havdalah

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

            _LOGGER.debug(f"Fetching calendar from URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                _LOGGER.error("Failed to fetch calendar. Status code: %d", response.status_code)
                raise ConnectionError(f"HTTP {response.status_code}: Failed to fetch calendar")
            
            _LOGGER.debug("Successfully fetched calendar page")
            return self.parse_calendar_html(response.text)
            
        except requests.RequestException as e:
            _LOGGER.error("Network error while fetching calendar: %s", str(e))
            raise ConnectionError(f"Network error: {str(e)}")
        except Exception as e:
            _LOGGER.exception("Unexpected error while scraping calendar")
            raise


if __name__ == "__main__":
    scraper = YIWHScraper()
    candle_lighting, havdalah = scraper.scrape_calendar(delta=6)
    
    print("\nCandle Lighting Times:")
    print("=====================")
    for event in candle_lighting:
        print(event)
        
    print("\nHavdalah Times:")
    print("==============")
    for event in havdalah:
        print(event)

