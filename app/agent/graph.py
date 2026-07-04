from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Checkpointer

from app.agent.prompts import build_system_prompt
from app.agent.rag import search_faq
from app.agent.tools import BOOKING_TOOLS
from app.config import get_settings


def build_graph(
    checkpointer: Checkpointer = None, llm: BaseChatModel | None = None
) -> CompiledStateGraph:
    settings = get_settings()
    tools = [*BOOKING_TOOLS, search_faq]
    llm = llm or init_chat_model(settings.llm_model)
    llm_with_tools = llm.bind_tools(tools)

    async def agent(state: MessagesState) -> MessagesState:
        system = SystemMessage(build_system_prompt(settings))
        response = await llm_with_tools.ainvoke([system, *state["messages"]])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)
