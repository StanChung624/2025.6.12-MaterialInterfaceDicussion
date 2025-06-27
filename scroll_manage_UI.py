from flask import Flask, request, redirect, url_for, render_template_string
import os

EQPMNT = {
    '裝備': ['頭盔','耳飾','套服','上衣','下衣','鞋子','手套','披風','盾牌'],
    '武器': {
        '魔法': ['短杖','長杖'],
        '物理': ['弓','弩','手槍','指虎','槍','矛','拳套','短劍','單手劍','單手斧','單手棍','雙手劍','雙手斧','雙手棍']
    },
    '屬性': {
        '裝備': ['防禦','智力','幸運','敏捷','力量','跳躍','移動速度','生命'],
        '武器': {
            '魔法': ['魔力'],
            '物理': ['攻擊','命中']
        }
    },
    '機率': ['100%', '60%', '10%']
}

CSV_PATH = "Inventory.csv"

def load_inventory():
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines[1:] if lines and lines[0].startswith("name,") else lines
    return []

def save_inventory(inventory):
    with open(CSV_PATH, 'w', encoding='utf-8') as f:
        f.write("name,quantity\n")
        for item in inventory:
            f.write(item + "\n")

def sort_inventory(inv_list):
    def sort_key(item):
        try:
            name, rest = item.rsplit("卷軸", 1)
            rate, _ = rest.split(",", 1)
            rate_order = {"100%": 0, "60%": 1, "10%": 2}
            return (name, rate_order.get(rate, 99))
        except:
            return (item, 99)
    eq = [i for i in inv_list if any(i.startswith(e) for e in EQPMNT['裝備'])]
    wp = [i for i in inv_list if i not in eq]
    return sorted(eq, key=sort_key) + sorted(wp, key=sort_key)

app = Flask(__name__)

HTML_TEMPLATE = '''
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>卷軸管理 UI</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    label { display: inline-block; width: 80px; }
    select, input[type=text], input[type=number] { width: 150px; margin-bottom: 10px; }
    .error { color: red; }
    .inventory-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 5px 10px;
      align-items: center;
    }
    .inventory-item {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 5px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 10px;
    }
    .inventory-item img {
      width: 32px;
      height: 32px;
      flex-shrink: 0;
    }
    .highlight {
      font-weight: bold;
      color: green;
    }
    .main-layout {
      display: flex;
      gap: 30px;
      align-items: flex-start;
    }
    .form-panel {
      flex: 0 0 320px;
    }
    .inventory-panel {
      flex: 1;
    }
  </style>
  <script>
    function updateCategory() {
      var kind = document.getElementById("kind").value;
      var wtype = document.getElementById("wtype").value;
      var catSelect = document.getElementById("cat");
      var attrSelect = document.getElementById("attr");
      var wtypeSelect = document.getElementById("wtype");
      
      var eqpmnt = {{ eqpmnt | tojson }};
      
      if (kind === "裝備") {
        wtypeSelect.disabled = true;
        var cats = eqpmnt['裝備'];
        var attrs = eqpmnt['屬性']['裝備'];
      } else {
        wtypeSelect.disabled = false;
        var cats = eqpmnt['武器'][wtype];
        var attrs = eqpmnt['屬性']['武器'][wtype];
      }
      
      catSelect.innerHTML = "";
      for (var i=0; i<cats.length; i++) {
        var opt = document.createElement("option");
        opt.value = cats[i];
        opt.text = cats[i];
        catSelect.appendChild(opt);
      }
      
      attrSelect.innerHTML = "";
      for (var i=0; i<attrs.length; i++) {
        var opt = document.createElement("option");
        opt.value = attrs[i];
        opt.text = attrs[i];
        attrSelect.appendChild(opt);
      }
    }
    window.onload = function() {
      document.getElementById("kind").addEventListener("change", updateCategory);
      document.getElementById("wtype").addEventListener("change", updateCategory);
      updateCategory();
    };
    function logClick(entry) {
      console.log("Clicked entry:", entry);

      const eqpmnt = {{ eqpmnt | tojson }};
      const cleanEntry = entry.trim().replace(/,+$/, "");
      const [scrollPart, qty] = cleanEntry.split(",");
      const [namePart, rate] = scrollPart.split("卷軸");
      let kind = "裝備";
      let wtype = "";
      let cat = "";
      let attr = "";

      if (eqpmnt["裝備"].includes(namePart.slice(0, 2))) {
        kind = "裝備";
        wtype = "";
        for (let a of eqpmnt["屬性"]["裝備"]) {
          if (namePart.endsWith(a)) {
            attr = a;
            cat = namePart.slice(0, namePart.length - a.length);
            break;
          }
        }
      } else {
        kind = "武器";
        for (let type of ["魔法", "物理"]) {
          for (let base of eqpmnt["武器"][type]) {
            if (namePart.startsWith(base)) {
              cat = base;
              wtype = type;
              for (let a of eqpmnt["屬性"]["武器"][type]) {
                if (namePart.endsWith(a)) {
                  attr = a;
                  break;
                }
              }
            }
          }
        }
      }

      document.getElementById("kind").value = kind;
      document.getElementById("wtype").value = wtype;
      updateCategory();
      setTimeout(() => {
        document.getElementById("cat").value = cat;
        document.getElementById("attr").value = attr;
        document.getElementById("rate").value = rate;
        document.getElementById("count").value = qty;
      }, 50);
    }
  </script>
</head>
<body>
  <h1>卷軸管理 UI</h1>
  {% if error %}
    <p class="error">{{ error }}</p>
  {% endif %}
  <div class="main-layout">
    <div class="form-panel">
      <form action="{{ url_for('add') }}" method="post">
        <label for="kind">選擇類型</label>
        <select name="kind" id="kind">
          <option value="裝備" {% if form_data.kind == "裝備" %}selected{% endif %}>裝備</option>
          <option value="武器" {% if form_data.kind == "武器" %}selected{% endif %}>武器</option>
        </select><br>
        
        <label for="wtype">武器類型</label>
        <select name="wtype" id="wtype">
          <option value="魔法" {% if form_data.wtype == "魔法" %}selected{% endif %}>魔法</option>
          <option value="物理" {% if form_data.wtype == "物理" %}selected{% endif %}>物理</option>
        </select><br>
        
        <label for="cat">選擇項目</label>
        <select name="cat" id="cat"></select><br>
        
        <label for="attr">屬性</label>
        <select name="attr" id="attr"></select><br>
        
        <label for="rate">機率</label>
        <select name="rate" id="rate">
          {% for r in eqpmnt['機率'] %}
            <option value="{{ r }}" {% if form_data.rate == r %}selected{% endif %}>{{ r }}</option>
          {% endfor %}
        </select><br>
        
        <label for="count">數量</label>
        <input type="number" name="count" id="count" min="0" value="{{ form_data.count }}"><br>
        
        <button type="submit">新增 / 更新</button>
      </form>
    </div>
    <div class="inventory-panel">
      <h2>庫存預覽</h2>
      <div class="inventory-grid">
      {% set image_map = {"10%": "image/po_10.32.png", "60%": "image/po_60.32.png", "100%": "image/po_99.32.png"} %}
      {% for entry in inventory %}
        {% set clean_entry = entry.strip(', ') %}
        {% set scroll_part, qty = clean_entry.rsplit(",", 1) %}
        {% if qty != "0" %}
          {% set scroll_name, rate = scroll_part.rsplit("卷軸", 1) %}
          <div class="inventory-item" onclick="logClick('{{ entry }}')">
            <img src="{{ url_for('static', filename=image_map.get(rate, '')) }}" alt="{{ rate }}">
            <span {% if highlight == entry %}class="highlight"{% endif %}>
              {{ scroll_name }}{{ rate }} ×{{ qty }}
            </span>
          </div>
        {% endif %}
      {% endfor %}
      </div>
    </div>
  </div>
</body>
</html>
'''

@app.route("/", methods=["GET"])
def index():
    inventory = load_inventory()
    form_data = {
        "kind": "裝備",
        "wtype": "魔法",
        "rate": "100%",
        "count": "1"
    }
    return render_template_string(HTML_TEMPLATE, eqpmnt=EQPMNT, inventory=inventory, form_data=form_data, error=None, highlight=None)

@app.route("/add", methods=["POST"])
def add():
    kind = request.form.get("kind", "")
    wtype = request.form.get("wtype", "")
    cat = request.form.get("cat", "")
    attr = request.form.get("attr", "")
    rate = request.form.get("rate", "")
    count = request.form.get("count", "")
    error = None
    form_data = {
        "kind": kind,
        "wtype": wtype,
        "rate": rate,
        "count": count
    }
    if not cat or not attr or not count.isdigit() or int(count) < 0:
        error = "請填寫完整且正確的資訊"
        inventory = load_inventory()
        return render_template_string(HTML_TEMPLATE, eqpmnt=EQPMNT, inventory=inventory, form_data=form_data, error=error, highlight=None)
    item = f"{cat}{attr}卷軸{rate},{count}"
    prefix = item.rsplit(",", 1)[0]

    inventory = load_inventory()
    found = False
    for i, entry in enumerate(inventory):
        if entry.startswith(prefix + ","):
            inventory[i] = item
            found = True
            break
    if not found:
        inventory.append(item)

    inventory = sort_inventory(inventory)
    save_inventory(inventory)
    return render_template_string(HTML_TEMPLATE, eqpmnt=EQPMNT, inventory=inventory, form_data=form_data, error=None, highlight=item)

if __name__ == "__main__":
    app.run(debug=True)