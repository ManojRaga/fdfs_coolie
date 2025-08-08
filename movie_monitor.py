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
        self.current_user_agent_index = 0
        self.current_viewport_index = 0

        # Pool of realistic user agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ]

        # Pool of realistic viewport sizes
        self.viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720},
            {"width": 1600, "height": 900},
            {"width": 1920, "height": 1200}
        ]
        
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
            "telegram": {
                "enabled": True,
                "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
                "chat_id": os.getenv("TELEGRAM_CHAT_ID", "")
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
        if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
            default_config["telegram"]["enabled"] = True
        
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

    def get_next_user_agent(self):
       """Get next user agent from rotation pool."""
       user_agent = self.user_agents[self.current_user_agent_index]
       self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
       return user_agent
  
    def get_next_viewport(self):
        """Get next viewport from rotation pool."""
        viewport = self.viewports[self.current_viewport_index]
        self.current_viewport_index = (self.current_viewport_index + 1) % len(self.viewports)
        return viewport
    
    def get_random_headers(self):
        """Generate randomized browser headers."""
        accept_languages = [
            "en-US,en;q=0.9",
            "en-US,en;q=0.9,es;q=0.8",
            "en-GB,en;q=0.9",
            "en-US,en;q=0.8,fr;q=0.7"
        ]
        
        platforms = [
            '"Windows"',
            '"macOS"',
            '"Linux"'
        ]
        
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": random.choice(accept_languages),
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": f'"Not A(Brand";v="99", "Google Chrome";v="{random.randint(120, 131)}", "Chromium";v="{random.randint(120, 131)}"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": random.choice(platforms),
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
        }

    def setup_browser(self, proxy=None, retry_count=0):
       """Initialize Playwright browser with optional proxy and adaptive settings."""
       try:
           self.playwright = sync_playwright().start()
          
           # Get dynamic user agent for this retry
           current_user_agent = self.get_next_user_agent()
          
           # Browser launch options with dynamic user agent
           launch_options = {
               "headless": True,
               "args": [
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
                   '--disable-ipc-flooding-protection',
                   '--disable-blink-features=AutomationControlled',
                   '--exclude-switches=enable-automation',
                   '--disable-client-side-phishing-detection',
                   '--disable-sync',
                   '--metrics-recording-only',
                   '--no-report-upload',
                   '--disable-features=TranslateUI',
                   '--disable-features=BlinkGenPropertyTrees',
                   '--disable-features=VizDisplayCompositor',
                   f'--user-agent={current_user_agent}'
               ]
           }
          
           # Add proxy if provided
           if proxy:
               launch_options["proxy"] = {"server": proxy}
               logging.info(f"Using proxy: {proxy}")
          
           logging.info(f"Using User Agent (attempt {retry_count + 1}): {current_user_agent[:80]}...")
          
           self.browser = self.playwright.chromium.launch(**launch_options)
          
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

    def check_movie_availability(self, retry_count=0) -> bool:
        """Check if the target movie is available on BookMyShow."""
        proxy_list = [
            None,  # No proxy first
            # Add your proxy servers here if available
            # "http://proxy1:port",
            # "http://proxy2:port",
        ]
        
        proxy = proxy_list[retry_count % len(proxy_list)] if retry_count < len(proxy_list) else None
        
        if not self.setup_browser(proxy, retry_count):
            return False
            
        try:
            # Create new page with realistic settings
            page = self.browser.new_page()
            
            # Set dynamic viewport size
            viewport = self.get_next_viewport()
            page.set_viewport_size(viewport)
            logging.info(f"Using viewport: {viewport['width']}x{viewport['height']}")
            
            # Enhanced stealth JavaScript to hide automation
            page.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                        {name: 'Native Client', filename: 'internal-nacl-plugin'}
                    ],
                });
                
                // Set realistic language preferences
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Mock chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Mock permissions
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({state: 'granted'})
                    }),
                });
                
                // Override getContext to hide canvas fingerprinting
                const getContext = HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext = function(type) {
                    if (type === '2d') {
                        const context = getContext.apply(this, arguments);
                        const getImageData = context.getImageData;
                        context.getImageData = function() {
                            const imageData = getImageData.apply(this, arguments);
                            for (let i = 0; i < imageData.data.length; i += 4) {
                                imageData.data[i] += Math.floor(Math.random() * 10) - 5;
                                imageData.data[i + 1] += Math.floor(Math.random() * 10) - 5;
                                imageData.data[i + 2] += Math.floor(Math.random() * 10) - 5;
                            }
                            return imageData;
                        };
                        return context;
                    }
                    return getContext.apply(this, arguments);
                };
                
                // Mock battery API
                Object.defineProperty(navigator, 'getBattery', {
                    get: () => () => Promise.resolve({
                        charging: true,
                        chargingTime: Infinity,
                        dischargingTime: Infinity,
                        level: 1
                    }),
                });
            """)
            
            # Set randomized headers
            page.set_extra_http_headers(self.get_random_headers())
            
            logging.info(f"Checking movie availability at {self.config['url']}")

            # Adaptive timing based on retry count (more human-like on retries)
            base_delay_multiplier = 1 + (retry_count * 0.5) # Slower on retries
            
            # Simulate human-like mouse movement before navigation
            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            page.wait_for_timeout(int(random.randint(500, 1500) * base_delay_multiplier))
            
            # Navigate with realistic timing
            page.goto(self.config["url"], wait_until="domcontentloaded", timeout=60000)
            
            # Human-like behavior: random scrolling and mouse movements (more on retries)
            page.wait_for_timeout(int(random.randint(2000, 4000) * base_delay_multiplier))
            
            # More realistic mouse behavior patterns on retries
            if retry_count > 0:
                # Simulate reading behavior - scroll and pause
                for _ in range(random.randint(2, 4)):
                    page.mouse.wheel(0, random.randint(50, 200))
                    page.wait_for_timeout(random.randint(800, 2000))
                
                # Random mouse movements like a real user browsing
                for _ in range(random.randint(3, 6)):
                    viewport_width = viewport["width"]
                    viewport_height = viewport["height"]
                    page.mouse.move(
                        random.randint(100, viewport_width - 100),
                        random.randint(100, viewport_height - 100)
                    )
                    page.wait_for_timeout(random.randint(200, 600))
            else:
                # Standard behavior for first attempt
                page.mouse.wheel(0, random.randint(100, 400))
                page.wait_for_timeout(random.randint(1000, 2000))
                
                for _ in range(random.randint(2, 4)):
                    page.mouse.move(random.randint(100, 1800), random.randint(100, 1000))
                    page.wait_for_timeout(random.randint(300, 800))
            
            # Wait for content to load with adaptive timing
            page.wait_for_timeout(int(random.randint(3000, 6000) * base_delay_multiplier))
            
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
            # If we get blocked, try with different approach
            if "cloudflare" in str(e).lower() or "blocked" in str(e).lower():
                logging.warning("Potential Cloudflare block detected, will retry with different strategy")
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

    def send_telegram_notification(self):
        """Send Telegram bot notification."""
        if not self.config["telegram"]["enabled"]:
            return
            
        try:
            bot_token = self.config["telegram"]["bot_token"]
            chat_id = self.config["telegram"]["chat_id"]
            
            if not bot_token or not chat_id:
                logging.warning("Telegram configuration incomplete - skipping Telegram notification")
                return
            
            import requests
            
            message = f"""🎬 *Movie Alert!*

The movie *{self.config['movie_name']}* is now available for booking on BookMyShow!

📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎫 [Book tickets here]({self.config['url']})

🤖 Movie Monitor"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logging.info("Telegram notification sent successfully")
            
        except Exception as e:
            logging.error(f"Failed to send Telegram notification: {e}")

    def notify_movie_found(self):
        """Send all configured notifications when movie is found."""
        logging.info(f"🎉 MOVIE FOUND: {self.config['movie_name']} is available!")
        
        self.send_email_notification()
        self.send_webhook_notification()
        self.send_telegram_notification()
        
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
                
                found = False
                max_retries = 3
                
                for retry in range(max_retries):
                    try:
                        result = self.check_movie_availability(retry)
                        if result is True:
                            found = True
                            break
                        elif result is False:
                            # Movie not found but page loaded successfully - no need to retry
                            break
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "cloudflare" in error_msg or "blocked" in error_msg or "timeout" in error_msg:
                            logging.warning(f"Retry {retry + 1}/{max_retries} due to blocking/timeout: {e}")
                            if retry < max_retries - 1:
                                # Wait longer between retries
                                time.sleep(random.randint(30, 90))
                        else:
                            # Other errors - don't retry
                            logging.error(f"Error checking movie: {e}")
                            break
                
                if found:
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