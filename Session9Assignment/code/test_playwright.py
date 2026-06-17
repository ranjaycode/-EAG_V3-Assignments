from playwright.sync_api import sync_playwright
import time
import urllib.parse

async def _setup_amazon_mocking(page):
    async def route_handler(route):
        url = route.request.url
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        
        # 1. Home Page
        if path == "/" or path == "":
            html = """
            <html>
            <head><title>Online Shopping site in India: Shop Online for Mobiles, Books, Watches, Shoes and More - Amazon.in</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #FF9900;">Amazon.in</h1>
                <form action="/s" method="GET">
                    <input type="text" id="twotabsearchtextbox" name="field-keywords" style="width: 400px; padding: 10px;" placeholder="Search Amazon.in" />
                    <input type="submit" id="nav-search-submit-button" value="Search" style="padding: 10px;" />
                </form>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return

        # 2. Search Results
        if path.startswith("/s"):
            html = """
            <html>
            <head><title>Amazon.in : gaming laptops under 80000</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #FF9900;">Search Results for Gaming Laptops</h1>
                <div style="display: flex;">
                    <div id="sidebar" style="width: 250px; border-right: 1px solid #ccc; padding-right: 20px;">
                        <h3>Brands</h3>
                        <ul>
                            <li id="p_89/ASUS" style="list-style: none; margin-bottom: 10px;">
                                <a href="/s?k=gaming+laptop&rh=p_89%3AASUS" class="a-link-normal" style="text-decoration: none; color: #0066c0;">
                                    <span class="a-size-base a-color-base" style="font-weight: bold;">ASUS</span>
                                </a>
                            </li>
                            <li id="p_89/HP" style="list-style: none; margin-bottom: 10px;">
                                <a href="/s?k=gaming+laptop&rh=p_89%3AHP" class="a-link-normal" style="text-decoration: none; color: #0066c0;">
                                    <span class="a-size-base a-color-base" style="font-weight: bold;">HP</span>
                                </a>
                            </li>
                        </ul>
                        <h3>Sort By</h3>
                        <div class="a-dropdown-container">
                            <select id="s-result-sort-select" style="padding: 5px;">
                                <option value="relevance">Featured</option>
                                <option value="review-rank" selected>Customer Review</option>
                            </select>
                            <br/><br/>
                            <a href="#" id="s-result-sort-select_3" style="text-decoration: none; color: #0066c0; font-weight: bold;">Customer Review</a>
                        </div>
                    </div>
                    <div id="results" style="flex-grow: 1; padding-left: 20px;">
                        <div class="s-main-slot">
                            <!-- spacer item to align with :nth-child(2) -->
                            <div class="s-result-item" data-index="1" data-component-type="s-search-result" style="display:none;"></div>
                            
                            <div class="s-result-item" data-index="2" data-component-type="s-search-result" style="border-bottom: 1px solid #eee; padding: 15px 0;">
                                <h2><a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal" href="/dp/ASUS-TUF-Gaming-F15" style="text-decoration: none; color: #0066c0;">ASUS TUF Gaming F15</a></h2>
                                <p style="color: #555;"><span class="a-icon-alt">4.6 out of 5 stars</span> | Price: ₹64,990</p>
                            </div>
                            <div class="s-result-item" data-index="3" data-component-type="s-search-result" style="border-bottom: 1px solid #eee; padding: 15px 0;">
                                <h2><a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal" href="/dp/HP-Victus-Gaming" style="text-decoration: none; color: #0066c0;">HP Victus Gaming Laptop</a></h2>
                                <p style="color: #555;"><span class="a-icon-alt">4.5 out of 5 stars</span> | Price: ₹58,990</p>
                            </div>
                            <div class="s-result-item" data-index="4" data-component-type="s-search-result" style="border-bottom: 1px solid #eee; padding: 15px 0;">
                                <h2><a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal" href="/dp/ASUS-Vivobook-Gaming" style="text-decoration: none; color: #0066c0;">ASUS Vivobook Gaming</a></h2>
                                <p style="color: #555;"><span class="a-icon-alt">4.4 out of 5 stars</span> | Price: ₹74,990</p>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return

        # 3. Product Details
        if "ASUS-TUF-Gaming-F15" in url or "ASUS-TUF-Gaming-F15" in path:
            html = """
            <html>
            <head><title>ASUS TUF Gaming F15 (2026)</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 id="title">ASUS TUF Gaming F15</h1>
                <h1 id="productTitle">ASUS TUF Gaming F15</h1>
                <h2>Product Specifications</h2>
                <table id="productDetails_techSpec_section_1" border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse;">
                    <tr><td>Processor Type</td><td>Intel Core i5-11400H</td></tr>
                    <tr><td>RAM Size</td><td>16GB</td></tr>
                    <tr><td>Price</td><td>₹64,990</td></tr>
                </table>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return

        if "HP-Victus-Gaming" in url or "HP-Victus-Gaming" in path:
            html = """
            <html>
            <head><title>HP Victus Gaming Laptop (2026)</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 id="title">HP Victus Gaming Laptop</h1>
                <h1 id="productTitle">HP Victus Gaming Laptop</h1>
                <h2>Product Specifications</h2>
                <table id="productDetails_techSpec_section_1" border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse;">
                    <tr><td>Processor Type</td><td>AMD Ryzen 5 5600H</td></tr>
                    <tr><td>RAM Size</td><td>8GB</td></tr>
                    <tr><td>Price</td><td>₹58,990</td></tr>
                </table>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return

        if "ASUS-Vivobook-Gaming" in url or "ASUS-Vivobook-Gaming" in path:
            html = """
            <html>
            <head><title>ASUS Vivobook Gaming (2026)</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 id="title">ASUS Vivobook Gaming</h1>
                <h1 id="productTitle">ASUS Vivobook Gaming</h1>
                <h2>Product Specifications</h2>
                <table id="productDetails_techSpec_section_1" border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse;">
                    <tr><td>Processor Type</td><td>Intel Core i7-12650H</td></tr>
                    <tr><td>RAM Size</td><td>16GB</td></tr>
                    <tr><td>Price</td><td>₹74,990</td></tr>
                </table>
            </body>
            </html>
            """
            await route.fulfill(status=200, content_type="text/html", body=html)
            return
            
        await route.continue_()

    await page.route("**/*amazon.in*", route_handler)

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        def route_handler_sync(route):
            url = route.request.url
            parsed_url = urllib.parse.urlparse(url)
            path = parsed_url.path
            print(f"Request: {url} (path: {path})")
            if path == "/" or path == "":
                html = '<html><body><form action="/s" method="GET"><input type="text" id="twotabsearchtextbox" name="k" /><input type="submit" id="nav-search-submit-button" /></form></body></html>'
                route.fulfill(status=200, content_type="text/html", body=html)
                return
            elif path.startswith("/s"):
                html = '<html><body><div class="s-main-slot"><div class="s-result-item"><a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal" href="https://www.amazon.in/dp/ASUS-TUF-Gaming-F15">ASUS</a></div></div></body></html>'
                route.fulfill(status=200, content_type="text/html", body=html)
                return
            elif "ASUS-TUF-Gaming-F15" in url:
                html = '<html><body><h1 id="title">ASUS TUF</h1><table id="productDetails_techSpec_section_1"><tr><td>Processor Type</td><td>Intel i5</td></tr></table></body></html>'
                route.fulfill(status=200, content_type="text/html", body=html)
                return
            route.continue_()

        page.route(lambda url: "amazon.in" in url, route_handler_sync)
        
        page.goto("https://www.amazon.in")
        print("Home URL:", page.url)
        page.fill("#twotabsearchtextbox", "gaming laptop")
        page.click("#nav-search-submit-button")
        
        # Click the link
        selector = "a.a-link-normal.s-underline-text.s-underline-link-text.s-link-style.a-text-normal"
        page.wait_for_selector(selector)
        print("Search URL:", page.url)
        page.eval_on_selector(selector, "el => el.click()")
        
        page.wait_for_timeout(3000)
        print("Product URL:", page.url)
        browser.close()

if __name__ == "__main__":
    test()



