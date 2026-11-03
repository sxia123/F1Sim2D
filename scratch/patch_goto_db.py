with open('public/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

target = """    // Driver Database search input
    const drvSearch = document.getElementById("driver-search-input");
    if (drvSearch) {
      drvSearch.addEventListener("input", (e) => {
        this.driverSearchQuery = e.target.value.trim().toLowerCase();
        this.renderDriverDatabase();
      });
    }"""

repl = """    // Driver Database search input
    const drvSearch = document.getElementById("driver-search-input");
    if (drvSearch) {
      drvSearch.addEventListener("input", (e) => {
        this.driverSearchQuery = e.target.value.trim().toLowerCase();
        this.renderDriverDatabase();
      });
    }

    const gotoDbBtn = document.getElementById("btn-goto-database");
    if (gotoDbBtn) {
      gotoDbBtn.addEventListener("click", () => {
        const tabBtn = document.querySelector('.nav-tab[data-tab="database"]');
        if (tabBtn) tabBtn.click();
      });
    }"""

assert target in js, "target not found in app.js"
js = js.replace(target, repl, 1)

with open('public/app.js', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(js)

print("Updated public/app.js with gotoDbBtn")

