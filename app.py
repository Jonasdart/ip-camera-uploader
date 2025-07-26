import math
import streamlit as st
import os
import camera_model
from drive_client import get_video_url
from record import base_dir

st.set_page_config(page_title="Gerenciador de Câmeras", layout="wide")

# Página principal ou detalhe
page = st.query_params.get("pagina", "home")
camera_name = st.query_params.get("cam", "")
camera_id = st.query_params.get("cam_id", "")


def normalize_name(name: str):
    return name.replace(" ", "_").lower()


# 📄 Página: gravações da câmera
if page == "gravacoes" and camera_name:
    st.button(
        "🔙 Voltar",
        on_click=lambda: st.query_params.from_dict({"pagina": "home"}),
        type="tertiary",
    )
    st.title(f"🎥 Gravações da câmera: {camera_name}")
    camera_data = camera_model.get_camera_data(camera_id)
    camera_path = os.path.join(base_dir, normalize_name(camera_name))

    if os.path.exists(camera_path):
        dates = sorted([f for f in os.listdir(camera_path)])

        if dates:
            for subpath in dates:
                records = sorted(
                    [f for f in os.listdir(os.path.join(camera_path, subpath))]
                )
                records = [record for record in records if record.endswith(".jpg")]

                with st.expander(f"🕒 {subpath} - {len(records)} Gravações"):
                    rows = [
                        st.columns(3, border=True)
                        for _ in range(math.ceil(len(records) / 3))
                    ]

                    index = 0
                    for row in rows:
                        for col in row:
                            if index >= len(records):
                                break
                            thumb_path = os.path.join(
                                camera_path, subpath, records[index]
                            )

                            col.image(thumb_path, caption=records[index])
                            video_path = os.path.split(thumb_path)[-1].replace(
                                ".jpg", ".mp4"
                            )
                            col.link_button(
                                "Link do drive",
                                get_video_url(
                                    video_path,
                                    subpath,
                                    camera_data["camera_folder_id"],
                                ),
                                use_container_width=True,
                                type="primary",
                                icon="▶️"
                            )
                            index += 1
    else:
        st.info("Nenhuma gravação encontrada localmente.")

    st.markdown("---")
    st.markdown(
        f"📁 [Ver gravações antigas no Google Drive](https://drive.google.com/drive/u/1/folders/{camera_data['camera_folder_id']})",
        unsafe_allow_html=True,
    )
else:
    st.title("Gerenciador de Câmeras IP")

    with st.expander("➕ Adicionar nova câmera"):
        with st.form("nova_camera"):
            name = st.text_input("Nome")
            ip = st.text_input("IP")
            user = st.text_input("Usuário")
            passw = st.text_input("Senha", type="password")
            segment_duration = st.text_input(
                "Duração de cada gravação", placeholder="00:00:30"
            )
            date_range = st.number_input(
                "Dias para manter gravações", min_value=1, value=7
            )

            if st.form_submit_button("Salvar"):
                with st.spinner("Salvando...", show_time=True):
                    camera_model.add_camera(
                        name, ip, user, passw, segment_duration, date_range
                    )
                st.success(f"Câmera {name} adicionada!")

    st.markdown("---")
    st.subheader("📷 Câmeras cadastradas")

    cameras = camera_model.list_cameras()
    if cameras:
        for cam in cameras:
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"**{cam['name']}** — {cam['ip']}")
                st.caption(f"{cam['date_range']} dias de retenção")
            with col2:
                c_col1, c_col2 = col2.columns([0.5, 0.5], gap="small")
                c_col1.button(
                    "⚙️",
                    key="editar_" + cam["name"],
                )
                c_col2.button(
                    "📂",
                    key="gravacoes_" + cam["name"],
                    on_click=lambda n=cam["name"]: st.query_params.from_dict(
                        {"pagina": "gravacoes", "cam": n, "cam_id": cam.doc_id}
                    ),
                )
    else:
        st.info("Nenhuma câmera cadastrada ainda.")
