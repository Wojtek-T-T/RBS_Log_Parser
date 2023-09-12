import json
import numpy as np

task_set = []

class RBS_task:
    def __init__(self, id, P, CPU, A, C, T, D, S, number_of_nodes, number_of_sequences):
        self.id = id
        self.priority = P
        self.adj = A
        self.ex_times = C
        self.period = T
        self.deadline = D
        self.sequences = S
        self.cpu = CPU
        self.number_of_nodes = number_of_nodes
        self.number_of_sequences = number_of_sequences
        self.nodesWCET = []
        self.nodesET = []

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

def get_priority(t_id):
    for task in task_set:
        if (task.id == t_id):
            return task.priority

def list_to_integer(list):
    #list.reverse()
    value = 0
    for index in range(len(list)):
        if list[index] == 0:
            continue
        else:
            value = value + pow(2, index)
    return(value)

def compute_adj_matrix(A, number_of_nodes):

    #define matrix size
    adj_matrix = [[0 for i in range(number_of_nodes)] for i in range(number_of_nodes)]

    for element in A:
        row_ind = element[1] - 1
        col_ind = element[0] - 1
        adj_matrix [row_ind][col_ind] = 1    

    return adj_matrix

def import_taskset():
    f = open('taskset2.json', "r")
    data = json.load(f)
    
    #Parse tasks from JSON file
    for task in data['taskset']:
        id = task['id']
        E = list(task['E'])
        C = list(task['C'])
        T = int(task['T'])
        D = int(task['T'])
        S = list(task['SEQ'])
        P = task['P']
        CPU = list(task['AFF'])

        P = 99 - P

        #Compute the number of nodes
        number_of_nodes = 0
        for element in E:
            for index in range(2):
                if element[index] > number_of_nodes:
                    number_of_nodes = element[index]

        #Compute the number of sequences
        number_of_sequences = len(S)
        
        #Add task to taskset list
        imported_task = RBS_task(id, P, CPU, compute_adj_matrix(E, number_of_nodes), C, T, D, S, number_of_nodes, number_of_sequences)
        task_set.append(imported_task)

    f.close()

def import_settings():
    import_taskset()
    global task_num

    task_num = len(task_set)

    for task in task_set:
        number_of_nodes.append(task.number_of_nodes)
        number_of_sequences.append(task.number_of_sequences)
        cpu_assignment.append(task.cpu) 


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
        for element2 in event_list:
            if element.cpu == element2.cpu:
                if (element2.start > element.start and element2.end < element.end):
                    el1_prio = get_priority(element.task)
                    el2_prio = get_priority(element2.task)
                    if el2_prio > el1_prio:
                    #if element2.task < element.task:
                            new_event = RBS_event(1, element.task, element.sequence, element.node, element.job, element2.end)
                            new_event.end = element.end
                            new_event.cpu = element.cpu
                            element.end = element2.start
                            event_list.append(new_event)


    #Remove parts of a low priority job between 2 higher priority jobs (side effect of preemption solving)
    for event in event_list:
        for event2 in event_list:
            if event.task != event2.task and event2.end == event.start and get_priority(event.task) < get_priority(event2.task):
                for event3 in event_list:
                    if (event3.task != event2.task):
                        continue
                    if(event2.job != event3.job):
                        continue
                    if event.end == event3.start:
                        event_list.remove(event)

def transformEventsToExecutions():
    global task_num
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
    for task in task_set:
        for node_nr in range(1, task.number_of_nodes+1):
            node_wcet = 0
            for ex in executions_list:
                if ex.task == task.id and ex.node == node_nr:
                    if ex.executionTime > node_wcet:
                        node_wcet = ex.executionTime

            task.nodesWCET.append(node_wcet)

def compute_ETs():
    for task in task_set:
        for node_nr in range(1, task.number_of_nodes+1):
            node_ETs = []
            for ex in executions_list:
                if ex.task == task.id and ex.node == node_nr:
                    node_ETs.append(ex.executionTime)
            task.nodesET.append(node_ETs)


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

def print_info():
    with open("ex_times.txt", "w") as log:
        string = "\nWCRTs: " +  str(WCRT_list)
        log.write(string)
        string = "\nBCRTs: " +  str(BCRT_list)
        log.write(string)
        string = "\nARTs: " +  str(ART_list)
        log.write(string)

        for task in task_set:
            string = "WCETs task" + str(task.id) + ":" + str(task.nodesWCET)

        for task in task_set:
            for node_nr in range(0, task.number_of_nodes):
                log.write("\n")
                string = "task: " + str(task.id) + " node: " + str(node_nr+1) + "\n"
                log.write(string)
                for element in task.nodesET[node_nr]:
                    string = str(element) + "\n"
                    log.write(string)   

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
    compute_WCET()
    compute_ETs()

    print_info()


    
if __name__ == "__main__":
    main()
