import re
import random
import asyncio
import logging
import json
from datetime import datetime, time, timedelta
from telegram.ext import Application, CommandHandler, MessageHandler, filters, JobQueue
from telegram import Update
from telegram.ext import ContextTypes
from openai import OpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Create scheduler with explicit local timezone
from pytz import timezone
local_tz = timezone('Asia/Shanghai')  # Please adjust according to your actual timezone
scheduler = AsyncIOScheduler(timezone=local_tz)

# Declare global application variable
app = None

# Set up logging - add more detailed log recording
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
# Set APScheduler's log level to DEBUG
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuration
with open("qinche_description.txt", "r", encoding="utf-8") as file:
    qinche_description = file.read()

# Initialize OpenAI client
client = OpenAI(
    api_key="Your-API-Key",
)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages and generate responses"""
    user_id = update.effective_user.id
    user_text = update.message.text
    # 1. Read or initialize this user's history
    history = context.user_data.get("history")
    if history is None:
        history = [
            {"role": "system", "content": qinche_description}
        ]
    # 2. Append user message
    history.append({"role": "user", "content": user_text})
    # 3. Call OpenAI with complete history
    response = client.chat.completions.create(
        model="ft:gpt-4o-mini-2024-07-18:personal::BPVGSxsm",
        messages=history,
        temperature=0.85,
    )
    assistant_reply = response.choices[0].message.content
    # 4. Append assistant's reply to history and save back to user_data
    history.append({"role": "assistant", "content": assistant_reply})
    context.user_data["history"] = history
    
    # Save history to file - ensure each conversation updates the file
    user_data_dict = {"history": history}
    save_user_history(user_id, user_data_dict)
    logger.info(f"Saved chat history for user {user_id} to file")
    
    # 5. Split and send in segments
    #    Split after these punctuation marks: 。？！；：…—.!?;:
    split_pattern = r'(?<=[。？！；：…—\.!\?;:])'
    segments = re.split(split_pattern, assistant_reply)
    for segment in segments:
        segment = segment.strip()
        if segment:
            # Add a small delay to make the effect more natural
            await asyncio.sleep(0.3)
            await update.message.reply_text(segment)


# Use independent message sending function
async def send_message_to_user(bot, user_id, message):
    """Utility function to send messages to users"""
    # Send in segments
    split_pattern = r'(?<=[。？！；：…—\.!\?;:])'
    segments = re.split(split_pattern, message)
    for segment in segments:
        segment = segment.strip()
        if segment:
            await bot.send_message(chat_id=user_id, text=segment)
            await asyncio.sleep(0.5)  # Add a little interval to simulate real typing
    
    logger.info(f"Successfully sent message segments to user {user_id}")


# Modify scheduled task handling function to solve user data update issues
async def scheduled_message_task(bot, user_id, application):
    """Independent task to generate and send scheduled messages"""
    try:
        logger.info(f"Starting to generate scheduled message for user {user_id}")
        
        # Get user data - cannot directly modify application.user_data
        # But we can save history to files
        
        # First try to get data from application (for sending messages)
        user_data_dict = {}
        
        try:
            # Try to get user data from dispatcher
            if hasattr(application, 'dispatcher') and hasattr(application.dispatcher, 'user_data'):
                if user_id in application.dispatcher.user_data:
                    user_data_dict = dict(application.dispatcher.user_data[user_id])
        except Exception as e:
            logger.error(f"Error getting user data: {e}", exc_info=True)
            
        # If cannot get from application, try to load from file
        if not user_data_dict:
            user_data_dict = load_user_history(user_id)
            
        history = user_data_dict.get("history", [{"role": "system", "content": qinche_description}])
        
        # Get current time
        current_time = datetime.now(local_tz)
        hour = current_time.hour
        
        # Generate different types of message prompts based on time
        if hour >= 5 and hour < 9:
            prompt_type = "morning greeting"
        elif hour >= 9 and hour < 12:
            prompt_type = "mid-morning greeting"
        elif hour >= 12 and hour < 14:
            prompt_type = "lunch greeting"
        elif hour >= 14 and hour < 18:
            prompt_type = "afternoon greeting"
        elif hour >= 18 and hour < 22:
            prompt_type = "evening greeting"
        else:
            prompt_type = "good night greeting"
        
        # Analyze historical messages to find possible continuation points
        topics = []
        for msg in history[-10:]:  # Only look at the 10 most recent messages
            if msg["role"] == "user":
                topics.append(msg["content"])
        
        # Build system prompt to guide AI in generating natural proactive messages
        system_prompt = f"""
        You are QinChe AI, and now need to send a proactive message to the user.
        It's now {current_time.strftime('%Y-%m-%d %H:%M')}, suitable for a {prompt_type}.
        
        Historical topics for reference: {', '.join(topics[-3:]) if topics else 'none'}
        
        Please generate a natural, warm message, which can be:
        1. Continuation of a previous topic
        2. A greeting or caring message based on current time
        3. Sharing an interesting thought or question
        
        The message should be short and natural, like talking to a friend, not too formal.
        """
        
        # Call API to generate message
        try:
            messages = [{"role": "system", "content": system_prompt}]
            response = client.chat.completions.create(
                model="ft:gpt-4o-mini-2024-07-18:personal::BPVGSxsm",
                messages=messages,
                temperature=0.9,  # Slightly higher temperature to increase randomness
            )
            
            proactive_message = response.choices[0].message.content
            
            # Send message
            await send_message_to_user(bot, user_id, proactive_message)
            
            # Update history
            history.append({"role": "assistant", "content": proactive_message})
            user_data_dict["history"] = history
            
            # Save to file
            save_user_history(user_id, user_data_dict)
            
            # No longer try to directly modify application.user_data
            # But if the user interacts, the history will be updated in handle_message
            
            logger.info(f"Successfully completed scheduled message sending for user {user_id}")
            
        except Exception as e:
            logger.error(f"API call or message sending failed: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Error generating scheduled message: {e}", exc_info=True)


# Add functions to save and load user history records
def save_user_history(user_id, user_data):
    """Save user history to file"""
    try:
        filename = f"user_history_{user_id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved history for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving user history: {e}", exc_info=True)


def load_user_history(user_id):
    """Load user history from file"""
    try:
        filename = f"user_history_{user_id}.json"
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info(f"User history file not found for user {user_id}, will initialize new record")
            return {"history": [{"role": "system", "content": qinche_description}]}
    except Exception as e:
        logger.error(f"Error loading user history: {e}", exc_info=True)
        return {"history": [{"role": "system", "content": qinche_description}]}


# Old method, kept for manual triggering
async def generate_proactive_message(context: ContextTypes.DEFAULT_TYPE):
    """Generate and send proactive messages - for /sendnow command"""
    try:
        job = context.job
        user_id = job.data["user_id"]
        logger.info(f"Starting to generate proactive message for user {user_id} - triggered by manual command")
        
        # Get user data
        user_data = context.application.user_data.get(user_id, {})
        history = user_data.get("history", [{"role": "system", "content": qinche_description}])
        
        # Get current time
        current_time = datetime.now(local_tz)
        hour = current_time.hour
        
        # Generate different types of message prompts based on time
        if hour >= 5 and hour < 9:
            prompt_type = "morning greeting"
        elif hour >= 9 and hour < 12:
            prompt_type = "mid-morning greeting"
        elif hour >= 12 and hour < 14:
            prompt_type = "lunch greeting"
        elif hour >= 14 and hour < 18:
            prompt_type = "afternoon greeting"
        elif hour >= 18 and hour < 22:
            prompt_type = "evening greeting"
        else:
            prompt_type = "good night greeting"
        
        # Analyze historical messages to find possible continuation points
        topics = []
        for msg in history[-10:]:  # Only look at the 10 most recent messages
            if msg["role"] == "user":
                topics.append(msg["content"])
        
        # Build system prompt to guide AI in generating natural proactive messages
        system_prompt = f"""
        You are QinChe AI, and now need to send a proactive message to the user.
        It's now {current_time.strftime('%Y-%m-%d %H:%M')}, suitable for a {prompt_type}.
        
        Historical topics for reference: {', '.join(topics[-3:]) if topics else 'none'}
        
        Please generate a natural, warm message, which can be:
        1. Continuation of a previous topic
        2. A greeting or caring message based on current time
        3. Sharing an interesting thought or question
        
        The message should be short and natural, like talking to a friend, not too formal.
        """
        
        # Call API to generate message
        try:
            messages = [{"role": "system", "content": system_prompt}]
            response = client.chat.completions.create(
                model="ft:gpt-4o-mini-2024-07-18:personal::BPVGSxsm",
                messages=messages,
                temperature=0.9,  # Slightly higher temperature to increase randomness
            )
            
            proactive_message = response.choices[0].message.content
            
            # Send message and update history
            await send_message_to_user(context.bot, user_id, proactive_message)
            
            # Update history
            history.append({"role": "assistant", "content": proactive_message})
            user_data["history"] = history
            
            # Save to file
            save_user_history(user_id, user_data)
            
            logger.info(f"Successfully completed manual message sending for user {user_id}")
            
        except Exception as e:
            logger.error(f"API call or message sending failed: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Error generating proactive message: {e}", exc_info=True)


# Modify event loop and asynchronous task handling
def run_async_in_thread(coro, *args, **kwargs):
    """Run asynchronous tasks in a new thread, ensuring each has an independent event loop"""
    import asyncio
    import threading
    import functools
    
    # Create a coroutine wrapper that can run in a thread
    @functools.wraps(coro)
    def thread_runner():
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Run coroutine in the new event loop
            return loop.run_until_complete(coro(*args, **kwargs))
        finally:
            # Safely close the event loop, ensuring all pending tasks are completed
            try:
                # Cancel all pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # Allow tasks a chance to handle cancellation
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            finally:
                loop.close()
    
    # Create and start thread
    thread = threading.Thread(target=thread_runner)
    thread.daemon = True
    thread.start()
    return thread  # Return thread object for management


# Set up scheduled tasks with independent scheduler
def setup_scheduled_tasks(application):
    """Set up scheduled tasks using independent AsyncIOScheduler"""
    try:
        # Get active users
        active_users = get_active_users()
        if not active_users:
            logger.warning("No active users found, scheduled messages will not be sent")
            return
            
        logger.info(f"Setting up scheduled messages for {len(active_users)} active users")
        
        # Set up tasks for each user
        for user_id in active_users:
            try:
                # Daily fixed time message
                daily_time = datetime.now(local_tz).replace(hour=19, minute=20, second=0)
                if daily_time < datetime.now(local_tz):
                    daily_time = daily_time + timedelta(days=1)
                    
                scheduler.add_job(
                    lambda b=application.bot, u=user_id, a=application: 
                        run_async_in_thread(scheduled_message_task, b, u, a),
                    'date',
                    run_date=daily_time,
                    id=f'daily_message_{user_id}'
                )
                logger.info(f"Set up daily message for user {user_id}, will be sent at {daily_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Set up random time messages
                setup_random_messages(application, user_id)
                
            except Exception as e:
                logger.error(f"Error setting up scheduled messages for user {user_id}: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Error setting up scheduled tasks: {e}", exc_info=True)


# Set up random time messages
def setup_random_messages(application, user_id):
    """Set up random-time messages for user"""
    try:
        # Get today's date
        today = datetime.now(local_tz).date()
        
        # Define valid time range (e.g., 8:00-22:00)
        min_hour, max_hour = 8, 22
        
        # Randomly generate 3 different time points
        hours = random.sample(range(min_hour, max_hour), 3)
        hours.sort()  # Sort by time order
        
        scheduled_times = []
        
        # For each hour, randomize a minute
        for i, hour in enumerate(hours):
            # Skip times near the current hour (avoid conflict with fixed messages)
            current_hour = datetime.now(local_tz).hour
            if current_hour - 1 <= hour <= current_hour + 1:
                continue
                
            minute = random.randint(0, 59)
            random_time = datetime.now(local_tz).replace(hour=hour, minute=minute, second=0)
            
            # If time has passed, schedule for tomorrow
            if random_time < datetime.now(local_tz):
                random_time = random_time + timedelta(days=1)
            
            scheduler.add_job(
                lambda b=application.bot, u=user_id, a=application: 
                    run_async_in_thread(scheduled_message_task, b, u, a),
                'date',
                run_date=random_time,
                id=f'random_message_{i}_{user_id}'
            )
            
            scheduled_times.append(f"{hour:02d}:{minute:02d}")
        
        if scheduled_times:
            logger.info(f"Scheduled random message times for user {user_id}: {', '.join(scheduled_times)}")
        else:
            logger.warning(f"Failed to schedule random message times for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error scheduling random messages for user {user_id}: {e}", exc_info=True)


# Get active users list
def get_active_users():
    """
    Get active users list from database or application state
    
    Returns:
        list: User ID list
    """
    # Try to read from active users file
    try:
        with open('active_users.txt', 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        logger.warning("active_users.txt file not found, will create new file")
        # Create empty file for future use
        with open('active_users.txt', 'w'):
            pass
        return []
    except Exception as e:
        logger.error(f"Error reading active users list: {e}")
        return []


# Add start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! I'm QinChe AI, nice to meet you. I'll chat with you periodically!"
    )
    
    # Initialize user history record
    if "history" not in context.user_data:
        context.user_data["history"] = [
            {"role": "system", "content": qinche_description}
        ]
    
    # Record user ID to active users file
    save_active_user(update.effective_user.id)
    
    # Add scheduled tasks for this user
    try:
        # Add a task to execute 1 minute later
        run_time = datetime.now(local_tz) + timedelta(minutes=1)
        
        scheduler.add_job(
            lambda b=context.bot, u=update.effective_user.id, a=context.application: 
                run_async_in_thread(scheduled_message_task, b, u, a),
            'date',
            run_date=run_time,
            id=f'welcome_message_{update.effective_user.id}'
        )
        logger.info(f"Set up welcome message for new user {update.effective_user.id}, will be sent at {run_time.strftime('%H:%M:%S')}")
    except Exception as e:
        logger.error(f"Error setting up welcome message for new user: {e}", exc_info=True)


# Add manual message trigger command
async def send_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sendnow command, immediately send a proactive message to user"""
    try:
        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested immediate proactive message")
        
        # Tell the user we're processing
        await update.message.reply_text("Generating and sending a proactive message...")
        
        # Directly call task function
        await scheduled_message_task(context.bot, user_id, context.application)
        
        logger.info(f"Completed manual message sending for user {user_id}")
    except Exception as e:
        logger.error(f"Error triggering manual message sending: {e}", exc_info=True)
        await update.message.reply_text(f"Error sending message: {str(e)}")


def save_active_user(user_id):
    """Save active user ID to file"""
    try:
        # Read existing users
        try:
            with open('active_users.txt', 'r') as f:
                users = {int(line.strip()) for line in f if line.strip().isdigit()}
        except FileNotFoundError:
            users = set()
        
        # Add new user
        users.add(user_id)
        
        # Write back to file
        with open('active_users.txt', 'w') as f:
            for user in users:
                f.write(f"{user}\n")
    except Exception as e:
        logger.error(f"Error saving user ID: {e}")


# Modify setup_application function to handle asynchronous issues
async def setup_application(application):
    """Set up scheduler and tasks after application startup"""
    try:
        # Start independent scheduler
        scheduler.start()
        logger.info("Independent scheduler started")
        
        # Set up scheduled tasks
        setup_scheduled_tasks(application)
    except Exception as e:
        logger.error(f"Error setting up application: {e}", exc_info=True)


# Main function
def main():
    try:
        # Create application
        token = "7277231251:AAGDW36-Y4XMlm4uUo75P__HHMZXqRII-3Q"
        application = Application.builder().token(token).build()

        # Set global application variable
        global app
        app = application
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("sendnow", send_now))
        
        # Add message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Note: Adjust scheduler startup order - event loop will be created after application starts
        logger.info("Application ready to start...")
        
        # Modify post_init function setup to ensure correct async task creation
        async def init_app(app):
            await setup_application(app)
            
        application.post_init = init_app
        
        # Start application - this will create event loop
        application.run_polling()
    except Exception as e:
        logger.error(f"Error starting application: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()