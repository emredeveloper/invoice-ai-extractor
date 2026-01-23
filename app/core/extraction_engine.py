import os
import httpx
from google import genai
from google.genai import types
from PIL import Image
import fitz  # PyMuPDF
import base64
import uuid
import logging
import mimetypes
from io import BytesIO
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json
import asyncio
from app.core.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, MULTIPAGE_MERGE_PROMPT

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, content: str, image_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate JSON from content and optional images."""
        pass

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash") # Stable default
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    async def generate_json(self, content: str, image_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT_TEMPLATE.format(content=content)}"
        
        parts = [types.Part.from_text(prompt)]
        
        # Add multiple images for multi-page support
        if image_paths:
            for img_path in image_paths:
                with open(img_path, "rb") as img_file:
                    img_data = img_file.read()
                mime_type = mimetypes.guess_type(img_path)[0] or "image/png"
                parts.append(types.Part.from_bytes(data=img_data, mime_type=mime_type))

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[types.Content(role="user", parts=parts)],
            generation_config=types.GenerationConfig(response_mime_type="application/json")
        )
        return response.text

class LocalLLMProvider(LLMProvider):
    def __init__(self, base_url: str, model_name: str = "qwen/qwen3-vl-4b"):
        self.base_url = base_url
        self.model_name = model_name
        self.max_images_per_request = int(os.getenv("LOCAL_LLM_MAX_IMAGES", "3"))

    async def _process_single_page(self, content: str, image_path: str) -> str:
        """Process a single page with the local LLM."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        
        user_content = [{"type": "text", "text": USER_PROMPT_TEMPLATE.format(content=content)}]
        
        with open(image_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode('utf-8')
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
            })
        
        messages.append({"role": "user", "content": user_content})

        async with httpx.AsyncClient() as client:
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

    async def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple page results into a single invoice."""
        if len(results) == 1:
            return results[0]
        
        # Merge strategy: combine items, keep first non-null general fields
        merged = {
            "general_fields": {},
            "items": []
        }
        
        general_fields = ["invoice_number", "date", "supplier_name", "total_amount", 
                         "currency", "tax_amount", "tax_rate"]
        
        for field in general_fields:
            for result in results:
                gf = result.get("general_fields", {})
                if gf.get(field) is not None:
                    merged["general_fields"][field] = gf[field]
                    break
        
        # Combine all items
        for result in results:
            items = result.get("items", [])
            merged["items"].extend(items)
        
        return merged

    async def generate_json(self, content: str, image_paths: Optional[List[str]] = None) -> str:
        if not image_paths:
            # Text-only processing
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(content=content)}
            ]
            
            async with httpx.AsyncClient() as client:
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
        
        # Multi-page processing: process each page and merge
        if len(image_paths) <= self.max_images_per_request:
            # Can process all at once with Qwen VL
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            user_content = [{"type": "text", "text": USER_PROMPT_TEMPLATE.format(content=content)}]
            
            for img_path in image_paths:
                with open(img_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                    })
            
            messages.append({"role": "user", "content": user_content})
            
            async with httpx.AsyncClient() as client:
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
        else:
            # Process pages in batches and merge results
            results = []
            for img_path in image_paths:
                result_str = await self._process_single_page(content, img_path)
                try:
                    result = json.loads(result_str)
                    results.append(result)
                except json.JSONDecodeError:
                    continue
            
            merged = await self._merge_results(results)
            return json.dumps(merged)


class ExtractionEngine:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.max_pages = int(os.getenv("MAX_PDF_PAGES", "10"))
        self.dpi_scale = float(os.getenv("PDF_DPI_SCALE", "1.5"))

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text directly from PDF using PyMuPDF (no system dependencies)."""
        doc = fitz.open(file_path)
        full_text = ""
        for i, page in enumerate(doc):
            full_text += f"\n--- Page {i+1} ---\n{page.get_text()}"
        doc.close()
        return full_text

    def convert_pdf_to_images(self, file_path: str) -> List[str]:
        """Convert all PDF pages to images for vision processing with unique filenames."""
        doc = fitz.open(file_path)
        image_paths = []
        
        num_pages = min(len(doc), self.max_pages)
        process_id = os.getpid()
        unique_id = uuid.uuid4().hex[:8]
        
        for i in range(num_pages):
            page = doc.load_page(i)
            # 150 DPI is usually enough for OCR while keeping file size small
            pix = page.get_pixmap(matrix=fitz.Matrix(self.dpi_scale, self.dpi_scale))
            temp_image = os.path.join(os.path.dirname(file_path), f"temp_{unique_id}_{process_id}_{i}.png")
            pix.save(temp_image)
            image_paths.append(temp_image)
        
        doc.close()
        return image_paths

    async def process_invoice(self, file_path: str, content_type: Optional[str]) -> Dict[str, Any]:
        text = ""
        image_paths = []
        temp_images = []
        
        # Detect type by extension as fallback
        ext = os.path.splitext(file_path)[1].lower()
        
        # Ensure content_type is a string for checking
        c_type = (content_type or "").lower()

        is_pdf = "pdf" in c_type or ext == ".pdf"
        is_local = isinstance(self.llm_provider, LocalLLMProvider)

        try:
            if is_pdf:
                text = self.extract_text_from_pdf(file_path)
                
                # Convert ALL pages to images for vision processing
                temp_images = self.convert_pdf_to_images(file_path)
                image_paths = temp_images
                
                if is_local:
                    # For local models, use simpler content description
                    text = f"Extracted from the attached {len(temp_images)} page(s) invoice image(s)."
                    
            elif "image" in c_type or ext in [".jpg", ".jpeg", ".png"]:
                image_paths = [file_path]
                text = "Process this invoice image"
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()

            json_str = await self.llm_provider.generate_json(text, image_paths=image_paths if image_paths else None)
            
            # Handle potential markdown code blocks and unexpected prefixes in response
            if isinstance(json_str, str):
                json_str = json_str.strip()
                # Remove Markdown code block wrappers
                if "```json" in json_str:
                    json_str = json_str.split("```json")[-1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[-1].split("```")[0]
                
                # Final strip of whitespace or potential artifacts
                json_str = json_str.strip()
                
                # If the string starts with anything other than { or [, it's likely malformed
                if not (json_str.startswith("{") or json_str.startswith("[")):
                    start_idx = json_str.find("{")
                    if start_idx != -1:
                        json_str = json_str[start_idx:]
                    end_idx = json_str.rfind("}")
                    if end_idx != -1:
                        json_str = json_str[:end_idx+1]
            
            result = json.loads(json_str)
            
            # Add metadata
            result["_metadata"] = {
                "pages_processed": len(temp_images) if temp_images else 1,
                "file_type": ext,
                "provider": "local" if is_local else "gemini"
            }
            
            return result
            
        finally:
            # Clean up temp images
            for temp_img in temp_images:
                if os.path.exists(temp_img):
                    try:
                        os.remove(temp_img)
                    except Exception:
                        pass
