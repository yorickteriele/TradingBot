from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time

site = "https://www.google.nl/alerts"
driver = uc.Chrome()

driver.get(site)

sign_in_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, "//a[@class='gb_Ta gb_yd gb_pd gb_gd']"))
)
sign_in_button.click()

print("Please log in manually. The script will continue after 60 seconds...")
time.sleep(15)

print("Logged into Google Alerts successfully.")


def create_alert_for_company(company_name):

    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@class='label-input-label']"))
    )
    search_box.clear()
    search_box.send_keys(company_name)

    other_options = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[@class='show_options']"))
    )
    other_options.click()

    frequency_dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='goog-inline-block goog-flat-menu-button-caption' and @id=':3']"))
    )
    frequency_dropdown.click()

    actions = ActionChains(driver)
    actions.move_to_element(frequency_dropdown)
    actions.move_by_offset(0, -20)
    actions.click()
    actions.perform()

    language_dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='goog-inline-block goog-flat-menu-button-caption' and @id=':1t']"))
    )
    language_dropdown.click()

    actions = ActionChains(driver)
    actions.move_to_element(language_dropdown)
    actions.move_by_offset(0, 310)
    actions.click()
    actions.perform()

    amount_dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='goog-inline-block goog-flat-menu-button-caption' and @id=':6']"))
    )
    amount_dropdown.click()

    actions = ActionChains(driver)
    actions.move_to_element(amount_dropdown)
    actions.move_by_offset(0, 20)
    actions.click()
    actions.perform()

    delivery_dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='goog-inline-block goog-flat-menu-button-caption' and @id=':8m']"))
    )
    delivery_dropdown.click()

    actions = ActionChains(driver)
    actions.move_to_element(delivery_dropdown)
    actions.move_by_offset(0, 20)
    actions.click()
    actions.perform()

    create_alert_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[@id='create_alert']"))
    )
    create_alert_button.click()

    rss_feed_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[@class='alert_buttons']/a"))
    )
    rss_feed_url = rss_feed_element.get_attribute("href")
    return rss_feed_url


