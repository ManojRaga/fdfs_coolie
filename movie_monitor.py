#!/usr/bin/env python3
"""
BookMyShow Movie Monitor
Monitors BookMyShow for specific movie availability and sends notifications.
"""

import requests
import time
import smtplib
import logging
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from bs4 import BeautifulSoup
from typing import List, Optional
import json
import os
import sys

class MovieMonitor:
    def __init__(self, config_file: str = "config.json"):
        """Initialize the movie monitor with configuration."""
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.session = requests.Session()
        
        # Set up session headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
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

    def check_movie_availability(self) -> bool:
        """Check if the target movie is available on BookMyShow."""
        try:
            logging.info(f"Checking movie availability at {self.config['url']}")
            response = self.session.get(self.config["url"], timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all movie title divs with the specific class
            movie_divs = soup.find_all('div', class_='sc-7o7nez-0 elfplV')
            
            if not movie_divs:
                logging.warning("No movie titles found - page structure might have changed")
                return False
            
            # Check if any movie title contains our target movie
            movies_found = []
            for div in movie_divs:
                movie_title = div.get_text(strip=True)
                movies_found.append(movie_title)
                if self.config["movie_name"].lower() in movie_title.lower():
                    logging.info(f"Found target movie: {movie_title}")
                    return True
            
            logging.info(f"Movie '{self.config['movie_name']}' not found. Found {len(movie_divs)} movies: {', '.join(movies_found[:5])}...")
            return False
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return False

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
            payload = {
                "content": f"🎬 **Movie Alert!** \n\nThe movie **{self.config['movie_name']}** is now available for booking!\n\nBook here: {self.config['url']}"
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
        
        print(f"🎬 Movie Monitor Started")
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

def main():
    """Main function to run the movie monitor."""
    monitor = MovieMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
