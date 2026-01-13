
from playwright.sync_api import sync_playwright

def inspect():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Standard UA
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        print("Navigating...")
        page.goto("https://www.scubedonline.co.za/recruitment_wcdh/vacancy-posting.aspx", timeout=60000)
        
        # Wait for table
        try:
            page.wait_for_selector("table#vacancyListingView", timeout=30000)
            rows = page.locator("table#vacancyListingView tr")
            count = rows.count()
            print(f"Rows found: {count}")
            if count > 0:
                # Row 0 might be header, let's look at first few
                for i in range(min(5, count)):
                    print(f"--- Row {i} ---")
                    # inner_text handles whitespace
                    text = rows.nth(i).inner_text()
                    print(text)
                    
                    # Columns
                    cols = rows.nth(i).locator("td")
                    col_count = cols.count()
                    print(f"Cols: {col_count}")
                    for j in range(col_count):
                         print(f"  Col {j}: {cols.nth(j).inner_text().strip()}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    inspect()
