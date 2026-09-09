from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('http://localhost:3000/')
    page.click('text=Continue as Guest')
    page.wait_for_url('**/dashboard')
    print("At dashboard, waiting for DSA")
    page.wait_for_selector('text=DSA')
    print("Clicking DSA")
    page.locator('text=DSA').first.click()
    page.wait_for_selector('button:has-text("Find Match"):not([disabled])')
    print("Clicking Find Match")
    page.click('button:has-text("Find Match")')
    print("Wait for queue")
    page.wait_for_timeout(2000)
    print("Success")
    browser.close()
