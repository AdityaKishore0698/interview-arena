import re

with open("frontend/e2e/matchmaking.spec.ts", "r") as f:
    content = f.read()

# Replace the test setup with prints
new_setup = '''
    console.log("Navigating A");
    await pageA.goto('/');
    console.log("Clicking continue A");
    await pageA.click('text=Continue as Guest');
    console.log("Waiting URL A");
    await pageA.waitForURL('**/dashboard');
    console.log("Waiting selector DSA A");
    await pageA.waitForSelector('text=DSA');
    console.log("Clicking DSA A");
    await pageA.locator('text=DSA').first().click();
    console.log("Waiting Find Match A");
    await pageA.waitForSelector('button:has-text("Find Match"):not([disabled])');
    console.log("Clicking Find Match A");
    await pageA.click('button:has-text("Find Match")');
    console.log("A is queued");
'''

# Do the same for B
# Actually, just write a standalone script to test Playwright clicking!
