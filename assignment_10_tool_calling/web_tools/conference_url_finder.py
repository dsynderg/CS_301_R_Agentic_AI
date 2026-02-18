"""
URL generator for LDS General Conference speaker pages.
"""


def generate_conference_speaker_url(speaker_name: str) -> str:
    """
    Generate a URL for an LDS General Conference speaker page.
    
    Takes a speaker name, lowercases it, replaces spaces with hyphens,
    and constructs the full conference speaker URL.
    
    Args:
        speaker_name: The name of the speaker (e.g., "Russell M Nelson")
    
    Returns:
        The full URL (e.g., "https://www.churchofjesuschrist.org/study/general-conference/speakers/russell-m-nelson?lang=eng")
    """
    # Lowercase the string and replace spaces with hyphens
    hyphenated_name = speaker_name.lower().replace(' ', '-')
    
    # Construct and return the URL
    url = f"https://www.churchofjesuschrist.org/study/general-conference/speakers/{hyphenated_name}?lang=eng"
    
    return url


if __name__ == "__main__":
    # Example usage
    speaker = "Russell M Nelson"
    url = generate_conference_speaker_url(speaker)
    print(f"Speaker: {speaker}")
    print(f"URL: {url}")
    
    # More examples
    print("\nMore examples:")
    examples = ["Dallin H Oaks", "Henry B Eyring", "Sheri L Dew", "M Russell Ballard"]
    for name in examples:
        print(f"{name} -> {generate_conference_speaker_url(name)}")
