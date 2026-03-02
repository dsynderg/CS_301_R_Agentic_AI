"""
Test script to verify Canvas API key functionality
"""

import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

def test_canvas_api():
    """Test Canvas API key and basic connectivity"""
    
    print("=" * 60)
    print("Canvas API Key Test")
    print("=" * 60)
    
    # Get credentials from environment
    api_token = os.getenv('CANVAS_API_TOKEN')
    api_url = os.getenv('CANVAS_API_URL')
    
    # Validate credentials exist
    if not api_token:
        print("❌ ERROR: CANVAS_API_TOKEN not found in .env file")
        return False
    
    if not api_url:
        print("❌ ERROR: CANVAS_API_URL not found in .env file")
        return False
    
    print(f"\n✓ Found CANVAS_API_TOKEN (length: {len(api_token)} characters)")
    print(f"✓ Found CANVAS_API_URL: {api_url}")
    
    # Test 1: Verify API token format
    print("\n[Test 1] Validating token format...")
    if '~' in api_token:
        print("✓ Token format looks correct (contains '~' separator)")
    else:
        print("⚠ Warning: Token format may be incorrect (missing '~' separator)")
    
    # Test 2: Get user profile (authentication test)
    print("\n[Test 2] Testing authentication with Canvas API...")
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Try to get the authenticated user's profile
        profile_url = f"{api_url.rstrip('/')}/users/self/profile"
        print(f"   Making request to: {profile_url}")
        
        response = requests.get(profile_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✓ Authentication successful!")
            user_data = response.json()
            print(f"   User: {user_data.get('name', 'Unknown')}")
            print(f"   ID: {user_data.get('id', 'Unknown')}")
            print(f"   Email: {user_data.get('email', 'Unknown')}")
            return True
        elif response.status_code == 401:
            print(f"❌ Authentication failed (401 Unauthorized)")
            print(f"   Response: {response.text}")
            return False
        elif response.status_code == 404:
            print(f"❌ API endpoint not found (404)")
            print(f"   Make sure CANVAS_API_URL is correct")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - check your internet connection")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print(f"   Check if CANVAS_API_URL is correct: {api_url}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False


def test_canvas_api_courses():
    """Test fetching courses from Canvas API"""
    
    print("\n" + "=" * 60)
    print("Canvas API Courses Test")
    print("=" * 60)
    
    api_token = os.getenv('CANVAS_API_TOKEN')
    api_url = os.getenv('CANVAS_API_URL')
    
    if not api_token or not api_url:
        print("❌ Missing API credentials, skipping courses test")
        return False
    
    print("\n[Test] Fetching enrolled courses...")
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        courses_url = f"{api_url.rstrip('/')}/courses?enrollment_state=active"
        response = requests.get(courses_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            courses = response.json()
            print(f"✓ Successfully fetched {len(courses)} course(s)")
            for course in courses[:5]:  # Show first 5
                print(f"   - {course.get('name', 'Unknown')} (ID: {course.get('id')})")
            if len(courses) > 5:
                print(f"   ... and {len(courses) - 5} more")
            return True
        else:
            print(f"❌ Failed to fetch courses (Status: {response.status_code})")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching courses: {type(e).__name__}: {e}")
        return False


if __name__ == '__main__':
    print("\nRunning Canvas API Tests...\n")
    
    # Run tests
    auth_test_passed = test_canvas_api()
    courses_test_passed = test_canvas_api_courses()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Authentication Test: {'✓ PASSED' if auth_test_passed else '❌ FAILED'}")
    print(f"Courses Test: {'✓ PASSED' if courses_test_passed else '❌ FAILED'}")
    
    if auth_test_passed:
        print("\n✓ Canvas API key is valid and working!")
        sys.exit(0)
    else:
        print("\n❌ Canvas API key test failed. Please check your credentials.")
        sys.exit(1)
