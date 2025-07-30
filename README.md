<b>AIIA</b> Script work similar to lm-studio but in terminal.

#--
# <b>Usage:</b><br>
# Start program with all options included and work as chat bot.
python run.py -m llama3.1

# In this case AIIA work as date parse service. Important is chat memory we set with option -M 1
python run.py -m llama3.1 -M 1 -Y "THU, 19 JUN"
# Response:
2025-06-19 00:00:00

#--
# User commands:
#--
# By running help inside of chat:
!HELP^X # Press CTRL+X and EnTER to send to AIIA so we can use new lines, pasting etc..

# Response:
New Session - Like restarting program. Usage: !NEW SESSION
Break Session - Start new history... Usage: !BREAK SESSION
Stats - Display statistics for program Usage: !STATS
Action Options - LIST, SET, GET action options Usage: 
LIST Ex.: !AO [action_num]
GET Ex.: !AO [action_num] GET path
!SET Ex.: AO [action_num] SET path=/Memorize

Import Actions - Import actions from classes/code Usage: !IA
Preview Imported Actions - Preview imported actions that are ready to get executed. Usage: !PA
Execute Action - Execute specific action... Usage: !EA
Clear Tools - Clear loaded tools to start fresh chat or load new tools. Usage: !CT
Tools - Choose tools to use with AIIA. Usage: !TOOLS
Preview History - Preview current chat history Usage: !PH
Preview Memory - Preview current chat memorized messages. Usage: !PM
Memory Specific - Memory specific message from history. Usage: !MS [history_num]
Memory all history - Memory all rows from history. Usage: !MAH
Memory Last - Memory last message from assistant. Usage: !ML
Memory Delete Row - Delete specific row from memory in use. Usage: !MDR [memory_num]
Memory Delete All - Delete all rows from memory in use. Usage: !MDA
Update Handle - Reinit code of program. Used after program update so there is no need to stop the program. Usage: !UPDATE HANDLE
Quit - Stop the program Usage: !QUIT
Load - Load text file as input to send to AIIA. Usage: !LOAD textfile.txt Text of textfile.txt will be loaded with this text and sent to AIIA. This is example.
Help - Display of available actions. Usage: !HELP

