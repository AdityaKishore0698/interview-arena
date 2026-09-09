with open("frontend/e2e/matchmaking.spec.ts", "r") as f:
    content = f.read()

old_timer = """
    // Both should see PREPARATION timer ~30 seconds
    const timerA = await pageA.locator('.text-2xl').innerText();
    const timerB = await pageB.locator('.text-2xl').innerText();
    
    // It should be 00:30, 00:29 etc
    expect(timerA).toMatch(/0:2[5-9]|0:30/);
"""

new_timer = """
    // Both should see PREPARATION timer ~30 seconds
    await expect(pageA.locator('.text-2xl')).toHaveText(/0:2[5-9]|0:30/, { timeout: 15000 });
    await expect(pageB.locator('.text-2xl')).toHaveText(/0:2[5-9]|0:30/, { timeout: 15000 });
"""
content = content.replace(old_timer.strip(), new_timer.strip())

old_role = """
    // Verify Roles in Round 1
    const aRole = await pageA.locator('text=You will be the').innerText();
    const bRole = await pageB.locator('text=You will be the').innerText();
    
    expect(aRole !== bRole).toBeTruthy();
    expect(aRole.includes('Observer')).toBeFalsy();
"""

new_role = """
    // Verify Roles in Round 1
    await expect(pageA.locator('text=You will be the')).toBeVisible();
    await expect(pageB.locator('text=You will be the')).toBeVisible();
    const aRole = await pageA.locator('.text-primary').first().innerText();
    const bRole = await pageB.locator('.text-primary').first().innerText();
    expect(aRole !== bRole).toBeTruthy();
    expect(aRole).not.toContain('Observer');
"""
content = content.replace(old_role.strip(), new_role.strip())

with open("frontend/e2e/matchmaking.spec.ts", "w") as f:
    f.write(content)
