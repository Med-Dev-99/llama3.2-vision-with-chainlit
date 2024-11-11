import ollama

with open('image.jpg', 'rb') as file:
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