"""Actual menu/navigation interactions shared by the browser scenarios."""
from playwright.sync_api import expect


def new_game(page,mode='long'):
    page.get_by_role('button',name='Новая игра',exact=True).click()
    page.get_by_label('Сценарий кампании',exact=True).select_option(mode)
    page.get_by_role('button',name='Начать кампанию',exact=True).click()


def resume_menu(page):
    button=page.get_by_role('button',name='Продолжить',exact=True)
    expect(page.locator('.campaign-main-menu')).to_be_visible()
    expect(button).to_be_enabled();button.click()


def nav(page,title):
    title={'Двор':'Совет','Атлас':'Карта','Держава':'Государство'}.get(title,title)
    page.get_by_role('button',name='Правление',exact=True).click()
    page.get_by_role('dialog',name='Правление',exact=True).get_by_role('button',name=title,exact=True).click()
