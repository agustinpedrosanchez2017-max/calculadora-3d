import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

st.set_page_config(page_title="Gestión 3D Tucumán", page_icon="📦", layout="wide")

# --- FUNCIONES DE PERSISTENCIA (CSV para Stock) ---
DB_FILE = "inventario.csv"

def cargar_datos():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        if "Precio ($)" not in df.columns:
            df["Precio ($)"] = 35000.0
        return df
    else:
        return pd.DataFrame(columns=["Marca", "Color", "Tipo", "Peso Restante (g)", "Precio ($)"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

# --- INICIALIZAR ESTADOS DE SESIÓN ---
if 'stock' not in st.session_state:
    st.session_state.stock = cargar_datos()

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FUNCIÓN PARA GENERAR EL PDF MULTI-ARTÍCULO ---
def crear_pdf_multi(cliente, carrito_items, mostrar_detalles, aplicar_iva):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(190, 15, "PRESUPUESTO DE IMPRESIÓN 3D", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(100, 10, f"Cliente: {cliente}")
    pdf.cell(90, 10, f"Fecha: 29/04/2026", ln=True, align='R') 
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    # Cabecera de la tabla
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "Artículo / Detalle", border=1, align='C')
    pdf.cell(50, 10, "Precio", border=1, align='C', ln=True)
    
    pdf.set_font("Arial", '', 11)
    
    subtotal_general = 0
    
    for item in carrito_items:
        nombre_pieza = item['pieza']
        precio_item = item['total_item']
        subtotal_general += precio_item
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(140, 8, f" {nombre_pieza}", border='LTR')
        pdf.cell(50, 8, f" ${precio_item:,.2f}", border='LTR', ln=True, align='R')
        
        if mostrar_detalles:
            pdf.set_font("Arial", 'I', 9)
            pdf.set_text_color(80, 80, 80)
            detalles_str = f"   - Material ({item['gramos']}g): ${item['costo_mat']:,.2f} | Impresora ({item['horas']}h): ${item['costo_maq']:,.2f} | Margen: ${item['ganancia']:,.2f}"
            pdf.cell(140, 6, detalles_str, border='LBR')
            pdf.cell(50, 6, "", border='LBR', ln=True)
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.cell(140, 2, "", border='LBR')
            pdf.cell(50, 2, "", border='LBR', ln=True)

    pdf.ln(5)
    total_final_pdf = subtotal_general
    
    pdf.set_font("Arial", 'B', 12)
    if aplicar_iva:
        iva_monto = subtotal_general * 0.21
        total_final_pdf += iva_monto
        pdf.cell(140, 10, " Subtotal", border=1, align='R')
        pdf.cell(50, 10, f" ${subtotal_general:,.2f}", border=1, ln=True, align='R')
        pdf.cell(140, 10, " IVA (21%)", border=1, align='R')
        pdf.cell(50, 10, f" ${iva_monto:,.2f}", border=1, ln=True, align='R')

    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(140, 12, " PRECIO TOTAL FINAL", border=1, fill=True, align='R')
    pdf.cell(50, 12, f" ${total_final_pdf:,.2f}", border=1, ln=True, align='R', fill=True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ ---
tab1, tab2 = st.tabs(["🧮 Crear Presupuesto", "📦 Inventario de Filamentos"])

with tab1:
    st.header("Armado de Presupuesto")
    
    col_cab1, col_cab2 = st.columns(2)
    with col_cab1: nombre_cliente = st.text_input("Nombre del Cliente", "Consumidor Final")
    with col_cab2: usar_iva = st.checkbox("Incluir IVA (21%) al total final", True)
    
    st.divider()
    st.subheader("➕ Agregar Pieza al Presupuesto")
    
    with st.container(border=True):
        if not st.session_state.stock.empty:
            opciones_filamento = []
            for index, row in st.session_state.stock.iterrows():
                texto_opcion = f"{row['Marca']} {row['Color']} ({row['Tipo']}) - ${row['Precio ($)']}"
                opciones_filamento.append(texto_opcion)
            
            filamento_elegido = st.selectbox("Seleccionar Filamento del Inventario", opciones_filamento)
            indice_elegido = opciones_filamento.index(filamento_elegido)
            precio_bobina_actual = st.session_state.stock.iloc[indice_elegido]['Precio ($)']
        else:
            st.warning("⚠️ Tu inventario está vacío. Ve a la pestaña 'Control de Stock'.")
            precio_bobina_actual = st.number_input("Precio Bobina Manual ($)", 35000)

        c1, c2, c3 = st.columns(3)
        with c1: pieza_actual = st.text_input("Nombre de la Pieza (Ej: Auto 3D)", "Pieza 1")
        with c2: gramos_actual = st.number_input("Gramos a usar", 100)
        with c3: horas_actual = st.number_input("Horas de impresión", 5.0)
        
        c4, c5 = st.columns(2)
        with c4: c_maq_hora = st.number_input("Costo hr máquina ($)", 500)
        with c5: margen_actual = st.slider("Margen %", 0, 200, 50)
        
        if st.button("🛒 Agregar Pieza al Carrito"):
            c_mat = (precio_bobina_actual / 1000) * gramos_actual
            c_maq = horas_actual * c_maq_hora
            sub_item = c_mat + c_maq
            ganancia_item = sub_item * (margen_actual / 100)
            total_item = sub_item + ganancia_item
            
            nuevo_item = {
                "pieza": pieza_actual,
                "gramos": gramos_actual,
                "horas": horas_actual,
                "costo_mat": c_mat,
                "costo_maq": c_maq,
                "ganancia": ganancia_item,
                "total_item": total_item
            }
            st.session_state.carrito.append(nuevo_item)
            st.success(f"✅ {pieza_actual} agregado al presupuesto.")
            st.rerun()

    if len(st.session_state.carrito) > 0:
        st.divider()
        st.subheader("🛒 Artículos en el Presupuesto Actual")
        
        df_carrito = pd.DataFrame(st.session_state.carrito)
        df_mostrar = df_carrito[['pieza', 'gramos', 'horas', 'total_item']].copy()
        df_mostrar['total_item'] = df_mostrar['total_item'].apply(lambda x: f"${x:,.2f}")
        st.table(df_mostrar)
        
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            if st.button("🗑️ Vaciar Presupuesto"):
                st.session_state.carrito = []
                st.rerun()
                
        with col_btn2:
            st.write("### Opciones de Exportación")
            mostrar_detalles_pdf = st.checkbox("Mostrar Detalles Técnicos en PDF", value=False)
            
            if st.button("📄 Generar PDF del Presupuesto"):
                pdf_bytes = crear_pdf_multi(nombre_cliente, st.session_state.carrito, mostrar_detalles_pdf, usar_iva)
                st.download_button("📥 Descargar Archivo PDF", pdf_bytes, f"Presupuesto_{nombre_cliente}.pdf", "application/pdf")

with tab2:
    st.header("Control de Stock")
    
    # Formulario rápido para añadir
    with st.expander("➕ Registrar Nueva Bobina Rápido"):
        c1, c2, c3 = st.columns(3)
        with c1: marca = st.text_input("Marca")
        with c2: color = st.text_input("Color")
        with c3: tipo = st.selectbox("Tipo", ["PLA", "PETG", "ABS", "Flex", "Resina"])
        
        c4, c5 = st.columns(2)
        with c4: peso = st.number_input("Peso Inicial (g)", 1000)
        with c5: precio_bobina = st.number_input("Precio de la Bobina ($)", 35000)
        
        if st.button("Añadir al Stock"):
            nueva_fila = pd.DataFrame([[marca, color, tipo, peso, precio_bobina]], columns=st.session_state.stock.columns)
            st.session_state.stock = pd.concat([st.session_state.stock, nueva_fila], ignore_index=True)
            guardar_datos(st.session_state.stock)
            st.success("Bobina agregada.")
            st.rerun()

    st.divider()
    st.subheader("📝 Editar Inventario (Interactivo)")
    st.info("💡 Haz doble clic en cualquier celda para cambiar su valor. Selecciona una fila haciendo clic en el número de la izquierda y presiona 'Suprimir' en tu teclado para borrarla.")
    
    # LA MAGIA: Tabla editable
    inventario_editado = st.data_editor(
        st.session_state.stock, 
        use_container_width=True, 
        num_rows="dynamic" # Esto permite agregar y borrar filas directamente desde la tabla
    )
    
    # Botón para guardar los cambios que hagas en la tabla interactiva
    if st.button("💾 Guardar Cambios en el Archivo"):
        st.session_state.stock = inventario_editado
        guardar_datos(st.session_state.stock)
        st.success("¡Tus modificaciones se guardaron en el archivo de inventario!")