#!/usr/bin/env python3
"""Carga en Odoo 17 los datos de los puntos 4 a 9 del caso Dulces Delicias S.A.

Parte de la base restaurada con los puntos 1-3 (productos, BoM, compra P00001 y
las 3 ordenes de fabricacion). Cada paso busca antes de crear, asi que el script
se puede correr varias veces sin duplicar datos.

Uso:
    python scripts/seed_puntos_4_9.py                    # todos los pasos
    python scripts/seed_puntos_4_9.py --solo crm,ventas  # solo algunos

Variables de entorno (con sus valores por defecto):
    ODOO_URL=http://localhost:8069  ODOO_DB=dulces_delicias
    ODOO_USER=admin@dulcesdelicias.com  ODOO_PASSWORD=(se pide si falta)
"""
import argparse
import getpass
import os
import sys
import xmlrpc.client
from datetime import date, datetime, timedelta

HOY = date.today()

# --- Datos del caso -----------------------------------------------------------

PRODUCTOS = {
    "caramelos": "Caramelos Artesanales",
    "chocolates": "Chocolates Artesanales",
    "galletas": "Galletas Artesanales",
}

CLIENTES = [
    {
        "clave": "ladulzura",
        "nombre": "Confitería La Dulzura",
        "tipo": "Minorista",
        "preferencia": "Prefiere chocolates",
        "nota": "Prefiere chocolates y galletas finas. Pedidos pequeños y frecuentes.",
        "contacto": ("Ana Pérez", "Compras"),
        "telefono": "5555-1001",
        "email": "compras@ladulzura.com",
        "oportunidad": "Surtido navideño La Dulzura",
        "etapa": "prospecto",
        "actividades": [("mail.mail_activity_data_call", "Presentar catálogo", 2)],
        "pedido": {"caramelos": 20, "chocolates": 10, "galletas": 10},
        "plazo": "inmediato",
        "entrega": "propio",
        "politica": "one",  # entrega completa
        "dias_entrega": 0,
        "pago": "tarjeta",
    },
    {
        "clave": "delicias",
        "nombre": "Supermercado Delicias",
        "tipo": "Supermercado",
        "preferencia": "Prefiere galletas",
        "nota": "Compra volumen en los 3 productos para góndola.",
        "contacto": ("Luis Gómez", "Jefe de góndola"),
        "telefono": "5555-2002",
        "email": "proveedores@superdelicias.com",
        "oportunidad": "Contrato góndola Delicias",
        "etapa": "negociacion",
        "actividades": [],  # su seguimiento es una reunion con recordatorio
        "reunion": "Negociar precio por volumen",
        "pedido": {"caramelos": 40, "chocolates": 20, "galletas": 20},
        "plazo": "30dias",
        "entrega": "propio",
        "politica": "direct",  # entrega parcial permitida
        "dias_entrega": 1,
        "pago": "transferencia",
    },
    {
        "clave": "dulcesabor",
        "nombre": "Distribuidora Dulce Sabor",
        "tipo": "Distribuidor",
        "preferencia": "Prefiere caramelos",
        "nota": "Distribuidor regional, compra caramelos a granel.",
        "contacto": ("María López", "Gerente"),
        "telefono": "5555-3003",
        "email": "pedidos@dulcesabor.com",
        "oportunidad": "Distribución regional Dulce Sabor",
        "etapa": "cierre",
        "actividades": [
            ("mail.mail_activity_data_email", "Enviar contrato firmado", 1),
            ("mail.mail_activity_data_todo", "Coordinar primera entrega", 3),
        ],
        "pedido": {"caramelos": 30, "chocolates": 15, "galletas": 15},
        "plazo": "50_50",
        "entrega": "flete",
        "politica": "one",
        "incoterm": "account.incoterm_EXW",
        "dias_entrega": 2,
        "pago": "contra_entrega",  # 50 % al facturar, 50 % al entregar
    },
]

ETAPAS_CRM = {  # xmlid de la etapa por defecto -> nuevo nombre
    "crm.stage_lead1": "Prospecto",
    "crm.stage_lead2": "Calificado",
    "crm.stage_lead3": "Negociación",
    "crm.stage_lead4": "Cierre (Ganado)",
}
ETAPA_XMLID = {"prospecto": "crm.stage_lead1", "negociacion": "crm.stage_lead3", "cierre": "crm.stage_lead4"}

DIARIOS = {  # metodo de pago -> (codigo, nombre, tipo)
    "transferencia": ("BNK1", "Banco - Transferencias", "bank"),
    "tarjeta": ("TDC", "Tarjeta de Crédito", "bank"),
    "contra_entrega": ("CE", "Contra Entrega", "cash"),
}

ETAPAS_POSTVENTA = ["Nuevo", "En revisión", "Esperando cliente", "Resuelto", "Cerrado"]
TAGS_POSTVENTA = ["Producto dañado", "Consulta", "Reclamo de entrega"]
CHOCOLATES_DANADOS = 5


# --- Cliente XML-RPC ----------------------------------------------------------

class Odoo:
    def __init__(self, url, db, user, password):
        self.url, self.db, self.password = url, db, password
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.uid = common.authenticate(db, user, password, {})
        if not self.uid:
            sys.exit(f"No se pudo iniciar sesion en {url} (base {db}, usuario {user}).")
        self.models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
        self._fields = {}

    def call(self, model, method, *args, **kw):
        try:
            return self.models.execute_kw(self.db, self.uid, self.password, model, method, list(args), kw)
        except xmlrpc.client.Fault as e:
            # Los metodos que devuelven None no se pueden serializar, pero se ejecutaron.
            if "cannot marshal None" in e.faultString:
                return None
            raise

    def search(self, model, domain, **kw):
        return self.call(model, "search", domain, **kw)

    def read(self, model, ids, fields):
        return self.call(model, "read", ids, fields)

    def first(self, model, domain, fields=("id",)):
        res = self.call(model, "search_read", domain, list(fields), limit=1)
        return res[0] if res else None

    def create(self, model, vals, context=None):
        return self.call(model, "create", vals, **({"context": context} if context else {}))

    def write(self, model, ids, vals):
        return self.call(model, "write", ids if isinstance(ids, list) else [ids], vals)

    def ensure(self, model, domain, vals):
        """Devuelve el id del registro que cumple domain; si no existe, lo crea."""
        found = self.search(model, domain, limit=1)
        return found[0] if found else self.create(model, vals)

    def ref(self, xmlid):
        module, name = xmlid.split(".")
        rec = self.first("ir.model.data", [("module", "=", module), ("name", "=", name)], ["res_id"])
        return rec["res_id"] if rec else False

    def has_field(self, model, field):
        if model not in self._fields:
            self._fields[model] = self.call(model, "fields_get", attributes=["type"])
        return field in self._fields[model]

    def model_id(self, model):
        return self.search("ir.model", [("model", "=", model)])[0]


def paso(titulo):
    print(f"\n=== {titulo}")


def ok(msg):
    print(f"  - {msg}")


# --- Helpers de negocio -------------------------------------------------------

def producto(o, clave):
    nombre = PRODUCTOS[clave]
    ids = o.search("product.product", [("name", "=", nombre)])
    if len(ids) != 1:
        sys.exit(f"Se esperaba 1 producto '{nombre}' y hay {len(ids)}.")
    return ids[0]


def cliente_id(o, c):
    ids = o.search("res.partner", [("name", "=", c["nombre"]), ("is_company", "=", True)])
    if not ids:
        sys.exit(f"Falta el cliente {c['nombre']}: corre antes el paso crm.")
    return ids[0]


def pedido(o, c, fields=("id", "name", "state", "invoice_ids", "picking_ids", "order_line")):
    return o.first("sale.order", [("client_order_ref", "=", f"DD-{c['clave'].upper()}")], fields)


def diario(o, metodo):
    return o.search("account.journal", [("code", "=", DIARIOS[metodo][0])])[0]


def factura_cliente(o, c):
    so = pedido(o, c)
    if not so or not so["invoice_ids"]:
        return None
    return o.first("account.move", [("id", "in", so["invoice_ids"]), ("move_type", "=", "out_invoice"),
                                    ("state", "=", "posted")],
                   ["id", "name", "amount_total", "amount_residual", "payment_state", "journal_id"])


def registrar_pago(o, move_id, metodo, monto=None, fecha=None):
    ctx = {"active_model": "account.move", "active_ids": [move_id]}
    vals = {"journal_id": diario(o, metodo), "payment_date": str(fecha or HOY)}
    if monto is not None:
        vals["amount"] = monto
    wiz = o.create("account.payment.register", vals, context=ctx)
    o.call("account.payment.register", "action_create_payments", [wiz], context=ctx)


def validar_picking(o, picking_id):
    """Reserva, marca todo como hecho y valida (sin backorders)."""
    o.call("stock.picking", "action_assign", [picking_id])
    pick = o.read("stock.picking", [picking_id], ["move_ids", "state"])[0]
    for mv in o.read("stock.move", pick["move_ids"], ["product_uom_qty"]):
        o.write("stock.move", mv["id"], {"quantity": mv["product_uom_qty"], "picked": True})
    ctx = {"skip_backorder": True, "cancel_backorder": True, "skip_sms": True}
    res = o.call("stock.picking", "button_validate", [picking_id], context=ctx)
    state = o.read("stock.picking", [picking_id], ["state"])[0]["state"]
    if state != "done":
        sys.exit(f"El picking {picking_id} quedo en '{state}' (respuesta: {res}). Revisa el stock.")


def actividad(o, model, res_id, xmlid_tipo, resumen, dias):
    existe = o.search("mail.activity", [("res_model", "=", model), ("res_id", "=", res_id),
                                        ("summary", "=", resumen)])
    if existe:
        return existe[0]
    return o.create("mail.activity", {
        "res_model_id": o.model_id(model),
        "res_id": res_id,
        "activity_type_id": o.ref(xmlid_tipo),
        "summary": resumen,
        "date_deadline": str(HOY + timedelta(days=dias)),
        "user_id": o.uid,
    })


# --- Pasos --------------------------------------------------------------------

def preparar(o):
    paso("Preparación: módulos, compañía, valoración y factura de proveedor")

    o.call("ir.module.module", "update_list")
    modulos = ["crm", "sale_management", "delivery", "project", "sale_project", "accounting_pdf_reports"]
    for m in o.call("ir.module.module", "search_read", [("name", "in", modulos)], ["name", "state"]):
        if m["state"] == "installed":
            continue
        o.call("ir.module.module", "button_immediate_install", [m["id"]])
        ok(f"instalado {m['name']}")
    if not o.search("ir.module.module", [("name", "=", "accounting_pdf_reports")]):
        ok("AVISO: accounting_pdf_reports no está en addons/; el estado de resultados no estará disponible")

    o.write("res.company", o.ref("base.main_company"), {"name": "Dulces Delicias S.A."})
    o.write("res.users", o.uid, {"groups_id": [(4, o.ref("account.group_account_user"))]})
    ok("compañía renombrada y usuario con Show Full Accounting Features")

    # Facturar por cantidad pedida: permite facturar antes de entregar (punto 6 antes que 7)
    tmpl = o.search("product.template", [("name", "in", list(PRODUCTOS.values()))])
    o.write("product.template", tmpl, {"invoice_policy": "order"})

    # Valoracion automatica para que el estado de resultados muestre costo de ventas
    categ = o.ref("product.product_category_all")
    actual = o.read("product.category", [categ], ["property_valuation"])[0]["property_valuation"]
    if actual != "real_time":
        try:
            o.write("product.category", categ, {"property_cost_method": "average", "property_valuation": "real_time"})
            ok("categoría All: costo promedio + valoración automática")
        except xmlrpc.client.Fault as e:
            ok(f"AVISO: no se pudo activar la valoración automática: {e.faultString.splitlines()[-1]}")

    # Factura de proveedor de la orden de compra del punto 2
    for po in o.call("purchase.order", "search_read", [("state", "=", "purchase"), ("invoice_status", "=", "to invoice")],
                     ["id", "name"]):
        o.call("purchase.order", "action_create_invoice", [po["id"]])
        bills = o.read("purchase.order", [po["id"]], ["invoice_ids"])[0]["invoice_ids"]
        borradores = o.search("account.move", [("id", "in", bills), ("state", "=", "draft")])
        if borradores:
            o.write("account.move", borradores, {"invoice_date": str(HOY)})
            o.call("account.move", "action_post", borradores)
        ok(f"factura de proveedor contabilizada para {po['name']}")


def crm(o):
    paso("Punto 4: CRM")

    for xmlid, nombre in ETAPAS_CRM.items():
        o.write("crm.stage", o.ref(xmlid), {"name": nombre})
    ok("etapas: " + " → ".join(ETAPAS_CRM.values()))

    for c in CLIENTES:
        tags_partner = [o.ensure("res.partner.category", [("name", "=", t)], {"name": t})
                        for t in (c["tipo"], c["preferencia"])]
        tags_crm = [o.ensure("crm.tag", [("name", "=", t)], {"name": t}) for t in (c["tipo"], c["preferencia"])]

        partner = o.ensure("res.partner", [("name", "=", c["nombre"]), ("is_company", "=", True)],
                           {"name": c["nombre"], "is_company": True})
        o.write("res.partner", partner, {
            "category_id": [(6, 0, tags_partner)],
            "phone": c["telefono"],
            "email": c["email"],
            "city": "Ciudad de Guatemala",
            "country_id": o.ref("base.gt"),
            "customer_rank": 1,
            "comment": f"<p>{c['nota']}</p>",
        })
        nombre_contacto, cargo = c["contacto"]
        o.ensure("res.partner", [("name", "=", nombre_contacto), ("parent_id", "=", partner)], {
            "name": nombre_contacto, "parent_id": partner, "function": cargo,
            "type": "contact", "email": c["email"], "phone": c["telefono"],
        })

        lead = o.ensure("crm.lead", [("name", "=", c["oportunidad"])], {
            "name": c["oportunidad"], "type": "opportunity", "partner_id": partner,
        })
        o.write("crm.lead", lead, {
            "tag_ids": [(6, 0, tags_crm)],
            "date_deadline": str(HOY + timedelta(days=30)),
            "stage_id": o.ref(ETAPA_XMLID[c["etapa"]]),
        })
        for tipo, resumen, dias in c["actividades"]:
            actividad(o, "crm.lead", lead, tipo, resumen, dias)

        if c.get("reunion") and not o.search("calendar.event", [("name", "=", c["reunion"])]):
            inicio = datetime.combine(HOY + timedelta(days=3), datetime.min.time()) + timedelta(hours=15)
            alarma = o.search("calendar.alarm", [("alarm_type", "=", "notification"), ("interval", "=", "hours"),
                                                 ("duration", "=", 1)], limit=1)
            me = o.read("res.users", [o.uid], ["partner_id"])[0]["partner_id"][0]
            o.create("calendar.event", {
                "name": c["reunion"],
                "start": inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "stop": (inicio + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                "partner_ids": [(6, 0, [partner, me])],
                "opportunity_id": lead,
                "res_model_id": o.model_id("crm.lead"),
                "res_id": lead,
                "alarm_ids": [(6, 0, alarma)],
            })
        ok(f"{c['nombre']}: ficha, contacto y oportunidad en {ETAPAS_CRM[ETAPA_XMLID[c['etapa']]]}")


def terminos_pago(o):
    nombre = "50% anticipo / 50% a 30 días"
    plazo = o.search("account.payment.term", [("name", "=", nombre)])
    if not plazo:
        dias = "nb_days" if o.has_field("account.payment.term.line", "nb_days") else "days"
        plazo = [o.create("account.payment.term", {"name": nombre, "line_ids": [
            (0, 0, {"value": "percent", "value_amount": 50, dias: 0}),
            (0, 0, {"value": "percent", "value_amount": 50, dias: 30}),
        ]})]
    return {
        "inmediato": o.ref("account.account_payment_term_immediate"),
        "30dias": o.ref("account.account_payment_term_30days"),
        "50_50": plazo[0],
    }


def metodos_entrega(o):
    res = {}
    for clave, nombre, precio in [("propio", "Reparto propio", 0.0), ("flete", "Flete a distribuidor", 50.0)]:
        prod = o.ensure("product.product", [("name", "=", nombre), ("type", "=", "service")], {
            "name": nombre, "type": "service", "sale_ok": False, "purchase_ok": False,
            "list_price": precio, "invoice_policy": "order",
        })
        carrier = o.ensure("delivery.carrier", [("name", "=", nombre)], {
            "name": nombre, "delivery_type": "fixed", "fixed_price": precio, "product_id": prod,
        })
        res[clave] = {"id": carrier, "producto": prod, "precio": precio, "nombre": nombre}
    return res


def ventas(o):
    paso("Punto 5: Ventas")
    plazos = terminos_pago(o)
    entregas = metodos_entrega(o)
    ok("términos de pago y métodos de entrega listos")

    for c in CLIENTES:
        if pedido(o, c):
            ok(f"{c['nombre']}: el pedido ya existe")
            continue
        partner = cliente_id(o, c)
        lead = o.search("crm.lead", [("name", "=", c["oportunidad"])], limit=1)
        carrier = entregas[c["entrega"]]
        lineas = [(0, 0, {"product_id": producto(o, k), "product_uom_qty": q}) for k, q in c["pedido"].items()]
        lineas.append((0, 0, {
            "product_id": carrier["producto"], "name": carrier["nombre"], "product_uom_qty": 1,
            "price_unit": carrier["precio"], "is_delivery": True,
        }))
        vals = {
            "partner_id": partner,
            "client_order_ref": f"DD-{c['clave'].upper()}",
            "payment_term_id": plazos[c["plazo"]],
            "carrier_id": carrier["id"],
            "picking_policy": c["politica"],
            "commitment_date": f"{HOY + timedelta(days=c['dias_entrega'])} 16:00:00",
            "order_line": lineas,
        }
        if lead:
            vals["opportunity_id"] = lead[0]
        if c.get("incoterm"):
            vals["incoterm"] = o.ref(c["incoterm"])
        so = o.create("sale.order", vals)
        o.call("sale.order", "action_quotation_sent", [so])
        o.call("sale.order", "action_confirm", [so])
        if c["etapa"] == "cierre" and lead:
            o.call("crm.lead", "action_set_won", lead)
        ok(f"{c['nombre']}: pedido {o.read('sale.order', [so], ['name'])[0]['name']} confirmado")


def facturacion(o):
    paso("Punto 6: Facturación")

    for metodo, (codigo, nombre, tipo) in DIARIOS.items():
        existe = o.search("account.journal", [("code", "=", codigo)])
        if existe:
            o.write("account.journal", existe, {"name": nombre})
        else:
            o.create("account.journal", {"name": nombre, "code": codigo, "type": tipo})
    ok("diarios: " + ", ".join(n for _, n, _ in DIARIOS.values()))

    for c in CLIENTES:
        so = pedido(o, c)
        if not so:
            sys.exit(f"Falta el pedido de {c['nombre']}: corre antes el paso ventas.")
        if not factura_cliente(o, c):
            borradores = o.search("account.move", [("id", "in", so["invoice_ids"]), ("state", "=", "draft")])
            if not borradores:
                ctx = {"active_model": "sale.order", "active_ids": [so["id"]], "active_id": so["id"]}
                wiz = o.create("sale.advance.payment.inv", {"advance_payment_method": "delivered",
                                                             "sale_order_ids": [(6, 0, [so["id"]])]}, context=ctx)
                o.call("sale.advance.payment.inv", "create_invoices", [wiz], context=ctx)
                borradores = o.search("account.move", [("id", "in", pedido(o, c)["invoice_ids"]),
                                                       ("state", "=", "draft")])
            o.write("account.move", borradores, {"invoice_date": str(HOY)})
            o.call("account.move", "action_post", borradores)
            # "Send & Print" sin servidor de correo: se marca como enviada y queda nota en el chatter
            o.write("account.move", borradores, {"is_move_sent": True})
            for move_id in borradores:
                o.call("account.move", "message_post", [move_id],
                       body=f"Factura enviada a {c['email']}.", subtype_xmlid="mail.mt_note")

        inv = factura_cliente(o, c)
        if inv["payment_state"] in ("paid", "in_payment"):
            ok(f"{c['nombre']}: {inv['name']} ya pagada")
            continue
        if c["pago"] == "contra_entrega":
            if inv["amount_residual"] == inv["amount_total"]:
                registrar_pago(o, inv["id"], c["pago"], monto=round(inv["amount_total"] / 2, 2))
            ok(f"{c['nombre']}: {inv['name']} con anticipo del 50 % (resto al entregar)")
        else:
            fecha = HOY + timedelta(days=30) if c["plazo"] == "30dias" else HOY
            registrar_pago(o, inv["id"], c["pago"], fecha=fecha)
            ok(f"{c['nombre']}: {inv['name']} pagada por {DIARIOS[c['pago']][1]}")


def entregas(o):
    paso("Punto 7: Entregas")
    for c in CLIENTES:
        so = pedido(o, c)
        for pick in o.read("stock.picking", so["picking_ids"], ["id", "name", "state", "picking_type_code"]):
            if pick["picking_type_code"] != "outgoing" or pick["state"] in ("done", "cancel"):
                continue
            o.write("stock.picking", pick["id"],
                    {"scheduled_date": f"{HOY + timedelta(days=c['dias_entrega'])} 16:00:00"})
            validar_picking(o, pick["id"])
            ok(f"{c['nombre']}: {pick['name']} entregada")

        if c["pago"] == "contra_entrega":
            inv = factura_cliente(o, c)
            if inv and inv["amount_residual"] > 0:
                registrar_pago(o, inv["id"], c["pago"], monto=inv["amount_residual"])
                ok(f"{c['nombre']}: cobrado el 50 % restante contra entrega")

    stock = o.call("stock.quant", "search_read",
                   [("product_id.name", "in", list(PRODUCTOS.values())), ("location_id.usage", "=", "internal")],
                   ["product_id", "quantity"])
    for q in stock:
        ok(f"stock {q['product_id'][1]}: {q['quantity']:g}")


def postventa(o):
    paso("Punto 8: Atención postventa")
    c = CLIENTES[0]  # Confitería La Dulzura
    so = pedido(o, c)

    proyecto = o.ensure("project.project", [("name", "=", "Atención al Cliente")], {"name": "Atención al Cliente"})
    etapas = {}
    for i, nombre in enumerate(ETAPAS_POSTVENTA):
        etapas[nombre] = o.ensure("project.task.type", [("name", "=", nombre), ("project_ids", "in", [proyecto])], {
            "name": nombre, "sequence": i, "project_ids": [(4, proyecto)], "fold": nombre == "Cerrado",
        })
    tags = {t: o.ensure("project.tags", [("name", "=", t)], {"name": t}) for t in TAGS_POSTVENTA}
    ok("proyecto Atención al Cliente con etapas " + " → ".join(ETAPAS_POSTVENTA))

    titulo = f"Chocolates en mal estado – pedido {so['name']}"
    tarea = o.search("project.task", [("name", "=", titulo)])
    if tarea and o.read("project.task", tarea, ["stage_id"])[0]["stage_id"][0] == etapas["Cerrado"]:
        ok("el caso ya está cerrado")
        return

    chocolate = producto(o, "chocolates")
    if not tarea:
        vals = {
            "name": titulo,
            "project_id": proyecto,
            "partner_id": cliente_id(o, c),
            "tag_ids": [(6, 0, [tags["Producto dañado"]])],
            "priority": "1",
            "stage_id": etapas["Nuevo"],
            # sale_line_id solo admite lineas de servicio, asi que el pedido se enlaza en la descripcion
            "description": f"<p>{CHOCOLATES_DANADOS} de 10 chocolates llegaron derretidos. "
                           "El cliente adjunta foto.</p>"
                           f"<p>Pedido: <a href=\"/web#id={so['id']}&amp;model=sale.order&amp;view_type=form\">"
                           f"{so['name']}</a></p>",
        }
        tarea = [o.create("project.task", vals)]
        ok(f"caso registrado: {titulo}")
    tarea = tarea[0]

    # Seguimiento
    o.write("project.task", tarea, {"stage_id": etapas["En revisión"]})
    llamada = actividad(o, "project.task", tarea, "mail.mail_activity_data_call", "Confirmar daño con el cliente", 0)
    o.call("project.task", "message_post", [tarea], subtype_xmlid="mail.mt_note",
           body="Daño verificado con el cliente. Causa probable: cadena de frío durante el reparto.")
    o.call("mail.activity", "action_feedback", [llamada], feedback="Cliente confirma 5 unidades dañadas.")
    o.write("project.task", tarea, {"stage_id": etapas["Esperando cliente"]})
    ok("seguimiento: llamada hecha, nota registrada, esperando recolección")

    # Resolucion 1: devolucion de los 5 chocolates
    salida = o.first("stock.picking", [("id", "in", so["picking_ids"]), ("picking_type_code", "=", "outgoing"),
                                       ("state", "=", "done")], ["id", "name", "location_id"])
    devolucion = o.first("stock.picking", [("origin", "=", f"Return of {salida['name']}")], ["id", "name", "state"])
    if not devolucion:
        mov = o.first("stock.move", [("picking_id", "=", salida["id"]), ("product_id", "=", chocolate)],
                      ["id", "product_uom"])
        linea = {"product_id": chocolate, "quantity": CHOCOLATES_DANADOS, "move_id": mov["id"],
                 "uom_id": mov["product_uom"][0]}
        if o.has_field("stock.return.picking.line", "to_refund"):
            linea["to_refund"] = True
        ctx = {"active_model": "stock.picking", "active_id": salida["id"], "active_ids": [salida["id"]]}
        wiz_vals = {"picking_id": salida["id"], "product_return_moves": [(0, 0, linea)]}
        if o.has_field("stock.return.picking", "location_id"):
            wiz_vals["location_id"] = salida["location_id"][0]
        wiz = o.create("stock.return.picking", wiz_vals, context=ctx)
        accion = o.call("stock.return.picking", "create_returns", [wiz], context=ctx)
        devolucion = o.read("stock.picking", [accion["res_id"]], ["id", "name", "state"])[0]
    if devolucion["state"] != "done":
        validar_picking(o, devolucion["id"])
    ok(f"devolución {devolucion['name']} validada")

    # Resolucion 2: nota de credito por los 5 chocolates y reembolso
    inv = factura_cliente(o, c)
    nc = o.first("account.move", [("reversed_entry_id", "=", inv["id"])], ["id", "name", "state"])
    if not nc:
        ctx = {"active_model": "account.move", "active_ids": [inv["id"]]}
        wiz = o.create("account.move.reversal", {
            "move_ids": [(6, 0, [inv["id"]])], "reason": "Producto en mal estado",
            "journal_id": inv["journal_id"][0], "date": str(HOY),
        }, context=ctx)
        accion = o.call("account.move.reversal", "refund_moves", [wiz], context=ctx)
        nc = {"id": accion["res_id"], "state": "draft"}
    if nc["state"] == "draft":
        lineas = o.call("account.move.line", "search_read",
                        [("move_id", "=", nc["id"]), ("display_type", "=", "product")], ["id", "product_id"])
        cambios = []
        for ln in lineas:
            if ln["product_id"] and ln["product_id"][0] == chocolate:
                cambios.append((1, ln["id"], {"quantity": CHOCOLATES_DANADOS}))
            else:
                cambios.append((2, ln["id"]))
        o.write("account.move", nc["id"], {"invoice_line_ids": cambios})
        o.call("account.move", "action_post", [nc["id"]])
    nc = o.read("account.move", [nc["id"]], ["id", "name", "payment_state"])[0]
    if nc["payment_state"] not in ("paid", "in_payment"):
        registrar_pago(o, nc["id"], c["pago"])
    ok(f"nota de crédito {nc['name']} contabilizada y reembolsada")

    o.call("project.task", "message_post", [tarea], subtype_xmlid="mail.mt_note",
           body=f"Resuelto: devolución {devolucion['name']} y nota de crédito {nc['name']} "
                f"por {CHOCOLATES_DANADOS} chocolates.")
    o.write("project.task", tarea, {"stage_id": etapas["Resuelto"]})
    o.write("project.task", tarea, {"stage_id": etapas["Cerrado"]})
    ok("caso movido a Resuelto y luego a Cerrado")


def reportes(o):
    paso("Punto 9: Reportes (verificación)")
    clientes = o.call("res.partner", "search_count", [("customer_rank", ">", 0), ("is_company", "=", True)])
    proveedores = o.call("res.partner", "search_count", [("supplier_rank", ">", 0)])
    ok(f"clientes: {clientes}  ·  proveedores: {proveedores}")
    pdf = o.first("ir.module.module", [("name", "=", "accounting_pdf_reports")], ["state"])
    if pdf and pdf["state"] == "installed":
        ok("estado de resultados: Invoicing → Reporting → Profit and Loss")
    else:
        ok("AVISO: accounting_pdf_reports no instalado; no hay Profit and Loss en Community")
    ok("inventario: Inventory → Reporting → Stock  ·  clientes: Sales → Orders → Customers  ·  "
       "proveedores: Purchase → Orders → Vendors")


PASOS = {
    "preparar": preparar,
    "crm": crm,
    "ventas": ventas,
    "facturacion": facturacion,
    "entregas": entregas,
    "postventa": postventa,
    "reportes": reportes,
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows no siempre muestra ñ, á o →
    ap =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solo", help="pasos separados por coma: " + ",".join(PASOS))
    args = ap.parse_args()

    elegidos = args.solo.split(",") if args.solo else list(PASOS)
    desconocidos = set(elegidos) - set(PASOS)
    if desconocidos:
        ap.error(f"pasos desconocidos: {', '.join(desconocidos)}")

    password = os.environ.get("ODOO_PASSWORD") or getpass.getpass("Contraseña de Odoo: ")
    o = Odoo(os.environ.get("ODOO_URL", "http://localhost:8069"),
             os.environ.get("ODOO_DB", "dulces_delicias"),
             os.environ.get("ODOO_USER", "admin@dulcesdelicias.com"),
             password)
    for nombre in PASOS:
        if nombre in elegidos:
            PASOS[nombre](o)
    print("\nListo.")


if __name__ == "__main__":
    main()
