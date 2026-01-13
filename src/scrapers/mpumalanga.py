from playwright.sync_api import sync_playwright
import datetime
import os
import json

BASE_URL = "https://ehr.mpuhealth.gov.za/OnlineApp/Advert.aspx"

def run():
    print(f"Navigating to {BASE_URL}...")
    jobs = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
             user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
             ignore_https_errors=True
        )
        page = context.new_page()
        
        try:
            page.goto(BASE_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # Heuristic 1: Check the specific "No Vacancies" box
            try:
                msg_input = page.locator("#TextBox1")
                if msg_input.count() > 0:
                    text_val = msg_input.input_value()
                    print(f"Mpumalanga Status Text: {text_val}")
                    
                    if "No Vacancies advertised" in text_val:
                        print("Confirmed: No vacancies available.")
                        return [] # Return empty list, no alert needed
                    
                    # If the text box exists but says something else, that's interesting!
                    jobs.append({
                        "reference_number": "MPU-STATUS-CHANGE",
                        "title": "Mpumalanga Site Status Change",
                        "location": "Mpumalanga Online Portal",
                        "link": BASE_URL,
                        "description": f"The 'No Vacancies' text has changed to: {text_val}"
                    })
            except Exception as e:
                print(f"Error checking TextBox1: {e}")

            # Heuristic 2: Check for any grid view or new table
            # The current page has a layout table, so we need to be careful.
            # Usually ASP.NET grids have ID like 'GridView1' or class like 'grid'
            # Let's look for any link that says "View" or "Apply"
            
            links = page.locator("a:text('View'), a:text('Apply')")
            if links.count() > 0:
                 jobs.append({
                    "reference_number": "MPU-POSSIBLE-JOBS",
                    "title": "Possible Jobs Detected (Links Found)",
                    "location": "Mpumalanga Online Portal",
                    "link": BASE_URL,
                    "description": f"Found {links.count()} buttons/links that might be job listings."
                })

        except Exception as e:
            print(f"Error scraping Mpumalanga: {e}")
        finally:
            browser.close()
            
    return jobs

if __name__ == "__main__":
    found = run()
    print(f"Found {len(found)} items.")
