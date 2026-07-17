#
#import lmstudio as lms
#model = lms.llm("gemma-3-1b-it")
#result = model.respond("What time is now?")
#print(result)
import lmstudio as lms

main_model_key = "qwen2.5-coder-14b-instruct"
draft_model_key = "qwen2.5-coder-0.5b-instruct"

model = lms.llm(main_model_key)
prediction_stream = model.respond_stream(
    #"What are the prime numbers between 0 and 100?",
    #"What is the capital of Paris?", # :)
    "What is the capital of France?",
    config={
        "draftModel": draft_model_key,
    }
)
for fragment in prediction_stream:
    print(fragment.content, end="", flush=True)
print() # Advance to a new line at the end of the response

stats = prediction_stream.result().stats
print(f"Accepted {stats.accepted_draft_tokens_count}/{stats.predicted_tokens_count} tokens")
