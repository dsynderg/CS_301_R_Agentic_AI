"""
A collection of tools that an LLM can call for various utilities.
"""

import random
from datetime import datetime, timedelta
from typing import Literal

from tools import ToolBox

# Create a toolbox instance for registering tools
tools = ToolBox()


# ==================== Random Tools ====================

@tools.tool
def generate_random_number(min_value: int, max_value: int) -> int:
    """Generate a random integer between min_value and max_value (inclusive)"""
    return random.randint(min_value, max_value)


@tools.tool
def generate_random_float(min_value: float, max_value: float) -> float:
    """Generate a random float between min_value and max_value"""
    return random.uniform(min_value, max_value)


@tools.tool
def random_choice(options: str) -> str:
    """Pick a random choice from a comma-separated list of options"""
    choices = [opt.strip() for opt in options.split(",")]
    return random.choice(choices)


@tools.tool
def shuffle_list(items: str) -> str:
    """Shuffle a comma-separated list of items and return as comma-separated string"""
    items_list = [item.strip() for item in items.split(",")]
    random.shuffle(items_list)
    return ", ".join(items_list)


# ==================== Math Tools ====================

@tools.tool
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b


@tools.tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a"""
    return a - b


@tools.tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b


@tools.tool
def divide(a: float, b: float) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


@tools.tool
def power(base: float, exponent: float) -> float:
    """Calculate base raised to the power of exponent"""
    return base ** exponent


@tools.tool
def absolute_value(number: float) -> float:
    """Get the absolute value of a number"""
    return abs(number)


# ==================== String Tools ====================

@tools.tool
def string_length(text: str) -> int:
    """Get the length of a string"""
    return len(text)


@tools.tool
def convert_to_uppercase(text: str) -> str:
    """Convert text to uppercase"""
    return text.upper()


@tools.tool
def convert_to_lowercase(text: str) -> str:
    """Convert text to lowercase"""
    return text.lower()


@tools.tool
def reverse_string(text: str) -> str:
    """Reverse a string"""
    return text[::-1]


@tools.tool
def count_words(text: str) -> int:
    """Count the number of words in a text"""
    return len(text.split())


@tools.tool
def replace_text(text: str, old: str, new: str) -> str:
    """Replace occurrences of old text with new text"""
    return text.replace(old, new)


# ==================== Date/Time Tools ====================

@tools.tool
def get_current_date() -> str:
    """Get today's date in YYYY-MM-DD format"""
    return datetime.now().strftime("%Y-%m-%d")


@tools.tool
def get_current_time() -> str:
    """Get current time in HH:MM:SS format"""
    return datetime.now().strftime("%H:%M:%S")


@tools.tool
def add_days_to_date(date_str: str, days: int) -> str:
    """Add days to a date (format: YYYY-MM-DD)"""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    new_date = date_obj + timedelta(days=days)
    return new_date.strftime("%Y-%m-%d")


@tools.tool
def days_between_dates(date1: str, date2: str) -> int:
    """Calculate the number of days between two dates (format: YYYY-MM-DD)"""
    d1 = datetime.strptime(date1, "%Y-%m-%d")
    d2 = datetime.strptime(date2, "%Y-%m-%d")
    return abs((d2 - d1).days)


# ==================== List/Array Tools ====================

@tools.tool
def count_items(items: str) -> int:
    """Count the number of items in a comma-separated list"""
    return len([item.strip() for item in items.split(",") if item.strip()])


@tools.tool
def find_max(numbers: str) -> float:
    """Find the maximum value in a comma-separated list of numbers"""
    nums = [float(n.strip()) for n in numbers.split(",")]
    return max(nums)


@tools.tool
def find_min(numbers: str) -> float:
    """Find the minimum value in a comma-separated list of numbers"""
    nums = [float(n.strip()) for n in numbers.split(",")]
    return min(nums)


@tools.tool
def calculate_average(numbers: str) -> float:
    """Calculate the average of comma-separated numbers"""
    nums = [float(n.strip()) for n in numbers.split(",")]
    return sum(nums) / len(nums)


@tools.tool
def sum_numbers(numbers: str) -> float:
    """Sum a comma-separated list of numbers"""
    nums = [float(n.strip()) for n in numbers.split(",")]
    return sum(nums)


# ==================== Utility Tools ====================

@tools.tool
def is_even(number: int) -> bool:
    """Check if a number is even"""
    return number % 2 == 0


@tools.tool
def is_odd(number: int) -> bool:
    """Check if a number is odd"""
    return number % 2 != 0


@tools.tool
def coin_flip() -> str:
    """Flip a coin and return Heads or Tails"""
    return random.choice(["Heads", "Tails"])


@tools.tool
def roll_dice(num_dice: int, dice_sides: int) -> str:
    """Roll dice and return the results as comma-separated values and total"""
    rolls = [random.randint(1, dice_sides) for _ in range(num_dice)]
    total = sum(rolls)
    return f"Rolls: {', '.join(map(str, rolls))}, Total: {total}"
