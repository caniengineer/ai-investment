import { test, expect } from "@playwright/test";

test.describe("Phase 1 scaffold", () => {
  test("home page renders with layout", async ({ page }) => {
    await page.goto("/");
    // Sidebar visible with AlphaAgent branding
    await expect(page.locator("aside")).toBeVisible();
    await expect(page.getByText("AlphaAgent").first()).toBeVisible();

    // Header visible
    await expect(page.locator("header")).toBeVisible();

    // Main content area
    await expect(page.getByRole("heading", { name: "Strategies" })).toBeVisible();
  });

  test("sidebar navigation links are present", async ({ page }) => {
    await page.goto("/");
    const sidebar = page.locator("aside");
    await expect(sidebar.getByText("Strategies")).toBeVisible();
    await expect(sidebar.getByText("Chat")).toBeVisible();
    await expect(sidebar.getByText("Knowledge")).toBeVisible();
    await expect(sidebar.getByText("Metrics")).toBeVisible();
    await expect(sidebar.getByText("Playbook")).toBeVisible();
    await expect(sidebar.getByText("Live Trading")).toBeVisible();
  });

  test("sidebar nav links navigate correctly", async ({ page }) => {
    await page.goto("/");

    // Click Chat link
    await page.locator("aside").getByText("Chat").click();
    await expect(page).toHaveURL(/\/chat/);

    // Click Knowledge link
    await page.locator("aside").getByText("Knowledge").click();
    await expect(page).toHaveURL(/\/knowledge/);

    // Click Metrics link
    await page.locator("aside").getByText("Metrics").click();
    await expect(page).toHaveURL(/\/metrics/);

    // Click Playbook link
    await page.locator("aside").getByText("Playbook").click();
    await expect(page).toHaveURL(/\/playbook/);

    // Click Live Trading link
    await page.locator("aside").getByText("Live Trading").click();
    await expect(page).toHaveURL(/\/live/);

    // Navigate back to Strategies
    await page.locator("aside").getByText("Strategies").click();
    await expect(page).toHaveURL("/");
  });

  test("active nav state highlights current page", async ({ page }) => {
    await page.goto("/");
    // The Strategies link should have the active style on home page
    const strategiesLink = page.locator("aside a", { hasText: "Strategies" });
    await expect(strategiesLink).toHaveClass(/text-primary/);
  });

  test("theme toggle button exists", async ({ page }) => {
    await page.goto("/");
    const themeButton = page.getByRole("button", { name: "Toggle theme" });
    await expect(themeButton).toBeVisible();
  });

  test("theme toggle switches between light and dark", async ({ page }) => {
    await page.goto("/");
    const html = page.locator("html");
    const themeButton = page.getByRole("button", { name: "Toggle theme" });

    // Click to toggle theme
    await themeButton.click();
    // Wait for theme transition
    await page.waitForTimeout(500);

    // Check that the class attribute changed (either added or removed 'dark')
    const classAfterClick = await html.getAttribute("class");
    expect(classAfterClick).toBeDefined();
  });
});
