from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
import logging
from pathlib import Path
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)


class GoogleAlertsManager:
    """Manager for creating Google Alerts with proper resource management."""
    
    def __init__(self, screenshot_dir: Optional[str] = None):
        """
        Initialize the Google Alerts Manager.
        
        Args:
            screenshot_dir: Directory to save error screenshots. Defaults to 'screenshots' in current dir.
        """
        self.driver: Optional[uc.Chrome] = None
        self.is_logged_in = False
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else Path('screenshots')
        self.screenshot_dir.mkdir(exist_ok=True)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.close()
        return False
    
    def _init_driver(self) -> uc.Chrome:
        """Initialize and return a Chrome WebDriver."""
        try:
            options = uc.ChromeOptions()
            # Add any options you need here
            # options.add_argument('--headless')  # Uncomment for headless mode
            driver = uc.Chrome(options=options)
            logger.info("WebDriver initialized successfully")
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def ensure_logged_in(self) -> bool:
        """
        Ensure user is logged in to Google Alerts.
        
        Returns:
            bool: True if logged in successfully, False otherwise.
        """
        if self.driver is None:
            self.driver = self._init_driver()
        
        # If already confirmed logged in, skip checks
        if self.is_logged_in:
            return True
        
        try:
            # Navigate to Google Alerts
            self.driver.get("https://www.google.com/alerts")
            
            try:
                sign_in_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[@id='gb']/div[2]/div[3]/div[1]/a/span"))
                )
                sign_in_button.click()
                
                # Wait for user to complete login
                print("\n" + "="*60)
                print("PLEASE LOG IN TO YOUR GOOGLE ACCOUNT IN THE BROWSER WINDOW")
                print("You have 2 minutes to complete the login...")
                print("="*60 + "\n")
                
                # Wait for the create alert input to appear, indicating successful login
                WebDriverWait(self.driver, 120).until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'label-input-label')]"))
                )
                logger.info("Successfully logged in to Google Alerts")
                self.is_logged_in = True
                return True
                
            except TimeoutException:
                logger.error("Login timeout. Please check if you completed the login process correctly.")
                return False
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
    
    def create_alert_for_company(self, company_name: str) -> Optional[str]:
        """
        Create a Google Alert for a company and return the RSS feed URL.
        
        Args:
            company_name: Name of the company to create alert for.
            
        Returns:
            str: RSS feed URL if successful, None otherwise.
        """
        if not self.ensure_logged_in():
            logger.error("Failed to log in to Google Alerts")
            return None
        
        try:
            # Navigate to Google Alerts
            self.driver.get("https://www.google.com/alerts")
            time.sleep(1)  # Small delay to ensure page loads
            
            # Wait for and fill in the search term
            search_box = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Create an alert about...')]"))
            )
            search_box.clear()
            search_box.send_keys(company_name)
            time.sleep(0.5)
            
            # Try to click 'Show options' to expand the options
            try:
                show_options = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Show options')]"))
                )
                show_options.click()
                time.sleep(1)
                 
                # Set amount to 'All results'
                self._set_dropdown_option('volume_select', 'All results')

                # Set delivery method to RSS feed
                self._set_delivery_to_rss()
                
            except TimeoutException:
                logger.warning("Could not find 'Show options' button, using default settings")
            
            # Click create alert button
            create_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='create_alert']")
                )
            )
            create_button.click()
            time.sleep(3)  # Wait for alert to be created and page to update
            
            # Find the first alert instance (the newly created one)
            # and get the RSS link from within that specific alert
            try:
                first_alert = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//li[@class='alert_instance'][1]"))
                )
                
                # Look for RSS link within the first alert
                rss_link = first_alert.find_element(By.XPATH, ".//a[contains(@href, '/alerts/feeds/')]")
                rss_feed_url = rss_link.get_attribute("href")
                
                logger.info(f"Successfully created alert for {company_name}")
                logger.info(f"RSS URL: {rss_feed_url}")
                return rss_feed_url
                
            except NoSuchElementException:
                logger.error(f"No RSS feed link found in the newly created alert for {company_name}")
                logger.error("The alert may not have been created with RSS delivery enabled")
                return None
            
        except Exception as e:
            logger.error(f"Error creating alert for {company_name}: {e}")
            # Take a screenshot for debugging
            try:
                screenshot_path = self.screenshot_dir / f"error_{company_name.replace(' ', '_').replace('/', '_')[:50]}.png"
                self.driver.save_screenshot(str(screenshot_path))
                logger.info(f"Screenshot saved to {screenshot_path}")
            except Exception as screenshot_error:
                logger.warning(f"Could not save screenshot: {screenshot_error}")
            return None
    
    def _set_dropdown_option(self, dropdown_class: str, option_text: str) -> bool:
        """
        Helper method to set a dropdown option.
        
        Args:
            dropdown_class: Class name of the dropdown (e.g., 'frequency_select', 'language_select', 'volume_select').
            option_text: Text of the option to select.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Find and click the dropdown button using the specific class
            dropdown = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'goog-flat-menu-button') and contains(@class, '{dropdown_class}')]"))
            )
            dropdown.click()
            time.sleep(0.5)
            
            # Select the option from the menu
            option = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'goog-menuitem') and contains(text(), '{option_text}')]"))
            )
            option.click()
            time.sleep(0.5)
            logger.info(f"Set {dropdown_class} to '{option_text}'")
            return True
        except Exception as e:
            logger.debug(f"Could not set {dropdown_class} to '{option_text}': {e}")
            return False
    
    def _set_delivery_to_rss(self) -> bool:
        """
        Set delivery to RSS feed using the delivery_select div.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Find the dropdown inside the delivery_select div
            dropdown = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@class='delivery_select']//div[contains(@class, 'goog-flat-menu-button')]"))
            )
            dropdown.click()
            time.sleep(0.5)
            
            # Select RSS feed option from the menu
            rss_option = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'goog-menuitem') and contains(text(), 'RSS feed')]"))
            )
            rss_option.click()
            time.sleep(0.5)
            logger.info("Set delivery to 'RSS feed'")
            return True
        except Exception as e:
            logger.warning(f"Could not set delivery to RSS feed: {e}")
            return False
    
    def close(self):
        """Close the WebDriver and clean up resources."""
        if self.driver is not None:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
                self.is_logged_in = False


# Convenience function for backward compatibility
def create_alert_for_company(company_name: str, manager: Optional[GoogleAlertsManager] = None) -> Optional[str]:
    """
    Create a Google Alert for a company (backward compatible function).
    
    Args:
        company_name: Name of the company.
        manager: Optional GoogleAlertsManager instance. If None, creates a new one.
        
    Returns:
        str: RSS feed URL if successful, None otherwise.
    """
    if manager:
        return manager.create_alert_for_company(company_name)
    else:
        # Create a temporary manager (not recommended for multiple alerts)
        with GoogleAlertsManager() as mgr:
            return mgr.create_alert_for_company(company_name)


