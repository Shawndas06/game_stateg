"""Exercise the built application, not a development-only component preview.

Run a local server first, then: python tests/browser_campaign.py
"""
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright,expect

url = os.environ.get("BROWSER_TEST_URL", "http://127.0.0.1:8000")
if urlparse(url).hostname not in {"127.0.0.1", "localhost"}:
    raise RuntimeError("This mutating browser check only runs against a local test server")


def run(browser_type, width, height):
    browser = browser_type.launch()
    context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="domcontentloaded")
    page.get_by_text("Другие режимы",exact=True).click()
    page.get_by_role("button", name="Начать историю").click()
    page.get_by_role("heading", name="Первый диван").wait_for()
    # The third choice must be reachable even when it starts below the fold.
    page.get_by_role("button", name="Начать с запасов и управления").scroll_into_view_if_needed()
    page.get_by_role("button", name="Дать пограничным беям").click()
    page.get_by_role("button", name="Карта", exact=True).click()
    page.get_by_role("heading", name="Атлас державы").wait_for()
    page.locator('.map-load-state').wait_for(state='hidden')
    page.get_by_role('button',name='Развернуть карту',exact=True).click()
    cities=page.request.get(url+'/api/catalog').json()['places']
    assert page.locator('[data-place]').count()>0
    # Hit every visible fortress at its actual rendered target, on both scales.
    names={city['id']:city['name'] for city in cities}
    for zoom in range(2):
        for marker in page.locator('[data-place]').all():
            city=marker.get_attribute('data-place')
            box=marker.locator('.place-hit-target').bounding_box()
            assert box and box['width']>=44 and box['height']>=44
            camera=page.locator('[data-coastline]').evaluate('(el)=>el.parentElement.getAttribute("transform")')
            marker.locator('.place-hit-target').click()
            expect(page.locator('.place-card h2')).to_contain_text(names[city])
            assert page.locator('[data-coastline]').evaluate('(el)=>el.parentElement.getAttribute("transform")')==camera,'Selecting an on-screen marker must not move its neighbours'
        page.get_by_role('button',name='Приблизить карту',exact=True).click()
    page.get_by_role('button',name='Весь мир',exact=False).click()
    assert page.locator('.original-world-map').count()==0
    assert page.locator('[data-overview-place]').count()==len(cities)
    page.get_by_label('Регион карты',exact=True).select_option('straits')
    assert page.locator('[data-overview-place="constantinople"]').count()==1
    # Search crosses regional bounds and must expose each real settlement;
    # the same selected ID is read back through the province card.
    check_cities=cities if width==390 and browser_type.name=='chromium' else [city for city in cities if city['id'] in ['sogut','bursa','constantinople','galata','chrysopolis','chalcedon','domanic','lisbon','cairo']]
    for index,city in enumerate(check_cities):
        if index%40==0:print(f'{browser_type.name} {width}: settlement {index+1}/{len(check_cities)}',flush=True)
        page.get_by_label('Поиск поселения',exact=True).fill(city['name'])
        result=page.locator(f'[data-search-place="{city["id"]}"]')
        result.first.click()
        marker=page.get_by_test_id('place-'+city['id'])
        marker.locator('.place-hit-target').click()
        assert page.locator('.place-card h2').inner_text().startswith(city['name'])
    page.get_by_label('Поиск поселения',exact=True).fill('Доманич')
    page.locator('.atlas-search-results button').filter(has_text='Доманич').click()
    assert page.get_by_role('button',name='При Мураде I',exact=True).is_disabled()
    page.get_by_label('Поиск поселения',exact=True).fill('Бурса')
    page.locator('.atlas-search-results button').filter(has_text='Бурса').click()
    page.keyboard.press('Escape')
    page.get_by_role("heading", name="Бурса", exact=False).wait_for()
    page.get_by_role("button", name="Армии", exact=True).click()
    page.get_by_role("heading", name="Походная армия").wait_for()
    page.get_by_role("button", name="Инегёль →", exact=True).click()
    page.get_by_role("button", name="Завершить сезон").click()
    page.get_by_role("button", name="Подтвердить приказы").click()
    page.get_by_text("Текущий план: блокада.").wait_for()
    for label in ("Совет", "Карта", "Держава", "Армии", "Развитие"):
        page.get_by_role("button", name=label, exact=True).click()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), label
    page.reload(wait_until="domcontentloaded")
    page.get_by_role("button", name="Армии", exact=True).click()
    page.get_by_text("Текущий план: блокада.").wait_for()
    if os.environ.get("BROWSER_SCREENSHOTS"):
        out = Path(os.environ["BROWSER_SCREENSHOTS"])
        out.mkdir(parents=True, exist_ok=True)
        for label in ("Совет", "Карта", "Армии", "Развитие"):
            page.get_by_role("button", name=label, exact=True).click()
            page.screenshot(path=str(out / f"{browser_type.name}-{width}-{label}.png"), full_page=True)
    assert not errors, errors
    context.close()
    browser.close()
    print(f"PASS {browser_type.name} {width}x{height}: choices, map hit, orders, siege, all tabs, persisted reload")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright.chromium, 390, 844)
        run(playwright.chromium, 320, 740)
        if os.environ.get("BROWSER_WEBKIT") == "1":
            run(playwright.webkit, 390, 844)
