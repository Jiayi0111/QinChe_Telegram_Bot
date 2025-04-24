from openai import OpenAI
client = OpenAI(api_key="Your-API-Key")

# Upload the training file
with open("conversations.jsonl", "rb") as f:
    resp = client.files.create(file=f, purpose="fine-tune")

training_file_id = resp.id
print("File ID:", training_file_id)

ft = client.fine_tuning.jobs.create(
  model="gpt-4o-mini-2024-07-18",     # 或者支持微调的其他基础模型
  training_file=training_file_id,
#   n_epochs=3,
#   learning_rate_multiplier=0.05
    method={
        "type": "supervised",
        "supervised": {
            "hyperparameters": {"n_epochs": 3, "learning_rate_multiplier": 0.05, 'batch_size': 4},

        },
    },
)
print("Fine-tune Job ID:", ft.id)

import time
# Monitor the fine-tuning job status
while True:
    status = client.fine_tuning.jobs.retrieve(ft.id)
    print("Status:", status.status)
    if status.status in ("succeeded", "failed"):
        print("Fine-tuned Model Name:", status.fine_tuned_model)
        break
    time.sleep(30)