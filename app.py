"""
Interface web Streamlit — Traitement Leads Meta
Déployable gratuitement sur https://streamlit.io/cloud
"""

import json
import pandas as pd
import zipfile
import io
import streamlit as st
from datetime import datetime
from traitement_core import traiter_fichiers, valider_config, df_to_csv_bytes

# ─────────────────────────────────────────────
# CONFIG PAGE
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Traitement Leads Meta",
    page_icon="📊",
    layout="centered"
)

# ─────────────────────────────────────────────
# STYLE
# ─────────────────────────────────────────────

st.markdown("""
<style>
    .main { background-color: #1e1e2e; }
    .stApp { background-color: #1e1e2e; color: #cdd6f4; }
    h1, h2, h3 { color: #89b4fa; }
    .stButton > button {
        background-color: #89b4fa;
        color: #1e1e2e;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 2rem;
    }
    .stButton > button:hover { background-color: #74c7ec; }
    .stDownloadButton > button {
        background-color: #a6e3a1;
        color: #1e1e2e;
        font-weight: bold;
        border-radius: 8px;
        border: none;
    }
    .stTextArea textarea { background-color: #181825; color: #cdd6f4; }
    .stFileUploader { background-color: #181825; }
    div[data-testid="stMetricValue"] { color: #a6e3a1; font-size: 2rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TITRE
# ─────────────────────────────────────────────

st.title("📊 Traitement Leads Meta")
st.markdown("**Facebook Ads — Classement automatique par code postal**")
st.divider()

# Initialisation session_state
if "resultats" not in st.session_state:
    st.session_state.resultats = None
if "doublons_df" not in st.session_state:
    st.session_state.doublons_df = None
if "global_df" not in st.session_state:
    st.session_state.global_df = None
if "logs" not in st.session_state:
    st.session_state.logs = []
if "timestamp" not in st.session_state:
    st.session_state.timestamp = None

# ─────────────────────────────────────────────
# ÉTAPE 1 — Configuration clients
# ─────────────────────────────────────────────

st.header("① Configuration des clients")

config_defaut = json.dumps({
  "clients": [
    {"nom": "SEE",        "prefixes": ["46","47","12","81","82"]},
    {"nom": "YC",         "prefixes": ["08","10","51","52","25","39","70","90","21","58","71","89"]},
    {"nom": "JND",        "prefixes": ["03","63","42","43"]},
    {"nom": "BE_LEADS",   "prefixes": ["27","76"]},
    {"nom": "SD",         "prefixes": ["14","27","50","61","01","38"]},
    {"nom": "PHOTO_CLIM", "prefixes": ["27","76","89","58","72","53","18","41","60","80","02","28","45"]}
  ]
}, indent=2, ensure_ascii=False)

config_json = st.text_area(
    "Colle ou modifie ta configuration JSON :",
    value=config_defaut,
    height=200,
    help="Ajoute ou retire des clients sans toucher au reste."
)

clients = None
try:
    clients = valider_config(config_json)
    st.success(f"✅ {len(clients)} client(s) configuré(s) : {', '.join(c['nom'] for c in clients)}")
except Exception as e:
    st.error(f"❌ Erreur de configuration : {e}")

st.divider()

# ─────────────────────────────────────────────
# ÉTAPE 2 — Upload des fichiers
# ─────────────────────────────────────────────

st.header("② Charger les fichiers CSV Meta")

fichiers_uploades = st.file_uploader(
    "Glisse tes fichiers CSV ici (plusieurs fichiers acceptés)",
    type=["csv"],
    accept_multiple_files=True
)

if fichiers_uploades:
    st.info(f"📁 {len(fichiers_uploades)} fichier(s) chargé(s) : {', '.join(f.name for f in fichiers_uploades)}")

st.divider()

# ─────────────────────────────────────────────
# ÉTAPE 3 — Lancement
# ─────────────────────────────────────────────

st.header("③ Lancer le traitement")

if st.button("▶  Lancer le traitement", disabled=(not fichiers_uploades or clients is None)):

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Préparation des fichiers
    fichiers_bytes = [(f.name, f.read()) for f in fichiers_uploades]

    # Zone de logs
    log_container = st.expander("📋 Journal d'exécution", expanded=True)
    log_lines = []

    def log_callback(level, msg):
        log_lines.append((level, msg))

    # Barre de progression
    progress = st.progress(0, text="Démarrage...")

    with st.spinner("Traitement en cours..."):
        progress.progress(10, "Lecture des fichiers...")
        resultats, resultats_prop, resultats_loc, doublons_df, global_df, logs = traiter_fichiers(
            fichiers_bytes, clients, log_callback
        )
        progress.progress(90, "Génération des fichiers de sortie...")
        # Sauvegarde dans session_state
        st.session_state.resultats = resultats
        st.session_state.doublons_df = doublons_df
        st.session_state.global_df = global_df
        st.session_state.logs = logs
        st.session_state.timestamp = timestamp

    progress.progress(100, "✅ Terminé !")

    # Affichage des logs
    with log_container:
        for level, msg in logs:
            if level == "ERROR":
                st.error(msg)
            elif level == "WARNING":
                st.warning(msg)
            elif level == "DEBUG":
                st.caption(msg)
            else:
                st.success(msg)

    st.divider()

    # ─────────────────────────────────────────────
    # RÉCAPITULATIF
    # ─────────────────────────────────────────────

    st.header("④ Récapitulatif")

    total_leads = sum(len(df) for df in resultats.values())
    nb_doublons = len(doublons_df) if not doublons_df.empty else 0

    # Calcul propriétaire/locataire sur le global
    nb_avec_statut = sum(
        len(df[df["Statut Propriété"].str.strip() != ""])
        for df in resultats.values()
        if "Statut Propriété" in df.columns
    )
    nb_sans_statut = total_leads - nb_avec_statut

    col1, col2, col3 = st.columns(3)
    col1.metric("Total leads valides", total_leads)
    col2.metric("Doublons détectés", nb_doublons)
    col3.metric("Fichiers traités", len(fichiers_uploades))

    col4, col5 = st.columns(2)
    col4.metric("✅ Statut propriété trouvé", nb_avec_statut)
    col5.metric("⬜ Statut propriété non trouvé", nb_sans_statut)

    # Tableau récap
    recap_data = []
    for cle, df in resultats.items():
        nb_prop = len(resultats_prop[cle]) if cle in resultats_prop else 0
        nb_loc  = len(resultats_loc[cle])  if cle in resultats_loc  else 0
        recap_data.append({
            "Client": cle,
            "Total leads": len(df),
            "Propriétaires": nb_prop,
            "Locataires": nb_loc,
            "Statut": "✅ OK" if len(df) > 0 else "— Vide"
        })
    if nb_doublons > 0:
        recap_data.append({"Client": "⚠ Doublons", "Total leads": nb_doublons, "Propriétaires": "—", "Locataires": "—", "Statut": "fichier séparé"})
    recap_data.append({"Client": "🌐 Global", "Total leads": total_leads, "Propriétaires": nb_avec_statut, "Locataires": total_leads - nb_avec_statut, "Statut": "tous les leads valides"})

    st.table(recap_data)

    st.divider()

    # ─────────────────────────────────────────────
    # TÉLÉCHARGEMENTS
    # ─────────────────────────────────────────────

    st.header("⑤ Télécharger les fichiers")

    # Boutons par client — propriétaires et locataires séparés
    for cle in resultats.keys():
        df_prop = resultats_prop.get(cle, pd.DataFrame())
        df_loc  = resultats_loc.get(cle, pd.DataFrame())
        st.markdown(f"**{cle}**")
        col_p, col_l = st.columns(2)
        with col_p:
            st.download_button(
                label=f"🏠 Propriétaires ({len(df_prop)})",
                data=df_to_csv_bytes(df_prop) if not df_prop.empty else b"",
                file_name=f"{cle}_proprietaires_{timestamp}.csv",
                mime="text/csv",
                key=f"prop_{cle}",
                disabled=df_prop.empty
            )
        with col_l:
            st.download_button(
                label=f"🔑 Locataires ({len(df_loc)})",
                data=df_to_csv_bytes(df_loc) if not df_loc.empty else b"",
                file_name=f"{cle}_locataires_{timestamp}.csv",
                mime="text/csv",
                key=f"loc_{cle}",
                disabled=df_loc.empty
            )

    st.divider()

    # Doublons
    if not doublons_df.empty:
        st.download_button(
            label=f"⬇ Doublons ({len(doublons_df)} leads)",
            data=df_to_csv_bytes(doublons_df),
            file_name=f"leads_doublons_{timestamp}.csv",
            mime="text/csv"
        )

    # Global
    st.download_button(
        label=f"⬇ Fichier Global ({len(global_df)} leads)",
        data=df_to_csv_bytes(global_df),
        file_name=f"leads_global_{timestamp}.csv",
        mime="text/csv"
    )

    # ZIP tout
    st.divider()
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for cle in resultats.keys():
            df_prop = resultats_prop.get(cle, pd.DataFrame())
            df_loc  = resultats_loc.get(cle, pd.DataFrame())
            if not df_prop.empty:
                zf.writestr(f"{cle}_proprietaires_{timestamp}.csv", df_to_csv_bytes(df_prop).decode("utf-8-sig"))
            if not df_loc.empty:
                zf.writestr(f"{cle}_locataires_{timestamp}.csv", df_to_csv_bytes(df_loc).decode("utf-8-sig"))
        if not doublons_df.empty:
            zf.writestr(f"leads_doublons_{timestamp}.csv", df_to_csv_bytes(doublons_df).decode("utf-8-sig"))
        zf.writestr(f"leads_global_{timestamp}.csv", df_to_csv_bytes(global_df).decode("utf-8-sig"))

    st.download_button(
        label="📦 Tout télécharger en ZIP",
        data=zip_buffer.getvalue(),
        file_name=f"leads_meta_{timestamp}.zip",
        mime="application/zip"
    )

# ─────────────────────────────────────────────
# AFFICHAGE APRÈS REFRESH (depuis session_state)
# ─────────────────────────────────────────────
elif st.session_state.resultats is not None:
    resultats  = st.session_state.resultats
    doublons_df = st.session_state.doublons_df
    global_df  = st.session_state.global_df
    timestamp  = st.session_state.timestamp

    st.info("ℹ️ Résultats du dernier traitement — relance le traitement pour mettre à jour.")
    st.divider()
    st.header("④ Récapitulatif")

    total_leads = sum(len(df) for df in resultats.values())
    nb_doublons = len(doublons_df) if not doublons_df.empty else 0

    col1, col2 = st.columns(2)
    col1.metric("Total leads valides", total_leads)
    col2.metric("Doublons détectés", nb_doublons)

    recap_data = []
    for cle, df in resultats.items():
        recap_data.append({"Client": cle, "Leads": len(df), "Statut": "✅ OK" if len(df) > 0 else "— Vide"})
    if nb_doublons > 0:
        recap_data.append({"Client": "⚠ Doublons", "Leads": nb_doublons, "Statut": "fichier séparé"})
    recap_data.append({"Client": "🌐 Global", "Leads": total_leads, "Statut": "tous les leads valides"})
    st.table(recap_data)

    st.divider()
    st.header("⑤ Télécharger les fichiers")

    cols = st.columns(2)
    for i, (cle, df) in enumerate(resultats.items()):
        with cols[i % 2]:
            st.download_button(
                label=f"⬇ {cle} ({len(df)} leads)",
                data=df_to_csv_bytes(df),
                file_name=f"{cle}_{timestamp}.csv",
                mime="text/csv",
                key=f"dl_refresh_{cle}"
            )

    if not doublons_df.empty:
        st.download_button(
            label=f"⬇ Doublons ({len(doublons_df)} leads)",
            data=df_to_csv_bytes(doublons_df),
            file_name=f"leads_doublons_{timestamp}.csv",
            mime="text/csv",
            key="dl_refresh_doublons"
        )

    st.download_button(
        label=f"⬇ Fichier Global ({len(global_df)} leads)",
        data=df_to_csv_bytes(global_df),
        file_name=f"leads_global_{timestamp}.csv",
        mime="text/csv",
        key="dl_refresh_global"
    )

    st.divider()
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for cle, df in resultats.items():
            zf.writestr(f"{cle}_{timestamp}.csv", df_to_csv_bytes(df).decode("utf-8-sig"))
        if not doublons_df.empty:
            zf.writestr(f"leads_doublons_{timestamp}.csv", df_to_csv_bytes(doublons_df).decode("utf-8-sig"))
        zf.writestr(f"leads_global_{timestamp}.csv", df_to_csv_bytes(global_df).decode("utf-8-sig"))

    st.download_button(
        label="📦 Tout télécharger en ZIP",
        data=zip_buffer.getvalue(),
        file_name=f"leads_meta_{timestamp}.zip",
        mime="application/zip",
        key="dl_refresh_zip"
    )
