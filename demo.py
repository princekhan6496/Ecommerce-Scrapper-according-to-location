import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime
import re

# =================================================================
#                         CONFIGURATION
# =================================================================

URL = "https://www.swiggy.com/instamart"
SEARCH_KEYWORD = "Chocolate" 

# Setting location data for both input and CSV metadata
CITY = "Mumbai"
PIN_CODE = "400001" 

# Consolidated Locators (ALL UPDATED FOR ROBUSTNESS)
LOCATORS = {
    # LOCATION FLOW LOCATORS
    "initial_location_input_class": "D4XVE", 
    "modal_input_class": "_1wkJd",
    "first_suggestion_css": ".sc-aXZVg.gPfbij",
    "confirm_button_css": ".sc-aXZVg.iwOBvp",
    
    # DIRECT SEARCH FLOW LOCATORS
    "search_icon_class": "_3BHA2", 
    "search_bar_class": "_18fRo",          
    "product_suggestion_css": ".sc-aXZVg.gctPCj._5MSn4", 
    
    # PRODUCT EXTRACTION LOCATORS (UPDATED!)
    "product_card_class": "sWdPz",
    "product_name_css": "div.sc-aXZVg.kyEzVU._1lbNR", # New locator for the name
    "price_container_class": "_2enD-", # Container for both selling and original price
    "discount_tag_testid": "item-offer-label-discount-text" # Reliable data-testid for discount
}

scraped_data = []

# =================================================================
#                         SETUP AND RUN
# =================================================================

def setup_driver():
    """Sets up and returns the Selenium WebDriver."""
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    return driver

driver = setup_driver()
wait = WebDriverWait(driver, 15) 

print(f"\n--- Starting Hybrid Scrape for: {CITY} ---")

try:
    driver.get(URL)
    time.sleep(2) 
    
    # -----------------------------------------------------------------
    # Stage 1: Setting Location 
    # -----------------------------------------------------------------
    
    # ... (Location Setting Steps 1-4 are retained and working)
    print("1. Setting Location: Clicking initial location bar.")
    initial_input_locator = (By.CLASS_NAME, LOCATORS["initial_location_input_class"])
    wait.until(EC.element_to_be_clickable(initial_input_locator)).click()
    time.sleep(1) 

    print(f"2. Setting Location: Entering City Name: {CITY}")
    modal_input_locator = (By.CLASS_NAME, LOCATORS["modal_input_class"])
    location_input = wait.until(EC.element_to_be_clickable(modal_input_locator))
    location_input.clear()
    location_input.send_keys(CITY)
    time.sleep(3) 

    print("3. Setting Location: Clicking first suggestion.")
    suggestion_locator = (By.CSS_SELECTOR, LOCATORS["first_suggestion_css"])
    wait.until(EC.element_to_be_clickable(suggestion_locator)).click()
    time.sleep(2) 
    
    print("4. Setting Location: Clicking 'Confirm Location'.")
    confirm_button_locator = (By.CSS_SELECTOR, LOCATORS["confirm_button_css"])
    wait.until(EC.element_to_be_clickable(confirm_button_locator)).click()
    time.sleep(4) 
    
    # 4.5. FIX: Dismiss the persistent banner by clicking the body
    print("4.5. Dismissing persistent banner by clicking page body...")
    try:
        driver.find_element(By.TAG_NAME, 'body').click()
        print("    - Banner dismissed successfully.")
        time.sleep(2)
    except:
        print("    - Body click failed. Proceeding anyway.") 
        pass 
        
    # -----------------------------------------------------------------
    # Stage 2: Direct Product Search 
    # -----------------------------------------------------------------
    
    # 5. Click the main search icon (Using the new _3BHA2 class)
    print("5. Searching: Clicking the search icon.")
    search_icon_locator = (By.CLASS_NAME, LOCATORS["search_icon_class"])
    wait.until(EC.element_to_be_clickable(search_icon_locator)).click()
    time.sleep(1) 

    # 6. Find the search bar that appears
    print(f"6. Searching: Typing keyword: '{SEARCH_KEYWORD}'")
    search_bar_locator = (By.CLASS_NAME, LOCATORS["search_bar_class"])
    product_input = wait.until(EC.presence_of_element_located(search_bar_locator))
    
    product_input.send_keys(SEARCH_KEYWORD)
    time.sleep(3) 

    # 7. Click the first product suggestion
    print("7. Searching: Clicking the product suggestion to see results.")
    suggestion_locator = (By.CSS_SELECTOR, LOCATORS["product_suggestion_css"])
    wait.until(EC.element_to_be_clickable(suggestion_locator)).click()
    time.sleep(6) 

    # -----------------------------------------------------------------
    # Stage 3: Data Extraction (FIXED!)
    # -----------------------------------------------------------------
    print("8. Extracting product data...")
    
    product_cards = driver.find_elements(By.CLASS_NAME, LOCATORS["product_card_class"])
    
    if not product_cards:
        print("No product cards found for this keyword.")
        raise Exception("No products found.")
        
    print(f"Found {len(product_cards)} products.")

    for rank, card in enumerate(product_cards, 1):
        try:
            # 1. Product Name (New CSS selector)
            product_name = card.find_element(By.CSS_SELECTOR, LOCATORS["product_name_css"]).text.strip()
            
            # 2. Selling Price
            # Find the price container, then the first child (which is the selling price)
            price_container = card.find_element(By.CLASS_NAME, LOCATORS["price_container_class"])
            selling_price_element = price_container.find_elements(By.TAG_NAME, 'div')[0] 
            selling_price = selling_price_element.text.strip().replace('₹', '').replace(',', '')
            
            # 3. Discount Tag 
            discount_tag = ""
            try:
                # Use the reliable data-testid
                discount_element = card.find_element(By.CSS_SELECTOR, f'div[data-testid="{LOCATORS["discount_tag_testid"]}"]')
                discount_tag = discount_element.text.strip()
            except:
                pass 

            # Append data 
            scraped_data.append({
                "City": CITY,
                "PinCode": PIN_CODE,
                "Search_Keyword": SEARCH_KEYWORD,
                "Product_Rank": rank,
                "Product_Name": product_name,
                "Selling_Price_INR": float(re.sub(r'[^\d.]', '', selling_price)),
                "Discount_Tag": discount_tag,
                "URL": driver.current_url
            })
            
        except Exception as card_e:
            # This should only skip a card if its HTML is incomplete or drastically different
            print(f"    - Error extracting data for product {rank}. Skipping.")
            continue

except Exception as general_e:
    print(f"--- General Error during scrape: {general_e} ---")
finally:
    # -----------------------------------------------------------------
    # Stage 4: Output
    # -----------------------------------------------------------------
    driver.quit() 

    if scraped_data:
        df = pd.DataFrame(scraped_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"instamart_{SEARCH_KEYWORD.lower().replace(' ', '_')}_data_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"\n✅ SUCCESS! Data saved to: {filename}")
    else:
        print("\n⚠️ FINISHED, but no data was successfully extracted.")