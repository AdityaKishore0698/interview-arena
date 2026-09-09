import { test, expect } from '@playwright/test';

test.describe('Real-time Communication (Chat & Media)', () => {
  test.beforeEach(async () => {
    await fetch('http://localhost:8000/api/v1/debug/redis', { method: 'DELETE' });
  });

  test('Users can exchange chat messages and connect media in an active round', async ({ browser }) => {
    const contextA = await browser.newContext({ permissions: ['camera', 'microphone'] });
    const contextB = await browser.newContext({ permissions: ['camera', 'microphone'] });
    
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    // User A connects
    await pageA.goto('/');
    await pageA.click('button:has-text("Continue as Guest")');
    await pageA.waitForURL('**/dashboard');
    await pageA.waitForSelector('text=DSA');
    await pageA.locator('text=DSA').first().click();
    await pageA.click('button:has-text("Join Queue")');

    // User B connects
    await pageB.goto('/');
    await pageB.click('button:has-text("Continue as Guest")');
    await pageB.waitForURL('**/dashboard');
    await pageB.waitForSelector('text=DSA');
    await pageB.locator('text=DSA').first().click();
    await pageB.click('button:has-text("Join Queue")');

    await pageA.waitForTimeout(5000);
    await pageA.screenshot({ path: 'test-screenshot-5s.png' });

    // Wait for Round 1
    await pageA.screenshot({ path: 'test-screenshot.png' });
    await expect(pageA.locator('h1', { hasText: 'Round 1' }).first()).toBeVisible({ timeout: 15000 });
    await expect(pageB.locator('h1', { hasText: 'Round 1' }).first()).toBeVisible({ timeout: 15000 });

    // Ensure Chat Panel is visible
    await pageA.screenshot({ path: 'test-screenshot.png' });
    await expect(pageA.locator('textarea[placeholder="Type a message..."]')).toBeVisible();
    await expect(pageB.locator('textarea[placeholder="Type a message..."]')).toBeVisible();

    // A sends message
    await pageA.fill('textarea[placeholder="Type a message..."]', 'Hello from User A');
    await pageA.keyboard.press('Enter');

    // B receives message
    await expect(pageB.locator('text=Hello from User A').first()).toBeVisible();

    // Test Media connection
    await pageA.screenshot({ path: 'test-screenshot-button.png' });
    await expect(pageA.getByRole('button', { name: /connect audio\/video/i })).toBeVisible();
    await expect(pageB.getByRole('button', { name: /connect audio\/video/i })).toBeVisible();
    
    await pageA.getByRole('button', { name: /connect audio\/video/i }).click();
    // Do not click on B, it auto-answers

    // Wait for the "Waiting for opponent..." text to disappear, indicating connection
    await expect(pageA.locator('text=Waiting for opponent...')).toBeHidden({ timeout: 10000 });
    await expect(pageB.locator('text=Waiting for opponent...')).toBeHidden({ timeout: 10000 });

    await contextA.close();
    await contextB.close();
  });
});
