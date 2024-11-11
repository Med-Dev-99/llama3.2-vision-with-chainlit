# ui.py
import chainlit as cl
import ollama
import base64
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import io


executor = ThreadPoolExecutor(max_workers=1)

def resize_image(image_data, max_size=(512, 512)):
    """Resize the image to reduce processing time."""
    with Image.open(io.BytesIO(image_data)) as img:
        img.thumbnail(max_size)
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        return byte_arr.getvalue()

def analyze_image_with_ollama(image_base64):
    """Run Ollama analysis in a separate thread"""
    try:
        print("Starting analysis with ollama.chat...")
        response = ollama.chat(
            model='llama3.2-vision',
            messages=[{
                'role': 'user',
                'content': 'Describe this image briefly.',
                'images': [image_base64],
            }],
            stream=False,
            options={
                "temperature": 0.7,
                "num_predict": 500,  
            }
        )
        print("Received response from ollama.")
        return response
    except Exception as e:
        print(f"Ollama error: {str(e)}")
        raise e

def analyze_image_with_retries(image_base64, max_retries=3):
    """Retry Ollama analysis if it fails."""
    for attempt in range(max_retries):
        try:
            return analyze_image_with_ollama(image_base64)
        except Exception as e:
            print(f"Retry {attempt + 1}/{max_retries} failed. Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise e

@cl.on_chat_start
async def start():
    await cl.Message(
        content="Welcome! Please send an image and I'll analyze it for you."
    ).send()

@cl.on_message
async def main(message: cl.Message):
    image_elements = message.elements
    
    if not image_elements:
        await cl.Message(content="Please provide an image to analyze.").send()
        return
        
    for image in image_elements:
        try:
            # Show processing message
            processing_msg = cl.Message(content="Processing image... (this may take up to 60 seconds)")
            await processing_msg.send()

            # Get image content and resize it
            if image.path:
                with open(image.path, 'rb') as file:
                    image_data = file.read()
            else:
                image_data = image.content

            # Resize the image to optimize processing
            resized_image_data = resize_image(image_data)
            image_base64 = base64.b64encode(resized_image_data).decode('utf-8')

            # Run analysis in thread pool with increased timeout and retries
            try:
                loop = asyncio.get_event_loop()
                future = loop.run_in_executor(executor, analyze_image_with_retries, image_base64)
                
                # Wait for the result with a 60-second timeout
                response = await asyncio.wait_for(future, timeout=60.0)
                
                # Process successful response
                if isinstance(response, dict) and 'message' in response:
                    analysis_text = response['message'].get('content', 'No analysis available')
                else:
                    analysis_text = "Unexpected response format"
                
                # Remove processing message
                await processing_msg.remove()
                
                # Send final response with image
                await cl.Message(
                    content=f"Analysis:\n\n{analysis_text}",
                    elements=[
                        cl.Image(
                            name="analyzed_image",
                            content=resized_image_data,
                            display="inline"
                        )
                    ]
                ).send()
                
            except asyncio.TimeoutError:
                await processing_msg.remove()
                await cl.Message(
                    content="⚠️ Analysis took too long. Please try again with a simpler image or wait a moment."
                ).send()
                
            except Exception as e:
                await processing_msg.remove()
                error_message = f"Error during analysis: {str(e)}"
                print(error_message)
                await cl.Message(content=error_message).send()
                
        except Exception as e:
            await cl.Message(
                content=f"❌ Error processing image: {str(e)}"
            ).send()

if __name__ == "__main__":
    print("Starting Chainlit application...")
