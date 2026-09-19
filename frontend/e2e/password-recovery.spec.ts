import { test, expect } from '@playwright/test';

// DEMO password recovery: no email is sent — the reset code is shown in the UI.
test.describe('Password recovery (demo)', () => {
  test('User can reset a forgotten password using the on-screen demo code', async ({ page }) => {
    const suffix = Math.floor(Math.random() * 1000000);
    const email = `recover_${suffix}@example.com`;
    const oldPassword = 'password123';
    const newPassword = 'brandnewpass456';
    const displayName = `Recover_${suffix}`;

    // Create an account (signs in immediately), then log out.
    await page.goto('/');
    await page.click('button:has-text("Don\'t have an account? Register")');
    await page.fill('input[placeholder="Display Name"]', displayName);
    await page.fill('input[placeholder="Email address"]', email);
    await page.fill('input[placeholder="Password"]', oldPassword);
    await page.click('button:has-text("Create Account")');
    await expect(page).toHaveURL(/.*\/dashboard/);
    await page.click('button[title="Logout"]');
    await expect(page.locator('button:has-text("Sign In")')).toBeVisible();

    // Forgot password -> the code is displayed on screen, not emailed.
    await page.click('button:has-text("Forgot password?")');
    await page.fill('input[placeholder="Email address"]', email);
    await page.click('button:has-text("Get Demo Reset Code")');

    const codeBox = page.getByTestId('demo-reset-code');
    await expect(codeBox).toBeVisible();
    await expect(page.getByText('Demo recovery code')).toBeVisible();
    await expect(page.getByText(/check your email|we sent/i)).toHaveCount(0);
    await expect(page.getByRole('button', { name: /resend/i })).toHaveCount(0);
    const code = (await codeBox.innerText()).trim();
    expect(code).toMatch(/^\d{6}$/);
    await expect(page.locator('input[placeholder="6-digit reset code"]')).toHaveValue(code);

    // Reset the password with it.
    await page.fill('input[placeholder="New password"]', newPassword);
    await page.fill('input[placeholder="Confirm new password"]', newPassword);
    await page.click('button:has-text("Reset Password")');
    await expect(page.getByText('Password updated. Sign in with your new password.')).toBeVisible();

    // Old password is rejected, new one works.
    await page.fill('input[placeholder="Email address"]', email);
    await page.fill('input[placeholder="Password"]', oldPassword);
    await page.click('button:has-text("Sign In")');
    await expect(page.getByText('Invalid credentials')).toBeVisible();

    await page.fill('input[placeholder="Password"]', newPassword);
    await page.click('button:has-text("Sign In")');
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.locator(`text=${displayName}`)).toBeVisible();
  });

  test('A wrong code is rejected', async ({ page }) => {
    const email = `recover_bad_${Math.floor(Math.random() * 1000000)}@example.com`;
    await page.goto('/');
    await page.click('button:has-text("Forgot password?")');
    await page.fill('input[placeholder="Email address"]', email);
    await page.click('button:has-text("Get Demo Reset Code")');
    await expect(page.getByTestId('demo-reset-code')).toBeVisible();

    // Unknown email gets an unredeemable decoy code; using it must fail.
    await page.fill('input[placeholder="New password"]', 'brandnewpass456');
    await page.fill('input[placeholder="Confirm new password"]', 'brandnewpass456');
    await page.click('button:has-text("Reset Password")');
    await expect(page.getByText('Invalid or expired code')).toBeVisible();
  });
});
