"""Gera os 6 PDFs (Diário e Destaques em Taxa 1, 2 e 3) usando o próprio portal num Chrome headless.
Uso: python3 gerar_pdfs.py <caminho do index.html> <pasta de saída>"""
import asyncio, base64, sys, shutil
from playwright.async_api import async_playwright
HTML, OUT = sys.argv[1], sys.argv[2]
INIT = "localStorage.clear(); window.claude={use:async(n)=>({save:async(o)=>{window.__saved=o.filename;return {status:'saved'}}})};"
async def main():
    exe = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe else await p.chromium.launch(args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1500, "height": 900})
        await pg.add_init_script(INIT)
        await pg.goto("file://" + HTML + "#destaques"); await pg.wait_for_timeout(1500)
        for m in ("m0", "m2", "m1"):          # Taxa 1, Taxa 2, Taxa 3
            await pg.click("#" + m); await pg.wait_for_timeout(300)
            for btn in ("#pdfall", "#pdfdest"):
                await pg.evaluate("window.__saved=null")
                await pg.click(btn); await pg.wait_for_timeout(400); await pg.click("#ex-go")
                for _ in range(120):
                    await pg.wait_for_timeout(500)
                    if await pg.evaluate("window.__saved"): break
                fn = await pg.evaluate("window.__saved")
                b64 = await pg.evaluate("new Promise(r=>{const fr=new FileReader();fr.onload=()=>r(fr.result.split(',')[1]);fr.readAsDataURL(window.__lastPdf)})")
                open(f"{OUT}/{fn}", "wb").write(base64.b64decode(b64)); print(fn)
        await b.close()
asyncio.run(main())
