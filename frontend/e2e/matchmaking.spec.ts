import { test, expect, request } from '@playwright/test';

test.describe('P0 Matchmaking Correctness Matrix', () => {

  // Flush Redis before each test to prevent cross-test matchmaking contamination.
  // The backend /api/v1/debug/flush-redis endpoint requires TESTING=true env var.
  test.beforeEach(async () => {
    const apiContext = await request.newContext({ baseURL: 'http://localhost:8000' });
    const resp = await apiContext.post('/api/v1/debug/flush-redis').catch(() => null);
    if (resp && resp.ok()) {
      console.log('[beforeEach] Redis flushed for clean test isolation.');
    } else {
      console.warn('[beforeEach] Redis flush failed — tests may have cross-test contamination.');
    }
    await apiContext.dispose();
  });

  test('Test 1 & 9: QUICK + QUICK Match & Roles Verification', async ({ browser }) => {
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
      await page.waitForSelector('button:has-text("Join Queue"):not([disabled])');
      await page.click('button:has-text("Join Queue")');
    }

    await pageA.waitForURL('**/interview/*');
    await pageB.waitForURL('**/interview/*');

    // Both should see PREPARATION timer ~30 seconds (we just check it's visible)
    await expect(pageA.locator('.font-mono').first()).toBeVisible();
    await expect(pageB.locator('.font-mono').first()).toBeVisible();

    // Verify Roles in Round 1
    await expect(pageA.locator('text=You are the')).toBeVisible();
    await expect(pageB.locator('text=You are the')).toBeVisible();
    await expect(pageA.locator('span.text-primary').first()).not.toHaveText("...");
    await expect(pageB.locator('span.text-primary').first()).not.toHaveText("...");
    const aRole = await pageA.locator('span.text-primary').first().innerText();
    const bRole = await pageB.locator('span.text-primary').first().innerText();
    expect(aRole !== bRole).toBeTruthy();
    expect(aRole).not.toContain('Observer');
    
    await contextA.close();
    await contextB.close();
  });

  test('Test 2: QUICK + STANDARD (No Match)', async ({ browser }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    await pageA.goto('/');
    await pageA.click('text=Continue as Guest');
    await pageA.waitForURL('**/dashboard');
    await pageA.waitForSelector('text=DSA');
    await pageA.locator('text=DSA').first().click();
    await pageA.click('button:has-text("Join Queue")');

    await pageB.goto('/');
    await pageB.click('text=Continue as Guest');
    await pageB.waitForURL('**/dashboard');
    await pageB.waitForSelector('text=DSA');
    await pageB.locator('text=DSA').first().click();
    await pageB.click('text=Standard');
    await pageB.click('button:has-text("Join Queue")');

    // Both should still be searching
    await expect(pageA.locator("text=Cancel Queue")).toBeVisible();
    await expect(pageB.locator("text=Cancel Queue")).toBeVisible();
    
    await pageA.waitForTimeout(2000);
    await expect(pageA).toHaveURL(/.*dashboard/);
    await expect(pageB).toHaveURL(/.*dashboard/);

    await contextA.close();
    await contextB.close();
  });

  test('Test 3: Single user (no ghost opponent)', async ({ browser }) => {
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();

    await pageA.goto('/');
    await pageA.click('text=Continue as Guest');
    await pageA.waitForURL('**/dashboard');
    await pageA.waitForSelector('text=DSA');
    await pageA.locator('text=DSA').first().click();
    await pageA.click('button:has-text("Join Queue")');

    await expect(pageA.locator("text=Cancel Queue")).toBeVisible();
    await pageA.waitForTimeout(2000);
    await expect(pageA).toHaveURL(/.*dashboard/);

    await contextA.close();
  });

  test('Test 4: Presence Semantics', async ({ browser }) => {
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
      await page.click('button:has-text("Join Queue")');
    }

    await pageA.waitForURL('**/interview/*');
    await pageB.waitForURL('**/interview/*');

    // After both navigate to interview, A should see either "Waiting for opponent..."
    // or "Opponent Connected" (depending on WS event timing). Either is valid; but
    // "Opponent Disconnected" is not valid at this point.
    await expect(pageA.locator('text=Opponent Disconnected')).not.toBeVisible();
    
    // Wait for Opponent Connected to arrive (WS OPPONENT_CONNECTED event)
    await expect(pageA.locator('text=Opponent Connected')).toBeVisible({ timeout: 8000 });
    
    // Close B to trigger disconnect
    await contextB.close();
    
    // A should see Opponent Disconnected
    await expect(pageA.locator('text=Opponent Disconnected')).toBeVisible({ timeout: 8000 });

    await contextA.close();
  });


  test('Test 5 & 11: Session termination and cleanup', async ({ browser }) => {
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
      await page.click('button:has-text("Join Queue")');
    }

    await pageA.waitForURL('**/interview/*');
    await pageB.waitForURL('**/interview/*');

    // A leaves
    await expect(pageA.locator('button:has-text("Leave")')).toBeVisible();
    await pageA.locator('button:has-text("Leave")').first().click();
    
    // Accept confirmation dialog
    await pageA.waitForSelector('text=Confirm Leave');
    await pageA.click('text=Confirm Leave');

    // Should return to dashboard
    await pageA.waitForURL('**/dashboard');
    
    // B should see Session Abandoned
    await expect(pageB.locator('text=Session Abandoned')).toBeVisible();

    // A joins again
    await expect(pageA.locator('button:has-text("Leave")')).not.toBeVisible();
    await pageA.waitForSelector('text=DSA');
    await pageA.locator('text=DSA').first().click();
    await pageA.click('button:has-text("Join Queue")');
    
    // A should be searching
    await expect(pageA.locator("text=Cancel Queue")).toBeVisible();
    await pageA.waitForTimeout(2000);
    await expect(pageA).toHaveURL(/.*dashboard/); // Still searching
    
    await contextA.close();
    await contextB.close();
  });

  test('Test 7: Queue switching', async ({ browser }) => {
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();

    await pageA.goto('/');
    await pageA.click('text=Continue as Guest');
    await pageA.waitForURL('**/dashboard');
    await pageA.waitForSelector('text=DSA');
    await pageA.locator('text=DSA').first().click();
    await pageA.click('button:has-text("Join Queue")');

    await expect(pageA.locator("text=Cancel Queue")).toBeVisible();
    
    // Cancel
    await pageA.locator("text=Cancel Queue").click({ force: true });
    
    // Prove old queue membership is removed
    await expect(pageA.locator('button:has-text("Join Queue")')).toBeVisible();
    
    // Switch to STANDARD
    await pageA.click('text=Standard');
    await pageA.click('button:has-text("Join Queue")');

    await expect(pageA.locator("text=Cancel Queue")).toBeVisible();
    
    // Prove we don't automatically jump to an interview (no stale MATCH_FOUND)
    await pageA.waitForTimeout(3000);
    await expect(pageA).toHaveURL(/.*dashboard/);
    
    await contextA.close();
  });

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
      await page.click('button:has-text("Join Queue")');
    }

    await pageA.waitForURL('**/interview/*');
    await pageB.waitForURL('**/interview/*');

    // Wait for timer to be visible
    await expect(pageA.locator('.font-mono').first()).toBeVisible();
    
    // Reload A
    await pageA.reload();
    await pageA.waitForURL('**/interview/*');
    
    // Ensure timer recovers via authoritative endsAt
    await expect(pageA.locator('.font-mono').first()).toBeVisible();
    const timerA2 = await pageA.locator('.font-mono').first().innerText();
    expect(timerA2 !== "0:00").toBeTruthy();

    await contextA.close();
    await contextB.close();
  });

  test('Test 12: Full MVP E2E Lifecycle', async ({ browser }) => {
    test.setTimeout(60000);
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
      await page.click('button:has-text("Join Queue")');
    }

    await pageA.waitForURL('**/interview/*');
    await pageB.waitForURL('**/interview/*');

    // Wait for Preparation to end and Round 1 to start
    await expect(pageA.locator('text=Round 1').first()).toBeVisible({ timeout: 10000 });
    await expect(pageB.locator('text=Round 1').first()).toBeVisible({ timeout: 10000 });

    // Store R1 roles
    const aRoleR1 = await pageA.locator('span.text-primary').first().innerText();
    const bRoleR1 = await pageB.locator('span.text-primary').first().innerText();
    expect(aRoleR1 !== bRoleR1).toBeTruthy();

    // Wait for Round 1 Feedback
    await expect(pageA.locator('text=Round 1 Feedback').first()).toBeVisible({ timeout: 45000 });
    await expect(pageB.locator('text=Round 1 Feedback').first()).toBeVisible({ timeout: 45000 });

    // Submit Feedback R1 for A
    await pageA.getByRole('radiogroup', { name: 'Communication' }).getByRole('radio').nth(4).click();
    await pageA.getByRole('radiogroup', { name: 'Technical Knowledge' }).getByRole('radio').nth(3).click();
    await pageA.getByRole('radiogroup', { name: 'Problem Solving' }).getByRole('radio').nth(4).click();
    await pageA.fill('textarea[placeholder="Constructive feedback, specific observations..."]', 'Good job');
    await pageA.click('button:has-text("Submit Feedback")');

    // Submit Feedback R1 for B
    await pageB.getByRole('radiogroup', { name: 'Communication' }).getByRole('radio').nth(3).click();
    await pageB.getByRole('radiogroup', { name: 'Technical Knowledge' }).getByRole('radio').nth(4).click();
    await pageB.getByRole('radiogroup', { name: 'Problem Solving' }).getByRole('radio').nth(3).click();
    await pageB.fill('textarea[placeholder="Constructive feedback, specific observations..."]', 'Could improve');
    await pageB.click('button:has-text("Submit Feedback")');

    // Wait for Round 2 to start
    await expect(pageA.locator('text=Round 2').first()).toBeVisible({ timeout: 45000 });
    await expect(pageB.locator('text=Round 2').first()).toBeVisible({ timeout: 45000 });

    // Verify Role Reversal
    const aRoleR2 = await pageA.locator('span.text-primary').first().innerText();
    const bRoleR2 = await pageB.locator('span.text-primary').first().innerText();
    expect(aRoleR2).not.toEqual(aRoleR1);
    expect(bRoleR2).not.toEqual(bRoleR1);

    // Wait for Round 2 Feedback
    await expect(pageA.locator('text=Round 2 Feedback').first()).toBeVisible({ timeout: 45000 });
    await expect(pageB.locator('text=Round 2 Feedback').first()).toBeVisible({ timeout: 45000 });

    // Submit Feedback R2 for A
    await pageA.getByRole('radiogroup', { name: 'Communication' }).getByRole('radio').nth(4).click();
    await pageA.getByRole('radiogroup', { name: 'Technical Knowledge' }).getByRole('radio').nth(4).click();
    await pageA.getByRole('radiogroup', { name: 'Problem Solving' }).getByRole('radio').nth(4).click();
    await pageA.click('button:has-text("Submit Feedback")');

    // Submit Feedback R2 for B
    await pageB.getByRole('radiogroup', { name: 'Communication' }).getByRole('radio').nth(4).click();
    await pageB.getByRole('radiogroup', { name: 'Technical Knowledge' }).getByRole('radio').nth(4).click();
    await pageB.getByRole('radiogroup', { name: 'Problem Solving' }).getByRole('radio').nth(4).click();
    await pageB.click('button:has-text("Submit Feedback")');

    // Wait for Interview Complete
    await expect(pageA.locator('text=Interview Complete')).toBeVisible({ timeout: 45000 });
    await expect(pageB.locator('text=Interview Complete')).toBeVisible({ timeout: 45000 });
    
    // Ensure Abandoned is NOT visible
    await expect(pageA.locator('text=Session Abandoned')).not.toBeVisible();
    await expect(pageB.locator('text=Session Abandoned')).not.toBeVisible();

    await contextA.close();
    await contextB.close();
  });
});
