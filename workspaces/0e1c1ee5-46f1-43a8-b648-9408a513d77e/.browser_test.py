
import asyncio
import json
import sys
from playwright.async_api import async_playwright

async def run_browser_test():
    test_results = {
        "passed": [],
        "failed": [],
        "screenshots": []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
        page.on("pageerror", lambda err: print(f"ERROR: {err}"))
        
        try:
            # Navigate to preview
            preview_url = "" or "http://localhost:8001/api/projects/0e1c1ee5-46f1-43a8-b648-9408a513d77e/preview/index.html"
            await page.goto(preview_url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(2000)
            
            # Take initial screenshot
            await page.screenshot(path="/tmp/browser_test_initial.png")
            test_results["screenshots"].append("/tmp/browser_test_initial.png")
            
            # Check if page is not blank
            body_content = await page.inner_text("body")
            if len(body_content.strip()) > 10:
                test_results["passed"].append("✓ Seite ist nicht leer")
            else:
                test_results["failed"].append("✗ Seite scheint leer zu sein")
            
            # Run test scenarios
            scenarios = ["Pr\u00fcfen Sie, ob die Hello-World-Nachricht im H1-Element korrekt angezeigt wird."]
            
            for i, scenario in enumerate(scenarios):
                scenario_lower = scenario.lower()
                
                try:
                    # Scenario: Fill form
                    if "form" in scenario_lower or "formular" in scenario_lower:
                        # Find all input fields
                        inputs = await page.query_selector_all("input:not([type='hidden'])")
                        textareas = await page.query_selector_all("textarea")
                        
                        filled_count = 0
                        for inp in inputs:
                            input_type = await inp.get_attribute("type") or "text"
                            name = await inp.get_attribute("name") or f"field_{filled_count}"
                            
                            if input_type in ["text", "email", "tel", "url", "search"]:
                                await inp.fill("Test Input")
                                filled_count += 1
                            elif input_type == "number":
                                await inp.fill("42")
                                filled_count += 1
                            elif input_type == "date":
                                await inp.fill("2024-12-31")
                                filled_count += 1
                        
                        for textarea in textareas:
                            await textarea.fill("Test Textarea Content")
                            filled_count += 1
                        
                        if filled_count > 0:
                            test_results["passed"].append(f"✓ Formular: {filled_count} Felder ausgefüllt")
                            
                            # Try to find and click submit button
                            submit_selectors = [
                                "button[type='submit']",
                                "input[type='submit']",
                                "button:has-text('Submit')",
                                "button:has-text('Speichern')",
                                "button:has-text('Senden')",
                                "button:has-text('Save')"
                            ]
                            
                            submitted = False
                            for selector in submit_selectors:
                                try:
                                    submit_btn = await page.query_selector(selector)
                                    if submit_btn:
                                        await submit_btn.click()
                                        await page.wait_for_timeout(1000)
                                        test_results["passed"].append(f"✓ Submit Button geklickt: {selector}")
                                        submitted = True
                                        break
                                except:
                                    pass
                            
                            if not submitted:
                                test_results["failed"].append("⚠️ Kein Submit Button gefunden")
                        else:
                            test_results["failed"].append("✗ Keine Formular-Felder gefunden")
                    
                    # Scenario: Click buttons
                    elif "button" in scenario_lower or "click" in scenario_lower:
                        # Search for both <button> elements AND <a> tags styled as buttons
                        # Includes Tailwind-styled buttons (rounded-full, bg-gradient, etc.)
                        buttons = await page.query_selector_all(
                            "button:not([type='submit']), "
                            "a.btn-primary, a.btn-secondary, a.btn, "
                            "a[class*='button'], a[class*='btn'], "
                            "a[class*='rounded-full'], a[class*='bg-gradient'], "
                            "a[class*='rounded-lg'][class*='px-'], "
                            "a[class*='rounded-xl'][class*='px-'], "
                            "[role='button']"
                        )
                        
                        if buttons:
                            for j, btn in enumerate(buttons[:3]):  # Test first 3 buttons
                                btn_text = await btn.inner_text() or f"Button {j+1}"
                                try:
                                    await btn.click()
                                    await page.wait_for_timeout(500)
                                    test_results["passed"].append(f"✓ Button geklickt: {btn_text}")
                                except Exception as e:
                                    test_results["failed"].append(f"✗ Button-Click fehlgeschlagen: {btn_text}")
                        else:
                            test_results["failed"].append("✗ Keine Buttons gefunden")
                    
                    # Scenario: Navigation
                    elif "nav" in scenario_lower or "link" in scenario_lower:
                        # Include BOTH anchor links (#section) AND regular links
                        links = await page.query_selector_all("a[href], nav a, .nav a, [class*='nav'] a")
                        
                        if links:
                            for j, link in enumerate(links[:5]):  # Test first 5 links
                                link_text = await link.inner_text() or f"Link {j+1}"
                                link_href = await link.get_attribute("href")
                                
                                if link_href:
                                    try:
                                        await link.click()
                                        await page.wait_for_timeout(500)
                                        test_results["passed"].append(f"✓ Navigation: {link_text}")
                                        # Only go back for non-anchor links
                                        if not link_href.startswith("#") and not link_href.startswith("mailto:"):
                                            await page.go_back()
                                    except:
                                        test_results["failed"].append(f"✗ Navigation fehlgeschlagen: {link_text}")
                        else:
                            test_results["failed"].append("⚠️ Keine Navigation-Links gefunden")
                    
                    # Generic scenario
                    else:
                        test_results["passed"].append(f"ℹ️ Szenario notiert: {scenario}")
                
                except Exception as e:
                    test_results["failed"].append(f"✗ Szenario fehlgeschlagen: {scenario} - {str(e)}")
            
            # Take final screenshot
            await page.screenshot(path="/tmp/browser_test_final.png")
            test_results["screenshots"].append("/tmp/browser_test_final.png")
            
        except Exception as e:
            test_results["failed"].append(f"✗ Browser-Test Fehler: {str(e)}")
        
        finally:
            await browser.close()
    
    # Output results as JSON
    print("BROWSER_TEST_RESULTS_START")
    print(json.dumps(test_results, indent=2))
    print("BROWSER_TEST_RESULTS_END")

if __name__ == "__main__":
    try:
        asyncio.run(run_browser_test())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_browser_test())
        loop.close()
