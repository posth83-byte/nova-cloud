const { test, expect } = require('@playwright/test');

test.describe('JARVIS Testportal E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigera till den lokala index.html-sidan
    await page.goto('./index.html');
  });

  test('ska inte ha horisontell overflow på mobilviewport (390px)', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    
    // Kontrollera att dokumentets totala bredd inte överstiger viewportens bredd
    const bodyWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);
  });

  test('ska kunna lägga till och ta bort uppgifter samt uppdatera räknaren', async ({ page }) => {
    const taskInput = page.locator('#taskInput');
    const addTaskBtn = page.locator('#addTaskBtn');
    const taskCounter = page.locator('#taskCounter');
    const taskList = page.locator('#taskList');

    // Kontrollera initial räknare
    await expect(taskCounter).toHaveText('Antal uppgifter: 0');

    // Lägg till första uppgiften
    await taskInput.fill('Kör E2E-tester');
    await addTaskBtn.click();
    await expect(taskCounter).toHaveText('Antal uppgifter: 1');
    await expect(taskList).toContainText('Kör E2E-tester');

    // Lägg till andra uppgiften
    await taskInput.fill('Verifiera GitHub Actions');
    await addTaskBtn.click();
    await expect(taskCounter).toHaveText('Antal uppgifter: 2');
    await expect(taskList).toContainText('Verifiera GitHub Actions');

    // Ta bort den första uppgiften
    const deleteButton = taskList.locator('.delete-btn').first();
    await deleteButton.click();
    await expect(taskCounter).toHaveText('Antal uppgifter: 1');
    await expect(taskList).not.toContainText('Kör E2E-tester');
  });

  test('mobilmenyn ska fungera vid klick och navigeringslänkar ska vara klickbara', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    const menuToggle = page.locator('#menuToggle');
    const nav = page.locator('#navMenu');
    const navLinks = nav.locator('a');

    // Menyn ska vara dold från början på mobil
    await expect(nav).not.toHaveClass(/open/);

    // Klicka för att öppna menyn
    await menuToggle.click();
    await expect(nav).toHaveClass(/open/);

    // Kontrollera att navigeringslänkar finns och är klickbara
    const linkCount = await navLinks.count();
    expect(linkCount).toBeGreaterThan(0);

    for (let i = 0; i < linkCount; i++) {
      const link = navLinks.nth(i);
      await expect(link).toBeVisible();
      await link.click();
    }

    // Klicka för att stänga menyn igen
    await menuToggle.click();
    await expect(nav).not.toHaveClass(/open/);
  });

  test('inga konsolfel ska uppstå under körning', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.reload();
    expect(consoleErrors).toEqual([]);
  });
});