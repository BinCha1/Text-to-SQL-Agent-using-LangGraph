import streamlit as st
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, TypedDict, List, Dict, Any, Optional
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode
from langgraph.errors import GraphRecursionError
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd
import sqlite3
from dotenv import load_dotenv

load_dotenv()

# ======================================================================
# Page Configuration
# ======================================================================
st.set_page_config(
    page_title="Text-to-SQL Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================================
# Logger Setup
# ======================================================================
def get_logger(name: str) -> logging.Logger:
    """Creates a logger that writes only to file: logger/agent.log"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers = []
    log_dir = Path("logger")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "agent.log"
    handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = logging.Formatter(
        fmt="[{asctime}] {levelname:8s} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

# ======================================================================
# SQL Agent Class
# ======================================================================
class State(TypedDict):
    messages: Annotated[list[HumanMessage | AIMessage | ToolMessage], add_messages]
    query_attempts: int
    final_answer: Optional[str]

class SQLAgent:
    def __init__(self, db_path: str, model_name: str = "llama-3.1-8b-instant", groq_api_key: Optional[str] = None):
        self.logger = get_logger("SQLAgent")
        start_init = datetime.now()

        self.connection_string = f"sqlite:///{db_path}"
        self.db = SQLDatabase.from_uri(self.connection_string)
        self.llm = ChatGroq(
            model=model_name,
            api_key=groq_api_key or os.getenv("GROQ_API_KEY"),
            temperature=0,
        )

        self.logger.info("🚀 Logger initialized. Starting SQLAgent setup...")
        self._setup_tools()
        self._setup_strong_prompts()
        self._build_graph()

        total_init_time = (datetime.now() - start_init).total_seconds()
        self.logger.info(f"✅ SQLAgent initialized successfully in {total_init_time:.2f}s")

    def _setup_tools(self):
        self.logger.info("🔧 Setting up SQL tools...")
        start_time = datetime.now()

        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        tools = toolkit.get_tools()
        self.list_tables_tool = next(t for t in tools if t.name == "sql_db_list_tables")
        self.get_schema_tool = next(t for t in tools if t.name == "sql_db_schema")

        @tool
        def db_query_tool(query: str) -> str:
            """Executes SELECT queries only. Blocks DML/DDL."""
            logger = get_logger("SQLAgent")
            logger.info(f"⚙️ Running db_query_tool with query: {query}")
            if not query.strip().upper().startswith("SELECT"):
                return "Error: Only SELECT queries are allowed."
            try:
                result = self.db.run_no_throw(query)
                logger.info(f"📊 Query result: {result}")
                return str(result) if result else "No results found."
            except Exception as e:
                logger.error(f"❌ Database error: {str(e)}")
                return f"Error: {str(e)}"

        self.db_query_tool = db_query_tool
        elapsed = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"✅ Tools ready in {elapsed:.2f}s")

    def _setup_strong_prompts(self):
        start_time = datetime.now()
        self.logger.info("🧠 Setting up prompts...")

        self.query_gen_prompt = ChatPromptTemplate.from_messages([
            ("system", """YOU ARE A STRICT SQL QUERY GENERATOR.

    Your ONLY job is to:
    1. Generate a SINGLE, VALID SQL SELECT query for the user's question
    2. Return ONLY the SQL query - no explanations, no markdown, no extra text
    3. Use proper table and column names from the schema
    4. Ensure the query is applicable to any table in the database, not just 'students'
    5. Use proper JOIN syntax if needed
    6. Use WHERE clauses for filtering

    Rules:
    - Output ONLY the SQL query
    - Start with SELECT
    - No markdown code blocks
    - No explanations before or after

    Example good output:
    SELECT email FROM students WHERE name = 'Nabin Gurung'

    Example good output (other table):
    SELECT course_name FROM courses WHERE department = 'Computer Science'

    Example bad output:
    Here's the query: ```sql SELECT...``` This will find..."""),
            ("placeholder", "{messages}")
        ])

        self.interpret_prompt = ChatPromptTemplate.from_messages([
            ("system", """YOU ARE A DATA ANALYST who explains query results in natural language.

Your job:
1. Read the SQL query result
2. Provide a clear, concise answer in natural language 
3. Be direct and helpful
4. If no results found, say so clearly

DO NOT:
- Show the SQL query
- Use technical jargon unnecessarily
- Add unnecessary details

Example:
Query result: [('nabin.gurung@example.com',)]
Good answer: "The email address is nabin.gurung@example.com"
Bad answer: "Based on the SQL query execution, the result shows that..."
"""),
            ("placeholder", "{messages}")
        ])

        elapsed = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"✅ Prompts ready in {elapsed:.2f}s")

    def _create_tool_node_with_fallback(self, tools: list) -> RunnableLambda:
        def handle_tool_error(state: Dict) -> Dict:
            self.logger.error("⚠️ Tool execution error encountered.")
            error = state.get("error")
            tool_calls = state.get("messages", [])[-1].tool_calls if state.get("messages") else []
            return {
                "messages": [
                    ToolMessage(content=f"Error: {repr(error)}", tool_call_id=tc["id"])
                    for tc in tool_calls
                ]
            }

        return ToolNode(tools).with_fallbacks([RunnableLambda(handle_tool_error)], exception_key="error")

    def _build_graph(self):
        self.logger.info("⚙️ Building workflow graph...")
        start_time = datetime.now()

        workflow = StateGraph(State)

        def first_tool_call(state: State) -> Dict:
            self.logger.info("🧩 Node: first_tool_call")
            return {
                "messages": [AIMessage(content="", tool_calls=[{
                    "name": "sql_db_list_tables",
                    "args": {},
                    "id": "init_001"
                }])],
                "query_attempts": 0,
                "final_answer": None
            }

        def model_get_schema(state: State) -> Dict:
            self.logger.info("🧩 Node: model_get_schema")
            return {"messages": [self.llm.bind_tools([self.get_schema_tool]).invoke(state["messages"])]}

        def query_gen_node(state: State) -> Dict:
            self.logger.info("🧩 Node: query_gen_node (Attempt %d)", state.get("query_attempts", 0) + 1)
            response = (self.query_gen_prompt | self.llm).invoke({"messages": state["messages"]})
            self.logger.info(f"🧾 Generated SQL: {response.content.strip()}")
            return {"messages": [response], "query_attempts": state.get("query_attempts", 0) + 1}

        def execute_query_node(state: State) -> Dict:
            self.logger.info("🧩 Node: execute_query_node")
            start_q = datetime.now()
            sql = state["messages"][-1].content.strip()
            try:
                result = self.db.run_no_throw(sql)
                content = str(result) if result else "No results found."
                elapsed = (datetime.now() - start_q).total_seconds()
                self.logger.info(f"✅ SQL executed in {elapsed:.2f}s")
                self.logger.info(f"📋 Query Result: {content}")
            except Exception as e:
                content = f"Error: {str(e)}"
                self.logger.error(f"❌ SQL execution failed: {str(e)}")
            return {"messages": [ToolMessage(content=content, tool_call_id="exec_001")]}

        def interpret_results_node(state: State) -> Dict:
            self.logger.info("🧩 Node: interpret_results_node")
            interp_start = datetime.now()
            interpretation = (self.interpret_prompt | self.llm).invoke({"messages": state["messages"]})
            elapsed = (datetime.now() - interp_start).total_seconds()
            self.logger.info(f"💬 Interpretation ready in {elapsed:.2f}s")
            self.logger.info(f"🧠 Final Answer: {interpretation.content.strip()}")
            return {"messages": [interpretation], "final_answer": interpretation.content}

        workflow.add_node("first_tool_call", first_tool_call)
        workflow.add_node("list_tables_tool", self._create_tool_node_with_fallback([self.list_tables_tool]))
        workflow.add_node("model_get_schema", model_get_schema)
        workflow.add_node("get_schema_tool", self._create_tool_node_with_fallback([self.get_schema_tool]))
        workflow.add_node("query_gen", query_gen_node)
        workflow.add_node("execute_query", execute_query_node)
        workflow.add_node("interpret_results", interpret_results_node)

        workflow.add_edge(START, "first_tool_call")
        workflow.add_edge("first_tool_call", "list_tables_tool")
        workflow.add_edge("list_tables_tool", "model_get_schema")
        workflow.add_edge("model_get_schema", "get_schema_tool")
        workflow.add_edge("get_schema_tool", "query_gen")
        workflow.add_edge("query_gen", "execute_query")
        workflow.add_edge("execute_query", "interpret_results")
        workflow.add_edge("interpret_results", END)

        elapsed = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"✅ Workflow graph built in {elapsed:.2f}s")

        self.app = workflow.compile()

    def query(self, question: str, recursion_limit: int = 10) -> Dict[str, Any]:
        start_time = datetime.now()
        logger = self.logger
        logger.info("=" * 80)
        logger.info(f"📝 New Question: {question}")

        try:
            result = self.app.invoke(
                {"messages": [HumanMessage(content=question)], "query_attempts": 0, "final_answer": None},
                config={"recursion_limit": recursion_limit}
            )

            sql_query = None
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and "SELECT" in str(msg.content).upper():
                    sql_query = str(msg.content).strip()
                    break

            answer = result.get("final_answer") or result["messages"][-1].content
            total_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"🧾 SQL Query: {sql_query}")
            logger.info(f"💬 Final Answer: {answer}")
            logger.info(f"⏱️ Total Runtime: {total_time:.2f}s")

            return {"sql_query": sql_query, "answer": answer}

        except GraphRecursionError:
            logger.error("⚠️ Graph recursion error detected.")
            return {"sql_query": None, "answer": "Query too complex or unclear."}
        except Exception as e:
            logger.error(f"❌ Unexpected Error: {str(e)}")
            return {"sql_query": None, "answer": f"Error: {str(e)}"}

# ======================================================================
# Helper Functions
# ======================================================================
def get_table_info(db_path: str) -> Dict[str, pd.DataFrame]:
    """Get information about all tables in the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    table_data = {}
    for table in tables:
        table_name = table[0]
        query = f"SELECT * FROM {table_name} LIMIT 5"
        df = pd.read_sql_query(query, conn)
        table_data[table_name] = df
    
    conn.close()
    return table_data

def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded database file"""
    upload_dir = Path("uploaded_dbs")
    upload_dir.mkdir(exist_ok=True)
    
    file_path = upload_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)

# ======================================================================
# Streamlit App
# ======================================================================
def main():
    # Custom CSS
    st.markdown("""
        <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            text-align: center;
            color: #666;
            margin-bottom: 2rem;
        }
        .stAlert {
            margin-top: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<p class="main-header">🤖 Text-to-SQL Agent</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ask questions in natural language, get intelligent answers from your database</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Get API Key from environment (hidden from user)
        api_key = os.getenv("GROQ_API_KEY", "")
        
        # Model selection (optional, can be hidden if you want single model)
        model_name = st.selectbox(
            "AI Model",
            ["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
            help="Select the AI model to use"
        )
        
        st.divider()
        
        # Database selection
        st.header("📊 Database")
        
        db_option = st.radio(
            "Choose database source",
            ["Upload Database", "Use Existing Database"],
            help="Upload a new SQLite database or use an existing one"
        )
        
        db_path = None
        
        if db_option == "Upload Database":
            uploaded_file = st.file_uploader(
                "Upload SQLite Database (.db)",
                type=["db", "sqlite", "sqlite3"],
                help="Upload your SQLite database file"
            )
            
            if uploaded_file:
                db_path = save_uploaded_file(uploaded_file)
                st.success(f"✅ Database loaded: {uploaded_file.name}")
        else:
            existing_db = st.text_input(
                "Database Path",
                value="university.db",
                help="Enter the path to your existing database"
            )
            if existing_db and os.path.exists(existing_db):
                db_path = existing_db
                st.success(f"✅ Connected to: {existing_db}")
            elif existing_db:
                st.error(f"❌ Database not found: {existing_db}")
        
        st.divider()
        
        # About
        with st.expander("ℹ️ About"):
            st.markdown("""
            **Text-to-SQL Agent** allows you to:
            - Ask questions in natural language
            - Get intelligent answers from your database
            - Upload custom SQLite databases
            - View database schema and sample data
            
            Powered by LangChain, LangGraph, and Groq.
            """)

    # Main content
    if db_path:
        # Check if API key is configured
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            st.error("❌ API key not configured. Please contact the administrator.")
            st.info("💡 Administrator: Add GROQ_API_KEY to your .env file")
            return
        
        # Initialize session state
        if 'agent' not in st.session_state or st.session_state.get('current_db') != db_path:
            with st.spinner("🔄 Initializing AI Agent..."):
                try:
                    st.session_state.agent = SQLAgent(
                        db_path=db_path,
                        model_name=model_name,
                        groq_api_key=api_key
                    )
                    st.session_state.current_db = db_path
                    st.success("✅ Ready to answer your questions!")
                except Exception as e:
                    st.error(f"❌ Error initializing agent: {str(e)}")
                    return
        
        # Tabs
        tab1, tab2 = st.tabs(["💬 Query", "📋 Database Info"])
        
        with tab1:
            # Chat interface
            st.subheader("Ask Your Question")
            
            # Initialize chat history
            if 'messages' not in st.session_state:
                st.session_state.messages = []
            
            # Display chat history
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # Chat input
            if question := st.chat_input("What would you like to know?"):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": question})
                with st.chat_message("user"):
                    st.markdown(question)
                
                # Get agent response
                with st.chat_message("assistant"):
                    with st.spinner("🤔 Thinking..."):
                        try:
                            result = st.session_state.agent.query(question)
                            answer = result["answer"]
                            st.markdown(answer)
                            
                            # Add assistant message
                            st.session_state.messages.append({"role": "assistant", "content": answer})
                        except Exception as e:
                            error_msg = f"❌ Error: {str(e)}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            
            # Clear chat button
            if st.button("🗑️ Clear Chat"):
                st.session_state.messages = []
                st.rerun()
        
        with tab2:
            st.subheader("Database Schema & Sample Data")
            
            try:
                table_data = get_table_info(db_path)
                
                if not table_data:
                    st.warning("No tables found in the database.")
                else:
                    # Table selector
                    selected_table = st.selectbox(
                        "Select a table to view",
                        options=list(table_data.keys())
                    )
                    
                    if selected_table:
                        st.markdown(f"### 📊 Table: `{selected_table}`")
                        
                        df = table_data[selected_table]
                        
                        # Show schema
                      # Create schema DataFrame
                        schema_df = pd.DataFrame({
                            'Column': df.columns,
                            'Type': df.dtypes.astype(str),
                            'Sample Value': [
                                str(df[col].iloc[0]) if len(df) > 0 else None
                                for col in df.columns
                            ]
                        })

                        # Display safely with updated Streamlit syntax
                        st.dataframe(schema_df, width='stretch') 
                        
                        # Show sample data
                        st.markdown("**Sample Data (First 5 rows):**")
                        st.dataframe(df, width='stretch')
                        
                        # Show record count
                        conn = sqlite3.connect(db_path)
                        count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {selected_table}", conn).iloc[0]['count']
                        conn.close()
                        st.info(f"📊 Total Records: {count}")
                        
            except Exception as e:
                st.error(f"❌ Error loading database info: {str(e)}")
    
    else:
        # Welcome message
        st.info("👈 Please select or upload a database from the sidebar to get started.")
        
        st.markdown("### 🚀 Getting Started")
        st.markdown("""
        1. Upload a SQLite database or use an existing one from the sidebar
        2. Start asking questions in natural language!
        
        ### 💡 Example Questions
        - What is the email of John Doe?
        - How many students are enrolled?
        - List all courses in the Computer Science department
        - What are the top 5 highest grades?
        """)

if __name__ == "__main__":
    main()