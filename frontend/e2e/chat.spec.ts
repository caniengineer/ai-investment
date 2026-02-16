import { test, expect } from "@playwright/test";

const mockChatResponse = {
  strategy_id: "strat-001",
  strategy: { name: "RSI Momentum", asset: "BTC/USD" },
  backtest: {
    passed: true,
    metrics: { sharpe_ratio: 1.85, total_return: 0.32, max_drawdown: -0.12 },
    iterations: [],
    explanation: "Strategy passed all criteria.",
  },
  deployment: {
    trade_id: "trade-001",
    strategy_id: "strat-001",
    status: "active",
    backtest_passed: true,
    message: "Deployed",
  },
  ace_feedback: {
    reflection: { quality: "high" },
    curation: { action: "keep" },
    playbook_stats: { entries: 5 },
  },
  summary: "Created RSI Momentum strategy for BTC/USD with 32% return.",
};

test.describe("Chat page", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the chat API
    await page.route("**/api/v1/chat", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockChatResponse),
      })
    );
  });

  test("AC1: renders textarea and send button", async ({ page }) => {
    await page.goto("/chat");
    await expect(page.getByTestId("chat-input")).toBeVisible();
    await expect(page.getByTestId("send-button")).toBeVisible();
  });

  test("AC2: send shows loading state", async ({ page }) => {
    // Delay the API response so we can observe loading
    await page.route("**/api/v1/chat", async (route) => {
      await new Promise((r) => setTimeout(r, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockChatResponse),
      });
    });

    await page.goto("/chat");
    await page.getByTestId("chat-input").fill("Create a momentum strategy");
    await page.getByTestId("send-button").click();

    // Loading indicator should appear
    await expect(page.getByTestId("loading-indicator")).toBeVisible();
  });

  test("AC3: message history shows both user and assistant messages", async ({
    page,
  }) => {
    await page.goto("/chat");
    await page.getByTestId("chat-input").fill("Create a momentum strategy");
    await page.getByTestId("send-button").click();

    // Wait for response
    await expect(page.getByTestId("message-user")).toBeVisible();
    await expect(page.getByTestId("message-assistant")).toBeVisible();

    // User message content
    await expect(page.getByTestId("message-user")).toContainText(
      "Create a momentum strategy"
    );
  });

  test("AC4: StrategyResultCard shows summary, metrics, badge, ACE feedback, view link", async ({
    page,
  }) => {
    await page.goto("/chat");
    await page.getByTestId("chat-input").fill("Test strategy");
    await page.getByTestId("send-button").click();

    // Wait for result card
    await expect(page.getByTestId("strategy-result-card")).toBeVisible();

    // Summary
    await expect(page.getByTestId("strategy-summary")).toContainText(
      "RSI Momentum"
    );

    // Metrics
    await expect(page.getByTestId("strategy-metrics")).toBeVisible();

    // Pass/fail badge
    await expect(page.getByTestId("pass-fail-badge")).toContainText("PASSED");

    // ACE feedback
    await expect(page.getByTestId("ace-feedback")).toBeVisible();

    // View link
    const viewLink = page.getByTestId("view-strategy-link");
    await expect(viewLink).toBeVisible();
    await expect(viewLink).toHaveAttribute("href", "/strategies/strat-001");
  });
});
