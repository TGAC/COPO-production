const puppeteer = require('puppeteer'); // v20.7.4 or later

const url =  process.env.BROWSERLESS_HTTP_URL + '/sessions' ;
const get_browser_id  = async () => {
  const res = await fetch(url);
  const data = await res.json();
  return data[0].browserId;
};

let browser = null;

(async () => {
    browser_id = await get_browser_id();
    browser = await puppeteer.connect({ browserWSEndpoint: process.env.BROWSERLESS_WS_URL + '/devtools/browser/' + browser_id + '?--user-data-dir=/tmp/puppeteer' });
    const page = await browser.newPage();
    const timeout = 5000;
    page.setDefaultTimeout(timeout);

    {
        const targetPage = page;
        await targetPage.setViewport({
            width: 1512,
            height: 444
        })
    }
    {
        const targetPage = page;
        const promises = [];
        const startWaitingForEvents = () => {
            promises.push(targetPage.waitForNavigation());
        }
        startWaitingForEvents();
        await targetPage.goto(process.env.COPO_WEB_URL + '/copo');
        await Promise.all(promises);
    }
    {
      const targetPage = page;
      await puppeteer.Locator.race([
          targetPage.locator('#profile_type'),
          targetPage.locator('::-p-xpath(//*[@id=\\"profile_type\\"])'),
          targetPage.locator(':scope >>> #profile_type')
      ])
          .setTimeout(timeout)
          .click({
            offset: {
              x: 375.4765625,
              y: 11.3671875,
            },
          });
  }
  {
      const targetPage = page;
      await puppeteer.Locator.race([
          targetPage.locator('#profile_type'),
          targetPage.locator('::-p-xpath(//*[@id=\\"profile_type\\"])'),
          targetPage.locator(':scope >>> #profile_type')
      ])
          .setTimeout(timeout)
          .fill('genomics');
  }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria() >>>> ::-p-aria([role=\\"generic\\"])'),
            targetPage.locator('div.global-page-title button.primary > i'),
            targetPage.locator('::-p-xpath(/html/body/div[5]/div/div[1]/div[2]/div[2]/div[1]/span[2]/button[2]/i)'),
            targetPage.locator(':scope >>> div.global-page-title button.primary > i')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 7.5,
                y: 5.359375,
              },
            });
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(Title required )'),
            targetPage.locator('#copo\\.profile\\.title'),
            targetPage.locator('::-p-xpath(//*[@id=\\"copo.profile.title\\"])'),
            targetPage.locator(':scope >>> #copo\\.profile\\.title')
        ])
            .setTimeout(timeout)
            .fill('test Standalone profile');
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(Description required )'),
            targetPage.locator('#copo\\.profile\\.description'),
            targetPage.locator('::-p-xpath(//*[@id=\\"copo.profile.description\\"])'),
            targetPage.locator(':scope >>> #copo\\.profile\\.description')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 19,
                y: 24.0234375,
              },
            });
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(Description required )'),
            targetPage.locator('#copo\\.profile\\.description'),
            targetPage.locator('::-p-xpath(//*[@id=\\"copo.profile.description\\"])'),
            targetPage.locator(':scope >>> #copo\\.profile\\.description')
        ])
            .setTimeout(timeout)
            .fill('It is Standalone profile');
    }
 
    {
      const targetPage = page;
      await puppeteer.Locator.race([
          targetPage.locator('::-p-aria( Save)'),
          targetPage.locator('#btnFormSave'),
          targetPage.locator('::-p-xpath(//*[@id=\\"btnFormSave\\"])'),
          targetPage.locator(':scope >>> #btnFormSave'),
          targetPage.locator('::-p-text(Save)')
      ])
          .setTimeout(timeout)
          .click({
            offset: {
              x: 42.359375,
              y: 12.578125,
            },
          });
    }
    {
      const targetPage = page;
      await  targetPage.locator('::-p-xpath(//*[@class=\\"alert-message\\" and contains(@value,\\"Record updated!\\")])').setTimeout(timeout).wait()
      console.info("done")
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('#copo_profiles_table > div:nth-of-type(1) div.panel-heading i'),
            targetPage.locator('::-p-xpath(//*[@id=\\"ellipsisID\\"])'),
            targetPage.locator(':scope >>> #copo_profiles_table > div:nth-of-type(1) div.panel-heading i')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 2.265625,
                y: 10.7265625,
              },
            });
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria( Edit)'),
            targetPage.locator('#editProfileBtn'),
            targetPage.locator('::-p-xpath(//*[@id=\\"editProfileBtn\\"])'),
            targetPage.locator(':scope >>> #editProfileBtn')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 16.015625,
                y: 16.7265625,
              },
            });
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(Description required )'),
            targetPage.locator('#copo\\.profile\\.description'),
            targetPage.locator('::-p-xpath(//*[@id=\\"copo.profile.description\\"])'),
            targetPage.locator(':scope >>> #copo\\.profile\\.description')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 142,
                y: 20.0234375,
              },
            });
    }
    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria(Description required )'),
            targetPage.locator('#copo\\.profile\\.description'),
            targetPage.locator('::-p-xpath(//*[@id=\\"copo.profile.description\\"])'),
            targetPage.locator(':scope >>> #copo\\.profile\\.description')
        ])
            .setTimeout(timeout)
            .fill('It is Standalone profile. It is a updated');
    }

    {
        const targetPage = page;
        await puppeteer.Locator.race([
            targetPage.locator('::-p-aria( Save)'),
            targetPage.locator('#btnFormSave'),
            targetPage.locator('::-p-xpath(//*[@id=\\"btnFormSave\\"])'),
            targetPage.locator(':scope >>> #btnFormSave'),
            targetPage.locator('::-p-text(Save)')
        ])
            .setTimeout(timeout)
            .click({
              offset: {
                x: 42.359375,
                y: 12.578125,
              },
            });
    }

})().catch(err => {
    console.error(err);
    process.exit(1);
}).finally(() => {
    if (browser != null)
        browser.disconnect();
})