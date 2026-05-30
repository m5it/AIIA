import lmstudio as lms

main_model_key = "qwen2.5-coder-14b-instruct"
draft_model_key = "qwen2.5-coder-0.5b-instruct"

model = lms.llm(main_model_key)
result = model.respond(
    #"What are the prime numbers between 0 and 100?",
    #"What is the capital of Paris?", # :)
    "What is the capital of France?",
    config={
        "draftModel": draft_model_key,
    }
)

print(result)
stats = result.stats
print(f"Accepted {stats.accepted_draft_tokens_count}/{stats.predicted_tokens_count} tokens")
