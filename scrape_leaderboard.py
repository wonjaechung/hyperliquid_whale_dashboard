# scrape_playwright.py
import asyncio
import pandas as pd
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://app.hyperliquid.xyz/leaderboard", timeout=60000)
        # All-time 뷰 클릭
        await page.click("div.variant_black", timeout=15000)
        await page.click("text=All-time", timeout=15000)
        # 테이블 로딩
        await page.wait_for_selector("table tr", timeout=30000)

        # 상위 30개 행 가져오기
        rows = await page.query_selector_all("table tr")
        records = []
        for row in rows[1:31]:
            cols = await row.query_selector_all("td")
            # 트레이더 이름
            trader = await cols[1].inner_text()
            # 클릭해서 지갑 주소 가져오기
            await cols[1].click()
            await page.wait_for_load_state("networkidle")
            wallet = page.url.split("/")[-1]
            await page.go_back()
            await page.wait_for_selector("table tr")

            # 나머지 컬럼들
            acct = await cols[2].inner_text()
            pnl  = await cols[3].inner_text()
            roi  = await cols[4].inner_text()
            vol  = await cols[5].inner_text()
            records.append({
                "Trader": trader,
                "Wallet": wallet,
                "Account Value": acct,
                "PNL": pnl,
                "ROI": roi,
                "Volume": vol
            })

        df = pd.DataFrame(records)
        df.to_csv("top30_wallets.csv", index=False)
        print("✅ Saved top30_wallets.csv")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
