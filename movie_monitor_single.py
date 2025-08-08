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
    
    # Try multiple times only if blocked by Cloudflare
    max_retries = 3
    for retry in range(max_retries):
        try:
            result = monitor.check_movie_availability(retry)
            if result is True:
                monitor.notify_movie_found()
                print("Movie found! Notifications sent.")
                return True
            elif result is False:
                # Movie not found but page loaded successfully - no need to retry
                print("Movie not found yet.")
                return False
        except Exception as e:
            error_msg = str(e).lower()
            if "cloudflare" in error_msg or "blocked" in error_msg or "timeout" in error_msg:
                print(f"Retry {retry + 1}/{max_retries} due to blocking/timeout: {e}")

                # Send admin alert on first blocking attempt
                if retry == 0:
                    monitor.send_admin_alert(str(e), retry)

                if retry < max_retries - 1:
                    import time
                    import random
                    time.sleep(random.randint(10, 30))
                else:
                    # Final attempt failed - send another alert if cooldown passed
                    monitor.send_admin_alert(f"All {max_retries} attempts failed. Last error: {str(e)}", retry)
            else:
                # Other errors - don't retry
                print(f"Error checking movie: {e}")
                return False
    
    print("Failed to check movie after retries.")
    return False

if __name__ == "__main__":
    found = main()
    sys.exit(0 if found else 1)