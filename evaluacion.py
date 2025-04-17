import streamlit as st
import openai
import difflib
import time
from contexto_equipo import chunks_equipo  # Chunks de los 3 TXT del equipo ideal
import base64
from io import BytesIO

# Inicializar cliente
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="Evaluador de Equipo Fundador", page_icon="🧑‍🤝‍🧑")
st.title("👥 Evaluador de Composición del Equipo Fundador")

# Funciones auxiliares
def obtener_contexto_relevante(user_input, n=5, min_similarity=0.2):
    # Ignorar entradas muy cortas para evitar coincidencias irrelevantes
    if len(user_input.strip()) < 5:
        return []
        
    similitudes = [(chunk, difflib.SequenceMatcher(None, user_input.lower(), chunk.lower()).ratio())
                   for chunk in chunks_equipo if len(chunk.strip()) > 50]  # Solo considerar chunks sustanciales
    
    # Filtrar por similitud mínima y ordenar por relevancia
    chunks_relevantes = [(c, ratio) for c, ratio in similitudes if ratio > min_similarity]
    top_chunks = sorted(chunks_relevantes, key=lambda x: x[1], reverse=True)[:n]
    
    # Si no hay coincidencias buenas, usar algunos fragmentos importantes por defecto
    if not top_chunks:
        fragmentos_clave = [chunk for chunk in chunks_equipo 
                           if "Founders Market Fit" in chunk 
                           or "dilema del rey o rico" in chunk
                           or "equity story" in chunk
                           or "valores" in chunk][:n]
        return fragmentos_clave
        
    return [c[0] for c in top_chunks]

# Función para crear HTML para exportar
def generar_html_para_pdf(secciones):
    # Estilo CSS
    html = """
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                line-height: 1.6;
            }
            h1 {
                color: #2C3E50;
                border-bottom: 2px solid #3498DB;
                padding-bottom: 10px;
            }
            h2 {
                color: #2980B9;
                margin-top: 30px;
            }
            .fortalezas {
                background-color: #E8F5E9;
                border-left: 5px solid #4CAF50;
                padding: 15px;
                margin: 20px 0;
            }
            .debilidades {
                background-color: #FFEBEE;
                border-left: 5px solid #F44336;
                padding: 15px;
                margin: 20px 0;
            }
            .recomendaciones {
                background-color: #E3F2FD;
                border-left: 5px solid #2196F3;
                padding: 15px;
                margin: 20px 0;
            }
            .capital {
                background-color: #FFF8E1;
                border-left: 5px solid #FFC107;
                padding: 15px;
                margin: 20px 0;
            }
            footer {
                margin-top: 50px;
                text-align: center;
                color: #7F8C8D;
                font-size: 12px;
                border-top: 1px solid #BDC3C7;
                padding-top: 15px;
            }
        </style>
    </head>
    <body>
        <h1>Diagnóstico del Equipo Fundador</h1>
        <p><em>Generado por Nuclio Founders</em></p>
    """
    
    # Añadir secciones
    for s in secciones:
        if "Fortalezas" in s:
            html += f"""
            <div class="fortalezas">
                <h2>💪 Fortalezas</h2>
                <p>{s.replace("Fortalezas:", "").strip()}</p>
            </div>
            """
        elif "Debilidades" in s:
            html += f"""
            <div class="debilidades">
                <h2>⚠️ Debilidades</h2>
                <p>{s.replace("Debilidades:", "").strip()}</p>
            </div>
            """
        elif "Recomendaciones" in s:
            html += f"""
            <div class="recomendaciones">
                <h2>🛠️ Recomendaciones</h2>
                <p>{s.replace("Recomendaciones:", "").strip()}</p>
            </div>
            """
        elif "Distribución del capital" in s:
            html += f"""
            <div class="capital">
                <h2>📊 Distribución del Capital</h2>
                <p>{s.replace("Distribución del capital:", "").strip()}</p>
            </div>
            """
    
    # Añadir footer
    html += """
        <footer>
            <p>© Nuclio Founders - Análisis de Equipo Fundador</p>
        </footer>
    </body>
    </html>
    """
    
    return html

# Función para crear un botón de descarga HTML
def create_download_link(html_content, filename="diagnostico.html"):
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">📥 Descargar como HTML</a>'
    return href

# Inicializar estados
if "modo_equipo" not in st.session_state:
    st.session_state.modo_equipo = False

if "chat" not in st.session_state:
    st.session_state.chat = []

if "diagnostico_realizado" not in st.session_state:
    st.session_state.diagnostico_realizado = False

if "secciones_diagnostico" not in st.session_state:
    st.session_state.secciones_diagnostico = []

if "resultado_diagnostico" not in st.session_state:
    st.session_state.resultado_diagnostico = None

# Comenzar evaluación
if not st.session_state.modo_equipo:
    st.write("Este chat analizará si tu equipo fundador está bien compuesto. Responderás 15 preguntas sobre dedicación, capital, roles y equilibrio.")
    if st.button("Comenzar Evaluación"):
        st.session_state.modo_equipo = True
        st.session_state.chat.append({
            "role": "system",
            "content": (
                "Eres el Director de Inversiones de un fondo de capital riesgo especializado en invertir en emprendedores y startups. "
                "Utiliza 'vosotros' en lugar de 'ustedes', tutea al usuario, y emplea vocabulario y expresiones propias de España. Evita completamente términos o expresiones latinoamericanas. "
                "Tu tarea es evaluar la adecuación y composición del equipo fundador de una empresa que busca inversión. "
                "Debes comunicarte EXACTAMENTE con el mismo estilo, tono y enfoque que Nuclio Founders. "
                "Utiliza ejemplos concretos, metáforas sobre emprendimiento y el enfoque directo que caracteriza a Nuclio. "
                "Debes hacer justamente 15 preguntas específicas, directas y claras sobre:\n\n"
                "- El modelo de negocio y el mercado\n"
                "- La composición y funciones del equipo fundador\n"
                "- La implicación y dedicación de cada cofundador\n"
                "- La distribución de capital y su justificación\n"
                "- La cohesión del equipo y cómo toman decisiones\n"
                "- El compromiso a largo plazo\n\n"
                "Haz preguntas directas, profesionales y críticas si es necesario. Pon en duda las respuestas cuando sea relevante. "
                "Detecta si hay desequilibrios entre capital y dedicación, si hay conflictos no resueltos, o si falta claridad. "
                "Puedes usar simulaciones hipotéticas si ayudan a extraer información. Tu rol es de evaluador, no de animador. "
                "No expliques lo que haces. Sé claro, directo. "
                "Adopta el estilo de Nuclio Founders, que es directo y algo cabroncete a nivel de tener las cosas claras. "
                "Menciona conceptos clave de Nuclio como el 'Founders Market Fit', el 'dilema del rey o rico', y usa frases como 'emprender con alguien es como casarte'. "
                "Cuando hayas hecho las 15 preguntas, deja de preguntar y espera que el usuario pulse el botón 'Ver diagnóstico'."
            )
        })
        st.session_state.chat.append({
            "role": "assistant",
            "content": "Empecemos. ¿Cuál es el modelo de negocio de tu empresa y qué problema resuelve?"
        })

# Mostrar historial del chat
for msg in st.session_state.chat:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Input del usuario
if st.session_state.modo_equipo and not st.session_state.diagnostico_realizado:
    if prompt := st.chat_input("Escribe tu respuesta aquí..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat.append({"role": "user", "content": prompt})

        # Añadir chunks relevantes como contexto auxiliar
        contextos = obtener_contexto_relevante(prompt)
        contexto_como_mensaje = {
            "role": "system",
            "content": (
                "Contexto de apoyo basado en el contenido formativo de Nuclio sobre equipos fundadores. "
                "DEBES adoptar el mismo tono, estilo, vocabulario y enfoque que se usa en estos textos. "
                "Imita su manera de expresarse y sus expresiones características. "
                "Usa las mismas metáforas y ejemplos que aparecen en estos textos siempre que sea posible:\n\n" +
                "\n---\n".join(contextos)
            )
        }

        mensajes_con_contexto = [
            {"role": "system", "content": st.session_state.chat[0]["content"]},
            contexto_como_mensaje
        ] + st.session_state.chat[1:]

        # Llamada al modelo
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=mensajes_con_contexto,
            temperature=0.7
        )

        reply = response.choices[0].message.content
        st.session_state.chat.append({"role": "assistant", "content": reply})

        # Typing effect
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_text = ""
            for char in reply:
                full_text += char
                message_placeholder.markdown(full_text + "▌")
                time.sleep(0.01)
            message_placeholder.markdown(full_text)

# Mostrar botón de diagnóstico tras 15 respuestas
respuestas_dadas = sum(1 for m in st.session_state.chat if m["role"] == "user")

# Depuración
st.sidebar.write(f"DEBUG - Respuestas dadas: {respuestas_dadas}")
st.sidebar.write(f"DEBUG - Diagnóstico realizado: {st.session_state.diagnostico_realizado}")

if st.session_state.modo_equipo and respuestas_dadas >= 15 and not st.session_state.diagnostico_realizado:
    st.divider()
    if st.button("Ver diagnóstico del equipo", key="boton_diagnostico"):
        with st.spinner("📊 Analizando tu equipo..."):
            try:
                resumen_prompt = [
                    {
                        "role": "system",
                        "content": (
                            "Eres el Director de Inversiones de un fondo de capital riesgo. DEBES hacer un análisis profesional sobre la composición del equipo fundador basado en esta conversación. Tu respuesta DEBE contener EXACTAMENTE estas 4 secciones, en este orden y con estos títulos:\n\n"
                            "### Fortalezas:\nDescribe aquí las fortalezas del equipo\n\n"
                            "### Debilidades:\nDescribe aquí las debilidades del equipo\n\n"
                            "### Recomendaciones:\nDescribe aquí las recomendaciones\n\n"
                            "### Distribución del capital:\nAnaliza aquí la distribución del capital\n\n"
                            "ES OBLIGATORIO usar '###' antes de cada sección exactamente como mostrado arriba. NO generes mensajes de despedida, conclusiones ni texto adicional fuera de estas secciones. "
                            "Sé directo, claro y 'cabroncete' con tus conclusiones. No te andes con rodeos. "
                            "Usa conceptos como Founders Market Fit, el dilema del rey o rico, y metáforas como 'emprender es como casarse'. "
                            "Incluye al menos 2-3 frases textuales que aparecen en los materiales de Nuclio."
                        )
                    }
                ] + st.session_state.chat

                resultado = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=resumen_prompt,
                    temperature=0.7
                )

                resultado_final = resultado.choices[0].message.content
                
                # Verificar si el resultado tiene el formato esperado
                if ("### Fortalezas:" not in resultado_final or 
                    "### Debilidades:" not in resultado_final or 
                    "### Recomendaciones:" not in resultado_final or 
                    "### Distribución del capital:" not in resultado_final):
                    
                    # Si no tiene el formato correcto, usar un diagnóstico de respaldo
                    st.warning("El modelo no generó el formato esperado. Usando diagnóstico de respaldo...")
                    
                    resultado_final = """### Fortalezas:
Basado en la conversación, se observa que el equipo muestra interés en estructurarse adecuadamente, lo cual es fundamental. Como decimos en Nuclio, "emprender con alguien es como casarte", y parece que estáis conscientes de la importancia de tener una buena configuración de cofundadores.

### Debilidades:
Se detectan posibles áreas de mejora en la definición de roles y responsabilidades. Es importante recordar el "Founders Market Fit" - necesitáis asegurar que cada cofundador aporta el valor adecuado en el momento adecuado del proyecto. Posiblemente falte claridad en cómo se distribuyen las tareas y responsabilidades.

### Recomendaciones:
Os recomendaría definir con mayor claridad los roles específicos de cada cofundador, establecer expectativas claras sobre dedicación y revisitar la distribución de capital para que refleje las aportaciones reales. Como decimos siempre, es mejor jugar con la estadística a tu favor y no en tu contra al configurar el equipo inicial.

### Distribución del capital:
Revisad si vuestra distribución actual refleja el valor real que cada miembro aporta. Recordad el "dilema del rey o rico" - aseguraos de que todos los cofundadores están alineados en sus motivaciones. La distribución de equity debe reflejar no solo las aportaciones iniciales sino también el compromiso futuro."""
                
                # Guardar el resultado en session_state
                st.session_state.resultado_diagnostico = resultado_final
                
                # Marcar como completado para que la próxima vez no vuelva a generarlo
                st.session_state.diagnostico_realizado = True
                
                # Recargar la página para mostrar el diagnóstico
                st.rerun()
            except Exception as e:
                st.error(f"❌ Ha ocurrido un error al generar el diagnóstico: {e}")

# Mostrar el diagnóstico si está disponible
if st.session_state.diagnostico_realizado and "resultado_diagnostico" in st.session_state:
    resultado_final = st.session_state.resultado_diagnostico
    
    if resultado_final:
        st.markdown("## 🧠 Diagnóstico del Equipo", unsafe_allow_html=True)
        secciones = resultado_final.split("###")
        st.session_state.secciones_diagnostico = secciones  # Guardar para generar HTML
        
        # Verificar si hay secciones con formato correcto
        seccion_encontrada = False
        
        for s in secciones:
            if "Fortalezas" in s:
                st.success("💪 **Fortalezas**\n\n" + s.replace("Fortalezas:", "").strip())
                seccion_encontrada = True
            elif "Debilidades" in s:
                st.error("⚠️ **Debilidades**\n\n" + s.replace("Debilidades:", "").strip())
                seccion_encontrada = True
            elif "Recomendaciones" in s:
                st.info("🛠️ **Recomendaciones**\n\n" + s.replace("Recomendaciones:", "").strip())
                seccion_encontrada = True
            elif "Distribución del capital" in s:
                st.warning("📊 **Distribución del capital**\n\n" + s.replace("Distribución del capital:", "").strip())
                seccion_encontrada = True
            elif s.strip():  # Solo mostrar secciones no vacías
                st.markdown(s.strip(), unsafe_allow_html=True)
        
        # Si no se encontró ninguna sección formateada correctamente
        if not seccion_encontrada:
            st.error("❌ El diagnóstico no se formateó correctamente. Por favor, reinicia el diagnóstico.")
            if st.button("Reiniciar diagnóstico"):
                st.session_state.diagnostico_realizado = False
                st.rerun()
    else:
        st.error("⚠️ No se ha podido generar el diagnóstico. Inténtalo de nuevo.")
        if st.button("Reintentar diagnóstico"):
            st.session_state.diagnostico_realizado = False
            st.rerun()

# Mostrar botón de descarga HTML si el diagnóstico está listo
if st.session_state.diagnostico_realizado and st.session_state.secciones_diagnostico:
    # Generar HTML para descargar
    html_content = generar_html_para_pdf(st.session_state.secciones_diagnostico)
    
    # Mostrar botón de descarga
    st.markdown("""---""")
    st.markdown("### 📑 Exportar diagnóstico")
    st.info("Puedes descargar este diagnóstico para compartirlo o imprimirlo.")
    
    # Botón de descarga
    st.markdown(create_download_link(html_content, "diagnostico_equipo_fundador.html"), unsafe_allow_html=True)
    
    # Nota explicativa
    st.caption("El archivo HTML se puede abrir en cualquier navegador y se puede imprimir como PDF desde allí.")
