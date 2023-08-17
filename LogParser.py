import json

#task settings
task_num = 0
number_of_nodes = []
number_of_sequences = []
cpu_assignment = []
priorities = []

#set offsets
task_offset = 5
sequence_offset = 9
node_ofset = 5
job_offset = 4
time_offset = 7
###################################

WCRT_list = []
BCRT_list = []
ART_list = []
ART_counter_list = []
event_list = []
executions_list = []

class RBS_execution:
    def __init__(self, task, sequence, node, job, start, end, executionTime):
        self.task = task
        self.sequence = sequence
        self.node = node
        self.job = job
        self.start = start
        self.end = end
        self.executionTime = executionTime
        self.responseTime = 0
        self.releaseTime = 0


class RBS_event:
    def __init__(self, type, task, sequence, node, job, start):
        self.type = type
        self.task = task
        self.sequence = sequence
        self.node = node
        self.job = job
        self.start = start
        self.end = 0
        self.duration = 0
        self.cpu = 0

def import_settings():
    global task_num

    with open("tasks_settings.txt", "r") as tasks_settings:

        #import number of tasks
        for line in tasks_settings:
            line_string = str(line)

            result = line_string.find("number_of_tasks")
            if result != (-1):
                task_num = obtain_value(line_string,'number_of_tasks', 17,',')
                break           

        #import number of nodes
        for i in range(1, task_num+1):
            string_to_search = "number_of_nodesT" + str(i)
            for line in tasks_settings:
                line_string = str(line)
                result = line_string.find(string_to_search)
                if result != (-1):
                    nodes_number  = obtain_value(line_string,string_to_search, 19,',')
                    number_of_nodes.append(nodes_number)
                    break

        #import number of sequences
        for i in range(1, task_num+1):
            string_to_search = "number_of_sequencesT" + str(i)
            for line in tasks_settings:
                line_string = str(line)
                result = line_string.find(string_to_search)
                if result != (-1):
                    sequences_number  = obtain_value(line_string,string_to_search, 23,',')
                    number_of_sequences.append(sequences_number)
                    break

        #import cpu assignments
        for i in range(1, task_num+1):
            assignemnts_cpu = []
            for x in range(1, (number_of_sequences[i-1]+1)):
                string_to_search = "cpu_assignmentT" + str(i) + "_S" + str(x)
                for line in tasks_settings:
                    line_string = str(line)
                    result = line_string.find(string_to_search)
                    if result != (-1):
                        assignemnts_cpu.append(obtain_value(line_string,string_to_search, 22,',')) 
                        break
           
            cpu_assignment.append(assignemnts_cpu)


def generate_trace():
    global task_num
    with open("sample.json", "w") as outfile: 

        dictionaries = []  
        for element in event_list:

            if element.type == 1:

                name_string = "TASK " + str(element.task) + ", NODE " + str(element.node) + ", JOB " + str(element.job)


                if task_num > 4:
                    # Data to be written
                    dictionary = {
                        "pid": element.cpu,
                        "tid": element.cpu,
                        "ts": element.start,
                        "dur": element.duration,
                        "ph": "X",
                        "name": name_string
                    }

                else:

                    color = ""

                    if element.task == 1:
                        color = "yellow"
                    elif element.task == 2:
                        color = "grey"
                    elif element.task == 3:
                        color = "white"
                    else:
                        color = "black"

                    # Data to be written
                    dictionary = {
                        "pid": element.cpu,
                        "tid": element.cpu,
                        "ts": element.start,
                        "dur": element.duration,
                        "ph": "X",
                        "name": name_string,
                        "cname" : str(color)
                    }

                dictionaries.append(dictionary)

            elif element.type == 2:
                name_string = "RELEASE OF TASK " + str(element.task)  + ", JOB " + str(element.job)

                dictionary = {
                    "pid": 1,
                    "tid": 1,
                    "ts": element.start,
                    "ph": "i",
                    "name": name_string,
                    "s": "g"
                }

                dictionaries.append(dictionary)

            else:
                continue

        json.dump(dictionaries, outfile)
        
def solve_preemptions():
    global task_num

    for element in event_list:
        if element.task == 1 or element.type != 1:
            continue
        else:
            for element2 in event_list:
                if element2.task < element.task:
                    if element.cpu == element2.cpu:
                        if (element2.start > element.start and element2.end < element.end and element2.end < element.end):

                            new_event = RBS_event(1, element.task, element.sequence, element.node, element.job, element2.end)
                            new_event.end = element.end
                            new_event.cpu = element.cpu

                            element.end = element2.start

                            event_list.append(new_event)

def transformEventsToExecutions():
    global task_num
    counter = 0
    for event in event_list:
        if event.type != 1:
            continue
        for element in executions_list:
            if element.task == event.task and element.node == event.node and element.job == event.job:

                #Detected slice of node was executed later than existing one
                if (event.end > element.end) and (event.start > element.start):
                    element.executionTime = element.executionTime + event.duration
                    element.end = event.end
                    continue

                #Detected slice of node was executed earlier than existing one
                if (event.end < element.end) and (event.start < element.start):
                    element.executionTime = element.executionTime + event.duration
                    element.start = event.start
                    continue

        new_execution = RBS_execution(event.task, event.sequence, event.node, event.job, event.start, event.end, event.duration)
        executions_list.append(new_execution)
    return

def compute_WCRT():
    #initialize WCRT list
    global task_num
    for i in range(task_num):
        WCRT_list.append(0) 

    for event in event_list:
        if event.type == 2:
            for execution in executions_list:
                if execution.task == event.task and execution.job == event.job and execution.node == number_of_nodes[(execution.task-1)]:
                    wc_response_t = execution.end - event.start
                    if wc_response_t > WCRT_list[(execution.task-1)]:
                        WCRT_list[(execution.task-1)] = wc_response_t


def compute_BCRT():

    #initialize BCRT list
    global task_num
    for i in range(task_num):
        BCRT_list.append(0) 

    for event in event_list:
        if event.type == 2:
            for execution in executions_list:
                if execution.task == event.task and execution.job == event.job and execution.node == number_of_nodes[(execution.task-1)]:
                    bc_response_t = execution.end - event.start

                    if BCRT_list[(execution.task-1)] == 0:
                        BCRT_list[(execution.task-1)] = bc_response_t
                    else:
                        if bc_response_t < BCRT_list[(execution.task-1)]:
                            BCRT_list[(execution.task-1)] = bc_response_t

def compute_ART():

    #initialize ART list
    global task_num
    for i in range(task_num):
        ART_list.append(0)
        ART_counter_list.append(0) 

    for event in event_list:
        if event.type == 2:
            for execution in executions_list:
                if execution.task == event.task and execution.job == event.job and execution.node == number_of_nodes[(execution.task-1)]:
                    response_t = execution.end - event.start
                    ART_list[(execution.task-1)] = ART_list[(execution.task-1)] + response_t
                    ART_counter_list[(execution.task-1)] = ART_counter_list[(execution.task-1)] + 1

    for i in range(task_num):
        ART_list[i] = round(ART_list[i] / ART_counter_list[i])

def compute_WCET():
    return

def add_cpu():
    for event in event_list:
        task_index = event.task -1
        sequence_index = event.sequence -1
        cpu = cpu_assignment[task_index][ sequence_index]
        event.cpu = cpu

def compute_duration():
    for event in event_list:
        event.duration = event.end - event.start

def obtain_value(line_string, value_type, offset, end_mark):
    index = line_string.find(value_type)
    extra_offset = 1
    while True:
        temp_index = index + offset + extra_offset
        if line_string[temp_index] == end_mark:
            extra_offset = extra_offset - 1
            break
        else:
            extra_offset = extra_offset + 1

    if(extra_offset == 0):
        return_value = line_string[index + offset]
    else:
        return_value = line_string[index + offset :(index + offset+ extra_offset + 1)]

    return int(return_value)

def read_and_convert_log():
    with open("log.txt", "r") as log:
        for line in log:
            line_string = str(line)
            result = line_string.find("NODE_EXECUTION_STARTED")
            if result != (-1):

                #find task number
                task = obtain_value(line_string,'task',task_offset,',')

                #find sequence number
                sequence = obtain_value(line_string,'sequence',sequence_offset,',')

                #find node number
                node = obtain_value(line_string,'node',node_ofset,',')

                #find job number
                job = obtain_value(line_string,'job',job_offset,',')

                #find start time
                start = obtain_value(line_string,'cycle', time_offset,'.')

                #create event
                event = RBS_event(1, task, sequence, node, job, start)
                event_list.append(event)

                continue

            result = line_string.find("NODE_EXECUTION_FINISHED")
            if result != (-1):

                #find task number
                task = obtain_value(line_string,'task', task_offset,',')

                #find sequence number
                sequence = obtain_value(line_string,'sequence', sequence_offset,',')

                #find node number
                node = obtain_value(line_string,'node', node_ofset,',')

                #find job number
                job = obtain_value(line_string,'job', job_offset,',')

                #find end time
                end = obtain_value(line_string,'cycle', time_offset,'.')

                for element in event_list:
                    if (element.task == task and element.sequence == sequence and element.node == node and element.job == job):
                        element.end = end
                continue

            result = line_string.find("NEW_JOB_RELEASED")
            if result != (-1):

                #find task number
                task = obtain_value(line_string,'task',task_offset,',')

                #find job number
                job = obtain_value(line_string,'job',job_offset,',')

                #find start time
                start = obtain_value(line_string,'cycle', time_offset,'.')

                #create event
                event = RBS_event(2, task, 0, 0, job, start)
                event_list.append(event)

                continue
        

def main():

    import_settings()
    read_and_convert_log()
    add_cpu()
    solve_preemptions()
    compute_duration()
    generate_trace()
    transformEventsToExecutions()


    compute_WCRT()
    compute_BCRT()
    compute_ART()
    print("WCRTs: ", WCRT_list)
    print("BCRTs: ", BCRT_list)
    print("ARTs: ", ART_list)

    #for element in executions_list:
        #print("task =", element.task,"node = ", element.node, "sequence = ", element.sequence,"job = ", element.job,"start =", element.start)

    



if __name__ == "__main__":
    main()
