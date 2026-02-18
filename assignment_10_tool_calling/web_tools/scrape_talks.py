"""
Scrape all talks from a General Conference speaker page.
"""

import requests
from bs4 import BeautifulSoup
from url_retriver import scrape_webpage


def scrape_all_talks(speaker_page_url: str) -> str:
    """Scrape all talks from a General Conference speaker page and return the content of the first talk."""
    # Fetch the HTML from the speaker page to get links
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(speaker_page_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error: Failed to retrieve speaker page from {speaker_page_url}: {e}"
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all talk links on the speaker page
    talk_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/study/general-conference/' in href and href not in talk_links:
            if not href.startswith('http'):
                href = f"https://www.churchofjesuschrist.org{href}"
            talk_links.append(href)
    
    if not talk_links:
        return "Error: No talks found on speaker page."
    
    # Scrape the first talk
    first_talk_content = scrape_webpage(talk_links[0])
    if first_talk_content is None:
        return f"Error: Failed to retrieve first talk from {talk_links[0]}"
    
    return f"First talk scraped from {talk_links[0]}:\n\n{first_talk_content}"


def main():
    """Main function to scrape talks from a speaker page."""
    speaker_url = "https://www.churchofjesuschrist.org/study/general-conference/speakers/david-a-bednar?lang=eng"
    
    print(f"Scraping talks from: {speaker_url}\n")
    
    result = scrape_all_talks(speaker_url)
    print(result)


if __name__ == "__main__":
    main()
