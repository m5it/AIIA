#<b>AIIA</b> <br>
Script work similar to lm-studio but in terminal.<br>
<br>
#--<br>
#Usage:<br>
<b>Start program with all options included and work as chat bot.</b><br>
python run.py -m llama3.1<br>
<br>
<b>In this case AIIA work as date parse service. Important is chat memory we set with option -M 1</b><br>
python run.py -m llama3.1 -M 1 -Y "THU, 19 JUN"<br>
<b>Response:</b><br>
2025-06-19 00:00:00<br>
<br>
#--<br>
# User commands:<br>
#--<br>
<b>By running help inside of chat:</b><br>
!HELP^X # Press CTRL+X and EnTER to send to AIIA so we can use new lines, pasting etc..<br>
<br>
<b>Response:</b><br>
New Session - Like restarting program. Usage: !NEW SESSION<br>
Break Session - Start new history... Usage: !BREAK SESSION<br>
Stats - Display statistics for program Usage: !STATS<br>
Action Options - LIST, SET, GET action options Usage: <br>
LIST Ex.: !AO [action_num]<br>
GET Ex.: !AO [action_num] GET path<br>
!SET Ex.: AO [action_num] SET path=/Memorize<br>
<br>
Import Actions - Import actions from classes/code Usage: !IA<br>
Preview Imported Actions - Preview imported actions that are ready to get executed. Usage: !PA<br>
Execute Action - Execute specific action... Usage: !EA<br>
Clear Tools - Clear loaded tools to start fresh chat or load new tools. Usage: !CT<br>
Tools - Choose tools to use with AIIA. Usage: !TOOLS<br>
Preview History - Preview current chat history Usage: !PH<br>
Preview Memory - Preview current chat memorized messages. Usage: !PM<br>
Memory Specific - Memory specific message from history. Usage: !MS [history_num]<br>
Memory all history - Memory all rows from history. Usage: !MAH<br>
Memory Last - Memory last message from assistant. Usage: !ML<br>
Memory Delete Row - Delete specific row from memory in use. Usage: !MDR [memory_num]<br>
Memory Delete All - Delete all rows from memory in use. Usage: !MDA<br>
Update Handle - Reinit code of program. Used after program update so there is no need to stop the program. Usage: !UPDATE HANDLE<br>
Quit - Stop the program Usage: !QUIT<br>
Load - Load text file as input to send to AIIA. Usage: !LOAD textfile.txt Text of textfile.txt will be loaded with this text and sent to AIIA. This is example.<br>
Help - Display of available actions. Usage: !HELP<br>
<br>
