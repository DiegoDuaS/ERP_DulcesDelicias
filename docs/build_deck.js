// Genera docs/presentacion.pptx a partir de las capturas en docs/capturas/
// Uso: node docs/build_deck.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const CAP_DIR = path.join(__dirname, "capturas");
const OUT = path.join(__dirname, "presentacion.pptx");

const COCOA = "3B2417";
const CARAMEL = "D98E32";
const CANDY = "C2185B";
const INK = "2B2B2B";
const MUTED = "6B6B6B";
const HEAD = "Cambria";
const BODY = "Calibri";

// Cada slide: titulo, puntos, nombre base de la captura (sin extension)
const SECTIONS = [
  {
    title: "Configuración de productos y materias primas",
    subtitle: "Punto 1",
    slides: [
      { t: "Catálogo de productos", b: ["3 productos terminados: caramelos, chocolates y galletas", "8 materias primas almacenables con UdM y costo"], img: "01-productos-lista" },
      { t: "Ficha de una materia prima", b: ["Tipo almacenable, UdM en kg y costo definido", "Solo compra: no se vende al cliente"], img: "02-insumo-azucar" },
      { t: "Proveedor del insumo", b: ["Distribuidora SixSeven S.A. como proveedor", "Precio y cantidad mínima de compra"], img: "03-insumo-proveedor" },
      { t: "Stock mínimo y máximo", b: ["Regla de reordenamiento: mín. 50, máx. 200", "Ubicación WH/Stock/Materias Primas", "Disparador manual"], img: "04-regla-reorden" },
      { t: "Producto terminado con ruta de fabricación", b: ["Ruta Manufacture activada", "Precio de venta definido"], img: "05-terminado-manufacture" },
    ],
  },
  {
    title: "Gestión de inventarios",
    subtitle: "Punto 2",
    slides: [
      { t: "Ubicaciones internas", b: ["WH/Stock/Materias Primas", "WH/Stock/Productos Terminados"], img: "06-ubicaciones" },
      { t: "Inventario inicial", b: ["Cantidades cargadas en Physical Inventory", "Azúcar en 20 kg: bajo el mínimo a propósito"], img: "07-physical-inventory" },
      { t: "Existencias con stock bajo", b: ["Reporte de Stock tras aplicar el inventario"], img: "08-stock-azucar-20" },
      { t: "Orden de compra", b: ["Generada automáticamente para el proveedor", "Confirmada con Confirm Order"], img: "10-orden-compra" },
      { t: "Recepción de mercancía", b: ["Receipt validado", "El stock entra a inventario"], img: "11-recepcion" },
      { t: "Inventario repuesto", b: ["Azúcar en 200 kg: máximo alcanzado"], img: "12-stock-azucar-200" },
    ],
  },
  {
    title: "Planificación y ejecución de la producción",
    subtitle: "Punto 3",
    slides: [
      { t: "Centro de trabajo", b: ["Línea de Producción", "Requerido para registrar operaciones y tiempos"], img: "13a-centro-trabajo" },
      { t: "Listas de materiales", b: ["Una lista de materiales por producto", "Tipo: fabricar este producto"], img: "13-bom-lista" },
      { t: "Chocolates: componentes", b: ["Lote de 50 unidades", "Cacao 5 kg, azúcar 3 kg, leche 2 L"], img: "14-bom-chocolates" },
      { t: "Chocolates: operación", b: ["Templado y Moldeado", "30 minutos"], img: "14-bom-chocolates-ops" },
      { t: "Caramelos: componentes", b: ["Lote de 100 unidades", "Azúcar 8 kg, saborizantes 0.2 L, colorantes 0.1 L"], img: "14-bom-caramelos" },
      { t: "Caramelos: operación", b: ["Cocción y Vertido", "40 minutos"], img: "14-bom-caramelos-ops" },
      { t: "Galletas: componentes", b: ["Lote de 50 unidades", "Harina 4 kg, azúcar 2 kg, mantequilla 2 kg, huevos 12 unidades"], img: "14-bom-galletas" },
      { t: "Galletas: operación", b: ["Amasado y Horneado", "45 minutos"], img: "14-bom-galletas-ops" },
      { t: "Órdenes de fabricación", b: ["Un lote de cada producto", "Componentes disponibles y órdenes confirmadas"], img: "15-ordenes-lista" },
      { t: "Chocolates: orden de fabricación", b: ["50 unidades", "Cacao, azúcar y leche tomados de WH/Stock"], img: "15-orden-chocolates" },
      { t: "Galletas: orden de fabricación", b: ["50 unidades", "Harina, azúcar, mantequilla y huevos"], img: "15-orden-galletas" },
      { t: "Caramelos: orden de fabricación", b: ["100 unidades", "Azúcar, saborizantes y colorantes"], img: "15-orden-caramelos" },
      { t: "Órdenes de trabajo", b: ["Tiempo de producción registrado", "Operación finalizada"], img: "16-work-orders" },
      { t: "Impacto en inventarios", b: ["Materias primas consumidas", "Productos terminados disponibles"], img: "17-stock-final" },
    ],
  },
  {
    title: "Gestión de clientes (CRM)",
    subtitle: "Punto 4",
    slides: [
      { t: "Etapas del ciclo de ventas", b: ["Prospecto, Calificado, Negociación y Cierre (Ganado)", "Cierre marcado como etapa ganada"], img: "18-crm-etapas" },
      { t: "Ficha de cliente", b: ["Tipo de cliente y preferencias como etiquetas", "Persona de contacto, teléfono y correo", "Historial de compras en el botón Sales"], img: "19-cliente-ficha" },
      { t: "Oportunidades por etapa", b: ["La Dulzura: Prospecto", "Supermercado Delicias: Negociación", "Dulce Sabor: Cierre (Ganado)"], img: "20-crm-pipeline" },
      { t: "Seguimientos programados", b: ["Llamada, correo y tarea por oportunidad", "Fechas de vencimiento por actividad"], img: "21-crm-actividades" },
      { t: "Reunión con recordatorio", b: ["Negociación con Supermercado Delicias", "Alerta 1 hora antes en el calendario"], img: "22-calendario-recordatorio" },
    ],
  },
  {
    title: "Gestión de ventas",
    subtitle: "Punto 5",
    slides: [
      { t: "Términos de pago", b: ["Pago inmediato y a 30 días", "Nuevo: 50% anticipo / 50% a 30 días"], img: "23-terminos-pago" },
      { t: "Condiciones de entrega", b: ["Reparto propio sin costo", "Flete a distribuidor con precio fijo"], img: "24-metodos-entrega" },
      { t: "Pedido: Confitería La Dulzura", b: ["20 caramelos, 10 chocolates, 10 galletas", "Pago inmediato, entrega completa"], img: "25-pedido-ladulzura" },
      { t: "Pedido: Supermercado Delicias", b: ["40 caramelos, 20 chocolates, 20 galletas", "Pago a 30 días, entrega parcial permitida"], img: "26-pedido-delicias" },
      { t: "Pedido: Distribuidora Dulce Sabor", b: ["30 caramelos, 15 chocolates, 15 galletas", "50% / 50%, flete e Incoterm EXW"], img: "27-pedido-dulcesabor" },
      { t: "Seguimiento de pedidos", b: ["Estado de facturación y de entrega por pedido"], img: "28-pedidos-lista" },
      { t: "Análisis de ventas", b: ["Ventas por cliente y producto"], img: "29-reporte-ventas" },
    ],
  },
  {
    title: "Facturación",
    subtitle: "Punto 6",
    slides: [
      { t: "Métodos de pago", b: ["Un diario por método", "Transferencia, tarjeta y contra entrega"], img: "30-diarios-pago" },
      { t: "Factura generada desde el pedido", b: ["Contabilizada y enviada al cliente", "Término de pago heredado del pedido"], img: "31-factura-confirmada" },
      { t: "Pago en dos partes", b: ["Dulce Sabor: 50% al facturar", "50% restante contra entrega"], img: "32-factura-pago-parcial" },
      { t: "Pagos registrados", b: ["Cada pago en el diario de su método"], img: "33-pagos-clientes" },
      { t: "Facturas pagadas", b: ["Las tres facturas en estado Paid"], img: "34-facturas-pagadas" },
    ],
  },
  {
    title: "Gestión de entregas",
    subtitle: "Punto 7",
    slides: [
      { t: "Órdenes de entrega", b: ["Generadas al confirmar cada pedido", "Fecha programada por cliente"], img: "35-entregas-lista" },
      { t: "Entrega completada", b: ["Validada al llegar al cliente", "El pedido queda totalmente entregado"], img: "36-entrega-validada" },
      { t: "Movimientos de inventario", b: ["De WH/Stock a Partners/Customers"], img: "38-moves-history" },
      { t: "Stock después de las ventas", b: ["Productos terminados descontados", "Las materias primas no cambian"], img: "39-stock-tras-ventas" },
    ],
  },
  {
    title: "Atención postventa",
    subtitle: "Punto 8",
    slides: [
      { t: "Proyecto de atención al cliente", b: ["Helpdesk es de Odoo Enterprise", "En Community: proyecto con etapas de atención"], img: "40-proyecto-postventa" },
      { t: "Caso: chocolates en mal estado", b: ["La Dulzura recibió 5 chocolates derretidos", "Seguimiento completo en el historial"], img: "41-ticket-caso" },
      { t: "Devolución del producto", b: ["5 chocolates devueltos al inventario"], img: "43-devolucion" },
      { t: "Nota de crédito", b: ["Reembolso de los 5 chocolates", "Pagado a la tarjeta del cliente", "Caso cerrado"], img: "44-nota-credito" },
    ],
  },
  {
    title: "Reportes",
    subtitle: "Punto 9",
    slides: [
      { t: "Estado del inventario", b: ["Existencias y valor por producto"], img: "39-stock-tras-ventas" },
      { t: "Listado de clientes", b: ["Los tres clientes con sus datos de contacto"], img: "47-listado-clientes" },
      { t: "Listado de proveedores", b: ["Distribuidora SixSeven S.A."], img: "48-listado-proveedores" },
      { t: "Estado de resultados", b: ["Periodo: octubre 2026", "Ingresos: Q 892.86", "Costo de ventas: Q 160.71"], img: "49-estado-resultados" },
    ],
  },
];

function findImage(base) {
  for (const ext of [".png", ".jpg", ".jpeg"]) {
    const p = path.join(CAP_DIR, base + ext);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

// Ancho / alto de un PNG, leido de su cabecera IHDR
function pngRatio(file) {
  const buf = fs.readFileSync(file).subarray(16, 24);
  return buf.readUInt32BE(0) / buf.readUInt32BE(4);
}

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10" x 5.625"
pres.title = "Dulces Delicias S.A. - Implementación en Odoo";
pres.fontFace = BODY;

// Portada
{
  const s = pres.addSlide();
  s.background = { color: COCOA };
  s.addText("Dulces Delicias S.A.", {
    x: 0.7, y: 1.6, w: 8.6, h: 1.0, fontFace: HEAD, fontSize: 44, bold: true,
    color: "FFFFFF", isTextBox: true, margin: 0,
  });
  s.addText("Implementación de Odoo: de la materia prima a la postventa", {
    x: 0.7, y: 2.7, w: 8.6, h: 0.7, fontFace: BODY, fontSize: 22,
    color: CARAMEL, isTextBox: true, margin: 0,
  });
  s.addText("Puntos 1 al 9 del caso de estudio", {
    x: 0.7, y: 4.4, w: 8.6, h: 0.4, fontFace: BODY, fontSize: 14,
    color: "D7CCC8", isTextBox: true, margin: 0,
  });
}

// Alcance
{
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };
  s.addText("Alcance", {
    x: 0.5, y: 0.35, w: 9, h: 0.7, fontFace: HEAD, fontSize: 36, bold: true,
    color: COCOA, isTextBox: true, margin: 0,
  });
  // Dos columnas para que entren los 9 puntos
  const filas = Math.ceil(SECTIONS.length / 2);
  SECTIONS.forEach((sec, i) => {
    const x = i < filas ? 0.5 : 5.1;
    const y = 1.3 + (i % filas) * 0.8;
    s.addShape(pres.ShapeType.ellipse, {
      x, y, w: 0.6, h: 0.6, fill: { color: CANDY }, line: { color: CANDY },
    });
    s.addText(String(i + 1), {
      x, y, w: 0.6, h: 0.6, align: "center", valign: "middle",
      fontFace: HEAD, fontSize: 22, bold: true, color: "FFFFFF", isTextBox: true, margin: 0,
    });
    s.addText(sec.title, {
      x: x + 0.8, y, w: 3.7, h: 0.6, valign: "middle", fontFace: BODY, fontSize: 17,
      color: INK, isTextBox: true, margin: 0,
    });
  });
}

SECTIONS.forEach((sec) => {
  // Divisor
  const d = pres.addSlide();
  d.background = { color: COCOA };
  d.addText(sec.subtitle.toUpperCase(), {
    x: 0.7, y: 1.7, w: 8.6, h: 0.5, fontFace: BODY, fontSize: 16, bold: true,
    color: CARAMEL, charSpacing: 4, isTextBox: true, margin: 0,
  });
  d.addText(sec.title, {
    x: 0.7, y: 2.3, w: 8.6, h: 1.4, fontFace: HEAD, fontSize: 38, bold: true,
    color: "FFFFFF", isTextBox: true, margin: 0,
  });

  sec.slides.forEach((sl) => {
    const s = pres.addSlide();
    s.background = { color: "FFFFFF" };
    s.addText(sl.t, {
      x: 0.5, y: 0.3, w: 9, h: 0.8, fontFace: HEAD, fontSize: 30, bold: true,
      color: COCOA, isTextBox: true, margin: 0, valign: "middle",
    });
    const img = findImage(sl.img);
    // Capturas muy anchas (listas, embudos): puntos arriba e imagen a todo el ancho
    const ancha = img && img.endsWith(".png") && pngRatio(img) > 2.2;
    const textBox = ancha
      ? { x: 0.5, y: 1.15, w: 9, h: 1.0, fontSize: 14 }
      : { x: 0.5, y: 1.4, w: 3.1, h: 3.6, fontSize: 16 };
    s.addText(
      sl.b.map((txt, i) => ({
        text: txt,
        options: { bullet: true, breakLine: i < sl.b.length - 1, paraSpaceAfter: ancha ? 4 : 10 },
      })),
      { ...textBox, fontFace: BODY, color: INK, valign: "top", isTextBox: true, margin: 0 }
    );
    const box = ancha ? { x: 0.5, y: 2.3, w: 9, h: 3.0 } : { x: 3.9, y: 1.3, w: 5.6, h: 3.8 };
    if (img) {
      s.addImage({
        path: img, ...box, sizing: { type: "contain", w: box.w, h: box.h },
        altText: sl.t,
      });
    } else {
      s.addShape(pres.ShapeType.rect, {
        ...box, fill: { color: "F3EDEA" }, line: { color: "BCAAA4", width: 1, dashType: "dash" },
      });
      s.addText("Captura pendiente\n" + sl.img + ".png", {
        ...box, align: "center", valign: "middle", fontFace: BODY, fontSize: 14,
        color: MUTED, isTextBox: true,
      });
    }
  });
});

// Cierre
{
  const s = pres.addSlide();
  s.background = { color: COCOA };
  s.addText("Resultado", {
    x: 0.7, y: 1.2, w: 8.6, h: 0.8, fontFace: HEAD, fontSize: 38, bold: true,
    color: "FFFFFF", isTextBox: true, margin: 0,
  });
  s.addText(
    [
      { text: "Materias primas y productos terminados configurados", options: { bullet: true, breakLine: true, paraSpaceAfter: 10 } },
      { text: "Inventario con reabastecimiento automatizado desde compras", options: { bullet: true, breakLine: true, paraSpaceAfter: 10 } },
      { text: "Producción planificada con listas de materiales y órdenes de trabajo", options: { bullet: true, breakLine: true, paraSpaceAfter: 10 } },
      { text: "Clientes, oportunidades, ventas, facturas y cobros conectados", options: { bullet: true, breakLine: true, paraSpaceAfter: 10 } },
      { text: "Entregas, postventa y estado de resultados sobre los mismos datos", options: { bullet: true } },
    ],
    { x: 0.7, y: 2.2, w: 8.6, h: 3.0, fontFace: BODY, fontSize: 20, color: "FFFFFF", valign: "top", isTextBox: true, margin: 0 }
  );
}

pres.writeFile({ fileName: OUT }).then(() => console.log("OK:", OUT));
