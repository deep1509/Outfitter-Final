"""
Virtual Try-On UI Components for Gradio
Provides sidebar interface for photo upload and virtual try-on results
"""

import gradio as gr
import base64
import io
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple

class VirtualTryOnUI:
    """
    UI components for virtual try-on functionality.
    """
    
    def __init__(self):
        self.current_photo = None
        self.tryon_results = {}
    
    def create_sidebar(self) -> gr.Column:
        """
        Create the virtual try-on sidebar component.
        """
        with gr.Column(visible=False, elem_id="virtual_tryon_sidebar") as sidebar:
            gr.Markdown("## 🎭 Virtual Try-On")
            
            # Photo upload section
            with gr.Group():
                gr.Markdown("### 📸 Upload Your Photo")
                photo_upload = gr.File(
                    label="Upload your photo",
                    file_types=["image"],
                    type="filepath"
                )
                
                upload_btn = gr.Button("📸 Use This Photo", variant="primary")
            
            # Try-on results section
            with gr.Group():
                
                # Results display
                results_container = gr.Column()
                
                # Try-on button
                tryon_btn = gr.Button("🎭 Try On Items", variant="secondary", visible=False)
            
            # Instructions
            gr.Markdown("""
            **How it works:**
            1. Upload a clear photo of yourself
            2. Click "Try On Items" to see how your cart items look on you
            3. The AI will overlay the clothing onto your photo realistically
            """)
        
        return sidebar
    
    def process_photo_upload(self, photo_path: str) -> Tuple[bool, str]:
        """
        Process uploaded photo and convert to base64.
        """
        try:
            if not photo_path:
                return False, "No photo uploaded"
            
            # Load and process image
            with open(photo_path, 'rb') as f:
                image_data = f.read()
            
            # Convert to base64
            self.current_photo = base64.b64encode(image_data).decode('utf-8')
            
            return True, "Photo uploaded successfully! Ready for virtual try-on."
            
        except Exception as e:
            return False, f"Error processing photo: {str(e)}"
    
    def display_tryon_results(self, results: Dict[str, Any]) -> str:
        """
        Display virtual try-on results in the UI.
        """
        if not results:
            return "No try-on results available."
        
        html_content = "<div style='display: flex; flex-direction: column; gap: 20px;'>"
        
        for category, result in results.items():
            if result.get('success', False):
                item = result.get('item', {})
                tryon_image = result.get('tryon_image', '')
                
                if tryon_image:
                    html_content += f"""
                    <div style='border: 1px solid #ddd; padding: 15px; border-radius: 8px;'>
                        <h3>🎭 {category.title()} Try-On</h3>
                        <p><strong>{item.get('name', 'Unknown Item')}</strong> - {item.get('price', 'N/A')}</p>
                        <img src="data:image/jpeg;base64,{tryon_image}" 
                             style="max-width: 100%; height: auto; border-radius: 4px;" />
                    </div>
                    """
            else:
                error = result.get('error', 'Unknown error')
                html_content += f"""
                <div style='border: 1px solid #ff6b6b; padding: 15px; border-radius: 8px; background-color: #ffe0e0;'>
                    <h3>❌ {category.title()} Try-On Failed</h3>
                    <p>Error: {error}</p>
                </div>
                """
        
        html_content += "</div>"
        return html_content
    
    def create_tryon_interface(self) -> Tuple[gr.Column, gr.File, gr.Button, gr.Button, gr.HTML]:
        """
        Create the complete virtual try-on interface.
        """
        sidebar = self.create_sidebar()
        
        # Extract components for event handling
        photo_upload = None
        upload_btn = None
        tryon_btn = None
        results_display = None
        
        # Find components in the sidebar
        for component in sidebar.children:
            if hasattr(component, 'children'):
                for child in component.children:
                    if isinstance(child, gr.File):
                        photo_upload = child
                    elif isinstance(child, gr.Button):
                        if "Use This Photo" in str(child.value):
                            upload_btn = child
                        elif "Try On Items" in str(child.value):
                            tryon_btn = child
                    elif isinstance(child, gr.HTML):
                        results_display = child
        
        return sidebar, photo_upload, upload_btn, tryon_btn, results_display
    
    def get_photo_data(self) -> Optional[str]:
        """
        Get the current uploaded photo data.
        """
        return self.current_photo
    
    def clear_results(self):
        """
        Clear current try-on results.
        """
        self.tryon_results = {}
    
    def set_results(self, results: Dict[str, Any]):
        """
        Set new try-on results.
        """
        self.tryon_results = results

# Global instance for the UI
virtual_tryon_ui = VirtualTryOnUI()
