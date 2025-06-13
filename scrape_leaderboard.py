# scrape_playwright.py

import asyncio
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        await page.goto("https://app.hyperliquid.xyz/leaderboard", wait_until="networkidle")

        # All-time 보기로 전환
        await page.wait_for_selector("div.variant_black", timeout=30000)
        await page.click("div.variant_black")
        await page.click("text=All-time")
        await page.wait_for_selector("table > tbody > tr", timeout=60000)

        # — 여기서부터 키보드로 스크롤 —
        # 페이지 전체를 여러 번 PageDown 해서 테이블의 virtualized rows를 로드
        for _ in range(20):
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(300)  # 0.3초 대기
        # — 스크롤 끝 —

        records = []
        rows_locator = page.locator("table > tbody > tr")
        count = await rows_locator.count()
        total = min(count, 30)
        print(f"🔍 총 로드된 로우: {count}, 가져올 개수: {total}")

        for i in range(total):
            row = rows_locator.nth(i)
            cols = row.locator("td")
            ccount = await cols.count()

            trader = await cols.nth(1).inner_text() if ccount > 1 else "N/A"
            acct   = await cols.nth(2).inner_text() if ccount > 2 else "N/A"
            pnl    = await cols.nth(3).inner_text() if ccount > 3 else "N/A"
            roi    = await cols.nth(4).inner_text() if ccount > 4 else "N/A"
            vol    = await cols.nth(5).inner_text() if ccount > 5 else "N/A"

            # 지갑주소 클릭 → URL 추출
            try:
                await cols.nth(1).click()
                await page.wait_for_load_state("networkidle", timeout=30000)
                wallet = page.url.split("/")[-1]
            except PlaywrightTimeoutError:
                wallet = "N/A"

            # 뒤로 가서 테이블 복귀
            await page.go_back(wait_until="networkidle", timeout=30000)
            await page.wait_for_selector("table > tbody > tr", timeout=30000)

            records.append({
                "Trader": trader,
                "Wallet": wallet,
                "Account Value": acct,
                "PNL": pnl,
                "ROI": roi,
                "Volume": vol
            })
            print(f"✅ Row {i+1}: {trader} / {wallet}")

        df = pd.DataFrame(records)
        df.to_csv("top30_wallets.csv", index=False)
        print("✅ Saved top30_wallets.csv")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
