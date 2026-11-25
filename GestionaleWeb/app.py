import os
import io
import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from PIL import Image as PILImage

st.set_page_config(
    page_title="Cartongesso & Color Group S.r.l. - Gestione Preventivi",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #1b2340;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff;
    }
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] * {
        color: #1b2340 !important;
    }
    .stButton>button[kind="primary"] {
        background-color: #f2b718;
        color: #1b2340;
        font-weight: bold;
        border: none;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #d9a110;
        color: #1b2340;
    }
    h1, h2, h3 {
        color: #1b2340;
    }
    </style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "contabilita_soci.db")
SOCIO_1, SOCIO_2 = "BAGLI", "TROPEA"
def trova_logo():
    estensioni_valide = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    if os.path.exists(BASE_DIR):
        for file in os.listdir(BASE_DIR):
            if "logo" in file.lower() and file.lower().endswith(estensioni_valide):
                return os.path.join(BASE_DIR, file)
    return None


def inizializza_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preventivi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num TEXT,
            data_doc TEXT,
            cliente TEXT,
            indirizzo TEXT,
            telefono TEXT,
            descrizione TEXT,
            importo REAL,
            socio TEXT,
            stato TEXT DEFAULT 'In Attesa'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listino (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice TEXT UNIQUE,
            descrizione TEXT,
            prezzo_unitario REAL,
            unita_misura TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM listino")
    if cursor.fetchone()[0] == 0:
        lavori_default = [
            ('CART01', 'FORNITURA E POSA DI CONTROSOFFITTO IN CARTONGESSO COSTITUITO DA STRUTTURA DI SOSTEGNO E LASTRA STANDARD', 35.00, 'mq'),
            ('CART02', 'FORNITURA E POSA CONTROPARETE CON STRUTTURA DI SOSTEGNO IN LAMIERA ZINCATA E LASTRA STANDARD', 40.00, 'mq'),
            ('TINT01', 'POSA DI RASATURA A PARO + TINTEGGIATURA INTERNA LAVABILE', 18.00, 'mq'),
            ('VELE01', 'FORNITURA E POSA IN OPERA DI VELETTA PERIMETRALE PER INCASSO LED', 25.00, 'ml')
        ]
        cursor.executemany(
            "INSERT INTO listino (codice, descrizione, prezzo_unitario, unita_misura) VALUES (?, ?, ?, ?)",
            lavori_default
        )
    conn.commit()
    conn.close()


def genera_numero_progressivo():
    anno_corrente = datetime.now().year
    suffisso = f"/{anno_corrente}"
    conn = sqlite3.connect(DB_PATH)
    righe = conn.execute("SELECT num FROM preventivi").fetchall()
    conn.close()

    max_num = 0
    for (num_str,) in righe:
        if not num_str:
            continue
        num_str = str(num_str).strip()
        if num_str.endswith(suffisso):
            parte_num = num_str[:-len(suffisso)].strip()
            if parte_num.isdigit():
                val = int(parte_num)
                if val > max_num:
                    max_num = val
        elif num_str.isdigit():
            val = int(num_str)
            if val > max_num:
                max_num = val

    return f"{max_num + 1}/{anno_corrente}"


def controlla_data_filtro(data_str, scelta, anno_sel, mese_o_semestre_sel):
    if not data_str:
        return False
    try:
        dt = datetime.strptime(data_str.strip(), "%Y-%m-%d")
    except ValueError:
        return False

    if scelta == "Tutto lo Storico":
        return True
    if str(dt.year) != str(anno_sel):
        return False
    if scelta == "Annuale":
        return True
    if scelta == "Mensile":
        mesi = {
            "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
            "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
            "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
        }
        return dt.month == mesi.get(mese_o_semestre_sel, 1)
    if scelta == "Semestrale":
        if "1°" in mese_o_semestre_sel:
            return 1 <= dt.month <= 6
        else:
            return 7 <= dt.month <= 12
    return False
def genera_pdf_bytes(row_dict, percorso_logo):
    buffer_pdf = io.BytesIO()
    num_doc = row_dict["num"]
    data_doc = row_dict["data_doc"]
    cliente = row_dict["cliente"]
    indirizzo = row_dict["indirizzo"] or ""
    telefono = row_dict["telefono"] or ""
    descrizione = row_dict["descrizione"] or ""
    importo_str = f"{float(row_dict['importo']):,.2f}"

    data_formattata = data_doc
    try:
        dt_obj = datetime.strptime(data_doc.strip(), "%Y-%m-%d")
        data_formattata = dt_obj.strftime("%d/%m/%Y")
    except ValueError:
        pass

    doc = SimpleDocTemplate(
        buffer_pdf,
        pagesize=A4,
        rightMargin=28,
        leftMargin=28,
        topMargin=22,
        bottomMargin=22,
        title=f"Preventivo_{num_doc}"
    )
    story = []

    BLU_LOGO = colors.HexColor("#1b2340")
    BLU_CHIARO = colors.HexColor("#eef2f8")
    GIALLO_LOGO = colors.HexColor("#f2b718")
    GRIGIO_CHIARO = colors.HexColor("#f8f9fa")
    GRIGIO_BORDO = colors.HexColor("#d0d7de")
    GRIGIO_TESTO = colors.HexColor("#333333")

    s_badge_titolo = ParagraphStyle("BadgeTit", fontName="Helvetica-Bold", fontSize=11, alignment=1, textColor=GIALLO_LOGO)
    s_badge_sub = ParagraphStyle("BadgeSub", fontName="Helvetica-Bold", fontSize=9, alignment=1, textColor=colors.white)
    s_spett_label = ParagraphStyle("SpettLbl", fontName="Helvetica-Bold", fontSize=8, textColor=BLU_LOGO)
    s_spett_val = ParagraphStyle("SpettVal", fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.black)
    s_azienda = ParagraphStyle("Azienda", fontName="Helvetica", fontSize=8, leading=11.5, textColor=GRIGIO_TESTO)
    s_desc_az = ParagraphStyle("DescAz", fontName="Helvetica-Oblique", fontSize=7.5, leading=10, textColor=GRIGIO_TESTO)

    if percorso_logo and os.path.exists(percorso_logo):
        try:
            with PILImage.open(percorso_logo) as img:
                if img.mode in ("RGBA", "LA", "P"):
                    sfondo = PILImage.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    sfondo.paste(img, mask=img.split()[-1])
                    img = sfondo
                else:
                    img = img.convert("RGB")
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="JPEG", quality=95)
                img_buffer.seek(0)
            logo_cell = Image(img_buffer, width=350, height=85, kind="proportional")
            logo_cell.hAlign = "LEFT"
        except Exception:
            logo_cell = Image(percorso_logo, width=350, height=85, kind="proportional")
            logo_cell.hAlign = "LEFT"
    else:
        logo_cell = Paragraph(
            "<font color='#1b2340'><b>CARTONGESSO<br/>&amp; COLOR</b></font> <font color='#f2b718'><b>GROUP S.R.L.</b></font>",
            ParagraphStyle("FallbackLogo", fontName="Helvetica-Bold", fontSize=18, leading=20)
        )

    badge_box = Table([
        [Paragraph(f"PREVENTIVO N° {num_doc}", s_badge_titolo)],
        [Paragraph(f"Data: {data_formattata}", s_badge_sub)]
    ], colWidths=[165])
    badge_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLU_LOGO),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("BOX", (0, 0), (-1, -1), 1.5, GIALLO_LOGO),
    ]))

    t_top = Table([[logo_cell, badge_box]], colWidths=[374, 165])
    t_top.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_top)

    barra_colorata = Table([["", ""]], colWidths=[374, 165], rowHeights=[4])
    barra_colorata.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BLU_LOGO),
        ("BACKGROUND", (1, 0), (1, 0), GIALLO_LOGO),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(barra_colorata)
    story.append(Spacer(1, 10))

    dati_soci = (
        "<font color='#1b2340'><b>DI BAGLI UMBERTO E TROPEA LEONARDO</b></font><br/>"
        "Via Str. 11 Cosentini Trv. C3 N.19 - 95018 Riposto (CT)<br/>"
        "Cell: 347 0719403 – 388 1655596 | Ufficio: 376 254 6251<br/>"
        "Email: info.cartongessocolorgroup@gmail.com<br/>"
        "PEC: cartongesso.color@pec.it"
    )

    info_cliente = f"<b>{cliente}</b>"
    if indirizzo:
        info_cliente += f"<br/>{indirizzo}"
    if telefono:
        info_cliente += f"<br/>Tel. {telefono}"

    box_cliente = Table([
        [Paragraph("SPETT.LE CLIENTE", s_spett_label)],
        [Paragraph(info_cliente, s_spett_val)]
    ], colWidths=[240])
    box_cliente.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIGIO_CHIARO),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, GIALLO_LOGO),
        ("BOX", (0, 0), (-1, -1), 0.5, GRIGIO_BORDO),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    t_info_az = Table([[Paragraph(dati_soci, s_azienda), box_cliente]], colWidths=[299, 240])
    t_info_az.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_info_az)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "Progettazione, costruzione a secco, divisioni in cartongesso, isolamenti termo-acustici, protezione al fuoco REI 120, allestimento locali commerciali, tinteggiature interne ed esterne, parati e cornici, decorazioni, controsoffitti civili e industriali, pavimenti galleggianti, impermeabilizzazioni.",
        s_desc_az
    ))
    story.append(Spacer(1, 10))
    s_th = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=8.5, alignment=1, textColor=colors.white)
    s_th_left = ParagraphStyle("THL", fontName="Helvetica-Bold", fontSize=8.5, alignment=0, textColor=colors.white)
    s_td = ParagraphStyle("TD", fontName="Helvetica", fontSize=8, leading=10.5, textColor=colors.black)
    s_td_center = ParagraphStyle("TDC", fontName="Helvetica", fontSize=8.5, alignment=1, textColor=colors.black)
    s_td_right = ParagraphStyle("TDR", fontName="Helvetica-Bold", fontSize=8.5, alignment=2, textColor=BLU_LOGO)

    table_data = [[
        Paragraph("DESCRIZIONE LAVORI", s_th_left),
        Paragraph("MISURE", s_th),
        Paragraph("PREZZO UNIT.", s_th),
        Paragraph("TOTALE", s_th)
    ]]

    righe = descrizione.strip().split("\n")
    righe_inserite = 0
    for riga in righe:
        if not riga.strip():
            continue
        if "|" in riga:
            parti = riga.split("|")
            if len(parti) == 4:
                table_data.append([
                    Paragraph(parti[0].replace("•", "").strip(), s_td),
                    Paragraph(parti[1].strip(), s_td_center),
                    Paragraph(parti[2].strip(), s_td_center),
                    Paragraph(parti[3].strip(), s_td_right)
                ])
            else:
                table_data.append([Paragraph(riga.strip(), s_td), "", "", ""])
        else:
            table_data.append([Paragraph(riga.strip(), s_td), "", "", ""])
        righe_inserite += 1

    while righe_inserite < 7:
        table_data.append(["", "", "", ""])
        righe_inserite += 1

    idx_totale = len(table_data)
    table_data.append([
        "", "",
        Paragraph("<b>TOTALE LAVORI</b>", ParagraphStyle("TotLbl", fontName="Helvetica-Bold", fontSize=9, alignment=2, textColor=GIALLO_LOGO)),
        Paragraph(f"<b>€ {importo_str} + IVA</b>", ParagraphStyle("TotCell", fontName="Helvetica-Bold", fontSize=9.5, alignment=2, textColor=colors.white))
    ])

    t_lavori = Table(table_data, colWidths=[314, 70, 70, 85])
    stili_tabella = [
        ("BACKGROUND", (0, 0), (-1, 0), BLU_LOGO),
        ("LINEBELOW", (0, 0), (-1, 0), 2, GIALLO_LOGO),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("GRID", (0, 0), (-1, idx_totale - 1), 0.5, GRIGIO_BORDO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, idx_totale - 1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, idx_totale - 1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (2, idx_totale), (3, idx_totale), BLU_LOGO),
        ("LINEABOVE", (2, idx_totale), (3, idx_totale), 2, GIALLO_LOGO),
        ("TOPPADDING", (0, idx_totale), (-1, idx_totale), 7),
        ("BOTTOMPADDING", (0, idx_totale), (-1, idx_totale), 7),
    ]

    for r_idx in range(1, idx_totale):
        if r_idx % 2 == 0:
            stili_tabella.append(("BACKGROUND", (0, r_idx), (-1, r_idx), BLU_CHIARO))
        else:
            stili_tabella.append(("BACKGROUND", (0, r_idx), (-1, r_idx), colors.white))

    t_lavori.setStyle(TableStyle(stili_tabella))
    story.append(t_lavori)
    story.append(Spacer(1, 12))

    s_nb = ParagraphStyle("NB", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=BLU_LOGO, spaceAfter=3)
    s_cond = ParagraphStyle("Cond", fontName="Helvetica", fontSize=7.5, leading=10, textColor=GRIGIO_TESTO, spaceAfter=2)
    s_art = ParagraphStyle("Art", fontName="Helvetica-Bold", fontSize=7.5, leading=10.5, textColor=BLU_LOGO, spaceBefore=3)

    testo_condizioni = [
        [Paragraph("N.B. IL PREZZO SOPRA INDICATO È COMPRENSIVO DI MATERIALI E POSA IN OPERA. IL PREVENTIVO È STATO CONSIDERATO SUL DISEGNO RICEVUTO E EVENTUALI VARIAZIONI VERRANNO CONTEGGIATE A PARTE.", s_nb)],
        [Paragraph("• Con l’approvazione del suddetto preventivo, ad inizio lavori necessita un acconto del 50% e i restanti ad avanzamento dei lavori.", s_cond)],
        [Paragraph("• Eventuali modifiche o richieste aggiuntive rispetto a quanto sopra pattuito saranno conteggiate a parte.", s_cond)],
        [Paragraph("• Il committente si impegna a garantire uno spazio idoneo, coperto e sicuro all'interno del cantiere per lo stoccaggio e la protezione dei materiali dalle intemperie.", s_cond)],
        [Paragraph("• La fornitura di acqua e luce è a carico del cliente per tutta la durata del cantiere.", s_cond)],
        [Paragraph("• Il presente preventivo è valido ed impegnativo per 30 giorni dalla data di emissione.", s_cond)],
        [Paragraph("DICHIARAZIONE DEL CLIENTE AI SENSI DELL’ART. 1341 C.C.", s_art)]
    ]

    box_cond = Table(testo_condizioni, colWidths=[539])
    box_cond.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIGIO_CHIARO),
        ("BOX", (0, 0), (-1, -1), 0.5, GRIGIO_BORDO),
        ("LINEBEFORE", (0, 0), (0, -1), 3, BLU_LOGO),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(box_cond)
    story.append(Spacer(1, 14))

    s_f_sx = ParagraphStyle("FSX", fontName="Helvetica", fontSize=7.5, leading=10.5, textColor=GRIGIO_TESTO)
    s_f_dx = ParagraphStyle("FDX", fontName="Helvetica-Bold", fontSize=8.5, leading=12, alignment=2, textColor=BLU_LOGO)

    dati_piede_sx = (
        "<font color='#1b2340'><b>CARTONGESSO &amp; COLOR GROUP S.r.l.</b></font><br/>"
        "Strada 11 Cosentini Trav. C3 N.19 - 95018 RIPOSTO (CT)<br/>"
        "Cod. Fisc. e P.IVA: 06150370879 | COD. SDI: KRRH6B9<br/><br/>"
        "<font color='#1b2340'><b>FIRMA AZIENDA:</b></font> ___________________________"
    )
    dati_piede_dx = (
        "CLIENTE (per accettazione)<br/><br/><br/>"
        "___________________________"
    )

    t_firme = Table([[Paragraph(dati_piede_sx, s_f_sx), Paragraph(dati_piede_dx, s_f_dx)]], colWidths=[300, 239])
    t_firme.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE", (0, 0), (-1, 0), 1, GRIGIO_BORDO),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_firme)
    doc.build(story)
    buffer_pdf.seek(0)
    return buffer_pdf.getvalue()

inizializza_db()

if "nuovo_desc" not in st.session_state:
    st.session_state.nuovo_desc = ""
if "nuovo_imp" not in st.session_state:
    st.session_state.nuovo_imp = 0.0

percorso_logo = trova_logo()

if percorso_logo and os.path.exists(percorso_logo):
    st.sidebar.image(percorso_logo, use_container_width=True)
else:
    st.sidebar.markdown("<h3 style='color:#f2b718;'>CARTONGESSO & COLOR GROUP</h3>", unsafe_allow_html=True)
    logo_caricato = st.sidebar.file_uploader("Carica il Logo Aziendale", type=["png", "jpg", "jpeg", "webp"])
    if logo_caricato is not None:
        ext = os.path.splitext(logo_caricato.name)[1]
        percorso_salvataggio = os.path.join(BASE_DIR, f"logo_aziendale{ext}")
        with open(percorso_salvataggio, "wb") as f:
            f.write(logo_caricato.getbuffer())
        st.rerun()

st.sidebar.markdown("<p style='color:#f2b718; font-weight:bold; font-size:16px;'>GESTIONE PREVENTIVI</p>", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navigazione",
    ["Registro Preventivi", "Nuovo Preventivo", "Modifica / Elimina", "Listino Prezzi"]
)

st.sidebar.divider()
st.sidebar.markdown("<p style='color:#f2b718; font-weight:bold;'>Filtro Periodo</p>", unsafe_allow_html=True)
tipo_periodo = st.sidebar.selectbox(
    "Tipo Filtro",
    ["Tutto lo Storico", "Mensile", "Semestrale", "Annuale"]
)

anno_sel = str(datetime.now().year)
mese_sem_sel = ""

if tipo_periodo != "Tutto lo Storico":
    anno_sel = st.sidebar.selectbox(
        "Anno",
        [str(a) for a in range(datetime.now().year, 2020, -1)]
    )
if tipo_periodo == "Mensile":
    mesi_nomi = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]
    mese_sem_sel = st.sidebar.selectbox("Mese", mesi_nomi, index=datetime.now().month - 1)
elif tipo_periodo == "Semestrale":
    mese_sem_sel = st.sidebar.selectbox("Semestre", ["1° Semestre (Gen-Giu)", "2° Semestre (Lug-Dic)"])

st.sidebar.divider()
conn = sqlite3.connect(DB_PATH)
df_all = pd.read_sql_query("SELECT * FROM preventivi ORDER BY id DESC", conn)
conn.close()

if not df_all.empty:
    excel_buffer = io.BytesIO()
    df_export = df_all.rename(columns={
        "num": "N° Preventivo", "data_doc": "Data Emessa", "cliente": "Cliente",
        "indirizzo": "Località", "telefono": "Contatto Telefono",
        "descrizione": "Descrizione Lavori", "importo": "Importo Totale €",
        "socio": "Socio Gestore", "stato": "Stato"
    }).drop(columns=["id"])

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_export[df_export["Socio Gestore"] == SOCIO_1].to_excel(writer, sheet_name=f"Preventivi {SOCIO_1}", index=False)
        df_export[df_export["Socio Gestore"] == SOCIO_2].to_excel(writer, sheet_name=f"Preventivi {SOCIO_2}", index=False)

    st.sidebar.download_button(
        label="📥 Esporta Registro Excel",
        data=excel_buffer.getvalue(),
        file_name="registro_preventivi_azienda.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

col_logo, col_titolo = st.columns([1, 3])
with col_logo:
    if percorso_logo and os.path.exists(percorso_logo):
        st.image(percorso_logo, width=260)
with col_titolo:
    st.title("Cartongesso & Color Group S.r.l.")
    st.caption("Sistema Gestionale Preventivi Soci — Bagli & Tropea")

st.divider()

if menu == "Registro Preventivi":
    st.header("Registro Preventivi Soci")

    if df_all.empty:
        st.info("Nessun preventivo presente nel database.")
    else:
        mask = df_all["data_doc"].apply(lambda d: controlla_data_filtro(d, tipo_periodo, anno_sel, mese_sem_sel))
        df_filtrato = df_all[mask].copy()

        for socio in [SOCIO_1, SOCIO_2]:
            st.subheader(f"Socio: {socio}")
            df_s = df_filtrato[df_filtrato["socio"] == socio]
            totale_s = df_s["importo"].sum() if not df_s.empty else 0.0
            st.metric("Volume Preventivi Totale del Periodo", f"€ {totale_s:,.2f}")

            if df_s.empty:
                st.write("Nessun preventivo nel periodo selezionato.")
            else:
                st.dataframe(
                    df_s[["num", "data_doc", "cliente", "indirizzo", "telefono", "descrizione", "importo", "stato"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "num": "N° Prev",
                        "data_doc": "Data",
                        "cliente": "Cliente",
                        "indirizzo": "Indirizzo/Città",
                        "telefono": "Telefono",
                        "descrizione": "Descrizione Lavori",
                        "importo": st.column_config.NumberColumn("Importo (€)", format="€ %.2f"),
                        "stato": "Stato"
                    }
                )
            st.divider()

        if not df_filtrato.empty:
            st.subheader("Genera e Scarica PDF")
            opzioni_pdf = {
                f"N° {r['num']} - {r['cliente']} (€ {r['importo']:,.2f})": r
                for _, r in df_filtrato.iterrows()
            }
            scelta_pdf = st.selectbox("Seleziona preventivo da stampare:", list(opzioni_pdf.keys()))
            riga_scelta = opzioni_pdf[scelta_pdf]
            pdf_bytes = genera_pdf_bytes(riga_scelta, percorso_logo)

            st.download_button(
                label="📄 Scarica Preventivo in PDF",
                data=pdf_bytes,
                file_name=f"Preventivo_{riga_scelta['num'].replace('/', '_')}.pdf",
                mime="application/pdf",
                type="primary"
            )
elif menu == "Nuovo Preventivo":
    st.header("Compilazione Nuovo Preventivo")

    conn = sqlite3.connect(DB_PATH)
    voci_listino = conn.execute("SELECT codice, descrizione, prezzo_unitario, unita_misura FROM listino").fetchall()
    conn.close()

    with st.expander("➕ Inserisci voce dal Listino Prezzi", expanded=True):
        if voci_listino:
            dict_listino = {f"{v[0]} - {v[1][:55]}... (€ {v[2]:.2f}/{v[3]})": v for v in voci_listino}
            c1, c2, c3 = st.columns([4, 1, 1])
            voce_sel = c1.selectbox("Voce di listino", list(dict_listino.keys()))
            qta = c2.number_input("Quantità (MQ/ML)", min_value=0.0, step=1.0, value=0.0)
            if c3.button("Aggiungi riga", use_container_width=True):
                if qta > 0:
                    cod, desc_lunga, prezzo, um = dict_listino[voce_sel]
                    tot_riga = qta * prezzo
                    riga_testo = f"{desc_lunga} | {qta} {um} | € {prezzo:,.2f} | € {tot_riga:,.2f}\n"
                    st.session_state.nuovo_desc += riga_testo
                    st.session_state.nuovo_imp += tot_riga
                    st.rerun()
        else:
            st.warning("Nessuna voce presente nel listino.")

    with st.form("form_nuovo_prev"):
        col1, col2, col3, col4 = st.columns(4)
        num_prev = col1.text_input("N° Preventivo", value=genera_numero_progressivo())
        data_prev = col2.date_input("Data", value=datetime.now())
        socio_prev = col3.selectbox("Socio Gestore", [SOCIO_1, SOCIO_2])
        stato_prev = col4.selectbox("Stato", ["In Attesa", "Approvato", "Rifiutato"])

        c_ana1, c_ana2, c_ana3 = st.columns([2, 2, 1])
        cliente = c_ana1.text_input("Cliente *")
        indirizzo = c_ana2.text_input("Indirizzo / Città")
        telefono = c_ana3.text_input("Telefono")

        descrizione = st.text_area(
            "Dettagli Lavorazioni (formato tabella PDF: Descrizione | Misure | Prezzo Unit. | Totale)",
            value=st.session_state.nuovo_desc,
            height=180
        )
        importo = st.number_input(
            "Importo Totale (€)",
            min_value=0.0,
            step=10.0,
            value=float(st.session_state.nuovo_imp)
        )

        salva = st.form_submit_button("💾 Salva Preventivo", type="primary")
        if salva:
            if not cliente.strip():
                st.error("Inserisci il nome del cliente.")
            else:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT INTO preventivi (num, data_doc, cliente, indirizzo, telefono, descrizione, importo, socio, stato) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (num_prev, data_prev.strftime("%Y-%m-%d"), cliente, indirizzo, telefono, descrizione, importo, socio_prev, stato_prev)
                )
                conn.commit()
                conn.close()
                st.session_state.nuovo_desc = ""
                st.session_state.nuovo_imp = 0.0
                st.success("Preventivo salvato correttamente!")

elif menu == "Modifica / Elimina":
    st.header("Modifica o Elimina Preventivo")

    if df_all.empty:
        st.info("Nessun preventivo da modificare.")
    else:
        opzioni = {
            f"ID {r['id']} | N° {r['num']} - {r['cliente']} ({r['socio']})": r
            for _, r in df_all.iterrows()
        }
        scelta = st.selectbox("Seleziona preventivo:", list(opzioni.keys()))
        record = opzioni[scelta]

        with st.form("form_modifica"):
            c1, c2, c3, c4 = st.columns(4)
            m_num = c1.text_input("N° Preventivo", value=record["num"])
            m_data = c2.text_input("Data (AAAA-MM-GG)", value=record["data_doc"])
            m_socio = c3.selectbox("Socio", [SOCIO_1, SOCIO_2], index=0 if record["socio"] == SOCIO_1 else 1)
            stati = ["In Attesa", "Approvato", "Rifiutato"]
            idx_stato = stati.index(record["stato"]) if record["stato"] in stati else 0
            m_stato = c4.selectbox("Stato", stati, index=idx_stato)

            c_a1, c_a2, c_a3 = st.columns([2, 2, 1])
            m_cli = c_a1.text_input("Cliente", value=record["cliente"])
            m_ind = c_a2.text_input("Indirizzo", value=record["indirizzo"] or "")
            m_tel = c_a3.text_input("Telefono", value=record["telefono"] or "")

            m_desc = st.text_area("Descrizione Lavori", value=record["descrizione"] or "", height=160)
            m_imp = st.number_input("Importo (€)", min_value=0.0, value=float(record["importo"] or 0.0))

            col_b1, col_b2 = st.columns(2)
            aggiorna = col_b1.form_submit_button("💾 Salva Modifiche", type="primary")
            elimina = col_b2.form_submit_button("🗑️ Elimina Preventivo")

            if aggiorna:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "UPDATE preventivi SET num=?, data_doc=?, cliente=?, indirizzo=?, telefono=?, descrizione=?, importo=?, socio=?, stato=? WHERE id=?",
                    (m_num, m_data, m_cli, m_ind, m_tel, m_desc, m_imp, m_socio, m_stato, int(record["id"]))
                )
                conn.commit()
                conn.close()
                st.success("Preventivo aggiornato!")
                st.rerun()

            if elimina:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("DELETE FROM preventivi WHERE id=?", (int(record["id"]),))
                conn.commit()
                conn.close()
                st.warning("Preventivo eliminato.")
                st.rerun()

elif menu == "Listino Prezzi":
    st.header("Gestione Listino Prezzi")

    with st.form("form_listino"):
        c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
        cod = c1.text_input("Codice (es. CART05)")
        desc = c2.text_input("Descrizione Lavoro/Materiale")
        prezzo = c3.number_input("Prezzo €", min_value=0.0, step=1.0)
        um = c4.text_input("U.M. (mq, ml, cad)")

        if st.form_submit_button("Salva / Aggiorna Voce", type="primary"):
            if cod and desc:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT OR REPLACE INTO listino (codice, descrizione, prezzo_unitario, unita_misura) VALUES (?, ?, ?, ?)",
                    (cod.strip().upper(), desc.strip(), prezzo, um.strip())
                )
                conn.commit()
                conn.close()
                st.success("Voce salvata nel listino!")
                st.rerun()
            else:
                st.error("Inserisci almeno Codice e Descrizione.")

    conn = sqlite3.connect(DB_PATH)
    df_listino = pd.read_sql_query("SELECT codice, descrizione, prezzo_unitario, unita_misura FROM listino", conn)
    conn.close()
    st.dataframe(df_listino, use_container_width=True, hide_index=True)
