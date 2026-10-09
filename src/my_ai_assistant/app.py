"""Gradio app for the Sidekick. Run with: uv run app.py"""

import sys

if sys.platform == "win32":
    import subprocess
    from functools import partial

    import langchain_mcp_adapters.sessions as mcp_sessions

    mcp_sessions.stdio_client = partial(
        mcp_sessions.stdio_client,
        errlog=subprocess.DEVNULL,
    )

import html

import gradio as gr

from . import styles
from .sidekick import Sidekick

LAUNCH_STYLE = {"theme": styles.THEME, "css": styles.CSS, "head": styles.JS}

HEADER = """
<div id="header">
    <div class="context-label">Your personal web search-assistance</div>
    <h1>AI Assistant</h1>
    <div class="brand-bar"></div>
</div>
"""


def render_todos(todos):
    if not todos:
        items = '<div class="placeholder">The AI-Assistant will write its plan here as it works</div>'
    else:
        items = "<ul>" + "".join(
            f'<li class="{todo["status"]}"><span class="mark"></span>{html.escape(todo["content"])}</li>'
            for todo in todos
        ) + "</ul>"
    return f"<h3>Plan</h3>{items}"


async def setup():
    sidekick = Sidekick()
    await sidekick.setup()
    return sidekick, gr.update(interactive=True)


async def process_message(sidekick, message, success_criteria, history):
    if sidekick is None:  # the user clicked before setup finished bringing up the MCP servers
        return history, gr.update(visible=False), sidekick
    results = await sidekick.run_turn(message, success_criteria, history)
    return results, gr.update(visible=sidekick.paused), sidekick


async def approve(sidekick, history):
    results = await sidekick.resume(history)
    return results, gr.update(visible=sidekick.paused), sidekick


def watch_todos(sidekick):
    """Called by the timer. The timer is the plan panel's only writer: if a long-running
    event owned the panel as an output, Gradio would lock it as pending and live updates
    would not render while the Sidekick works."""
    return render_todos(sidekick.todos) if sidekick else render_todos([])


async def reset(sidekick):
    if sidekick:
        sidekick.cleanup()
    new_sidekick = Sidekick()
    await new_sidekick.setup()
    return "", "", None, gr.update(visible=False), new_sidekick


def free_resources(sidekick):
    if sidekick:
        sidekick.cleanup()


with gr.Blocks(title="AI Assistant") as ui:
    gr.HTML(HEADER)
    sidekick = gr.State(delete_callback=free_resources)

    with gr.Row():
        chatbot = gr.Chatbot(label="AI Assistant", height=320, scale=3, elem_id="chat")
        with gr.Column(scale=1):
            todos_panel = gr.HTML(render_todos([]), elem_id="plan-panel")
    with gr.Group(elem_id="ask-panel"):
        with gr.Row():
            message = gr.Textbox(show_label=False, placeholder="Your request to the AI Assistant")
        with gr.Row():
            success_criteria = gr.Textbox(show_label=False, placeholder="What are your success criteria?")
    with gr.Row():
        reset_button = gr.Button("Reset", elem_id="reset-button")
        approve_button = gr.Button("Approve and continue", visible=False, elem_id="approve-button")
        go_button = gr.Button("Go!", elem_id="go-button", interactive=False)

    timer = gr.Timer(1)

    ui.load(setup, [], [sidekick, go_button])
    timer.tick(watch_todos, [sidekick], [todos_panel], show_progress="hidden")
    message.submit(process_message, [sidekick, message, success_criteria, chatbot],
                   [chatbot, approve_button, sidekick])
    success_criteria.submit(process_message, [sidekick, message, success_criteria, chatbot],
                            [chatbot, approve_button, sidekick])
    go_button.click(process_message, [sidekick, message, success_criteria, chatbot],
                    [chatbot, approve_button, sidekick])
    approve_button.click(approve, [sidekick, chatbot], [chatbot, approve_button, sidekick])
    reset_button.click(reset, [sidekick], [message, success_criteria, chatbot, approve_button, sidekick])


def main():
    ui.launch(inbrowser=True, **LAUNCH_STYLE)


if __name__ == "__main__":
    main()
