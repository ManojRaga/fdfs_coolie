#!/usr/bin/env python3
"""
Single-run version for GitHub Actions or cron jobs
"""


from movie_monitor import MovieMonitor
import sys


def main():
   """Run a single check instead of continuous monitoring."""
   monitor = MovieMonitor()
  
   print(f"Checking for movie: {monitor.config['movie_name']}")
   print(f"URL: {monitor.config['url']}")
  
   if monitor.check_movie_availability():
       monitor.notify_movie_found()
       print("Movie found! Notifications sent.")
       return True
   else:
       print("Movie not found yet.")
       return False


if __name__ == "__main__":
   found = main()
   sys.exit(0 if found else 1)

