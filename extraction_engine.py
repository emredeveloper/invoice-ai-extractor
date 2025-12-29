import os
import httpx
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF
import base64
from io import BytesIO
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

class LLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, content: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        pass

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-3-flash-preview')

    async def generate_json(self, content: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT_TEMPLATE.format(content=content)}"
        
        parts = [prompt]
        if image_path:
            img = Image.open(image_path)
            parts.append(img)

        response = self.model.generate_content(
            parts,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        return response.text

class LocalLLMProvider(LLMProvider):
    def __init__(self, base_url: str, model_name: str = "qwen/qwen3-vl-4b"):
        self.base_url = base_url
        self.model_name = model_name

    async def generate_json(self, content: str, image_path: Optional[str] = None) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        
        user_content = [{"type": "text", "text": USER_PROMPT_TEMPLATE.format(content=content)}]
        
        if image_path:
            with open(image_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                })
        
        messages.append({"role": "user", "content": user_content})

        async with httpx.AsyncClient() as client:
            # LM Studio specific: Use 'text' or omit response_format if json_object is not supported
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.1
            }
            
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=600.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

class ExtractionEngine:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text directly from PDF using PyMuPDF (no system dependencies)."""
        doc = fitz.open(file_path)
        full_text = ""
        for i, page in enumerate(doc):
            full_text += f"\n--- Page {i+1} ---\n{page.get_text()}"
        return full_text

    async def process_invoice(self, file_path: str, content_type: Optional[str]) -> Dict[str, Any]:
        text = ""
        image_path = None
        temp_image = None
        
        # Detect type by extension as fallback
        ext = os.path.splitext(file_path)[1].lower()
        
        # Ensure content_type is a string for checking
        c_type = (content_type or "").lower()

        is_pdf = "pdf" in c_type or ext == ".pdf"
        is_local = isinstance(self.llm_provider, LocalLLMProvider)

        if is_pdf:
            text = self.extract_text_from_pdf(file_path)
            # For local models, we MUST provide an image for vision capabilities
            if is_local:
                doc = fitz.open(file_path)
                if len(doc) > 0:
                    page = doc.load_page(0)
                    # Reduced resolution for better memory stability on local models
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
                    temp_image = f"temp_preview_{os.getpid()}.png"
                    pix.save(temp_image)
                    image_path = temp_image
                doc.close()
                # IMPORTANT: If we have an image, we don't send the full text to local models
                # as it overflows the context window.
                text = "Extracted from the attached image."
        elif "image" in c_type or ext in [".jpg", ".jpeg", ".png"]:
            image_path = file_path
            text = "Process this image"
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

        try:
            json_str = await self.llm_provider.generate_json(text, image_path=image_path)
            return json.loads(json_str)
        finally:
            # Clean up temp image
            if temp_image and os.path.exists(temp_image):
                os.remove(temp_image)
