#!/usr/bin/env python3
"""
Single-run version for GitHub Actions or cron jobs (Playwright)
"""

from movie_monitor import MovieMonitor
import sys

def main():
    """Run a single check instead of continuous monitoring."""
    monitor = MovieMonitor()
    
    print(f"Checking for movie: {monitor.config['movie_name']}")
    print(f"URL: {monitor.config['url']}")
    
    # Try multiple times with different strategies
    max_retries = 3
    for retry in range(max_retries):
        try:
            if monitor.check_movie_availability(retry):
                monitor.notify_movie_found()
                print("Movie found! Notifications sent.")
                return True
        except Exception as e:
            print(f"Retry {retry + 1}/{max_retries} failed: {e}")
            if retry < max_retries - 1:
                import time
                import random
                time.sleep(random.randint(10, 30))
    
    print("Movie not found yet.")
    return False

if __name__ == "__main__":
    found = main()
    sys.exit(0 if found else 1)