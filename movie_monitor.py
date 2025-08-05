#!/usr/bin/env python3
"""
BookMyShow Movie Monitor with Playwright
Monitors BookMyShow for specific movie availability and sends notifications.
"""

import time
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from typing import List, Optional
import json
import os
import sys
import random
from playwright.sync_api import sync_playwright, Browser, Page

class MovieMonitor:
    def __init__(self, config_file: str = "config.json"):
        """Initialize the movie monitor with configuration."""
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.playwright = None
        self.browser = None
        
        logging.info("Movie Monitor initialized successfully")

    def _parse_recipient_emails(self, emails_string: str) -> List[str]:
        """Parse comma-separated email addresses from string."""
        if not emails_string:
            return []
        
        emails = [email.strip() for email in emails_string.split(',')]
        # Filter out empty strings
        return [email for email in emails if email]

    def load_config(self, config_file: str) -> dict:
        """Load configuration from JSON file or environment variables."""
        default_config = {
            "url": "https://in.bookmyshow.com/explore/movies-bengaluru?languages=tamil",
            "movie_name": "Coolie",
            "check_interval": 300,  # 5 minutes
            "email": {
                "enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": os.getenv("SENDER_EMAIL", ""),
                "sender_password": os.getenv("SENDER_PASSWORD", ""),
                "recipient_emails": self._parse_recipient_emails(os.getenv("RECIPIENT_EMAILS", ""))
            },
            "webhook": {
                "enabled": False,
                "url": os.getenv("WEBHOOK_URL", "")
            },
            "logging": {
                "level": "INFO",
                "file": "movie_monitor.log"
            }
        }
        
        # Override with environment variables if they exist
        if os.getenv("MOVIE_NAME"):
            default_config["movie_name"] = os.getenv("MOVIE_NAME")
        if os.getenv("CHECK_INTERVAL"):
            default_config["check_interval"] = int(os.getenv("CHECK_INTERVAL"))
        if os.getenv("WEBHOOK_URL"):
            default_config["webhook"]["enabled"] = True
            default_config["webhook"]["url"] = os.getenv("WEBHOOK_URL")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
            except Exception as e:
                print(f"Error loading config file: {e}")
                print("Using default configuration")
                return default_config
        else:
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created default config file: {config_file}")
            return default_config

    def setup_logging(self):
        """Set up logging configuration."""
        log_level = getattr(logging, self.config["logging"]["level"].upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

    def setup_browser(self):
        """Initialize Playwright browser."""
        try:
            self.playwright = sync_playwright().start()
            
            # Launch browser with stealth settings to bypass Cloudflare
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage',
                    '--no-first-run',
                    '--disable-extensions',
                    '--disable-default-apps',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
                ]
            )
            
            logging.info("Browser initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            return False

    def close_browser(self):
        """Close browser and cleanup."""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logging.info("Browser closed successfully")
        except Exception as e:
            logging.warning(f"Error closing browser: {e}")

    def check_movie_availability(self) -> bool:
        """Check if the target movie is available on BookMyShow."""
        if not self.setup_browser():
            return False
            
        try:
            # Create new page with realistic settings
            page = self.browser.new_page()
            
            # Set viewport and stealth headers
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Add stealth JavaScript to hide automation
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                window.chrome = {
                    runtime: {},
                };
            """)
            
            page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            })
            
            logging.info(f"Checking movie availability at {self.config['url']}")
            
            # Navigate with realistic timing
            page.goto(self.config["url"], wait_until="domcontentloaded", timeout=60000)
            
            # Wait for content to load
            page.wait_for_timeout(random.randint(3000, 6000))
            
            # Wait for movie elements to appear
            page.wait_for_selector('.sc-7o7nez-0.elfplV', timeout=30000)
            
            # Find all movie title elements
            movie_elements = page.query_selector_all('.sc-7o7nez-0.elfplV')
            
            movie_found = False
            movies_list = []
            
            for element in movie_elements:
                movie_title = element.text_content().strip()
                movies_list.append(movie_title)
                if self.config["movie_name"].lower() in movie_title.lower():
                    logging.info(f"Found target movie: {movie_title}")
                    movie_found = True
            
            logging.info(f"Found {len(movies_list)} movies: {', '.join(movies_list[:5])}...")
            
            page.close()
            return movie_found
            
        except Exception as e:
            logging.error(f"Error checking movie availability: {e}")
            return False
        finally:
            self.close_browser()

    def send_email_notification(self):
        """Send email notification when movie is found."""
        if not self.config["email"]["enabled"]:
            return
            
        try:
            sender_email = self.config["email"]["sender_email"]
            sender_password = self.config["email"]["sender_password"]
            recipient_emails = self.config["email"]["recipient_emails"]
            
            if not all([sender_email, sender_password]) or not recipient_emails:
                logging.warning("Email configuration incomplete - skipping email notification")
                return
            
            body = f"""
Great news! The movie "{self.config['movie_name']}" is now available for booking on BookMyShow.

You can book your tickets here: {self.config['url']}

Movie Monitor Alert
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            server = smtplib.SMTP(self.config["email"]["smtp_server"], self.config["email"]["smtp_port"])
            server.starttls()
            server.login(sender_email, sender_password)
            
            # Send to each recipient
            for recipient_email in recipient_emails:
                message = MimeMultipart()
                message["From"] = sender_email
                message["To"] = recipient_email
                message["Subject"] = f"🎬 Movie Alert: {self.config['movie_name']} is now available!"
                message.attach(MimeText(body, "plain"))
                
                text = message.as_string()
                server.sendmail(sender_email, recipient_email, text)
                logging.info(f"Email notification sent to {recipient_email}")
            
            server.quit()
            logging.info(f"Email notifications sent to {len(recipient_emails)} recipients")
            
        except Exception as e:
            logging.error(f"Failed to send email notification: {e}")

    def send_webhook_notification(self):
        """Send webhook notification (for Discord, Slack, etc.)"""
        if not self.config["webhook"]["enabled"] or not self.config["webhook"]["url"]:
            return
            
        try:
            import requests
            payload = {
                "content": f"🎬 **Movie Alert!** \\n\\nThe movie **{self.config['movie_name']}** is now available for booking!\\n\\nBook here: {self.config['url']}"
            }
            
            response = requests.post(self.config["webhook"]["url"], json=payload, timeout=10)
            response.raise_for_status()
            
            logging.info("Webhook notification sent successfully")
            
        except Exception as e:
            logging.error(f"Failed to send webhook notification: {e}")

    def notify_movie_found(self):
        """Send all configured notifications when movie is found."""
        logging.info(f"🎉 MOVIE FOUND: {self.config['movie_name']} is available!")
        
        self.send_email_notification()
        self.send_webhook_notification()
        
        # Print to console as well
        print(f"\n{'='*60}")
        print(f"🎬 MOVIE ALERT: {self.config['movie_name']} IS AVAILABLE!")
        print(f"Book your tickets at: {self.config['url']}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

    def run(self):
        """Main monitoring loop."""
        logging.info(f"Starting movie monitor for '{self.config['movie_name']}'")
        logging.info(f"Check interval: {self.config['check_interval']} seconds")
        
        print(f"🎬 Movie Monitor Started (Playwright)")
        print(f"Monitoring: {self.config['movie_name']}")
        print(f"URL: {self.config['url']}")
        print(f"Check interval: {self.config['check_interval']} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{current_time}] Checking movie availability...")
                
                if self.check_movie_availability():
                    self.notify_movie_found()
                    # Stop monitoring after finding the movie
                    logging.info("Movie found - stopping monitor")
                    break
                else:
                    logging.info(f"Movie not found - waiting {self.config['check_interval']} seconds")
                
                time.sleep(self.config["check_interval"])
                
        except KeyboardInterrupt:
            logging.info("Movie monitor stopped by user")
            print("\nMovie monitor stopped.")
        except Exception as e:
            logging.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            self.close_browser()

def main():
    """Main function to run the movie monitor."""
    monitor = MovieMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
