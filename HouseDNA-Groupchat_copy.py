import autogen
import os
from dotenv import load_dotenv
from autogen import AssistantAgent, UserProxyAgent
from autogen import ConversableAgent, UserProxyAgent, config_list_from_json
from autogen import register_function
import sqlite3
from pathlib import Path
from typing import List, Any
import agentops

# Load environment variables from .env file
load_dotenv()

# Get the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")
# api_key_ops = os.getenv("OPENAI_API_KEY")

agentops.init(api_key="paste here")


# # Lesson 6: Planning and Stock Report Generation

# ## Setup

config_list = [
    {
        'model': 'gpt-4o-mini',
        'api_key': api_key
    }
]

# ## Setup

llm_config={

    "seed": 42,
    "config_list": config_list,
    "temperature": 0
}

# DEFINE TOOLS


# DATABASE
def query_sql_database(query: str) -> List[Any]:
    """
    Function to query an SQLite database located on the user's system and return the results.
    
    You will be working with the 'properties' table, which has the following schema:
    [(0, 'zpid', 'BIGINT', 0, None, 0), (1, 'city', 'TEXT', 0, None, 0), (2, 'state', 'TEXT', 0, None, 0), (3, 'homeStatus', 'TEXT', 0, None, 0), 
    (4, 'streetAddress', 'TEXT', 0, None, 0), (5, 'zipcode', 'BIGINT', 0, None, 0), (6, 'bedrooms', 'FLOAT', 0, None, 0), (7, 'bathrooms', 'FLOAT', 0, None, 0), 
    (8, 'price', 'BIGINT', 0, None, 0), (9, 'longitude', 'FLOAT', 0, None, 0), (10, 'latitude', 'FLOAT', 0, None, 0), (11, 'homeType', 'TEXT', 0, None, 0), 
    (12, 'lotSize', 'FLOAT', 0, None, 0), (13, 'zestimate', 'FLOAT', 0, None, 0), (14, 'rentZestimate', 'BIGINT', 0, None, 0), 
    (15, 'dateSoldString', 'TEXT', 0, None, 0), (16, 'taxAssessedValue', 'FLOAT', 0, None, 0), (17, 'taxAssessedYear', 'FLOAT', 0, None, 0), 
    (18, 'parcelId', 'TEXT', 0, None, 0)].
    

    :param query: The SQL query to be executed.
    :return: A list containing the query results.
    """
    
    # Path to the database file
    db_path = Path(r"C:\Users\danielcarvalho.dcf\AppData\Local\Programs\Python\Python311\Scripts\Notebooks\Capstone\Daniel\Q&A-and-RAG-with-SQL-and-TabularData\data\csv_xlsx_sqldb.db")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Execute the SQL query
        cursor.execute(query)
        
        # Fetch all results
        results = cursor.fetchall()

        # Log the result (you can modify this to save or display results)
        print(f"Query executed successfully: {query}")
        print("Results:", results)
        
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        results = []

    finally:
        # Close the connection
        conn.close()

    return results

# Example usage:
# query_sql_database("SELECT * FROM tablename LIMIT 10;")


# SAVE MARKDOWN FILE
def save_markdown_file(filename: str, content: str) -> None:
    """
    Function to save a Markdown file to the current folder.

    :param filename: The name of the Markdown file (should include .md extension).
    :param content: The content to be written to the Markdown file.
    :return: None.
    """
    
    # Ensure the filename ends with .md extension
    if not filename.endswith(".md"):
        filename += ".md"
    
    try:
        # Write content to the Markdown file
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
        
        # Log the successful save
        print(f"Markdown file saved successfully: {filename}")
        
    except IOError as e:
        # Handle errors in writing to the file
        print(f"An error occurred while saving the Markdown file: {e}")

# Example usage:
# save_markdown_file("example_markdown", "# This is a title\n\nThis is some content in Markdown.")


# ## The task!

task = """Generate a real estate report to show some homes I am interested"""

# ## Build a group chat
# 
# This group chat will include these agents:
# 
# 1. **User_proxy** or **Admin**: to allow the user to comment on the report and ask the writer to refine it.
# 2. **Planner**: to determine relevant information needed to complete the task.
# 3. **Engineer**: to write code using the defined plan by the planner.
# 4. **Executor**: to execute the code written by the engineer.
# 5. **Writer**: to write the report.


user_proxy = autogen.ConversableAgent(
    name="Admin",
    system_message="Give the task, and send "
    "instructions to writer to refine the real estate report.",
    code_execution_config=False,
    llm_config=llm_config,
    human_input_mode="ALWAYS",
)

planner = autogen.ConversableAgent(
    name="Planner",
    system_message="Given a task, please determine "
    "what information is needed to complete the task. "
    "Please note that the information will all be retrieved using"
    " Python code. Please only suggest information that can be "
    "retrieved using Python code. "
    "After each step is done by others, check the progress and "
    "instruct the remaining steps. If a step fails, try to "
    "workaround",
    description="Planner. Given a task, determine what "
    "information is needed to complete the task. "
    "After each step is done by others, check the progress and "
    "instruct the remaining steps",
    llm_config=llm_config,
)

engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=llm_config,
    description="An engineer that writes code based on the plan "
    "provided by the planner. ",
    system_message="""You are a helpful AI assistant.
Solve tasks using your coding and language skills.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
You may need to generate SQL code to query a database that has only one table named 'properties'. here is an example query on that table so you can get a sense of the columns and values:
"SELECT * FROM properties LIMIT 5;
Results: [(63662682, 'Greer', 'SC', 'SOLD', '1008 Carriage Park Cir', 29650, 4.0, 3.0, 415000, -82.27929, 34.86798, 'SINGLE_FAMILY', 9583.0, 581300.0, 3153, '2021-09-28', 402970.0, 2023.0, '0534410100500'), (5716098, 'Lexington', 'NC', 'SOLD', '1309 Riverwood Dr', 27292, 3.0, 3.0, 375000, -80.29264, 35.654854, 'SINGLE_FAMILY', 80586.0, 447100.0, 1900, '2022-09-02', 262980.0, 2023.0, '06036L0000006000'), (29134937, 'Arlington', 'TX', 'SOLD', '1418 Cardinal St', 76010, 4.0, 2.0, 0, -97.08692, 32.724987, 'SINGLE_FAMILY', 9147.0, 240000.0, 1802, '2022-05-25', 213321.0, 2023.0, '03243176'), (101673757, 'Bayport', 'MN', 'OTHER', '945 Inspiration Pkwy S', 55003, 4.0, 3.0, 571000, -92.787865, 45.012478, 'SINGLE_FAMILY', 10018.0, 571000.0, 2999, '2017-11-14', 516300.0, 2023.0, '1002920420081'), (49400095, 'Rainier', 'WA', 'OTHER', '802 Tipsoo Loop S', 98576, 3.0, 1.25, 469900, -122.68318, 46.89975, 'MANUFACTURED', 67082.0, 469900.0, 2114, '2000-11-15', 429900.0, 2023.0, '63550014200')]"
The columns in the `properties` table are as follows:
| Column Name              | Data Type |
|-------------------------|-----------|
| zpid                    | BIGINT    |
| city                    | TEXT      |
| state                   | TEXT      |
| homeStatus              | TEXT      |
| streetAddress           | TEXT      |
| zipcode                 | BIGINT    |
| bedrooms                | FLOAT     |
| bathrooms               | FLOAT     |
| price                   | BIGINT    |
| longitude               | FLOAT     |
| latitude                | FLOAT     |
| homeType                | TEXT      |
| lotSize                 | FLOAT     |
| zestimate               | FLOAT     |
| rentZestimate           | BIGINT    |
| dateSoldString          | TEXT      |
| taxAssessedValue        | FLOAT     |
| taxAssessedYear         | FLOAT     |
| parcelId                | TEXT      |

If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.

Reply "TERMINATE" in the end when everything is done.
    """
)

# **Note**: In this lesson, you'll use an alternative method of code execution by providing a dict config. However, you can always use the LocalCommandLineCodeExecutor if you prefer. For more details about code_execution_config, check this: https://microsoft.github.io/autogen/docs/reference/agentchat/conversable_agent/#__init__

executor = autogen.ConversableAgent(
    name="Executor",
    system_message="Execute the code written by the "
    "engineer and report the result.",
    human_input_mode="NEVER",
    code_execution_config={
        "last_n_messages": 3,
        "work_dir": "coding",
        "use_docker": False,
    },
)

writer = autogen.ConversableAgent(
    name="Writer",
    llm_config=llm_config,
    system_message="Writer."
    "Please write a real estate report, Use tables where each row is a listing"
    " and put the content in pseudo ```md``` code block. "
    "You take feedback from the admin and refine your report."
    "everytime you generate a report, save it as a markdown file calling the save_markdown_file function"
    "if the user asks for different data ask the engineer to query the new data the user asked",
    description="Writer."
    "Write real estate report based on the code execution results and take "
    "feedback from the admin to refine the report."
)

## REGISTER THE TOOLS



# query_sql_database
register_function(
    query_sql_database,
    caller=engineer,  # The assistant agent can suggest calls to the calculator.
    executor=executor,  # The user proxy agent can execute the calculator calls.
    name="query_sql_database",  # By default, the function name is used as the tool name.
    description="A tool that queries a sql database",  # A description of the tool.
)

# save_markdown_file
register_function(
    save_markdown_file,
    caller=writer,  # The assistant agent can suggest calls to the calculator.
    executor=executor,  # The user proxy agent can execute the calculator calls.
    name="save_markdown_file",  # By default, the function name is used as the tool name.
    description="A tool that saves a markdown file to the current folder",  # A description of the tool.
)


# ## Define the group chat

groupchat = autogen.GroupChat(
    agents=[user_proxy, engineer, writer, executor, planner],
    messages=[],
    max_round=20,
)

manager = autogen.GroupChatManager(
    groupchat=groupchat, llm_config=llm_config
)


# ## Start the group chat!

# <p style="background-color:#ECECEC; padding:15px; "> <b>Note:</b> In this lesson, you will use GPT 4 for better results. Please note that the lesson has a quota limit. If you want to explore the code in this lesson further, we recommend trying it locally with your own API key.

groupchat_result = user_proxy.initiate_chat(
    manager,
    message=task,
)

# ## Add a speaker selection policy

# user_proxy = autogen.ConversableAgent(
#     name="Admin",
#     system_message="Give the task, and send "
#     "instructions to writer to refine the blog post.",
#     code_execution_config=False,
#     llm_config=llm_config,
#     human_input_mode="ALWAYS",
# )

# planner = autogen.ConversableAgent(
#     name="Planner",
#     system_message="Given a task, please determine "
#     "what information is needed to complete the task. "
#     "Please note that the information will all be retrieved using"
#     " Python code. Please only suggest information that can be "
#     "retrieved using Python code. "
#     "After each step is done by others, check the progress and "
#     "instruct the remaining steps. If a step fails, try to "
#     "workaround",
#     description="Given a task, determine what "
#     "information is needed to complete the task. "
#     "After each step is done by others, check the progress and "
#     "instruct the remaining steps",
#     llm_config=llm_config,
# )

# engineer = autogen.AssistantAgent(
#     name="Engineer",
#     llm_config=llm_config,
#     description="Write code based on the plan "
#     "provided by the planner.",
# )

# writer = autogen.ConversableAgent(
#     name="Writer",
#     llm_config=llm_config,
#     system_message="Writer. "
#     "Please write blogs in markdown format (with relevant titles)"
#     " and put the content in pseudo ```md``` code block. "
#     "You take feedback from the admin and refine your blog.",
#     description="After all the info is available, "
#     "write blogs based on the code execution results and take "
#     "feedback from the admin to refine the blog. ",
# )

# executor = autogen.ConversableAgent(
#     name="Executor",
#     description="Execute the code written by the "
#     "engineer and report the result.",
#     human_input_mode="NEVER",
#     code_execution_config={
#         "last_n_messages": 3,
#         "work_dir": "coding",
#         "use_docker": False,
#     },
# )

# groupchat = autogen.GroupChat(
#     agents=[user_proxy, engineer, writer, executor, planner],
#     messages=[],
#     max_round=10,
#     allowed_or_disallowed_speaker_transitions={
#         user_proxy: [engineer, writer, executor, planner],
#         engineer: [user_proxy, executor],
#         writer: [user_proxy, planner],
#         executor: [user_proxy, engineer, planner],
#         planner: [user_proxy, engineer, writer],
#     },
#     speaker_transitions_type="allowed",
# )

# manager = autogen.GroupChatManager(
#     groupchat=groupchat, llm_config=llm_config
# )

# groupchat_result = user_proxy.initiate_chat(
#     manager,
#     message=task,
# )

# # **Note**: You might experience slightly different interactions between the agents. The engineer agent may write incorrect code, which the executor agent will report and send back for correction. This process could go through multiple rounds.



agentops.end_session("Success")