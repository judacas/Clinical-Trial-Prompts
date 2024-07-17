import networkx as nx
import matplotlib.pyplot as plt

def read_ann_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    entities = {}
    relations = []

    for line in lines:
        if line.startswith('T'):
            parts = line.strip().split('\t')
            entity_id = parts[0]
            entity_info = parts[1].split(' ')
            entity_type = entity_info[0]
            entity_start = int(entity_info[1])
            entity_end = entity_info[2]
            if ';' in entity_end:
                entity_end = [int(end) for end in entity_end.split(';')]
            else:
                entity_end = [int(entity_end)]
            entity_text = parts[2]
            entities[entity_id] = {
                'type': entity_type,
                'start': entity_start,
                'end': entity_end,
                'text': entity_text
            }
        elif line.startswith('R'):
            parts = line.strip().split('\t')
            relation_info = parts[1].split(' ')
            relation_type = relation_info[0]
            arg1 = relation_info[1].split(':')[1]
            arg2 = relation_info[2].split(':')[1]
            relations.append((relation_type, arg1, arg2))
        elif line.startswith('*'):
            parts = line.strip().split('\t')
            relation_info = parts[1].split(' ')
            relation_type = relation_info[0]
            args = [arg.split(':')[1] for arg in relation_info[1:] if ':' in arg]
            relations.append((relation_type, *args))

    return entities, relations

def visualize_ann(entities, relations):
    G = nx.DiGraph()

    for entity_id, entity in entities.items():
        G.add_node(entity_id, label=entity['text'])

    for relation in relations:
        if len(relation) == 3:
            relation_type, arg1, arg2 = relation
            G.add_edge(arg1, arg2, label=relation_type)
        else:
            relation_type, *args = relation
            for i in range(len(args) - 1):
                G.add_edge(args[i], args[i+1], label=relation_type)

    pos = nx.spring_layout(G)
    plt.figure(figsize=(15, 10))

    nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=3000, font_size=10, font_weight='bold', arrows=True)
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red')

    plt.show()

entities, relations = read_ann_file('chia_annotations.txt')
visualize_ann(entities, relations)
