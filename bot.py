import discord
from discord.ext import commands
import json
import os
import time
from flask import Flask
from threading import Thread

# ========== KEEP-ALIVE WEB SERVER (Prevents Render from sleeping) ==========
app = Flask('')

@app.route('/')
def home():
    return '<h1>2PixelBlogs Discord Bot is running!</h1>'

@app.route('/health')
def health():
    return 'OK'

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    server = Thread(target=run_web)
    server.start()

# ========== DISCORD BOT CODE ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

TODO_FILE = 'todos.json'

def load_todos():
    if not os.path.exists(TODO_FILE):
        return {}
    with open(TODO_FILE, 'r') as f:
        return json.load(f)

def save_todos(todos):
    with open(TODO_FILE, 'w') as f:
        json.dump(todos, f, indent=2)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    print(f'✅ Bot is ready to use!')
    print(f'✅ Try typing: !todo help')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Try `!todo help` for list of commands.")
    else:
        await ctx.send(f"❌ Error: {error}")

@bot.command()
async def todo(ctx, *, args=None):
    if args is None or args == 'help':
        help_text = """
**📌 2PixelBlogs To-Do Bot Commands**

**Personal Tasks:**
`!todo add <task>` – Add a new task for yourself
`!todo list` – Show your pending tasks
`!todo check <id>` – Mark your task as done
`!todo undo <id>` – Unmark a completed task
`!todo delete <id>` – Delete a task
`!todo clear` – Delete all your tasks

**Assign Tasks to Others:**
`!todo addto @user <task>` – Assign a task to another user
`!todo assigned` – Show tasks assigned to you
`!todo assignedby` – Show tasks you assigned to others
`!todo complete <id>` – Mark an assigned task as done
`!todo review <id>` – Review/check someone's completed task

**Examples:**
`!todo add Write blog post for 2PixelBlogs`
`!todo addto @john Review the website design`
`!todo assigned`
`!todo complete 1234567890`
        """
        embed = discord.Embed(title="✅ To-Do Bot Help", description=help_text, color=0x00AE86)
        await ctx.send(embed=embed)
        return
    
    parts = args.split()
    if not parts:
        return
    
    command = parts[0].lower()
    
    if command == 'add':
        task = ' '.join(parts[1:])
        if not task:
            await ctx.send("❌ Please specify a task. Example: `!todo add Buy milk`")
            return
        
        todos = load_todos()
        user_id = str(ctx.author.id)
        if user_id not in todos:
            todos[user_id] = []
        new_id = int(time.time() * 1000)
        todos[user_id].append({
            "id": new_id, 
            "text": task, 
            "completed": False,
            "assigned_by": None,
            "assigned_to": None,
            "status": "pending"
        })
        save_todos(todos)
        await ctx.send(f"✅ Task added for yourself: **{task}** (ID: {new_id})")
    
    elif command == 'addto':
        if len(parts) < 3:
            await ctx.send("❌ Usage: `!todo addto @user <task>`")
            return
        
        mentioned_user = None
        for user in ctx.message.mentions:
            mentioned_user = user
            break
        
        if not mentioned_user:
            await ctx.send("❌ Please mention a user to assign the task to.")
            return
        
        task_parts = parts[1:]
        task_parts = [p for p in task_parts if not p.startswith('<@')]
        task = ' '.join(task_parts)
        
        if not task:
            await ctx.send("❌ Please specify a task.")
            return
        
        todos = load_todos()
        assigned_to_id = str(mentioned_user.id)
        
        if assigned_to_id not in todos:
            todos[assigned_to_id] = []
        
        new_id = int(time.time() * 1000)
        todos[assigned_to_id].append({
            "id": new_id,
            "text": task,
            "completed": False,
            "assigned_by": ctx.author.id,
            "assigned_by_name": ctx.author.name,
            "assigned_to": mentioned_user.id,
            "assigned_to_name": mentioned_user.name,
            "status": "assigned",
            "assigned_date": time.time()
        })
        save_todos(todos)
        
        user_id = str(ctx.author.id)
        if user_id not in todos:
            todos[user_id] = []
        todos[user_id].append({
            "id": new_id,
            "text": f"[ASSIGNED TO {mentioned_user.name}] {task}",
            "completed": False,
            "assigned_by": ctx.author.id,
            "assigned_to": mentioned_user.id,
            "status": "assigned",
            "task_type": "assigned"
        })
        save_todos(todos)
        
        await ctx.send(f"✅ Task assigned to {mentioned_user.mention}: **{task}** (ID: {new_id})")
        try:
            await mentioned_user.send(f"📌 You've been assigned a task by {ctx.author.name}: **{task}**\nUse `!todo assigned` to see all your assigned tasks.")
        except:
            pass
    
    elif command == 'assigned':
        todos = load_todos()
        user_id = str(ctx.author.id)
        tasks = todos.get(user_id, [])
        
        assigned_tasks = [t for t in tasks if t.get('assigned_by') and t.get('assigned_by') != ctx.author.id and not t.get('task_type') == 'assigned']
        
        if not assigned_tasks:
            await ctx.send("📭 You have no tasks assigned to you by others.")
            return
        
        pending = [t for t in assigned_tasks if not t.get('completed')]
        completed = [t for t in assigned_tasks if t.get('completed')]
        
        embed = discord.Embed(title="📋 Tasks Assigned to You", color=0x00AE86)
        
        if pending:
            pending_desc = "\n".join([f"**{t['id']}** – {t['text']} (by <@{t['assigned_by']}>)" for t in pending])
            embed.add_field(name="⏳ Pending", value=pending_desc, inline=False)
        
        if completed:
            completed_desc = "\n".join([f"**{t['id']}** – {t['text']} (by <@{t['assigned_by']}>)" for t in completed])
            embed.add_field(name="✅ Completed", value=completed_desc, inline=False)
        
        await ctx.send(embed=embed)
    
    elif command == 'list':
        todos = load_todos()
        user_id = str(ctx.author.id)
        tasks = todos.get(user_id, [])
        personal_tasks = [t for t in tasks if not t.get('assigned_by') or t.get('assigned_by') == ctx.author.id]
        pending = [t for t in personal_tasks if not t["completed"]]
        
        if not pending:
            await ctx.send("📭 You have no pending tasks. Add one with `!todo add <task>`")
            return
        
        desc = "\n".join([f"**{t['id']}** – {t['text']}" for t in pending])
        embed = discord.Embed(title="📋 Your Personal To-Do List", description=desc, color=0x00AE86)
        await ctx.send(embed=embed)
    
    elif command == 'check':
        if len(parts) < 2:
            await ctx.send("❌ Please provide a task ID.")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await ctx.send("❌ Invalid task ID.")
            return
        
        todos = load_todos()
        user_id = str(ctx.author.id)
        tasks = todos.get(user_id, [])
        for t in tasks:
            if t["id"] == task_id and not t.get('assigned_by'):
                if t["completed"]:
                    await ctx.send("✅ Task already completed.")
                    return
                t["completed"] = True
                save_todos(todos)
                await ctx.send(f"🎉 Completed: **{t['text']}**")
                return
        await ctx.send("❌ Task not found.")
    
    elif command == 'delete':
        if len(parts) < 2:
            await ctx.send("❌ Please provide a task ID.")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await ctx.send("❌ Invalid task ID.")
            return
        
        todos = load_todos()
        user_id = str(ctx.author.id)
        tasks = todos.get(user_id, [])
        for i, t in enumerate(tasks):
            if t["id"] == task_id:
                deleted = tasks.pop(i)
                save_todos(todos)
                await ctx.send(f"🗑️ Deleted: **{deleted['text']}**")
                return
        await ctx.send("❌ Task not found.")
    
    elif command == 'clear':
        todos = load_todos()
        user_id = str(ctx.author.id)
        todos[user_id] = [t for t in todos.get(user_id, []) if t.get('assigned_by')]
        save_todos(todos)
        await ctx.send("🧹 All your personal tasks have been cleared.")
    
    else:
        await ctx.send(f"❌ Unknown command: {command}. Try `!todo help`")

# ========== START THE BOT WITH KEEP-ALIVE ==========
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Error: DISCORD_TOKEN environment variable not set")
        print("Please add DISCORD_TOKEN in Render dashboard")
    else:
        print("✅ Token found, starting bot...")
        keep_alive()  # Starts the web server to keep bot alive
        bot.run(token)