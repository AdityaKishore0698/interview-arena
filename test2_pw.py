from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    pageB = browser.new_page()
    pageB.goto('http://localhost:3000/')
    pageB.click('text=Continue as Guest')
    pageB.wait_for_url('**/dashboard')
    pageB.wait_for_selector('text=DSA')
    pageB.locator('text=DSA').first.click()
    pageB.click('button[role="combobox"]')
    pageB.click('text=Standard (35 mins)')
    pageB.click('button:has-text("Find Match")')
    print("Test 2 Success")
    browser.close()
