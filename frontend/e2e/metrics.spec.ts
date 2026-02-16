import { test, expect } from "@playwright/test";

const mockMetricsResponse = {
  llm_usage: [
    {
      provider: "anthropic",
      model: "claude-3",
      total_calls: 150,
      total_prompt_tokens: 50000,
      total_completion_tokens: 25000,
      avg_latency_ms: 320,
    },
    {
      provider: "openai",
      model: "gpt-4",
      total_calls: 80,
      total_prompt_tokens: 30000,
      total_completion_tokens: 15000,
      avg_latency_ms: 450,
    },
  ],
  tool_calls: [
    { tool: "backtest", count: 45 },
    { tool: "deploy", count: 12 },
    { tool: "rag_query", count: 30 },
  ],
  agent_actions: [
    { agent: "strategist", action: "create", count: 20 },
    { agent: "backtester", action: "run", count: 45 },
    { agent: "deployer", action: "deploy", count: 12 },
  ],
};

test.describe("Metrics page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/metrics", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockMetricsResponse),
      })
    );
  });

  test("AC8: renders stat cards with correct data", async ({ page }) => {
    await page.goto("/metrics");
    await expect(page.getByTestId("stat-cards")).toBeVisible();

    // Total Calls: 150 + 80 = 230
    await expect(page.getByTestId("stat-calls")).toContainText("230");

    // Total Tokens: 50000+25000+30000+15000 = 120,000
    await expect(page.getByTestId("stat-tokens")).toContainText("120,000");

    // Avg Latency: (320+450)/2 = 385
    await expect(page.getByTestId("stat-latency")).toContainText("385 ms");
  });

  test("AC9: three tabs switchable", async ({ page }) => {
    await page.goto("/metrics");
    await expect(page.getByTestId("metrics-tabs")).toBeVisible();

    // LLM tab is default
    await expect(page.getByTestId("tab-llm")).toBeVisible();
    await expect(page.getByTestId("tab-tools")).toBeVisible();
    await expect(page.getByTestId("tab-agents")).toBeVisible();

    // LLM table visible by default
    await expect(page.getByTestId("llm-table")).toBeVisible();

    // Switch to Tools tab
    await page.getByTestId("tab-tools").click();
    await expect(page.getByTestId("tools-table")).toBeVisible();

    // Switch to Agents tab
    await page.getByTestId("tab-agents").click();
    await expect(page.getByTestId("agents-table")).toBeVisible();
  });

  test("AC10: charts render in each tab", async ({ page }) => {
    await page.goto("/metrics");

    // LLM chart (default tab)
    await expect(page.getByTestId("llm-chart")).toBeVisible();

    // Tools chart
    await page.getByTestId("tab-tools").click();
    await expect(page.getByTestId("tools-chart")).toBeVisible();

    // Agents chart
    await page.getByTestId("tab-agents").click();
    await expect(page.getByTestId("agents-chart")).toBeVisible();
  });
});
