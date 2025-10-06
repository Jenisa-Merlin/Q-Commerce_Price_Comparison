# main scraper
import pandas as pd
from typing import List, Dict
import time 
import re
import os 

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# constants
common_brands = [
    'Harvest Gold', 'Modern', 'Britannia', 'Fresho', 
    'English Oven', 'Kitty', 'Wibs', 'Bonn', 'Nature\'s Own',
    'Sunblest', 'Milk Man', 'American Garden', 'Mrs Bector\'s',
    'Eggoz', 'Horlicks', 'MTR', 'Aashirvaad', 'bb Royal'
]

class BreadScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.results = []
        self.blinkit = []
        self.jiomart = []
        self.amazon_fresh = []

    # setup driver
    def setup_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        # viewport
        options.add_argument("--window-size=1920,1080")
        # language
        options.add_argument("--lang=en-US")
        # flags
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # reduce automation fingerprint
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # user agent
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=options)
        # remove navigator.webdriver
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
              """
        })
        return driver

    def wait_dom_ready(self, driver, timeout=10):
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )

    def scroll_hydrate(self, driver, rounds=5, pause=1.0):
        last_h = 0
        for _ in range(rounds):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            h = driver.execute_script("return document.body.scrollHeight;")
            if h == last_h:
                break
            last_h = h

    def extract_weight_from_name(self, name: str) -> str:
        match = re.search(r'\b\d+(\.\d+)?\s*(g|kg|ml|l|pcs|pc|pieces|slice|slices|loaf|loaves)\b', name, re.IGNORECASE)
        if match:
            return match.group(0)
        return "N/A"
    
    def extract_brand_from_name(self, name: str) -> str:
        for brand in common_brands:
            if brand.lower() in name.lower():
                return brand
        return name.split()[0] if name else "Unknown"
    
    # scrape blinkit
    def scrape_blinkit(self, url=None) -> List[Dict]:
        url = url or "https://blinkit.com/s/?q=bread"
        products = []
        driver = None 
        try:
            driver = self.setup_driver()
            driver.get(url)

            time.sleep(2)  # initial wait

            # basic page readiness
            self.wait_dom_ready(driver, 30)

            # hydrate and wait for products to load
            self.scroll_hydrate(driver, rounds=6, pause=0.8)

            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//div[contains(@class, 'categories-table')]")
                )
            )

            # pull product elements
            tiles = driver.find_elements(By.XPATH, "//div[contains(@class, 'categories-table')]//div/div")

            # scroll a bit more if no tiles found
            if not tiles:
                self.scroll_hydrate(driver, rounds=4, pause=0.8)
                tiles = driver.find_elements(By.XPATH, "//div[contains(@class, 'categories-table')]//div/div")

            for tile in tiles[:60]:  # limit to first 60 products
                try:
                    text = (tile.text or "").strip()
                    if not text:
                        continue

                    if "ADD" not in text and "Add" not in text:
                        if "₹" not in text:
                            continue

                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    
                    name = ""
                    price = "N/A"
                    weight = "N/A"

                    for line in lines:
                        if not name and "₹" not in line and not any(k in line for k in ["min", "mins", "delivery", "rating"]):
                            name = line
                            continue
                        if weight == "N/A" and re.search(r'\b\d+(\.\d+)?\s*(g|kg|ml|l|pcs|pc|pieces|slice|slices|loaf|loaves)\b', line, re.IGNORECASE):
                            weight = line
                        if price == "N/A" and "₹" in line:
                            price = " ".join(line.split())

                    if not name:
                        try:
                            name_el = tile.find_element(By.CSS_SELECTOR, "[data-testid='product-title'], h3, h2, [class*='title']")
                            name = (name_el.text or "").strip()
                        except Exception:
                            pass
                    
                    if weight == "N/A":
                        weight = self.extract_weight_from_name(name)

                    if not name:
                        continue

                    products.append({
                        "platform": "Blinkit",
                        "product_name": name,
                        "brand": self.extract_brand_from_name(name),
                        "weight": weight,
                        "price": price,
                    })
                except Exception:
                    continue

            return products
        finally:
            if driver:
                driver.quit()

    # scrape jiomart
    def scrape_jiomart(self, url=None) -> List[Dict]:
        url = url or "https://www.jiomart.com/search/bread"
        products = []
        driver = None
        try:
            driver = self.setup_driver()
            driver.get(url)

            time.sleep(2) # initial wait

            # basic page readiness
            self.wait_dom_ready(driver, 30)

            # hydrate and wait for products to load (in case of lazy loading)
            self.scroll_hydrate(driver, rounds=3, pause=0.8)

            # wait for product tiles to appear
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, '[id*="product"], .product-tile, .ais-InfiniteHits-item')
                )
            )

            # pull product elements
            tiles = driver.find_elements(By.CSS_SELECTOR, '[id*="product"], .product-tile, .ais-InfiniteHits-item')

            # scroll a bit more if no tiles found
            if not tiles:
                self.scroll_hydrate(driver, rounds=4, pause=0.8)
                tiles = driver.find_elements(By.CSS_SELECTOR, '[id*="product"], .product-tile, .ais-InfiniteHits-item')

            for tile in tiles[:60]:  # limit to first 60 products
                try:
                    name_elem = tile.find_element(By.CSS_SELECTOR, '.product-name, .jm-body-xs, [class*="title"]')
                    name = (name_elem.text or "").strip()

                    price_elem = tile.find_element(By.CSS_SELECTOR, '[class*="price"], .final-price, .jm-heading-xxs')
                    price = (price_elem.text or "").strip()
                    
                    try:
                        weight_elem = tile.find_element(By.CSS_SELECTOR, '[class*="weight"], .pack-size')
                        weight = (weight_elem.text or "").strip()
                    except Exception:
                        weight = self.extract_weight_from_name(name)

                    if name:
                        products.append({
                            "platform": "JioMart",
                            "product_name": name,
                            "brand": self.extract_brand_from_name(name),
                            "weight": weight,
                            "price": price,
                        })
                except Exception:
                    continue
            return products
        finally:
            if driver:
                driver.quit()

    # scrape amazon fresh
    def scrape_amazon_fresh(self, url=None) -> List[Dict]:
        url = url or "https://www.amazon.in/s?k=bread&i=fresh&rh=n%3A21862203031"
        products = []
        driver = None
        try:
            driver = self.setup_driver()
            driver.get(url)

            time.sleep(2)  # initial wait

            # basic page readiness
            self.wait_dom_ready(driver, 30)

            # hydrate and wait for products to load (in case of lazy loading)
            self.scroll_hydrate(driver, rounds=3, pause=0.8)

            # wait for product tiles to appear
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, '.s-result-item, [data-component-type="s-search-result"]')
                )
            )

            # pull product elements
            tiles = driver.find_elements(By.CSS_SELECTOR, '[data-component-type="s-search-result"]')

            # scroll a bit more if no tiles found
            if not tiles:
                self.scroll_hydrate(driver, rounds=4, pause=0.8)
                tiles = driver.find_elements(By.CSS_SELECTOR, '.s-result-item, [data-component-type="s-search-result"]')

            for tile in tiles[:60]:  # limit to first 60 products
                try:
                    name_elem = tile.find_element(By.CSS_SELECTOR, 'h2 a span, .a-text-normal')
                    name = (name_elem.text or "").strip()

                    price_whole_elem = tile.find_elements(By.CSS_SELECTOR, '.a-price-whole')
                    price_fraction_elem = tile.find_elements(By.CSS_SELECTOR, '.a-price-fraction')
                    if price_whole_elem and price_fraction_elem and price_whole_elem[0].text.strip():
                        price = f"₹{price_whole_elem[0].text.strip()}.{price_fraction_elem[0].text.strip()}"
                    else:
                        off = tile.find_elements(By.CSS_SELECTOR, '.a-price .a-offscreen')
                        price = off[0].get_attribute('innerText').strip() if off else "N/A"

                    weight = self.extract_weight_from_name(name)

                    if name and 'bread' in name.lower():
                        products.append({
                            "platform": "Amazon Fresh",
                            "product_name": name,
                            "brand": self.extract_brand_from_name(name),
                            "weight": weight,
                            "price": price,
                        })
                except Exception:
                    continue
            return products
        finally:
            if driver:
                driver.quit()

    def scrape_all(self):
        print("Scraping Blinkit...")
        print("-" * 60)

        self.blinkit = self.scrape_blinkit()
        self.results.extend(self.blinkit)

        print("\nScraping JioMart...")
        print("-" * 60)

        self.jiomart = self.scrape_jiomart()
        self.results.extend(self.jiomart)

        print("\nScraping Amazon Fresh...")
        print("-" * 60)

        self.amazon_fresh = self.scrape_amazon_fresh()
        self.results.extend(self.amazon_fresh)

        print("\nScraping completed.")
        return self.results
    
    def summarize_results(self):
        print("\nSummary of Scraped Results:")
        print("-" * 60)
        
        if not self.results:
            print("No products were scraped.")
            return
        
        print(f"Total products scraped: {len(self.results)}")

        print(f"\nProducts per platform:")
        print(f"Blinkit: {len(self.blinkit)} products")
        print(f"JioMart: {len(self.jiomart)} products") 
        print(f"Amazon Fresh: {len(self.amazon_fresh)} products")

        # convert to DataFrame
        df = pd.DataFrame(self.results)

        print("\nSample of scraped data:")
        print(df.head(15).to_string(index=False))
        print("\n" + "-" * 60)

    # save results to CSV
    def save_to_csv(self, filename="bread_products.csv"):
        if not self.results:
            print("No data to save.")
            return
        
        os.makedirs("data", exist_ok=True)
        df = pd.DataFrame(self.results)
        df.to_csv(f"data/{filename}", index=False)

if __name__ == "__main__":
    print("=" * 60)
    print("BREAD PRODUCT SCRAPER")
    print("=" * 60)

    print("\nPlatforms to scrape:")
    print("1. Blinkit")
    print("2. JioMart")
    print("3. Amazon Fresh")

    scraper = BreadScraper(headless=True) # running without visible GUI

    # scrape all platforms
    scraper.scrape_all()

    # summarize results
    scraper.summarize_results()

    # save results
    if scraper.results:
        scraper.save_to_csv("bread_products.csv")
        print("Scraped data saved to 'data/bread_products.csv'")
    else:
        print("No products were scraped; nothing to save.")