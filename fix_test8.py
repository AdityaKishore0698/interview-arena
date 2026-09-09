with open("frontend/e2e/matchmaking.spec.ts", "r") as f:
    content = f.read()

import re

new_test8 = """
  test('Test 8: Timer reload and reconnect', async ({ browser }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    for (const page of [pageA, pageB]) {
      await page.goto('/');
      await page.click('text=Continue as Guest');
      await page.waitForURL('**/dashboard');
      await page.waitForSelector('text=DSA');
      await page.locator('text=DSA').first().click();
      await page.click('button:has-text("Find Match")');
    }

    await pageA.waitForURL('**/interview/*');
    await pageB.waitForURL('**/interview/*'); // ADDED WAITING FOR PAGE B
    
    // Wait for the timer to be visible so we know state is loaded
    await expect(pageA.locator('.font-mono').first()).toBeVisible();

    // Reload
    await pageA.reload();
    
    // Assert the timer does not show the fallback offline state
    await pageA.waitForTimeout(2000); // Wait for React to settle
    await expect(pageA.locator('.font-mono').first()).toBeVisible();
    await expect(pageA.locator('.font-mono').first()).not.toHaveText("--:--");
    await expect(pageA.locator('.font-mono').first()).not.toHaveText("0:00");

    await contextA.close();
    await contextB.close();
  });
"""

# Just find where test 8 starts
start_idx = content.find("test('Test 8: Timer reload and reconnect'")
if start_idx != -1:
    end_idx = content.find("});\n\n});", start_idx)
    content = content[:start_idx] + new_test8.strip() + "\n\n});"
    
with open("frontend/e2e/matchmaking.spec.ts", "w") as f:
    f.write(content)
