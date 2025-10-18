# 🤖 Text-to-SQL Agent with LangGraph

An intelligent agent that converts natural language questions into SQL queries and provides human-readable answers. Built with LangChain, LangGraph, and powered by Groq's fast LLM models.

<!-- ## 🌟 Features


- **Natural Language to SQL**: Ask questions in plain English and get SQL queries executed
- **Intelligent Workflow**: Multi-step agent workflow using LangGraph for robust query processing
- **Multiple Interfaces**:
  - Interactive Streamlit web app (`app.py`)
  - Jupyter notebook for development and testing (`sql_agent_logger.ipynb`)
- **Comprehensive Logging**: Detailed logging system for debugging and monitoring
- **Database Flexibility**: Works with any SQLite database, includes sample university database
- **Error Handling**: Robust error handling with fallback mechanisms
- **Security**: Only SELECT queries allowed, prevents data modification -->

## 🏗️ Architecture

The project uses a sophisticated multi-node workflow built with LangGraph:

```
START → first_tool_call → list_tables_tool → model_get_schema → get_schema_tool → query_gen → execute_query → interpret_results → END
```

### Workflow Nodes:

1. **first_tool_call**: Initializes the workflow by listing database tables
2. **list_tables_tool**: Retrieves all available tables in the database
3. **model_get_schema**: AI model determines which tables need schema information
4. **get_schema_tool**: Retrieves detailed schema for relevant tables
5. **query_gen**: Generates SQL query from natural language question
6. **execute_query**: Executes the SQL query safely (SELECT only)
7. **interpret_results**: Converts query results into human-readable answers

## 📁 Project Structure

```
text-sql-langgraph-agentic-ai/
├── app.py                          # Streamlit web application
├── sql_agent_logger.ipynb         # Jupyter notebook for development
├── database_setup.py              # Creates sample university database
├── requirements.txt               # Python dependencies
├── university.db                  # Sample SQLite database
├── logger/
│   └── agent.log                 # Detailed execution logs
├── .env                          # Environment variables (API keys)
└── README.md
```

<!-- ### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd text-sql-langgraph-agentic-ai

# Install dependencies
pip install -r requirements.txt
``` -->

### 2. Environment Setup

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Database Setup

The project includes a sample university database. To create it:

```bash
python database_setup.py
```

This creates `university.db` with sample data including:

- Students, Teachers, Courses, Departments
- Enrollments, Exams, Results, Payments
- Library Records, Student Clubs, Attendance

s

### Sample Questions

Here are some list of sample question of how natural language the model take and interact with db sqlite and fetch the query in natural language .

- "What is the email of Nabin Gurung?"
- "How many students are enrolled in Computer Science?"
- "List all courses taught by Suman Adhikari"
- "Which students have the highest grades?"
- "Show me all payments made in January 2025"
- "What clubs is Aayush Shrestha a member of?"
