## Project Overview: **QinChe AI – Personalized Telegram AI Companion with Scheduled Emotional Engagement**

**Project Name:** QinChe AI
**Platform:** Telegram
**Tech Stack:** Python, Telegram Bot API, OpenAI API (GPT-4o-mini fine-tuned model), APScheduler, asyncio
**Mode:** Long-term emotional companion, proactive interaction

### 📝 Description

**QinChe AI** is a custom-built Telegram chatbot that transcends typical user-initiated AI conversations. Unlike standard chatbots, QinChe AI offers *persistent memory*, *scheduled emotional engagement*, and *context-aware interactions* through a personalized, fine-tuned GPT-4o-mini model.

The system stores and continuously learns from each user's chat history, enabling it to deliver messages that feel emotionally intelligent, timely, and personally relevant. It uses a hybrid scheduling model (fixed + randomized) to send natural, spontaneous check-ins or thoughtful messages throughout the day.

### 🛠️ Key Features

| Feature                           | Description                                                                                                                       |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Persistent User Memory**        | Stores each user's chat history (`user_history_{id}.json`) for long-term emotional context.                                       |
| **Scheduled Messaging**           | Proactively sends personalized messages at appropriate times (e.g., morning greetings, bedtime reflections).                      |
| **Intelligent Message Splitting** | Splits responses at sentence boundaries to create a more natural messaging feel.                                                  |
| **Fine-Tuned GPT Model**          | Uses a fine-tuned GPT-4o-mini model with a personality description (`qinche_description.txt`) for consistency and emotional tone. |
| **Independent Scheduler**         | Employs `APScheduler` to deliver both fixed-time and random-time messages per user.                                               |
| **Human-like Warmth**             | Uses time-of-day cues and recent chat topics to simulate emotional intelligence and care.                                         |

---

## 🔍 Comparison: How QinChe AI is Better Than Normal AI Conversation Tools

| **Aspect**                    | **QinChe AI**                                                                           | **Typical Chatbot / ChatGPT Bot**                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Memory**                    | Saves and uses persistent user history for every interaction                            | Stateless by default (e.g., resets every session unless API manages state manually) |
| **Proactivity**               | Sends messages *without user prompt* using fixed and random schedules                   | Only responds when prompted by user                                                 |
| **Time-Aware Tone**           | Adjusts language and intent based on time (morning, lunch, night, etc.)                 | No temporal awareness unless explicitly prompted                                    |
| **Fine-Tuned Personality**    | Built on a custom prompt (`qinche_description.txt`) and refined tone per use case       | Generic assistant tone or requires manual re-prompting                              |
| **File-based Fallbacks**      | Uses local JSON history files to restore memory when Telegram `context.user_data` fails | Most bots lose continuity when restarted                                            |
| **Custom Greeting Generator** | Uses recent conversation topics to create engaging follow-ups                           | No follow-up unless explicitly referenced by user                                   |
| **Natural Messaging Flow**    | Splits long messages into segments with delays to mimic real human texting              | Sends full block of text at once, unnatural pacing                                  |
| **Scalable and Extensible**   | Easily adds support for more users via `active_users.txt` and modular scheduler setup   | Often hard-coded, lacks multi-user scalability                                      |

---

## 📈 Use Cases

* **Emotional AI Companion** for users seeking connection and regular, non-intrusive companionship
* **Mental Health Support Tool** that checks in with users proactively
* **Otome/Character-based AI Simulation** with an evolving, familiar personality
* **Telegram Marketing Bot with Memory** that retains personalized leads and engages meaningfully over time
