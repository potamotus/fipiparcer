"""Диагностика пагинации: какой параметр у ФИПИ работает и есть ли там кнопка."""
import asyncio
from playwright.async_api import async_playwright

PROJ = "DE0E276E497AB3784C3FC4CC20248DC0"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1400, "height": 2400},
            locale="ru-RU",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            ignore_https_errors=True,
        )
        page = await ctx.new_page()

        # 1) Без фильтра — сколько и есть ли пагинация?
        url0 = f"https://oge.fipi.ru/bank/questions.php?proj={PROJ}"
        print(f"[1] open {url0}")
        await page.goto(url0, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_load_state("networkidle", timeout=20_000)
        await asyncio.sleep(3)
        n0 = await page.locator(".qblock").count()
        print(f"   qblock: {n0}")

        # JS — посмотреть все глобальные функции с pagination-related именами
        fns = await page.evaluate("""
            () => {
                const names = [];
                for (const k of Object.keys(window)) {
                    if (typeof window[k] === 'function' && /page|next|prev|go|change|load|show|nav|fetch/i.test(k)) {
                        names.push(k);
                    }
                }
                return names;
            }
        """)
        print(f"   pagination-related global funcs: {fns[:30]}")

        # Все onclick содержащие page/next/prev/go/change
        onclicks = await page.evaluate("""
            () => {
                const els = [...document.querySelectorAll('[onclick]')];
                return els
                    .map(e => ({tag: e.tagName, text: (e.innerText || '').trim().slice(0, 40), onclick: e.getAttribute('onclick')}))
                    .filter(o => /page|next|prev|navigate|go\\(|show|change/i.test(o.onclick));
            }
        """)
        print(f"\n   pagination-related onclick:")
        for o in onclicks[:15]:
            print(f"     <{o['tag']}> «{o['text']}» onclick={o['onclick']!r}")

        # Network requests на текущей странице — какие AJAX делает ФИПИ
        print("\n[2] перехват AJAX (POST/GET к ajax-endpoint) при попытке клика по «Найти»")
        requests = []
        page.on("request", lambda r: requests.append({"url": r.url, "method": r.method, "post": r.post_data and r.post_data[:200]}))

        # Попробовать найти и кликнуть кнопку фильтра/поиска
        for sel in ["text=Найти", ".button-find", "[onclick*=filter]"]:
            loc = page.locator(sel).first
            if await loc.count():
                try:
                    await loc.click(force=True, timeout=5_000)
                    print(f"   clicked: {sel}")
                    break
                except Exception:
                    continue
        await asyncio.sleep(3)
        ajax_likes = [r for r in requests if "ajax" in r["url"].lower() or "questions" in r["url"].lower() or r["method"] == "POST"]
        for r in ajax_likes[:15]:
            print(f"     {r['method']} {r['url']}  post={r['post']!r}")

        # 3) Проверить разные параметры URL
        print("\n[3] пробую разные URL-параметры пагинации")
        for param in ["pagenum", "page", "p", "start", "offset", "from", "qb_pageno", "pgnum"]:
            test_url = f"https://oge.fipi.ru/bank/questions.php?proj={PROJ}&{param}=2"
            await page.goto(test_url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_load_state("networkidle", timeout=10_000)
            await asyncio.sleep(1.5)
            n = await page.locator(".qblock").count()
            first_id = await page.locator(".qblock").first.evaluate("el => el.id") if n else ""
            print(f"   ?{param}=2 → qblock: {n}, first id: {first_id}")

        # 4) Есть ли JSON-endpoint?
        print("\n[4] пробую questions.php напрямую POST'ом (как AJAX)")
        try:
            resp = await ctx.request.post(
                f"https://oge.fipi.ru/bank/questions.php?proj={PROJ}",
                form={"pagenum": "2"},
            )
            text = await resp.text()
            print(f"   status={resp.status}, len={len(text)}")
            print(f"   first 400 chars:\n     {text[:400]!r}")
        except Exception as e:
            print(f"   FAIL: {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
