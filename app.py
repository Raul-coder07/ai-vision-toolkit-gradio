import os
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np
import gradio as gr
from transformers import AutoProcessor, BlipForConditionalGeneration, BlipProcessor, BlipForQuestionAnswering

print("Cargando modelos de IA (esto puede tomar unos segundos)...")
# Modelos para Image Captioning y Scraping
caption_processor = AutoProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# Modelos para VQA (Visual Question Answering)
vqa_processor = BlipProcessor.from_pretrained("Salesforce/blip-vqa-base")
vqa_model = BlipForQuestionAnswering.from_pretrained("Salesforce/blip-vqa-base")
print("¡Modelos cargados exitosamente!")

# --- FUNCIÓN PROYECTO 1: Image Captioning ---
def caption_image(input_image):
    if input_image is None:
        return "Por favor, sube o selecciona una imagen."
    
    if isinstance(input_image, str):
        raw_image = Image.open(input_image).convert('RGB')
    else:
        raw_image = Image.fromarray(input_image).convert('RGB')

    inputs = caption_processor(images=raw_image, return_tensors="pt")
    outputs = caption_model.generate(**inputs, max_length=50)
    caption = caption_processor.decode(outputs[0], skip_special_tokens=True)
    return caption

# --- FUNCIÓN PROYECTO 2: Visual Question Answering (VQA) ---
def answer_question(image, question):
    if image is None:
        return "Por favor, sube una imagen."
    if not question.strip():
        return "Por favor, ingresa una pregunta válida en inglés."
    
    if isinstance(image, str):
        raw_image = Image.open(image).convert('RGB')
    else:
        raw_image = Image.fromarray(image).convert('RGB')
        
    inputs = vqa_processor(raw_image, question, return_tensors="pt")
    outputs = vqa_model.generate(**inputs)
    answer = vqa_processor.decode(outputs[0], skip_special_tokens=True)
    return answer

# --- FUNCIÓN PROYECTO 3: Web Scraper + Captioning ---
def scrape_and_caption(url):
    if not url.strip():
        return "Por favor, ingresa una URL válida.", None

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"Error al acceder a la URL. Código: {response.status_code}", None
    except Exception as e:
        return f"Error de conexión: {str(e)}", None

    soup = BeautifulSoup(response.text, "html.parser")
    img_elements = soup.find_all("img")
    
    output_filename = "captions_output.txt"
    results_log = []
    count = 0
    
    with open(output_filename, "w", encoding="utf-8") as f:
        for idx, img_element in enumerate(img_elements, start=1):
            img_url = img_element.get("src") or img_element.get("data-src")
            if not img_url and img_element.has_attr("srcset"):
                img_url = img_element.get("srcset").split()[0]
            if not img_url:
                continue
            
            if img_url.endswith(".svg") or ".svg" in img_url:
                continue
            
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            elif img_url.startswith("/"):
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                img_url = base_domain + img_url
            elif not img_url.startswith("http"):
                continue

            try:
                r = requests.get(img_url, timeout=5, headers=headers)
                raw_image = Image.open(BytesIO(r.content))
                
                # Filtrar imágenes muy pequeñas (iconos)
                if raw_image.size[0] * raw_image.size[1] < 400:
                    continue
                    
                raw_image = raw_image.convert("RGB")
                
                inputs = caption_processor(images=raw_image, text="the image of", return_tensors="pt")
                out = caption_model.generate(**inputs, max_new_tokens=50)
                caption = caption_processor.decode(out[0], skip_special_tokens=True)
                
                f.write(f"{img_url} : {caption}\n")
                results_log.append(f"[{idx}] {img_url} ➔ {caption}")
                count += 1
                
                if count >= 12:  # Límite para evitar bloqueos largos en demostraciones
                    break
            except Exception:
                continue

    summary = f"¡Proceso completado! Se procesaron {count} imágenes con éxito."
    log_text = "\n".join(results_log) if results_log else "No se encontraron imágenes válidas."
    return f"{summary}\n\n{log_text}", output_filename

# --- CONSTRUCCIÓN DE LA INTERFAZ CON GRADIO BLOCKS ---
custom_theme = gr.themes.Soft(primary_hue="indigo", secondary_hue="blue")

with gr.Blocks(theme=custom_theme) as demo:
    gr.Markdown("# 🚀 Suite Multimodal de Inteligencia Artificial")
    gr.Markdown("Colección de aplicaciones de Visión por Computador y Procesamiento de Lenguaje Natural usando **Hugging Face (BLIP)** y **Gradio**.")
    
    with gr.Tabs():
        # PESTAÑA 1
        with gr.TabItem("🖼️ Image Captioning"):
            gr.Markdown("### Genera descripciones automáticas para cualquier imagen.")
            with gr.Row():
                with gr.Column():
                    img_input1 = gr.Image(type="numpy", label="Sube una imagen")
                    btn1 = gr.Button("Generar Descripción", variant="primary")
                with gr.Column():
                    output1 = gr.Textbox(label="Descripción Generada", lines=4)
            btn1.click(fn=caption_image, inputs=img_input1, outputs=output1)
            
        # PESTAÑA 2
        with gr.TabItem("❓ Visual Q&A"):
            gr.Markdown("### Hazle preguntas a una imagen en lenguaje natural.")
            with gr.Row():
                with gr.Column():
                    img_input2 = gr.Image(type="numpy", label="Sube una imagen")
                    question_input = gr.Textbox(label="Pregunta (en inglés)", placeholder="Ej: What is the main object in this image?")
                    btn2 = gr.Button("Obtener Respuesta", variant="primary")
                with gr.Column():
                    output2 = gr.Textbox(label="Respuesta de la IA", lines=4)
            btn2.click(fn=answer_question, inputs=[img_input2, question_input], outputs=output2)
            
        # PESTAÑA 3
        with gr.TabItem("🌐 Web Image Scraper & Captioner"):
            gr.Markdown("### Extrae imágenes de una página web y descríbelas automáticamente.")
            with gr.Row():
                url_input = gr.Textbox(label="URL de la página web", placeholder="https://en.wikipedia.org/wiki/Artificial_intelligence")
                btn3 = gr.Button("Procesar Página", variant="primary")
            with gr.Row():
                output_log = gr.Textbox(label="Registro de Procesamiento", lines=10)
                output_file = gr.File(label="Descargar Archivo captions_output.txt")
            btn3.click(fn=scrape_and_caption, inputs=url_input, outputs=[output_log, output_file])

if __name__ == "__main__":
    demo.launch(share=True) # share=True genera un link público temporal automáticamente