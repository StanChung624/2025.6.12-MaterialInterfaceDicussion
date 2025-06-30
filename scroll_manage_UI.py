from flask import Flask, request, redirect, url_for, render_template_string
import os
import logging
from datetime import datetime

EQPMNT_ATTR = ['防禦','智力','敏捷','幸運','力量','跳躍','攻擊','移動速度','體力']

EQPMNT_ORDER = {
    '披風': ['力量','智力','敏捷','防禦','幸運','跳躍','攻擊','移動速度','體力'],
    '套服': ['智力','敏捷','防禦','幸運','力量','跳躍','攻擊','移動速度','體力'],
    'default': EQPMNT_ATTR
}

EQPMNT = {
    '裝備': ['頭盔','耳飾','上衣','套服','下衣','鞋子','手套','盾牌','披風'],
    '武器': {
        '魔法': ['短杖','長杖'],
        '物理': ['單手斧','單手棍','短劍','弓','弩','手槍','指虎','槍','矛','拳套','單手劍','雙手劍','雙手斧','雙手棍']
    },
    '屬性': {
        '裝備': EQPMNT_ATTR,
        '武器': {
            '魔法': ['魔力'],
            '物理': ['攻擊','命中']
        }
    },
    '機率': ['100%', '60%', '10%']
}

WEAPON_ORDER = ['單手劍','單手斧','單手棍','短劍',
                '短杖','長杖','雙手劍','雙手斧','雙手棍',
                '槍','矛','弓','弩','拳套','指虎','手槍']

CSV_PATH = "Inventory.csv"

def validate_form(form):
    required = ['cat', 'attr', 'count']
    for field in required:
        if not form.get(field):
            return False
    try:
        return int(form.get('count', -1)) >= 0
    except:
        return False

def build_item_string(cat, attr, rate, count):
    return f"{cat}{attr}卷軸{rate},{count},"

def find_item_index(inventory, prefix):
    for i, entry in enumerate(inventory):
        if entry.startswith(prefix + ","):
            return i
    return -1

def load_inventory():
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines[1:] if lines and lines[0].startswith("name,") else lines
    return []

def save_inventory(inventory):
    with open(CSV_PATH, 'w', encoding='utf-8') as f:
        f.write("name,quantity,\n")
        for item in inventory:
            f.write(item + "\n")

def sort_inventory(inv_list):
    equipment_order = ['頭盔','耳飾','上衣','套服','下衣','鞋子','手套','盾牌','披風']
    attribute_order = None
    weapon_order = WEAPON_ORDER
    weapon_attr_order = EQPMNT['屬性']['武器']['物理'] + EQPMNT['屬性']['武器']['魔法']
    def sort_key(item):
        try:
            name, rest = item.rsplit("卷軸", 1)
            rate, _ = rest.split(",", 1)
            rate_order = {"100%": 0, "60%": 1, "10%": 2}
            is_equipment = any(name.startswith(e) for e in equipment_order)
            if is_equipment:
                order_index = next((i for i, prefix in enumerate(equipment_order) if name.startswith(prefix)), len(equipment_order))
                attribute_order = EQPMNT_ORDER.get(name[:2], EQPMNT_ORDER['default'])
                attr_index = next((i for i, attr in enumerate(attribute_order) if name.endswith(attr)), len(attribute_order))
                return (0, order_index, attr_index, name, rate_order.get(rate, 99))
            else:
                weapon_index = next((i for i, prefix in enumerate(weapon_order) if name.startswith(prefix)), len(weapon_order))
                attr_index = next((i for i, attr in enumerate(weapon_attr_order) if name.endswith(attr)), len(weapon_attr_order))
                return (1, weapon_index, attr_index, name, rate_order.get(rate, 99))
        except:
            return (2, item, 99)
    return sorted(inv_list, key=sort_key)


app = Flask(__name__)

# Suppress default Flask (werkzeug) HTTP request logs
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Logger setting
logging.basicConfig(
    filename='operation_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

HTML_TEMPLATE = '''
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>卷軸管理 UI</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    label { display: inline-block; width: 80px; }
    select, input[type=text], input[type=number] {
      width: 150px;
      min-width: 150px;
      max-width: 150px;
      box-sizing: border-box;
      margin-bottom: 10px;
    }
    .error { color: red; }
    .inventory-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 5px 10px;
      align-items: center;
      width: 48px;
      max-width: 480px;
      min-width: 480px;
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
    .image-container {
      position: relative;
      display: inline-block;
    }
    .inventory-item img {
      width: 32px;
      height: 32px;
      flex-shrink: 0;
    }
    .quantity-badge {
      position: absolute;
      bottom: 0;
      right: 0;
      background: rgba(0, 0, 0, 0.7);
      color: white;
      font-size: 10px;
      padding: 1px 3px;
      border-radius: 3px;
      font-family: monospace;
    }
    .highlight {
      font-weight: bold;
      color: green;
    }
    .form-panel {
      flex: 0 0 320px;
      min-width: 320px;
      max-width: 320px;
    }
    .inventory-panel {
      flex: 0 0 auto;
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
    let currentEditEntry = "";

    function logClick(entry) {
      const cleanEntry = entry.trim().replace(/,+$/, "");
      currentEditEntry = cleanEntry;
      const lastComma = cleanEntry.lastIndexOf(",");
      const scrollPart = cleanEntry.substring(0, lastComma);
      const qty = cleanEntry.substring(lastComma + 1);
      document.getElementById("modalItemName").textContent = scrollPart;
      document.getElementById("modalItemQty").value = qty;
      document.getElementById("editModal").style.display = "block";
    }

    function closeModal() {
      document.getElementById("editModal").style.display = "none";
    }

    function confirmEdit() {
      const qty = document.getElementById("modalItemQty").value;

      // Avoid splitting rate and qty together
      const baseEntry = currentEditEntry.trim().replace(/,+$/, "");
      const lastComma = baseEntry.lastIndexOf(",");
      const scrollPart = baseEntry.substring(0, lastComma);
      const [scrollName, rate] = scrollPart.split("卷軸");

      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/add";

      const hiddenFields = {
        kind: '', wtype: '', cat: '', attr: '', rate: rate, count: qty,
        pad: document.getElementById("pad")?.value || "0"
      };

      const eqpmnt = {{ eqpmnt | tojson }};
      const name = scrollName;

      if (eqpmnt["裝備"].some(e => name.startsWith(e))) {
        hiddenFields.kind = "裝備";
        for (const attr of eqpmnt["屬性"]["裝備"]) {
          if (name.endsWith(attr)) {
            hiddenFields.attr = attr;
            hiddenFields.cat = name.slice(0, name.length - attr.length);
            break;
          }
        }
      } else {
        hiddenFields.kind = "武器";
        for (const type of ["物理", "魔法"]) {
          for (const base of eqpmnt["武器"][type]) {
            if (name.startsWith(base)) {
              hiddenFields.cat = base;
              hiddenFields.wtype = type;
              for (const attr of eqpmnt["屬性"]["武器"][type]) {
                if (name.endsWith(attr)) {
                  hiddenFields.attr = attr;
                  break;
                }
              }
            }
          }
        }
      }

      for (let k in hiddenFields) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = k;
        input.value = hiddenFields[k];
        form.appendChild(input);
      }

      document.body.appendChild(form);
      form.submit();
    }
    function updatePad(val) {
      padValue.value = val;
      const grid = document.querySelector('.inventory-grid');
      const items = Array.from(grid.querySelectorAll('.inventory-item'));
      // Clear grid
      grid.innerHTML = '';
      // Prepend empty blocks
      for (let i = 0; i < parseInt(val); i++) {
        const spacer = document.createElement('div');
        grid.appendChild(spacer);
      }
      // Append all items
      for (const item of items) {
        grid.appendChild(item);
      }
    }
  </script>
</head>
<body>
  <h1>卷軸管理 UI</h1>
  {% if error %}
    <p class="error">{{ error }}</p>
  {% endif %}
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

      <label for="pad">前面空格</label>
      <input type="range" id="pad" name="pad" min="0" max="3" value="{{ form_data.pad }}" oninput="updatePad(this.value)">
      <output id="padValue">{{ form_data.pad }}</output><br>
      
      <button type="submit">新增 / 更新</button>
    </form>
  </div>
    <div class="inventory-panel">
    <h2>庫存預覽</h2>
    <div class="inventory-grid">
    {% for _ in range(form_data.pad | int) %}
      <div></div>
    {% endfor %}
    {% set image_map = {"10%": "image/po_10.32.png", "60%": "image/po_60.32.png", "100%": "image/po_99.32.png"} %}
    {% for entry in inventory %}
      {% set clean_entry = entry.strip(', ') %}
      {% set scroll_part, qty = clean_entry.rsplit(",", 1) %}
      {% if qty != "0" %}
        {% set scroll_name, rate = scroll_part.rsplit("卷軸", 1) %}
        <div class="inventory-item" onclick="logClick('{{ entry }}')">
          <div class="image-container">
            <img src="{{ url_for('static', filename=image_map.get(rate, '')) }}" alt="{{ rate }}">
            <div class="quantity-badge">×{{ qty }}</div>
          </div>
          <span {% if highlight == entry %}class="highlight"{% endif %}>
            {{ scroll_name }}{{ rate }}
          </span>
        </div>
      {% endif %}
    {% endfor %}
    </div>
  </div>
</body>
  <div id="editModal" style="display:none; position:fixed; top:30%; left:50%; transform:translate(-50%, -30%);
    background:white; border:1px solid #ccc; padding:20px; z-index:999;">
    <h3>編輯卷軸數量</h3>
    <p id="modalItemName" style="font-weight:bold;"></p>
    <input type="number" id="modalItemQty" min="0" />
    <br><br>
    <button onclick="confirmEdit()">儲存</button>
    <button onclick="closeModal()">取消</button>
  </div>
</html>
'''

@app.route("/", methods=["GET"])
def index():
    inventory = sort_inventory(load_inventory())
    form_data = {
        "kind": "裝備",
        "wtype": "魔法",
        "rate": "100%",
        "count": "1",
        "pad": "0"
    }
    return render_template_string(HTML_TEMPLATE, eqpmnt=EQPMNT, inventory=inventory, form_data=form_data, error=None, highlight=None)

@app.route("/add", methods=["POST"])
def add():
    form = request.form
    kind, wtype = form.get("kind", ""), form.get("wtype", "")
    cat, attr = form.get("cat", ""), form.get("attr", "")
    rate, count = form.get("rate", ""), form.get("count", "")
    pad = int(form.get("pad", "0"))
    prefix = f"{cat}{attr}卷軸{rate}"
    item = build_item_string(cat, attr, rate, count)
    form_data = {
        "kind": kind, "wtype": wtype, "rate": rate,
        "count": count, "pad": str(pad)
    }

    if not validate_form(form):
        logging.warning(f"Form input error: cat={cat}, attr={attr}, count={count}")
        return render_template_string(HTML_TEMPLATE, eqpmnt=EQPMNT,
            inventory=sort_inventory(load_inventory()),
            form_data=form_data,
            error="請填寫完整且正確的資訊",
            highlight=None)

    inventory = sort_inventory(load_inventory())
    idx = find_item_index(inventory, prefix)

    if idx >= 0:
        prev_qty = inventory[idx].split(",")[1]
        inventory[idx] = item
        logging.info(f"Modified: {prefix}, count {prev_qty} > {count}")
    else:
        inventory.append(item)
        logging.info(f"Added: {prefix}, count 0 > {count}")

    save_inventory(sort_inventory(inventory))
    return render_template_string(HTML_TEMPLATE, eqpmnt=EQPMNT,
        inventory=sort_inventory(inventory),
        form_data=form_data,
        error=None,
        highlight=item)

if __name__ == "__main__":
  app.run(debug=True, host="127.0.0.1", port=5000)