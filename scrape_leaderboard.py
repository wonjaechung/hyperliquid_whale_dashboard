# scrape_leaderboard.py

import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def switch_to_all_time(driver):
    dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'variant_black')]"))
    )
    dropdown.click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//div[contains(text(),'All-time')]").click()
    time.sleep(3)

def parse_top30_with_wallet(driver):
    rows = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
    )[1:31]
    data = []
    for i, row in enumerate(rows, start=1):
        cols = row.find_elements(By.TAG_NAME, "td")
        trader = cols[1].text
        cols[1].click()
        time.sleep(2)
        url = driver.current_url
        wallet = url.split("/")[-1]
        driver.back()
        time.sleep(2)
        cols = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//table//tr"))
        )[i].find_elements(By.TAG_NAME, "td")
        data.append({
            "Trader": trader,
            "Wallet": wallet,
            "Account Value": cols[2].text,
            "PNL": cols[3].text,
            "ROI": cols[4].text,
            "Volume": cols[5].text,
        })
    return pd.DataFrame(data)

def main():
    options = webdriver.ChromeOptions()
    # uncomment next line to hide the browser window
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://app.hyperliquid.xyz/leaderboard")
    switch_to_all_time(driver)
    df = parse_top30_with_wallet(driver)
    driver.quit()
    df.to_csv("top30_wallets.csv", index=False)
    print("Saved top30_wallets.csv")

if __name__ == "__main__":
    main()
