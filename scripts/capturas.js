// Toma las capturas de los puntos 4 a 9 desde Odoo y las guarda en docs/capturas/
// Uso: node scripts/capturas.js            (todas)
//      node scripts/capturas.js 25 49      (solo las que empiezan con esos numeros)
// Variables: ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD, CHROME_PATH
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright-core");

const BASE = process.env.ODOO_URL || "http://localhost:8069";
const DB = process.env.ODOO_DB || "dulces_delicias";
const LOGIN = process.env.ODOO_USER || "admin@dulcesdelicias.com";
const PASSWORD = process.env.ODOO_PASSWORD;
const OUT = path.join(__dirname, "..", "docs", "capturas");

// --- JSON-RPC con la misma sesion que usa el navegador ------------------------

let cookie = "";

async function jsonrpc(route, params) {
  const res = await fetch(BASE + route, {
    method: "POST",
    headers: { "Content-Type": "application/json", Cookie: cookie },
    body: JSON.stringify({ jsonrpc: "2.0", method: "call", params }),
  });
  const setCookie = res.headers.get("set-cookie");
  if (setCookie) cookie = setCookie.split(";")[0];
  const body = await res.json();
  if (body.error) throw new Error(`${route}: ${body.error.data?.message || body.error.message}`);
  return body.result;
}

const call = (model, method, args = [], kwargs = {}) =>
  jsonrpc("/web/dataset/call_kw", { model, method, args, kwargs });

async function idOf(model, domain) {
  const ids = await call(model, "search", [domain], { limit: 1 });
  if (!ids.length) throw new Error(`No hay ${model} con ${JSON.stringify(domain)}`);
  return ids[0];
}

async function ref(xmlid) {
  const [module, name] = xmlid.split(".");
  const rows = await call("ir.model.data", "search_read", [[["module", "=", module], ["name", "=", name]]], { fields: ["res_id"] });
  if (!rows.length) throw new Error(`No existe ${xmlid}`);
  return rows[0].res_id;
}

let menus;
async function menuAction(completeName) {
  menus ??= await call("ir.ui.menu", "search_read", [[["action", "!=", false]]], { fields: ["complete_name", "action"] });
  const menu = menus.find((m) => m.complete_name === completeName);
  if (!menu) throw new Error(`No existe el menu ${completeName}`);
  return Number(menu.action.split(",")[1]);
}

const accion = (id, viewType, extra = "") => `#action=${id}&view_type=${viewType}${extra}`;
const registro = (model, id) => `#id=${id}&model=${model}&view_type=form`;

// --- Capturas ------------------------------------------------------------------

async function plAccion() {
  const hoy = new Date();
  const desde = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  const hasta = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0);
  const iso = (d) => d.toISOString().slice(0, 10);
  const wiz = await call("accounting.report", "create", [{
    account_report_id: await ref("accounting_pdf_reports.account_financial_report_profitandloss0"),
    date_from: iso(desde), date_to: iso(hasta), target_move: "posted",
  }]);
  const act = await call("accounting.report", "check_report", [[wiz]]);
  // El reporte exige active_model y active_id en el contexto, como al imprimir desde el asistente
  const ctx = { active_model: "accounting.report", active_id: wiz, active_ids: [wiz] };
  const options = encodeURIComponent(JSON.stringify(act.data));
  return `/report/html/${act.report_name}/${wiz}?options=${options}&context=${encodeURIComponent(JSON.stringify(ctx))}`;
}

const pedido = (clave) => idOf("sale.order", [["client_order_ref", "=", `DD-${clave}`]]);
const factura = async (clave) => idOf("account.move", [
  ["move_type", "=", "out_invoice"], ["invoice_origin", "=", await call("sale.order", "read", [[await pedido(clave)], ["name"]]).then((r) => r[0].name)],
]);
const entrega = async (clave) => idOf("stock.picking", [
  ["sale_id", "=", await pedido(clave)], ["picking_type_code", "=", "outgoing"],
]);

const CAPTURAS = [
  ["18-crm-etapas", async () => accion(await ref("crm.crm_stage_action"), "list")],
  ["19-cliente-ficha", async () => registro("res.partner", await idOf("res.partner", [["name", "=", "Confitería La Dulzura"]]))],
  ["20-crm-pipeline", async () => accion(await menuAction("CRM/Sales/My Pipeline"), "kanban")],
  ["21-crm-actividades", async () => accion(await menuAction("CRM/Sales/My Activities"), "list")],
  ["22-calendario-recordatorio", async () => registro("calendar.event", await idOf("calendar.event", [["name", "=", "Negociar precio por volumen"]]))],
  ["23-terminos-pago", async () => accion(await menuAction("Invoicing/Configuration/Invoicing/Payment Terms"), "list")],
  ["24-metodos-entrega", async () => accion(await menuAction("Inventory/Configuration/Delivery/Shipping Methods"), "list")],
  ["25-pedido-ladulzura", async () => registro("sale.order", await pedido("LADULZURA"))],
  ["26-pedido-delicias", async () => registro("sale.order", await pedido("DELICIAS"))],
  ["27-pedido-dulcesabor", async () => registro("sale.order", await pedido("DULCESABOR"))],
  ["28-pedidos-lista", async () => accion(await menuAction("Sales/Orders/Orders"), "list")],
  ["29-reporte-ventas", async () => accion(await menuAction("Sales/Reporting/Sales"), "graph")],
  ["30-diarios-pago", async () => accion(await menuAction("Invoicing/Configuration/Accounting/Journals"), "list")],
  ["31-factura-confirmada", async () => registro("account.move", await factura("DELICIAS"))],
  ["32-factura-pago-parcial", async () => registro("account.move", await factura("DULCESABOR"))],
  ["33-pagos-clientes", async () => accion(await menuAction("Invoicing/Customers/Payments"), "list")],
  ["34-facturas-pagadas", async () => accion(await menuAction("Invoicing/Customers/Invoices"), "list")],
  ["35-entregas-lista", async () => accion(await menuAction("Inventory/Operations/Transfers/Deliveries"), "list"), { limpiarFiltros: true }],
  ["36-entrega-validada", async () => registro("stock.picking", await entrega("DELICIAS"))],
  ["38-moves-history", async () => accion(await menuAction("Inventory/Reporting/Moves History"), "list")],
  ["39-stock-tras-ventas", async () => accion(await menuAction("Inventory/Reporting/Stock"), "list")],
  ["40-proyecto-postventa", async () => accion(await ref("project.act_project_project_2_project_task_all"), "kanban",
    `&active_id=${await idOf("project.project", [["name", "=", "Atención al Cliente"]])}`),
    { limpiarFiltros: true, desplegarColumnas: true }],
  ["41-ticket-caso", async () => registro("project.task", await idOf("project.task", [["name", "ilike", "Chocolates en mal estado"]]))],
  ["43-devolucion", async () => registro("stock.picking", await idOf("stock.picking", [["origin", "ilike", "Return of"]]))],
  ["44-nota-credito", async () => registro("account.move", await idOf("account.move", [["move_type", "=", "out_refund"]]))],
  ["47-listado-clientes", async () => accion(await menuAction("Sales/Orders/Customers"), "list")],
  ["48-listado-proveedores", async () => accion(await menuAction("Purchase/Orders/Vendors"), "list")],
  ["49-estado-resultados", plAccion, { reporte: true }],
];

function chromePath() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const raiz = path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"), "ms-playwright");
  const dir = fs.readdirSync(raiz).filter((d) => /^chromium-\d+$/.test(d)).sort().pop();
  if (!dir) throw new Error("No hay Chromium de Playwright; define CHROME_PATH");
  return path.join(raiz, dir, "chrome-win64", "chrome.exe");
}

// Odoo mantiene abierta la conexion del bus, asi que "networkidle" puede no llegar nunca
const quieto = (page) => page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});

async function capturar(page, nombre, url, opts = {}) {
  await page.goto(BASE + (opts.reporte ? url : `/web?c=${nombre}${url}`));
  if (opts.reporte) {
    await quieto(page);
    // Hasta el final de la ultima tabla del reporte
    const fin = await page.evaluate(() =>
      Math.max(300, ...[...document.querySelectorAll("table")].map((t) => t.getBoundingClientRect().bottom)));
    const ancho = page.viewportSize().width;
    await page.screenshot({ path: path.join(OUT, `${nombre}.png`), clip: { x: 0, y: 0, width: ancho, height: fin + 30 } });
    return;
  }
  await page.waitForSelector(".o_action_manager .o_view_controller", { timeout: 30000 });
  await quieto(page);
  if (opts.limpiarFiltros) {
    while (await page.locator(".o_searchview_facet .o_facet_remove").count()) {
      await page.locator(".o_searchview_facet .o_facet_remove").first().click();
      await quieto(page);
    }
  }
  if (opts.desplegarColumnas) {
    // El caso cerrado queda en una columna plegada; se abre para que se vea
    for (const col of await page.locator(".o_kanban_group.o_column_folded").all()) {
      await col.click();
      await quieto(page);
    }
  }
  // Sin avisos flotantes en la captura
  await page.addStyleTag({ content: ".o_notification_manager,.o_tour_pointer{display:none!important}" });
  await page.waitForTimeout(800);
  // Recorta debajo del ultimo contenido visible para no dejar media captura en blanco
  const caja = await page.locator(".o_action_manager").boundingBox();
  const fin = await page.evaluate(() => {
    const root = document.querySelector(".o_action_manager");
    const top = root.getBoundingClientRect().top;
    let max = 0;
    for (const el of root.querySelectorAll("*")) {
      const r = el.getBoundingClientRect();
      const grafico = el.matches("canvas, img, svg");
      if (!r.height || (!grafico && r.height > 300)) continue;
      if (el.children.length && !el.matches(".o_kanban_record, button")) continue;
      if (!grafico && !el.matches("input, .o_kanban_record, button") && !el.textContent.trim()) continue;
      max = Math.max(max, r.bottom - top);
    }
    return max;
  });
  const alto = Math.min(caja.height, Math.max(300, fin + 24));
  await page.screenshot({ path: path.join(OUT, `${nombre}.png`), clip: { ...caja, height: alto } });
}

async function main() {
  if (!PASSWORD) throw new Error("Define ODOO_PASSWORD");
  const filtro = process.argv.slice(2);
  const lista = CAPTURAS.filter(([n]) => !filtro.length || filtro.some((f) => n.startsWith(f)));

  await jsonrpc("/web/session/authenticate", { db: DB, login: LOGIN, password: PASSWORD });
  const browser = await chromium.launch({ executablePath: chromePath() });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, locale: "en-US" });
  const { hostname } = new URL(BASE);
  await context.addCookies([{ name: "session_id", value: cookie.split("=")[1], domain: hostname, path: "/" }]);
  const page = await context.newPage();

  let fallos = 0;
  for (const [nombre, url, opts] of lista) {
    try {
      await capturar(page, nombre, await url(), opts);
      console.log(`ok   ${nombre}`);
    } catch (e) {
      fallos++;
      console.log(`FALLO ${nombre}: ${e.message.split("\n")[0]}`);
    }
  }
  await browser.close();
  if (fallos) process.exitCode = 1;
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
