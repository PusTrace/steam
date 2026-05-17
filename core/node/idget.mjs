/**
 * Steam Market Skin Scraper
 * ─────────────────────────
 * Читает все name из таблицы skins,
 * ищет каждый на Steam Market CS2 (appid=730),
 * извлекает market_hash_name из URL
 * и сохраняет в таблицу skin_hashes.
 *
 * Установка:
 *   npm install
 *   npx playwright install chromium
 *
 * Использование:
 *   node scraper.js            ← обрабатывает все скины из skins
 *   node scraper.js --skip-existing  ← пропускает уже найденные
 */

import { chromium } from "playwright";
import pg from "pg";

const { Pool } = pg;

// ─── Конфиг БД ────────────────────────────────────────────────────────────────
const pool = new Pool({
  host: "localhost",
  port: 5432,
  database: "database",
  user: "postgres",
  password: "password",
});

// ─── Создание таблицы если не существует ──────────────────────────────────────
async function initDb() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS skin_hashes (
      id               SERIAL PRIMARY KEY,
      name             TEXT NOT NULL UNIQUE,
      market_hash_name TEXT NOT NULL
    )
  `);
  console.log("✅ Таблица skin_hashes готова\n");
}

// ─── Получить все name из skins ───────────────────────────────────────────────
async function getSkinNames(skipExisting) {
  if (skipExisting) {
    // Только те, которых ещё нет в skin_hashes
    const res = await pool.query(`
      SELECT s.name
      FROM skins s
      WHERE NOT EXISTS (
        SELECT 1 FROM skin_hashes h WHERE h.name = s.name
      )
      ORDER BY s.id
    `);
    return res.rows.map((r) => r.name);
  } else {
    const res = await pool.query(`SELECT name FROM skins ORDER BY id`);
    return res.rows.map((r) => r.name);
  }
}

// ─── Сохранение в БД ─────────────────────────────────────────────────────────
const WEARS = [
  "Factory New",
  "Minimal Wear", 
  "Field-Tested",
  "Well-Worn",
  "Battle-Scarred",
];

async function saveSkinAllWears(name, marketHashName) {
  // Извлекаем базовое имя без потёртости: "StatTrak™ P90 | Randy Rush"
  const baseMatch = name.match(/^(.+?)\s*\((?:Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)$/);
  if (!baseMatch) {
    // Нет потёртости в имени — сохраняем как есть
    await saveSkin(name, marketHashName);
    return;
  }

  const baseName = baseMatch[1]; // "StatTrak™ P90 | Randy Rush"

  for (const wear of WEARS) {
    const fullName = `${baseName} (${wear})`;
    await saveSkin(fullName, marketHashName);
  }
}

async function saveSkin(name, marketHashName) {
  const res = await pool.query(
    `INSERT INTO skin_hashes (name, market_hash_name)
     VALUES ($1, $2)
     ON CONFLICT (name) DO NOTHING
     RETURNING id`,
    [name, marketHashName]
  );
  if (res.rows.length > 0) {
    console.log(`  ✅ Добавлен (id=${res.rows[0].id}): "${name}" → ${marketHashName}`);
  } else {
    console.log(`  ⏭️  Пропущен (уже есть): "${name}"`);
  }
}

// ─── Playwright: поиск одного скина ──────────────────────────────────────────
async function scrapeSkin(page, skinName) {
  console.log(`\n🔍 "${skinName}"`);

  try {
    // 1. Открываем страницу поиска
    await page.goto("https://steamcommunity.com/market/search?appid=730", {
      waitUntil: "domcontentloaded",
      timeout: 30_000,
    });
    await page.waitForTimeout(1500);

    // 2. Вводим название — fill() мгновенно, без посимвольной задержки
    const searchInput = page.locator('input[placeholder="New search..."]');
    await searchInput.waitFor({ state: "visible", timeout: 15_000 });
    await searchInput.click();
    await searchInput.fill(skinName);

    // 3. Ждём появления автодополнения — без фиксированной паузы
    const firstOption = page.locator('[role="option"]').first();
    await firstOption.waitFor({ state: "visible", timeout: 10_000 });

    // 4. Берём href из <a> внутри option — NO клик, NO навигация
    const link = firstOption.locator("a").first();
    const href = await link.getAttribute("href", { timeout: 3_000 }).catch(() => null);

    let finalUrl;
    if (href && href.includes("/market/listings/730/")) {
      // Есть href — берём напрямую, браузер никуда не переходит
      finalUrl = href.startsWith("http")
        ? href
        : "https://steamcommunity.com" + href;
    } else {
      // Fallback: href нет — кликаем и ждём навигацию
      await Promise.all([
        page.waitForNavigation({ timeout: 15_000 }),
        firstOption.click(),
      ]);
      finalUrl = page.url();
    }

    console.log(`  🔗 ${finalUrl}`);

    // 5. Извлекаем market_hash_name
    const match = finalUrl.match(/\/market\/listings\/730\/(.+)$/);
    if (!match) {
      console.error(`  ❌ Не удалось извлечь market_hash_name`);
      return null;
    }

    const marketHashName = decodeURIComponent(match[1]);
    return { name: skinName, marketHashName };
  } catch (err) {
    console.error(`  ❌ Ошибка: ${err.message}`);
    await page
      .screenshot({ path: `debug_${skinName.replace(/[^a-z0-9]/gi, "_")}.png` })
      .catch(() => {});
    return null;
  }
}

// ─── Проверка есть ли уже скин в базе ────────────────────────────────────────
async function isAlreadyScraped(name) {
  const baseMatch = name.match(/^(.+?)\s*\((?:Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)$/);
  const baseName = baseMatch ? baseMatch[1] : name;

  const res = await pool.query(
    `SELECT 1 FROM skin_hashes WHERE name LIKE $1 LIMIT 1`,
    [`${baseName}%`]
  );
  return res.rows.length > 0;
}

// ─── Точка входа ──────────────────────────────────────────────────────────────
async function main() {
  const skipExisting = process.argv.includes("--skip-existing");

  await initDb();

  // Читаем скины из БД
  const names = await getSkinNames(skipExisting);

  if (names.length === 0) {
    console.log(
      skipExisting
        ? "✨ Все скины из skins уже есть в skin_hashes."
        : "⚠️  Таблица skins пуста."
    );
    await pool.end();
    return;
  }

  

  console.log(`📋 Найдено скинов для обработки: ${names.length}`);
  if (skipExisting) console.log("   (пропускаем уже существующие)\n");

  // Один браузер на весь прогон — быстрее
  const browser = await chromium.launch({
    headless: false, // поменяй на true для фонового режима
    args: ["--no-sandbox"],
  });

  const context = await browser.newContext({
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
      "AppleWebKit/537.36 (KHTML, like Gecko) " +
      "Chrome/124.0.0.0 Safari/537.36",
    locale: "en-US",
  });

  const page = await context.newPage();

  let success = 0;
  let failed = 0;

  for (let i = 0; i < names.length; i++) {
    const name = names[i];
    console.log(`\n[${i + 1}/${names.length}]`);
  // ← Новая проверка
  if (await isAlreadyScraped(name)) {
    console.log(`⏭️  Уже в базе, пропускаем: "${name}"`);
    success++;
    continue;
  }
    const result = await scrapeSkin(page, name);

if (result) {
  await saveSkinAllWears(result.name, result.marketHashName); // ← было saveSkin
  success++;
}else {
      console.log(`  ⚠️  Пропущен: "${name}"`);
      failed++;
    }

    // Небольшая пауза между запросами чтобы не получить бан
    if (i < names.length - 1) {
      await page.waitForTimeout(800);
    }
  }

  await browser.close();
  await pool.end();

  console.log(`\n${"═".repeat(45)}`);
  console.log(`✅ Готово! Успешно: ${success}, ошибок: ${failed}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
