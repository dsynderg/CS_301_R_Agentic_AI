"""
Web scraping utilities for retrieving and processing web page content.
"""

import argparse
import requests
from bs4 import BeautifulSoup
from typing import Optional


def scrape_webpage(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch a webpage and extract its text content.
    
    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds (default: 10)
    
    Returns:
        The extracted text content from the page, or None if the request fails
    
    Raises:
        requests.RequestException: If the request fails
    """
    try:
        # Set a user agent to avoid being blocked by some sites
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()  # Raise an error for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get only the body element
        body = soup.find('body')
        if not body:
            return None
        
        # Extract all paragraph elements from body
        paragraphs = body.find_all('p')
        if not paragraphs:
            return None
        
        # Get text from paragraphs, removing script/style tags and skipping paragraphs with parent <a> tags
        text_parts = []
        for p in paragraphs:
            # Skip this paragraph if it has a parent <a> tag
            if p.find_parent('a'):
                continue
            
            # Remove script and style elements from this paragraph
            for script in p(["script", "style"]):
                script.decompose()
            # Extract clean text
            para_text = p.get_text().strip()
            if para_text:
                text_parts.append(para_text)
        
        text = '\n'.join(text_parts)
        
        return text
    
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def scrape_webpage_with_title(url: str, timeout: int = 10) -> dict:
    """
    Fetch a webpage and extract both its title and text content.
    
    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds (default: 10)
    
    Returns:
        A dictionary with 'title' and 'text' keys containing the page's title and content
    
    Raises:
        requests.RequestException: If the request fails
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else "No title found"
        
        # Get only the body element
        body = soup.find('body')
        if not body:
            text = None
        else:
            # Extract all paragraph elements from body
            paragraphs = body.find_all('p')
            if not paragraphs:
                text = None
            else:
                # Get text from paragraphs, removing script/style tags and skipping paragraphs with parent <a> tags
                text_parts = []
                for p in paragraphs:
                    # Skip this paragraph if it has a parent <a> tag
                    if p.find_parent('a'):
                        continue
                    
                    # Remove script and style elements from this paragraph
                    for script in p(["script", "style"]):
                        script.decompose()
                    # Extract clean text
                    para_text = p.get_text().strip()
                    if para_text:
                        text_parts.append(para_text)
                
                text = '\n'.join(text_parts)
        
        return {
            'url': url,
            'title': title,
            'text': text
        }
    
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return {
            'url': url,
            'title': None,
            'text': None,
            'error': str(e)
        }


def main():
    """
    Main function to run the web page retriever from the command line.
    """
    parser = argparse.ArgumentParser(
        description='Scrape text content from a webpage'
    )
    parser.add_argument(
        'url',
        nargs='?',
        help='The URL to scrape'
    )
    parser.add_argument(
        '--title',
        action='store_true',
        help='Include the page title in the output'
    )
    parser.add_argument(
        '--preview',
        type=int,
        default=None,
        help='Print only the first N characters of the content'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds (default: 10)'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode, prompting for URLs'
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        # Interactive mode
        print("Web Page Retriever - Interactive Mode")
        print("Type 'quit' or 'exit' to stop\n")
        
        while True:
            url = input("Enter URL to scrape (or 'quit'): ").strip()
            
            if url.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break
            
            if not url:
                print("Please enter a valid URL.\n")
                continue
            
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            print(f"\nFetching {url}...")
            
            if args.title:
                result = scrape_webpage_with_title(url, timeout=args.timeout)
                if result.get('title'):
                    print(f"\nTitle: {result['title']}")
                if result.get('text'):
                    content = result['text']
                    if args.preview:
                        print(f"\nContent (first {args.preview} characters):")
                        print(content[:args.preview])
                    else:
                        print(f"\nContent ({len(result['text'])} characters):")
                        print(content)
                elif result.get('error'):
                    print(f"Error: {result['error']}")
            else:
                content = scrape_webpage(url, timeout=args.timeout)
                if content:
                    if args.preview:
                        print(f"\nContent (first {args.preview} characters):")
                        print(content[:args.preview])
                    else:
                        print(f"\nContent ({len(content)} characters):")
                        print(content)
                else:
                    print("Failed to retrieve content.")
            
            print()
    
    elif args.url:
        # Single URL mode
        url = args.url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        print(f"Fetching {url}...\n")
        
        if args.title:
            result = scrape_webpage_with_title(url, timeout=args.timeout)
            if result.get('title'):
                print(f"Title: {result['title']}\n")
            if result.get('text'):
                content = result['text']
                if args.preview:
                    print(f"Content (first {args.preview} characters):")
                    print(content[:args.preview])
                else:
                    print(f"Content ({len(result['text'])} characters):")
                    print(content)
            elif result.get('error'):
                print(f"Error: {result['error']}")
        else:
            content = scrape_webpage(url, timeout=args.timeout)
            if content:
                if args.preview:
                    print(f"Content (first {args.preview} characters):")
                    print(content[:args.preview])
                else:
                    print(f"Content ({len(content)} characters):")
                    print(content)
            else:
                print("Failed to retrieve content.")
    
    else:
        # No URL provided, run interactive by default
        print("No URL provided. Use --interactive for interactive mode or provide a URL.\n")
        parser.print_help()


if __name__ == "__main__":
    main()
