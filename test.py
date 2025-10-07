# bread_scraper_fixed.py
import re
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


BRANDS = [
    "Harvest Gold","Modern","Britannia","Fresho","English Oven","Kitty","Wibs","Bonn",
    "Nature's Own","Sunblest","Milk Man","American Garden","Mrs Bector's","Eggoz",
    "Horlicks","MTR","Aashirvaad","bb Royal","The Baker's Dozen","The Health Factory",
    "Protein Chef","Daily Good","Brik Oven","Naturbaked","Parle","ID","Amul","Bauli",
    "Wheafree","Gullon","Sprinng","Only Gluten Free","TWF","BakeMate","HAZEL","Pigeon",
]

BRAND_CANON = {b.lower(): b for b in BRANDS}

BREAD_TERMS = [
    "bread","loaf","bun","buns","pav","pao","toast","baguette","brioche","kulcha",
    "naan","roti","lavash","pita","sourdough","multigrain","brown bread","white bread",
]
NON_BREAD_EXCLUDE = [
    "knife","toaster","basket","crumbs","panko","spread","yeast","seasoning","flour",
    "storage box","tin","mould","pan","tray","maker","cutter","improver",
]

NUM_RE = re.compile(r"\d+(?:\.\d+)?")

PRICE_RE = re.compile(r"₹\s*([0-9][0-9,]*)(?:\.(\d{1,2}))?")
WEIGHT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(kg|g|l|ml|pc|pcs|pieces|slice|slices)\b", re.IGNORECASE)

@dataclass
class Product:
    platform: str
    product_name: str
    brand: str
    pack_display: Optional[str]
    price_rupees: Optional[float]
    qty: Optional[float]
    unit: Optional[str]
    weight_grams: Optional[float]
    url: Optional[str] = None

def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined })
        """
    })
    return driver

def is_bread_like(text: str) -> bool:
    t = (text or "").lower()
    if any(x in t for x in NON_BREAD_EXCLUDE):
        return False
    return any(term in t for term in BREAD_TERMS)

def clean_name_lines(block: str) -> str:
    lines = [ln.strip() for ln in (block or "").split("\n") if ln.strip()]
    cleaned = []
    for ln in lines:
        low = ln.lower()
        if low == "add" or low.startswith("save") or "premium" in low:
            continue
        if "₹" in ln:
            continue
        if re.fullmatch(r"\d+(\.\d+)?k?", low):
            continue
        if "%" in ln or ("(" in ln and ")" in ln):
            continue
        if len(ln) < 4:
            continue
        cleaned.append(ln)
    for ln in cleaned:
        if is_bread_like(ln):
            return ln
    return max(cleaned, key=len) if cleaned else ""

def parse_price(text: str):
    if not text:
        return None
    m = PRICE_RE.search(text.replace(",", ""))
    if not m:
        return None
    whole = m.group(1)
    frac = m.group(2) or "00"
    try:
        return float(f"{whole}.{frac}")
    except:
        return float(whole) if whole.isdigit() else None

def parse_pack(text: str):
    if not text:
        return None, None, None, None
    pack_display = None
    qty = None
    unit = None
    grams = None
    # canonical display
    m = WEIGHT_RE.search(text)
    if m:
        val = float(m.group(1))
        u = m.group(2).lower()
        pack_display = f"{int(val) if val.is_integer() else val} {u}"
        if u == "kg":
            grams = val * 1000
        elif u == "g":
            grams = val
        elif u in ["pc","pcs","pieces"]:
            qty = val
            unit = "pcs"
        elif u in ["slice","slices"]:
            qty = val
            unit = "slices"
    # patterns like "180 g X 2"
    x_match = re.search(r"(\d+(?:\.\d+)?)\s*g\s*[xX]\s*(\d+)", text)
    if x_match:
        per = float(x_match.group(1)); count = float(x_match.group(2))
        grams = per * count
        pack_display = f"{int(per) if per.is_integer() else per} g x {int(count)}"
    return pack_display, qty, unit, grams

def extract_brand(name: str) -> str:
    n = (name or "").strip()
    parts = n.split()
    first_two = " ".join(parts[:2]).lower()
    first_three = " ".join(parts[:3]).lower()
    for key in [first_three, first_two, (parts[0].lower() if parts else "")]:
        if key in BRAND_CANON:
            return BRAND_CANON[key]
    low = n.lower()
    for b in BRAND_CANON:
        if b in low:
            return BRAND_CANON[b]
    if parts and parts[0].lower() not in ["add","save","premium","filters","the"]:
        return parts[0].capitalize()
    return "Unknown"

def normalize_record(platform: str, name: str, block_text: str, href: Optional[str]) -> Optional[Product]:
    pname = clean_name_lines(name or block_text)
    if not pname:
        return None
    if not is_bread_like(pname):
        return None
    brand = extract_brand(pname)
    pack_display, qty, unit, grams = parse_pack(f"{name}\n{block_text}")
    price = parse_price(block_text) or parse_price(name)

    # Try to preserve a readable pack string
    pack_match = re.search(r"(\d+\s*(?:g|kg|ml|l)|\d+\s*(?:pc|pcs|pieces|slice|slices)|\d+\s*g\s*[xX]\s*\d+)", f"{name} {block_text}", re.IGNORECASE)
    if pack_match:
        pack_display = pack_match.group(1)

    return Product(
        platform=platform,
        product_name=pname,
        brand=brand,
        pack_display=pack_display,
        price_rupees=price,
        qty=qty,
        unit=unit,
        weight_grams=grams,
        url=href,
    )

class BreadScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.results: List[Product] = []

    def wait_dom(self, driver, timeout=15):
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")

    def scroll(self, driver, rounds=4, pause=0.8):
        last_h = 0
        for _ in range(rounds):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            h = driver.execute_script("return document.body.scrollHeight;")
            if h == last_h:
                break
            last_h = h
    
    def _dedupe(self, items):
        seen = set(); out = []
        for p in items:
            key = (p["platform"], p["product_name"].lower(), (p["brand"] or "").lower(), int(p["weight_grams"] or 0))
            if key in seen:
                continue
            seen.add(key); out.append(p)
        return out

    def scrape_zepto(self, url="https://www.zeptonow.com/search?query=bread") -> List[Product]:
        out: List[Product] = []
        driver = None
        try:
            driver = setup_driver(self.headless)
            driver.get("https://www.zeptonow.com/")
            time.sleep(3)
            # try location
            try:
                loc = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder,'location') or contains(@placeholder,'address')]"))
                )
                loc.clear()
                loc.send_keys("Connaught Place, New Delhi, Delhi 110001")
                time.sleep(2)
                try:
                    WebDriverWait(driver,5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'suggestion')]//div[1]"))
                    ).click()
                except:
                    from selenium.webdriver.common.keys import Keys
                    loc.send_keys(Keys.RETURN)
                time.sleep(2)
            except:
                pass

            driver.get(url)
            self.wait_dom(driver, 20)
            self.scroll(driver, 6, 1.0)

            containers = []
            for xp in [
                "//div[contains(@class,'styles_container') and .//img[@alt]]",
                "//a[contains(@href,'/pn/')]",
                "//div[contains(@class,'product-card')]",
            ]:
                try:
                    containers.extend(driver.find_elements(By.XPATH, xp))
                    if len(containers) > 60:
                        break
                except:
                    continue

            seen_keys = set()
            for c in containers[:120]:
                try:
                    txt = (c.text or "").strip()
                    if len(txt) < 8:
                        continue
                    try:
                        a = c.find_element(By.XPATH, ".//a[contains(@href,'/pn/')]")
                        href = a.get_attribute("href")
                    except:
                        href = None
                    # prefer image alt as name; fallback to cleaned text
                    name = ""
                    try:
                        img = c.find_element(By.XPATH, ".//img[@alt]")
                        name = img.get_attribute("alt") or ""
                    except:
                        pass
                    if not name:
                        name = clean_name_lines(txt)
                    prod = normalize_record("Zepto", name, txt, href)
                    if not prod:
                        continue
                    key = (prod.product_name.lower(), prod.brand.lower(), int(prod.weight_grams) if prod.weight_grams else 0)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    out.append(prod)
                    if len(out) >= 80:
                        break
                except:
                    continue
            return out
        finally:
            if driver:
                driver.quit()

    def scrape_jiomart(self, url="https://www.jiomart.com/search/bread") -> List[Product]:
        out: List[Product] = []
        driver = None
        try:
            driver = setup_driver(self.headless)
            driver.get(url)
            time.sleep(2)
            self.wait_dom(driver, 20)
            self.scroll(driver, 4, 0.8)
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[id*='product'], .product-tile, .ais-InfiniteHits-item"))
            )
            tiles = driver.find_elements(By.CSS_SELECTOR, "[id*='product'], .product-tile, .ais-InfiniteHits-item")
            seen = set()
            for t in tiles[:120]:
                try:
                    block = (t.text or "").strip()
                    if not block:
                        continue
                    # name
                    try:
                        name = t.find_element(By.CSS_SELECTOR, ".product-name, .jm-body-xs, [class*='title']").text.strip()
                    except:
                        name = clean_name_lines(block)
                    if not name:
                        continue
                    # filter accessories
                    if not is_bread_like(name):
                        continue
                    # url
                    try:
                        href = t.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    except:
                        href = None
                    prod = normalize_record("JioMart", name, block, href)
                    if not prod:
                        continue
                    key = (prod.product_name.lower(), prod.brand.lower(), int(prod.weight_grams) if prod.weight_grams else 0)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(prod)
                    if len(out) >= 80:
                        break
                except:
                    continue
            return out
        finally:
            if driver:
                driver.quit()

    def scrape_amazon_fresh(self, url="https://www.amazon.in/s?k=bread&i=fresh&rh=n%3A21862203031") -> List[Product]:
        out: List[Product] = []
        driver = None
        try:
            driver = setup_driver(self.headless)
            driver.get(url)
            time.sleep(2)
            self.wait_dom(driver, 20)
            self.scroll(driver, 4, 0.8)
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
            )
            tiles = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
            seen = set()
            for t in tiles[:120]:
                try:
                    try:
                        name = t.find_element(By.CSS_SELECTOR, "h2 a span, .a-text-normal").text.strip()
                    except:
                        name = (t.text or "").strip()
                    if not name or not is_bread_like(name):
                        continue
                    # block & price
                    block = (t.text or "").strip()
                    # prefer offscreen price
                    price_txt = ""
                    off = t.find_elements(By.CSS_SELECTOR, ".a-price .a-offscreen")
                    if off:
                        price_txt = off[0].get_attribute("innerText")
                    else:
                        whole = t.find_elements(By.CSS_SELECTOR, ".a-price-whole")
                        frac = t.find_elements(By.CSS_SELECTOR, ".a-price-fraction")
                        if whole:
                            price_txt = f"₹{whole[0].text}.{frac[0].text if frac else '00'}"
                    try:
                        href = t.find_element(By.CSS_SELECTOR, "h2 a").get_attribute("href")
                    except:
                        href = None
                    prod = normalize_record("Amazon Fresh", name, f"{block}\n{price_txt}", href)
                    if not prod:
                        continue
                    key = (prod.product_name.lower(), prod.brand.lower(), int(prod.weight_grams) if prod.weight_grams else 0)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(prod)
                    if len(out) >= 80:
                        break
                except:
                    continue
            return out
        finally:
            if driver:
                driver.quit()

    def scrape_all(self) -> List[Product]:
        results = []
        results.extend(self.scrape_zepto())
        results.extend(self.scrape_jiomart())
        results.extend(self.scrape_amazon_fresh())
        self.results = results
        return results

    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame([asdict(p) for p in self.results])
        # order columns
        cols = ["platform","product_name","brand","pack_display","price_rupees","qty","unit","weight_grams","url"]
        return df[cols]

    def save_csv(self, filename="bread_products_clean.csv"):
        if not self.results:
            print("No data to save.")
            return
        os.makedirs("data", exist_ok=True)
        import pandas as pd
        df = pd.DataFrame(self.results)
        cols = ["platform","product_name","brand","pack_display","price_rupees","qty","unit","weight_grams","url"]
        for c in cols:
            if c not in df.columns:
                df[c] = None
        df = df[cols]
        df.to_csv(f"data/{filename}", index=False)


    def summarize(self):
        df = self.to_dataframe() if self.results else pd.DataFrame()
        if df.empty:
            print("No products scraped.")
            return
        print("Counts by platform:")
        print(df.groupby("platform")["product_name"].count().to_string())
        print("\nSample:")
        print(df.head(15).to_string(index=False))


if __name__ == "__main__":
    scraper = BreadScraper(headless=True)
    scraper.scrape_all()
    scraper.summarize()
    scraper.save_csv()
