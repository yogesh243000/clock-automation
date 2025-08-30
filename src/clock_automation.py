import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import subprocess
import tempfile
import zipfile
import requests
import stat

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ClockAutomation:
    def __init__(self):
        self.username = os.getenv('CLOCK_USERNAME', 'E00358@ocs')
        self.password = os.getenv('CLOCK_PASSWORD', 'E00358@ocs')
        self.login_url = "https://clocklive.emplive.net/Account/LogOn"
        
    def setup_driver(self):
        """Setup Chrome driver for Apple Silicon Mac"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # First try webdriver-manager
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("✅ Driver setup with webdriver-manager successful")
                return driver
            except Exception as wdm_error:
                logger.warning(f"⚠️ webdriver-manager failed: {wdm_error}")
                logger.info("🔄 Trying manual driver setup...")
            
            # Manual driver setup for Apple Silicon
            # Get Chrome version
            try:
                chrome_version_output = subprocess.run(
                    ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                    capture_output=True, text=True, timeout=10
                )
                chrome_version = chrome_version_output.stdout.strip().split()[-1]
                logger.info(f"🔍 Chrome version: {chrome_version}")
            except:
                chrome_version = "139.0.7258.139"  # Fallback version
                logger.info(f"⚠️ Using fallback Chrome version: {chrome_version}")
            
            # Download the correct ARM driver
            driver_url = f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/mac-arm64/chromedriver-mac-arm64.zip"
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_path = os.path.join(tmp_dir, "chromedriver.zip")
                
                # Download driver
                logger.info(f"📥 Downloading ChromeDriver from: {driver_url}")
                response = requests.get(driver_url, timeout=30)
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Extract
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmp_dir)
                
                # Find chromedriver executable
                chromedriver_path = None
                for root, dirs, files in os.walk(tmp_dir):
                    if 'chromedriver' in files:
                        chromedriver_path = os.path.join(root, 'chromedriver')
                        break
                    for file in files:
                        if file.startswith('chromedriver'):
                            chromedriver_path = os.path.join(root, file)
                            break
                
                if chromedriver_path and os.path.exists(chromedriver_path):
                    # Make executable
                    os.chmod(chromedriver_path, stat.S_IRWXU)
                    
                    # Use the downloaded driver
                    service = Service(executable_path=chromedriver_path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("✅ Manual driver setup successful")
                    return driver
                else:
                    raise Exception("Could not find chromedriver in downloaded package")
            
        except Exception as e:
            logger.error(f"❌ All driver setup methods failed: {e}")
            
            # Final fallback: try system chromedriver if available
            try:
                logger.info("🔄 Trying system chromedriver...")
                service = Service(executable_path='/usr/local/bin/chromedriver')
                driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("✅ System chromedriver worked!")
                return driver
            except:
                logger.error("❌ System chromedriver also failed")
                return None
    
    def login(self, driver):
        """Login to the system"""
        try:
            logger.info("🌐 Navigating to login page...")
            driver.get(self.login_url)
            time.sleep(3)
            
            # Take screenshot for debugging
            driver.save_screenshot("login_page.png")
            logger.info("📸 Screenshot saved: login_page.png")
            
            # Enter credentials
            logger.info("🔐 Entering credentials...")
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "Username"))
            )
            password_field = driver.find_element(By.ID, "Password")
            login_btn = driver.find_element(By.CSS_SELECTOR, "[type='submit']")
            
            username_field.clear()
            username_field.send_keys(self.username)
            logger.info("✅ Username entered")
            
            password_field.clear()
            password_field.send_keys(self.password)
            logger.info("✅ Password entered")
            
            login_btn.click()
            logger.info("✅ Login button clicked")
            
            # Wait for login to complete
            time.sleep(3)
            
            # Take screenshot after login
            driver.save_screenshot("after_login.png")
            logger.info("📸 Screenshot saved: after_login.png")
            
            # Check login success
            current_url = driver.current_url
            if "login" in current_url.lower() or "logon" in current_url.lower():
                logger.error("❌ Login failed - still on login page")
                return False
                
            logger.info("🎉 Login successful!")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            # Take screenshot on error
            try:
                driver.save_screenshot("login_error.png")
                logger.info("📸 Screenshot saved: login_error.png")
            except:
                pass
            return False
    
    def perform_clock_operation(self, operation_type):
        """Perform clock in/out operation"""
        logger.info(f"🚀 Starting {operation_type.upper()} operation")
        
        driver = self.setup_driver()
        if not driver:
            logger.error("❌ Failed to setup Chrome driver")
            return False
            
        try:
            if not self.login(driver):
                return False
            
            # Find and click clock button
            logger.info(f"⏰ Looking for {operation_type} button...")
            
            if operation_type.lower() == "in":
                selectors = [
                    "input[value*='Clock In']",
                    "input[value*='clock in']",
                    "#clock-in-button",
                    "#btnClockIn",
                    "button[value*='Clock In']",
                    "button[onclick*='clockIn']"
                ]
            else:
                selectors = [
                    "input[value*='Clock Out']", 
                    "input[value*='clock out']",
                    "#clock-out-button",
                    "#btnClockOut",
                    "button[value*='Clock Out']",
                    "button[onclick*='clockOut']"
                ]
            
            # Try each selector
            button_found = False
            for selector in selectors:
                try:
                    clock_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if clock_btn.is_displayed():
                        logger.info(f"✅ Found {operation_type} button using: {selector}")
                        clock_btn.click()
                        logger.info(f"✅ {operation_type.capitalize()} button clicked")
                        button_found = True
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not button_found:
                logger.error(f"❌ Could not find {operation_type} button")
                # Take screenshot to see what's on the page
                driver.save_screenshot("button_not_found.png")
                logger.info("📸 Screenshot saved: button_not_found.png")
                return False
            
            # Wait for operation to complete
            time.sleep(3)
            
            # Take final screenshot
            driver.save_screenshot("after_operation.png")
            logger.info("📸 Screenshot saved: after_operation.png")
            
            logger.info(f"🎉 {operation_type.upper()} completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"💥 Operation failed: {e}")
            # Take screenshot on error
            try:
                driver.save_screenshot("operation_error.png")
                logger.info("📸 Screenshot saved: operation_error.png")
            except:
                pass
            return False
        finally:
            try:
                driver.quit()
                logger.info("✅ Browser closed")
            except:
                pass

def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clock Automation')
    parser.add_argument('operation', choices=['in', 'out'], help='Clock in or out')
    parser.add_argument('--env', '-e', default='.env', help='Environment file path')
    parser.add_argument('--dry-run', action='store_true', help='Test without actually clicking')
    
    args = parser.parse_args()
    
    # Load environment variables from specified file
    if os.path.exists(args.env):
        load_dotenv(args.env)
    
    if args.dry_run:
        logger.info("🧪 DRY RUN MODE - No actual operations will be performed")
    
    automation = ClockAutomation()
    
    if args.dry_run:
        # Just test driver setup and login
        driver = automation.setup_driver()
        if driver:
            logger.info("✅ Driver setup successful in dry-run mode")
            success = automation.login(driver)
            if success:
                logger.info("✅ Login successful in dry-run mode")
            driver.quit()
        return 0
    
    success = automation.perform_clock_operation(args.operation)
    
    if success:
        print("✅ Operation completed successfully!")
        return 0
    else:
        print("❌ Operation failed!")
        return 1

if __name__ == "__main__":
    exit(main())