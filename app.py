import math
import streamlit as st
import os
import camera_model
from drive_client import get_video_url
from orchestrator import get_container_logs, BASE_CONTAINER_NAME
from record import base_dir

st.set_page_config(page_title="Gerenciador de Câmeras", layout="wide")

# Página principal ou detalhe
page = st.query_params.get("pagina", "home")
camera_name = st.query_params.get("cam", "")
camera_id = st.query_params.get("cam_id", "")


def normalize_name(name: str):
    return name.replace(" ", "_").lower()


@st.dialog("Editar Câmera", width="large")
def edit_camera(camera_id: int):
    with st.form("edit_camera"):
        camera_data = camera_model.get_camera_data(camera_id)
        camera_data.name = st.text_input("Nome", value=camera_data.name)
        camera_data.ip = st.text_input("IP", value=camera_data.ip)
        camera_data.user = st.text_input("Usuário", value=camera_data.user)
        camera_data.passw = st.text_input(
            "Senha", type="password", value=camera_data.passw
        )
        camera_data.segment_duration = st.text_input(
            "Duração de cada gravação",
            placeholder="00:00:30",
            value=camera_data.segment_duration,
        )
        camera_data.date_range = st.number_input(
            "Dias para manter gravações", min_value=1, value=camera_data.date_range
        )

        if st.form_submit_button("Salvar", use_container_width=True, type="primary"):
            with st.spinner("Salvando...", show_time=True):
                camera_data.edit()
            st.success(f"Câmera {camera_data.name} atualizada!")


@st.dialog("Logs", width="large")
def get_recorder_logs(last_container_name: str):
    minutes_range = st.number_input(
        "Buscar ultimos",
        help="Quantidade em minutos de tempo no passado para buscar os logs",
        min_value=1,
        max_value=60,
        value=1,
    )
    try:
        logs = get_container_logs(
            f"{BASE_CONTAINER_NAME}-{last_container_name}", minutes_range
        )
    except Exception as err:
        st.error(err)
        logs = []
    for log_line in logs:
        if not log_line:
            continue
        with st.empty():
            if log_line.startswith("WARNING"):
                st.warning(log_line.strip())
                continue
            if log_line.startswith("ERROR"):
                st.error(log_line.strip())
                continue
            st.info(log_line.strip())


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
        records = sorted([f for f in os.listdir(camera_path) if f.endswith(".jpg")])
        rows = [st.columns(3, border=True) for _ in range(math.ceil(len(records) / 3))]

        index = 0
        for row in rows:
            for col in row:
                if index >= len(records):
                    break
                thumb_path = os.path.join(camera_path, records[index])

                col.image(thumb_path, caption=records[index])
                video_filename = os.path.split(records[index])[-1].replace(
                    ".jpg", ".mp4"
                )
                video_url = get_video_url(
                    video_filename,
                    camera_data.uri,
                )
                if video_url:
                    col.link_button(
                        "Link do drive",
                        video_url,
                        use_container_width=True,
                        type="primary",
                        icon="▶️",
                    )
                else:
                    col.warning("Video não encontrado no drive!")
                index += 1
    else:
        st.info("Nenhuma gravação encontrada localmente.")

    st.markdown("---")
    st.markdown(
        f"📁 [Ver gravações antigas no Google Drive](https://drive.google.com/drive/u/1/folders/{camera_data.uri})",
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
                    camera = camera_model.Camera(
                        name=name,
                        ip=ip,
                        user=user,
                        passw=passw,
                        segment_duration=segment_duration,
                        date_range=date_range,
                    )
                    camera.save()
                st.success(f"Câmera {name} adicionada!")

    st.markdown("---")

    title_col1, title_col2 = st.columns([6, 1])
    title_col1.subheader("📷 Câmeras cadastradas")
    title_col2.button(
        "_",
        key="orchestrator_logs",
        on_click=lambda: get_recorder_logs("orchestrator"),
    )

    cameras = camera_model.list_cameras()
    if cameras:
        for cam in cameras:
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"**{cam.name}** — {cam.ip}")
                st.caption(f"status: {'Gravando' if cam.recording else 'Parado'}")
            with col2:
                c_col1, c_col2, c_col3 = col2.columns(3, gap="small")
                c_col1.button(
                    "_",
                    key="logs_" + cam.name,
                    on_click=lambda cam_id=cam.wid: get_recorder_logs(
                        f"monitoring-{cam_id}"
                    ),
                )
                c_col2.button(
                    "⚙️",
                    key="editar_" + cam.name,
                    on_click=lambda cam_id=cam.wid: edit_camera(cam_id),
                )
                c_col3.button(
                    "📂",
                    key="gravacoes_" + cam.name,
                    on_click=lambda cam_data=cam: st.query_params.from_dict(
                        {
                            "pagina": "gravacoes",
                            "cam": cam_data.name,
                            "cam_id": cam_data.wid,
                        }
                    ),
                )
    else:
        st.info("Nenhuma câmera cadastrada ainda.")
