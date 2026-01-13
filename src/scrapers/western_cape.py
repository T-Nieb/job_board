import json
import time
import os
import datetime
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.scubedonline.co.za/recruitment_wcdh/vacancy-posting.aspx"

def scrape_vacancy_details(page):
    """Scrapes details from the current vacancy details page."""
    details = {}
    details['job_url'] = page.url
    try:
        # Example: Reference Number
        ref_elem = page.locator("span[id*='lblReferenceNumber']")
        if ref_elem.count() > 0:
            details['reference_number'] = ref_elem.first.inner_text().strip()
            
        # Example: Job Title
        title_elem = page.locator("span[id*='lblPost']")
        if title_elem.count() > 0:
            details['title'] = title_elem.first.inner_text().strip()

        # Location
        loc_elem = page.locator("span[id*='lblCentre']")
        if loc_elem.count() > 0:
            details['location'] = loc_elem.first.inner_text().strip()

        # Generic full text
        main_content = page.locator("div#MainContent_pnlVacancyDetails")
        if main_content.count() > 0:
            details['full_text'] = main_content.inner_text().strip()
        else:
            details['full_text'] = page.locator("form").inner_text().strip()
            
    except Exception as e:
        print(f"Error extracting details: {e}")
        details['error'] = str(e)
        
    return details

def save_jobs(jobs, output_path):
    """Saves the current list of jobs to file."""
    try:
        with open(output_path, "w") as f:
            json.dump(jobs, f, indent=2)
        print(f"Progress saved: {len(jobs)} jobs total.")
    except Exception as e:
        print(f"Error saving jobs: {e}")

def run():
    all_jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a standard user agent to avoid bot detection
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )

        # Create timestamped directory
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        # Only create directories if we are running as main, or keep it for logging purposes
        if __name__ == "__main__":
             os.makedirs(output_dir, exist_ok=True)
             output_path = os.path.join(output_dir, "jobs.json")
        else:
             # If imported, maybe just log or silence saving?
             # For now, let's keep it simple and just skip file saving if not main, 
             # OR allow passing an output path. 
             # Let's keep existing behavior for now but safeguard the path.
             output_path = None

        page = context.new_page()

        print(f"Navigating to {BASE_URL}...")
        try:
            page.goto(BASE_URL, timeout=60000)
        except Exception as e:
            print(f"Error navigating: {e}")
            return []
        
        page_num = 1
        
        try:
            while True:
                print(f"Processing Page {page_num}...")
                
                # Wait for grid to load with retry
                grid_found = False
                for attempt in range(3):
                    try:
                        # Check for either the table OR the "No vacancies" message
                        # We use a race condition check effectively by checking if either exists
                        # But simpler: just wait for body, then check content.
                        page.wait_for_selector("body", timeout=30000)
                        
                        if page.locator("table#vacancyListingView").count() > 0:
                            grid_found = True
                            break
                        
                        # Check for no vacancies message (heuristic based on subagent report)
                        # We can look for the text "No vacancies available"
                        content = page.content()
                        if "No vacancies available" in content:
                            print("No vacancies available currently.")
                            break
                            
                        # If neither, wait a bit
                        time.sleep(2)
                    except Exception:
                        print(f"Grid wait retry {attempt+1}...")
                        time.sleep(2)
                
                if not grid_found and "No vacancies available" in page.content():
                    print("No jobs to scrape.")
                    break
                elif not grid_found:
                    print("Grid not found after retries.")
                    break

                # Find all 'Vacancy Details' buttons
                # Re-query every time to avoid stale handles
                buttons = page.locator("input[value='Vacancy Details']")
                buttons_count = buttons.count()
                print(f"Found {buttons_count} jobs on this page.")
                
                if buttons_count == 0:
                    break

                for i in range(buttons_count):
                    # Robust re-locate
                    button = page.locator("input[value='Vacancy Details']").nth(i)
                    
                    print(f"  Scraping job {i+1}/{buttons_count} on page {page_num}...")
                    
                    # Open in new tab strategy
                    page.evaluate("document.forms['vacancyPost'].target = '_blank'")
                    
                    try:
                        with context.expect_page(timeout=15000) as new_page_info:
                            button.click()
                        
                        new_page = new_page_info.value
                        new_page.wait_for_load_state()
                        
                        # Scrape
                        job_data = scrape_vacancy_details(new_page)
                        if job_data:
                            all_jobs.append(job_data)
                        
                        new_page.close()
                        
                    except Exception as e:
                        print(f"    -> Error opening job detail: {e}")
                        pass
                    
                    # Reset target
                    page.evaluate("document.forms['vacancyPost'].target = '_self'")
                
                # Incremental Save if we have an output path
                if output_path:
                    save_jobs(all_jobs, output_path)

                # Pagination
                next_page_num = page_num + 1
                # Try specific page number link
                next_link = page.locator(f"tr.GridPager a[href*='Page${next_page_num}']")
                
                if next_link.count() > 0:
                    print(f"Navigating to Page {next_page_num}...")
                    with page.expect_response(lambda response: response.status == 200, timeout=30000): # rudimentary postback wait
                        next_link.first.click()
                    
                    # Give it a moment for DOM to update
                    time.sleep(2)
                    page_num += 1
                else:
                    print("No next page found. Finished.")
                    break
                    
        finally:
            browser.close()
            if output_path:
                save_jobs(all_jobs, output_path)
            print("Done.")
            
    return all_jobs

if __name__ == "__main__":
    run()
