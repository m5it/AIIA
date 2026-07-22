import ollama
 
response = ollama.chat(model='gemma4:26b', messages=[
  {'role': 'user', 'content': 'Why is the sky blue?'},
])
 
# The usage information is inside the response
prompt_tokens = response.get('prompt_eval_count', 0)
response_tokens = response.get('eval_count', 0)
total_tokens = prompt_tokens + response_tokens
 
print(f"Prompt tokens: {prompt_tokens}")
print(f"Response tokens: {response_tokens}")
print(f"Total tokens: {total_tokens}")
