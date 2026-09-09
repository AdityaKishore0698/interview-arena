with open("frontend/e2e/matchmaking.spec.ts", "r") as f:
    content = f.read()

old_t8 = """
    // The timer should still be synced, no 00:00
    const timer = await pageA.locator('.text-2xl').innerText();
    expect(timer).not.toBe("0:00");
"""

new_t8 = """
    // The timer should still be synced, no 00:00
    await expect(pageA.locator('.text-2xl')).not.toHaveText("0:00", { timeout: 10000 });
"""

content = content.replace(old_t8.strip(), new_t8.strip())

with open("frontend/e2e/matchmaking.spec.ts", "w") as f:
    f.write(content)
