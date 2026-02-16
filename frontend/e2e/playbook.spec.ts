import { test, expect } from "@playwright/test";

const mockPlaybookResponse = {
  stats: {
    total_entries: 8,
    helpful_total: 24,
    harmful_total: 3,
  },
  rendered: "",
  entries: [
    {
      id: "pb-001",
      entry_id: "E-001",
      section: "Risk Management",
      content: "Always set stop losses below 5% of portfolio value",
      helpful_count: 8,
      harmful_count: 1,
      created_at: "2026-01-15T10:00:00Z",
      updated_at: "2026-02-10T10:00:00Z",
    },
    {
      id: "pb-002",
      entry_id: "E-002",
      section: "Risk Management",
      content: "Use trailing stops for momentum strategies",
      helpful_count: 6,
      harmful_count: 0,
      created_at: "2026-01-16T10:00:00Z",
      updated_at: "2026-02-10T10:00:00Z",
    },
    {
      id: "pb-003",
      entry_id: "E-003",
      section: "Entry Signals",
      content: "RSI crossing 30 from below is a strong buy signal",
      helpful_count: 10,
      harmful_count: 2,
      created_at: "2026-01-17T10:00:00Z",
      updated_at: "2026-02-10T10:00:00Z",
    },
  ],
};

test.describe("Playbook page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/playbook", (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockPlaybookResponse),
        });
      }
      // POST /playbook/reset handled separately
    });
    await page.route("**/api/v1/playbook/reset", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", message: "Playbook reset" }),
      })
    );
  });

  test("AC11: renders stats banner and entry list", async ({ page }) => {
    await page.goto("/playbook");
    await expect(page.getByTestId("stats-banner")).toBeVisible();

    // Stats should show values
    await expect(page.getByTestId("stats-banner")).toContainText("8");
    await expect(page.getByTestId("stats-banner")).toContainText("24");

    // Entries should be present
    await expect(page.getByTestId("playbook-entries")).toBeVisible();
    const entries = page.getByTestId("playbook-entry");
    await expect(entries).toHaveCount(3);
  });

  test("AC12: reset button shows confirm dialog", async ({ page }) => {
    await page.goto("/playbook");
    await expect(page.getByTestId("reset-button")).toBeVisible();

    // Click reset
    await page.getByTestId("reset-button").click();

    // Confirm dialog appears
    await expect(page.getByTestId("reset-dialog")).toBeVisible();
    await expect(page.getByTestId("confirm-reset")).toBeVisible();

    // Cancel closes dialog
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByTestId("reset-dialog")).not.toBeVisible();
  });

  test("AC13: entries show helpful/harmful badges", async ({ page }) => {
    await page.goto("/playbook");

    // Check badges exist
    const helpfulBadges = page.getByTestId("helpful-badge");
    const harmfulBadges = page.getByTestId("harmful-badge");
    await expect(helpfulBadges).toHaveCount(3);
    await expect(harmfulBadges).toHaveCount(3);

    // First entry: +8 / -1
    await expect(helpfulBadges.first()).toContainText("+8");
    await expect(harmfulBadges.first()).toContainText("-1");
  });
});
