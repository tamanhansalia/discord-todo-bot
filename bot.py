import discord
from discord.ext import commands
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Setup intents
intents = discord.Intents.default()
intents.message_content = True  # REQUIRED - Enable in Discord Developer Portal
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
    
    # Parse command
    parts = args.split()
    if not parts:
        return
    
    command = parts[0].lower()
    
    # !todo add <task> - Add task for yourself
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
            "status": "pending"  # pending, completed, approved
        })
        save_todos(todos)
        await ctx.send(f"✅ Task added for yourself: **{task}** (ID: {new_id})")
    
    # !todo addto @user <task> - Assign task to another user
    elif command == 'addto':
        if len(parts) < 3:
            await ctx.send("❌ Usage: `!todo addto @user <task>`")
            return
        
        # Extract mentioned user
        mentioned_user = None
        for user in ctx.message.mentions:
            mentioned_user = user
            break
        
        if not mentioned_user:
            await ctx.send("❌ Please mention a user to assign the task to. Example: `!todo addto @john Fix the bug`")
            return
        
        # Get task description (everything after the mention)
        task_parts = parts[1:]
        # Remove the mention from task_parts
        task_parts = [p for p in task_parts if not p.startswith('<@')]
        task = ' '.join(task_parts)
        
        if not task:
            await ctx.send("❌ Please specify a task. Example: `!todo addto @john Review the code`")
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
            "status": "assigned",  # assigned, completed, approved
            "assigned_date": time.time()
        })
        save_todos(todos)
        
        # Also add to assigner's record for tracking
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
        await mentioned_user.send(f"📌 You've been assigned a task by {ctx.author.name}: **{task}**\nUse `!todo assigned` to see all your assigned tasks.")
    
    # !todo assigned - Show tasks assigned to you by others
    elif command == 'assigned':
        todos = load_todos()
        user_id = str(ctx.author.id)
        tasks = todos.get(user_id, [])
        
        # Filter tasks assigned by others (not self-assigned)
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
    
    # !todo assignedby - Show tasks you assigned to others
    elif command == 'assignedby':
        todos = load_todos()
        assigned_tasks = []
        
        for user_id, tasks in todos.items():
            for task in tasks:
                if task.get('assigned_by') == ctx.author.id and task.get('assigned_to'):
                    assigned_tasks.append({
                        "id": task['id'],
                        "text": task['text'],
                        "assigned_to": task['assigned_to'],
                        "completed": task.get('completed', False),
                        "status": task.get('status', 'assigned')
                    })
        
        if not assigned_tasks:
            await ctx.send("📭 You haven't assigned any tasks to others yet.")
            return
        
        embed = discord.Embed(title="📋 Tasks You've Assigned", color=0x00AE86)
        
        for task in assigned_tasks:
            status_emoji = "✅" if task['completed'] else "⏳"
            embed.add_field(
                name=f"{status_emoji} Task ID: {task['id']}",
                value=f"To: <@{task['assigned_to']}>\nTask: {task['text']}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    # !todo list - Show your personal tasks
    elif command == 'list':
        todos = load_todos()
        user_id = str(ctx.author.id)
        tasks = todos.get(user_id, [])
        # Filter out assigned tasks (only show self-created)
        personal_tasks = [t for t in tasks if not t.get('assigned_by') or t.get('assigned_by') == ctx.author.id]
        pending = [t for t in personal_tasks if not t["completed"]]
        
        if not pending:
            await ctx.send("📭 You have no pending tasks. Add one with `!todo add <task>`")
            return
        
        desc = "\n".join([f"**{t['id']}** – {t['text']}" for t in pending])
        embed = discord.Embed(title="📋 Your Personal To-Do List", description=desc, color=0x00AE86)
        await ctx.send(embed=embed)
    
    # !todo complete <id> - Mark an assigned task as complete (for the person it was assigned to)
    elif command == 'complete':
        if len(parts) < 2:
            await ctx.send("❌ Please provide a task ID. Example: `!todo complete 1234567890`")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await ctx.send("❌ Invalid task ID. Please use a number.")
            return
        
        todos = load_todos()
        user_id = str(ctx.author.id)
        tasks = todos.get(user_id, [])
        
        for t in tasks:
            if t["id"] == task_id and t.get('assigned_by'):
                if t.get("completed"):
                    await ctx.send("✅ Task already marked as completed.")
                    return
                
                t["completed"] = True
                t["status"] = "completed"
                save_todos(todos)
                
                # Notify the person who assigned the task
                assigner_id = str(t.get('assigned_by'))
                if assigner_id in todos:
                    await ctx.send(f"🎉 Task marked as completed: **{t['text']}**\nThe person who assigned this (<@{assigner_id}>) has been notified.")
                    
                    # Try to DM the assigner
                    assigner = await bot.fetch_user(int(assigner_id))
                    if assigner:
                        await assigner.send(f"📢 {ctx.author.name} has completed the task you assigned: **{t['text']}**\nUse `!todo review {task_id}` to review and approve.")
                return
        
        await ctx.send("❌ Task not found or it's not a task assigned to you.")
    
    # !todo review <id> - Review and approve a completed task (for the assigner)
    elif command == 'review':
        if len(parts) < 2:
            await ctx.send("❌ Please provide a task ID. Example: `!todo review 1234567890`")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await ctx.send("❌ Invalid task ID. Please use a number.")
            return
        
        todos = load_todos()
        
        # Search through all users to find the task
        found_task = None
        found_user_id = None
        
        for user_id, tasks in todos.items():
            for task in tasks:
                if task["id"] == task_id and task.get('assigned_by') == ctx.author.id:
                    found_task = task
                    found_user_id = user_id
                    break
            if found_task:
                break
        
        if not found_task:
            await ctx.send("❌ Task not found or you didn't assign this task.")
            return
        
        if not found_task.get("completed"):
            await ctx.send("⚠️ This task hasn't been marked as completed yet.")
            return
        
        found_task["status"] = "approved"
        save_todos(todos)
        
        await ctx.send(f"✅ Task approved and closed: **{found_task['text']}**\nGreat work! Task completed by <@{found_user_id}>.")
        
        # Notify the person who completed the task
        assignee = await bot.fetch_user(int(found_user_id))
        if assignee:
            await assignee.send(f"🎉 {ctx.author.name} has approved your completed task: **{found_task['text']}**")
    
    # !todo check <id> - Mark personal task as done
    elif command == 'check':
        if len(parts) < 2:
            await ctx.send("❌ Please provide a task ID. Example: `!todo check 1234567890`")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await ctx.send("❌ Invalid task ID. Please use a number.")
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
        await ctx.send("❌ Task not found. Use `!todo list` to see your personal task IDs.")
    
    # !todo undo <id> - Unmark personal task
    elif command == 'undo':
        if len(parts) < 2:
            await ctx.send("❌ Please provide a task ID. Example: `!todo undo 1234567890`")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await ctx.send("❌ Invalid task ID. Please use a number.")
            return
        
        todos = load_todos()
        user_id = str(ctx.author.id)
        tasks = todos.get(user_id, [])
        for t in tasks:
            if t["id"] == task_id:
                if not t["completed"]:
                    await ctx.send("⚠️ Task is not completed yet.")
                    return
                t["completed"] = False
                save_todos(todos)
                await ctx.send(f"↩️ Unchecked: **{t['text']}**")
                return
        await ctx.send("❌ Task not found.")
    
    # !todo delete <id> - Delete task
    elif command == 'delete':
        if len(parts) < 2:
            await ctx.send("❌ Please provide a task ID. Example: `!todo delete 1234567890`")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await ctx.send("❌ Invalid task ID. Please use a number.")
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
    
    # !todo clear - Clear all personal tasks
    elif command == 'clear':
        todos = load_todos()
        user_id = str(ctx.author.id)
        # Only clear personal tasks, not assigned ones
        todos[user_id] = [t for t in todos.get(user_id, []) if t.get('assigned_by')]
        save_todos(todos)
        await ctx.send("🧹 All your personal tasks have been cleared.")
    
    else:
        await ctx.send(f"❌ Unknown command: {command}. Try `!todo help`")

bot.run(os.getenv("DISCORD_TOKEN"))