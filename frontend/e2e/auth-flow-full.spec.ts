import { test, expect } from '@playwright/test';

test.describe('Full MVP Acceptance Flow (Google Auth to Completion)', () => {

  test.beforeEach(async ({ request }) => {
    // Clean state for tests
    await request.delete('/api/v1/debug/redis');
  });

  test('Test Full Product Flow with Chat and Media', async ({ browser }) => {
    // We need permissions for WebRTC
    const contextA = await browser.newContext({ permissions: ['camera', 'microphone'] });
    const contextB = await browser.newContext({ permissions: ['camera', 'microphone'] });

    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();
    
    pageA.on('console', msg => console.log(`A: ${msg.text()}`));
    pageB.on('console', msg => console.log(`B: ${msg.text()}`));

    // 1. Google/authenticated user setup
    // Since TESTING=true, backend auto-mocks the Google callback -> redirects /?token=...
    // The frontend page.tsx picks up ?token and stores it, then navigates to /dashboard
    await pageA.goto('http://localhost:8000/api/v1/auth/google/login');
    await pageA.waitForURL('**/dashboard', { timeout: 15000 });
    await expect(pageA.locator('text=Start an Interview').first()).toBeVisible();

    await pageB.goto('http://localhost:8000/api/v1/auth/google/login');
    await pageB.waitForURL('**/dashboard', { timeout: 15000 });
    await expect(pageB.locator('text=Start an Interview').first()).toBeVisible();

    // 2. Matchmaking — join both into queue (QUICK DSA, QUICK is already default)
    await pageA.locator('text=DSA').first().click();
    await pageA.click('button:has-text("Join Queue")');

    await pageB.locator('text=DSA').first().click();
    await pageB.click('button:has-text("Join Queue")');

    // Both should be redirected to the Arena once matched
    await Promise.all([
      pageA.waitForURL('**/interview/*', { timeout: 30000 }),
      pageB.waitForURL('**/interview/*', { timeout: 30000 }),
    ]);

    // 3. Preparation phase → Round 1
    await expect(pageA.locator('text=Round 1').first()).toBeVisible({ timeout: 20000 });
    await expect(pageB.locator('text=Round 1').first()).toBeVisible({ timeout: 20000 });

    // 4. Opponent Presence (both WebSockets connected)
    await expect(pageA.locator('text=Opponent Connected').first()).toBeVisible({ timeout: 10000 });
    await expect(pageB.locator('text=Opponent Connected').first()).toBeVisible({ timeout: 10000 });

    // 5. Chat A → B
    await pageA.locator('textarea[placeholder="Type a message..."]').fill('Hello from A');
    await pageA.getByLabel('Send message').click();
    await expect(pageA.locator('text=Hello from A')).toBeVisible({ timeout: 10000 }); // Check A first!
    await expect(pageB.locator('text=Hello from A')).toBeVisible({ timeout: 10000 });

    // 6. Chat B → A
    await pageB.locator('textarea[placeholder="Type a message..."]').fill('Hi back from B');
    await pageB.getByLabel('Send message').click();
    await expect(pageB.locator('text=Hi back from B')).toBeVisible({ timeout: 10000 }); // Check B first!
    await expect(pageA.locator('text=Hi back from B')).toBeVisible({ timeout: 10000 });

    // 7. WebRTC signaling — A initiates, B auto-answers
    await pageA.click('button:has-text("Connect Audio/Video")');
    await expect(pageA.locator('text=Connected').first()).toBeVisible({ timeout: 15000 });
    await expect(pageB.locator('text=Connected').first()).toBeVisible({ timeout: 15000 });

    // 8. Wait for Round 1 → Feedback phase
    await expect(pageA.locator('button:has-text("Submit Feedback")').first()).toBeVisible({ timeout: 45000 });
    await expect(pageB.locator('button:has-text("Submit Feedback")').first()).toBeVisible({ timeout: 45000 });

    // Submit R1 feedback
    await pageA.getByRole('radiogroup', { name: 'Communication' }).getByRole('radio').nth(4).click();
    await pageA.getByRole('radiogroup', { name: 'Technical Knowledge' }).getByRole('radio').nth(3).click();
    await pageA.getByRole('radiogroup', { name: 'Problem Solving' }).getByRole('radio').nth(4).click();
    await pageA.fill('textarea[placeholder="Constructive feedback, specific observations..."]', 'Good job overall.');
    await pageA.click('button:has-text("Submit Feedback")');

    await pageB.getByRole('radiogroup', { name: 'Communication' }).getByRole('radio').nth(3).click();
    await pageB.getByRole('radiogroup', { name: 'Technical Knowledge' }).getByRole('radio').nth(4).click();
    await pageB.getByRole('radiogroup', { name: 'Problem Solving' }).getByRole('radio').nth(3).click();
    await pageB.fill('textarea[placeholder="Constructive feedback, specific observations..."]', 'Could improve.');
    await pageB.click('button:has-text("Submit Feedback")');

    // 9. Round 2 (role reversal)
    await expect(pageA.locator('text=Round 2').first()).toBeVisible({ timeout: 45000 });
    await expect(pageB.locator('text=Round 2').first()).toBeVisible({ timeout: 45000 });

    // 10. Round 2 Feedback
    await expect(pageA.locator('button:has-text("Submit Feedback")').first()).toBeVisible({ timeout: 45000 });
    await expect(pageB.locator('button:has-text("Submit Feedback")').first()).toBeVisible({ timeout: 45000 });

    // Submit R2 feedback
    await pageA.getByRole('radiogroup', { name: 'Communication' }).getByRole('radio').nth(4).click();
    await pageA.getByRole('radiogroup', { name: 'Technical Knowledge' }).getByRole('radio').nth(4).click();
    await pageA.getByRole('radiogroup', { name: 'Problem Solving' }).getByRole('radio').nth(4).click();
    await pageA.click('button:has-text("Submit Feedback")');

    await pageB.getByRole('radiogroup', { name: 'Communication' }).getByRole('radio').nth(4).click();
    await pageB.getByRole('radiogroup', { name: 'Technical Knowledge' }).getByRole('radio').nth(4).click();
    await pageB.getByRole('radiogroup', { name: 'Problem Solving' }).getByRole('radio').nth(4).click();
    await pageB.click('button:has-text("Submit Feedback")');

    // 11. SESSION_COMPLETED
    await expect(pageA.locator('text=Interview Complete').first()).toBeVisible({ timeout: 45000 });
    await expect(pageB.locator('text=Interview Complete').first()).toBeVisible({ timeout: 45000 });

    await contextA.close();
    await contextB.close();
  });
});
