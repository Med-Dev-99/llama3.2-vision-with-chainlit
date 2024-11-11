import ollama

with open('/home/meddev/Pictures/perso_data/WhatsApp Image 2024-10-21 at 10.00.47.jpeg', 'rb') as file:
  response = ollama.chat(
    model='llama3.2-vision',
    messages=[
      {
        'role': 'user',
        'content': 'What is in this image?',
        'images': [file.read()],
      },
    ],
  )

print(response['message']['content'])