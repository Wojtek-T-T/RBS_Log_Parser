import json
from re import I
import numpy as np

import openpyxl
from openpyxl import Workbook
import multiprocessing

import scipy.io

#SETTINGS
time_unit_length = 42
number_of_sets = 400



max_job = 300
task_set = []
event_list = []
executions_list = []

matlab_WCRT = []
matlab_WCRT_analysis = []
matlab_P = []
matlab_BCRT = []
matlab_ART = []
matlab_PRIO = []
matlab_rel_overhead = []
matlab_number_of_sequences = []

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
        self.lastJOB = 0
        self.periodUS = 0
        self.firstRelTime = 0
        self.replicasExecuted = []
        self.total_rel_overhead = []
        self.avg_rel_overhead = 0



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

        #compute period in microseconds
        imported_task.periodUS = T * time_unit_length

        task_set.append(imported_task)

    f.close()

def generate_trace(task_to_parse):
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
                        "dur": (element.end - element.start),
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

def determine_replicas_ex_pattern():
    for task in task_set:
        for node in range(1, task.number_of_nodes + 1):
            replicas = []
            for i in range(0, task.number_of_sequences):
                replicas.append(0)
            for event in event_list:
                if event.type != 1:
                    continue
                if event.task == task.id and event.node == node:
                    replicas[event.sequence -1] = replicas[event.sequence -1] + 1
            task.replicasExecuted.append(replicas)
                


    return
        
def solve_preemptions(cpu_to_handle):
    global event_list
    for element in event_list:
        if element.type != 1 or element.cpu != cpu_to_handle:
            continue
        for element2 in event_list:
            if element2.type != 1 or element2.cpu != cpu_to_handle:
                continue
            if (element2.start > element.start and element2.end < element.end):
                el1_prio = get_priority(element.task)
                el2_prio = get_priority(element2.task)
                if el2_prio > el1_prio:
                #if element2.task < element.task:
                        new_event = RBS_event(1, element.task, element.sequence, element.node, element.job, element2.end, element.end, (element.part_of_execution + 1))
                        new_event.cpu = element.cpu
                        element.end = element2.start
                        event_list.append(new_event)



def discard_foulty_events(cpu_to_handle):
    #Remove parts of a low priority job between 2 higher priority jobs (side effect of preemption solving)
    for event in event_list:
        if event.type != 1 or event.cpu != cpu_to_handle:
            continue
        for event2 in event_list:
            if event2.type != 1 or event2.cpu != cpu_to_handle:
                continue
            if event.task != event2.task and event2.end == event.start and get_priority(event.task) < get_priority(event2.task):
                for event3 in event_list:
                    if event3.type != 1:
                        continue
                    if (event3.task != event2.task):
                        continue
                    if(event2.job != event3.job):
                        continue
                    if event.end == event3.start:
                        #event_list.remove(event)
                        event.discard_flag = 1



            

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
                    response_time = (execution.end - event.start)/time_unit_length
                    if response_time > 0:
                        task_set[event.task-1].RTs_experiment.append(response_time)

def compute_RTs_short():
    for event in event_list:
        if event.type == 2:
            for event2 in event_list:
                if event2.type == 1:
                    if event2.task == event.task and event2.job == event.job and event2.node == task_set[event.task-1].number_of_nodes:
                        response_time = (event2.end - event.start)/time_unit_length
                        if response_time > 0:
                            task_set[event.task-1].RTs_experiment.append(response_time) 


def compute_release_overhead():
    for event in event_list:
        if event.type == 2:
            for event2 in event_list:
                if event2.type == 1:
                    if event2.task == event.task and event2.job == event.job and event2.node == 1:
                        overhead  = (event2.start - event.start)
                        if overhead > 0:
                            task_set[event.task-1].total_rel_overhead.append(overhead) 

    for task in task_set:
        task.avg_rel_overhead = sum(task.total_rel_overhead)/len(task.total_rel_overhead)  

def compute_WCRT():   
    for task in task_set:
        three_proc = (round(task.lastJOB*0.03))
        for index in range(0, three_proc+1):
            #task.RTs_experiment.pop(index)
            max_value = max(task.RTs_experiment)
            task.RTs_experiment.remove(max_value)
        #max_value = max(task.RTs_experiment)
        #task.RTs_experiment.remove(max_value)
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
            cpu = task_set[task_index].cpu[sequence_index ]
            event.cpu = cpu

def compute_duration():
    for event in event_list:
        event.duration = event.end - event.start

def read_and_convert_log_json(task_to_parse):
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

        if event_type == 6:
            task_set[task-1].firstRelTime = start
            continue

        event = RBS_event(event_type, task, sequence, node, job, start, end, 1)
        event_list.append(event)

        #determine latest job
        if event_type == 1:
            if task_set[task-1].lastJOB < job:
                task_set[task-1].lastJOB = job

        #determine which replica of a node is executed the most

    add_cpu()



def generate_release_events():

    for task in task_set:
        rel_list = []
        for job in range(1, task.lastJOB + 1):
            start = task.firstRelTime + (task.periodUS * job)
            event = RBS_event(2, task.id, 0, 0, job, start, 0, 1)
            rel_list.append(event)
        
        rel_list.reverse()

        for element in rel_list:
            event_list.insert(0, element)
    

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
        log.write("\n")

        log.write("\n")
        log.write("Nodes executions per sequence: \n")
        log.write("\n")
        for task in task_set:
            for element in task.replicasExecuted:
                log.write(str(element))
                log.write("\n")
            
            log.write("\n\n")

        for task in task_set:
            log.write("\n\n")
            string = "RTs task" + str(task.id) + ":\n"
            log.write(string)
            for element in task.RTs_experiment:
                string = str(round(element,2)) + "\n"
                log.write(string)

def sort_by_prio(task):
    return 100 - task.priority
    

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
    compute_release_overhead()
    determine_replicas_ex_pattern()


def complete_action(task_nr):
    print("importing tasks data...")
    import_taskset(task_nr)
    print("reading and converting log file...")
    read_and_convert_log_json(task_nr)
    print("solving preemptions conflicts...")

    solve_preemptions(1)
    solve_preemptions(2)
    solve_preemptions(3)
    solve_preemptions(4)

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
    generate_release_events()
    print("generating trace...")
    generate_trace(task_nr)
    print("Computing statistics...")
    compute_statistics_short()
    print("printing statistics to file...")
    print_info_short(task_nr)

def main():
    workbook = Workbook()
    workbook.save('exp_7_stats.xlsx')
    sheet  = workbook.active
    current_line = 3
    current_task_set = 0
    string_cell = "C" + str(current_line)
    sheet[string_cell] = "WCRT analysis"
    string_cell = "D" + str(current_line)
    sheet[string_cell] = "prio"
    string_cell = "E" + str(current_line)
    sheet[string_cell] = "WCRT experiment"
    string_cell = "F" + str(current_line)
    sheet[string_cell] = "ART experiment"
    string_cell = "G" + str(current_line)
    sheet[string_cell] = "BCRT experiment"
    string_cell = "H" + str(current_line)
    sheet[string_cell] = "Num nodes"
    string_cell = "I" + str(current_line)
    sheet[string_cell] = "Num seq"
    string_cell = "J" + str(current_line)
    sheet[string_cell] = "rel overhead"

    for task_nr in range(1,(number_of_sets+1)):
        print("STARING WITH TASK ", task_nr)



        short_action(task_nr)

        for event in event_list:
            if event.task == 4 and event.node == 1 and event.job == 1:
                print(event.start)



        #generate excell file
        current_task_set = current_task_set + 1
        string_cell = "B" + str(current_task_set*4)
        sheet[string_cell] = current_task_set

        task_set.sort(key=sort_by_prio)
        for task in task_set:
            current_line = current_line + 1


            string_cell = "C" + str(current_line)
            sheet[string_cell] = round(task.WCRT_analysis)

            string_cell = "D" + str(current_line)
            sheet[string_cell] = round(task.priority)

            string_cell = "E" + str(current_line)
            sheet[string_cell] = round(task.WCRT_experiment)

            string_cell = "F" + str(current_line)
            sheet[string_cell] = round(task.ART_experiment)

            string_cell = "G" + str(current_line)
            sheet[string_cell] = round(task.BCRT_experiment)

            string_cell = "H" + str(current_line)
            sheet[string_cell] = round(task.number_of_nodes)

            string_cell = "I" + str(current_line)
            sheet[string_cell] = round(task.number_of_sequences)

            string_cell = "J" + str(current_line)
            sheet[string_cell] = round(task.avg_rel_overhead)

            #For matlab file
            matlab_WCRT_analysis.append(round(task.WCRT_analysis))
            matlab_WCRT.append( round(task.WCRT_experiment))
            matlab_BCRT.append(round(task.BCRT_experiment))
            matlab_ART.append(round(task.ART_experiment))
            matlab_PRIO.append(task.priority)

            #if task.priority == 98:
               # matlab_rel_overhead.append(task.avg_rel_overhead)
               # matlab_number_of_sequences.append(task.number_of_sequences)

            


        




        workbook.save('exp_7_stats.xlsx')
        task_set.clear()
        event_list.clear()
        executions_list.clear()

        #print matlab file
        obj_arr = [np.array(matlab_WCRT_analysis), np.array(matlab_WCRT), np.array(matlab_BCRT), np.array(matlab_ART), np.array(matlab_PRIO)]
        scipy.io.savemat('log_file_parsed.mat', mdict={'Log_parsed': obj_arr})

        #obj_arr2 = [np.array(matlab_rel_overhead), np.array(matlab_number_of_sequences)]
       # scipy.io.savemat('rel_overhead2.mat', mdict={'Rel_overhead2': obj_arr2})

    workbook.save('exp_7_stats.xlsx')



if __name__ == "__main__":
    main()
