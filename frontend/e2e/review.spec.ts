import {test,expect,Page} from '@playwright/test';
async function login(page:Page){await page.goto('/');await page.getByLabel('Пароль',{exact:true}).fill('admin123');await page.getByRole('button',{name:'Войти',exact:true}).click();await expect(page.getByRole('heading',{name:'Обзор риска'})).toBeVisible();}
test('background settings response preserves edits made after request started',async({page})=>{
 await login(page);await page.getByRole('link',{name:'Настройки модели'}).click();
 await expect(page.getByLabel('Вес: Нехватка денег')).toBeVisible();
 await page.getByRole('link',{name:'Клиенты',exact:true}).click();
 let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);
 let started!:()=>void;const reading=new Promise<void>(resolve=>started=resolve);
 await page.route('**/api/v1/model/settings',async route=>{if(route.request().method()!=='GET')return route.continue();const response=await route.fetch();started();await gate;await route.fulfill({response});});
 await page.getByRole('link',{name:'Настройки модели'}).click();await reading;
 const field=page.getByLabel('Вес: Нехватка денег');const changed=(await field.inputValue())==='0.77'?'0.66':'0.77';await field.fill(changed);release();
 await expect(page.getByText('Несохранённый черновик',{exact:false})).toBeVisible();
 await expect(field).toHaveValue(changed);await expect(page.getByRole('button',{name:'Сохранить',exact:true})).toBeEnabled();
});
test('sorting preserves scroll position and table focus',async({page})=>{
 await page.setViewportSize({width:1440,height:650});await login(page);
 await page.getByRole('link',{name:'Клиенты',exact:true}).click();
 const sort=page.getByRole('button',{name:/Ожидаемые потери, EUR/});await expect(sort).toBeVisible();
 await sort.scrollIntoViewIfNeeded();await sort.focus();
 const before=await page.evaluate(()=>window.scrollY);expect(before).toBeGreaterThan(0);
 const response=page.waitForResponse(r=>r.url().includes('/customers?')&&r.url().includes('sort=expectedLoss'));
 await sort.click();await response;await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
 expect(Math.abs(await page.evaluate(()=>window.scrollY)-before)).toBeLessThan(8);await expect(sort).toBeFocused();
});
test('custom factor is created disabled, enabled and saved with its rule',async({page})=>{
 await login(page);await page.getByRole('link',{name:'Настройки модели'}).click();
 await page.getByRole('button',{name:'Добавить фактор',exact:true}).click();
 await page.getByLabel('Название фактора',{exact:true}).fill('Ближайшие три дня');
 await page.getByRole('button',{name:'Добавить в черновик'}).click();
 await page.getByRole('button',{name:'Изменить фактор Ближайшие три дня'}).click();
 await page.getByLabel('Оценка при выполнении, 0–100').fill('80');
 await page.getByRole('button',{name:'Обновить в черновике'}).click();
 await expect(page.locator('.custom-rule',{hasText:'Ближайшие три дня'})).toContainText('80 из 100');
 const toggle=page.getByLabel('Включить: Ближайшие три дня');await expect(toggle).not.toBeChecked();
 await toggle.check();await page.getByRole('button',{name:'Сохранить',exact:true}).click();
 await expect(page.getByText('Настройки сохранены.',{exact:false})).toBeVisible();
 await page.reload();await expect(page.getByLabel('Включить: Ближайшие три дня')).toBeChecked();
});
