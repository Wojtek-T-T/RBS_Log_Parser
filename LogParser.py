import json
from re import I
import numpy as np

time_unit_length = 41
max_job = 300
task_set = []
event_list = []
executions_list = []

class RBS_task:
    def __init__(self, id, P, CPU, A, C, T, D, S, number_of_nodes, number_of_sequences, WCRT):
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
        self.WCRT_analysis = WCRT
        self.RTs_experiment = []
        self.WCRT_experiment = 0
        self.ART_experiment = 0
        self.BCRT_experiment = 0


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
    def __init__(self, type, task, sequence, node, job, start, end, part):
        self.type = type
        self.task = task
        self.sequence = sequence
        self.node = node
        self.job = job
        self.start = start
        self.end = end
        self.duration = 0
        self.cpu = 0
        self.part_of_execution = part
        self.discard_flag = 0

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

def import_taskset(task_to_parse):
    string = "taskset" + str(task_to_parse) + ".json"
    f = open(string, "r")
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
        WCRT = task['WCRT']

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
        imported_task = RBS_task(id, P, CPU, compute_adj_matrix(E, number_of_nodes), C, T, D, S, number_of_nodes, number_of_sequences, WCRT)
        task_set.append(imported_task)

    f.close()

def generate_trace(task_to_parse):
    global event_list
    string = "trace" + str(task_to_parse) + ".json"
    with open(string, "w") as outfile: 

        dictionaries = []  
        for element in event_list:

            if element.type == 1 and element.discard_flag == 0:

                name_string = "TASK " + str(element.task) + ", NODE " + str(element.node) + ", JOB " + str(element.job) + ", ex_prt " + str(element.part_of_execution)


                if len(task_set) > 4:
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

                # dictionary = {
                #         "pid": element.cpu,
                #         "tid": element.cpu,
                #         "ts": element.start,
                #         "dur": (element.end - element.start),
                #         "ph": "X",
                #         "name": name_string
                #         }               

                dictionaries.append(dictionary)

            elif element.type == 5:
                name_string = "AUT SIGNAL AFTER: TASK " + str(element.task) + ", NODE " + str(element.node) + ", JOB " + str(element.job) + ", ex_prt " + str(element.part_of_execution)
                dictionary = {
                        "pid": element.cpu,
                        "tid": element.cpu,
                        "ts": element.start,
                        "dur": (element.end - element.start),
                        "ph": "X",
                        "name": name_string
                        }               

                dictionaries.append(dictionary)
            else:
                continue

        json.dump(dictionaries, outfile)
        
def solve_preemptions():
    global event_list
    for element in event_list:
        if element.type != 1:
            continue
        for element2 in event_list:
            if element2.type != 1:
                continue
            if element.cpu == element2.cpu:
                if (element2.start > element.start and element2.end < element.end):
                    el1_prio = get_priority(element.task)
                    el2_prio = get_priority(element2.task)
                    if el2_prio > el1_prio:
                    #if element2.task < element.task:
                            new_event = RBS_event(1, element.task, element.sequence, element.node, element.job, element2.end, element.end, (element.part_of_execution + 1))
                            new_event.cpu = element.cpu
                            element.end = element2.start
                            event_list.append(new_event)



    # #Remove parts of a low priority job between 2 higher priority jobs (side effect of preemption solving)
    # for event in event_list:
    #     if event.type != 1:
    #         continue
    #     for event2 in event_list:
    #         if event2.type != 1:
    #             continue
    #         if event.task != event2.task and event2.end == event.start and get_priority(event.task) < get_priority(event2.task):
    #             for event3 in event_list:
    #                 if event3.type != 1:
    #                     continue
    #                 if (event3.task != event2.task):
    #                     continue
    #                 if(event2.job != event3.job):
    #                     continue
    #                 if event.end == event3.start:
    #                     #event_list.remove(event)
    #                     event.discard_flag = 1



            

def transformEventsToExecutions():
    global event_list
    for event in event_list:
        if event.type != 1:
            continue
        if event.discard_flag == 1:
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


def compute_RTs():
    for event in event_list:
        if event.type == 2:
            for execution in executions_list:
                if execution.task == event.task and execution.job == event.job and execution.node == task_set[event.task-1].number_of_nodes:
                    wc_response_t = (execution.end - event.start)/time_unit_length
                    task_set[event.task-1].RTs_experiment.append(wc_response_t)

def compute_RTs_short():
    for event in event_list:
        if event.type == 2:
            for event2 in event_list:
                if event2.type == 1:
                    if event2.task == event.task and event2.job == event.job and event2.node == task_set[event.task-1].number_of_nodes:
                        wc_response_t = (event2.end - event.start)/time_unit_length
                        task_set[event.task-1].RTs_experiment.append(wc_response_t)  

def compute_WCRT():   
    for task in task_set:
        #task.RTs_experiment.sort()
        #task.RTs_experiment.reverse()
        #one_p = len(task.RTs_experiment) / 100
        #one_p = 1
        for index in range(0, 3):
            task.RTs_experiment.pop(index)
        task.WCRT_experiment = max(task.RTs_experiment)



def compute_BCRT():
    for task in task_set:
        task.BCRT_experiment = min(task.RTs_experiment)

def compute_ART():
    for task in task_set:
        task.ART_experiment = sum(task.RTs_experiment) / len(task.RTs_experiment)

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
        if event.type != 2:
            task_index = event.task -1
            sequence_index = event.sequence -1
            cpu = task_set[task_index].cpu[sequence_index]
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


def read_and_convert_log_json(task_to_parse):
    temp_list = []
    string = "log" + str(task_to_parse) + ".json"
    f = open(string, "r")
    log_file = json.load(f)

    #Parse tasks from JSON file
    for log_event in log_file['log']:
        event_type = log_event['type']
        task = log_event['task']
        sequence = log_event['sequence']
        node = log_event['node']
        job = log_event['job']
        start = int(log_event['start'])
        end = int(log_event['end'])

        #if event_type == 1 or event_type == 2:
        event = RBS_event(event_type, task, sequence, node, job, start, end, 1)
        temp_list.append(event)

    #determine the time of the last release of the lowest period task
    task_lowest_period = 9999999
    task_lowest_period_id = 0
    for task in task_set:
        if task.period < task_lowest_period:
            task_lowest_period = task.period
            task_lowest_period_id = task.id

    latest_release = 0
    for event in temp_list:
        if event.type == 1 and event.task == task_lowest_period_id and event.job == max_job and event.node == task_set[task_lowest_period_id-1].number_of_nodes:
            latest_release = event.start

    if latest_release == 0:
        print("hallo")
        for event in temp_list:
            if event.type == 1 and event.task == task_lowest_period_id and event.job == 20 and event.node == task_set[task_lowest_period_id-1].number_of_nodes:
                latest_release = event.start

    for event in temp_list:
        if event.start < latest_release:
            event_list.append(event)


 
    add_cpu()

def print_info(task_to_parse):
    string = "experiment_outcome" + str(task_to_parse) + ".txt"
    with open(string, "w") as log:

        string = "\nAnalyzed WCRTs: \n"
        log.write(string)
        deadlines = []
        for task in task_set:
            string = str(round(task.WCRT_analysis)) + "\n" 
            log.write(string)
            deadlines.append(task.deadline)

        string = "\nPriorities: \n"
        log.write(string)
        for task in task_set:
            string = str(round(task.priority)) + "\n" 
            log.write(string)

        string = "\nWCRTs: \n"
        log.write(string)
        for task in task_set:
            string = str(round(task.WCRT_experiment)) + "\n" 
            log.write(string)

        string = "\nARTs: \n"
        log.write(string)
        for task in task_set:
            string = str(round(task.ART_experiment)) + "\n" 
            log.write(string)

        string = "\nBCRTs: \n"
        log.write(string)
        for task in task_set:
            string = str(round(task.BCRT_experiment)) + "\n" 
            log.write(string)

        string = "\ndeadlines: " +  str(deadlines)
        log.write(string)

        for task in task_set:
            for node_nr in range(0, task.number_of_nodes):
                log.write("\n")
                string = "task: " + str(task.id) + " node: " + str(node_nr+1) + "\n"
                log.write(string)
                for element in task.nodesET[node_nr]:
                    string = str(element) + "\n"
                    log.write(string) 

        for task in task_set:
            log.write("\n\n")
            string = "RTs task" + str(task.id) + ":"
            log.write(string)
            for element in task.RTs_experiment:
                string = str(round(element,2)) + "\n"
                log.write(string)

def print_info_short(task_to_parse):   
    string = "experiment_outcome" + str(task_to_parse) + "_short.txt"
    with open(string, "w") as log:

        string = "\nWCRTs: \n"
        log.write(string)
        for task in task_set:
            string = str(round(task.WCRT_experiment)) + "\n" 
            log.write(string)

        string = "\nARTs: \n"
        log.write(string)
        for task in task_set:
            string = str(round(task.ART_experiment)) + "\n" 
            log.write(string)

        string = "\nBCRTs: \n"
        log.write(string)
        for task in task_set:
            string = str(round(task.BCRT_experiment)) + "\n" 
            log.write(string)

        string = "\nPriorities: \n"
        log.write(string)
        for task in task_set:
            string = str(round(task.priority)) + "\n" 
            log.write(string)

        string = "\nAnalyzed WCRTs: \n"
        log.write(string)
        deadlines = []
        for task in task_set:
            string = str(round(task.WCRT_analysis)) + "\n" 
            log.write(string)
            deadlines.append(task.deadline)


        string = "\ndeadline: " +  str(deadlines)
        log.write(string)

        for task in task_set:
            log.write("\n\n")
            string = "RTs task" + str(task.id) + ":\n"
            log.write(string)
            for element in task.RTs_experiment:
                string = str(round(element,2)) + "\n"
                log.write(string)
    

def compute_statistics():
    transformEventsToExecutions()
    compute_RTs()
    compute_WCRT()
    compute_BCRT()
    compute_ART()
    compute_WCET()
    compute_ETs()

def compute_statistics_short():
    compute_RTs_short()
    compute_WCRT()
    compute_BCRT()
    compute_ART()


def complete_action(task_nr):
    print("importing tasks data...")
    import_taskset(task_nr)
    print("reading and converting log file...")
    read_and_convert_log_json(task_nr)
    print("solving preemptions conflicts...")
    solve_preemptions()
    print("computing durations...")
    compute_duration()
    print("generating trace...")
    generate_trace(task_nr)
    print("Computing statistics...")
    compute_statistics()
    print("printing statistics to file...")
    print_info(task_nr)

def short_action(task_nr):
    print("importing tasks data...")
    import_taskset(task_nr)
    print("reading and converting log file...")
    read_and_convert_log_json(task_nr)
    print("Computing statistics...")
    compute_statistics_short()
    print("printing statistics to file...")
    print_info_short(task_nr)

def main():
    for task_nr in range(44,106):
        print("STARING WITH TASK ", task_nr)
        complete_action(task_nr)
        task_set.clear()
        event_list.clear()
        executions_list.clear()




if __name__ == "__main__":
    main()
