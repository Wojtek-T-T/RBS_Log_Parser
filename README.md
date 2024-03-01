# RBS_Log_Parser
This programm reads the log file created by the implementation of RBS and converts it to chromium trace file for visualisation of the flow. Additionally WCRT, BCRT and ART are calculated and provided in form of an excell and .mat files.

In order to use the application set the following two values at the top of the file:

time_unit_length -> length of 1 time unit in microseconds


After setting the values, place the application in a directory with the following files:
- log.JSON -> logfile produced during the execution
- taskset.JSON -> description of the task set


# RBS_Log_Parser_automatic
This programm reads the log file created by the implementation of RBS and converts it to chromium trace file for visualisation of the flow. Additionally WCRT, BCRT and ART are calculated and provided in form of an excell and .mat files.
 
In order to use the application set the following two values at the top of the file:
time_unit_length -> length of 1 time unit in microseconds
number_of_sets -> number of task sets to parse

place it in one directory with the following files:
- logX.JSON -> logfile produced during the execution with X being a number between 1 and number of task sets to parse
- tasksetX.JSON -> description of the task set with X being a number between 1 and number of task sets to parse
