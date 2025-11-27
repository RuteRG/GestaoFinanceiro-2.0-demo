import streamlit as st
import pandas as pd
import uuid
import os
import hashlib
from datetime import date, datetime
import matplotlib.pyplot as plt
from reportlab.platypus import Image
from reportlab.lib.units import cm

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO


# -----------------------------
# Configuração e título
# -----------------------------
st.set_page_config(page_title="Controle Financeiro", layout="centered")

st.markdown("""
<style>
    .header-container {
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .header-title {
        font-size: 32px;
        font-weight: 700;
        margin: 0;
        padding: 0;
    }
    .header-divider {
        border-bottom: 2px solid #ddd;
        margin-top: 10px;
        margin-bottom: 25px;
    }
    .header-title h1 {
        font-size: 32px;
        font-weight: 700;
        margin: 0;
        padding-left: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Colunas para logo + título
col_logo, col_title = st.columns([1, 5])

with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)

with col_title:
    st.markdown(
        "<div class='header-title'><h2>💸 Controle Financeiro</h2></div>",
        unsafe_allow_html=True
    )

st.markdown("<div class='header-divider'></div>", unsafe_allow_html=True)

# -----------------------------
# Funções auxiliares
# -----------------------------
def gerar_nome_arquivo(email):
    hash_email = hashlib.md5(email.strip().lower().encode()).hexdigest()
    return f"gastos_{hash_email}.csv"

def to_iso_date(d):
    if isinstance(d, (pd.Timestamp, datetime)):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    try:
        return pd.to_datetime(d, dayfirst=True).date().isoformat()
    except Exception:
        return None

def ensure_schema(df):
    expected = ["Id", "Data", "Tipo", "Descrição", "Valor", "Forma de pagamento", "Categoria"]
    for c in expected:
        if c not in df.columns:
            df[c] = pd.Series(dtype="object")
    return df[expected]

def gerar_pdf(df, ano, mes):
    from reportlab.lib.utils import ImageReader
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ==========================
    # DESENHAR LOGO NO PDF
    # ==========================
    logo_path = None
    possible = [
        "logo.png",
        os.path.join(os.getcwd(), "logo.png"),
        os.path.expanduser("~/OneDrive/logo.png"),
    ]
    
    for p in possible:
        if os.path.exists(p):
            logo_path = p
            break

    if logo_path:
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            target_w = 90
            target_h = (ih / iw) * target_w
            x = (width - target_w) / 2
            y = height - (target_h + 20)
            c.drawImage(img, x, y, width=target_w, height=target_h, mask='auto')
        except Exception as e:
            print("Erro ao inserir logo no PDF:", e)
        title_y = y - 25
    else:
        title_y = height - 70

    # ==========================
    # TÍTULO
    # ==========================
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.30, 0.40, 0.95)
    c.drawCentredString(width/2, title_y, "Relatório Financeiro")

    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(width/2, title_y - 20, f"Período: {mes:02d}/{ano}")

    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawCentredString(
        width/2,
        title_y - 35,
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

    # ==========================
    # PREPARAR DADOS
    # ==========================
    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Data Formatada"] = df["Data"].dt.strftime("%d/%m/%Y")
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)

    # ==========================
    # RESUMO FINANCEIRO
    # ==========================
    resumo_y = title_y - 65
    
    total_receitas = df[df["Tipo"] == "Receita"]["Valor"].sum()
    despesas_sem_cartao = df[(df["Tipo"] == "Despesa") & (df["Forma de pagamento"] != "Cartão")]["Valor"].sum()
    despesas_cartao = df[(df["Tipo"] == "Despesa") & (df["Forma de pagamento"] == "Cartão")]["Valor"].sum()
    saldo = total_receitas - despesas_sem_cartao

    # Box do resumo
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.roundRect(70, resumo_y - 95, width - 140, 105, 8, fill=1, stroke=1)

    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(width/2, resumo_y - 15, "Resumo Financeiro:")

    # Total de Receitas (verde)
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0, 0.6, 0)
    c.drawString(90, resumo_y - 35, f"Total de Receitas: R$ {total_receitas:.2f}")

    # Despesas sem cartão (vermelho)
    c.setFillColorRGB(0.8, 0, 0)
    c.drawString(90, resumo_y - 52, f"Total de Despesas (sem cartão): R$ {despesas_sem_cartao:.2f}")

    # Saldo (preto)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(90, resumo_y - 69, f"Saldo: R$ {saldo:.2f}")

    # Gastos no cartão (laranja) - DENTRO DA CAIXA
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.9, 0.5, 0)
    c.drawString(90, resumo_y - 86, f"Gastos no Cartão (não descontados): R$ {despesas_cartao:.2f}")

    # ==========================
    # TABELA
    # ==========================
    y = resumo_y - 130
    c.setFillColorRGB(0.40, 0.42, 0.95)
    c.rect(40, y, width - 80, 22, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(1, 1, 1)
    c.drawString(50, y + 6, "Data")
    c.drawString(110, y + 6, "Tipo")
    c.drawString(165, y + 6, "Descrição")
    c.drawString(320, y + 6, "Categoria")
    c.drawString(420, y + 6, "Forma")
    c.drawString(500, y + 6, "Valor")

    y -= 26
    row_height = 20

    for i, row in df.iterrows():
        if y < 60:
            c.showPage()
            y = height - 100

            c.setFillColorRGB(0.40, 0.42, 0.95)
            c.rect(40, y, width - 80, 22, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(1, 1, 1)
            c.drawString(50, y + 6, "Data")
            c.drawString(110, y + 6, "Tipo")
            c.drawString(165, y + 6, "Descrição")
            c.drawString(320, y + 6, "Categoria")
            c.drawString(420, y + 6, "Forma")
            c.drawString(500, y + 6, "Valor")
            y -= 26

        if i % 2 == 0:
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(40, y - 2, width - 80, row_height, fill=1, stroke=0)

        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0, 0, 0)

        c.drawString(50, y, str(row["Data Formatada"]))
        c.drawString(110, y, str(row["Tipo"])[:8])
        c.drawString(165, y, str(row["Descrição"])[:25])
        c.drawString(320, y, str(row["Categoria"])[:15])
        c.drawString(420, y, str(row["Forma de pagamento"])[:12])

        # Cor do valor baseado no tipo
        if row["Tipo"] == "Receita":
            c.setFillColorRGB(0, 0.55, 0)
        else:
            c.setFillColorRGB(0.9, 0, 0)

        c.drawRightString(530, y, f"R$ {row['Valor']:.2f}")

        y -= row_height

    c.save()
    buffer.seek(0)
    return buffer


# -----------------------------
# Entrada de e-mail
# -----------------------------
email_usuario = st.text_input("📧 Digite seu e-mail para acessar seus dados")
if not email_usuario:
    st.warning("Por favor, digite seu e-mail para continuar.")
    st.stop()

# Caminhos de arquivos
BASE_DIR = os.path.expanduser("~/OneDrive/ControleFinanceiro")
os.makedirs(BASE_DIR, exist_ok=True)
ARQUIVO_GASTOS = os.path.join(BASE_DIR, gerar_nome_arquivo(email_usuario))
ARQUIVO_SALDOS = os.path.join(BASE_DIR, "saldos.csv")

# -----------------------------
# Estado da sessão
# -----------------------------
if "gastos" not in st.session_state:
    if os.path.exists(ARQUIVO_GASTOS):
        try:
            df_gastos = pd.read_csv(ARQUIVO_GASTOS, sep=";")
        except Exception:
            df_gastos = pd.DataFrame(columns=["Id","Data","Tipo","Descrição","Valor","Forma de pagamento","Categoria"])
    else:
        df_gastos = pd.DataFrame(columns=["Id","Data","Tipo","Descrição","Valor","Forma de pagamento","Categoria"])

    if "Id" not in df_gastos.columns or df_gastos["Id"].duplicated().any():
        df_gastos["Id"] = [str(uuid.uuid4()) for _ in range(len(df_gastos))]

    df_gastos = ensure_schema(df_gastos)
    st.session_state.gastos = df_gastos.to_dict(orient="records")

# Saldos
if os.path.exists(ARQUIVO_SALDOS):
    try:
        df_saldos = pd.read_csv(ARQUIVO_SALDOS)
    except Exception:
        df_saldos = pd.DataFrame(columns=["Ano","Mês","Saldo"])
else:
    df_saldos = pd.DataFrame(columns=["Ano","Mês","Saldo"])

# -----------------------------
# DataFrame atualizado
# -----------------------------
df = pd.DataFrame(st.session_state.gastos)
df = ensure_schema(df)
df["Data"] = pd.to_datetime(df["Data"], format="%Y-%m-%d", errors="coerce")
df = df.dropna(subset=["Data"])
df["Data Formatada"] = df["Data"].dt.strftime("%d/%m/%Y")
df["Ano"] = df["Data"].dt.year.astype(int)
df["Mês"] = df["Data"].dt.month.astype(int)

if not df.empty:
    anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
    meses_disponiveis = sorted(df["Mês"].unique())
else:
    anos_disponiveis = [datetime.now().year]
    meses_disponiveis = [datetime.now().month]

# -----------------------------
# Expanders
# -----------------------------

# Controle de Transações
with st.expander("💰 Adicionar Despesa", expanded=True):
    with st.form("form_transacao", clear_on_submit=True):
        col1, col2 = st.columns(2)
        data_sel = col1.date_input("📅 Data", value=date.today())
        tipo = col2.selectbox("📊 Tipo", ["Despesa"])
        
        descricao = st.text_input("📝 Descrição")
        valor = st.number_input("💵 Valor (R$)", min_value=0.0, step=0.01)
        
        col3, col4 = st.columns(2)
        forma = col3.selectbox("💳 Forma de pagamento", ["Cartão", "Pix", "Dinheiro", "Boleto", "Transferência"])
        
        if tipo == "Receita":
            categoria = col4.selectbox("📂 Categoria", ["Salário", "Saldo Inicial", "Freelance", "Investimentos", "Venda", "Outros"])
        else:
            categoria = col4.selectbox("📂 Categoria", ["Alimentação", "Transporte", "Moradia", "Lazer", "Saúde", "Internet", "Streaming", "Cartão de Crédito", "Outros"])
        
        enviar = st.form_submit_button("➕ Adicionar")
        if enviar:
            novo = {
                "Id": str(uuid.uuid4()),
                "Data": to_iso_date(data_sel),
                "Tipo": tipo,
                "Descrição": descricao,
                "Valor": float(valor),
                "Forma de pagamento": forma,
                "Categoria": categoria
            }
            st.session_state.gastos.append(novo)
            pd.DataFrame(st.session_state.gastos).to_csv(ARQUIVO_GASTOS, sep=";", index=False)
            st.success(f"✅ {tipo} adicionada com sucesso!")
            st.rerun()

# Filtro por mês/ano
with st.expander("📅 Filtro por Mês e Ano", expanded=False):
    colf1, colf2 = st.columns(2)
    ano_selecionado = colf1.selectbox("Ano", anos_disponiveis)
    mes_selecionado = colf2.selectbox("Mês", meses_disponiveis)

df_filtrado = df[(df["Ano"] == int(ano_selecionado)) & (df["Mês"] == int(mes_selecionado))].copy()

# Saldo do mês como receita
with st.expander("💼 Adicionar Saldo do Mês como Receita", expanded=False):
    # Verifica se já existe um saldo registrado neste mês
    df_temp = pd.DataFrame(st.session_state.gastos)
    if not df_temp.empty:
        df_temp["Data"] = pd.to_datetime(df_temp["Data"], format="%Y-%m-%d", errors="coerce")
        df_temp = df_temp.dropna(subset=["Data"])
        df_temp["Ano"] = df_temp["Data"].dt.year.astype(int)
        df_temp["Mês"] = df_temp["Data"].dt.month.astype(int)
        
        saldo_existente = df_temp[
            (df_temp["Ano"] == int(ano_selecionado)) & 
            (df_temp["Mês"] == int(mes_selecionado)) & 
            (df_temp["Descrição"] == "Saldo inicial do mês")
        ]
        
        if not saldo_existente.empty:
            valor_atual = float(saldo_existente.iloc[0]["Valor"])
            st.info(f"✅ Saldo do mês já registrado: R$ {valor_atual:.2f}")
            
            if st.button("🗑️ Remover saldo do mês"):
                df_all = pd.DataFrame(st.session_state.gastos)
                df_all = df_all[df_all["Id"] != saldo_existente.iloc[0]["Id"]]
                st.session_state.gastos = df_all.to_dict(orient="records")
                df_all.to_csv(ARQUIVO_GASTOS, sep=";", index=False)
                st.success("Saldo removido!")
                st.rerun()
    
    novo_saldo_str = st.text_input("Valor do saldo inicial (R$)", value="0,00")
    try:
        novo_saldo = float(novo_saldo_str.replace(" ", "").replace(".", "").replace(",", "."))
        if st.button("💾 Salvar saldo do mês"):
            # Remove saldo anterior se existir
            df_all = pd.DataFrame(st.session_state.gastos)
            df_all["Data"] = pd.to_datetime(df_all["Data"], format="%Y-%m-%d", errors="coerce")
            df_all = df_all.dropna(subset=["Data"])
            df_all["Ano"] = df_all["Data"].dt.year.astype(int)
            df_all["Mês"] = df_all["Data"].dt.month.astype(int)
            
            df_all = df_all[~(
                (df_all["Ano"] == int(ano_selecionado)) & 
                (df_all["Mês"] == int(mes_selecionado)) & 
                (df_all["Descrição"] == "Saldo inicial do mês")
            )]
            
            # Adiciona novo saldo como receita no primeiro dia do mês
            from datetime import datetime
            primeiro_dia = datetime(int(ano_selecionado), int(mes_selecionado), 1)
            
            novo_registro = {
                "Id": str(uuid.uuid4()),
                "Data": primeiro_dia.date().isoformat(),
                "Tipo": "Receita",
                "Descrição": "Saldo inicial do mês",
                "Valor": float(novo_saldo),
                "Forma de pagamento": "Saldo",
                "Categoria": "Saldo Inicial"
            }
            
            st.session_state.gastos = df_all.to_dict(orient="records")
            st.session_state.gastos.append(novo_registro)
            pd.DataFrame(st.session_state.gastos).to_csv(ARQUIVO_GASTOS, sep=";", index=False)
            st.success("✅ Saldo do mês adicionado como receita!")
            st.rerun()
    except ValueError:
        st.warning("Digite um valor válido para o saldo")

# Resumo Financeiro
with st.expander("📊 Resumo Financeiro do Mês", expanded=True):
    if not df_filtrado.empty:
        df_filtrado["Valor"] = pd.to_numeric(df_filtrado["Valor"], errors="coerce")
        
        total_receitas = df_filtrado[df_filtrado["Tipo"] == "Receita"]["Valor"].sum()
        despesas_sem_cartao = df_filtrado[(df_filtrado["Tipo"] == "Despesa") & (df_filtrado["Forma de pagamento"] != "Cartão")]["Valor"].sum()
        despesas_cartao = df_filtrado[(df_filtrado["Tipo"] == "Despesa") & (df_filtrado["Forma de pagamento"] == "Cartão")]["Valor"].sum()
        saldo = total_receitas - despesas_sem_cartao
        
        st.markdown(f"""
        <div style='background-color: #e8e8e8; padding: 20px; margin: 20px 0; border-radius: 10px; border: 2px solid #ccc;'>
            <h3 style='text-align: center; margin-bottom: 15px; color: #333;'>Resumo Financeiro:</h3>
            <p style='color: #008000; font-size: 17px; font-weight: 600;'>Total de Receitas: R$ {total_receitas:.2f}</p>
            <p style='color: #cc0000; font-size: 17px; font-weight: 600;'>Total de Despesas (sem cartão): R$ {despesas_sem_cartao:.2f}</p>
            <p style='font-weight: bold; font-size: 19px; color: #1a1a1a; margin-top: 10px;'>Saldo: R$ {saldo:.2f}</p>
            <hr style='margin: 15px 0; border: none; border-top: 1px dashed #999;'>
            <p style='color: #ff8c00; font-size: 15px; font-weight: 600; background-color: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px;'>
                💳 Gastos no Cartão (não descontados): R$ {despesas_cartao:.2f}
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Sem dados para o período selecionado")

# Transações Filtradas
with st.expander("📋 Transações do Mês", expanded=False):
    if not df_filtrado.empty:
        h1, h2, h3, h4, h5, h6, h7 = st.columns([1.5, 1.5, 3, 2, 2, 2, 1])
        h1.write("📅 Data")
        h2.write("📊 Tipo")
        h3.write("📝 Descrição")
        h4.write("💵 Valor")
        h5.write("💳 Forma")
        h6.write("📂 Categoria")
        h7.write("Excluir")

        for i, row in df_filtrado.iterrows():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 1.5, 3, 2, 2, 2, 1])
            c1.write(row["Data Formatada"])
            
            if row["Tipo"] == "Receita":
                c2.markdown(f"<span style='color: green;'>✅ {row['Tipo']}</span>", unsafe_allow_html=True)
                c4.markdown(f"<span style='color: green;'>R$ {float(row['Valor']):.2f}</span>", unsafe_allow_html=True)
            else:
                c2.markdown(f"<span style='color: red;'>❌ {row['Tipo']}</span>", unsafe_allow_html=True)
                c4.markdown(f"<span style='color: red;'>R$ {float(row['Valor']):.2f}</span>", unsafe_allow_html=True)
            
            c3.write(row["Descrição"])
            c5.write(row["Forma de pagamento"])
            c6.write(row["Categoria"])
            
            if c7.button("🗑️", key=f"del_{row['Id']}_{i}"):
                df_all = pd.DataFrame(st.session_state.gastos)
                df_all = df_all[df_all["Id"] != row["Id"]]
                st.session_state.gastos = df_all.to_dict(orient="records")
                df_all.to_csv(ARQUIVO_GASTOS, sep=";", index=False)
                st.success("Registro excluído!")
                st.rerun()

        # Download PDF
        pdf_buffer = gerar_pdf(df_filtrado, ano_selecionado, mes_selecionado)
        st.download_button(
            label="📄 Baixar relatório em PDF",
            data=pdf_buffer,
            file_name=f"relatorio_financeiro_{ano_selecionado}_{mes_selecionado}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Nenhuma transação no período selecionado.")

# Gráfico por categoria
with st.expander(f"📊 Análise por Categoria - {mes_selecionado:02d}/{ano_selecionado}", expanded=False):
    if not df_filtrado.empty:
        df_filtrado["Valor"] = pd.to_numeric(df_filtrado["Valor"], errors="coerce")
        
        tab1, tab2 = st.tabs(["💸 Despesas", "💰 Receitas"])
        
        with tab1:
            despesas = df_filtrado[df_filtrado["Tipo"] == "Despesa"]
            if not despesas.empty:
                totais_despesa = despesas.groupby("Categoria")["Valor"].sum().sort_values(ascending=False)
                fig, ax = plt.subplots()
                ax.bar(totais_despesa.index, totais_despesa.values, color="#ff6b6b")
                ax.set_ylabel("Valor (R$)")
                ax.set_xlabel("Categoria")
                ax.set_title("Despesas por Categoria")
                plt.xticks(rotation=20)
                st.pyplot(fig)
            else:
                st.info("Sem despesas no período")
        
        with tab2:
            receitas = df_filtrado[df_filtrado["Tipo"] == "Receita"]
            if not receitas.empty:
                totais_receita = receitas.groupby("Categoria")["Valor"].sum().sort_values(ascending=False)
                fig, ax = plt.subplots()
                ax.bar(totais_receita.index, totais_receita.values, color="#51cf66")
                ax.set_ylabel("Valor (R$)")
                ax.set_xlabel("Categoria")
                ax.set_title("Receitas por Categoria")
                plt.xticks(rotation=20)
                st.pyplot(fig)
            else:
                st.info("Sem receitas no período")
    else:
        st.info("Sem dados para análise.")
