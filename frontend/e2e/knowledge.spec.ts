import { test, expect } from "@playwright/test";

const mockIngestResponse = {
  message: "Ingested 3 chunks successfully",
  chunks: 3,
};

const mockQueryResponse = {
  query: "momentum",
  results: [
    {
      source: "research-paper.pdf",
      content: "Momentum strategies rely on trend persistence...",
      similarity: 0.92,
    },
    {
      source: "trading-guide.md",
      content: "RSI momentum is a popular indicator...",
      similarity: 0.85,
    },
  ],
};

test.describe("Knowledge page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/rag/ingest", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockIngestResponse),
      })
    );
    await page.route("**/api/v1/rag/query", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockQueryResponse),
      })
    );
  });

  test("AC5: renders upload and search sections", async ({ page }) => {
    await page.goto("/knowledge");
    await expect(page.getByTestId("upload-section")).toBeVisible();
    await expect(page.getByTestId("search-section")).toBeVisible();

    // Upload fields
    await expect(page.getByTestId("upload-content")).toBeVisible();
    await expect(page.getByTestId("upload-source")).toBeVisible();
    await expect(page.getByTestId("upload-button")).toBeVisible();

    // Search fields
    await expect(page.getByTestId("search-query")).toBeVisible();
    await expect(page.getByTestId("search-top-k")).toBeVisible();
    await expect(page.getByTestId("search-button")).toBeVisible();
  });

  test("AC6: upload shows success message", async ({ page }) => {
    await page.goto("/knowledge");
    await page
      .getByTestId("upload-content")
      .fill("Some research content about trading");
    await page.getByTestId("upload-source").fill("research.pdf");
    await page.getByTestId("upload-button").click();

    await expect(page.getByTestId("upload-result")).toContainText(
      "Ingested 3 chunks successfully"
    );
  });

  test("AC7: search returns result cards", async ({ page }) => {
    await page.goto("/knowledge");
    await page.getByTestId("search-query").fill("momentum");
    await page.getByTestId("search-button").click();

    // Should have 2 result cards
    const cards = page.getByTestId("result-card");
    await expect(cards).toHaveCount(2);

    // First card should have source and similarity
    await expect(cards.first()).toContainText("research-paper.pdf");
    await expect(cards.first()).toContainText("92.0%");
  });
});
