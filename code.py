import displayio
import terminalio
import time
import wifi
import socketpool
import usb_hid
import digitalio
import busio
import microcontroller

try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

from adafruit_display_text import label
from adafruit_st7735r import ST7735R
from adafruit_httpserver import Server, Request, Response, POST, GET
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse


def unquote(text):
    text = text.replace("+", " ")
    parts = text.split("%")
    out = parts[0]
    for p in parts[1:]:
        try: out += chr(int(p[:2], 16)) + p[2:]
        except: out += "%" + p
    return out

#on the lcd
displayio.release_displays()

backlight = digitalio.DigitalInOut(microcontroller.pin.GPIO38)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = False 

spi = busio.SPI(clock=microcontroller.pin.GPIO5, MOSI=microcontroller.pin.GPIO3)
display_bus = FourWire(spi, command=microcontroller.pin.GPIO2, chip_select=microcontroller.pin.GPIO4, reset=microcontroller.pin.GPIO1)

display = ST7735R(display_bus, width=160, height=80, rotation=90, bgr=True, colstart=26, rowstart=1, invert=True)


main_group = displayio.Group()

bg_bitmap = displayio.Bitmap(160, 80, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = 0x000000  # black
bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=0, y=0)
main_group.append(bg_sprite)


MATRIX_GREEN = 0x00FF00
DARK_GREEN = 0x008800
CYAN_ACCENT = 0x00FFFF
WARNING_RED = 0xFF3333


lbl_title = label.Label(terminalio.FONT, text="Welcome to Keybord Remote", color=CYAN_ACCENT, x=2, y=6)

lbl_divider = label.Label(terminalio.FONT, text="-"*26, color=DARK_GREEN, x=2, y=16)


lbl_line1 = label.Label(terminalio.FONT, text="[i] BOOTING...", color=MATRIX_GREEN, x=2, y=30)
lbl_line2 = label.Label(terminalio.FONT, text="[i] STANDBY", color=MATRIX_GREEN, x=2, y=45)


lbl_prompt = label.Label(terminalio.FONT, text="idan@less:~#", color=DARK_GREEN, x=2, y=68)
lbl_cursor = label.Label(terminalio.FONT, text="_", color=MATRIX_GREEN, x=70, y=68)

main_group.append(lbl_title)
main_group.append(lbl_divider)
main_group.append(lbl_line1)
main_group.append(lbl_line2)
main_group.append(lbl_prompt)
main_group.append(lbl_cursor)

display.root_group = main_group

def update_matrix_ui(line1, line2, status="OK", show_cursor=True):
    try:
        
        lbl_line1.text = f"[*] {line1}"
        lbl_line2.text = f"[>] {line2}"
        
       
        if status == "WIFI":
            lbl_title.color = CYAN_ACCENT      
        elif status == "AP":
            lbl_title.color = WARNING_RED    
        else:
            lbl_title.color = MATRIX_GREEN
            
       
        lbl_cursor.text = "_" if show_cursor else " "
    except:
        pass


WIFI_SSID = "Idan-Remote-KBD"
WIFI_PASS = "12345678"

hebrew_map = {
    'ש': Keycode.A, 'ד': Keycode.S, 'ג': Keycode.D, 'כ': Keycode.F, 'ע': Keycode.G,
    'י': Keycode.H, 'ח': Keycode.J, 'ל': Keycode.K, 'ך': Keycode.L, 'ף': Keycode.SEMICOLON,
    'ז': Keycode.Z, 'ס': Keycode.X, 'ב': Keycode.C, 'ה': Keycode.V, 'נ': Keycode.B,
    'מ': Keycode.N, 'צ': Keycode.M, 'ת': Keycode.COMMA, 'ץ': Keycode.PERIOD, 
    'ק': Keycode.Q, 'ר': Keycode.W, 'א': Keycode.E, 'ט': Keycode.R, 'ו': Keycode.T,
    'ן': Keycode.Y, 'ם': Keycode.U, 'פ': Keycode.I, 'ס': Keycode.P,
    ' ': Keycode.SPACE, '\n': Keycode.ENTER,
    '!': (Keycode.SHIFT, Keycode.ONE), '@': (Keycode.SHIFT, Keycode.TWO),
    '#': (Keycode.SHIFT, Keycode.THREE), '$': (Keycode.SHIFT, Keycode.FOUR),
    '%': (Keycode.SHIFT, Keycode.FIVE), '^': (Keycode.SHIFT, Keycode.SIX),
    '&': (Keycode.SHIFT, Keycode.SEVEN), '*': (Keycode.SHIFT, Keycode.EIGHT),
    '(': (Keycode.SHIFT, Keycode.NINE), ')': (Keycode.SHIFT, Keycode.ZERO),
    '?': (Keycode.SHIFT, Keycode.FORWARD_SLASH), '_': (Keycode.SHIFT, Keycode.MINUS),
    '+': (Keycode.SHIFT, Keycode.EQUALS), '"': (Keycode.SHIFT, Keycode.QUOTE),
    '{': (Keycode.SHIFT, Keycode.LEFT_BRACKET), '}': (Keycode.SHIFT, Keycode.RIGHT_BRACKET),
    '|': (Keycode.SHIFT, Keycode.BACKSLASH), ':': (Keycode.SHIFT, Keycode.SEMICOLON),
    '<': (Keycode.SHIFT, Keycode.COMMA), '>': (Keycode.SHIFT, Keycode.PERIOD),
    '~': (Keycode.SHIFT, Keycode.GRAVE_ACCENT),
    '-': Keycode.MINUS, '=': Keycode.EQUALS, "'": Keycode.QUOTE,
    ',': Keycode.QUOTE, '.': Keycode.PERIOD, '/': Keycode.FORWARD_SLASH,
    '\\': Keycode.BACKSLASH, '[': Keycode.LEFT_BRACKET, ']': Keycode.RIGHT_BRACKET,
    ';': Keycode.SEMICOLON, '`': Keycode.GRAVE_ACCENT
}

mod_map = {"CTRL": Keycode.CONTROL, "ALT": Keycode.ALT, "SHIFT": Keycode.SHIFT, "WIN": Keycode.GUI}
num_map = {'0': Keycode.ZERO, '1': Keycode.ONE, '2': Keycode.TWO, '3': Keycode.THREE, '4': Keycode.FOUR, '5': Keycode.FIVE, '6': Keycode.SIX, '7': Keycode.SEVEN, '8': Keycode.EIGHT, '9': Keycode.NINE}

kbd = Keyboard(usb_hid.devices)
mouse_dev = Mouse(usb_hid.devices)

wifi.radio.start_ap(WIFI_SSID, WIFI_PASS)
pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, debug=True)

# Ai Part
html = """
<!DOCTYPE html>
<html dir="ltr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
<style>
    body { font-family: sans-serif; text-align: center; background: #000; color: #0f0; padding: 10px; margin: 0; touch-action: manipulation; }
    textarea { width: 95%; height: 60px; background: #111; color: #fff; border: 1px solid #0f0; padding: 10px; font-size: 18px; border-radius: 8px; box-sizing: border-box; }
    .flex-row { display: flex; justify-content: space-between; width: 95%; margin: 10px auto; gap: 10px;}
    .btn { flex: 1; padding: 12px; background: #0f0; color: #000; font-weight: bold; font-size: 16px; border: none; border-radius: 8px; cursor: pointer; }
    .btn-gray { background: #444; color: #fff; }
    .btn-red { background: #a00; color: #fff; border: 1px solid #f00; }
    
    details { background: #1a1a1a; margin-bottom: 10px; border-radius: 8px; border: 1px solid #0f0; overflow: hidden; text-align: left; }
    summary { padding: 15px; font-weight: bold; font-size: 18px; cursor: pointer; outline: none; background: #0a0a0a; list-style: none; }
    summary::after { content: ' ▼'; float: right; color: #0f0; }
    details[open] summary::after { content: ' ▲'; }
    .content { padding: 15px; text-align: center; }

    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
    .grid-6 { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin-bottom: 10px; }
    
    .vk-btn { padding: 12px 0; background: #333; color: #0f0; border: 1px solid #0f0; border-radius: 6px; font-size: 14px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.5); cursor: pointer; transition: 0.2s;}
    .vk-btn:active { background: #0f0; color: #000; }
    
    .trackpad { width: 100%; height: 220px; background: #111; border: 2px dashed #0f0; border-radius: 12px; touch-action: none; position: relative; margin-bottom: 10px;}
    .trackpad::after { content: 'Trackpad'; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #444; font-size: 18px; pointer-events: none; }
    
    .custom-input { background: #000; color: #0f0; border: 1px solid #0f0; text-align: center; font-size: 18px; font-weight: bold; border-radius: 8px; }
</style>
</head>
<body>
    <h2 style="margin-top: 5px;">Remote Control</h2>
    
    <details>
        <summary>External Wi-Fi Connection</summary>
        <div class="content">
            <p style="font-size: 14px; margin-top:0;">Select a network for internet access</p>
            
            <div style="display: flex; gap: 5px; justify-content: center; margin-bottom: 10px; width: 95%; margin-left: auto; margin-right: auto;">
                <select id="ext-ssid" class="custom-input" style="width: 70%; font-size: 16px; padding: 5px;">
                    <option value="">Select network...</option>
                </select>
                <button onclick="scanWifi()" class="btn btn-gray" style="width: 30%; padding: 10px; font-size: 14px;">Scan</button>
            </div>
            
            <input type="password" id="ext-pass" placeholder="Password (leave blank if open)" class="custom-input" style="width:90%; padding: 8px; margin-bottom:10px; font-size: 14px;"><br>
            <button onclick="connectWifi()" class="btn">Connect to Router</button>
            <div id="wifi-status" style="margin-top:10px; font-size:16px; font-weight:bold;"></div>
        </div>
    </details>

    <details open>
        <summary>Text & Custom Commands</summary>
        <div class="content">
            <textarea id="txtbox" placeholder="Type or paste regular text..."></textarea>
            <div class="flex-row">
                <button onclick="sendText()" class="btn">Send Text</button>
                <button onclick="clearText()" class="btn btn-gray">Clear</button>
            </div>
            <div class="flex-row" style="margin-top: 0;">
                <button onclick="vKey('ENTER')" class="btn btn-gray" style="background: #333;">Enter</button>
                <button onclick="vKey('SPACE')" class="btn btn-gray" style="background: #333;">Space</button>
            </div>
            
            <hr style="border-color: #0f0; margin: 15px 0;">
            <p style="font-size: 12px; color: #aaa; margin: 0 0 10px 0;">Build shortcut (e.g. Ctrl+Shift+T): Click to lock and add letter</p>
            
            <div class="grid-4" id="mod-keys">
                <button class="vk-btn" id="btn-CTRL" onclick="toggleMod('CTRL')">Ctrl</button>
                <button class="vk-btn" id="btn-ALT" onclick="toggleMod('ALT')">Alt</button>
                <button class="vk-btn" id="btn-SHIFT" onclick="toggleMod('SHIFT')">Shift</button>
                <button class="vk-btn" id="btn-WIN" onclick="toggleMod('WIN')">Win</button>
            </div>
            <div class="flex-row" style="margin-top: 15px; justify-content: center; gap: 15px;">
                <input type="text" id="custom-char" class="custom-input" maxlength="1" placeholder="Letter" style="width: 35%; text-transform: uppercase;">
                <button onclick="sendCustom()" class="btn btn-red" style="flex: none; width: 50%;">Send Shortcut!</button>
            </div>
        </div>
    </details>

    <details>
        <summary>Quick Shortcuts</summary>
        <div class="content">
            <div id="combo-keys" class="grid-4"></div>
        </div>
    </details>

    <details open>
        <summary>Smart Mouse</summary>
        <div class="content">
            <div class="trackpad" id="pad"></div>
            <div class="flex-row" style="margin: 0;">
                <button onclick="sendClick('left')" class="btn btn-gray">Left Click</button>
                <button onclick="sendClick('right')" class="btn btn-gray">Right Click</button>
            </div>
        </div>
    </details>

    <details>
        <summary>Full Keyboard</summary>
        <div class="content">
            <div id="f-keys" class="grid-6"></div>
            <div id="ctrl-keys" class="grid-4"></div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top:15px; width: 70%; margin-left: auto; margin-right: auto;">
                <div></div><button class="vk-btn" onclick="vKey('UP')">UP</button><div></div>
                <button class="vk-btn" onclick="vKey('LEFT')">LEFT</button>
                <button class="vk-btn" onclick="vKey('DOWN')">DOWN</button>
                <button class="vk-btn" onclick="vKey('RIGHT')">RIGHT</button>
            </div>
        </div>
    </details>

<script>
    // --- WIFI SCAN ---
    function scanWifi() {
        let ssidSelect = document.getElementById('ext-ssid');
        ssidSelect.innerHTML = '<option value="">Scanning... Please wait</option>';
        fetch('/scan')
        .then(res => res.text())
        .then(txt => {
            let networks = txt.split(',');
            ssidSelect.innerHTML = '<option value="">Select network...</option>';
            networks.forEach(n => {
                if(n) ssidSelect.innerHTML += `<option value="${n}">${n}</option>`;
            });
        })
        .catch(() => ssidSelect.innerHTML = '<option value="">Scan error</option>');
    }

    function connectWifi() {
        let s = document.getElementById('ext-ssid').value;
        let p = document.getElementById('ext-pass').value;
        let status = document.getElementById('wifi-status');
        if(!s) { status.innerText = "Select a network from the list!"; return; }
        status.innerText = "Connecting... Wait about 10 seconds";
        fetch('/wifi?s=' + encodeURIComponent(s) + '&p=' + encodeURIComponent(p))
        .then(res => res.text())
        .then(txt => status.innerText = txt)
        .catch(() => status.innerText = "Communication error");
    }

    function sendText() { fetch('/send', { method: 'POST', body: 'text=' + encodeURIComponent(document.getElementById('txtbox').value), headers: {'Content-Type': 'application/x-www-form-urlencoded'} }); }
    function clearText() { document.getElementById('txtbox').value = ''; }
    function sendClick(btn) { fetch('/mouse?click=' + btn); }
    function vKey(k) { fetch('/key?k=' + k); }
    function vCombo(a) { fetch('/combo?a=' + a); }

    let activeMods = new Set();
    function toggleMod(mod) {
        let btn = document.getElementById('btn-' + mod);
        if(activeMods.has(mod)) {
            activeMods.delete(mod); btn.style.background = '#333'; btn.style.color = '#0f0';
        } else {
            activeMods.add(mod); btn.style.background = '#0f0'; btn.style.color = '#000';
        }
    }

    function sendCustom() {
        let charInput = document.getElementById('custom-char').value.toUpperCase();
        let modsArray = Array.from(activeMods).join(',');
        fetch('/custom?mods=' + modsArray + '&key=' + encodeURIComponent(charInput));
        document.getElementById('custom-char').value = '';
        activeMods.clear();
        ['CTRL','ALT','SHIFT','WIN'].forEach(m => { document.getElementById('btn-'+m).style.background = '#333'; document.getElementById('btn-'+m).style.color = '#0f0'; });
    }

    const fKeys = [['F1','F1'],['F2','F2'],['F3','F3'],['F4','F4'],['F5','F5'],['F6','F6'],['F7','F7'],['F8','F8'],['F9','F9'],['F10','F10'],['F11','F11'],['F12','F12']];
    const ctrlKeys = [['ESC','ESC'],['TAB','TAB'],['PRTSCR','PrtScn'],['HOME','Home'],['END','End'],['PGUP','PgUp'],['PGDN','PgDn'],['INS','Insert'],['DEL','Del'],['BACK','Back'],['ENTER','Enter']];
    const comboKeys = [['COPY','Copy'],['PASTE','Paste'],['CUT','Cut'],['UNDO','Undo'],['ALTTAB','Alt+Tab'],['DESKTOP','Desktop'],['ALTF4','Close'],['LANG','Language']];
    function renderGrid(id, items, func) { document.getElementById(id).innerHTML = items.map(k => `<button class="vk-btn" onclick="${func}('${k[0]}')">${k[1]}</button>`).join(''); }
    renderGrid('f-keys', fKeys, 'vKey'); renderGrid('ctrl-keys', ctrlKeys, 'vKey'); renderGrid('combo-keys', comboKeys, 'vCombo');

    let pad = document.getElementById('pad');
    let lastX = 0, lastY = 0, dx = 0, dy = 0, sending = false;
    pad.addEventListener('touchstart', e => { lastX = e.touches[0].clientX; lastY = e.touches[0].clientY; });
    pad.addEventListener('touchmove', e => {
        e.preventDefault();
        let curX = e.touches[0].clientX, curY = e.touches[0].clientY;
        dx += (curX - lastX) * 1.5; dy += (curY - lastY) * 1.5;
        lastX = curX; lastY = curY;
        sendMovement();
    });
    function sendMovement() {
        if(sending || (dx === 0 && dy === 0)) return;
        sending = true;
        let sendX = Math.round(dx), sendY = Math.round(dy); dx = 0; dy = 0;
        fetch('/mouse?x=' + sendX + '&y=' + sendY).then(() => { sending = false; sendMovement(); }).catch(() => { sending = false; });
    }
</script>
</body>
</html>
"""

@server.route("/")
def base(request: Request):
    return Response(request, html, content_type="text/html")

@server.route("/scan", GET)
def handle_scan(request: Request):
    nets = []
    try:
        for n in wifi.radio.start_scanning_networks():
            if n.ssid and n.ssid not in nets:
                nets.append(n.ssid)
        wifi.radio.stop_scanning_networks()
    except:
        pass
    return Response(request, ",".join(nets), content_type="text/plain")

@server.route("/wifi", GET)
def handle_wifi(request: Request):
    s = request.query_params.get("s", "")
    p = request.query_params.get("p", "")
    if s:
        try:
           
            if p:
                wifi.radio.connect(s, p)
            else:
                wifi.radio.connect(s)
            return Response(request, f"Your New IP for WEb is \n{wifi.radio.ipv4_address}")
        except Exception as e:
            return Response(request, f"fail to connected ")
    return Response(request, "mssing objcet")

@server.route("/send", POST)
def send_text(request: Request):
    text = unquote(request.form_data.get("text", ""))
    for char in text:
        if char in hebrew_map:
            val = hebrew_map[char]
            if type(val) is tuple: kbd.send(*val)
            else: kbd.send(val)
        elif 'A' <= char <= 'Z': kbd.send(Keycode.SHIFT, getattr(Keycode, char.upper()))
        elif 'a' <= char <= 'z': kbd.send(getattr(Keycode, char.upper()))
        else: kbd.send(Keycode.SPACE)
    return Response(request, "OK", content_type="text/plain")

@server.route("/key", GET)
def handle_vkey(request: Request):
    k = request.query_params.get("k", "")
    vkey_map = {
        "ESC": Keycode.ESCAPE, "ENTER": Keycode.ENTER, "TAB": Keycode.TAB, "BACK": Keycode.BACKSPACE, "DEL": Keycode.DELETE, "PRTSCR": Keycode.PRINT_SCREEN,
        "HOME": Keycode.HOME, "END": Keycode.END, "PGUP": Keycode.PAGE_UP, "PGDN": Keycode.PAGE_DOWN, "INS": Keycode.INSERT,
        "UP": Keycode.UP_ARROW, "DOWN": Keycode.DOWN_ARROW, "LEFT": Keycode.LEFT_ARROW, "RIGHT": Keycode.RIGHT_ARROW,
        "F1": Keycode.F1, "F2": Keycode.F2, "F3": Keycode.F3, "F4": Keycode.F4, "F5": Keycode.F5, "F6": Keycode.F6, 
        "F7": Keycode.F7, "F8": Keycode.F8, "F9": Keycode.F9, "F10": Keycode.F10, "F11": Keycode.F11, "F12": Keycode.F12,
        "SPACE": Keycode.SPACE # הוספתי תמיכה בפקודת רווח כאן
    }
    if k in vkey_map: kbd.send(vkey_map[k])
    return Response(request, "OK", content_type="text/plain")

@server.route("/combo", GET)
def handle_combo(request: Request):
    a = request.query_params.get("a", "")
    try:
        if a == "COPY": kbd.send(Keycode.CONTROL, Keycode.C)
        elif a == "PASTE": kbd.send(Keycode.CONTROL, Keycode.V)
        elif a == "CUT": kbd.send(Keycode.CONTROL, Keycode.X)
        elif a == "UNDO": kbd.send(Keycode.CONTROL, Keycode.Z)
        elif a == "ALTTAB": kbd.send(Keycode.ALT, Keycode.TAB)
        elif a == "DESKTOP": kbd.send(Keycode.GUI, Keycode.D)
        elif a == "ALTF4": kbd.send(Keycode.ALT, Keycode.F4)
        elif a == "LANG": kbd.send(Keycode.ALT, Keycode.SHIFT)
    except: pass
    return Response(request, "OK", content_type="text/plain")

@server.route("/custom", GET)
def handle_custom(request: Request):
    mods_str = request.query_params.get("mods", "")
    key_char = request.query_params.get("key", "").upper()
    modifiers = [mod_map[m] for m in mods_str.split(',') if m in mod_map]
    
    key_code = None
    if key_char:
        if 'A' <= key_char <= 'Z': key_code = getattr(Keycode, key_char)
        elif key_char in num_map: key_code = num_map[key_char]
            
    try:
        if modifiers and key_code: kbd.send(*modifiers, key_code)
        elif modifiers: kbd.send(*modifiers)
        elif key_code: kbd.send(key_code)
    except: pass
    return Response(request, "OK", content_type="text/plain")

try:
    server.start("0.0.0.0", port=80)
except Exception as e:
    pass

blink_state = True
loop_counter = 0

while True:
    server.poll()
    backlight.value = False 
    
    loop_counter += 1
    if loop_counter % 10 == 0:
        blink_state = not blink_state
        
        if wifi.radio.ipv4_address:
            update_matrix_ui("NET: Wifi CONNECTED", f"IP: {wifi.radio.ipv4_address}", blink_state)
        else:
            try: num_clients = len(wifi.radio.ap_info) if wifi.radio.ap_info is not None else 0
            except: num_clients = 0
            
            if num_clients > 0:
                update_matrix_ui("AP: CONNECTED", "IP: 192.168.4.1", blink_state)
            else:
                update_matrix_ui("SYSTEM: READY AP Mode", f"PW: {WIFI_PASS}", blink_state)
                
    time.sleep(0.05)
