from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from math import floor
import igraph as ig
import networkx as nx
import json
import numpy as np

from graphmaker import cabinet, graph, models, config

palette = [
    "#001219",
    "#005f73",
    "#0a9396",
    "#94d2bd",
    "#e9d8a6",
    "#ee9b00",
    "#ca6702",
    "#bb3e03",
    "#ae2012",
    "#9b2226",
]


@dataclass
class GroupChoices:
    ID = "id"
    TYPE_DESCRIPTION = "typeDesc"
    INDUSTRY_LABEL = "projectIndustryLabel"


def get_color(n, palette):
    palette_size = len(palette)

    if n >= palette_size:
        idx = n - (palette_size * floor(n / palette_size))
        color = palette[idx]
    else:
        color = palette[n]

    return color


def extract_edges(project_data: dict, group_by: GroupChoices):
    team = project_data["detailed_team"]
    # team = [i for i in team if not i["endDate"]]

    leaders = project_data["leaders"]

    team_nodes = []
    for member in team:
        full_name = member["fullName"]

        if member["middle_name"] and member["first_name"]:
            short_name = f"{member['last_name']} {member['first_name'][0]}.{member['middle_name'][0]}"
        elif member["first_name"]:
            short_name = f"{member['last_name']} {member['first_name'][0]}."
        else:
            short_name = f"{member['last_name']}"

        if full_name is None:
            continue

        user_id = f"user_{member['userId']}"
        role = member["role"]

        try:
            join_date = datetime.strptime(member["startDate"], "%d.%m.%Y")
        except ValueError:
            continue
        except TypeError:
            continue

        now = datetime.now()

        duration = now - join_date
        node = models.UserNode(
            id=user_id,
            full_name=full_name,
            short_name=short_name,
            role=role,
            in_project_duration=duration.days,
        )
        team_nodes.append(node)

    leader_nodes = []
    for leader in leaders:

        if leader["middle_name"] and leader["first_name"]:
            short_name = f"{leader['last_name']} {leader['first_name'][0]}.{leader['middle_name'][0]}"
        elif leader["first_name"]:
            short_name = f"{leader['last_name']} {leader['first_name'][0]}."
        else:
            short_name = f"{leader['last_name']}"

        full_name = leader["name"] if "name" in leader else leader["fio"]
        ownerPrivilege = leader["ownerPrivilege"]
        if full_name is None or ownerPrivilege == 0:
            continue

        user_id = f"user_{leader['id']}"
        role = leader["role"]

        try:
            join_date = datetime.strptime(
                project_data["dateCreated"], "%d.%m.%Y %H:%M:%S"
            )
        except ValueError:
            continue

        now = datetime.now()

        duration = now - join_date
        node = models.UserNode(
            id=user_id,
            full_name=full_name,
            short_name=short_name,
            role=role,
            in_project_duration=duration.days,
        )
        leader_nodes.append(node)

    group = project_data[group_by]
    project_id = f"project_{project_data['id']}"

    project_node = models.ProjectNode(
        id=project_id, name=project_data["nameRus"], type=project_data["type"]
    )
    edges = []
    all_nodes = {}
    for node in team_nodes:
        edge = models.Edge(
            source=node,
            target=project_node,
            width=node.in_project_duration / 100,
            group=group,
        )
        edges.append(edge)
        all_nodes[node.id] = node

    for node in leader_nodes:
        edge = models.Edge(
            source=node,
            target=project_node,
            width=node.in_project_duration / 100,
            group=group,
        )
        edges.append(edge)
        all_nodes[node.id] = node

    return edges, all_nodes, project_node


@lru_cache(maxsize=5)
def make_graph(group_by: str = GroupChoices.INDUSTRY_LABEL) -> nx.Graph:
    data = cabinet.get_projects()

    g = nx.DiGraph()
    nodes = {}
    project_nodes = {}
    group_to_id = {}

    # конструирование связей
    for project in data:
        project_edges, project_team, project_node = extract_edges(
            project, group_by=group_by
        )
        for edge in project_edges:
            if edge.group not in group_to_id:
                group_to_id[edge.group] = len(group_to_id)

            color = get_color(group_to_id[edge.group], palette)
            g.add_edge(
                edge.source.id,
                edge.target.id,
                width=edge.width,
                group=edge.group,
                group_id=group_to_id[edge.group],
                color=color,
                label=edge.group,
            )

        nodes.update(project_team)
        project_nodes[project_node.id] = project_node

    for source, target, data in g.edges(data=True):
        source_node = nodes[source]
        target_node = project_nodes[target]

        g.nodes[source]["label"] = source_node.short_name
        g.nodes[source][
            "title"
        ] = f"{source_node.full_name}</br>{source_node.role}</br>{source_node.in_project_duration}"
        # g.nodes[source]["role"] = source_node.role
        g.nodes[source]["color"] = data["color"]
        g.nodes[source]["shape"] = "disc"
        g.nodes[source]["size"] = min(max([g.degree(source) / 2, 2]), 10)

        g.nodes[target]["label"] = target_node.name
        g.nodes[target]["title"] = f"{target_node.name}</br>{target_node.type}"
        # g.nodes[target]["type"] = target_node.type
        g.nodes[target]["color"] = data["color"]
        g.nodes[target]["shape"] = "square"
        g.nodes[target]["size"] = min(max([g.degree(target) / 2, 2]), 10)

    return g


def get_color(n, palette):
    palette_size = len(palette)

    if n >= palette_size:
        idx = n - (palette_size * floor(n / palette_size))
        color = palette[idx]
    else:
        color = palette[n]

    return color


@lru_cache(maxsize=5)
def formatted_graph(group: graph.GroupChoices, save_json: bool = False):
    g = graph.make_graph(group_by=group)
    g = nx.relabel.convert_node_labels_to_integers(g, label_attribute="node_id")

    h = ig.Graph.from_networkx(g)
    
    rng = np.random.default_rng(10)
    start_positions = rng.random((g.number_of_nodes(), 2))
    
    np.random.seed(10)
    layout = h.layout_fruchterman_reingold(weights="width", grid=False, niter=2000, seed=start_positions)

    tags = [
        models.Tag(key="Person", image="person.svg"),
        models.Tag(key="Tool", image="tool.svg"),
    ]

    edges = []

    exists_nodes = set()
    nodes = set()
    clusters = set()
    for source, target, data in g.edges(data=True):
        source_node = g.nodes[source]
        target_node = g.nodes[target]

        edges.append([source, target])

        x_source, y_source = layout[source]
        x_target, y_target = layout[target]

        source_score = min(max([g.degree(source) / 2, 2]), 10)
        target_score = min(max([g.degree(target) / 2, 2]), 10)

        if source not in exists_nodes:
            source_node = models.Node(
                key=source,
                label=source_node["label"],
                cluster=data["group_id"],
                x=x_source,
                y=y_source,
                tag="Person",
                score=source_score,
                URL="",
            )
            nodes.add(source_node)
            exists_nodes.add(source)

        if target not in exists_nodes:
            target_node = models.Node(
                key=target,
                label=target_node["label"],
                cluster=data["group_id"],
                x=x_target,
                y=y_target,
                tag="Tool",
                score=target_score,
                URL="",
            )
            nodes.add(target_node)
            exists_nodes.add(target)

        cluster = models.Cluster(
            key=data["group_id"], color=data["color"], clusterLabel=data["group"]
        )
        clusters.add(cluster)

    response = models.Response(nodes=nodes, edges=edges, clusters=clusters, tags=tags)

    if save_json:
        with open(f"{config.ROOT_DIR}/data/meim_{group}_graph.json", "w") as f:
            json.dump(response.dict(), f, ensure_ascii=False)

    return response


if __name__ == "__main__":
    formatted_graph(group=graph.GroupChoices.INDUSTRY_LABEL, save_json=True)
    formatted_graph(group=graph.GroupChoices.ID, save_json=True)
    from pprint import pprint

    pprint(graph)
