import { expect, test } from "@playwright/test";

/**
 * P1 Source Library E2E (upload path only — no network, no yt-dlp).
 *
 * Preconditions (the spec does not start servers other than the web app via playwright.config.ts):
 *   - the StoryWeaver API is running on http://localhost:8000 against a DISPOSABLE database that has
 *     the P1 migration applied (e.g. the local `storyweaver` database from `make db-up-nodocker`,
 *     never a shared or hosted database);
 *   - NEXT_PUBLIC_API_URL is unset or http://localhost:8000;
 *   - PLAYWRIGHT_CHROMIUM_PATH is set on OSes Playwright cannot install a browser for.
 * Each run uses a unique word, so reruns against the same database do not collide.
 */
test("upload a transcript, find it by keyword, and see the duplicate notice", async ({ page }) => {
  const word = `zebraquartz${Date.now().toString(36)}`;
  const title = `E2E transcript ${word}`;
  const body = `Early humans crossed the frozen plain. The ${word} herd moved south before winter.`;
  const upload = (name: string, text: string) => ({
    name,
    mimeType: "text/plain",
    buffer: Buffer.from(text),
  });

  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

  // 1. Upload
  await page.goto("/sources/videos");
  await page.getByRole("button", { name: "Add source" }).click();
  await page.getByRole("tab", { name: "Upload or paste" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByLabel(/Transcript file/).setInputFiles(upload("talk.txt", body));
  await page.getByRole("button", { name: "Add transcript" }).click();
  await expect(page.getByText(/Added\./)).toBeVisible();
  await page.keyboard.press("Escape");

  // 2. It appears exactly once in the library
  await page.goto("/sources/videos");
  await expect(page.getByRole("link", { name: title })).toHaveCount(1);

  // 3. Keyword search finds it, with the match highlighted
  await page.getByLabel("Search transcripts").fill(word);
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(new RegExp(`q=${word}`));
  const results = page.getByRole("list", { name: "Search results" });
  await expect(results.getByRole("link", { name: title })).toBeVisible();
  await expect(results.locator("mark", { hasText: word })).toBeVisible();

  // 4. Uploading the same text again (different file name and title) shows the duplicate notice
  await page.goto("/sources/videos");
  await page.getByRole("button", { name: "Add source" }).click();
  await page.getByRole("tab", { name: "Upload or paste" }).click();
  await page.getByLabel("Title").fill(`${title} (again)`);
  await page.getByLabel(/Transcript file/).setInputFiles(upload("again.txt", body));
  await page.getByRole("button", { name: "Add transcript" }).click();
  await expect(page.getByRole("status")).toContainText(/already in your library/i);
  await page.keyboard.press("Escape");

  // 5. Still exactly one source for this transcript
  await page.goto(`/sources/videos?q=${word}`);
  await expect(
    page.getByRole("list", { name: "Search results" }).getByRole("listitem"),
  ).toHaveCount(1);

  expect(errors, `console/page errors: ${errors.join(" | ")}`).toEqual([]);
});
