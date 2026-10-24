import {test,expect} from '@playwright/test';
for(const width of [1920,1440,1129,900,899,768,360]){
 test(`clients content stays beside navigation at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});
  await page.goto('/');await page.getByLabel('Пароль',{exact:true}).fill('admin123');
  await page.getByRole('button',{name:'Войти',exact:true}).click();
  if(width<900)await page.getByRole('button',{name:'Открыть меню'}).click();
  await page.getByRole('link',{name:'Клиенты',exact:true}).click();
  await expect(page.getByRole('button',{name:'Экспорт CSV',exact:true})).toBeEnabled();
  const dimensions=await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth,x:scrollX}));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.width);
  expect(dimensions.x).toBe(0);
  if(width>=900){
   const sidebar=await page.locator('.sidebar').boundingBox();
   const heading=await page.locator('#customers-heading').boundingBox();
   expect(heading!.x).toBeGreaterThanOrEqual(sidebar!.x+sidebar!.width);
  }
  const table=page.getByRole('region',{name:'Таблица клиентов',exact:true});
  const box=await table.boundingBox();expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x+box!.width).toBeLessThanOrEqual(width+1);
  const overflowing=await table.evaluate(el=>el.scrollWidth>el.clientWidth);
  if(width===1129)expect(overflowing).toBe(true);
  if(overflowing){
   await table.scrollIntoViewIfNeeded();await table.hover();await page.mouse.wheel(1200,0);
   await expect.poll(()=>table.evaluate(el=>el.scrollLeft)).toBeGreaterThan(0);
   expect(await page.evaluate(()=>window.scrollX)).toBe(0);
  }
 });
}
