import { test, expect } from '@playwright/test';

test.describe('Auth Flow', () => {
  test('User can register, login, and logout', async ({ page, request }) => {
    // 0. Ensure clean state
    await request.post('http://localhost:8000/api/v1/debug/flush-redis');

    const randomSuffix = Math.floor(Math.random() * 1000000);
    const email = `testuser_${randomSuffix}@example.com`;
    const password = 'password123';
    const displayName = `TestUser_${randomSuffix}`;

    // 1. Go to Home Page
    await page.goto('/');
    await expect(page.locator('text=Access the Arena')).toBeVisible();

    // 2. Switch to Register Mode
    await page.click('button:has-text("Don\'t have an account? Register")');

    // 3. Fill Registration Form
    await page.fill('input[placeholder="Display Name"]', displayName);
    await page.fill('input[placeholder="Email address"]', email);
    await page.fill('input[placeholder="Password"]', password);

    // 4. Submit Registration — sends an OTP and switches to the verification step
    await page.click('button:has-text("Create Account")');

    // 5. Complete email verification (OTP is the fixed 123456 under TESTING=true)
    await expect(page.locator('input[placeholder="6-digit OTP"]')).toBeVisible();
    await page.fill('input[placeholder="6-digit OTP"]', '123456');
    await page.click('button:has-text("Verify & Complete")');

    // 6. Verify Dashboard Navigation
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.locator(`text=${displayName}`)).toBeVisible();

    // 6. Logout
    await page.click('button[title="Logout"]');
    
    // 7. Verify Redirected to Home
    await expect(page).toHaveURL('http://localhost:3000/');
    await expect(page.locator('button:has-text("Sign In")')).toBeVisible();

    // 8. Login again
    await page.fill('input[placeholder="Email address"]', email);
    await page.fill('input[placeholder="Password"]', password);
    await page.click('button:has-text("Sign In")');

    // 9. Verify Dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.locator(`text=${displayName}`)).toBeVisible();
  });
});
